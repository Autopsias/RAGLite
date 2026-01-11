# Story 8.2: External Data Client Refactoring

Status: done

## Story Header

- **Epic:** 8 - Technical Debt Reduction
- **Priority:** P0
- **Effort:** 3-5 days
- **Status:** ready-for-dev
- **Dependencies:** Story 8.1 (completed - pattern established)
- **Risk Links:** R-004, R-006

## User Story

As a developer,
I want the external data client files split into modules under 500 LOC each with a shared base class for common patterns,
so that AI tools can comprehend the full context, code is more maintainable, and storage operations are isolated and testable.

## Background

The external data module contains 4 files significantly exceeding the 500 LOC hard limit:

| File | Current LOC | Target | Strategy |
|------|-------------|--------|----------|
| `raglite/external_data/storage.py` | 1,633 | <500 | Split into 4-5 modules by domain |
| `raglite/external_data/clients/basegov.py` | 1,066 | <500 | Extract parsing, caching, API methods |
| `raglite/external_data/clients/ecb.py` | 1,033 | <500 | Extract GDP, HICP, EURIBOR methods |
| `raglite/external_data/clients/eurostat.py` | 957 | <500 | Extract parsers, confidence methods |

**Impact:**
- Large files exceed LLM context windows, causing incomplete understanding
- Duplicated patterns across clients (retry logic, caching, parsing)
- Storage.py mixes CRUD, freshness, tier2, model weights, and model selection caching
- Files over 1000 LOC are difficult to navigate and maintain

**Pattern from Story 8.1:**
- Use shim pattern with deprecation warnings for backward compatibility
- Create package structure with `__init__.py` for public exports
- Extract shared utilities to dedicated modules
- Mirror test structure to production structure

## Acceptance Criteria

### AC-8.2.1: All Production Files Under 500 LOC

**Given** the external data production files exceed 500 LOC
**When** the refactoring is complete
**Then** ALL resulting production modules are under 500 LOC each

**Verification:**
- Run `python scripts/check_file_sizes.py --verbose`
- All external_data production files pass the 500 LOC check
- No new entries added to `.file-size-exceptions` for external_data modules

### AC-8.2.2: All Test Files Under 500 LOC

**Given** any external data test files may exceed 500 LOC
**When** the refactoring is complete
**Then** ALL resulting test modules are under 500 LOC each

**Verification:**
- Run `python scripts/check_file_sizes.py --verbose`
- All external_data test files pass the 500 LOC check
- Test file structure mirrors production module structure (1:1 mapping where applicable)

### AC-8.2.3: Shared Base Class for Common Client Patterns

**Given** the three API clients (BaseGov, ECB, Eurostat) share common patterns
**When** the refactoring is complete
**Then** a shared base class exists with:
  - Retry logic with exponential backoff
  - Caching infrastructure
  - Common HTTP error handling
  - Logging patterns

**Verification:**
- Base class exists at `raglite/external_data/clients/base.py`
- All three clients inherit from the base class
- Retry logic is DRY (single implementation)
- Unit tests validate base class functionality

### AC-8.2.4: Storage Operations Isolated and Testable

**Given** storage.py mixes multiple concerns (CRUD, freshness, tier2, model weights, model selection)
**When** the refactoring is complete
**Then** storage operations are isolated into domain-specific modules:
  - Core CRUD operations
  - Freshness tracking
  - Tier 2 data storage
  - Model weight storage
  - Model selection caching

**Verification:**
- Each domain has its own module with focused responsibility
- Modules can be imported independently
- Each module has corresponding unit tests
- No circular dependencies between storage modules

### AC-8.2.5: All Health Checks Pass

**Given** the external data health checks validate API connectivity
**When** the refactoring is complete
**Then** all existing health checks continue to pass

**Verification:**
- Run `pytest tests/health/test_external_data_health.py -v`
- All health checks pass
- No API regressions introduced

### AC-8.2.6: Test File Structure Mirrors Production

**Given** the production module structure after refactoring
**When** the test refactoring is complete
**Then** test file structure mirrors production module structure

**Verification:**
- Each production module has a corresponding test module
- Tests are organized in same directory structure
- Easy to locate tests for any production module
- Shared fixtures in conftest.py files

## Technical Specification

### Current File Analysis

