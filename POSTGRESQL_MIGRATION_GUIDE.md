# PostgreSQL Migration & Alembic Setup Guide

**Status:** ✅ **COMPLETE**

## Overview

The Bank Statement Analyzer now supports PostgreSQL with automatic database migrations via Alembic. The system seamlessly switches between SQLite (development) and PostgreSQL (production) based on the `DATABASE_URL` configuration.

---

## What Was Implemented

### 1. PostgreSQL Support ([models.py](backend/models.py#L248-L274))

**Features:**
- **Auto-detection** - Automatically detects database type from `DATABASE_URL`
- **Connection Pooling** - Configured for PostgreSQL with:
  - `pool_size=10` - Base connection pool
  - `max_overflow=20` - Additional connections beyond pool
  - `pool_timeout=30` - Wait time for connection (seconds)
  - `pool_pre_ping=True` - Verify connections before use
  - `pool_recycle=3600` - Recycle connections after 1 hour
- **SQLite Compatibility** - Maintains `check_same_thread=False` for SQLite

### 2. Alembic Database Migrations

**Structure:**
```
backend/
├── alembic/
│   ├── versions/
│   │   └── a9d0008eea5f_initial_migration_with_all_tables.py
│   ├── env.py          # Migration environment configuration
│   ├── README
│   └── script.py.mako
└── alembic.ini         # Alembic configuration
```

**Configured:**
- Auto-imports models from [models.py](backend/models.py) for autogeneration
- Reads `DATABASE_URL` from [config.py](backend/config.py)
- Detects schema changes automatically

### 3. Initial Migration

**Generated:**
- Migration ID: `a9d0008eea5f`
- File: [a9d0008eea5f_initial_migration_with_all_tables.py](backend/alembic/versions/a9d0008eea5f_initial_migration_with_all_tables.py)
- **Includes all tables:**
  - users
  - clients
  - transactions
  - reconciliations
  - overall_reconciliations
  - transaction_merchants
  - session_states
  - rules
  - invoices
  - invoice_matches
  - session_vat_configs
  - learned_rules
  - custom_categories

---

## PostgreSQL Installation

### Windows

**Option 1: Official Installer**
1. Download from: https://www.postgresql.org/download/windows/
2. Run installer (PostgreSQL 15+ recommended)
3. Set password for `postgres` user
4. Default port: 5432

**Option 2: Docker**
```powershell
docker run --name postgres-statement-analyzer `
  -e POSTGRES_PASSWORD=yourpassword `
  -e POSTGRES_DB=statement_analyzer `
  -p 5432:5432 `
  -d postgres:15
```

