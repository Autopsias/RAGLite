# Story 7.3: Split Integration conftest.py (1,463 LOC -> <500 LOC per file)

**Epic:** 7 - Technical Debt & Code Quality
**Sprint Change Proposal:** SCP-2025-12-10-002
**Status:** Drafted
**Priority:** P0 (Critical - Enables Test Infrastructure Maintainability)
**Estimated Effort:** 1 day
**Actual Effort:** TBD

---

## User Story

As a developer, I want `tests/integration/conftest.py` to be split into organized modules under 500 LOC each, so that AI assistants can comprehend the full fixture context and integration test configuration is easier to maintain.

---

## Context

The `tests/integration/conftest.py` file is currently **1,463 lines**, nearly 3x the 500 LOC limit established for optimal AI comprehension. This file contains critical integration test infrastructure including session-scoped fixtures for PDF ingestion, Qdrant test isolation, and database verification.

### Why This File?

Per the File Size Refactoring Briefing (`docs/analysis/file-size-refactoring-briefing.md`):

1. **Core integration test infrastructure** - All integration tests depend on this conftest for environment setup, session fixtures, and test isolation
2. **Exceeds hard limit** - At 1,463 LOC, it's nearly 3x the ideal limit (500 LOC)
3. **Clear split boundaries** - Logical groups of fixtures (session ingestion, test isolation, module-scoped fixtures) make natural module boundaries

### Current Structure Analysis (1,463 LOC)

| Component | Lines | Purpose |
|-----------|-------|---------|
| **Environment Setup** | ~50 | APP_ENV, TESTING, PostgreSQL env vars (before raglite imports) |
| **Service Checking** | ~60 | check_service_available, get_service_availability, check_and_skip_if_unavailable |
| **Imports & Globals** | ~40 | Lazy imports, session state globals |
| **Database Schema Fixture** | ~75 | ensure_test_database_schema (session-scoped) |
| **Embedding Model Warmup** | ~70 | warmup_embedding_model (session-scoped) |
| **Session Ingestion Fixture** | ~470 | session_ingested_collection (main ingestion logic) |
| **Restoration Helper** | ~90 | _do_restoration function |
| **Test Isolation Fixture** | ~170 | ensure_qdrant_test_isolation (autouse per-test fixture) |
| **Module-Scoped PDF Fixtures** | ~200 | ingested_160_page_pdf, ingested_excerpt_pdf |
| **Read-Only Access Fixtures** | ~60 | qdrant_with_sample_docs, mock_synthesis_agent |
| **Ground Truth Fixtures** | ~60 | sample_ground_truth |
| **Comments/Whitespace** | ~118 | Documentation and formatting |

---

## Acceptance Criteria

### AC1: File Size Reduction
**Given** the integration `tests/integration/conftest.py` file exceeds 500 LOC (currently 1,463)
**When** the refactoring is complete
**Then**:
- [ ] `tests/integration/conftest.py` reduced to <350 LOC (core only)
- [ ] All new modules are <500 LOC each
- [ ] Ideal target: 150-350 LOC per module

### AC2: New Module Structure
**Given** fixtures are currently monolithic in integration conftest
**When** creating the new modular structure
**Then**:
- [ ] Create `tests/integration/fixtures/` directory
- [ ] Split into organized modules:
  - `tests/integration/conftest.py` (~300 LOC) - Core env setup, pytest_plugins, pytestmark
  - `tests/integration/fixtures/__init__.py` (~5 LOC) - Empty or minimal exports
  - `tests/integration/fixtures/service_checking.py` (~80 LOC) - Service availability checks
  - `tests/integration/fixtures/session_fixtures.py` (~350 LOC) - Session-scoped fixtures (ingestion, warmup)
  - `tests/integration/fixtures/test_isolation.py` (~280 LOC) - Qdrant test isolation, restoration
  - `tests/integration/fixtures/module_fixtures.py` (~250 LOC) - Module-scoped PDF fixtures
  - `tests/integration/fixtures/helper_fixtures.py` (~120 LOC) - Mock agents, ground truth, read-only access

### AC3: Functionality Preserved
**Given** the existing integration test suite has ~115 passing tests
**When** fixture extraction is complete
**Then**:
- [ ] All existing integration tests pass unchanged
- [ ] No behavior changes to fixture logic
- [ ] All fixtures remain discoverable by pytest
- [ ] Session-scoped fixtures still run exactly once per session
- [ ] Test isolation (lazy restoration) still works correctly

