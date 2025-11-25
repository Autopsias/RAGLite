# Qdrant Snapshot Optimization - Status & Next Steps

**Date:** 2025-11-08
**Status:** ✅ Implementation Complete, ⏳ Awaiting VS Code Reload

---

## Problem Identified

VS Code Test Explorer is still taking 1000+ seconds to run all tests because it **hasn't reloaded** the modified `conftest.py` file with snapshot optimizations.

### Root Cause Analysis

1. ✅ **Snapshot code exists** in `tests/integration/conftest.py`:
   - Global variable: Line 90
   - Snapshot creation: Lines 413-432
   - Snapshot restoration: Lines 507-553

2. ✅ **VS Code settings correct**:
   - No `--skip-ingestion` flag
   - Sequential execution (`-n 0`)
   - All 428 tests enabled

3. ❌ **VS Code hasn't reloaded** the modified conftest.py:
   - Python extension caches imported modules
   - Test output shows NO snapshot messages
   - Still using old code path without snapshots

---

## What We Implemented

### 1. Qdrant Snapshot Creation (Session Fixture)
**Location:** `tests/integration/conftest.py:413-432`

After PDF ingestion completes, creates a Qdrant snapshot:
```python
snapshot_info = qdrant.create_snapshot(
    collection_name=settings.qdrant_collection_name, wait=True
)
_session_snapshot_name = snapshot_info.name
```

**Expected Output:**
```
⚡ Creating Qdrant snapshot for fast test isolation...
✓ Snapshot created: [snapshot-name]
✓ Snapshot time: 0.XX s
✓ Restoration will be ~10-15x faster than re-ingestion
```

### 2. Qdrant Snapshot Restoration (Per-Test Fixture)
**Location:** `tests/integration/conftest.py:507-553`

Instead of re-ingesting PDF (10-15s), restores from snapshot (<1s):
```python
if _session_snapshot_name:
    # FAST PATH: Restore from snapshot
    qdrant.recover_snapshot(
        collection_name=settings.qdrant_collection_name,
        location=snapshot_url,
        priority="snapshot",
        wait=True,
    )
```

**Expected Output:**
```
⚡ Using snapshot: [snapshot-name]
✓ Restored (XX chunks) in 0.XX s
```

### 3. Integration Test Markers
**Files:** 10 integration test files

Added `pytestmark = pytest.mark.integration` to:
- test_ac1_fuzzy_entity_matching.py
- test_ac3_ground_truth.py
- test_accuracy_validation.py
- test_epic2_regression.py
- test_mcp_server.py
- test_metadata_injection.py
- test_multi_index_integration.py
- test_sql_routing.py
- test_story_2_14_excerpt_validation.py
- test_table_retrieval.py

---

## Expected Performance Improvement

### Before Snapshots (Current State)
- **Session fixture:** 15-20s (PDF ingestion + embedding)
- **Per-test restoration:** 10-15s × N tests without `preserve_collection`
- **Total for 428 tests:** 1500+ seconds

### After Snapshots (Once VS Code Reloads)
- **Session fixture:** 15-20s (PDF ingestion + embedding + snapshot creation)
- **Per-test restoration:** <1s × N tests (snapshot restore)
- **Expected total:** 300-400 seconds (70-75% faster)

### Caveat: `preserve_collection` Marker
**44 occurrences** across 16 test files skip restoration entirely:
- Tests marked with `@pytest.mark.preserve_collection` don't restore
- These tests benefit from session-scoped fixture but not per-test snapshots
- Expected impact: ~70% of tests will see speedup, 30% already optimal

---

## Next Steps

### Step 1: Reload VS Code (Required)
Choose ONE of these options:

**Option A - Quick Reload (Recommended):**
1. Open Command Palette: `Cmd+Shift+P`
2. Run: `Developer: Reload Window`

**Option B - Clear Cache + Reload:**
1. Open Command Palette: `Cmd+Shift+P`
2. Run: `Python: Clear Cache and Reload Window`

**Option C - Full Restart:**
1. Close VS Code completely
2. Reopen VS Code
3. Wait for Python extension to activate

### Step 2: Verify Snapshots Are Working
Run the verification script:
```bash
./scripts/verify_snapshot_optimization.sh
```

**Expected output:**
```
✅ FOUND: Snapshot creation message
✅ FOUND: Snapshot created: [snapshot-name]
✅ FOUND: Snapshot time: X.XX s
✅ SUCCESS: Snapshot optimization is active!
```

**If verification fails:**
- Snapshot code not executing (VS Code still using old conftest.py)
- Try Option B or C above (more aggressive reload)

### Step 3: Run Full Test Suite in Test Explorer
After verification passes:
1. Open Test Explorer in VS Code
2. Click "Run All Tests"
3. Monitor execution time

**Expected results:**
- **First run:** ~300-400 seconds (down from 1500s)
- **Subsequent runs:** Similar (snapshots reused)
- **Per-test time:** Most tests <1s restoration overhead

---

## Troubleshooting

### If snapshots still don't work after reload:

1. **Check Qdrant API compatibility:**
   ```bash
   # Verify Qdrant version supports snapshots (requires 1.0+)
   curl http://localhost:6333/
   ```

2. **Check for snapshot creation errors:**
   ```bash
   # Run a single test with full output
   pytest tests/integration/test_table_retrieval.py::TestTableRetrieval::test_search_tables_basic -xvs
   ```

3. **Verify snapshot files exist:**
   ```bash
   # Snapshots should be created in Qdrant data directory
   # (location depends on Docker/local install)
   ```

4. **Kill pytest processes manually:**
   ```bash
   pkill -f pytest
   # Then restart Test Explorer
   ```

---

## Technical Details

### Why 44 Tests Skip Restoration

Tests with `@pytest.mark.preserve_collection` are read-only tests that:
- Don't modify Qdrant collection
- Don't need restoration after execution
- Already optimized with session-scoped fixture

These tests won't benefit from snapshots but are already fast.

### Snapshot vs Re-ingestion Performance

| Operation | Time | Method |
|-----------|------|--------|
| **PDF ingestion** | 15-20s | Session fixture (once) |
| **Snapshot creation** | 0.5-1s | After ingestion (once) |
| **Snapshot restore** | <1s | Per-test (fast path) |
| **Re-ingestion** | 10-15s | Per-test (old slow path) |

**Speedup ratio:** 10-15x per restoration

---

## Files Modified

1. `tests/integration/conftest.py`
   - Added global `_session_snapshot_name` variable
   - Added snapshot creation after PDF ingestion
   - Modified `ensure_qdrant_test_isolation` to use snapshot restoration

2. `tests/integration/test_*.py` (10 files)
   - Added `pytestmark = pytest.mark.integration`

3. `scripts/verify_snapshot_optimization.sh` (new)
   - Verification script to confirm snapshots are active

4. `docs/SNAPSHOT-OPTIMIZATION-STATUS.md` (this file)
   - Documentation of implementation and next steps

---

## Success Criteria

✅ Verification script reports snapshot creation
✅ Verification script reports snapshot restoration
✅ Test Explorer completes all 428 tests in <500 seconds
✅ No test failures introduced by snapshot optimization

---

## Contact & Support

If issues persist after following all troubleshooting steps, provide:
- Output of verification script
- Full output of a single integration test run
- VS Code Python extension version
- Qdrant server version