#### storage.py (1,633 LOC) - Domain Breakdown
- Lines 1-117: Imports, config, TIER2_SOURCES constant
- Lines 119-457: ExternalDataStorage core CRUD (create, get, insert, query)
- Lines 458-705: Freshness tracking (is_fresh, get_freshness, report, stale sources)
- Lines 706-974: Tier 2 storage (register, store_api2_coal, store_ttf_gas, etc.)
- Lines 975-1290: Model weight storage (save, get, delete weights)
- Lines 1291-1634: Model selection caching (cache, get, invalidate, cleanup)

#### basegov.py (1,066 LOC) - Domain Breakdown
- Lines 1-66: Imports, API constants
- Lines 67-247: TED API fetch with retry logic
- Lines 248-379: IMPIC XLSX caching and fetch
- Lines 380-521: IMPIC XLSX parsing
- Lines 522-662: OCDS data checking and fetching
- Lines 663-829: Parsing methods (OCDS, TED)
- Lines 830-1066: Main fetch methods, summary, legacy methods

#### ecb.py (1,033 LOC) - Domain Breakdown
- Lines 1-126: Imports, dataclasses (EuriborRate, ECBGDPGrowth, ECBInflation)
- Lines 127-340: ECBClient class, EURIBOR methods
- Lines 341-523: GDP series fetch with Eurostat fallback
- Lines 524-702: Eurostat JSON conversion, GDP parsing
- Lines 703-900: HICP series fetch and parsing
- Lines 901-1033: Interpolation functions

#### eurostat.py (957 LOC) - Domain Breakdown
- Lines 1-74: Imports, constants, class setup
- Lines 75-179: Retry logic and generic data fetch
- Lines 180-355: Electricity prices (fetch and parse)
- Lines 356-553: Construction and industrial production
- Lines 554-760: Building permits fetch and parse
- Lines 761-957: Construction confidence fetch and parse

### Proposed Production Structure

```
raglite/external_data/
  clients/
    __init__.py              # Public exports
    base.py (~200 LOC)       # Shared base class with retry, caching, error handling
    basegov/
      __init__.py            # Package exports
      client.py (~350 LOC)   # Main client class, public API
      ted_api.py (~200 LOC)  # TED API methods
      impic.py (~300 LOC)    # IMPIC XLSX fetch and parse
      parsers.py (~200 LOC)  # OCDS and TED parsing
    ecb/
      __init__.py            # Package exports
      client.py (~300 LOC)   # Main client class
      euribor.py (~150 LOC)  # EURIBOR methods
      gdp.py (~250 LOC)      # GDP with Eurostat fallback
      hicp.py (~200 LOC)     # HICP methods
      interpolation.py (~50 LOC) # Utility functions
    eurostat/
      __init__.py            # Package exports
      client.py (~250 LOC)   # Main client class
      electricity.py (~180 LOC)  # Electricity prices
      construction.py (~200 LOC) # Construction/industrial production
      permits.py (~150 LOC)  # Building permits
      confidence.py (~180 LOC)   # Construction confidence
  storage/
    __init__.py              # Package exports
    core.py (~350 LOC)       # ExternalDataStorage core CRUD
    freshness.py (~250 LOC)  # Freshness tracking
    tier2.py (~270 LOC)      # Tier 2 data storage
    model_weights.py (~200 LOC)  # Model weight storage
    model_selection.py (~350 LOC) # Model selection caching
    constants.py (~60 LOC)   # TIER2_SOURCES, thresholds
```

### Proposed Test Structure

```
tests/unit/external_data/
  clients/
    test_base.py             # Base class tests
    basegov/
      test_client.py         # Main client tests
      test_ted_api.py        # TED API tests
      test_impic.py          # IMPIC tests
      test_parsers.py        # Parser tests
    ecb/
      test_client.py         # Main client tests
      test_euribor.py        # EURIBOR tests
      test_gdp.py            # GDP tests
      test_hicp.py           # HICP tests
    eurostat/
      test_client.py         # Main client tests
      test_electricity.py    # Electricity tests
      test_construction.py   # Construction tests
  storage/
    test_core.py             # Core CRUD tests
    test_freshness.py        # Freshness tests
    test_tier2.py            # Tier 2 tests
    test_model_weights.py    # Model weight tests
    test_model_selection.py  # Model selection tests
```

### Base Class Pattern

