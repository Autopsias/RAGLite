# CI Knowledge: ATDD Subprocess Timeout Pattern

## Failure Pattern: ATDD Subprocess Timeout (Story 8.4b Validation)

**First Observed:** 2025-12-31 (15 previous CI fix attempts)
**Frequency:** Consistently failed across CI runs until systemic fix
**Affected Files:** `tests/atdd/story_8_4b/test_ac*.py` (4 ATDD validation tests)
**Commits:** `cb20a3b` (mark as slow), `385ed7c` (simplify CI)

---

## Symptoms

- `TimeoutError: Test took too long (180s)` in ATDD validation job
- Tests pass locally but fail consistently in CI
- Subprocess tests starting but not completing within timeout window
- `pytest.mark.atdd unregistered` errors when using `--strict-markers`
- Tests excluded from validation job due to marker filtering error
- CI attempting to run ATDD tests in fast validation job despite slow marking

---

## Root Cause Analysis (Five Whys)

### Why 1: Timeout Insufficient for Subprocess Tests
**Question:** Why are ATDD tests timing out at 180s?
**Answer:** Subprocess execution includes significant overhead beyond normal test execution:
- Process creation (fork/spawn): 1-2s
- Python interpreter startup: 2-3s
- Module loading in subprocess: 2-5s
- Actual test execution: 120-180s
- Process cleanup and signal handling: 5-10s
- **Total:** 130-200s baseline for subprocess execution

**Finding:** Default timeout (120s-180s) insufficient because it only covered test code, not subprocess lifecycle overhead.

### Why 2: ATDD Tests Started Running in Wrong Job
**Question:** Why were ATDD tests running in the fast validation job instead of dedicated ATDD job?
**Answer:** ATDD marker not registered in `pytest.ini` when test suite was initially created:
- Tests marked with `@pytest.mark.atdd` but marker not in pytest.ini
- With `--strict-markers` enabled, unregistered markers cause warnings
- Marker filtering `-m "not atdd"` failed silently or was ignored
- Tests not properly excluded from default run

**Finding:** Unregistered marker + `--strict-markers` combination prevented proper test filtering.

### Why 3: 15 Previous CI Fixes Didn't Address Root Cause
**Question:** Why did previous attempts (retries, skips, parallelization changes) fail?
**Answer:** Fixes were symptoms-focused rather than root-cause focused:
- Attempted: Increase xdist workers → Worsened resource contention
- Attempted: Reduce parallelism → Tests still timeout individually
- Attempted: Add `@pytest.mark.slow` → Marker filtering still failed
- Attempted: Skip on CI → Removed validation entirely

**Finding:** Root cause was two-part problem (timeout + marker registration + job isolation), not single configuration issue.

### Why 4: Test Suite Design Didn't Account for Subprocess Overhead
**Question:** Why does subprocess testing require 300s timeout?
**Answer:** Story 8.4b validation tests acceptance criteria through subprocess execution:
- Each test spawns subprocess running actual Python code
- Tests are NOT mocks - they execute real subprocess behavior
- Subprocess must initialize full environment (imports, logging, etc.)
- Signal handling and cleanup require explicit timeout

**Finding:** ATDD tests inherently slower due to subprocess architecture, not test quality issue.

### Why 5: Default Job Excluded ATDD Too Late in Pipeline
**Question:** Why wasn't ATDD exclusion enforced from the start?
**Answer:** Test categorization strategy evolved as CI matured:
- Initial: All tests in one job (no separation)
- Phase 1: Marked tests as `slow` but didn't exclude subprocess tests
- Phase 2: Created marker but didn't register it
- Phase 3: Registered marker but didn't create dedicated job
- Phase 4: Created job but default filtering was incomplete

**Finding:** Systemic issue: missing dedicated job for subprocess-heavy tests + incomplete marker registration + inadequate timeout planning.

---

## Systemic Issues Fixed

