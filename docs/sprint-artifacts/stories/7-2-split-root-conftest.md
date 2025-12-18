# Story 7.2: Split Root conftest.py (857 LOC -> <500 LOC per file)

**Epic:** 7 - Technical Debt & Code Quality
**Sprint Change Proposal:** SCP-2025-12-10-002
**Status:** Drafted
**Priority:** P0 (Critical - Enables Test Infrastructure Maintainability)
**Estimated Effort:** 1 day
**Actual Effort:** TBD

---

## User Story

As a developer, I want `tests/conftest.py` to be split into organized modules under 500 LOC each, so that AI assistants can comprehend the full fixture context and pytest configuration is easier to maintain.

---

## Context

The `tests/conftest.py` file is currently **857 lines**, exceeding the 500 LOC limit established for optimal AI comprehension. This file contains critical test infrastructure that affects the entire test suite.

### Why This File?

Per the File Size Refactoring Briefing (`docs/analysis/file-size-refactoring-briefing.md`):

1. **Core test infrastructure** - All tests depend on root conftest.py for environment setup and shared fixtures
2. **Exceeds hard limit** - At 857 LOC, it's 71% over the ideal limit (500 LOC)
3. **Clear split boundaries** - Logical groups of fixtures and hooks make natural module boundaries

### Current Structure Analysis (857 LOC)

| Component | Lines | Purpose |
|-----------|-------|---------|
| **Environment Setup** | ~60 | APP_ENV, TESTING, PostgreSQL env vars |
| **Session Fixtures** | ~120 | configure_test_environment, session_test_settings, mock_mistral_api_globally |
| **Mock Client Fixtures** | ~60 | mock_qdrant_client, mock_claude_client |
| **Sample Data Fixtures** | ~40 | sample_document_metadata, sample_chunk |
| **Mistral Mock Helpers** | ~300 | generate_mock_sql, mock_mistral_client fixture |
| **Pytest Hooks** | ~150 | pytest_addoption, pytest_configure, pytest_collection_modifyitems |
| **Performance Monitoring** | ~75 | pytest_sessionstart, pytest_sessionfinish |
| **Imports/Comments** | ~52 | Module documentation and imports |

---

## Acceptance Criteria

### AC1: File Size Reduction
**Given** the root `tests/conftest.py` file exceeds 500 LOC (currently 857)
**When** the refactoring is complete
**Then**:
- [ ] `tests/conftest.py` reduced to <300 LOC (core only)
- [ ] All new modules are <500 LOC each
- [ ] Ideal target: 150-300 LOC per module

### AC2: New Module Structure
**Given** fixtures are currently monolithic in root conftest
**When** creating the new modular structure
**Then**:
- [ ] Create `tests/fixtures/` directory (if not exists)
- [ ] Split into organized modules:
  - `tests/conftest.py` (~200 LOC) - Core fixtures, env setup, pytest_plugins declaration
  - `tests/fixtures/mock_clients.py` (~120 LOC) - Mock Qdrant, Claude, Mistral fixtures
  - `tests/fixtures/mistral_mock_helpers.py` (~300 LOC) - SQL generation mock logic
  - `tests/fixtures/sample_data.py` (~80 LOC) - Sample document metadata, chunks
  - `tests/fixtures/pytest_hooks.py` (~150 LOC) - Custom pytest hooks and options
  - `tests/fixtures/performance_monitoring.py` (~75 LOC) - Session timing/budget checks

### AC3: Functionality Preserved
**Given** the existing test suite has ~372 passing tests
**When** fixture extraction is complete
**Then**:
- [ ] All existing tests pass unchanged
- [ ] No behavior changes to fixture logic
- [ ] All fixtures remain discoverable by pytest
- [ ] pytest hooks still execute correctly

### AC4: Shared Imports Organized
**Given** fixtures will be distributed across multiple modules
**When** organizing imports and dependencies
**Then**:
- [ ] Common imports consolidated appropriately
- [ ] No circular import issues
- [ ] pytest_plugins list updated to load new fixture modules

### AC5: CI Compatibility
**Given** CI pipeline depends on pytest test discovery
**When** running in GitHub Actions
**Then**:
- [ ] All tests discoverable by pytest
- [ ] No changes to test markers behavior
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
tests/
  conftest.py                     # ~200 LOC - Core env setup, pytest_plugins
  fixtures/
    __init__.py                   # Empty or minimal re-exports
    mock_clients.py               # ~120 LOC - Mock Qdrant, Claude fixtures
    mistral_mock_helpers.py       # ~300 LOC - SQL generation mock logic
    sample_data.py                # ~80 LOC - Sample metadata, chunks
    pytest_hooks.py               # ~150 LOC - pytest_addoption, pytest_configure, etc.
    performance_monitoring.py     # ~75 LOC - Session timing hooks
    database_fixtures.py          # (already exists, ~200 LOC)