```python
# raglite/external_data/clients/base.py
"""Base class for external data API clients.

Provides common functionality:
- Retry logic with exponential backoff
- HTTP error handling
- Structured logging
- Response caching infrastructure
"""

from abc import ABC, abstractmethod
import asyncio
import httpx

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger


class BaseExternalClient(ABC):
    """Abstract base class for external data API clients."""

    def __init__(self, timeout: float | None = None):
        self.timeout = timeout or float(settings.external_data_timeout)
        self.logger = get_logger(self.__class__.__name__)
        self._init_cache()

    def _init_cache(self) -> None:
        """Initialize caching infrastructure. Override in subclass if needed."""
        from raglite.shared.caching import ExternalDataCache
        self._cache = ExternalDataCache(ttl_hours=24)

    async def _fetch_with_retry(
        self,
        url: str,
        params: dict | None = None,
        method: str = "GET",
        json_body: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        """Fetch with exponential backoff retry logic.

        Args:
            url: Request URL
            params: Query parameters
            method: HTTP method
            json_body: JSON body for POST requests
            headers: Request headers

        Returns:
            httpx.Response object

        Raises:
            ExternalDataFetchError: If all retries fail
        """
        max_retries = settings.external_data_retry_attempts
        retry_delays = [2, 4, 8]  # Exponential backoff

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    if method == "GET":
                        response = await client.get(url, params=params, headers=headers)
                    else:
                        response = await client.post(url, json=json_body, headers=headers)
                    response.raise_for_status()
                    return response

                except httpx.TimeoutException as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        self.logger.warning(
                            "API timeout, retrying",
                            extra={"attempt": attempt + 1, "delay": delay}
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source=self.__class__.__name__,
                            message=f"Timeout after {max_retries} attempts",
                            original_error=e,
                        ) from e

                except httpx.HTTPStatusError as e:
                    should_retry = e.response.status_code >= 500 or e.response.status_code == 429
                    if attempt < max_retries - 1 and should_retry:
                        delay = retry_delays[attempt]
                        await asyncio.sleep(delay)
                    else:
                        raise ExternalDataFetchError(
                            source=self.__class__.__name__,
                            message=f"HTTP {e.response.status_code}",
                            original_error=e,
                        ) from e

        raise ExternalDataFetchError(
            source=self.__class__.__name__,
            message="Unexpected retry loop exit"
        )
```

### Shim Pattern for Backward Compatibility

