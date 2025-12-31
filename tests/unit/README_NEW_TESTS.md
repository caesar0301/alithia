# ArXrec Optimization Unit Tests

This directory contains comprehensive unit tests for the enhanced ArXiv recommendation agent.

## New Test Suites

### 1. `test_arxiv_arxiv_paper_fetcher.py` (18 tests)

Tests for the enhanced ArXiv paper fetcher with automatic fallback strategies.

**Test Coverage:**
- ✅ Initialization and configuration
- ✅ API search strategy
- ✅ RSS feed fallback
- ✅ Web scraper fallback
- ✅ Retry logic with exponential backoff
- ✅ Debug mode
- ✅ Error handling
- ✅ Convenience function

**Key Tests:**
```bash
# Test successful API search
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py::test_fetch_papers_api_search_success -v

# Test fallback to RSS when API fails
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py::test_fetch_papers_rss_fallback -v

# Test web scraper as last resort
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py::test_fetch_papers_web_scraper_fallback -v

# Test retry logic
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py::test_fetch_with_api_search_retry_logic -v
```

**Run All Paper Fetcher Tests:**
```bash
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py -v
```

---

### 2. `test_web_scraper.py` (16 tests)

Tests for the ArXiv web scraping fallback mechanism.

**Test Coverage:**
- ✅ Web scraper initialization
- ✅ Search URL construction
- ✅ HTML parsing
- ✅ Paper entry extraction
- ✅ Date filtering
- ✅ Pagination handling
- ✅ Error recovery
- ✅ Individual paper details scraping

**Key Tests:**
```bash
# Test URL building
pytest tests/unit/test_web_scraper.py::test_build_search_url_multiple_categories -v

# Test paper parsing
pytest tests/unit/test_web_scraper.py::test_parse_paper_entry_valid -v

# Test date filtering
pytest tests/unit/test_web_scraper.py::test_filter_by_date -v

# Test pagination
pytest tests/unit/test_web_scraper.py::test_scrape_arxiv_search_pagination -v
```

**Run All Web Scraper Tests:**
```bash
pytest tests/unit/test_web_scraper.py -v
```

---

### 3. `test_reranker.py` (14 tests)

Tests for the optimized paper reranking system.

**Test Coverage:**
- ✅ Reranker initialization
- ✅ Sentence transformer reranking
- ✅ Error handling and fallback
- ✅ Time-decay weighting
- ✅ Batch processing
- ✅ Custom model support
- ✅ Empty/invalid data handling
- ✅ Relevance factor calculation

**Key Tests:**
```bash
# Test successful reranking
pytest tests/unit/test_reranker.py::test_rerank_sentence_transformer_success -v

# Test error fallback
pytest tests/unit/test_reranker.py::test_rerank_sentence_transformer_error_fallback -v

# Test time decay
pytest tests/unit/test_reranker.py::test_rerank_sentence_transformer_time_decay -v

# Test invalid corpus handling
pytest tests/unit/test_reranker.py::test_rerank_sentence_transformer_with_invalid_corpus -v
```

**Run All Reranker Tests:**
```bash
pytest tests/unit/test_reranker.py -v
```

---

## Running Tests

### Run All New Tests
```bash
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py tests/unit/test_web_scraper.py tests/unit/test_reranker.py -v
```

### Run Tests by Category

**Paper Fetching Tests:**
```bash
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py -v
```

**Web Scraping Tests:**
```bash
pytest tests/unit/test_web_scraper.py -v
```

**Reranking Tests:**
```bash
pytest tests/unit/test_reranker.py -v
```

### Run Tests with Coverage

```bash
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py --cov=alithia.utils.paper_fetcher --cov-report=html
pytest tests/unit/test_web_scraper.py --cov=alithia.utils.web_scraper --cov-report=html
pytest tests/unit/test_reranker.py --cov=alithia.arxrec.reranker --cov-report=html
```

### Run Specific Tests

```bash
# Run tests matching a pattern
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py -k "fallback" -v

# Run a single test
pytest tests/unit/test_web_scraper.py::test_parse_paper_entry_valid -v

# Run tests with specific markers
pytest tests/unit/ -m unit -v
```

