# Tests Directory

This directory contains the automated test suite for PlanProof.

## Directory Structure

```
tests/
├── conftest.py           # Pytest configuration and shared fixtures
├── unit/                 # Unit tests (fast, isolated)
├── integration/         # Integration tests (require services)
├── golden/              # Golden/snapshot tests
└── fixtures/            # Test data and fixtures
```

## Test Categories

### Unit Tests (`unit/`)

Fast, isolated tests that mock external dependencies.

**Characteristics:**
- Run in milliseconds
- No external services required
- Mock database, Azure services, file I/O
- Test individual functions/classes

**Run unit tests:**
```bash
pytest tests/unit/ -v
```

**Markers:**
```python
@pytest.mark.unit
def test_something():
    pass
```

### Integration Tests (`integration/`)

Tests that interact with real services.

**Characteristics:**
- Require running database
- May use Azure services (can be test subscriptions)
- Slower execution
- Test component interactions

**Run integration tests:**
```bash
# Requires services running
pytest tests/integration/ -v

# Skip if services unavailable
pytest -m "not requires_db and not requires_api"
```

**Markers:**
```python
@pytest.mark.integration
@pytest.mark.requires_db
def test_database_query():
    pass

@pytest.mark.integration
@pytest.mark.requires_api
@pytest.mark.slow
async def test_api_workflow():
    pass
```

### Golden Tests (`golden/`)

Snapshot/approval tests that compare outputs.

**Use for:**
- LLM prompt outputs
- Document parsing results
- Generated reports
- Template rendering

**Updating golden files:**
```bash
# Update all golden snapshots
pytest tests/golden/ --update-snapshots

# Review changes carefully
git diff tests/golden/snapshots/
```

## Test Configuration

### Markers

Available test markers (defined in `pyproject.toml`):

| Marker | Purpose | Usage |
|--------|---------|-------|
| `unit` | Fast unit tests | `-m unit` |
| `integration` | Integration tests | `-m integration` |
| `slow` | Long-running tests | `-m "not slow"` to skip |
| `requires_db` | Needs database | `-m "not requires_db"` to skip |
| `requires_api` | Needs API server | `-m "not requires_api"` to skip |
| `golden` | Snapshot tests | `-m golden` |

### Running Tests

**All tests:**
```bash
pytest
```

**By marker:**
```bash
# Only unit tests (fast)
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Only integration tests that need database
pytest -m "integration and requires_db"
```

**By directory:**
```bash
# Unit tests only
pytest tests/unit/

# Specific test file
pytest tests/unit/test_validation.py

# Specific test function
pytest tests/unit/test_validation.py::test_rule_validation
```

**With coverage:**
```bash
# Run with coverage report
pytest --cov=planproof --cov-report=html

# View coverage
open htmlcov/index.html
```

**Verbose output:**
```bash
pytest -v                    # Verbose
pytest -vv                   # Extra verbose
pytest --tb=short           # Short traceback
pytest --tb=long            # Full traceback
pytest -x                   # Stop on first failure
pytest --pdb                # Drop into debugger on failure
```

## Writing Tests

### Basic Test Structure

```python
"""Test module docstring."""

import pytest
from planproof.module import function_to_test


class TestClassName:
    """Group related tests."""
    
    def test_something(self):
        """Test docstring explaining what is tested."""
        # Arrange
        input_data = "test"
        
        # Act
        result = function_to_test(input_data)
        
        # Assert
        assert result == expected_output


@pytest.mark.unit
def test_standalone_function():
    """Test independent function."""
    assert 1 + 1 == 2
```

### Using Fixtures

```python
@pytest.fixture
def sample_data():
    """Provide test data."""
    return {"key": "value"}


def test_with_fixture(sample_data):
    """Use fixture data."""
    assert sample_data["key"] == "value"
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("test", "TEST"),
])
def test_uppercase(input, expected):
    """Test with multiple inputs."""
    assert input.upper() == expected
```

### Mocking

```python
from unittest.mock import Mock, patch


def test_with_mock():
    """Test with mocked dependency."""
    mock_db = Mock()
    mock_db.query.return_value = [{"id": 1}]
    
    result = function_using_db(mock_db)
    
    assert len(result) == 1
    mock_db.query.assert_called_once()


@patch('planproof.module.external_api_call')
def test_with_patch(mock_api):
    """Test with patched function."""
    mock_api.return_value = {"status": "success"}
    
    result = function_calling_api()
    
    assert result["status"] == "success"
```

### Testing Exceptions

```python
def test_raises_exception():
    """Test that exception is raised."""
    with pytest.raises(ValueError, match="Invalid input"):
        function_that_raises("bad_input")
```

## Test Data

### Fixtures Directory