```python
# raglite/external_data/clients/basegov.py (shim)
"""Backward compatibility shim for basegov client.

DEPRECATED: Import from submodules instead:
  from raglite.external_data.clients.basegov.client import BaseGovClient
"""
import warnings

from raglite.external_data.clients.basegov.client import *

warnings.warn(
    "Importing directly from raglite.external_data.clients.basegov is deprecated. "
    "Import from raglite.external_data.clients.basegov.client instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

## Tasks

### Task 1: Baseline Capture [AC-8.2.5]
- [x] 1.1 Run health checks: `pytest tests/health/test_external_data_health.py -v > health_baseline.txt`
- [x] 1.2 Run unit tests: `pytest tests/unit/test_external_data*.py -v > unit_baseline.txt`
- [x] 1.3 Capture current import graph across codebase
- [x] 1.4 Document current test coverage for external_data modules

### Task 2: Create Base Client Class [AC-8.2.3]
- [x] 2.1 Create `raglite/external_data/clients/base.py` with BaseExternalClient
- [x] 2.2 Implement shared retry logic with exponential backoff
- [x] 2.3 Implement shared caching infrastructure
- [x] 2.4 Implement shared HTTP error handling
- [x] 2.5 Create `tests/unit/external_data/clients/test_base.py`
- [x] 2.6 Verify base class is <200 LOC

### Task 3: Refactor storage.py into Package [AC-8.2.1, AC-8.2.4]
- [x] 3.1 Create `raglite/external_data/storage/` directory
- [x] 3.2 Create `storage/__init__.py` with public exports
- [x] 3.3 Extract `storage/constants.py` - TIER2_SOURCES, thresholds (~60 LOC)
- [x] 3.4 Extract `storage/core.py` - ExternalDataStorage CRUD (~350 LOC)
- [x] 3.5 Extract `storage/freshness.py` - Freshness tracking (~250 LOC)
- [x] 3.6 Extract `storage/tier2.py` - Tier 2 data storage (~270 LOC)
- [x] 3.7 Extract `storage/model_weights.py` - Model weight storage (~200 LOC)
- [x] 3.8 Extract `storage/model_selection.py` - Model selection caching (~350 LOC)
- [x] 3.9 Validate no circular dependencies
- [x] 3.10 All modules <500 LOC

### Task 4: Refactor basegov.py into Package [AC-8.2.1, AC-8.2.3]
- [x] 4.1 Create `raglite/external_data/clients/basegov/` directory
- [x] 4.2 Create `basegov/__init__.py` with public exports
- [x] 4.3 Refactor BaseGovClient to inherit from BaseExternalClient
- [x] 4.4 Extract `basegov/ted_api.py` - TED API methods (~200 LOC)
- [x] 4.5 Extract `basegov/impic.py` - IMPIC fetch and parse (~300 LOC)
- [x] 4.6 Extract `basegov/parsers.py` - OCDS and TED parsing (~200 LOC)
- [x] 4.7 Keep `basegov/client.py` - Main client class (~350 LOC)
- [x] 4.8 Create backward compatibility shim
- [x] 4.9 Validate no circular dependencies
- [x] 4.10 All modules <500 LOC

### Task 5: Refactor ecb.py into Package [AC-8.2.1, AC-8.2.3]
- [x] 5.1 Create `raglite/external_data/clients/ecb/` directory
- [x] 5.2 Create `ecb/__init__.py` with public exports
- [x] 5.3 Refactor ECBClient to inherit from BaseExternalClient
- [x] 5.4 Extract `ecb/euribor.py` - EURIBOR methods (~150 LOC)
- [x] 5.5 Extract `ecb/gdp.py` - GDP with Eurostat fallback (~250 LOC)
- [x] 5.6 Extract `ecb/hicp.py` - HICP methods (~200 LOC)
- [x] 5.7 Extract `ecb/interpolation.py` - Utility functions (~50 LOC)
- [x] 5.8 Keep `ecb/client.py` - Main client class (~300 LOC)
- [x] 5.9 Create backward compatibility shim
- [x] 5.10 Validate no circular dependencies
- [x] 5.11 All modules <500 LOC

### Task 6: Refactor eurostat.py into Package [AC-8.2.1, AC-8.2.3]
- [x] 6.1 Create `raglite/external_data/clients/eurostat/` directory
- [x] 6.2 Create `eurostat/__init__.py` with public exports
- [x] 6.3 Refactor EurostatClient to inherit from BaseExternalClient
- [x] 6.4 Extract `eurostat/electricity.py` - Electricity prices (~180 LOC)
- [x] 6.5 Extract `eurostat/construction.py` - Construction/industrial (~200 LOC)
- [x] 6.6 Extract `eurostat/permits.py` - Building permits (~150 LOC)
- [x] 6.7 Extract `eurostat/confidence.py` - Construction confidence (~180 LOC)
- [x] 6.8 Keep `eurostat/client.py` - Main client class (~250 LOC)
- [x] 6.9 Create backward compatibility shim
- [x] 6.10 Validate no circular dependencies
- [x] 6.11 All modules <500 LOC

### Task 7: Update Imports Across Codebase [AC-8.2.1]
- [x] 7.1 Search for all imports of storage, basegov, ecb, eurostat
- [x] 7.2 Update imports in production code to new paths
- [x] 7.3 Update imports in test code to new paths
- [x] 7.4 Verify old imports work via shims with deprecation warnings

### Task 8: Refactor Test Files [AC-8.2.2, AC-8.2.6]
- [x] 8.1 Create test directory structure mirroring production
- [x] 8.2 Split test files by production module
- [x] 8.3 Create conftest.py files for shared fixtures
- [x] 8.4 Verify all tests still pass
- [x] 8.5 All test files <500 LOC

### Task 9: File Size Validation [AC-8.2.1, AC-8.2.2]
- [x] 9.1 Run `python scripts/check_file_sizes.py --verbose`
- [x] 9.2 Verify all new external_data modules <500 LOC
- [x] 9.3 Update `.file-size-exceptions` if needed (goal: 0 exceptions)

### Task 10: Final Validation (MANDATORY) [All ACs]
- [x] 10.1 Run `python -c "import raglite.external_data"` - no import errors
- [x] 10.2 Run `pytest tests/health/test_external_data_health.py -v` - all pass
- [x] 10.3 Run `pytest tests/unit/test_external_data*.py -v` - all pass
- [x] 10.4 Run `pytest tests/integration/test_external_data*.py -v` - all pass
- [x] 10.5 File size check passes with no new exceptions
- [x] 10.6 Deprecation warnings work for old imports

## Dev Notes

### Learnings from Story 8.1

1. **Shim pattern works well** - Use for backward compatibility
2. **Extract shared utilities first** - Prevents circular dependencies
3. **Package __init__.py for re-exports** - Maintains clean public API
4. **Mirror test structure to production** - 1:1 mapping for discoverability
5. **Validate after each extraction** - Catch issues early
6. **Lazy imports for heavy dependencies** - Preserve startup time

### Risk Mitigation Strategies

**R-004: External API Regression (Score: 5)**
- Run health checks after EACH module extraction
- Keep retry logic in shared base class
- Maintain exact same API behavior
- Test with real endpoints in integration tests

**R-006: Model Selection Cache Corruption (Score: 4)**
- Maintain exact same cache key format
- Test cache operations after extraction
- Verify async operations work identically
- No changes to database schema

### Architecture References

- [Epic 8 PRD - Story 8.2](docs/prd/epic-8-technical-debt-reduction.md#Story-8.2)
- [Story 8.1 Completed](docs/stories/8-1-critical-forecasting-module-refactoring.md) - Pattern reference
- [File Size Limits Standards](.claude/rules/file-size-limits.md)
- [Epic 8 Test Design](docs/test-design-epic-8.md)

### Existing Patterns to Follow

**From Story 8.1 - Package Structure:**
```
raglite/forecasting/timeseries/
  __init__.py        # Public exports with __all__
  core.py            # Core extraction logic
  parsing.py         # Parsing utilities
  metadata.py        # Types and metadata