### AC4: Shared State Preserved
**Given** session-scoped fixtures share global state variables
**When** distributing fixtures across modules
**Then**:
- [ ] Global state variables (_session_sample_pdf_chunk_count, etc.) accessible to all fixture modules
- [ ] No circular import issues between fixture modules
- [ ] State management for lazy restoration works correctly

### AC5: CI Compatibility
**Given** CI pipeline depends on integration test discovery and execution
**When** running in GitHub Actions
**Then**:
- [ ] All integration tests discoverable by pytest
- [ ] `--skip-ingestion` flag still works
- [ ] Test markers (preserve_collection, manages_collection_state) still work
- [ ] CI pipeline passes with new structure
- [ ] VS Code Test Explorer works correctly

### AC6: Documentation
**Given** the refactored structure changes fixture organization
**When** updating documentation
**Then**:
- [ ] Module docstrings explain fixture/hook purposes
- [ ] Update any references to old conftest.py organization
- [ ] Developer notes in story file document new structure

---

## Technical Design

### Target Directory Structure

```
tests/integration/
  conftest.py                       # ~300 LOC - Core env setup, pytest_plugins, pytestmark
  fixtures/
    __init__.py                     # ~5 LOC - Empty or minimal re-exports
    service_checking.py             # ~80 LOC - Service availability checks
    session_fixtures.py             # ~350 LOC - Session-scoped fixtures
    test_isolation.py               # ~280 LOC - Test isolation, restoration
    module_fixtures.py              # ~250 LOC - Module-scoped PDF fixtures
    helper_fixtures.py              # ~120 LOC - Mock agents, ground truth, etc.
```

### Session State Management

The session-scoped fixtures share global state that tracks:
- `_session_sample_pdf_chunk_count` - Baseline chunk count for test isolation
- `_session_snapshot_name` - Qdrant snapshot name for fast restoration
- `_session_postgresql_row_count` - PostgreSQL baseline for restoration
- `_session_sample_pdf_result` - Ingestion result for --skip-ingestion mode
- `_session_ingestion_duration` - Ingestion timing

**Strategy:** Create a `tests/integration/fixtures/session_state.py` module that defines these globals and is imported by other fixture modules:

```python
# tests/integration/fixtures/session_state.py
"""Session state management for integration test fixtures.

This module defines global variables shared across session-scoped fixtures.
These track the baseline state for test isolation and restoration.
"""

# Track session-level expected Qdrant state for test isolation
session_sample_pdf_chunk_count: int | None = None
session_snapshot_name: str | None = None
session_postgresql_row_count: int | None = None
session_sample_pdf_result = None
session_ingestion_duration: float = 0.0
```

### pytest_plugins Configuration

The integration conftest.py will declare pytest_plugins to load fixture modules:

```python
# tests/integration/conftest.py
"""Integration test configuration for RAGLite.

PRODUCTION-PROVEN PATTERN: Session-scoped fixture with read-only data sharing.
"""

import os
import sys

# CRITICAL: Set test environment variables BEFORE any raglite imports
if "APP_ENV" not in os.environ:
    os.environ["APP_ENV"] = "test"
if "TESTING" not in os.environ:
    os.environ["TESTING"] = "true"
# ... other env vars

# Force reload Settings singleton after env vars set
import raglite.shared.config
from raglite.shared.config import Settings
raglite.shared.config.settings = Settings()

# Load fixture modules via pytest_plugins
pytest_plugins = [
    "tests.integration.fixtures.service_checking",
    "tests.integration.fixtures.session_fixtures",
    "tests.integration.fixtures.test_isolation",
    "tests.integration.fixtures.module_fixtures",
    "tests.integration.fixtures.helper_fixtures",
]

# Apply preserve_collection to all integration tests by default
import pytest
pytestmark = pytest.mark.preserve_collection
```

### Module Responsibilities