Test data files in `tests/fixtures/`:
- `sample_documents/` - Example PDFs, images
- `sample_responses/` - API response examples
- `sample_configs/` - Configuration files
- `sample_database/` - SQL dumps or fixtures

### Loading Test Data

```python
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_pdf():
    """Load sample PDF for testing."""
    return FIXTURES_DIR / "sample_documents" / "test.pdf"


def test_document_processing(sample_pdf):
    """Test document processing."""
    result = process_document(sample_pdf)
    assert result is not None
```

## Best Practices

### DO ✅

1. **Write tests for all new code**
   - Aim for >80% coverage
   - Test happy path and edge cases
   - Include error conditions

2. **Use descriptive names**
   ```python
   # Good
   def test_validation_rejects_invalid_postal_code():
       pass
   
   # Bad
   def test_validation():
       pass
   ```

3. **One assertion per test (when possible)**
   ```python
   def test_user_creation():
       user = create_user("test")
       assert user.name == "test"
   
   def test_user_creation_generates_id():
       user = create_user("test")
       assert user.id is not None
   ```

4. **Isolate tests**
   - No dependencies between tests
   - Clean up after test
   - Use fixtures for setup/teardown

5. **Mark tests appropriately**
   ```python
   @pytest.mark.integration
   @pytest.mark.requires_db
   @pytest.mark.slow
   async def test_full_workflow():
       pass
   ```

### DON'T ❌

1. **Don't test implementation details**
   - Test behavior, not internals
   - Avoid testing private methods directly

2. **Don't use real credentials in tests**
   - Mock external services
   - Use test subscriptions if needed
   - Never commit secrets

3. **Don't write flaky tests**
   - No sleep() statements
   - No random data without seeds
   - Avoid time-dependent assertions

4. **Don't skip cleanup**
   ```python
   # Bad
   def test_creates_file():
       create_file("test.txt")
       # File left behind!
   
   # Good
   def test_creates_file(tmp_path):
       file_path = tmp_path / "test.txt"
       create_file(file_path)
       # tmp_path auto-cleaned
   ```

## Continuous Integration

Tests run automatically on:
- Every commit to main
- All pull requests
- Nightly builds (full suite with slow tests)

### CI Configuration

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest -m "not slow" --cov=planproof
    pytest -m "slow" --timeout=300
```

## Troubleshooting

### Tests Not Collected

**Problem:** Pytest finds 0 tests

**Solutions:**
1. Check file names start with `test_` or end with `_test.py`
2. Check function names start with `test_`
3. Check `conftest.py` doesn't have collection issues
4. Run with verbose: `pytest --collect-only -v`

### Import Errors

**Problem:** `ModuleNotFoundError` or import failures

**Solutions:**
1. Install package in editable mode: `pip install -e .`
2. Check `PYTHONPATH` includes project root
3. Ensure `__init__.py` files exist in packages
4. Run from project root: `pytest` (not `cd tests && pytest`)

### Database Tests Fail

**Problem:** Integration tests fail with database errors

**Solutions:**
1. Check database is running: `docker ps`
2. Verify connection string in `.env`
3. Run migrations: `alembic upgrade head`
4. Check database user permissions

### Async Tests Fail

**Problem:** `RuntimeError: Event loop is closed`

**Solutions:**
1. Install `pytest-asyncio`: `pip install pytest-asyncio`
2. Mark tests with `@pytest.mark.asyncio`
3. Check `conftest.py` has proper async setup
4. Use `pytest-asyncio` fixtures

### Slow Test Suite

**Solutions:**
1. Run unit tests only: `pytest -m unit`
2. Run in parallel: `pytest -n auto` (requires `pytest-xdist`)
3. Skip slow tests: `pytest -m "not slow"`
4. Profile slow tests: `pytest --durations=10`

## Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Core Logic | >90% | 85% |
| API Routes | >80% | 78% |
| Database | >80% | 82% |
| UI | >60% | 45% |
| Utilities | >70% | 88% |

View detailed coverage:
```bash
pytest --cov=planproof --cov-report=html
open htmlcov/index.html
```

## Resources

### Documentation
- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

### Internal Guides
- [Contributing Guide](../docs/CONTRIBUTING.md)
- [Development Setup](../docs/setup_guide.md)

### Test Examples
- Check `tests/unit/` for unit test patterns
- Check `tests/integration/` for integration test patterns
- Check `conftest.py` for fixture examples

## Contributing

When adding tests:
1. Follow naming conventions
2. Add appropriate markers
3. Include docstrings
4. Update this README if adding new patterns
5. Ensure tests pass before committing

---

**Current Test Count:** 382 tests  
**Last Updated:** 2024  
**Maintained By:** PlanProof Development Team
