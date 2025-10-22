# Tests

This directory contains tests for the Alithia researcher project.

## Test Structure

- `unit/` - Unit tests that don't require external services
- `integration/` - Integration tests that make real API calls
- `run_integration_tests.py` - Script to run integration tests

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest tests/unit/ -m "not integration"
```

### Integration Tests Only
```bash
pytest tests/integration/ -m integration
```

### Using the Integration Test Runner
```bash
python tests/run_integration_tests.py
```

### Specific Test Categories
```bash
# Run only slow tests
pytest -m slow

# Run tests excluding slow ones
pytest -m "not slow"

# Run integration tests with verbose output
pytest -m integration -v
```

## Test Markers

- `@pytest.mark.unit` - Unit tests (no external dependencies)
- `@pytest.mark.integration` - Integration tests (real API calls)
- `@pytest.mark.slow` - Slow running tests

## Integration Tests

Integration tests make real API calls to external services like ArXiv. These tests:

- Require internet connectivity
- May take longer to run
- Can be affected by external service availability
- Should be run in CI/CD pipelines

### Current Integration Tests

- `test_arxiv_client.py` - Tests ArXiv API client functionality

## Adding New Tests

### Unit Tests
1. Create test files in `tests/unit/`
2. Use `@pytest.mark.unit` marker
3. Mock external dependencies

### Integration Tests
1. Create test files in `tests/integration/`
2. Use `@pytest.mark.integration` marker
3. Make real API calls
4. Handle potential network issues gracefully

## Test Configuration

Pytest configuration is in `pyproject.toml` under `[tool.pytest.ini_options]`.