| Module | Responsibility | Key Functions/Fixtures |
|--------|---------------|------------------------|
| `conftest.py` | Environment setup, pytest_plugins, pytestmark | Core configuration |
| `session_state.py` | Global state variables for session tracking | State variables only |
| `service_checking.py` | Service availability checks before tests | check_service_available, get_service_availability |
| `session_fixtures.py` | Session-scoped fixtures | ensure_test_database_schema, warmup_embedding_model, session_ingested_collection |
| `test_isolation.py` | Per-test isolation and restoration | _do_restoration, ensure_qdrant_test_isolation |
| `module_fixtures.py` | Module-scoped PDF fixtures | ingested_160_page_pdf, ingested_excerpt_pdf |
| `helper_fixtures.py` | Helper fixtures for tests | qdrant_with_sample_docs, mock_synthesis_agent, sample_ground_truth |

---

## Implementation Tasks

### Task 1: Create Module Structure (AC2)
- [ ] Create `tests/integration/fixtures/` directory
- [ ] Create `tests/integration/fixtures/__init__.py` file
- [ ] Create `tests/integration/fixtures/session_state.py` for shared globals
- [ ] Verify directory structure

### Task 2: Extract Service Checking (AC1, AC2)
- [ ] Create `tests/integration/fixtures/service_checking.py`
- [ ] Move check_service_available function
- [ ] Move get_service_availability function
- [ ] Move check_and_skip_if_unavailable function
- [ ] Move QDRANT_HOST, QDRANT_PORT, POSTGRES_HOST, POSTGRES_PORT constants
- [ ] Move qdrant_available, postgres_available globals
- [ ] Verify file size: `wc -l tests/integration/fixtures/service_checking.py` (expect ~80 LOC)
- [ ] Verify pytest can discover module: `pytest tests/integration/ --collect-only --quiet | tail -5`
  - Expected output: "collected X items" where X is the same as before extraction
- [ ] Verify no import errors: `python -c "from tests.integration.fixtures.service_checking import *; print('OK')"`
  - Expected output: "OK"

### Task 3: Extract Session Fixtures (AC1, AC2, AC4)
- [ ] Create `tests/integration/fixtures/session_fixtures.py`
- [ ] Move ensure_test_database_schema fixture
- [ ] Move warmup_embedding_model fixture
- [ ] Move session_ingested_collection fixture
- [ ] Import session state from session_state.py
- [ ] Verify file size: `wc -l tests/integration/fixtures/session_fixtures.py` (expect ~350 LOC)
- [ ] Verify no import errors: `python -c "from tests.integration.fixtures.session_fixtures import *; print('OK')"`
  - Expected output: "OK"
- [ ] Verify fixture discovery: `pytest tests/integration/ --fixtures | grep -E "session_ingested_collection|warmup_embedding_model|ensure_test_database_schema"`
  - Expected: All 3 session fixtures listed
- [ ] Verify tests pass: `pytest tests/integration/ --skip-ingestion -v --collect-only --quiet | tail -5`
  - Expected: Same test count as before, no import errors

### Task 4: Extract Test Isolation (AC1, AC2, AC4)
- [ ] Create `tests/integration/fixtures/test_isolation.py`
- [ ] Move _do_restoration helper function
- [ ] Move ensure_qdrant_test_isolation fixture
- [ ] Import session state from session_state.py
- [ ] Verify tests pass

### Task 5: Extract Module Fixtures (AC1, AC2)
- [ ] Create `tests/integration/fixtures/module_fixtures.py`
- [ ] Move ingested_160_page_pdf fixture
- [ ] Move ingested_excerpt_pdf fixture
- [ ] Import session state from session_state.py
- [ ] Verify tests pass

### Task 6: Extract Helper Fixtures (AC1, AC2)
- [ ] Create `tests/integration/fixtures/helper_fixtures.py`
- [ ] Move qdrant_with_sample_docs fixture
- [ ] Move mock_synthesis_agent fixture
- [ ] Move sample_ground_truth fixture
- [ ] Verify tests pass

### Task 7: Update Root conftest.py (AC1, AC4)
- [ ] Update pytest_plugins list to load new modules
- [ ] Keep only core environment setup
- [ ] Keep pytestmark definition
- [ ] Keep imports needed for env setup
- [ ] Verify conftest.py is <350 LOC

### Task 8: Validate State Sharing (AC3, AC4)
- [ ] Verify session state accessible from all modules
- [ ] Test lazy restoration works correctly
- [ ] Verify --skip-ingestion flag still works
- [ ] Run: `pytest tests/integration/ --skip-ingestion -v`

