# CI Infrastructure Refactoring - Session Continuation Prompt

**Created**: 2025-12-24
**Branch**: `ci-refactor-phase2-complete`
**Last CI Run**: 20488331257

---

## CONTEXT: What Was Accomplished

### Phase 1-3: COMPLETED ✅

We successfully completed the core CI infrastructure refactoring:

1. **Container Management Scripts** (Phase 2)
   - Created `scripts/ci/container-config.sh` - Centralized container configuration
   - Created `scripts/ci/start-test-containers.sh` - Unified container startup
   - Created `scripts/ci/cleanup-test-containers.sh` - Cleanup script

2. **SIGKILL Fix** (Phase 3) - **VALIDATED WORKING**
   - Root cause: Orphaned `resource_tracker` processes from joblib multiprocessing
   - Fix Part 1: Added orphaned process cleanup in CI workflow pre-test step
   - Fix Part 2: Configured joblib to use threading backend (no multiprocessing)
   - Location: `.github/workflows/ci.yml` lines 503-525 and `tests/conftest.py` lines 150-200

3. **Docker Desktop → Colima Migration** (Phase 3) - **VALIDATED WORKING**
   - Replaced unstable Docker Desktop with Colima (runs as launchd service)
   - Colima config: 4 CPUs, 8GB RAM, 100GB disk, Docker runtime
   - Updated CI workflow to use Colima for self-healing
   - Service enabled: `brew services start colima`

### Validation Results (Run 20488331257):
```
✅ Integration Tests: PASSED (6m8s) - NO SIGKILL!
✅ E2E Tests: PASSED (4m40s)
✅ Coverage Gates: PASSED (1m27s)
✅ Docker Availability: PASSED (14s) - Colima stable
✅ Unit Tests: PASSED (4m34s)
```

---

## TASK: Complete Remaining Phases

### Phase 4: Migrate Remaining Test Jobs (PRIORITY: HIGH)

The following jobs still use inline container management and need migration to use the new scripts:

1. **test-agentic-workflows job**
   - Currently: Inline PostgreSQL/Qdrant startup on ports 5438/6338
   - Migrate to: `./scripts/ci/start-test-containers.sh agentic`

2. **test-discovery job**
   - Currently: Inline Qdrant startup
   - Migrate to: `./scripts/ci/start-test-containers.sh discovery`

3. **burn-in job**
   - Currently: Inline container management
   - Migrate to: `./scripts/ci/start-test-containers.sh burnin`

### Phase 5: Cleanup Infrastructure (PRIORITY: HIGH)

Add a guaranteed cleanup job that runs `always()` at the end of the workflow:
```yaml
cleanup:
  name: "🧹 Cleanup: Containers"
  runs-on: [self-hosted, raglite]
  if: always()
  needs: [all-other-jobs]
  steps:
    - name: Cleanup all test containers
      run: |
        ./scripts/ci/cleanup-test-containers.sh all
```

### Phase 6: Concurrency Management (PRIORITY: MEDIUM)

Disable `cancel-in-progress` for main branch to prevent production disruption:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
```

### Phase 7: Performance Optimization (PRIORITY: LOW)

Lazy-load Settings in `tests/conftest.py` to prevent import-time database connections:
- Move `from raglite.shared.settings import Settings` inside fixtures
- Use `@lru_cache` for settings singleton

### Phase 8: Production Protection (PRIORITY: MEDIUM)

1. Create production protection test suite in `tests/integration/test_production_safety.py`
2. Add container safety validation module
3. Add CI pre-flight checks to all database jobs

### Phase 9: Documentation (PRIORITY: LOW)

1. Create `tests/CONFTEST_ARCHITECTURE.md`
2. Create `docs/operations/emergency-procedures.md`
3. Create `scripts/ci/README.md`

### Phase 10: Final Validation & Merge (PRIORITY: HIGH)

1. Verify conftest.py line reduction (target: <500 LOC)
2. Run full test suite
3. Merge to main
4. Validate CI pipeline on main branch

---

## CI ISSUES TO FIX

### Issue 1: UV Cache Corruption (RECURRING)

**Symptoms**:
```
× Failed to download `torch==2.9.1`
├─▶ Failed to extract archive
├─▶ I/O operation failed during extraction
╰─▶ failed to create file / No such file or directory (os error 2)
```

**Affected Jobs**: Test Discovery, Performance Validation

**Root Cause**: UV cache corruption from interrupted downloads or APFS quirks

**Fix**: Add uv cache validation/cleaning step BEFORE dependency installation:
```yaml
- name: Validate uv cache
  run: |
    # Clean corrupted cache entries
    if [ -d ~/.cache/uv ]; then
      CACHE_SIZE=$(du -sm ~/.cache/uv 2>/dev/null | cut -f1 || echo "0")
      if [ "$CACHE_SIZE" -gt 2048 ]; then
        echo "Pruning large uv cache (${CACHE_SIZE}MB)..."
        rm -rf ~/.cache/uv
      fi
    fi
```

**Quick Fix**: Run `rm -rf ~/.cache/uv` on runner to clear cache

### Issue 2: Agentic PostgreSQL Startup Failure

**Symptoms**: "Start and verify PostgreSQL (Agentic)" step fails with exit code 1

**Affected Jobs**: Agentic Workflow Suite

**Root Cause**: Port conflict or container startup race condition on port 5438

**Fix**: Migrate to use `./scripts/ci/start-test-containers.sh agentic` which has proper port management

### Issue 3: Epic 6 Accuracy Gate Failure

**Symptoms**: `Epic 6 accuracy gate failed (MAPE > 12%)`

**Affected Jobs**: NFR: Epic 6 Accuracy Gate

**Root Cause**: This is a TEST LOGIC failure, not infrastructure. The forecasting models are not meeting the 12% MAPE threshold.

**Fix**: This requires investigation of the forecasting model accuracy, not CI infrastructure. May need Story 6.8 (model retraining).

**Note**: This is BLOCKING the merge but is unrelated to the CI refactoring work.

---

## COMMANDS TO RESUME

```bash
# Switch to the branch
git checkout ci-refactor-phase2-complete

# Verify Colima is running
colima status
docker info

# Check latest CI run status
gh run list --branch ci-refactor-phase2-complete --limit 3

# Clear uv cache if needed (fixes extraction errors)
rm -rf ~/.cache/uv

# Run integration tests locally to verify
APP_ENV=test uv run pytest tests/integration/ -v --tb=short
```

---

## KEY FILES

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Main CI workflow (updated for Colima) |
| `scripts/ci/container-config.sh` | Container configuration constants |
| `scripts/ci/start-test-containers.sh` | Unified container startup |
| `scripts/ci/cleanup-test-containers.sh` | Container cleanup |
| `tests/conftest.py` | Pytest fixtures (joblib fix at line 150) |

---

## DECISION POINTS

1. **Epic 6 Accuracy Failure**: Should we bypass this gate temporarily to merge CI fixes, or fix accuracy first?

2. **UV Cache**: Should we add proactive cache cleaning to ALL jobs, or just the affected ones?

3. **Remaining Phases**: Complete all phases before merge, or merge core fixes and do phases 6-9 as follow-up PRs?

---

## SUCCESS CRITERIA

- [ ] All test jobs use `scripts/ci/` container management
- [ ] No SIGKILL failures (exit code 137) in any test job
- [ ] Colima stays running throughout entire workflow
- [ ] UV cache errors resolved
- [ ] Integration, E2E, and Unit tests all pass
- [ ] Merged to main with green CI