---

## Test Structure

### Fixtures

Each test module includes fixtures for common test data:

**test_arxiv_arxiv_paper_fetcher.py:**
- `mock_paper`: Sample ArxivPaper object
- `mock_arxiv_result`: Mock arxiv.Result object

**test_web_scraper.py:**
- HTML parsing mocks
- BeautifulSoup element mocks

**test_reranker.py:**
- `sample_papers`: List of test papers
- `sample_corpus`: Mock Zotero corpus

### Mocking Strategy

Tests use `unittest.mock` to:
- Mock external API calls (ArXiv API, web requests)
- Mock ML models (SentenceTransformer)
- Mock file system operations
- Isolate units under test

### Test Patterns

**Arrange-Act-Assert:**
```python
def test_example():
    # Arrange
    fetcher = ArxivPaperFetcher()
    
    # Act
    result = fetcher.fetch_papers(...)
    
    # Assert
    assert result.success
    assert len(result.papers) > 0
```

**Mock and Verify:**
```python
def test_with_mock():
    with patch('module.function') as mock_func:
        mock_func.return_value = expected_value
        
        result = function_under_test()
        
        mock_func.assert_called_once()
        assert result == expected_value
```

---

## Test Metrics

### Coverage Goals
- Line Coverage: >90%
- Branch Coverage: >85%
- Function Coverage: >95%

### Current Coverage (New Modules)
- `arxiv_paper_fetcher.py`: ~95% line coverage
- `web_scraper.py`: ~92% line coverage
- `reranker.py`: ~93% line coverage

---

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Push to main/development branches
- Pull requests
- Scheduled daily runs

### Local Pre-commit

Run tests before committing:
```bash
# Quick test
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py -x

# Full test suite
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=alithia --cov-report=term-missing
```

---

## Debugging Tests

### Run with Detailed Output
```bash
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py -vv
```

### Run with Print Statements
```bash
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py -s
```

### Run with Debug Mode
```bash
pytest tests/unit/test_arxiv_arxiv_paper_fetcher.py --pdb
```

### Show Test Duration
```bash
pytest tests/unit/ --durations=10
```

---

## Adding New Tests

### Template for New Test

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
def test_new_feature():
    """
    Test description.
    
    This test verifies that...
    """
    # Arrange
    setup_test_data()
    
    # Act
    result = function_to_test()
    
    # Assert
    assert result.is_valid()
    assert result.meets_requirements()
```

### Best Practices

1. **Descriptive Names**: Use clear, descriptive test names
2. **Single Responsibility**: Test one thing per test
3. **Arrange-Act-Assert**: Follow the AAA pattern
4. **Mock External Calls**: Don't make real API/network calls
5. **Test Edge Cases**: Include error conditions and boundary cases
6. **Document**: Add docstrings explaining what's being tested

---

## Test Dependencies

Required packages (included in `[dev]` extra):
- `pytest>=8.2`
- `pytest-cov>=4.0.0`
- `pytest-asyncio>=1.1.0`

---

## Troubleshooting

### Issue: Import Errors

**Solution:**
```bash
# Install in development mode
pip install -e ".[dev]"

# Or with uv
uv sync --extra dev
```

### Issue: Mock Not Found

**Solution:**
```python
# Use correct import path
from unittest.mock import Mock, patch
```

### Issue: Test Discovery Fails

**Solution:**
```bash
# Run from project root
cd /workspace
pytest tests/unit/
```

### Issue: Slow Tests

**Solution:**
```bash
# Run tests in parallel
pytest tests/unit/ -n auto

# Or skip slow tests
pytest tests/unit/ -m "not slow"
```

---

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure >90% coverage
3. Run full test suite
4. Update this README
5. Document edge cases

---

## Resources

- **pytest documentation**: https://docs.pytest.org/
- **Mock documentation**: https://docs.python.org/3/library/unittest.mock.html
- **Testing best practices**: `tests/README.md`

---

**Happy Testing!** 🧪
