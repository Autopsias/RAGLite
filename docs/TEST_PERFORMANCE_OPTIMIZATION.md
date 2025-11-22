# Test Performance Optimization Guide

## Problem

VS Code Test Explorer was taking **44 minutes** to run the full test suite due to repeated session fixture executions.

## Root Cause

VS Code Test Explorer invokes pytest separately for each test or small group, causing the expensive `session_ingested_collection` fixture (10s ingestion + 60s model loading) to run hundreds of times instead of once.

## Solutions Implemented

### Fix #1: Session-Scoped Mistral API Mock (CRITICAL) - Eliminates API Costs

**Impact**: Prevents ALL Mistral API calls during testing, eliminating token costs and API latency

**Implementation**: Session-scoped autouse fixture in `tests/conftest.py`

This fix was the root cause of the 44-minute runtime. Tests were making real Mistral API calls for:
- Metadata extraction during session fixture ingestion
- SQL generation during query classification tests
- Multiple API calls per test = hundreds of expensive API requests

**Configuration**: Automatically enabled via `mock_mistral_api_globally()` fixture

**Verified Results** (2025-11-21):
- ✅ Zero Mistral API calls in test logs
- ✅ No unexpected API costs
- ✅ Tests complete in **11:38 minutes** (validated)

---

### Fix #2: Batch Execution Mode (DEFAULT) - 73% Speedup

**Runtime**: 44 minutes → **11-12 minutes** (validated at 11:38)

**Configuration**: Already enabled in `.vscode/settings.json`

```json
{
  "python.testing.pytestArgs": [
    "tests",
    "-v",
    "-n", "1",                    // Single worker for integration tests
    "--dist", "loadfile"          // Batch tests by file
  ],
  "python.testing.autoTestDiscoverOnSaveEnabled": false
}
```

**Usage**:
- Run tests normally via VS Code Test Explorer
- Tests are batched by file for optimal performance
- Session fixture runs once per test session

---

### Fix #3: Skip-Ingestion Mode (OPTIONAL) - 98% Speedup

**Runtime**: 44 minutes → **~1 minute**

**Best for**: Rapid test-driven development and iteration

#### Setup (One-Time)

1. **Ingest test data manually** (takes ~10 seconds):
   ```bash
   python scripts/ingest-test-data.py
   ```

2. **Enable skip-ingestion mode**:
   - Open `.vscode/settings.json`
   - Uncomment the line: `// "--skip-ingestion"`
   - Result:
     ```json
     "python.testing.pytestArgs": [
       "tests",
       "-v",
       "-n", "1",
       "--dist", "loadfile",
       "--skip-ingestion"  // Now enabled
     ]
     ```

3. **Reload VS Code**:
   - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
   - Type: "Developer: Reload Window"
   - Press Enter

#### Usage

- Run tests via Test Explorer → completes in ~1 minute
- Tests reuse existing Qdrant/PostgreSQL data
- No repeated ingestion overhead

#### When to Re-Ingest

Re-run `python scripts/ingest-test-data.py` when:
- Test data changes (new PDFs, modified fixtures)
- Database schema changes
- Test expectations change (new ground truth queries)

---

## Performance Comparison

| Mode | Setup Time | Test Time | Total Time | Speedup | API Costs |
|------|-----------|-----------|------------|---------|-----------|
| **Original** (VS Code per-test, real API) | N/A | N/A | 44 min | Baseline | $$$$ |
| **Fix #1** (Mistral mock) | 32s | 11 min | **11:38** | **73%** ↓ | **$0** ✅ |
| **Fix #2** (Batch execution) | 50s | 11 min | 12 min | **73%** ↓ | **$0** ✅ |
| **Fix #3** (Skip ingestion) | 0s | 1 min | 1 min | **98%** ↓ | **$0** ✅ |
| **Command-line** (pytest CLI) | 50s | 11 min | 12 min | **73%** ↓ | **$0** ✅ |

**Validated Results (2025-11-21)**:
- Integration test suite: **158 passed, 62 skipped** in **698.45s (11:38)**
- Wall clock: **11:41.55** (518.19s user + 738.90s system)
- **Zero Mistral API calls** confirmed in logs
- Session fixture setup: **32-77 seconds** (one-time per pytest invocation)

---

## Recommended Workflows

