# VS Code Test Explorer Configuration Guide

## Current Setup

### Configuration Files

1. **pytest.ini** - Controls command-line test execution
   - Enables: `-n auto` (parallel workers), test filtering, timeouts, markers
   - Used by: `pytest tests/` commands, CI/CD pipelines
   - Does NOT affect: VS Code Test Explorer

2. **.vscode/settings.json** - Controls VS Code Test Explorer
   - Minimal args: `["tests", "-m", "not slow"]` only
   - No xdist flags (parallelism disabled in VS Code)
   - No timeout, no duration tracking
   - Used by: VS Code Test Explorer UI only

3. **tests/conftest.py** - Session-level pytest configuration
   - Applies to: ALL test execution (CLI + VS Code)
   - Auto-groups integration tests into single worker (prevents race conditions)
   - Reorders tests (unit → integration → slow/e2e)
   - Initializes session-scoped fixtures

4. **tests/integration/conftest.py** - Integration test setup
   - Session-scoped fixture: Ingests test PDF once per session
   - Ensures Qdrant isolation between tests
   - Cleanup: Deletes collection after all tests complete

## Why This Configuration?

### The Problem We Solved

**Original Issue:** `/test_orchestrate` command showed 37 ERROR-level failures

**Root Cause:** Command was hardcoded to wrong directory (Powerpoint Agent Generator instead of RAGLite)

**VS Code Issue:** When xdist flags were added to VS Code settings, conflicts occurred:
- VS Code doesn't handle worker coordination well
- Multiple workers competing for shared Qdrant collection
- Result: 67 test errors instead of running properly

### The Solution

**Separation of Concerns:**
- pytest.ini: Handles ALL parallelism and optimization (CLI usage)
- .vscode/settings.json: Minimal, clean args (VS Code only)
- conftest.py hooks: Automatic per-mode configuration

**When you run tests:**
- `pytest tests/` → Uses pytest.ini + conftest hooks → Parallel execution
- VS Code Test Explorer → Uses .vscode/settings.json + conftest hooks → Sequential

## Configuration Details

### pytest.ini Settings (Command-Line)
```ini
addopts =
    -v
    --tb=line
    --strict-markers
    --strict-config
    -ra
    --timeout=900
    --durations=5
    --durations-min=2.0
    -m "not slow"                    # Skip slow tests by default
    -n auto                          # Parallel workers
    --dist loadfile                  # Smart worker distribution
```

**Key Points:**
- `-n auto`: Use all available CPU cores for parallelism
- `--dist loadfile`: Group tests by file for better load balancing
- `-m "not slow"`: Skip 34 tests marked with @pytest.mark.slow
- Result: ~5-10 minutes for typical development run

### .vscode/settings.json (VS Code Only)
```json
"python.testing.pytestArgs": [
  "tests",
  "-m",
  "not slow"
]
```

**Key Points:**
- Minimal args prevent conflicts
- pytest.ini is NOT explicitly loaded (VS Code ignores it)
- But pytest still auto-loads pytest.ini markers (@pytest.mark.slow)
- Integration tests still grouped automatically by conftest.py

### conftest.py Hooks (Applied Always)

1. **pytest_collection_modifyitems** (tests/conftest.py:159)
   - Automatically adds `@pytest.mark.xdist_group("embedding_model")` to ALL integration tests
   - Forces them into single worker (prevents Qdrant race conditions)
   - Reorders tests by type (unit → integration → slow)

2. **session_ingested_collection** (tests/integration/conftest.py:30)
   - Session-scoped: Runs ONCE per test session (not per test)
   - Ingests test PDF (10-page sample in local mode)
   - All tests share this collection (read-only)
   - Cleans up after all tests complete

## Execution Modes

### Local Development (VS Code)
```
Settings: .vscode/settings.json
PDF: 10-page sample (tests/fixtures/sample_financial_report.pdf)
Time: ~2-5 minutes
Workers: 1 (no parallelism)
Skips: All @pytest.mark.slow tests
```

### Command-Line (Fast)
```
Settings: pytest.ini
Command: pytest tests/
PDF: 10-page sample (default)
Time: ~5-10 minutes
Workers: 8-10 (parallel)
Skips: All @pytest.mark.slow tests
```

### Command-Line (Full/CI)
```
Settings: pytest.ini
Command: TEST_USE_FULL_PDF=true pytest tests/
PDF: 160-page full (docs/sample pdf/2025-08 Performance Review...)
Time: ~30-50 minutes
Workers: 8-10 (parallel)
Runs: ALL tests including @pytest.mark.slow
```

## Common Issues and Fixes

### Issue: VS Code shows "Error collecting test"
**Cause:** Test PDF missing or Qdrant not running
**Fix:**
1. Verify PDF exists: `tests/fixtures/sample_financial_report.pdf`
2. Check Qdrant running: `docker-compose ps`
3. See conftest.py line 68 - if PDF missing, tests are skipped