### Task 9: Run Full Test Suite (AC3, AC5)
- [ ] Verify test discovery:
  - Command: `pytest tests/integration/ --collect-only --quiet | tail -5`
  - Expected: "collected ~115 items" (exact count should match pre-refactor baseline)
  - Fail criteria: Different test count or import errors
- [ ] Verify fixtures are loadable:
  - Command: `pytest tests/integration/ --fixtures | grep -E "^(ensure_|warmup_|session_|ingested_)" | wc -l`
  - Expected: ~8 fixtures (ensure_test_database_schema, warmup_embedding_model, session_ingested_collection, ensure_qdrant_test_isolation, ingested_160_page_pdf, ingested_excerpt_pdf, qdrant_with_sample_docs, sample_ground_truth)
  - Fail criteria: Missing fixtures or import errors
- [ ] Verify tests pass with pre-ingested data:
  - Command: `pytest tests/integration/ --skip-ingestion -v --tb=short`
  - Expected: All tests PASSED, no FAILED, no import errors
  - Fail criteria: Any test failures or import errors
- [ ] Verify fresh ingestion works:
  - Command: `pytest tests/integration/ -v -k "test_query_" --tb=short`
  - Expected: Session ingestion runs once, tests PASSED
  - Fail criteria: Ingestion errors, test failures
- [ ] Verify CI pipeline passes:
  - Check: GitHub Actions workflow completes successfully
  - Expected: All jobs green (lint, type check, tests, accuracy gate)
  - Fail criteria: Any job failures or warnings

### Task 10: File Size Validation (AC1)
- [ ] Run: `wc -l tests/integration/conftest.py tests/integration/fixtures/*.py`
- [ ] Verify all files <500 LOC
- [ ] Document final line counts in completion notes

---

## Dev Notes

### Architecture Documentation References

This refactoring follows established patterns from the RAGLite architecture documentation:

1. **Fixture Organization Patterns**
   - Source: `docs/architecture/6-complete-reference-implementation.md`
   - Section: "Testing Infrastructure & Fixtures"
   - Pattern: pytest_plugins for modular fixture loading
   - Pattern: Session-scoped fixtures for expensive setup (embeddings, ingestion)
   - Pattern: Module-scoped fixtures for shared test data

2. **Testing Strategy & Infrastructure**
   - Source: `docs/architecture/8-phased-implementation-strategy-v11-simplified.md`
   - Section: "Testing Strategy"
   - Strategy: ~372 total tests (200 unit, 115 integration, 28 e2e)
   - Strategy: Integration tests use real Qdrant/PostgreSQL on test ports (6335/5433)
   - Strategy: Session-scoped fixtures for expensive operations (PDF ingestion ~75-85s)

3. **Test Organization & Separation**
   - Source: `docs/architecture/3-repository-structure-monolithic.md`
   - Section: "tests/ Directory Structure"
   - Structure: tests/unit/, tests/integration/, tests/e2e/
   - Structure: Shared fixtures in tests/fixtures/, test-specific in conftest.py files

### Refactoring Rules

Per [File Size Refactoring Briefing](../../analysis/file-size-refactoring-briefing.md):

1. **Extract one module at a time** - Run tests after each extraction
2. **Do NOT batch changes** - Incremental commits keep changes reviewable
3. **Run full test suite** - Prevent hidden regressions
4. **Preserve fixture discovery** - pytest fixtures must be loadable

### Integration Test Architecture

Per `tests/CLAUDE.md` and `tests/integration/conftest.py` documentation:
- Session-scoped fixtures ingest PDFs once (75-85 seconds)
- All read-only tests share the ingested collection (zero setup per test)
- Tests that need fresh data use @pytest.mark.manages_collection_state
- Lazy restoration reduces O(N) restorations to O(transitions)

### Key Fixture Dependencies

```
warmup_embedding_model (session)
    |
    v
session_ingested_collection (session, autouse)
    |
    +---> ensure_qdrant_test_isolation (function, autouse)
    |
    +---> ingested_160_page_pdf (module)
    |
    +---> ingested_excerpt_pdf (module)
    |
    +---> qdrant_with_sample_docs (function)
```

### Commands for Validation

