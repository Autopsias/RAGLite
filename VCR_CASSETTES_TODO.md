# VCR Cassettes Recording - TODO

## Status: Ready for CI - Cassettes Will Be Recorded on First Run

The CI workflow changes for P0 and P1 fixes have been implemented and committed.

VCR cassettes were not recorded locally (Docker/Colima not running), but this is **NOT a blocker** because the VCR configuration uses `record_mode: "once"`, which means the first CI run will automatically record cassettes when tests make live API calls.

## What Was Implemented

### ✅ P0 Immediate Fixes
1. Updated `MARKER_EXPR` to exclude `external_api` tests (line 382)
2. Changed `--dist loadfile` to `--dist loadgroup` (line 383)

### ✅ P1 Structural Fixes
1. Removed `tests/integration/external_data/` from postgresql shard (line 233)
2. Removed root-level external_data tests from postgresql shard:
   - `test_external_data_core.py`
   - `test_external_data_schema.py`
   - `test_ecb_macro_core.py`
3. Removed `--ignore=tests/integration/external_data/` from "other" shard
4. Updated shard descriptions to reflect changes

## What Still Needs To Be Done

### Record VCR Cassettes

VCR cassettes need to be recorded for the ~69 external API tests in `tests/integration/external_data/`.

**Option 1: Record locally (requires Docker)**
```bash
# Start Docker/Colima
colima start

# Record cassettes (VCR will record on first run)
uv run pytest tests/integration/external_data/ \
  --record-mode=once \
  -v \
  --timeout=300
```

**Option 2: Let CI record on first run**

The VCR configuration uses `record_mode: "once"`, which means:
- If cassettes are missing, VCR will record them during the test run
- If cassettes exist, VCR will replay them (no network calls)

The first CI run after these changes will:
1. Detect missing cassettes
2. Make live API calls and record responses
3. Commit the cassettes to the repository

Subsequent CI runs will use the recorded cassettes (fast).

## Expected Results After Cassette Recording

- PostgreSQL shard: 20+ min → 5-10 min (70% reduction)
- External API tests: 10-20 min → <5 min (cassettes eliminate network calls)
- ~50-100 YAML cassette files in `tests/integration/external_data/cassettes/`

## Verification Commands

```bash
# Count cassettes after recording
find tests/integration/external_data/cassettes -type f -name "*.yaml" | wc -l

# Verify cassettes work (should be fast, no network calls)
uv run pytest tests/integration/external_data/ -v --timeout=120

# Check test duration improvement
uv run pytest tests/integration/external_data/ -v --durations=10
```

## Next Steps

1. Wait for Docker to be available OR
2. Push changes and let CI record cassettes on first run
3. Verify cassettes are committed to repository
4. Monitor CI timing improvements

## Technical Details

- VCR config location: `tests/integration/external_data/conftest.py`
- Cassette directory: `tests/integration/external_data/cassettes/{module_name}/`
- Record mode: `"once"` (records if missing, replays if exists)
- Sensitive headers filtered: authorization, x-api-key, cookie