### Issue: VS Code takes 3+ minutes per test
**Cause:** Session fixture is re-running (PDF re-ingesting each test)
**Fix:**
1. Close and reopen VS Code
2. Run "Run All Tests" instead of individual tests
3. Check conftest.py line 31 - fixture scope should be "session"

### Issue: Too many errors in VS Code
**Cause:** Multiple workers competing for Qdrant (xdist flags present)
**Fix:**
1. Ensure .vscode/settings.json has NO `-n`, `--dist`, `--timeout` flags
2. Only args should be: `["tests", "-m", "not slow"]`
3. Reload VS Code window: Cmd+Shift+P → "Reload Window"

### Issue: Tests fail with "Collection doesn't exist"
**Cause:** Integration tests ran without session fixture initializing first
**Fix:**
1. Run all tests together (not individual tests)
2. vs Code caches state - reload: Cmd+Shift+P → "Reload Window"
3. Check Qdrant is running: `docker-compose up -d`

## How to Run Tests

### VS Code Test Explorer (Recommended for Development)
1. Open Test Explorer: Cmd+Shift+P → "Test: Focus on Test Explorer"
2. Click "Run All" button (not individual test)
3. Or: Open any test file and click "Run Test" above test function
4. Watch output in VS Code "Terminal" tab

**Why "Run All" instead of individual?**
- Session fixture runs once for all tests (fast)
- Running individual tests ingests PDF multiple times (slow)

### Command Line (Recommended for CI/Pre-Push)
```bash
# Fast development run (5-10 min)
pytest tests/

# With test details
pytest tests/ -v

# Show slowest tests
pytest tests/ --durations=10

# Full CI run with 160-page PDF (30-50 min)
TEST_USE_FULL_PDF=true pytest tests/

# Unit tests only (~2 min)
pytest tests/unit/

# Integration tests only (~5 min)
pytest tests/integration/ -m "not slow"
```

### Command Line (Custom Options)
```bash
# Sequential execution (for debugging)
pytest tests/ -n 0

# Specific number of workers
pytest tests/ -n 4

# Include slow tests
pytest tests/ -m ""

# Stop on first failure
pytest tests/ -x

# Show print statements
pytest tests/ -s

# Show test names as they run
pytest tests/ -v
```

## Design Rationale

### Why Separate Configuration?

**Command-Line (pytest.ini):**
- Can use all CPU cores for speed
- Xdist worker coordination works well on CI
- Full parallelism: 5-10 minutes
- Intended for: Pre-push validation, CI/CD

**VS Code (.vscode/settings.json):**
- Sequential execution is stable
- No worker coordination issues
- Better debugging (stop at breakpoints)
- Intended for: Development iteration, exploration

**Automatic Grouping (conftest.py):**
- Integration tests forced into single worker (prevents Qdrant race conditions)
- Works in BOTH modes (CLI + VS Code)
- Session fixture shared across tests (fast)
- No configuration needed - automatic

### Why Not Let pytest.ini Apply Everywhere?

**Problem:** pytest.ini settings in VS Code cause issues:
- Xdist worker confusion in IDE environment
- Multiple workers compete for Qdrant collection
- Timeout settings interfere with debugging
- Result: Lots of errors instead of clean runs

**Solution:** Use minimal .vscode/settings.json, let conftest.py handle the rest:
- Minimal → No conflicts
- Conftest hooks apply automatically (both modes)
- Clean, predictable behavior
- Easy to debug: Just look at conftest.py

## Testing Strategy

### Before Committing
```bash
# 1. Run fast tests locally (5-10 min)
pytest tests/

# 2. Check coverage
pytest tests/ --cov=raglite --cov-report=term-missing

# 3. Fix any failures
# (repeat until all pass)
```

### Before Pushing
```bash
# 1. Run full test suite (30-50 min)
TEST_USE_FULL_PDF=true pytest tests/

# 2. Run linting
ruff check raglite tests

# 3. Run type checking
mypy raglite --strict

# 4. Push if all pass
git push
```

### Development Workflow
```
1. Open VS Code
2. Edit code
3. Click "Run Test" on affected test
4. Fix failures
5. Repeat 2-4 until passing
6. Run full `pytest tests/` before commit
```

## Key Takeaway

✅ **VS Code Test Explorer WILL work correctly if:**
- .vscode/settings.json has ONLY: `["tests", "-m", "not slow"]`
- pytest.ini exists but is NOT referenced in VS Code
- conftest.py auto-groups integration tests
- Test PDF exists at `tests/fixtures/sample_financial_report.pdf`
- Qdrant running: `docker-compose up -d`

❌ **VS Code Test Explorer WILL fail if:**
- xdist flags (`-n`, `--dist`, `--timeout`) added to VS Code settings
- Multiple workers try to access shared Qdrant collection
- Test PDF is missing
- Qdrant is not running

---

**Last Updated:** 2025-10-28
**Configuration Version:** 1.0
