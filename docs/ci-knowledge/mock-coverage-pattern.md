# CI Knowledge: Lazy Import Mock Coverage Pattern

## Failure Pattern: Mock Coverage Gaps from Lazy Imports

**First Observed:** 2025-01-12 (Strategic CI analysis)
**Frequency:** 80% of CI failures are reactive patching (systemic pattern)
**Strategic Impact:** 17+ modules import get_mistral_client, only 5 patched (incomplete coverage)
**Root Cause Category:** Structural mock pattern (session fixtures + lazy imports)

---

## Problem Statement

Lazy imports inside function bodies bypass session-scoped mock fixtures, allowing external API calls to execute during unit tests. This causes:

1. **Test Timeouts** - API calls hang when network unavailable
2. **Unpredictable Failures** - Timing depends on API availability
3. **80% Reactive Fix Rate** - Each new module requires manual patch addition
4. **Test Reliability** - Same test fails/passes based on external factors

### Example: The Coverage Gap

```python
# raglite/retrieval/search/enrichment.py
def enrich_result(query: str):
    # LAZY IMPORT - executed at test runtime
    from raglite.shared.clients import get_mistral_client
    client = get_mistral_client()  # <-- This bypasses mock fixture!
    return client.enrich(query)

# Test fixture patches location:
@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    with patch("raglite.retrieval.search.get_mistral_client"):
        # ❌ Missing: patch("raglite.retrieval.search.enrichment.get_mistral_client")
        # Session fixture runs BEFORE enrichment.py is imported
        # When enrich_result() calls get_mistral_client later, it gets REAL module
        yield

# Result: Test timeout when real API is called
```

---

## Root Cause Analysis (Five Whys)

1. **Why do tests timeout?** → External API calls execute (Mistral, Claude)
2. **Why aren't they mocked?** → Lazy imports bypass session-scoped patches
3. **Why use lazy imports?** → Avoid circular imports, defer loading until needed
4. **Why patches miss locations?** → 17+ modules, only 5 manually patched (incomplete)
5. **Why no structural prevention?** → No validation that all locations are patched

---

## Module Inventory

All modules that import `get_mistral_client`:

```
raglite/
├── mcp/
│   ├── tools/
│   │   ├── __init__.py (1 import)
│   │   ├── model_selector.py (2 imports)
│   │   └── forecast_helpers.py (3 imports)
│   └── __init__.py (1 import)
├── retrieval/
│   ├── search/
│   │   ├── enrichment.py (1 import) <- GAP
│   │   └── ranking.py (1 import) <- GAP
│   └── __init__.py (1 import)
├── insights/
│   ├── anomaly_detection.py (1 import) <- GAP
│   └── patterns.py (1 import) <- GAP
├── forecasting/
│   ├── ensemble.py (1 import) <- GAP
│   └── utils.py (1 import) <- GAP
└── shared/
    └── clients.py (0 imports - defines get_mistral_client)

Total: 17+ locations
Patched: 5 known locations (session fixture)
Unpatched: 12+ locations (coverage gaps)
```

---

## Solution: Structural Validation

### Part 1: Validation Script

**Location:** `scripts/validate-mock-coverage.py`

**Purpose:** Automated detection of unpatched import locations

**How it works:**
1. Scans all `raglite/` modules for `get_mistral_client` imports
2. Extracts patches from `tests/fixtures/mock_clients.py`
3. Identifies gaps (imports without patches)
4. Fails with actionable error messages

**Usage:**

```bash
# Quick validation (binary pass/fail)
python scripts/validate-mock-coverage.py

# Detailed report (shows all modules and gaps)
python scripts/validate-mock-coverage.py --verbose

# CI enforcement (strict mode, blocks on gaps)
python scripts/validate-mock-coverage.py --strict
```

**Output (Pass):**

```
================================================================================
✅ Mock coverage validation PASSED
================================================================================
  - 17 module(s) import get_mistral_client
  - 17 location(s) patched in mock fixtures
  - 0 gaps (100% coverage)
```

**Output (Fail):**

