# ArXrec Optimization Deployment Checklist

## Pre-Deployment

### Code Review
- [ ] Review all new modules
  - [ ] `alithia/utils/paper_fetcher.py`
  - [ ] `alithia/utils/web_scraper.py`
- [ ] Review modified modules
  - [ ] `alithia/arxrec/nodes.py`
  - [ ] `alithia/arxrec/reranker.py`
  - [ ] `alithia/utils/arxiv_paper_utils.py`
- [ ] Review test files
  - [ ] `tests/unit/test_paper_fetcher.py`
  - [ ] `tests/unit/test_web_scraper.py`
  - [ ] `tests/unit/test_reranker.py`

### Dependency Check
- [ ] Update `pyproject.toml` verified
- [ ] Install new dependencies:
  ```bash
  pip install beautifulsoup4>=4.12.0 lxml>=5.0.0
  # or
  uv sync
  ```
- [ ] Verify all imports work
  ```bash
  python -c "from alithia.utils.paper_fetcher import fetch_arxiv_papers"
  python -c "from alithia.utils.web_scraper import ArxivWebScraper"
  ```

### Testing
- [ ] Run all new unit tests
  ```bash
  pytest tests/unit/test_paper_fetcher.py -v
  pytest tests/unit/test_web_scraper.py -v
  pytest tests/unit/test_reranker.py -v
  ```
- [ ] Run full test suite
  ```bash
  pytest tests/unit/ -v
  ```
- [ ] Check test coverage
  ```bash
  pytest tests/unit/ --cov=alithia --cov-report=html
  ```
- [ ] Verify syntax
  ```bash
  python -m py_compile alithia/utils/paper_fetcher.py
  python -m py_compile alithia/utils/web_scraper.py
  ```

### Documentation Review
- [ ] Read `ARXREC_OPTIMIZATION.md`
- [ ] Read `QUICK_START_OPTIMIZATION.md`
- [ ] Read `OPTIMIZATION_SUMMARY.md`
- [ ] Read `tests/unit/README_NEW_TESTS.md`

---

## Deployment

### Staging Environment

#### Step 1: Deploy Code
- [ ] Checkout/pull latest code
- [ ] Install dependencies
  ```bash
  pip install -e ".[dev]"
  # or
  uv sync --extra dev
  ```

#### Step 2: Configuration
- [ ] Update config file (optional):
  ```json
  {
    "arxrec": {
      "query": "cs.AI+cs.CV+cs.LG+cs.CL",
      "max_papers": 50,
      "max_retries": 3,
      "enable_web_fallback": true
    }
  }
  ```
- [ ] Verify configuration loads correctly

#### Step 3: Test Run
- [ ] Run in debug mode (limits to 5 papers):
  ```bash
  python -m alithia.run arxrec_agent --config config.json --debug
  ```
- [ ] Verify output and logs
- [ ] Check which strategy was used
- [ ] Verify paper count and quality

#### Step 4: Full Test
- [ ] Run without debug mode:
  ```bash
  python -m alithia.run arxrec_agent --config config.json
  ```
- [ ] Monitor logs for errors
- [ ] Check performance metrics
- [ ] Verify email delivery (if configured)

#### Step 5: Staging Validation
- [ ] Papers retrieved successfully
- [ ] Reranking completed without errors
- [ ] Performance within expected range
- [ ] No unexpected errors in logs
- [ ] Email formatting correct (if applicable)

---

### Production Environment

#### Step 1: Backup
- [ ] Backup current production code
- [ ] Backup current configuration
- [ ] Document current performance baseline

#### Step 2: Deploy
- [ ] Deploy new code to production
- [ ] Install dependencies
- [ ] Update configuration (if needed)

#### Step 3: Gradual Rollout
- [ ] Enable for single user/test group first
- [ ] Monitor for 24 hours
- [ ] Check logs for errors
- [ ] Verify performance metrics

#### Step 4: Full Rollout
- [ ] Enable for all users
- [ ] Monitor closely for first week
- [ ] Track performance metrics:
  - Papers retrieved per day
  - API success rate
  - Reranking time
  - Error rate
  - Strategy usage (API/RSS/Web)

#### Step 5: Post-Deployment Monitoring
- [ ] Set up alerts for failures
- [ ] Monitor API rate limits
- [ ] Track web scraping success rate
- [ ] Monitor performance metrics
- [ ] Collect user feedback

---

## Verification Tests

### Functional Tests

#### Test 1: API Search
```bash
# Should use API search successfully
python -c "
from alithia.utils.paper_fetcher import fetch_arxiv_papers
papers = fetch_arxiv_papers('cs.AI', '202312230000', '202312232359', max_results=10)
print(f'✓ Retrieved {len(papers)} papers')
"
```

