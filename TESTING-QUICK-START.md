# Quick Test Commands Reference

## 🚀 Run Tests (Choose One)

### Fastest - Smoke Tests (~30 seconds)
```bash
pytest -m smoke
```
Critical paths only. Use on every commit.

### Fast - Default Suite (~5-10 minutes) ⭐ RECOMMENDED
```bash
pytest tests/
# Or explicitly:
pytest tests/ -m "not slow"
```
All unit + integration tests (excludes slow/obsolete).

### Complete - Full Suite (~30-40 minutes)
```bash
TEST_USE_FULL_PDF=true pytest tests/
```
Comprehensive with 160-page PDF (CI/CD mode).

### Debug - Sequential Execution (~10-15 minutes)
```bash
pytest tests/ -n 0 --tb=short
```
No parallelism. Use when debugging race conditions.

---

## 🎯 Run Specific Tests

```bash
# Single test file
pytest tests/unit/test_shared_config.py -v

# Single test class
pytest tests/unit/test_query_classifier.py::TestQueryClassifier -v

# Single test
pytest tests/unit/test_query_classifier.py::TestQueryClassifier::test_financial_vs_table_routing -v

# All tests matching pattern
pytest tests/unit/ -k "test_table" -v

# Integration tests only
pytest tests/integration/ -v

# Unit tests only
pytest tests/unit/ -v

# E2E tests only
pytest tests/e2e/ -v
```

---

## 📊 Analyze Performance

```bash
# Show slowest 10 tests
pytest tests/ --durations=10

# Show only tests slower than 5 seconds
pytest tests/ --durations=5 --durations-min=5.0

# Show test names as they run (good for debugging)
pytest tests/ -v --tb=line

# Full traceback for debugging
pytest tests/ -v --tb=short

# Very verbose (includes setup/teardown)
pytest tests/ -vv --tb=long
```

---

## 🔧 Troubleshooting

```bash
# Clear pytest cache and re-run
pytest tests/ --cache-clear

# Reset Qdrant and retry
docker-compose down -v && docker-compose up -d
pytest tests/ --cache-clear

# Run without parallel (if xdist issues)
pytest tests/ -n 0

# Show what tests will run (don't execute)
pytest tests/ --collect-only -q

# Run with custom worker count
pytest tests/ -n 4  # Use 4 workers instead of auto

# Skip slow tests (reduces from 30+ min to ~10 min)
pytest tests/ -m "not slow"
```

---

## 📈 Expected Results

| Command | Time | Tests | Notes |
|---------|------|-------|-------|
| `pytest -m smoke` | ~30s | Critical paths | Pre-commit |
| `pytest tests/` | ~5-10 min | 274 passed | Default, CI |
| `TEST_USE_FULL_PDF=true pytest tests/` | ~30-40 min | All + slow | Full validation |
| `pytest tests/ -n 0` | ~10-15 min | Sequential | Debugging |

---

## 🐛 Common Issues & Fixes

### Tests hanging or running slow
```bash
# Check for slow tests
pytest tests/ --durations=10

# Run without parallelism
pytest tests/ -n 0 --tb=short

# Show live output
pytest tests/ -s
```

### Rate limit errors (429 from Mistral API)
```bash
# Already fixed in pytest.ini - integration tests run in single worker
# If still occurring, reset and retry:
pytest tests/integration/ -n 0
```

### "No test PDF found"
```bash
# Check file exists
ls tests/fixtures/sample_financial_report.pdf

# Use full PDF mode (CI)
TEST_USE_FULL_PDF=true pytest tests/integration/
```

### Qdrant connection errors
```bash
# Verify Qdrant is running
docker-compose ps

# Restart Qdrant
docker-compose restart qdrant
docker-compose logs qdrant  # Check logs
```

---

## 📝 Continuous Integration

### Pre-commit (run locally)
```bash
pytest -m smoke --timeout=60
```

### Pre-push (run locally)
```bash
pytest tests/ -m "not slow" --timeout=900
```

### GitHub Actions (PR)
```bash
pytest tests/ -m "not slow" --timeout=900
```

### GitHub Actions (main - weekly)
```bash
TEST_USE_FULL_PDF=true pytest tests/ --timeout=2700
```

---

## 🎓 Learn More

See `docs/TESTING-OPTIMIZATION.md` for:
- Detailed bottleneck analysis
- Execution time breakdown
- Advanced configuration options
- Performance optimization strategies
- Maintenance guidelines