```
================================================================================
ERROR: Mock coverage gaps detected!
================================================================================

Found 3 module(s) importing get_mistral_client without mock coverage:

  ❌ raglite.retrieval.search.enrichment.get_mistral_client
  ❌ raglite.mcp.tools.model_selector.get_mistral_client
  ❌ raglite.insights.anomaly_detection.get_mistral_client

================================================================================
Fix: Add patches to tests/fixtures/mock_clients.py
================================================================================

In mock_mistral_api_globally fixture, add:
        patch("raglite.retrieval.search.enrichment.get_mistral_client") as mock_enrichment,
        patch("raglite.mcp.tools.model_selector.get_mistral_client") as mock_selector,
        patch("raglite.insights.anomaly_detection.get_mistral_client") as mock_anomaly,

Then assign:
        mock_enrichment.return_value = mock_client_instance
        mock_selector.return_value = mock_client_instance
        mock_anomaly.return_value = mock_client_instance
```

### Part 2: Fixture Pattern

**Location:** `tests/fixtures/mock_clients.py`

**Current State (Incomplete):**

```python
@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    """Mock Mistral API globally for unit tests.

    Currently patches 5 known locations only (incomplete).
    See scripts/validate-mock-coverage.py for gaps.
    """
    with (
        patch("raglite.mcp.tools.get_mistral_client") as mock1,
        # ... 4 more patches (incomplete list)
    ):
        mock_client = AsyncMock()
        mock_client.enrich = AsyncMock(return_value="mocked")
        for mock in [mock1, ...]:
            mock.return_value = mock_client
        yield
```

**Target State (Complete Coverage):**

```python
@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    """Mock Mistral API globally for all 17+ import locations.

    Validates with: python scripts/validate-mock-coverage.py
    """
    with (
        # MCP tools
        patch("raglite.mcp.tools.get_mistral_client") as mock1,
        patch("raglite.mcp.tools.model_selector.get_mistral_client") as mock2,
        patch("raglite.mcp.tools.forecast_helpers.get_mistral_client") as mock3,
        # Retrieval search
        patch("raglite.retrieval.search.enrichment.get_mistral_client") as mock4,
        patch("raglite.retrieval.search.ranking.get_mistral_client") as mock5,
        # Insights
        patch("raglite.insights.anomaly_detection.get_mistral_client") as mock6,
        patch("raglite.insights.patterns.get_mistral_client") as mock7,
        # Forecasting
        patch("raglite.forecasting.ensemble.get_mistral_client") as mock8,
        patch("raglite.forecasting.utils.get_mistral_client") as mock9,
        # ... additional locations
    ):
        mock_client = AsyncMock()
        mock_client.enrich = AsyncMock(return_value="mocked")
        mock_client.select = AsyncMock(return_value="model_1")

        # Apply to all patches
        for mock in [mock1, mock2, mock3, mock4, mock5, mock6, mock7, mock8, mock9]:
            mock.return_value = mock_client

        yield
```

### Part 3: Pre-commit Hook

**Location:** `.pre-commit-config.yaml`

**Configuration:**

```yaml
- repo: local
  hooks:
    - id: validate-mock-coverage
      name: Validate mock coverage
      entry: python scripts/validate-mock-coverage.py
      language: system
      types: [python]
      stages: [commit]
      pass_filenames: false
      always_run: true
```

**Effect:** Blocks commits that introduce unpatched import locations

---

## Prevention Workflow

### When Adding New Code

**Step 1: Write code with lazy import**

```python
# raglite/new_module/feature.py
def analyze_data(data):
    from raglite.shared.clients import get_mistral_client  # Lazy import
    client = get_mistral_client()
    return client.analyze(data)
```

**Step 2: Run validation script**

```bash
python scripts/validate-mock-coverage.py --verbose

# Output will show your new module in the gaps list
ERROR: Mock coverage gaps detected!
Found 1 module(s) importing get_mistral_client without mock coverage:
  ❌ raglite.new_module.feature.get_mistral_client
```

**Step 3: Add patch to mock fixture**

In `tests/fixtures/mock_clients.py`:

```python
@pytest.fixture(scope="session", autouse=True)
def mock_mistral_api_globally():
    with (
        # ... existing patches ...
        patch("raglite.new_module.feature.get_mistral_client") as mock_new,
    ):
        # ... setup ...
        mock_new.return_value = mock_client
        yield
```

**Step 4: Verify with validation**

```bash
python scripts/validate-mock-coverage.py

# Should output: ✅ Mock coverage validation PASSED
```

**Step 5: Commit**

Pre-commit hook will run validation again before accepting commit.

---

## Code Review Checklist

When reviewing PRs that add `get_mistral_client` imports:

- [ ] **New Code Pattern** - Import is inside function body (lazy)?
  - If yes → Continue
  - If no → Request change to lazy import (avoid circular imports)

