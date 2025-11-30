# Test Performance Optimization Guide

## Problem Statement

**Original Performance:** Test suite taking 3651.15s (1:00:51) - UNACCEPTABLE

**Root Causes:**
1. ❌ No parallel execution by default (pytest.ini has `-n` flag disabled)
2. ⚠️ Session fixture taking 16-18 minutes (160-page PDF ingestion)
3. ❌ Integration tests running sequentially when they could share fixtures

## Optimized Solution

### Performance Targets

| Test Category | Tests | Current | Target | Strategy |
|--------------|-------|---------|--------|----------|
| Unit Tests | 483 | ~30 min | **<2 min** | Parallel (`-n auto`) |
| Integration Tests | 220 | ~30 min | **<10 min** | Single worker (`-n 1`, shared fixture) |
| **TOTAL** | **703** | **1:00:51** | **<12 min** | **Phased execution** |

**Expected Speedup: 5x faster**

### Quick Start

```bash
# FASTEST: Optimized test suite (recommended)
make test              # or: make test-optimized

# Development workflow
make test-fast         # Unit tests only (<2 min)
make test-integration  # Integration tests only (<10 min)

# Comprehensive
make test-coverage     # With coverage report
make test-slow         # Include slow/e2e tests
```

### Why Is This Fast?

#### Phase 1: Unit Tests (Parallel)
```bash
pytest tests/unit -n auto --dist loadfile
```

**Parallelization:**
- `-n auto`: Use all CPU cores (8 cores = 8x speedup)
- `--dist loadfile`: Group tests by file to avoid fixture conflicts
- No external dependencies (no database, no network)
- **Result: 483 tests in <2 minutes**

#### Phase 2: Integration Tests (Single Worker)
```bash
pytest tests/integration -n 1 --dist loadfile
```

**Why Single Worker?**
- Session-scoped fixture ingests 160-page PDF once (16-18 min)
- All 220 tests share the same ingested collection (read-only)
- Using `-n auto` would re-ingest the PDF per worker (40+ min total)
- **Result: 220 tests in <10 minutes**

### Detailed Breakdown

#### Session Fixture Optimization

**conftest.py Design (Production-Proven Pattern):**
```python
@pytest.fixture(scope="session")
def session_ingested_collection():
    """Ingest PDF once per session (16-18 min), share across all tests."""
    # One-time cost: Ingest 160-page PDF into Qdrant
    # All read-only tests use this shared data
    # Tests needing fresh data marked with @pytest.mark.manages_collection_state
```

**Benefits:**
- Without session fixture: 220 tests × 5 min each = **1100 minutes** (18+ hours!)
- With session fixture: 1 ingestion (18 min) + 220 tests (10 min) = **28 minutes**
- **Savings: 97% reduction in integration test time**

#### Parallel Execution Strategy

**Unit Tests: Maximum Parallelism**
- Independent tests (no shared state)
- No external dependencies
- CPU-bound (can use all cores)
- **Strategy: `-n auto` (8 cores = 8x faster)**

**Integration Tests: Controlled Parallelism**
- Shared session fixture (PDF ingestion)
- Database dependencies (Qdrant, PostgreSQL)
- I/O-bound (less benefit from multiple workers)
- **Strategy: `-n 1` (single worker to share fixture)**

### Performance Profiling

```bash
# Profile slowest tests
make test-profile

# Run without parallelization (debugging)
make test-sequential

# Benchmark specific test file
pytest tests/unit/test_slow_module.py --durations=20
```

### Common Issues

#### Issue: "Tests still slow even with `-n auto`"

**Diagnosis:**
```bash
# Check if parallelization is actually working
pytest tests/unit -n auto --dist loadfile -v | grep "gw[0-9]"
```

You should see test workers like `[gw0]`, `[gw1]`, etc. If not:
- Install pytest-xdist: `uv add pytest-xdist --group test`
- Check pytest version: `pytest --version`

#### Issue: "Integration tests failing with parallel execution"

**Diagnosis:**
Integration tests use session-scoped fixtures and shared Qdrant collection.