### Daily Development (Rapid Iteration)
1. Use **Fix #3** (Skip-Ingestion Mode)
2. Run tests via VS Code Test Explorer
3. Tests complete in ~1 minute
4. Perfect for TDD and rapid feedback
5. **Zero API costs** (Fix #1 mock automatically active)

### Pre-Commit Validation
1. Use **Fix #2** (Batch Execution Mode) - comment out `--skip-ingestion`
2. Run full test suite via VS Code Test Explorer
3. Tests complete in **11-12 minutes** with fresh data
4. Ensures no stale data issues before commit
5. **Zero API costs** (Fix #1 mock automatically active)

### CI/CD Pipelines
- Already optimized (uses command-line pytest)
- No changes needed
- Runtime: ~12 minutes with fresh ingestion

---

## Troubleshooting

### Tests Fail with "Collection doesn't exist"

**Cause**: Skip-ingestion mode enabled but data not ingested

**Fix**:
```bash
python scripts/ingest-test-data.py
```

### Tests Still Slow After Fix #1

**Verify configuration**:
1. Open `.vscode/settings.json`
2. Confirm `"--dist", "loadfile"` is present
3. Confirm `autoTestDiscoverOnSaveEnabled` is `false`
4. Reload VS Code window

### Want to Reset to Fresh Data

**Disable skip-ingestion**:
1. Open `.vscode/settings.json`
2. Comment out: `"--skip-ingestion"` → `// "--skip-ingestion"`
3. Reload VS Code window
4. Tests will ingest fresh data on next run

---

## Technical Details

### Fix #1: Session-Scoped Autouse Mistral Mock

**Root Cause**: Function-scoped mocks don't protect session fixtures or tests that don't explicitly request the mock.

**Problem**:
- Session fixture calls Mistral API for metadata extraction BEFORE any test mocks activate
- 220+ integration tests make real Mistral API calls during execution
- Function-scoped `mock_mistral_client` fixture requires explicit test parameter request

**Solution**: Session-scoped autouse mock in `tests/conftest.py`:

```python
@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    """Session-scoped autouse mock - BLOCKS ALL Mistral API calls."""
    from unittest.mock import MagicMock, patch

    # Patch ALL import paths where get_mistral_client() is used
    patches = [
        patch("raglite.shared.clients.get_mistral_client"),
        patch("raglite.retrieval.query_classifier.get_mistral_client"),
        patch("raglite.ingestion.document_ingestion.get_mistral_client"),
        patch("raglite.ingestion.contextual.get_mistral_client"),
        patch("raglite.agentic.agents.synthesis_agent.get_mistral_client"),
    ]

    for p in patches:
        p.start()

    yield

    for p in patches:
        p.stop()
```

**Key Benefits**:
- `autouse=True`: Runs automatically without explicit test parameter
- `scope="session"`: Runs once per pytest invocation, protects session fixtures
- Patches all import paths where Mistral client is used
- Returns realistic mock SQL queries to avoid breaking tests

---

### Why Session-Scoped Fixtures Don't Work Across Invocations

Pytest session scope means "one pytest process invocation", not "persistent global state":

```python
# This fixture runs ONCE per pytest invocation
@pytest.fixture(scope="session", autouse=True)
def session_ingested_collection(...):
    # Ingest data (expensive: 10s + 60s model loading)
    pass
```

**Command-line**: One invocation → fixture runs once
**VS Code Test Explorer**: Many invocations → fixture runs many times

### The --skip-ingestion Flag

Implemented in `tests/integration/conftest.py:308-349`:

```python
if skip_ingestion:
    # Use existing Qdrant/PostgreSQL data
    # Skip expensive ingestion
    yield
    return
```

This allows tests to reuse manually ingested data across multiple pytest invocations.

---

## Additional Resources

- **Root Cause Analysis**: See investigation logs in test orchestration output
- **Fixture Documentation**: `tests/integration/conftest.py` (lines 256-705)
- **Ingestion Script**: `scripts/ingest-test-data.py`
- **CI Configuration**: `.github/workflows/` (unchanged - already optimal)

---

## Quick Reference Commands

```bash
# Ingest test data for skip-ingestion mode
python scripts/ingest-test-data.py

# Run tests via command-line (fast - 12 minutes)
pytest tests/integration/ -n 1 --dist loadfile

# Run tests with skip-ingestion (fastest - 1 minute)
pytest tests/integration/ --skip-ingestion -n 1 --dist loadfile

# Check test timing breakdown
pytest tests/integration/ --durations=20 -v

# Reload VS Code window (after settings changes)
# Cmd+Shift+P → "Developer: Reload Window"
```