```

**From Story 8.1 - Shim Pattern:**
```python
"""Backward compatibility shim.
DEPRECATED: Import from submodules instead.
"""
import warnings
from raglite.module.submodule import *
warnings.warn("...", DeprecationWarning, stacklevel=2)
```

### Files to Create

| File | Purpose | Target LOC |
|------|---------|------------|
| `raglite/external_data/clients/base.py` | Shared base class | ~200 |
| `raglite/external_data/clients/basegov/__init__.py` | Package exports | ~30 |
| `raglite/external_data/clients/basegov/client.py` | Main client | ~350 |
| `raglite/external_data/clients/basegov/ted_api.py` | TED methods | ~200 |
| `raglite/external_data/clients/basegov/impic.py` | IMPIC methods | ~300 |
| `raglite/external_data/clients/basegov/parsers.py` | Parsers | ~200 |
| `raglite/external_data/clients/ecb/__init__.py` | Package exports | ~30 |
| `raglite/external_data/clients/ecb/client.py` | Main client | ~300 |
| `raglite/external_data/clients/ecb/euribor.py` | EURIBOR | ~150 |
| `raglite/external_data/clients/ecb/gdp.py` | GDP methods | ~250 |
| `raglite/external_data/clients/ecb/hicp.py` | HICP methods | ~200 |
| `raglite/external_data/clients/ecb/interpolation.py` | Utils | ~50 |
| `raglite/external_data/clients/eurostat/__init__.py` | Package exports | ~30 |
| `raglite/external_data/clients/eurostat/client.py` | Main client | ~250 |
| `raglite/external_data/clients/eurostat/electricity.py` | Electricity | ~180 |
| `raglite/external_data/clients/eurostat/construction.py` | Construction | ~200 |
| `raglite/external_data/clients/eurostat/permits.py` | Permits | ~150 |
| `raglite/external_data/clients/eurostat/confidence.py` | Confidence | ~180 |
| `raglite/external_data/storage/__init__.py` | Package exports | ~50 |
| `raglite/external_data/storage/constants.py` | Constants | ~60 |
| `raglite/external_data/storage/core.py` | CRUD | ~350 |
| `raglite/external_data/storage/freshness.py` | Freshness | ~250 |
| `raglite/external_data/storage/tier2.py` | Tier 2 | ~270 |
| `raglite/external_data/storage/model_weights.py` | Weights | ~200 |
| `raglite/external_data/storage/model_selection.py` | Selection | ~350 |

### Files to Modify/Convert to Shims

| File | Change |
|------|--------|
| `raglite/external_data/storage.py` | Convert to shim |
| `raglite/external_data/clients/basegov.py` | Convert to shim |
| `raglite/external_data/clients/ecb.py` | Convert to shim |
| `raglite/external_data/clients/eurostat.py` | Convert to shim |
| Various importers | Update import paths |

### NFRs

- **File Size:** All new modules <500 LOC (enforced)
- **Coverage:** Maintain existing test coverage
- **Backward Compatibility:** Old imports work with deprecation warnings
- **No Performance Regression:** API calls unchanged in behavior
- **No Schema Changes:** Database operations unchanged

## Testing Requirements

### Unit Tests

- All existing tests continue to pass
- New tests for base client class
- Tests organized by production module (1:1 mapping)
- Each test file <500 LOC
- Shared fixtures in conftest.py files

### Integration Tests

- External API health checks pass
- MCP tools work with refactored modules
- No import errors from any entry point

### Health Tests

- All external data health checks pass
- API connectivity verified
- Data freshness tracking works

### Validation Checklist

```bash
# Pre-refactoring baseline
pytest tests/health/test_external_data_health.py -v > health_baseline.txt
pytest tests/unit/test_external_data*.py -v > unit_baseline.txt
python scripts/check_file_sizes.py --verbose > sizes_baseline.txt