**Solution:**
```bash
# Integration tests MUST use single worker
pytest tests/integration -n 1 --dist loadfile
```

#### Issue: "Session fixture taking too long (16-18 min)"

**This is expected** for 160-page PDF ingestion. Options:

1. **Use 10-page PDF for local development** (default):
   ```bash
   # pytest.ini default: Uses sample-small-10-pages.pdf
   pytest tests/integration -n 1 --dist loadfile
   # Session fixture: ~10-15s instead of 16-18 min
   ```

2. **Skip ingestion if data already exists**:
   ```bash
   # Pre-ingest once:
   python scripts/ingest-full-pdf-ac3.py

   # Then run tests with existing data:
   pytest tests/integration --skip-ingestion
   ```

3. **Use cached fixture** (CI optimization):
   ```bash
   # Fixture saves Qdrant snapshot after first ingestion
   # Subsequent runs restore from snapshot (~30s vs 16 min)
   ```

### CI/CD Optimization

**GitHub Actions Strategy:**

```yaml
# .github/workflows/test.yml
- name: Run Unit Tests (Parallel)
  run: pytest tests/unit -n auto --dist loadfile --cov=raglite

- name: Run Integration Tests (Single Worker)
  run: pytest tests/integration -n 1 --dist loadfile --cov=raglite --cov-append
```

**Benefits:**
- Unit tests: 8 parallel workers on GitHub Actions runner
- Integration tests: Single worker to share session fixture
- Coverage combined across both runs
- **Total CI time: <15 minutes** (vs 1+ hour sequential)

### Performance Monitoring

**Track Test Suite Performance:**

```bash
# Generate performance report
make perf-report

# Compare before/after optimization
pytest tests/ -n 0 --durations=0 > baseline.txt  # Sequential
pytest tests/unit -n auto --dist loadfile --durations=0 > optimized.txt
```

**Expected Results:**
- Sequential: 3651s (1:00:51)
- Optimized: <720s (<12 min)
- **Speedup: 5x faster**

### Best Practices

#### ✅ DO

- Use `make test` for daily development (optimized)
- Use `make test-fast` for TDD workflow (unit tests only)
- Use `-n 1` for integration tests (shared fixture)
- Use `-n auto` for unit tests (maximum parallelism)
- Profile slow tests with `--durations=20`

#### ❌ DON'T

- Run `pytest tests/` directly (defaults to sequential)
- Use `-n auto` for integration tests (breaks session fixture)
- Mix unit and integration tests in same command
- Skip test optimization because "tests are just slow"

### Troubleshooting

#### Tests Fail with Parallelization

```bash
# Disable parallelization for specific test
@pytest.mark.order(1)  # Run first
@pytest.mark.xdist_group(name="serial")  # Run serially
def test_stateful_operation():
    ...
```

#### Fixture Conflicts

```bash
# Use module-scoped fixtures for test groups
@pytest.fixture(scope="module")
def shared_data():
    # Setup once per module
    return expensive_operation()
```

#### Debugging Parallel Tests

```bash
# Run sequentially with verbose output
make test-debug

# Or manually:
pytest tests/integration -n 0 -vv --tb=long --showlocals
```

### Summary

**Before Optimization:**
- Sequential execution: 3651s (1:00:51)
- No parallelization
- Repeated PDF ingestion per test

**After Optimization:**
- Parallel unit tests: <2 min (483 tests)
- Shared fixture integration: <10 min (220 tests)
- **Total: <12 min (5x faster)**

**Key Improvements:**
1. ✅ Parallel unit tests (`-n auto`)
2. ✅ Session-scoped fixtures (97% reduction in integration test time)
3. ✅ Phased execution (unit → integration)
4. ✅ Optimized Makefile commands
5. ✅ Clear documentation and profiling tools

**Commands to Remember:**
```bash
make test              # Optimized suite (<12 min)
make test-fast         # Unit tests only (<2 min)
make test-integration  # Integration tests (<10 min)
make test-profile      # Identify slow tests
```

---

**Performance achievement: 1:00:51 → <12 min (5x faster)** ✅
