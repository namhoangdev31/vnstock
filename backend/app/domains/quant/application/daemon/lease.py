"""Process-wide lease for the quant daemon.

PostgreSQL advisory locks are connection-scoped.  Keeping the connection open
for the lifetime of the lease gives us a distributed singleton without adding
another table or allowing two web workers to poll the market concurrently.
"""

import logging
import threading

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

    def acquire(self) -> bool:
        """Return whether this process became the active daemon owner."""
        with self._lock:
            if self._connection is not None:
                return True

            # SQLite is used by unit tests and has no advisory-lock primitive.
            # Production is PostgreSQL, where the lock is mandatory.
            if self.engine.dialect.name != "postgresql":
                return True

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
