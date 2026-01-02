# Scripts Directory

This directory contains various utility scripts for development, testing, and maintenance.

## Directory Structure

```
scripts/
├── manual-tests/       # Manual test scripts (require running services)
├── analysis/          # Analysis and evaluation scripts
├── db/               # Database management scripts
├── utilities/        # General utility scripts
└── *.py             # Top-level maintenance scripts
```

## Manual Tests (`manual-tests/`)

Scripts that require external services to be running:

### `test_api.py`
Test REST API endpoints (requires API server running)
```bash
# Start API first
python run_api.py

# Then run tests in another terminal
python scripts/manual-tests/test_api.py
```

### `test_db_connection.py`
Test database connectivity and operations
```bash
python scripts/manual-tests/test_db_connection.py
```

## Top-Level Scripts

### `smoke_test.py`
Quick smoke test of all Azure services
```bash
python scripts/smoke_test.py
```

### `build_rule_catalog.py`
Build validation rule catalog from markdown
```bash
python scripts/build_rule_catalog.py
```

### `eval_kpis.py`
Evaluate system KPIs and performance metrics
```bash
python scripts/eval_kpis.py
```

### `test_ui_setup.py`
Verify UI dependencies and configuration
```bash
python scripts/test_ui_setup.py
```

## Database Scripts (`db/`)

Scripts for database management and migrations:

- `create_tables.py` - Create all database tables
- `migrate_schema.py` - Run schema migrations
- `enable_postgis.py` - Enable PostGIS extension
- `add_content_hash_column.py` - Add content hash column

Usage:
```bash
python scripts/db/create_tables.py
python scripts/db/migrate_schema.py
```

## Utility Scripts (`utilities/`)

Helper scripts for development and debugging:

- `check_*.py` - Various status check scripts
- `list_*.py` - List database resources
- `show_*.py` - Display detailed information
- `view_*.py` - View blob storage contents
- `query_*.py` - Query database
- `profile_processing.py` - Performance profiling
- `analyze_batch.py` - Batch analysis

## Analysis Scripts (`analysis/`)

Scripts for evaluating system performance and accuracy.

## Best Practices

### Running Scripts

1. **Always activate virtual environment first:**
   ```bash
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

2. **Ensure environment variables are set:**
   ```bash
   # Load from .env file
   python-dotenv run -- python script.py
   
   # Or export manually
   export $(cat .env | xargs)
   ```

3. **Run from project root:**
   ```bash
   # Do this
   python scripts/smoke_test.py
   
   # Not this (may have import issues)
   cd scripts && python smoke_test.py
   ```

### Writing New Scripts

1. **Add proper imports:**
   ```python
   from __future__ import annotations
   import sys
   from pathlib import Path
   
   # Add project root to path
   PROJECT_ROOT = Path(__file__).resolve().parents[1]
   sys.path.insert(0, str(PROJECT_ROOT))
   ```

2. **Include docstring:**
   ```python
   """
   Script name and purpose.
   
   Usage:
       python scripts/my_script.py [options]
   
   Requirements:
       - Database must be running
       - .env file must be configured
   """
   ```

3. **Add error handling:**
   ```python
   try:
       main()
   except Exception as e:
       print(f"❌ Error: {e}")
       import traceback
       traceback.print_exc()
       sys.exit(1)
   ```

4. **Use logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   ```

## Automated Tests vs Manual Scripts

### Use pytest (tests/) for:
- Unit tests (mock external dependencies)
- Integration tests (can run in CI/CD)
- Automated regression tests
- Tests that should run on every commit

### Use manual scripts (scripts/) for:
- One-off maintenance tasks
- Interactive debugging
- Performance profiling
- Scripts that require manual intervention
- Tests that need specific external services running

## Contributing

When adding new scripts:

1. Place in appropriate subdirectory
2. Add comprehensive docstring
3. Update this README
4. Add to `.gitignore` if generates output files
5. Consider if it should be a pytest test instead

## See Also

- [Testing Guide](../docs/CONTRIBUTING.md#testing)
- [Development Setup](../docs/setup_guide.md)
- [Database Guide](../docs/DATABASE_CONNECTION_FIX.md)