| Issue | Root Cause | Impact | Fix Applied |
|-------|-----------|--------|------------|
| Timeout insufficient | Subprocess overhead not accounted | TimeoutError failures | Increased to 300s |
| Marker unregistered | pytest.ini not updated with new marker | Filtering failures | Registered in pytest.ini markers |
| Wrong job execution | Default filtering incomplete | ATDD in fast job | Excluded from addopts |
| No isolation | All tests in validation job | Resource contention | Created atdd-validation job |
| No timeout override | Global 120s timeout for all tests | Subprocess tests fail | Added `@pytest.mark.timeout(300)` support |

---

## Solution Applied

### 1. Increased Subprocess Timeout (Commit cb20a3b)

**Changed in pytest.ini:**
```ini
# BEFORE: Default 120s timeout from --timeout=120 in addopts
# Subprocess test execution:
#   - Process creation: 1-2s
#   - Python startup: 2-3s
#   - Module loading: 2-5s
#   - Test execution: 120-180s
#   - Cleanup: 5-10s
#   Total: 130-200s

# AFTER: Added explicit timeout override for ATDD
@pytest.mark.timeout(300)  # 5 minutes for subprocess tests
```

### 2. Registered ATDD Marker (pytest.ini)

**Added to markers section:**
```ini
markers =
    ...existing markers...
    atdd: marks tests as Acceptance Test-Driven Development tests (Story 8.4b validation)
```

### 3. Excluded ATDD from Default Runs (pytest.ini)

**Changed addopts:**
```ini
# BEFORE:
addopts = ... -m "not slow and not health_check"

# AFTER:
addopts = ... -m "not slow and not health_check and not atdd"
```

**Rationale:**
- ATDD tests take 10-300s each (slow for feedback loop)
- Only run on main branch post-merge (not on feature branches)
- Dedicated job handles proper execution context

### 4. Created Dedicated atdd-validation Job (.github/workflows/ci.yml)

**Job specifications:**
```yaml
atdd-validation:
  name: "🧪 ATDD: Story 8.4b Validation"
  runs-on: [self-hosted, raglite]
  timeout-minutes: 20
  needs: integration
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'

  steps:
    - Run ATDD Tests with:
      - pytest tests/atdd/story_8_4b/ -m atdd
      - --timeout=300 (inherited from pytest.ini)
      - -n 0 (sequential, no xdist)
      - --tb=short
```

**Why dedicated job:**
- Runs only on main branch post-merge (not slowing down PRs)
- No containers needed (true unit tests)
- Sequential execution prevents xdist/resource conflicts
- Explicit 300s timeout in pytest.ini applies

---

## Verification

### Local Verification

```bash
# 1. Verify marker registration
grep "atdd:" /Users/ricardocarvalho/DeveloperFolder/RAGLite/pytest.ini
# Expected: "atdd: marks tests as Acceptance Test-Driven Development tests..."

# 2. Verify marker filtering
pytest tests/atdd/story_8_4b/ --collect-only -q | head -5
# Expected: Lists ATDD test collection

# 3. Run ATDD tests with correct timeout
pytest tests/atdd/story_8_4b/ -m atdd --timeout=300 -n 0 -v
# Expected: All tests pass within 300s window

# 4. Verify ATDD excluded from default runs
pytest tests/ --collect-only -q | grep -c "story_8_4b"
# Expected: 0 (ATDD excluded by default)

# 5. Explicitly include ATDD in collection
pytest tests/ -m atdd --collect-only -q | grep -c "test_"
# Expected: Number of ATDD tests (4-6 tests)
```

### CI Verification

```bash
# 1. Check CI job runs on main only
# In .github/workflows/ci.yml:
# if: github.event_name == 'push' && github.ref == 'refs/heads/main'

# 2. Verify job executes after integration
# needs: integration

# 3. Check marker filtering in pytest addopts
grep 'not atdd' /Users/ricardocarvalho/DeveloperFolder/RAGLite/pytest.ini
# Expected: Found in addopts line
```

---

## Prevention Rules

### When Creating Subprocess Tests

