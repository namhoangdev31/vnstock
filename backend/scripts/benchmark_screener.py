"""Script benchmark hiệu năng Keyset Pagination của ScreenerSnapshot.

Mục tiêu SLA: DB Execution Time P95 < 10 ms (mục tiêu thực tế < 2 ms)
với 10.000 bản ghi giả lập và partial index:
  (roe DESC NULLS LAST, instrument_id ASC) WHERE is_active = true.

Cách dùng:
  uv run python scripts/benchmark_screener.py [--postgres] [--samples 10000] [--queries 100]
"""

import argparse
import random
import statistics
import time
import uuid
from datetime import date

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.models.entities.asset_master import Instrument
from app.models.entities.screener import ScreenerSnapshot
from app.services.screener_service import ScreenerCursor, ScreenerService


def run_benchmark(
    use_postgres: bool = False, total_samples: int = 10000, num_queries: int = 100
) -> None:
    if use_postgres and settings.DATABASE_URL:
        db_url = str(settings.DATABASE_URL)
        engine = create_engine(db_url, echo=False)
        is_postgres = True
    else:
        engine = create_engine("sqlite:///:memory:", echo=False)
        is_postgres = False

    SQLModel.metadata.create_all(engine)

    today = date(2026, 9, 21)
    batch_size = 1000

    print(f"[Benchmark] Seeding {total_samples:,} benchmark instruments & snapshots...")
    t0 = time.perf_counter()

    with Session(engine) as session:
        # Xóa dữ liệu cũ nếu dùng Postgres
        if is_postgres:
            session.exec(
                text("DELETE FROM screener_snapshot WHERE symbol LIKE 'BENCH_%'")
            )  # type: ignore
            session.commit()

        # Tạo 10.000 instruments và snapshots
        for b in range(0, total_samples, batch_size):
            insts = []
            snaps = []
            for i in range(b, b + batch_size):
                inst_id = uuid.uuid4()
                sym = f"BENCH_{i:05d}"
                # 85% có ROE, 15% ROE là None
                roe = (
                    round(random.uniform(-10.0, 45.0), 2)
                    if random.random() > 0.15
                    else None
                )
                pe = round(random.uniform(3.0, 40.0), 2) if roe else None
                ex = random.choice(["HOSE", "HNX", "UPCOM"])

                inst = Instrument(
                    id=inst_id,
                    canonical_code=f"EQUITY:{sym}",
                    instrument_type="equity",
                    exchange=ex,
                    is_active=True,
                )
                insts.append(inst)

                snap = ScreenerSnapshot(
                    instrument_id=inst_id,
                    snapshot_date=today,
                    symbol=sym,
                    exchange=ex,
                    industry="Technology",
                    is_active=True,
                    roe=roe,
                    pe=pe,
                    price=random.uniform(10.0, 150.0),
                )
                snaps.append(snap)

            session.add_all(insts)
            session.commit()
            session.add_all(snaps)
            session.commit()

    t_seed = time.perf_counter() - t0
    print(f"[Benchmark] Seeded {total_samples:,} records in {t_seed:.2f}s.")

    # Kiểm tra EXPLAIN
    db_exec_time_ms: float | None = None
    with Session(engine) as session:
        if is_postgres:
            explain_query = text(
                """
                EXPLAIN (ANALYZE, BUFFERS)
                SELECT * FROM screener_snapshot
                WHERE is_active = true
                ORDER BY roe DESC NULLS LAST, instrument_id ASC
                LIMIT 50;
                """
            )
            explain_res = session.exec(explain_query).all()  # type: ignore
            print("\n[Benchmark] PostgreSQL EXPLAIN (ANALYZE, BUFFERS) Plan:")
            for line in explain_res:
                line_str = str(line[0])
                print(f"  {line_str}")
                if "Execution Time:" in line_str:
                    try:
                        parts = line_str.split("Execution Time:")
                        db_exec_time_ms = float(parts[1].replace("ms", "").strip())
                    except Exception:
                        pass
        else:
            explain_query = text(
                """
                EXPLAIN QUERY PLAN
                SELECT * FROM screener_snapshot
                WHERE is_active = 1
                ORDER BY roe DESC, instrument_id ASC
                LIMIT 50;
                """
            )
            explain_res = session.exec(explain_query).all()  # type: ignore
            print("\n[Benchmark] SQLite EXPLAIN QUERY PLAN:")
            for line in explain_res:
                print(f"  {line}")

    # Chạy chuỗi queries đo độ trễ Keyset Pagination
    print(f"\n[Benchmark] Running {num_queries} keyset pagination queries...")
    latencies_ms: list[float] = []

    with Session(engine) as session:
        cursor: ScreenerCursor | None = None
        for _q in range(num_queries):
            t_start = time.perf_counter()
            resp = ScreenerService.query_screener_keyset(
                session=session,
                page_size=50,
                cursor=cursor,
                exchange="HOSE",
            )
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            latencies_ms.append(elapsed_ms)

            # Cập nhật cursor hoặc reset về đầu
            if resp.has_next and resp.next_cursor:
                cursor = resp.next_cursor
            else:
                cursor = None

    # Dọn dẹp dữ liệu benchmark nếu dùng Postgres
    if is_postgres:
        with Session(engine) as session:
            session.exec(
                text("DELETE FROM screener_snapshot WHERE symbol LIKE 'BENCH_%'")
            )  # type: ignore
            session.exec(
                text(
                    "DELETE FROM instrument WHERE canonical_code LIKE 'EQUITY:BENCH_%'"
                )
            )  # type: ignore
            session.commit()
            print("[Benchmark] Cleaned up benchmark rows from PostgreSQL.")

    # Tính toán số liệu thống kê SLA
    latencies_ms.sort()
    p50 = statistics.median(latencies_ms)
    p90 = latencies_ms[int(len(latencies_ms) * 0.90)]
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    p99 = latencies_ms[int(len(latencies_ms) * 0.99)]
    avg = statistics.mean(latencies_ms)

    print("\n" + "=" * 50)
    print("           SCREENER KEYSET BENCHMARK RESULTS     ")
    print("=" * 50)
    print(f"Total records in dataset : {total_samples:,}")
    print(f"Total queries executed   : {num_queries}")
    if is_postgres and db_exec_time_ms is not None:
        print(f"PostgreSQL DB Exec Time  : {db_exec_time_ms:.3f} ms")
    print(f"Average client latency   : {avg:.2f} ms")
    print(f"P50 client latency       : {p50:.2f} ms")
    print(f"P90 client latency       : {p90:.2f} ms")
    print(f"P95 client latency       : {p95:.2f} ms")
    print(f"P99 client latency       : {p99:.2f} ms")
    print("=" * 50)

    if is_postgres and db_exec_time_ms is not None:
        if db_exec_time_ms < 10.0:
            print(
                f"SUCCESS: PostgreSQL DB Execution Time ({db_exec_time_ms:.3f} ms) complies with SLA (< 10 ms)."
            )
        else:
            print(
                f"WARNING: PostgreSQL DB Execution Time ({db_exec_time_ms:.3f} ms) exceeds SLA (< 10 ms)."
            )
    elif p95 < 10.0:
        print(f"SUCCESS: P95 ({p95:.2f} ms) complies with SLA (< 10 ms).")
    else:
        print(f"WARNING: P95 ({p95:.2f} ms) exceeds SLA (10 ms).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Screener Keyset Pagination")
    parser.add_argument(
        "--postgres",
        action="store_true",
        help="Run benchmark against configured PostgreSQL",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=10000,
        help="Number of samples to seed (default: 10000)",
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=100,
        help="Number of queries to run (default: 100)",
    )
    args = parser.parse_args()

    run_benchmark(
        use_postgres=args.postgres, total_samples=args.samples, num_queries=args.queries
    )
