# Story 7.1: Split test_external_data_clients.py (3,025 LOC -> <500 LOC per file)

**Epic:** 7 - Technical Debt & Code Quality
**Sprint Change Proposal:** SCP-2025-12-10-002
**Status:** Drafted
**Priority:** P0 (Critical - Enables Other Refactoring)
**Estimated Effort:** 1.5 days
**Actual Effort:** TBD

---

## User Story

As a developer, I want `tests/unit/test_external_data_clients.py` to be split into multiple files under 500 LOC each, so that AI assistants can comprehend the full file context and provide better suggestions when working on external data client tests.

---

## Context

The `tests/unit/test_external_data_clients.py` file is the **LARGEST FILE IN THE CODEBASE** at 3,025 lines. This significantly exceeds the 500 LOC limit established for optimal AI comprehension.

### Why This File First?

Per the File Size Refactoring Briefing (`docs/analysis/file-size-refactoring-briefing.md`):

1. **Unblocks external client refactoring** - Production files like `raglite/external_data/clients/basegov.py` (1,066 LOC) cannot be safely refactored until their test coverage is properly organized
2. **Largest test file** - At 3,025 LOC, it's 6x the ideal limit (500 LOC)
3. **Clear split boundaries** - 29 test classes organized by client make natural module boundaries

### Current Structure (29 Test Classes)

| Client | Test Classes | Estimated LOC |
|--------|--------------|---------------|
| **INE** | TestINEClient, TestINEDateFiltering, TestINEClientAdditional, TestStory68INEExtensions | ~550 |
| **BaseGov** | TestBaseGovClient, TestBaseGovStory695, TestBaseGovClientAdditional, TestBaseGovClientCoverage | ~600 |
| **BPstat** | TestBPstatClient, TestBPstatClientAdditional, TestBPstatStory693, TestStory68BPstatExtensions | ~500 |
| **OMIE** | TestOMIEClient, TestOMIEStory692, TestOMIEClientAdditional | ~400 |
| **EU Oil Bulletin** | TestEUOilBulletinClient, TestEUOilBulletinAdditional, TestEUOilBulletinStory694 | ~500 |
| **Commodities** | TestCommoditiesURLFix, TestCommoditiesClient, TestCommoditiesClientAdditional, TestCommoditiesClientCoverage | ~450 |
| **ATIC** | TestATICClient, TestATICClientAdditional | ~150 |
| **IPMA** | TestIPMAClient, TestIPMAClientAdditional, TestIPMAClientCoverage | ~250 |
| **Shared** | TestExceptions, TestRateLimitHandling | ~125 |

---

## Acceptance Criteria

### AC1: File Size Reduction
- [ ] `test_external_data_clients.py` removed (no longer exists)
- [ ] All new test modules are <500 LOC each
- [ ] Ideal target: 250-400 LOC per module

### AC2: New Module Structure
- [ ] Create `tests/unit/external_data/` directory
- [ ] Split into 7-9 test modules by client:
  - `tests/unit/external_data/__init__.py`
  - `tests/unit/external_data/conftest.py` (shared fixtures)
  - `tests/unit/external_data/test_ine_client.py` (~550 LOC or split further)
  - `tests/unit/external_data/test_basegov_client.py` (~600 LOC or split further)
  - `tests/unit/external_data/test_bpstat_client.py` (~500 LOC)
  - `tests/unit/external_data/test_omie_client.py` (~400 LOC)
  - `tests/unit/external_data/test_oil_bulletin_client.py` (~500 LOC)
  - `tests/unit/external_data/test_commodities_client.py` (~450 LOC)
  - `tests/unit/external_data/test_atic_client.py` (~150 LOC)
  - `tests/unit/external_data/test_ipma_client.py` (~250 LOC)
  - `tests/unit/external_data/test_exceptions.py` (~125 LOC)

### AC3: Functionality Preserved
- [ ] All existing tests pass unchanged
- [ ] No behavior changes to test logic
- [ ] Test count remains the same (no tests lost or duplicated)
- [ ] Coverage unchanged or improved

### AC4: Shared Fixtures Extracted
- [ ] Common imports consolidated in `conftest.py`
- [ ] Shared mock patterns extracted to conftest
- [ ] Client fixture factories if patterns emerge

### AC5: CI Compatibility
- [ ] All tests discoverable by pytest
- [ ] No changes to test markers (integration, slow, etc.)
- [ ] CI pipeline passes with new structure

### AC6: Documentation
- [ ] Update any references to old test file location
- [ ] Module docstrings explain test coverage scope

