# CI Prevention Infrastructure - Pytestmark E402

**Created:** 2025-12-26
**Purpose:** Break the fix-push-fail cycle by preventing pytestmark-before-imports violations at commit time

---

## Root Cause Analysis

### Problem
- **Symptom:** CI fails with E402 errors (import not at top of file)
- **Root Cause:** pytestmark placed before or between imports violates ruff E402 rule
- **Impact:** 10 test files with violations, causing recurring CI failures

### Why This Happens
```python
# WRONG - pytestmark before imports (violates E402)
pytestmark = pytest.mark.integration  # ❌ Module-level code
import pytest  # Import must be at top

# WRONG - pytestmark between imports (violates E402)
import pytest
pytestmark = pytest.mark.integration  # ❌ Module-level code
from qdrant_client import QdrantClient  # Import must be at top

# CORRECT - pytestmark after all imports
import pytest
from qdrant_client import QdrantClient

pytestmark = pytest.mark.integration  # ✅ After all imports
```

---

## Infrastructure Changes

### 1. Pre-Commit Hook Added

**File:** `.pre-commit-config.yaml`

**Hook Added:**
```yaml
- id: check-pytestmark-e402
  name: check-pytestmark-e402-violations
  entry: python scripts/fix-pytestmark-e402.py --check
  language: python
  pass_filenames: false
  stages: [pre-commit]
  files: ^tests/.*\.py$
```

**Behavior:**
- Runs automatically on `git commit`
- Scans all test files for pytestmark violations
- **Blocks commit** if violations found
- Exit code 1 triggers pre-commit to fail

### 2. Test File Template

**File:** `tests/_template.py`

**Purpose:**
- Shows correct pytestmark placement pattern
- Documents wrong patterns to avoid
- Reference for new test files

**Usage:**
```bash
# Copy template when creating new test
cp tests/_template.py tests/unit/test_new_feature.py
```

---

## Current Violations

As of 2025-12-26, **10 files** have pytestmark E402 violations:

### Integration Tests (5 files)
1. `tests/integration/test_metadata_injection.py` - pytestmark at line 13 (between imports)
2. `tests/integration/test_mcp_server.py` - pytestmark at line 18 (between imports)
3. `tests/integration/test_epic2_regression.py` - pytestmark at line 37 (between imports)
4. `tests/integration/test_table_retrieval.py` - pytestmark at line 10 (between imports)
5. `tests/integration/test_anomaly_detection_integration.py` - pytestmark at line 16 (between imports)

### Unit Tests (5 files)
6. `tests/unit/test_trend_analysis.py` - pytestmark at line 16 (between imports)
7. `tests/unit/test_multivariate_forecasting.py` - pytestmark at line 19 (between imports)
8. `tests/unit/test_chronos_integration.py` - pytestmark at line 23 (between imports)
9. `tests/unit/test_catboost_integration.py` - pytestmark at line 22 (between imports)
10. `tests/unit/test_hybrid_forecasting.py` - pytestmark at line 20 (between imports)

**Note:** These files are temporarily allowed via E402 per-file-ignores in `pyproject.toml` (lines 178-183).

---

## Workflow Changes

### Before (Fix-Push-Fail Cycle)
1. Developer writes test with pytestmark before imports
2. Commits and pushes code
3. CI fails 10 minutes later with E402 error
4. Developer fixes violation
5. Pushes again
6. Cycle repeats

### After (Prevention at Commit Time)
1. Developer writes test with pytestmark before imports
2. Attempts `git commit`
3. **Pre-commit hook fails immediately** (<5 seconds)
4. Developer fixes violation using template
5. Commit succeeds
6. CI passes (violations prevented)

---

## Developer Quick Reference

### Fix Violations Automatically
```bash
# Preview changes
python scripts/fix-pytestmark-e402.py --dry-run

# Apply fixes
python scripts/fix-pytestmark-e402.py

# Check for violations
python scripts/fix-pytestmark-e402.py --check
```

### Manual Fix Pattern
1. Move all imports to top of file
2. Add blank line after imports
3. Place `pytestmark = ...` after imports
4. Add blank line after pytestmark
5. Verify: `python scripts/fix-pytestmark-e402.py --check`

### Reference Template
```bash
# View correct pattern
cat tests/_template.py

# Copy template for new test
cp tests/_template.py tests/unit/test_new_feature.py
```

---

## Next Steps (Tactical Phase)

### Phase 1: Remove Grandfathered Violations
- [ ] Run `python scripts/fix-pytestmark-e402.py` to fix all 10 violations
- [ ] Remove E402 per-file-ignores from `pyproject.toml` (lines 178-183)
- [ ] Verify: `python scripts/fix-pytestmark-e402.py --check` exits 0
- [ ] Commit fixes

### Phase 2: Enable Pre-Commit Enforcement
- [ ] Install pre-commit hooks: `pre-commit install`
- [ ] Test hook: `pre-commit run check-pytestmark-e402 --all-files`
- [ ] Verify hook blocks commits with violations

### Phase 3: Documentation
- [ ] Update `.claude/rules/testing.md` with pytestmark pattern
- [ ] Add pytestmark section to developer onboarding guide

---

## CI Impact

### Current CI Check (To Be Removed)
**Location:** `.github/workflows/ci.yml` lines 83-87

```yaml
- name: Check E402 pytestmark Violations
  run: |
    echo "=== Checking for pytestmark E402 violations ==="
    python scripts/fix-pytestmark-e402.py --check
    echo "No pytestmark E402 violations found"
```

**Status:** This check is redundant once pre-commit is enforced. Can be removed after Phase 2.

### Pre-Commit vs CI
| Check Point | Time to Feedback | Blocks Merge | Developer Experience |
|-------------|------------------|--------------|---------------------|
| **Pre-Commit** | <5 seconds | Yes (prevents push) | ✅ Fast feedback loop |
| **CI** | ~10 minutes | Yes (after push) | ❌ Slow feedback loop |

---

## Metrics

### Before Infrastructure
- E402 violations: 10 files
- Average fix time: 15 minutes (discovery + fix + re-push)
- CI wait time: 10 minutes per failure
- Total waste: ~25 minutes per violation

### After Infrastructure (Projected)
- E402 violations: 0 (enforced at commit time)
- Average fix time: 30 seconds (immediate feedback)
- CI wait time: 0 (violations never reach CI)
- Total savings: ~25 minutes per developer per violation

---

## Related Documentation

- [Testing Rules](.claude/rules/testing.md) - Test infrastructure patterns
- [CI Strategy](docs/ci/STRATEGY.md) - CI pipeline architecture
- [Fix Script](scripts/fix-pytestmark-e402.py) - Automated violation fixer
- [Template](tests/_template.py) - Correct pytestmark pattern reference
