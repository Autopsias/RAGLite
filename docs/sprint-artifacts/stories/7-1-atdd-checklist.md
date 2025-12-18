# ATDD Checklist - Story 7.1: Split test_external_data_clients.py

**Story:** 7-1-split-test-external-data-clients
**Epic:** 7 - Technical Debt & Code Quality
**Status:** RED (Tests Created, Implementation Pending)
**Created:** 2025-12-18
**Last Run:** 2025-12-18 (20 failed, 2 passed, 44 skipped in 0.18s)

---

## TDD Phase: RED

All acceptance tests are written and should **FAIL** until the refactoring is complete.
This is expected TDD behavior - we write tests first, then implement.

**Summary:**
- Total tests: 66
- Failed: 20 (expected - modules don't exist yet)
- Passed: 2 (directory and __init__.py exist)
- Skipped: 44 (waiting for implementation)

---

## Acceptance Criteria Test Mapping

### AC1: File Size Reduction

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-1.1 | `test_ac1_1_original_file_removed` | RED | Original test_external_data_clients.py should not exist |
| TEST-AC-1.2 | `test_ac1_2_module_under_hard_limit` | RED | Each new module must be under 500 LOC |
| TEST-AC-1.3 | `test_ac1_3_module_under_ideal_limit` | RED | Each new module should ideally be under 400 LOC |

### AC2: New Module Structure

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-2.1 | `test_ac2_1_directory_exists` | GREEN | tests/unit/external_data/ directory exists |
| TEST-AC-2.2 | `test_ac2_2_init_file_exists` | GREEN | __init__.py exists in the package |
| TEST-AC-2.3 | `test_ac2_3_conftest_exists` | RED | conftest.py exists with shared fixtures |
| TEST-AC-2.4 | `test_ac2_4_conftest_under_size_limit` | SKIP | conftest.py should be under 200 LOC |
| TEST-AC-2.5 | `test_ac2_5_expected_module_exists` | RED | Each expected module file exists (9 modules) |
| TEST-AC-2.6 | `test_ac2_6_module_contains_expected_classes` | RED | Each module contains expected test classes |

### AC3: Functionality Preserved

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-3.1 | `test_ac3_1_test_count_preserved` | SKIP | Test count must match baseline (131 tests) |
| TEST-AC-3.2 | `test_ac3_2_all_tests_pass` | SKIP | All tests in new structure must pass |
| TEST-AC-3.3 | `test_ac3_3_module_importable` | RED | Each module must be importable without errors |

### AC4: Shared Fixtures Extracted

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-4.1 | `test_ac4_1_conftest_has_mock_httpx_fixture` | SKIP | conftest.py has mock_httpx_response fixture |
| TEST-AC-4.2 | `test_ac4_2_conftest_has_required_imports` | SKIP | conftest.py has common imports |
| TEST-AC-4.3 | `test_ac4_3_conftest_has_sample_date_range_fixture` | SKIP | conftest.py has sample_date_range fixture |

### AC5: CI Compatibility

| Test ID | Test Name | Status | Description |
|---------|-----------|--------|-------------|
| TEST-AC-5.1 | `test_ac5_1_tests_discoverable` | SKIP | All tests discoverable by pytest |
| TEST-AC-5.2 | `test_ac5_2_module_has_asyncio_markers` | RED | Modules preserve @pytest.mark.asyncio markers |
| TEST-AC-5.3 | `test_ac5_3_no_duplicate_test_names` | SKIP | No duplicate test function names |

---

## Test Execution Commands

```bash
# Run all acceptance tests (expect failures in RED phase)
uv run pytest tests/unit/external_data/test_refactoring_acceptance.py -v

# Run specific AC category
uv run pytest tests/unit/external_data/test_refactoring_acceptance.py -v -k "TestAC1"
uv run pytest tests/unit/external_data/test_refactoring_acceptance.py -v -k "TestAC2"
uv run pytest tests/unit/external_data/test_refactoring_acceptance.py -v -k "TestAC3"
uv run pytest tests/unit/external_data/test_refactoring_acceptance.py -v -k "TestAC4"
uv run pytest tests/unit/external_data/test_refactoring_acceptance.py -v -k "TestAC5"

# Run only failing tests (RED phase)
uv run pytest tests/unit/external_data/test_refactoring_acceptance.py -v --tb=short
```

---

## Expected Module Structure After Refactoring

```
tests/unit/external_data/
  __init__.py              # Package init (EXISTS)
  conftest.py              # Shared fixtures (~150 LOC) - TO CREATE
  test_refactoring_acceptance.py  # ATDD tests (EXISTS)
  test_ine_client.py       # INE API tests (~400-550 LOC) - TO CREATE
  test_basegov_client.py   # BaseGov tests (~450-600 LOC) - TO CREATE
  test_bpstat_client.py    # BPstat API tests (~400-500 LOC) - TO CREATE
  test_omie_client.py      # OMIE API tests (~350-400 LOC) - TO CREATE
  test_oil_bulletin_client.py # EU Oil Bulletin tests (~400-500 LOC) - TO CREATE
  test_commodities_client.py # Commodities tests (~350-450 LOC) - TO CREATE
  test_atic_client.py      # ATIC cement tests (~150 LOC) - TO CREATE
  test_ipma_client.py      # IPMA weather tests (~200-250 LOC) - TO CREATE
  test_exceptions.py       # Shared exception tests (~125 LOC) - TO CREATE
```

---

## Baseline Metrics

| Metric | Before | After Target |
|--------|--------|--------------|
| Original file LOC | 3,025 | 0 (removed) |
| Test count | 131 | 131 (unchanged) |
| Max file LOC | 3,025 | <500 |
| Number of modules | 1 | 9-11 |
| Test classes | 29 | 29 (unchanged) |

---

## Test File Location

**ATDD Tests:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/tests/unit/external_data/test_refactoring_acceptance.py`

---

## Transition to GREEN Phase

After refactoring is complete, run:

```bash
# Verify all acceptance tests pass
uv run pytest tests/unit/external_data/test_refactoring_acceptance.py -v

# Verify original tests still pass
uv run pytest tests/unit/external_data/ -v --ignore=tests/unit/external_data/test_refactoring_acceptance.py

# Full validation
uv run pytest tests/unit/ -v
```

---

## Notes

- Tests use `pytest.skip()` for tests that cannot run until original file is removed
- Tests use `pytest.xfail()` for soft limits (ideal LOC) that are warnings
- All tests are marked with `@pytest.mark.acceptance` for filtering
- Parametrized tests cover all 9 expected modules
