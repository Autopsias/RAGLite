# ATDD Checklist: Story 7b-5 Model Selection Slash Commands & Subagent

## Story Information

- **Story ID:** 7b-5
- **Epic:** 7b - Intelligent Model Selection Framework
- **Priority:** P0
- **Status:** TDD RED Phase (Tests Created, Implementation Pending)
- **Created:** 2024-12-21
- **Dependencies:** 7b-3 (Per-Variable Model Selection via Cross-Validation), 7b-4 (Model Selection Cache in PostgreSQL)

## Acceptance Criteria Summary

| AC ID | Description | Unit Tests | Status |
|-------|-------------|------------|--------|
| AC-7b.5.1 | Slash command file with argument-hint, description, --all, --force, --dry-run flags | 7 tests | RED |
| AC-7b.5.2 | Model-selection-executor subagent file with name, description, tools | 6 tests | RED |
| AC-7b.5.3 | `run_batch_model_selection()` function with correct signature and ALL_VARIABLES | 15 tests | RED |
| AC-7b.5.4 | Parallel execution with 4 workers (default) using asyncio.Semaphore | 2 tests | RED |
| AC-7b.5.5 | Cache results in PostgreSQL via cache_model_selection() | 1 test | RED |
| AC-7b.5.6 | Generate JSON + Markdown reports | 5 tests | RED |
| AC-7b.5.7 | Progress logging with [N/total] format and summary | 2 tests | RED |
| AC-7b.5.8 | Runtime less than 120 minutes (performance test) | 1 test (skipped) | RED |

**Total Tests:** 39+ unit tests (plus 2 error handling tests)

---

## Test Files Created

### Unit Tests
- **File:** `tests/unit/test_model_selection_job.py`
- **Count:** 41 tests
- **Markers:** `@pytest.mark.unit`

---

## Detailed Test Coverage

### AC-7b.5.1: Slash Command Definition

**Unit Tests (tests/unit/test_model_selection_job.py):**
- [ ] TEST-AC-7b.5.1.1: `.claude/commands/model-selection.md` file exists
- [ ] TEST-AC-7b.5.1.2: Slash command has argument-hint in frontmatter
- [ ] TEST-AC-7b.5.1.3: Slash command has allowed-tools in frontmatter
- [ ] TEST-AC-7b.5.1.4: Slash command documents single variable execution
- [ ] TEST-AC-7b.5.1.5: Slash command documents --all flag
- [ ] TEST-AC-7b.5.1.6: Slash command documents --force flag
- [ ] TEST-AC-7b.5.1.7: Slash command documents --dry-run flag

### AC-7b.5.2: Model-Selection-Executor Subagent

**Unit Tests:**
- [ ] TEST-AC-7b.5.2.1: `.claude/agents/model-selection-executor.md` file exists
- [ ] TEST-AC-7b.5.2.2: Subagent has name and description in frontmatter
- [ ] TEST-AC-7b.5.2.3: Subagent has tools in frontmatter
- [ ] TEST-AC-7b.5.2.4: Subagent has model in frontmatter
- [ ] TEST-AC-7b.5.2.5: Subagent documents batch processing steps
- [ ] TEST-AC-7b.5.2.6: Subagent documents the 20 variables to process

### AC-7b.5.3: run_batch_model_selection() Python Function

**Unit Tests:**
- [ ] TEST-AC-7b.5.3.1: model_selection_job.py is importable
- [ ] TEST-AC-7b.5.3.2: run_batch_model_selection function exists
- [ ] TEST-AC-7b.5.3.3: ALL_VARIABLES constant has 20 variables
- [ ] TEST-AC-7b.5.3.4: ALL_VARIABLES contains key financial variables (ebitda, revenue, etc.)
- [ ] TEST-AC-7b.5.3.5: ALL_VARIABLES contains key external variables (ttf_gas, co2_eua_price, etc.)
- [ ] TEST-AC-7b.5.3.6: Function has variables parameter
- [ ] TEST-AC-7b.5.3.7: Function has workers parameter
- [ ] TEST-AC-7b.5.3.8: Function has force_refresh parameter
- [ ] TEST-AC-7b.5.3.9: Function has output_dir parameter
- [ ] TEST-AC-7b.5.3.10: Function is async
- [ ] TEST-AC-7b.5.3.11: run_single_variable_selection function exists
- [ ] TEST-AC-7b.5.3.12: run_single_variable_selection is async
- [ ] TEST-AC-7b.5.3.13: run_single_variable_selection has dry_run parameter
- [ ] TEST-AC-7b.5.3.14: run_single_variable_selection has force_refresh parameter
- [ ] TEST-AC-7b.5.3.15: CANDIDATE_MODELS is imported and accessible