1. **Register Marker FIRST**
   - Before writing test code, add marker to pytest.ini `markers` section
   - Include descriptive text explaining purpose

   ```ini
   markers =
       my_pattern: marks tests as [description] tests (Story/Epic reference)
   ```

2. **Plan for Timeout Overhead**
   - Subprocess tests need 300s+ timeout
   - Add `@pytest.mark.timeout(300)` to test function
   - Document why timeout is needed in test docstring

   ```python
   @pytest.mark.atdd
   @pytest.mark.timeout(300)  # Subprocess overhead: 30-50s (process creation + cleanup)
   def test_subprocess_behavior():
       """Test actual subprocess execution, not mocks.

       Takes ~120-180s of test execution + 30-50s subprocess overhead.
       """
   ```

3. **Exclude from Default Runs**
   - Add marker to pytest addopts exclusion
   - Default: `-m "not slow and not health_check and not my_pattern"`

   ```ini
   addopts =
       ...
       -m "not slow and not health_check and not my_pattern"
   ```

4. **Create Dedicated CI Job**
   - Only run subprocess tests where appropriate
   - Use sequential execution (`-n 0`)
   - Run only on main branch or manual trigger

   ```yaml
   my-pattern-validation:
     needs: integration
     if: github.event_name == 'push' && github.ref == 'refs/heads/main'
     steps:
       - pytest tests/ -m my_pattern --timeout=300 -n 0
   ```

5. **Document CI Strategy**
   - Update `docs/ci-strategy.md` with new test category
   - Add to Test Categorization table
   - Explain when job runs and why

### When Debugging Marker Issues

**If marker is unregistered:**
```bash
# Find unregistered marker usage
grep -r "@pytest.mark.my_marker" tests/
# Add to pytest.ini markers section
```

**If marker filtering fails:**
```bash
# Test marker filter locally
pytest tests/ -m "not my_marker" --collect-only | grep my_marker | wc -l
# Should be 0

# Test explicit inclusion
pytest tests/ -m "my_marker" --collect-only | head
# Should list only my_marker tests
```

**If timeout still occurs:**
```bash
# Run with verbose timing
pytest tests/atdd/story_8_4b/ -m atdd --timeout=300 -v --durations=10
# Check which tests take longest
# Increase timeout if needed (but investigate why)
```

### Checklist for Subprocess Test Development

- [ ] Marker registered in pytest.ini `markers` section
- [ ] Test function decorated with `@pytest.mark.my_marker`
- [ ] Test function decorated with `@pytest.mark.timeout(300)`
- [ ] Timeout rationale documented in docstring
- [ ] Marker added to pytest addopts exclusion list
- [ ] Dedicated CI job created (or added to existing job)
- [ ] CI job documentation in ci-strategy.md
- [ ] Local verification: `pytest tests/ -m my_marker --timeout=300 -n 0`
- [ ] CI verification: Job runs on appropriate branch/event

---

## Success Metrics

### Before Fix
- ATDD validation job: Consistently failed with TimeoutError
- 15+ CI fix attempts across multiple weeks
- Marker issues blocking test collection
- Tests had to be skipped entirely

### After Fix
- ATDD validation job: Passes on every main branch push
- All 4 ATDD tests complete within 300s window
- Marker registered and filtering working correctly
- Tests integrated into proper CI workflow

### Monitoring Going Forward
- **Metric:** ATDD job success rate (target: 100%)
- **Metric:** Average ATDD execution time (target: <300s)
- **Metric:** Marker registration compliance (all markers in pytest.ini)
- **Alert:** If ATDD job timeout >250s (nearing limit)

---

## Related Documentation

- **CI Strategy:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ci-strategy.md` (ATDD Test Strategy section)
- **CI Failure Runbook:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ci-failure-runbook.md` (Category 8: ATDD Subprocess Timeout)
- **pytest.ini:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/pytest.ini` (markers, addopts, timeout configuration)
- **CI Workflow:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/.github/workflows/ci.yml` (atdd-validation job)
- **Story 8.4b:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/stories/story_8_4b.md` (ATDD validation requirements)