---

## Technical Design

### Target Directory Structure

```
tests/unit/external_data/
  __init__.py              # Empty or re-exports
  conftest.py              # ~150 LOC - shared fixtures, mocks
  test_ine_client.py       # ~400 LOC - INE API tests
  test_ine_date_filtering.py # ~150 LOC - Date filtering tests (if INE too large)
  test_basegov_client.py   # ~450 LOC - BaseGov tests (may need split)
  test_basegov_story695.py # ~150 LOC - Story 6.9.5 specific tests
  test_bpstat_client.py    # ~400 LOC - BPstat API tests
  test_omie_client.py      # ~350 LOC - OMIE API tests
  test_oil_bulletin_client.py # ~400 LOC - EU Oil Bulletin tests
  test_commodities_client.py # ~350 LOC - Commodities tests
  test_atic_client.py      # ~150 LOC - ATIC cement tests
  test_ipma_client.py      # ~200 LOC - IPMA weather tests
  test_exceptions.py       # ~125 LOC - Shared exception tests
```

### Shared Conftest Pattern

```python
# tests/unit/external_data/conftest.py
"""Shared fixtures for external data client unit tests."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.exceptions import (
    ExternalDataFetchError,
    ExternalDataValidationError,
)


@pytest.fixture
def mock_httpx_response() -> MagicMock:
    """Create a mock httpx response with configurable status and JSON."""
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_httpx_client(mock_httpx_response):
    """Create a mock async httpx client context manager."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_httpx_response
        )
        yield mock_client


@pytest.fixture
def sample_date_range() -> tuple[date, date]:
    """Common date range for testing."""
    return date(2024, 1, 1), date(2024, 12, 31)
```

### Split Strategy Per Client

| Client | Current Classes | Target Split |
|--------|-----------------|--------------|
| INE | 4 classes (~550 LOC) | Keep together if <500, else split date filtering |
| BaseGov | 4 classes (~600 LOC) | Split: main + story-specific |
| BPstat | 4 classes (~500 LOC) | Keep together (at limit) |
| OMIE | 3 classes (~400 LOC) | Keep together |
| EU Oil | 3 classes (~500 LOC) | Keep together (at limit) |
| Commodities | 4 classes (~450 LOC) | Keep together |
| ATIC | 2 classes (~150 LOC) | Keep together |
| IPMA | 3 classes (~250 LOC) | Keep together |
| Shared | 2 classes (~125 LOC) | Separate file |

---

## Implementation Tasks

### Task 1: Create Directory Structure (AC2)
- [ ] Create `tests/unit/external_data/` directory
- [ ] Create `__init__.py` file
- [ ] Create `conftest.py` with shared fixtures

### Task 2: Extract INE Client Tests (AC1, AC2)
- [ ] Move TestINEClient, TestINEDateFiltering to `test_ine_client.py`
- [ ] Move TestINEClientAdditional, TestStory68INEExtensions
- [ ] Update imports
- [ ] Verify tests pass: `pytest tests/unit/external_data/test_ine_client.py -v`

### Task 3: Extract BaseGov Client Tests (AC1, AC2)
- [ ] Move TestBaseGovClient to `test_basegov_client.py`
- [ ] Move TestBaseGovStory695, TestBaseGovClientAdditional, TestBaseGovClientCoverage
- [ ] If >500 LOC, split story-specific tests to separate file
- [ ] Verify tests pass

### Task 4: Extract BPstat Client Tests (AC1, AC2)
- [ ] Move TestBPstatClient, TestBPstatClientAdditional to `test_bpstat_client.py`
- [ ] Move TestBPstatStory693, TestStory68BPstatExtensions
- [ ] Verify tests pass

### Task 5: Extract OMIE Client Tests (AC1, AC2)
- [ ] Move TestOMIEClient, TestOMIEStory692, TestOMIEClientAdditional to `test_omie_client.py`
- [ ] Verify tests pass

### Task 6: Extract EU Oil Bulletin Tests (AC1, AC2)
- [ ] Move all EU Oil Bulletin classes to `test_oil_bulletin_client.py`
- [ ] Verify tests pass

### Task 7: Extract Commodities Tests (AC1, AC2)
- [ ] Move all Commodities classes to `test_commodities_client.py`
- [ ] Verify tests pass

### Task 8: Extract ATIC Tests (AC1, AC2)
- [ ] Move TestATICClient, TestATICClientAdditional to `test_atic_client.py`
- [ ] Verify tests pass

