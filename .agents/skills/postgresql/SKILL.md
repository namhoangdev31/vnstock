---
name: postgresql
description: "PostgreSQL best practices, SQL querying, schema design, indexes, Alembic migrations, database maintenance, and Docker operations for PostgreSQL. Use when interacting with PostgreSQL, writing or optimizing SQL queries, inspecting schemas, running psql, performing database migrations with Alembic, or troubleshooting PostgreSQL performance."
---

# PostgreSQL Skill Guide

This skill provides operational workflows, schema design rules, performance optimization patterns, and CLI commands for managing PostgreSQL in this project.

---

## 1. Project Database Architecture & Connections

- **Database Engine**: PostgreSQL 18 (Alpine/Debian via Docker Compose `db` service)
- **Default Database**: `app`
- **Default Superuser**: `postgres`
- **Local Port**: `5432`
- **Connection String (local development)**:
  ```env
  DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@localhost:5432/app
  ```
- **Docker Compose Service**:
  ```yaml
  db:
    image: postgres:18
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=app
    volumes:
      - app-db-data:/var/lib/postgresql
  ```

---

## 2. Common Operations & CLI Cheatsheet

### A. Connecting via psql in Docker
```bash
# Start the database container if not running
docker compose up -d db

# Open an interactive psql session
docker compose exec db psql -U postgres -d app

# Execute a one-off SQL query
docker compose exec db psql -U postgres -d app -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
```

### B. Essential psql Meta-Commands
```text
\l                 # List all databases
\dt                # List all tables in current database
\d <table_name>    # Describe table structure, columns, and constraints
\di                # List indexes
\df                # List functions
\dn                # List schemas
\x                 # Toggle expanded output (useful for wide records)
\timing            # Toggle query execution timing
\q                 # Quit psql
```

### C. Backup and Restore
```bash
# Dump the database to a SQL file
docker compose exec db pg_dump -U postgres app > backup.sql

# Restore from a SQL file
cat backup.sql | docker compose exec -T db psql -U postgres -d app
```

---

## 3. Alembic Migrations with SQLModel / SQLAlchemy

This project uses SQLModel with Alembic for database migrations.

### Running Migrations
From the project root:
```bash
# Generate a new migration after modifying SQLModel models
uv run alembic revision --autogenerate -m "Add new table or column"

# Apply pending migrations to head
uv run alembic upgrade head

# Rollback the last migration
uv run alembic downgrade -1

# Show migration history
uv run alembic history --verbose

# Show current database revision
uv run alembic current
```

### Safe Migration Best Practices
1. **Never drop columns or rename tables directly in production without a transition phase**:
   - Step 1: Add new column (nullable or with default).
   - Step 2: Dual-write in application code.
   - Step 3: Backfill existing records.
   - Step 4: Remove references from code and then drop old column.
2. **Adding Indexes without Locking**:
   - For large tables, create indexes concurrently to prevent write locks:
     ```sql
     CREATE INDEX CONCURRENTLY idx_users_email ON "user" (email);
     ```
3. **Avoid table locks on `DEFAULT`**:
   - In PostgreSQL 11+, `ALTER TABLE ... ADD COLUMN ... DEFAULT ...` on non-volatile defaults is an instant metadata update.

---

## 4. Schema & Data Types Guidelines

| Requirement | Recommended Type | Anti-Pattern | Reason |
|:---|:---|:---|:---|
| **Primary Keys** | `UUID` (UUIDv7 preferred) or `BIGINT IDENTITY` | `SERIAL` / `INT` | 32-bit INT overflows at ~2.1B; UUID avoids collision in distributed setups. |
| **Timestamps** | `TIMESTAMPTZ` (`TIMESTAMP WITH TIME ZONE`) | `TIMESTAMP` | Prevents subtle timezone comparison bugs. |
| **Flexible JSON** | `JSONB` | `JSON` or `TEXT` | `JSONB` is parsed binary, indexable via GIN, and faster to query. |
| **Monetary / Decimal** | `NUMERIC` or `INTEGER` (in cents) | `FLOAT` / `REAL` | Floating-point rounding errors. |
| **Short Strings** | `VARCHAR(N)` or `TEXT` | `CHAR(N)` | `CHAR(N)` pads with trailing spaces. |

---

## 5. Indexing Strategies

1. **B-Tree (Default)**:
   - Use for equality (`=`), comparison (`<`, `<=`, `>`, `>=`), and sorting (`ORDER BY`).
   - Order compound indexes: `(equality_column, range_column)`.
2. **Partial Indexes**:
   - For queries targeting specific subsets (e.g., active rows):
     ```sql
     CREATE INDEX idx_orders_unprocessed ON orders (created_at) WHERE status = 'pending';
     ```
   - Drastically reduces index size and write overhead.
3. **GIN Indexes (Generalized Inverted Index)**:
   - For `JSONB` document searches or full-text search (`tsvector`):
     ```sql
     CREATE INDEX idx_items_metadata ON item USING gin (metadata jsonb_path_ops);
     ```

---

## 6. Query Optimization & Diagnostics

### Analyzing Query Performance
Always check the query execution plan with `EXPLAIN ANALYZE`:
```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM "user" WHERE email = 'user@example.com';
```

Key signals to look for:
- **`Seq Scan` on large tables**: Missing index.
- **`Buffers: shared read`**: Disk I/O occurred. A well-tuned query should primarily hit `shared hit` (RAM cache).
- **`Rows Removed by Filter` high**: Index is missing or filter condition is not selective enough.

### Connection Management
- Use connection pooling (e.g., SQLAlchemy engine pool configuration with sensible `pool_size` and `max_overflow`).
- Avoid long-running idle transactions (`idle in transaction`), as they hold locks and prevent VACUUM from reclaiming dead tuples.

---

## 7. Related Skills
- See [supabase-postgres-best-practices](file:///Volumes/developer101/code/vnstock/.agents/skills/supabase-postgres-best-practices/SKILL.md) for deeper deep-dive rules covering RLS, connection scaling, locking diagnostics, and vector search.
