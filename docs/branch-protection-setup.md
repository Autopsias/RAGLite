# GitHub Branch Protection Configuration

**Story:** 3-0-7 Priority Classification System
**Purpose:** Configure GitHub to require P0+P1 tests before merging to main
**Last Updated:** 2025-11-05

---

## Overview

Priority-based CI workflows are now configured in `.github/workflows/test-priority-based.yml`. To enforce quality gates, configure GitHub branch protection to require P0+P1 tests to pass before merging.

---

## Branch Protection Setup (GitHub UI)

### Step 1: Navigate to Branch Protection

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Click **Branches** in left sidebar
4. Under "Branch protection rules", click **Add rule** (or edit existing `main` rule)

### Step 2: Configure Protection Rule for `main`

**Branch name pattern:** `main`

**Required Settings:**

#### ✅ Require a pull request before merging
- [x] Require approvals: **1** (recommended)
- [ ] Dismiss stale pull request approvals when new commits are pushed (optional)
- [x] Require review from Code Owners (if using CODEOWNERS file)

#### ✅ Require status checks to pass before merging
- [x] Require branches to be up to date before merging

**Required Status Checks:**
- [x] `Pre-Merge (P0+P1 - 20 min)` ← **REQUIRED** for Story 3-0-7
- [x] `Smoke Tests (P0 - 6 min)` ← Optional but recommended

**Do NOT require:**
- `Full Test Suite (All priorities)` - Only runs nightly/on-demand

#### ✅ Additional Recommended Settings
- [x] Require conversation resolution before merging
- [x] Require linear history (optional - keeps history clean)
- [ ] Include administrators (optional - up to you)

#### ❌ Do NOT Enable (Unless Needed)
- [ ] Require deployments to succeed before merging
- [ ] Require signed commits (optional - adds friction)
- [ ] Lock branch (prevents all pushes)

### Step 3: Save Changes

Click **Create** (or **Save changes** if editing existing rule)

---

## Verification

### Test Branch Protection Works

1. **Create a test branch:**
   ```bash
   git checkout -b test/verify-branch-protection
   echo "test" >> README.md
   git add README.md
   git commit -m "test: verify branch protection"
   git push origin test/verify-branch-protection
   ```

2. **Create a Pull Request:**
   - Go to GitHub → Pull Requests → New Pull Request
   - Base: `main`, Compare: `test/verify-branch-protection`
   - Click "Create Pull Request"

3. **Verify Status Checks:**
   - You should see "Smoke Tests (P0)" and "Pre-Merge (P0+P1)" workflows running
   - Merge button should be **disabled** until both pass
   - If checks fail, merge button stays disabled ✅

4. **Clean up:**
   ```bash
   git checkout main
   git branch -D test/verify-branch-protection
   git push origin --delete test/verify-branch-protection
   ```

---

## CI Workflow Overview

### Smoke Tests (P0 only - ~18 min)
- **Runs on:** Every push to main, epic-*/*, story-*/*
- **Purpose:** Quick critical path validation (82 tests)
- **Required:** No (but recommended for fast feedback)

### Pre-Merge Tests (P0+P1 - ~49 min)
- **Runs on:** Every push + pull requests to main
- **Purpose:** Core features + critical path (225 tests)
- **Required:** **YES** ← Blocks merge if fails

### Full Test Suite (All priorities - ~82 min)
- **Runs on:** Nightly at 2 AM UTC, manual dispatch, `[full-tests]` in commit message
- **Purpose:** Comprehensive validation (379 tests)
- **Required:** No (too slow for pre-merge)

---

## Cost Optimization Impact

**Before Priority System:**
- Full suite every commit: ~82 min × 50 commits/day = **68.4 hours/day**

**After Priority System:**
- Pre-merge (P0+P1): ~49 min × 50 commits/day = **40.6 hours/day**
- **Savings:** **41% reduction** in CI time (27.8 hours/day saved)

---

## Troubleshooting

### Issue: "Merge button is always disabled"

**Cause:** Status check names don't match workflow job names

**Solution:**
1. Go to Settings → Branches → Edit rule for `main`
2. In "Require status checks to pass", click "Search for status checks"
3. Type "Pre-Merge" and select the exact job name
4. Ensure it matches workflow name in `.github/workflows/test-priority-based.yml`

### Issue: "Status checks don't run on PRs"

**Cause:** Workflow not configured to run on pull requests

**Solution:**
Check `.github/workflows/test-priority-based.yml` has:
```yaml
on:
  pull_request:
    branches:
      - main
```

### Issue: "Full Test Suite blocks merges"

**Cause:** Full Test Suite is marked as required status check

**Solution:**
1. Go to Settings → Branches → Edit rule for `main`
2. **Uncheck** "Full Test Suite (All priorities)"
3. Only require "Pre-Merge (P0+P1)" and optionally "Smoke Tests (P0)"

---

## Manual Testing Commands

```bash
# Run P0 smoke tests locally (18 min)
pytest tests/ -m "priority('P0')"

# Run P0+P1 pre-merge tests locally (49 min)
pytest tests/ -m "priority('P0') or priority('P1')"

# Run full test suite locally (82 min)
pytest tests/

# Check priority distribution
python scripts/analyze-test-priorities.py
```

---

## References

- **Story:** `docs/stories/3-0-7-priority-classification-system.md`
- **Priority Report:** `docs/test-priority-report.md`
- **Testing Guidelines:** `docs/testing-guidelines.md`
- **CI Workflow:** `.github/workflows/test-priority-based.yml`

---

## Next Steps After Configuration

1. ✅ Verify branch protection works (create test PR)
2. ✅ Monitor CI run times in GitHub Actions tab
3. ✅ Adjust priority distribution if needed (rebalance P0/P1/P2/P3)
4. ✅ Train team on priority-based testing workflow
5. ✅ Document priority assignment criteria for new tests

---

**Questions?**

Contact Test Architect (Murat) or raise in team standup.