#### Test 2: RSS Fallback
```bash
# Test RSS fallback (simulate API failure)
python -c "
from alithia.utils.paper_fetcher import EnhancedPaperFetcher
from unittest.mock import patch

fetcher = EnhancedPaperFetcher()
# Mock API to fail, RSS should succeed
with patch.object(fetcher, '_fetch_with_api_search') as mock:
    mock.return_value.success = False
    result = fetcher.fetch_papers('cs.AI')
    print(f'✓ Fallback working: {result.strategy_used}')
"
```

#### Test 3: Web Scraper
```bash
# Test web scraper directly
python -c "
from alithia.utils.web_scraper import ArxivWebScraper
scraper = ArxivWebScraper()
papers = scraper.scrape_arxiv_search('cs.AI', max_results=5)
print(f'✓ Scraped {len(papers)} papers')
"
```

#### Test 4: Reranker
```bash
# Test optimized reranker
python -c "
from alithia.arxrec.reranker import PaperReranker
from alithia.models import ArxivPaper

papers = [ArxivPaper(
    title='Test', summary='ML paper', authors=['A'],
    arxiv_id='2312.00001', pdf_url='url'
)]
corpus = [{'data': {'abstractNote': 'ML paper', 'dateAdded': '2023-12-01T10:00:00Z'}}]

reranker = PaperReranker(papers, corpus)
scored = reranker.rerank_sentence_transformer()
print(f'✓ Ranked {len(scored)} papers')
"
```

---

## Monitoring

### Metrics to Track

#### Performance Metrics
- [ ] Papers retrieved per day
- [ ] Average retrieval time
- [ ] Reranking time
- [ ] Total workflow time

#### Strategy Usage
- [ ] API search success rate
- [ ] RSS feed usage rate
- [ ] Web scraper usage rate
- [ ] Retry counts per strategy

#### Error Metrics
- [ ] Total errors per day
- [ ] Error types breakdown
- [ ] Failed strategy counts
- [ ] Recovery success rate

#### Quality Metrics
- [ ] Papers with valid metadata
- [ ] Reranking score distribution
- [ ] User satisfaction (if tracked)

### Alerting

Set up alerts for:
- [ ] API success rate < 90%
- [ ] Total retrieval failures > 5 per day
- [ ] Reranking errors > 3 per day
- [ ] Web scraper blocked
- [ ] Average retrieval time > 60s

---

## Rollback Procedure

If critical issues occur:

### Immediate Actions
1. [ ] Disable web fallback:
   ```python
   enable_web_fallback=False
   ```
2. [ ] Monitor if issues persist
3. [ ] Check logs for root cause

### Partial Rollback
1. [ ] Revert to old fetcher in nodes.py:
   ```python
   from alithia.utils.arxiv_paper_utils import get_arxiv_papers_search
   papers = get_arxiv_papers_search(...)
   ```
2. [ ] Keep other optimizations
3. [ ] Test thoroughly

### Full Rollback
1. [ ] Revert all changes:
   ```bash
   git revert <commit-hash>
   ```
2. [ ] Reinstall dependencies
3. [ ] Test old version
4. [ ] Document issues for debugging

---

## Success Criteria

### Must Have
- [ ] Papers retrieved successfully (>95% success rate)
- [ ] No critical errors in production
- [ ] Performance within acceptable range
- [ ] Backward compatibility maintained

### Should Have
- [ ] 10%+ increase in papers retrieved
- [ ] 30%+ reduction in reranking time
- [ ] <1% error rate
- [ ] Automatic error recovery working

### Nice to Have
- [ ] Web scraper used < 5% of time (API/RSS working well)
- [ ] User feedback positive
- [ ] Monitoring dashboard set up
- [ ] Documentation complete

---

## Post-Deployment

### Week 1
- [ ] Daily monitoring of all metrics
- [ ] Review logs for errors
- [ ] Check user feedback
- [ ] Document any issues

### Week 2-4
- [ ] Weekly metric reviews
- [ ] Performance optimization if needed
- [ ] Update documentation based on learnings
- [ ] Plan next improvements

### Month 2+
- [ ] Monthly metric reviews
- [ ] Consider additional features
- [ ] Plan future optimizations
- [ ] Update roadmap

---

## Sign-off

### Technical Lead
- [ ] Code reviewed and approved
- [ ] Tests passing
- [ ] Documentation complete
- Date: ____________ Signature: ____________

### DevOps
- [ ] Deployment plan reviewed
- [ ] Monitoring set up
- [ ] Rollback plan tested
- Date: ____________ Signature: ____________

### Product Owner
- [ ] Features validated
- [ ] Success criteria defined
- [ ] User impact assessed
- Date: ____________ Signature: ____________

---

## Notes

Record any issues, observations, or important decisions here:

```
[Date] [Your Name]
- Note 1
- Note 2
```

---

## Contact Information

- **Technical Lead**: [Name] [Email]
- **DevOps**: [Name] [Email]
- **On-Call**: [Name] [Phone]
- **Emergency**: [Process/Contact]

---

*Checklist Version: 1.0*
*Last Updated: December 23, 2025*