```

### pytest_plugins Configuration

The root conftest.py will declare pytest_plugins to load fixture modules:

```python
# tests/conftest.py
"""Root pytest configuration for RAGLite tests."""

# Environment setup MUST happen before any raglite imports
import os
os.environ["APP_ENV"] = "test"
os.environ["TESTING"] = "true"
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_DB"] = "raglite_ci"
os.environ["POSTGRES_USER"] = "raglite_ci"
os.environ["POSTGRES_PASSWORD"] = "raglite_ci"
os.environ.setdefault("MISTRAL_API_KEY", "test-mistral-api-key-for-ci")

# Force reload Settings singleton after env vars set
import raglite.shared.config
from raglite.shared.config import Settings
raglite.shared.config.settings = Settings()

# Load fixture modules via pytest_plugins
pytest_plugins = [
    "tests.fixtures.database_fixtures",
    "tests.fixtures.mock_clients",
    "tests.fixtures.sample_data",
    "tests.fixtures.performance_monitoring",
]

# Core fixtures defined in this file...
```

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `conftest.py` | Environment setup, session config fixture, safety guard integration |
| `mock_clients.py` | Mock Qdrant, Claude, Mistral client fixtures |
| `mistral_mock_helpers.py` | SQL generation mock logic (extracted from mock_mistral_api_globally) |
| `sample_data.py` | sample_document_metadata, sample_chunk fixtures |
| `pytest_hooks.py` | pytest_addoption, pytest_configure, pytest_collection_modifyitems |
| `performance_monitoring.py` | pytest_sessionstart, pytest_sessionfinish, timing helpers |

### Hook Loading Strategy

Pytest hooks must be in conftest.py or loaded via pytest plugins. The hooks module will be loaded via pytest_plugins:

```python
# In tests/conftest.py
pytest_plugins = [
    # ... other plugins
    "tests.fixtures.pytest_hooks",
]
```

**IMPORTANT:** The hooks module exports hook functions at module level, and pytest auto-discovers them when loaded via pytest_plugins.

---

## Implementation Tasks

### Task 1: Create Module Structure (AC2)
- [ ] Create `tests/fixtures/` directory if not exists
- [ ] Create `tests/fixtures/__init__.py` file
- [ ] Verify directory structure

### Task 2: Extract Mock Clients (AC1, AC2)
- [ ] Create `tests/fixtures/mock_clients.py`
- [ ] Move mock_qdrant_client fixture
- [ ] Move mock_claude_client fixture
- [ ] Move mock_mistral_api_globally fixture (references mistral_mock_helpers)
- [ ] Move mock_mistral_client fixture
- [ ] Verify tests pass: `pytest tests/unit/ -v --collect-only`

### Task 3: Extract Mistral Mock Helpers (AC1, AC2)
- [ ] Create `tests/fixtures/mistral_mock_helpers.py`
- [ ] Move generate_mock_sql function
- [ ] Move generate_mock_metadata function
- [ ] Move generate_query_aware_sql function
- [ ] Update imports in mock_clients.py
- [ ] Verify tests pass

### Task 4: Extract Sample Data Fixtures (AC1, AC2)
- [ ] Create `tests/fixtures/sample_data.py`
- [ ] Move sample_document_metadata fixture
- [ ] Move sample_chunk fixture
- [ ] Verify tests pass

### Task 5: Extract Pytest Hooks (AC1, AC2)
- [ ] Create `tests/fixtures/pytest_hooks.py`
- [ ] Move pytest_addoption function
- [ ] Move pytest_configure function
- [ ] Move pytest_collection_modifyitems function
- [ ] Move _timed_fixture helper
- [ ] Verify pytest options work: `pytest --help | grep run-slow`

### Task 6: Extract Performance Monitoring (AC1, AC2)
- [ ] Create `tests/fixtures/performance_monitoring.py`
- [ ] Move pytest_sessionstart function
- [ ] Move pytest_sessionfinish function
- [ ] Move _session_start_time global
- [ ] Verify performance monitoring works

### Task 7: Update Root conftest.py (AC1, AC4)
- [ ] Update pytest_plugins list to load new modules
- [ ] Keep only core environment setup
- [ ] Keep configure_test_environment fixture
- [ ] Keep session_test_settings fixture
- [ ] Keep test_settings fixture
- [ ] Verify conftest.py is <300 LOC

### Task 8: Validate Imports (AC3, AC4)
- [ ] Check for circular import issues
- [ ] Verify all fixture imports work
- [ ] Test with fresh pytest invocation

### Task 9: Run Full Test Suite (AC3, AC5)
- [ ] Run: `pytest tests/ -v --collect-only` (verify discovery)
- [ ] Run: `pytest tests/unit/ -v` (verify unit tests)
- [ ] Run: `pytest tests/integration/ --skip-ingestion -v` (verify integration tests)
- [ ] Verify CI pipeline passes

### Task 10: File Size Validation (AC1)
- [ ] Run: `wc -l tests/conftest.py tests/fixtures/*.py`
- [ ] Verify all files <500 LOC
- [ ] Document final line counts in completion notes

---

## Dev Notes

### Refactoring Rules

Per [File Size Refactoring Briefing](../../analysis/file-size-refactoring-briefing.md):

1. **Extract one module at a time** - Run tests after each extraction
2. **Do NOT batch changes** - Incremental commits keep changes reviewable
3. **Run full test suite** - Prevent hidden regressions
4. **Preserve hook discovery** - pytest hooks must be loadable

### Test Structure Architecture

Per `docs/architecture/3-repository-structure-monolithic.md`:
- Test fixtures should be organized in `tests/fixtures/` for modularity
- Root `conftest.py` should contain core environment setup and pytest_plugins declarations
- Fixture modules load via pytest_plugins for automatic discovery

Per `docs/architecture/6-complete-reference-implementation.md`:
- Fixtures use session/function scope appropriately
- Mock clients follow standard fixture pattern with proper cleanup
- Test environment setup MUST happen before raglite imports

### Pytest Plugin Loading

Pytest loads fixtures and hooks from:
1. `conftest.py` files in test directories
2. Modules listed in `pytest_plugins` variable

Hooks (pytest_addoption, pytest_configure, etc.) MUST be either:
- Defined in conftest.py directly, OR
- In a module listed in pytest_plugins

### Commands for Validation

```bash
# Count lines in all fixture files
wc -l tests/conftest.py tests/fixtures/*.py

# Verify pytest options work
pytest --help | grep -E "(run-slow|skip-ingestion|enforce-isolation)"

# Verify fixture discovery
pytest tests/unit/ --collect-only 2>&1 | grep -c "test_"

# Verify hooks run (look for session fixture messages)
pytest tests/unit/test_config.py -v -s 2>&1 | head -50

# Full unit test suite
pytest tests/unit/ -v

# Check for import errors
python -c "from tests.fixtures.mock_clients import *; print('OK')"
python -c "from tests.fixtures.sample_data import *; print('OK')"
```

### Incremental Commit Strategy

```bash
# Commit after each module extraction
git commit -m "refactor(tests): extract mock_clients to separate module"
git commit -m "refactor(tests): extract mistral_mock_helpers to separate module"
git commit -m "refactor(tests): extract sample_data to separate module"
git commit -m "refactor(tests): extract pytest_hooks to separate module"
git commit -m "refactor(tests): extract performance_monitoring to separate module"
git commit -m "refactor(tests): update root conftest.py to load fixture modules"
```

### Risk Mitigation

- **Hook discovery**: Ensure pytest_plugins loads hook modules BEFORE other fixtures
- **Import order**: Environment vars must be set BEFORE raglite imports
- **Circular imports**: mock_clients depends on mistral_mock_helpers, not vice versa
- **Fixture scope**: Session-scoped fixtures must remain in correct module

---

## Testing Requirements

### Before Refactoring
- Run: `pytest tests/ --collect-only -q | tail -5`
- Record: Total test count (expected: ~372 tests)
- Record: `wc -l tests/conftest.py` (expected: 857 LOC)

### After Each Extraction
- Run: `pytest tests/unit/ -v --tb=short`
- Verify: No failures, no import errors
- Verify: pytest options still work

### Final Validation
- Run: `pytest tests/ -v --collect-only`
- Run: `pytest tests/unit/ -v`
- Run: `pytest tests/integration/ --skip-ingestion -v`
- Verify: Full test suite green
- Verify: CI pipeline passes
- Verify: `wc -l tests/conftest.py` < 300 LOC

---

## Dependencies

- **Story 7.1** (split_test_external_data_clients) - Independent, can run in parallel
- **tests/fixtures/database_fixtures.py** - Already exists, will remain unchanged

---

## Success Metrics

1. **File size compliance**: Root conftest.py <300 LOC, all new files <500 LOC
2. **Test count preservation**: Same number of tests before/after (~372)
3. **Fixture discovery**: All fixtures remain discoverable
4. **Hook execution**: All pytest hooks execute correctly
5. **CI green**: All pipelines pass

---

## References

- [File Size Refactoring Briefing](../../analysis/file-size-refactoring-briefing.md)
- [File Size Limits Rule](../../.claude/rules/file-size-limits.md)
- [Testing Guidelines](../../tests/CLAUDE.md)
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
- `tests/conftest.py` (857 LOC -> ~200 LOC)

**Files to Create:**
- `tests/fixtures/__init__.py` (~5 LOC)
- `tests/fixtures/mock_clients.py` (~120 LOC)
- `tests/fixtures/mistral_mock_helpers.py` (~300 LOC)
- `tests/fixtures/sample_data.py` (~80 LOC)
- `tests/fixtures/pytest_hooks.py` (~150 LOC)
- `tests/fixtures/performance_monitoring.py` (~75 LOC)

### Change Log

TBD