### Task 9: Extract IPMA Tests (AC1, AC2)
- [ ] Move all IPMA classes to `test_ipma_client.py`
- [ ] Verify tests pass

### Task 10: Extract Shared Tests (AC1, AC2)
- [ ] Move TestExceptions, TestRateLimitHandling to `test_exceptions.py`
- [ ] Verify tests pass

### Task 11: Remove Original File (AC1)
- [ ] Delete `tests/unit/test_external_data_clients.py`
- [ ] Verify full test suite passes: `pytest tests/unit/external_data/ -v`

### Task 12: Validate Totals (AC3, AC5)
- [ ] Count tests before and after (must match)
- [ ] Run full unit test suite
- [ ] Verify CI compatibility
- [ ] Check coverage is unchanged

---

## Dev Notes

### Refactoring Rules

Per [File Size Refactoring Briefing](../../analysis/file-size-refactoring-briefing.md) and [Complete Reference Implementation](../../architecture/6-complete-reference-implementation.md) for test organization patterns:

1. **Extract one module at a time** - Run tests after each extraction
2. **Do NOT batch test updates** - Incremental commits keep changes reviewable
3. **Run full test suite, not just affected tests** - Prevent hidden regressions
4. **Coverage must NOT drop** - Compare before/after coverage

### Commands for Validation

```bash
# Count tests in original file
pytest tests/unit/test_external_data_clients.py --collect-only | grep "test session starts" -A 1

# Count tests after split
pytest tests/unit/external_data/ --collect-only | grep "test session starts" -A 1

# Check file sizes after split
wc -l tests/unit/external_data/*.py

# Run full unit test suite
pytest tests/unit/ -v

# Check coverage
pytest tests/unit/external_data/ --cov=raglite/external_data --cov-report=term-missing
```

### Incremental Commit Strategy

```bash
# Commit after each client extraction
git commit -m "refactor(tests): extract INE client tests to separate module"
git commit -m "refactor(tests): extract BaseGov client tests to separate module"
# ... etc for each client
git commit -m "refactor(tests): remove original test_external_data_clients.py"
```

### Risk Mitigation

- **Import errors**: Ensure all imports are updated in new files
- **Fixture scope**: Shared fixtures in conftest.py are session/function scoped appropriately
- **Marker preservation**: All `@pytest.mark.asyncio` and other markers must be preserved

---

## Testing Requirements

### Before Refactoring
- Run: `pytest tests/unit/test_external_data_clients.py --collect-only -q`
- Record: Total test count (expected: ~180+ tests based on 29 classes)

### After Each Extraction
- Run: `pytest tests/unit/external_data/ -v`
- Verify: No failures, test count matches expectations

### Final Validation
- Run: `pytest tests/unit/ -v`
- Run: `pytest tests/ -m "not slow" -v`
- Verify: Full test suite green
- Verify: CI pipeline passes

---

## Dependencies

- None - This is the first story in Epic 7

---

## Success Metrics

1. **File size compliance**: All new files <500 LOC
2. **Test count preservation**: Same number of tests before/after
3. **Coverage maintained**: No coverage regression
4. **CI green**: All pipelines pass

---

## References

- [File Size Refactoring Briefing](../../analysis/file-size-refactoring-briefing.md)
- [File Size Limits Rule](../../.claude/rules/file-size-limits.md)
- [Sprint Status](../sprint-status.yaml)

---

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

TBD

### Debug Log References

N/A

### Completion Notes List

TBD

### File List

**Files to Delete:**
- `tests/unit/test_external_data_clients.py` (3,025 LOC)

**Files to Create:**
- `tests/unit/external_data/__init__.py`
- `tests/unit/external_data/conftest.py` (~150 LOC)
- `tests/unit/external_data/test_ine_client.py` (~400-550 LOC)
- `tests/unit/external_data/test_basegov_client.py` (~450-600 LOC)
- `tests/unit/external_data/test_bpstat_client.py` (~400-500 LOC)
- `tests/unit/external_data/test_omie_client.py` (~350-400 LOC)
- `tests/unit/external_data/test_oil_bulletin_client.py` (~400-500 LOC)
- `tests/unit/external_data/test_commodities_client.py` (~350-450 LOC)
- `tests/unit/external_data/test_atic_client.py` (~150 LOC)
- `tests/unit/external_data/test_ipma_client.py` (~200-250 LOC)
- `tests/unit/external_data/test_exceptions.py` (~125 LOC)

### Change Log

TBD
