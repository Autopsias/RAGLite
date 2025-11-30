# Quick Test Commands - Two-Mode System

**RAGLite uses a simple two-mode test system:**

## 🏃 LOCAL MODE (Default - VS Code & Command Line)

**What it does:**
- Uses 10-page sample PDF (~10-15s ingestion)
- Skips tests marked `@pytest.mark.slow`
- Target time: **5-8 minutes**

**How to run:**

### VS Code Test Explorer (Recommended)
1. Open Test Explorer (cmd+shift+T)
2. Click "Run Tests" on any folder/file
3. Automatically uses LOCAL mode

### Command Line
```bash
# Run all tests (default LOCAL mode)
pytest tests/ -v

# Run unit tests only (fastest - <2 min)
pytest tests/unit -v

# Run integration tests only (fast mode - 5-8 min)
pytest tests/integration -v
```

---

## 🔬 CI MODE (Comprehensive - CI/CD Pipeline)

**What it does:**
- Uses 160-page full PDF (~150s ingestion)
- Runs ALL tests including slow ones
- Target time: **30-50 minutes**

**How to run:**

### Local Testing (CI-equivalent)
```bash
# Set environment variable to enable CI mode
TEST_USE_FULL_PDF=true pytest tests/ -v -m ""

# Or run specific test suite in CI mode
TEST_USE_FULL_PDF=true pytest tests/integration -v -m ""
```

### CI/CD Pipeline
Automatically runs in CI mode when triggered by:
- Push to main/develop/story/epic branches
- Pull requests to main/develop
- Manual workflow dispatch

---

## Unit Tests Only (Ultra-Fast)

```bash
# Run unit tests only (< 2 min)
pytest tests/unit -v

# With parallel execution (< 1 min on multi-core)
pytest tests/unit -n auto -v
```

---

## Troubleshooting

### See what tests will run
```bash
# List all tests
pytest --collect-only -q

# List only LOCAL mode tests (excludes slow)
pytest --collect-only -q -m "not slow"
```

### Run specific tests
```bash
# Run tests matching keyword
pytest -k "retrieval" -v

# Run specific file
pytest tests/unit/test_retrieval.py -v

# Run specific test function
pytest tests/unit/test_retrieval.py::test_search_documents -v
```

### Debug failing tests
```bash
# Stop on first failure
pytest tests/unit -x -v

# Show print statements
pytest tests/unit -s -v

# Time individual tests
pytest tests/unit --durations=10 -v
```

---

## Performance Summary

| Mode | Command | Time | PDF Used | Tests Run |
|------|---------|------|----------|-----------|
| **LOCAL** | `pytest tests/` | 5-8 min | 10-page sample | All except `@pytest.mark.slow` |
| **LOCAL (unit only)** | `pytest tests/unit` | <2 min | N/A | 130 unit tests |
| **CI** | `TEST_USE_FULL_PDF=true pytest tests/` | 30-50 min | 160-page full | All 207 tests |

---

## What Changed?

**Previous system:**
- Complex multi-tier marker filtering
- Multiple test configurations
- Confusing performance targets

**New simplified system:**
- **Two modes only**: LOCAL (fast) and CI (comprehensive)
- Single environment variable switch: `TEST_USE_FULL_PDF`
- Clear performance expectations:
  - LOCAL: 5-8 minutes for fast iteration
  - CI: 30-50 minutes for comprehensive validation

---

## VS Code Test Explorer

After reloading VS Code (`cmd+shift+P` → "Reload Window"):

1. Open Test Explorer (`cmd+shift+T`)
2. You should see:
   - **tests/unit/** (130 tests) - Ultra-fast unit tests
   - **tests/integration/** (77 tests) - Real integration tests
3. Click "Run" on any folder/file - automatically uses LOCAL mode
4. All tests share ingested PDF data (session fixture pattern)

**Expected times:**
- Unit tests folder: **<2 minutes**
- Integration tests folder: **5-8 minutes**
- All tests: **5-8 minutes** (LOCAL mode)