### AC-7b.5.4: Parallel Execution (4 Workers)

**Unit Tests:**
- [ ] TEST-AC-7b.5.4.1: Default workers parameter is 4
- [ ] TEST-AC-7b.5.4.2: Semaphore limits concurrent executions

### AC-7b.5.5: Cache Results in PostgreSQL

**Unit Tests:**
- [ ] TEST-AC-7b.5.5.1: cache_model_selection called for each successful result

### AC-7b.5.6: Generate JSON + Markdown Report

**Unit Tests:**
- [ ] TEST-AC-7b.5.6.1: _generate_reports function exists
- [ ] TEST-AC-7b.5.6.2: _generate_reports is async
- [ ] TEST-AC-7b.5.6.3: JSON and Markdown reports created in output_dir
- [ ] TEST-AC-7b.5.6.4: JSON report contains required fields (timestamp, runtime_minutes, results)
- [ ] TEST-AC-7b.5.6.5: Markdown report contains summary table

### AC-7b.5.7: Progress Logging with Status Updates

**Unit Tests:**
- [ ] TEST-AC-7b.5.7.1: Progress printed with [N/total] format
- [ ] TEST-AC-7b.5.7.2: Summary section printed at completion

### AC-7b.5.8: Runtime Performance (P2)

**Unit Tests (skipped for regular runs):**
- [ ] TEST-AC-7b.5.8.1: Full batch completes in <120 minutes

### Error Handling Tests

**Unit Tests:**
- [ ] TEST-ERR-1: Individual variable failures don't stop batch processing
- [ ] TEST-RET-1: run_batch_model_selection returns dict of results

---

## Implementation Artifacts Required

### Files to Create

1. **Slash Command:** `.claude/commands/model-selection.md`
   - YAML frontmatter with argument-hint, description, allowed-tools
   - Single variable execution documentation
   - --all flag delegation to subagent
   - --force and --dry-run flag documentation

2. **Subagent:** `.claude/agents/model-selection-executor.md`
   - YAML frontmatter with name, description, tools, model
   - Variables list documentation (20 variables)
   - Execution steps documentation
   - Error handling documentation

3. **Python Module:** `raglite/forecasting/model_selection_job.py`
   - ALL_VARIABLES constant (20 variables)
   - run_batch_model_selection() async function
   - _generate_reports() async helper
   - run_single_variable_selection() async helper

### Module Dependencies

```python
# Required imports in model_selection_job.py
from raglite.forecasting.model_selection import (
    select_best_model,
    ModelSelectionResult,
    CANDIDATE_MODELS,
)
from raglite.external_data.storage import cache_model_selection
```

---

## Run Commands

```bash
# Run unit tests (expected to FAIL in RED phase)
uv run pytest tests/unit/test_model_selection_job.py -v

# Run specific AC tests
uv run pytest tests/unit/test_model_selection_job.py -v -k "AC-7b.5.1"
uv run pytest tests/unit/test_model_selection_job.py -v -k "AC-7b.5.3"

# Run all tests for this story (excluding slow/skipped)
uv run pytest tests/unit/test_model_selection_job.py -v -m "not slow"

# Check test count
uv run pytest tests/unit/test_model_selection_job.py --collect-only | grep "test session starts" -A 100 | grep "test_"
```

---

## TDD Workflow Status

- [x] **RED Phase:** Acceptance tests created and expected to fail
- [ ] **GREEN Phase:** Implementation complete, all tests passing
- [ ] **REFACTOR Phase:** Code cleaned up, edge cases handled

---

## Variables List Reference (20 Total)

| Category | Variables | Count |
|----------|-----------|-------|
| Financial | revenue, turnover, ebitda, variable_cost | 4 |
| Energy | electricity_cost, thermal_cost | 2 |
| Volume | sales_volume, capacity_utilization | 2 |
| Pricing | avg_selling_price | 1 |
| External | ttf_gas, api2_coal, diesel, eurostat_electricity | 4 |
| Macro | gdp_growth, inflation, euribor_3m | 3 |
| Construction | construction_output, building_permits, construction_confidence | 3 |
| Carbon | co2_eua_price | 1 |
| **Total** | | **20** |

---

## Notes

1. Tests are designed to fail initially because the implementation does not exist
2. Unit tests use mocking to avoid real model selection execution
3. File existence tests check for Claude Code configuration files
4. Performance test (AC-7b.5.8) is marked as skipped for regular runs
5. Error handling tests verify batch continues after individual failures
6. Report generation tests verify both JSON and Markdown output formats