### Linux/Mac

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Mac (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Create database
sudo -u postgres createdb statement_analyzer
```

---

## Configuration

### 1. Update Environment Variables

Edit your `.env` file:

```bash
# Production (PostgreSQL)
DATABASE_URL=postgresql://username:password@localhost:5432/statement_analyzer

# Or for connection with specific options
DATABASE_URL=postgresql://username:password@localhost:5432/statement_analyzer?sslmode=require
```

**Connection String Format:**
```
postgresql://[user[:password]@][host][:port][/database][?param1=value1&...]
```

### 2. Create PostgreSQL Database

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database
CREATE DATABASE statement_analyzer;

-- Create user
CREATE USER analyzer_user WITH PASSWORD 'yourpassword';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE statement_analyzer TO analyzer_user;

-- Exit
\q
```

---

## Migration Commands

### Run Migrations (Apply to Database)

```bash
cd backend
alembic upgrade head
```

**Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> a9d0008eea5f, Initial migration with all tables
```

### Create New Migration (After Model Changes)

```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

**Example:**
```bash
alembic revision --autogenerate -m "Add is_archived column to clients"
```

### View Migration History

```bash
cd backend
alembic history
```

### Rollback Migration

```bash
# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### View Current Version

```bash
alembic current
```

---

## Migration Workflow

### Making Schema Changes

1. **Edit Models** - Update [models.py](backend/models.py)
   ```python
   class Client(Base):
       # Add new column
       is_archived = Column(Boolean, default=False)
   ```

2. **Generate Migration**
   ```bash
   cd backend
   alembic revision --autogenerate -m "Add is_archived to clients"
   ```

3. **Review Migration** - Check generated file in `alembic/versions/`
   - Verify upgrade operations
   - Verify downgrade operations
   - Add data migrations if needed

4. **Apply Migration**
   ```bash
   alembic upgrade head
   ```

5. **Test**
   - Run application
   - Verify schema changes
   - Run tests

---

## Testing PostgreSQL Setup

### 1. Test Connection

```python
from backend.models import engine
from sqlalchemy import text

# Test connection
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(result.scalar())
```

### 2. Verify Pool Configuration

```python
from backend.models import engine

print(f"Database: {engine.url}")
print(f"Pool size: {engine.pool.size()}")
print(f"Max overflow: {engine.pool._max_overflow}")
print(f"Pool timeout: {engine.pool._timeout}")
```

### 3. Test Migration

```bash
# Apply all migrations
cd backend
alembic upgrade head

# Verify current version
alembic current

# Test rollback
alembic downgrade -1

# Re-apply
alembic upgrade head
```

### 4. Run Application Tests

```bash
# Set PostgreSQL DATABASE_URL in .env
DATABASE_URL=postgresql://user:password@localhost:5432/statement_analyzer_test

# Run tests
pytest backend/tests -v
```

---

## Connection Pooling Details

### Pool Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `pool_size` | 10 | Base connections maintained |
| `max_overflow` | 20 | Additional connections beyond pool |
| `pool_timeout` | 30s | Wait time for connection |
| `pool_pre_ping` | True | Verify connections before use |
| `pool_recycle` | 3600s | Recycle after 1 hour |

### Total Connections

- **Normal load:** 10 connections
- **Peak load:** Up to 30 connections (10 + 20 overflow)
- **Per-process:** Each worker has its own pool

### Monitoring Connections

```sql
-- View active connections
SELECT count(*) FROM pg_stat_activity 
WHERE datname = 'statement_analyzer';

-- View connection details
SELECT pid, usename, application_name, client_addr, state 
FROM pg_stat_activity 
WHERE datname = 'statement_analyzer';

-- Kill a connection
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'statement_analyzer' AND pid <> pg_backend_pid();
```

---

## Production Deployment

### 1. Environment Setup

```bash
# .env for production
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=postgresql://user:password@db-host:5432/statement_analyzer
SECRET_KEY=<strong-random-key>
```

### 2. Database Initialization

```bash
# Run migrations
cd backend
alembic upgrade head

# Verify
alembic current
```

### 3. Connection Limits

**PostgreSQL Configuration** (`postgresql.conf`):
```ini
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
```

**Calculate Per-App Pool:**
```
max_connections / number_of_app_instances = pool_size + max_overflow
Example: 100 / 3 instances = 33 connections per instance
```

### 4. Backup Strategy

```bash
# Backup database
pg_dump -U analyzer_user statement_analyzer > backup_$(date +%Y%m%d).sql

# Restore database
psql -U analyzer_user statement_analyzer < backup_20260212.sql
```

---

## Troubleshooting

### Connection Errors

**Error:** `FATAL: password authentication failed`
```bash
# Check pg_hba.conf for authentication methods
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Change: local all all peer
# To:     local all all md5
sudo systemctl restart postgresql
```

**Error:** `could not connect to server: Connection refused`
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start if needed
sudo systemctl start postgresql
```

### Pool Exhaustion

**Error:** `QueuePool limit of size X overflow Y reached`

**Solutions:**
1. Increase `pool_size` and `max_overflow` in [models.py](backend/models.py#L265-L266)
2. Reduce connection timeout
3. Check for connection leaks (always use `with` statements)
4. Add more app instances

### Migration Conflicts

**Error:** `Target database is not up to date`
```bash
# View current state
alembic current

# View history
alembic history

# Force to specific version
alembic stamp head
```

### Autogenerate Not Detecting Changes

**Solutions:**
1. Ensure models are imported in [alembic/env.py](backend/alembic/env.py#L14)
2. Check `target_metadata` is set correctly
3. Verify model changes are in `Base.metadata`
4. Try manual revision if autogenerate fails:
   ```bash
   alembic revision -m "Manual migration"
   # Edit generated file manually
   ```

---

## Performance Tips

### 1. Connection Pooling

✅ **Do:**
- Use connection pooling (already configured)
- Close sessions properly (use `with` statements)
- Set appropriate `pool_recycle` for load balancers

❌ **Don't:**
- Create new engines for each request
- Keep sessions open longer than needed
- Disable `pool_pre_ping` in production

### 2. Index Optimization

All existing indexes are preserved:
- `users.email` (unique)
- `clients.user_id`
- `transactions.client_id`, `session_id`, `category`, `date`
- Foreign keys automatically indexed

### 3. Query Optimization

```python
# Use lazy loading efficiently
user = db.query(User).options(
    joinedload(User.clients)
).filter(User.id == user_id).first()

# Batch operations
db.bulk_insert_mappings(Transaction, transactions_list)
db.commit()
```

---

## Migration from SQLite to PostgreSQL

### Data Migration

```bash
# 1. Export from SQLite
sqlite3 statement_analyzer.db .dump > sqlite_dump.sql

# 2. Convert SQLite dump to PostgreSQL syntax
# https://github.com/caiiiycuk/db-dump-converter

# 3. Import to PostgreSQL
psql -U analyzer_user statement_analyzer < postgresql_dump.sql

# 4. Update sequence values
psql -U analyzer_user statement_analyzer
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
SELECT setval('clients_id_seq', (SELECT MAX(id) FROM clients));
# ... repeat for all tables with auto-increment IDs
```

**OR use Alembic:**

```bash
# 1. Backup SQLite data programmatically
python tools/export_sqlite_data.py > data_backup.json

# 2. Update DATABASE_URL to PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/statement_analyzer

# 3. Run migrations
alembic upgrade head

# 4. Import data
python tools/import_data.py data_backup.json
```

---

## Next Steps

✅ PostgreSQL + Alembic setup complete!

**Remaining Phase 1 item:**
- ❌ **Cloud File Storage** - Migrate from local file storage to S3/Azure Blob/GCS

Would you like to proceed with Cloud File Storage implementation?