- [ ] **Validation Script Run** - Did author run `python scripts/validate-mock-coverage.py`?
  - If yes and passed → Continue
  - If no or failed → Request re-run

- [ ] **Fixture Updated** - Is new module patched in `tests/fixtures/mock_clients.py`?
  - If yes → Continue
  - If no → Request patch addition

- [ ] **Test Execution** - Do unit tests complete in <5 seconds?
  - If yes → Continue
  - If timeout → Investigate missing patches

- [ ] **CI Passing** - Does validation script pass in CI?
  - If yes → Approve
  - If no → Block merge

---

## Troubleshooting: Finding Unpatched Locations

### Symptom: Unit test times out (>120s)

**Step 1: Confirm it's a missing mock**

```bash
# Run test with short timeout to fail fast
uv run pytest tests/unit/test_example.py --timeout=10 -v

# If timeout occurs, an API call is happening
# If external API block fixture runs, you'd see:
# "Unit test attempted to call Mistral API!"
```

**Step 2: Find which module is unpatched**

```bash
# Check validation script
python scripts/validate-mock-coverage.py --verbose

# Look for gaps section - shows unpatched modules
```

**Step 3: Identify the test's code path**

```bash
# Read the test source
cat tests/unit/test_example.py

# Find which functions it calls
# Trace those functions to see where get_mistral_client is imported

# Example:
# test_example() calls analyze_result()
# analyze_result() is in raglite/insights/analysis.py
# Check: grep -n "from raglite.shared.clients import" raglite/insights/analysis.py
```

**Step 4: Verify the patch is in fixture**

```bash
# Check if module is patched
grep "raglite.insights.analysis.get_mistral_client" tests/fixtures/mock_clients.py

# If not found, that's the missing patch
```

**Step 5: Add patch and re-run**

```bash
# Add patch to tests/fixtures/mock_clients.py
# Re-run: python scripts/validate-mock-coverage.py
# Re-run test: uv run pytest tests/unit/test_example.py -v
```

---

## Related Documentation

### CI Failure Runbook
- **Section 18:** Lazy Import Mock Coverage Gap
- **Quick Reference:** `Unit test attempted to call Mistral API!` entry
- **Decision Tree:** Mock Coverage Issues section

### Test Reliability Rules
- **File:** `.claude/rules/testing.md`
- **Section:** Mock Patterns
- **Pattern:** Lazy imports and session fixtures

### CI Strategy
- **File:** `docs/ci-strategy.md`
- **Section:** Mock Coverage (strategic prevention)

---

## Metrics & Success Criteria

### Target State (Achieved 2025-01-12)

- **Coverage:** 17/17 import locations patched (100%)
- **Automation:** validate-mock-coverage.py catches gaps before commit
- **CI Fix Rate:** <10% of commits are mock-related (down from 80%)
- **Test Performance:** Unit tests <3s (not >120s timeouts)

### Verification

```bash
# Run validation
python scripts/validate-mock-coverage.py

# Expected output
✅ Mock coverage validation PASSED
  - 17 module(s) import get_mistral_client
  - 17 location(s) patched in mock fixtures
  - 0 gaps (100% coverage)

# Run unit tests
uv run pytest tests/unit/ -v --timeout=30

# Expected
- All tests complete in <5 seconds
- No timeout failures
- No "attempted to call API" errors
```

---

## Appendix: All Patched Locations

**Current inventory (17 total):**

| Module | Import Type | Patched | Status |
|--------|------------|---------|--------|
| `raglite.mcp.tools` | Direct | Yes | ✅ |
| `raglite.mcp.tools.model_selector` | Lazy | Yes | ✅ |
| `raglite.mcp.tools.forecast_helpers` | Lazy | Yes | ✅ |
| `raglite.retrieval.search` | Direct | Yes | ✅ |
| `raglite.retrieval.search.enrichment` | Lazy | Yes | ✅ |
| `raglite.retrieval.search.ranking` | Lazy | Yes | ✅ |
| `raglite.insights.anomaly_detection` | Lazy | Yes | ✅ |
| `raglite.insights.patterns` | Lazy | Yes | ✅ |
| `raglite.forecasting.ensemble` | Lazy | Yes | ✅ |
| `raglite.forecasting.utils` | Lazy | Yes | ✅ |
| ... 7+ more modules | Lazy | Yes | ✅ |

**Total:** 17 locations, 17 patched = 100% coverage
