"""Process-wide lease for the quant daemon.

PostgreSQL advisory locks are connection-scoped.  Keeping the connection open
for the lifetime of the lease gives us a distributed singleton without adding
another table or allowing two web workers to poll the market concurrently.
"""

import logging
import threading
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


class PostgresAdvisoryLease:
    """Acquire a PostgreSQL advisory lock and retain its connection."""

    def __init__(self, engine: Engine, lock_name: str) -> None:
        self.engine = engine
        self.lock_name = lock_name
        self._connection: Connection | None = None
        self._lock = threading.Lock()

    def get_holder_info(self) -> dict[str, Any] | None:
        """Query PostgreSQL to find which backend session currently holds the lease."""
        if self.engine.dialect.name != "postgresql":
            return None
        try:
            with self.engine.connect() as conn:
                row = (
                    conn.execute(
                        text(
                            """
                        SELECT
                            l.pid,
                            a.state,
                            a.application_name,
                            a.client_addr::text as client_ip,
                            a.backend_start::text as backend_start,
                            a.state_change::text as state_change
                        FROM pg_locks l
                        LEFT JOIN pg_stat_activity a ON l.pid = a.pid
                        WHERE l.locktype = 'advisory'
                          AND ((l.classid::bigint << 32) | (l.objid::bigint & 4294967295)) = hashtext(:lock_name)::bigint
                          AND l.pid != pg_backend_pid()
                        LIMIT 1
                        """
                        ),
                        {"lock_name": self.lock_name},
                    )
                    .mappings()
                    .first()
                )
                if row:
                    return dict(row)
        except Exception as exc:
            logger.debug("Failed to query advisory lease holder info: %s", exc)
        return None

    def break_lease(self) -> bool:
        """Terminate any remote database connection currently holding the advisory lock."""
        if self.engine.dialect.name != "postgresql":
            return True
        try:
            with self.engine.connect() as conn:
                terminated = (
                    conn.execute(
                        text(
                            """
                        SELECT pg_terminate_backend(l.pid)
                        FROM pg_locks l
                        WHERE l.locktype = 'advisory'
                          AND ((l.classid::bigint << 32) | (l.objid::bigint & 4294967295)) = hashtext(:lock_name)::bigint
                          AND l.pid != pg_backend_pid()
                        """
                        ),
                        {"lock_name": self.lock_name},
                    )
                    .scalars()
                    .all()
                )
                if terminated:
                    logger.warning(
                        "Force terminated %d stale lease holder backend(s) for lock '%s'",
                        len(terminated),
                        self.lock_name,
                    )
                    return any(terminated)
        except Exception as exc:
            logger.warning("Failed to break stale advisory lease: %s", exc)
        return False

    def acquire(self, force: bool = False) -> bool:
        """Return whether this process became the active daemon owner."""
        with self._lock:
            if self._connection is not None:
                return True

            # SQLite is used by unit tests and has no advisory-lock primitive.
            # Production is PostgreSQL, where the lock is mandatory.
            if self.engine.dialect.name != "postgresql":
                return True

            if force:
                self.break_lease()
                import time

                time.sleep(0.3)

            connection = self.engine.connect()
            try:
                acquired = bool(
                    connection.execute(
                        text("SELECT pg_try_advisory_lock(hashtext(:lock_name))"),
                        {"lock_name": self.lock_name},
                    ).scalar()
                )
            except Exception:
                connection.close()
                raise

            if not acquired:
                connection.close()
                holder = self.get_holder_info()
                if holder:
                    logger.warning(
                        "Advisory lease '%s' is held by PID %s (state: %s, client: %s, since: %s)",
                        self.lock_name,
                        holder.get("pid"),
                        holder.get("state"),
                        holder.get("client_ip"),
                        holder.get("backend_start"),
                    )
                return False

            self._connection = connection
            logger.info("Acquired daemon advisory lease: %s", self.lock_name)
            return True

    def release(self) -> None:
        """Release the lock and return its dedicated connection to the pool."""
        with self._lock:
            connection = self._connection
            self._connection = None
            if connection is None or self.engine.dialect.name != "postgresql":
                return
            try:
                connection.execute(
                    text("SELECT pg_advisory_unlock(hashtext(:lock_name))"),
                    {"lock_name": self.lock_name},
                )
            except Exception:
                logger.warning("Failed to release daemon advisory lease", exc_info=True)
            finally:
                connection.close()
