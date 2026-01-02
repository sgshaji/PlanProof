# Database Schema Management Guide

## Problem: Database Schema Mismatches

When the SQLAlchemy models don't match the actual database schema, you get errors like:
- `UndefinedColumn: column X does not exist`
- `AttributeError: type object 'Model' has no attribute 'column_name'`

## Systematic Solutions

### 1. Automated Schema Validation & Fixing ✅

**Tool:** `validate_schema.py`

```bash
# Run schema validator
python validate_schema.py
```

**What it does:**
- Compares SQLAlchemy models vs actual database schema
- Identifies missing tables, missing columns, type mismatches
- Generates a comprehensive report
- Offers automatic fixes with confirmation

**Usage modes:**
- `dry-run` - See what would be changed without making changes
- `yes` - Apply fixes automatically
- `no` - Exit without changes

**Benefits:**
- ✅ Catches ALL schema mismatches at once
- ✅ No trial and error
- ✅ Safe with dry-run mode
- ✅ Generates audit trail

### 2. Manual Column Addition

For quick single-column fixes:

```bash
python fix_schema.py
```

**When to use:** When you know exactly which column is missing and want a quick fix.

### 3. Database Migrations with Alembic

**For production environments:**

```bash
# Create new migration
alembic revision --autogenerate -m "Add missing columns"

# Review the migration file
# Edit alembic/versions/<timestamp>_add_missing_columns.py if needed

# Apply migration
alembic upgrade head
```

**Benefits:**
- ✅ Version controlled changes
- ✅ Rollback capability
- ✅ Works across environments
- ✅ Audit trail in git

### 4. Complete Database Recreation

**When schema is severely out of sync:**

```python
from planproof.db import Base, get_engine

# WARNING: This drops ALL data!
engine = get_engine()
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
```

**When to use:**
- Development environment only
- After pulling major schema changes
- When starting fresh

## Common Issues Fixed

### Issue 1: `Run.created_at` doesn't exist
**Root cause:** Column is named `started_at` in schema, not `created_at`
**Fix:** Changed all `Run.created_at` → `Run.started_at` in UI code

### Issue 2: Missing `submission_type` columns
**Root cause:** New columns added to model but not to database
**Fix:** Added via `fix_schema.py`:
- `submission_type` (VARCHAR)
- `submission_type_confidence` (FLOAT)
- `submission_type_source` (VARCHAR)

### Issue 3: `run_type` missing from runs table
**Root cause:** New field in model, missing in DB
**Fix:** Added `run_type VARCHAR(50) DEFAULT 'ui_single'`

## Best Practices

### Development Workflow

1. **Before starting work:**
   ```bash
   python validate_schema.py
   ```

2. **After pulling code changes:**
   ```bash
   git pull
   python validate_schema.py
   # If issues found, apply fixes
   ```

3. **After modifying models:**
   ```bash
   # Option A: Auto-migration
   alembic revision --autogenerate -m "Description"
   alembic upgrade head
   
   # Option B: Validate and fix
   python validate_schema.py
   ```

### Production Workflow

1. **Create migration in development:**
   ```bash
   alembic revision --autogenerate -m "Add new columns"
   ```

2. **Test migration:**
   ```bash
   alembic upgrade head  # Apply
   alembic downgrade -1  # Test rollback
   alembic upgrade head  # Reapply
   ```

3. **Commit migration:**
   ```bash
   git add alembic/versions/*.py
   git commit -m "feat: Add new columns to submissions table"
   ```

4. **Deploy to production:**
   ```bash
   git pull
   alembic upgrade head
   ```

## Prevention

### 1. Keep Models and Schema in Sync

When adding a column to a model:
```python
class MyModel(Base):
    __tablename__ = "my_table"
    
    # New column
    new_field = Column(String(100))  # Add this
```

Immediately create migration:
```bash
alembic revision --autogenerate -m "Add new_field to my_table"
alembic upgrade head
```

### 2. Use Alembic for All Schema Changes

❌ **Don't:**
```python
# Manually adding columns with raw SQL
conn.execute("ALTER TABLE...")
```

✅ **Do:**
```bash
alembic revision -m "Add column"
# Edit migration file
alembic upgrade head
```

### 3. Run Schema Validator in CI/CD

Add to `.github/workflows/test.yml`:
```yaml
- name: Validate database schema
  run: python validate_schema.py --check
```

## Tools Reference

### validate_schema.py

**Purpose:** Comprehensive schema validation and auto-fixing

**Features:**
- Compares all models vs database
- Identifies missing tables
- Identifies missing columns
- Reports type mismatches
- Auto-fixes with confirmation
- Dry-run mode for safety

**Usage:**
```bash
# Interactive mode
python validate_schema.py

# Auto-apply fixes (use with caution)
echo "yes" | python validate_schema.py
```

### fix_schema.py

**Purpose:** Quick fix for known missing columns

**Features:**
- Adds specific missing columns
- Checks existence before adding
- Commits changes automatically

**Usage:**
```bash
python fix_schema.py
```

### Alembic Commands

```bash
# Check current version
alembic current

# Create new migration
alembic revision --autogenerate -m "Message"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# See migration history
alembic history
```

## Troubleshooting

### Error: Cannot drop table topology
**Problem:** PostGIS extension conflict
**Solution:**
```sql
-- In psql:
DROP EXTENSION IF EXISTS postgis_topology CASCADE;
-- Then run: alembic upgrade head
```

### Error: Column already exists
**Problem:** Trying to add column that exists
**Solution:** Run `python validate_schema.py` to see actual state

### Error: Type mismatch
**Problem:** Column exists but with wrong type
**Solution:** Create Alembic migration with ALTER TABLE

### Error: Multiple heads
**Problem:** Merge conflict in migrations
**Solution:**
```bash
alembic merge heads -m "Merge migrations"
alembic upgrade head
```

## Summary

**Best approach for schema issues:**

1. **First time:** Run `python validate_schema.py` to see all issues
2. **Fix:** Let it auto-fix or create proper Alembic migration
3. **Prevent:** Use Alembic for all future schema changes
4. **CI/CD:** Add schema validation to automated tests

**Remember:**
- 🔍 Always validate before applying fixes
- 🧪 Use dry-run mode first
- 📝 Commit migrations to git
- ✅ Test in dev before production
- 🔄 Keep models and schema in sync

---

**Quick Commands:**
```bash
# Check schema
python validate_schema.py

# Fix schema issues
python validate_schema.py  # then type 'yes'

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head
```