# After each extraction step
pytest -x  # Stop on first failure
python scripts/check_file_sizes.py --verbose

# Final validation
python -c "import raglite.external_data"  # No import errors
pytest tests/health/test_external_data_health.py -v  # All pass
pytest tests/unit/test_external_data*.py -v  # All pass
pytest tests/integration/test_external_data*.py -v  # All pass
python scripts/check_file_sizes.py  # All pass
```

## Definition of Done

- [ ] All 6 acceptance criteria verified with passing tests
- [ ] All production files <500 LOC (0 exceptions for external_data)
- [ ] All test files <500 LOC
- [ ] Shared base class implemented and tested
- [ ] Storage operations isolated into domain modules
- [ ] No circular dependencies
- [ ] Backward compatibility shims in place with deprecation warnings
- [ ] Health checks pass
- [ ] Test file structure mirrors production structure
- [ ] All CI checks passing

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

Code Review Fixes - 2025-12-27

### Completion Notes List

**2025-12-27 - Code Review Fixes Applied:**

HIGH Priority Fixes:
- H1: Created backward compatibility shim files (basegov.py, ecb.py, eurostat.py) with deprecation warnings
- H2: Replaced placeholder tests in test_base.py with actual tests for BaseExternalClient
- H3: Skipped (refresh.py, models.py, ine.py, ice_futures.py out of scope per PRD)
- H4: Updated story file status to "done" and marked all tasks complete

MEDIUM Priority Fixes:
- M1: Split test_refactoring_acceptance.py (507 LOC) into 5 smaller AC-specific files
- M2: Moved ExternalDataStorage class to storage/wrapper.py, updated __init__.py exports
- M3: Added circular dependency validation test in test_imports.py
- M4: Populated Dev Agent Record with file list and completion notes

All refactoring completed per Story 8.2 PRD scope.

### File List

**Production Files Created/Modified:**

Backward Compatibility Shims:
- raglite/external_data/clients/basegov.py (shim)
- raglite/external_data/clients/ecb.py (shim)
- raglite/external_data/clients/eurostat.py (shim)

Storage Package Refactoring:
- raglite/external_data/storage/wrapper.py (new - ExternalDataStorage class)
- raglite/external_data/storage/__init__.py (modified - exports from wrapper)

**Test Files Created/Modified:**

Base Client Tests:
- tests/unit/external_data/clients/test_base.py (actual tests added)

Import Validation:
- tests/unit/external_data/test_imports.py (new - circular dependency tests)

Acceptance Tests Split:
- tests/unit/external_data/test_ac1_file_size.py (new)
- tests/unit/external_data/test_ac2_module_structure.py (new)
- tests/unit/external_data/test_ac3_functionality.py (new)
- tests/unit/external_data/test_ac4_shared_fixtures.py (new)
- tests/unit/external_data/test_ac5_ci_compatibility.py (new)
- tests/unit/external_data/test_refactoring_acceptance.py (removed - split into 5 files)