```bash
# Count lines in all fixture files
wc -l tests/integration/conftest.py tests/integration/fixtures/*.py

# Verify fixture discovery (should show all fixtures)
pytest tests/integration/ --fixtures | grep -E "^(ensure_|warmup_|session_|ingested_)"

# Verify pytest options work
pytest --help | grep -E "(skip-ingestion|run-slow)"

# Verify test discovery (should be ~115 tests)
pytest tests/integration/ --collect-only -q | tail -5

# Full integration test suite (with pre-ingested data)
pytest tests/integration/ --skip-ingestion -v

# Check for import errors
python -c "from tests.integration.fixtures.session_fixtures import *; print('OK')"
python -c "from tests.integration.fixtures.test_isolation import *; print('OK')"
```

### Incremental Commit Strategy

```bash
# Commit after each module extraction
git commit -m "refactor(tests): create integration fixtures directory structure"
git commit -m "refactor(tests): extract service_checking to separate module"
git commit -m "refactor(tests): extract session_fixtures to separate module"
git commit -m "refactor(tests): extract test_isolation to separate module"
git commit -m "refactor(tests): extract module_fixtures to separate module"
git commit -m "refactor(tests): extract helper_fixtures to separate module"
git commit -m "refactor(tests): update integration conftest.py to load fixture modules"
```

### Risk Mitigation

- **Session state sharing**: Use centralized session_state.py module to avoid import order issues
- **Import order**: Environment vars must be set BEFORE raglite imports (in conftest.py only)
- **Fixture discovery**: pytest_plugins must list all fixture modules
- **Autouse fixtures**: ensure_test_database_schema, warmup_embedding_model, session_ingested_collection must remain autouse
- **Lazy restoration**: Global dirty flag (_collection_dirty) must be accessible from test_isolation module

### Test Markers Behavior

The following markers must continue to work after refactoring:
- `@pytest.mark.preserve_collection` - Skip cleanup (read-only tests)
- `@pytest.mark.manages_collection_state` - Mark session dirty, defer restoration

---

## Testing Requirements

### Before Refactoring
- Run: `pytest tests/integration/ --collect-only -q | tail -5`
- Record: Total test count (expected: ~115 tests)
- Record: `wc -l tests/integration/conftest.py` (expected: 1,463 LOC)

### After Each Extraction
- Run: `pytest tests/integration/ --skip-ingestion -v --tb=short`
- Verify: No failures, no import errors
- Verify: pytest markers still work

### Final Validation
- Run: `pytest tests/integration/ --collect-only`
- Run: `pytest tests/integration/ --skip-ingestion -v`
- Verify: Full test suite green
- Verify: CI pipeline passes
- Verify: `wc -l tests/integration/conftest.py` < 350 LOC

---

## Dependencies

- **Story 7.1** (split_test_external_data_clients) - Independent, can run in parallel
- **Story 7.2** (split_root_conftest) - Independent, can run in parallel
- **tests/fixtures/database_fixtures.py** - Already exists, will remain unchanged

---

## Success Metrics

1. **File size compliance**: Root conftest.py <350 LOC, all new files <500 LOC
2. **Test count preservation**: Same number of integration tests before/after (~115)
3. **Fixture discovery**: All fixtures remain discoverable
4. **Session behavior**: Session fixtures still run exactly once
5. **Test isolation**: Lazy restoration still works correctly
6. **CI green**: All pipelines pass

---

## References

- [File Size Refactoring Briefing](../../analysis/file-size-refactoring-briefing.md)
- [File Size Limits Rule](../../.claude/rules/file-size-limits.md)
- [Testing Guidelines](../../tests/CLAUDE.md)
- [Testing Rules](../../.claude/rules/testing.md)
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

**Files to Modify:**
- `tests/integration/conftest.py` (1,463 LOC -> ~300 LOC)

**Files to Create:**
- `tests/integration/fixtures/__init__.py` (~5 LOC)
- `tests/integration/fixtures/session_state.py` (~30 LOC)
- `tests/integration/fixtures/service_checking.py` (~80 LOC)
- `tests/integration/fixtures/session_fixtures.py` (~350 LOC)
- `tests/integration/fixtures/test_isolation.py` (~280 LOC)
- `tests/integration/fixtures/module_fixtures.py` (~250 LOC)
- `tests/integration/fixtures/helper_fixtures.py` (~120 LOC)

### Change Log

TBD
