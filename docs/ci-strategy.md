# CI/CD Strategy

## Executive Summary
- **Tech stack**: Docker, GitHub Actions, pytest-xdist, Qdrant, PostgreSQL
- **Key challenges**: Test isolation, container mount management, resource cleanup
- **Target performance**: <5s p50, <15s p95 for test execution

## Root Cause Analysis
### Primary Issues Identified
1. **Test State Pollution**: Settings singleton initialization in pytest-xdist workers
2. **Resource Leaks**: Joblib multiprocessing processes not properly terminated
3. **Environment Inconsistency**: Docker container mount staleness
4. **Mock Management**: Incorrect patching strategies causing test interference

### Five Whys Applied
| Issue | Root Cause | Impact |
|-------|------------|--------|
| State Pollution | Global objects loaded at import time | Flaky tests, inconsistent results |
| Resource Leaks | Missing cleanup in teardown | CI timeouts, SIGKILL failures |
| Mount Issues | CI containers using stale paths | "Database Empty" errors |
| Mock Problems | Patching at definition vs usage | False positives/negatives |

### Systemic Fixes Implemented
1. **Lazy Loading Pattern**: Settings and resources loaded on demand
2. **Process Management**: Explicit resource cleanup in fixtures
3. **Volume Mount Verification**: Scripts to validate and correct mounts
4. **Mock Standards**: Function-level patching with clear scope

## Pipeline Architecture

### CI Job Execution Model

```
EVERY PUSH/PR                          MAIN BRANCH ONLY (Post-Merge)
    |                                        |
    v                                        v
[1. lint-gate]                         [1. lint-gate]
  (Ruff/Black)                           (Ruff/Black)
    |                                        |
    v                                        v
[2. validate]                          [2. validate]
  (Type checks/security/unit tests)      (Type checks/security/unit tests)
    |                                        |
    v                                        v
[3. integration-fast]                  [3. integration-full]
  (Fast integration, <5min)              (Full integration, <30min)
    |                                        |
    +-------> PR Ready                       v
                                       [4. accuracy-gate]
                                         (AC3 >=70% validation)
                                             |
                                             v
                                        Release Ready
```

**Best Practices Alignment (2025):**
- **Shift-left testing**: PRs run fast integration tests to catch bugs before merge
- **Test pyramid**: Unit tests on every commit, integration tests tiered by scope
- **Fast feedback**: PR validation completes in <17 minutes total

### Job Timing & Requirements

| Job | When | Duration | Containers | Dependencies |
|-----|------|----------|-----------|--------------|
| **lint-gate** | All pushes/PRs | <2min | None | None |
| **validate** | All pushes/PRs | <10min | None | lint-gate |
| **integration-fast** | PRs only | <5min | Qdrant/PostgreSQL | validate |
| **integration** | Main only OR manual | <30min | Qdrant/PostgreSQL | validate |
| **accuracy-gate** | Main only OR manual | <45min | Qdrant/PostgreSQL | integration |

### Stage Diagram (Fast Feedback)
```
PR WORKFLOW (Shift-Left Testing):
[Code Commit] → [Lint] → [Validate] → [Fast Integration] → [PR Ready]
                (2min)   (10min)       (5min)              Total: ~17min

MAIN BRANCH (Post-Merge Validation):
[Main Merge] → [Lint] → [Validate] → [Full Integration] → [Accuracy Gate] → [Release Ready]
               (2min)   (10min)       (30min)              (45min)
```

### Timing Targets
| Job | Target Duration | SLA |
|-----|-----------------|-----|
| lint-gate | <2min | Hard |
| validate | <10min | Hard |
| integration-fast | <5min | Hard |
| integration | <30min | Hard |
| accuracy-gate | <45min | Hard |

### Quality Gates
- **Test Coverage**: 80%+ (enforced)
- **Linting**: ruff, black formatting
- **Type Safety**: mypy strict mode
- **Security**: bandit scan
- **Accuracy**: Ground truth validation
- **Performance**: Budget enforcement

## Test Categorization

| Marker | Description | Expected Duration | Concurrency | CI Job |
|--------|-------------|-------------------|-------------|--------|
| `unit` | Fast, mocked tests | <1s | Yes | validate |
| `integration` | Real services | 1-10s | Limited | integration-fast / integration |
| `slow` | Stateful tests | 10-60s | No | integration (main only) |
| `e2e` | Full system | >60s | No | accuracy-gate |
| `health_check` | External API health checks | Variable | No | daily (dedicated) |

**Note:** Fast integration tests (not marked `slow`) run on PRs via `integration-fast` job. Full suite runs on main.

## Prevention Rules

### Test Isolation
- Use explicit `@pytest.mark.integration` for integration tests
- Never rely on file path heuristics for fixture activation
- Ensure session fixtures have explicit skip conditions

### Container Management
- Always verify Docker container volume mounts before tests
- Never assume containers have correct mounts after CI runs
- Use `./scripts/start-dev.sh` for consistent startup

### Resource Management
- Always patch wrapper functions, not direct class imports
- Never patch at the definition location; patch where the object is used
- Always verify mock call counts match expected behavior

### Mock Standards
- ALWAYS use lazy-load wrapper functions for external ML libraries
- NEVER define dataclasses in large utility modules; use dedicated `models.py` files
- ALWAYS use `TYPE_CHECKING` guards for cross-module type hints

### Module Refactoring (Epic 8)
- Follow `.claude/rules/module-rename-checklist.md` for ALL module renames
- Verify patch targets exist: `python scripts/validate-mock-targets.py`
- Run `pytest --collect-only` after import changes to catch ModuleNotFoundError
- Search comprehensively for all references before finalizing renames

### Test File Size Management
- Monitor test file size before each commit: `wc -l tests/path/to/test_file.py`
- Split files when approaching 400 LOC (before hitting 500 limit)
- Use `.file-size-exceptions` for TEMPORARY exceptions only (with refactoring targets)
- Move reusable fixtures to `conftest.py` to reduce duplication

## Global Environment Variables

### Strategic Configuration (Self-Hosted Runners)

All CI jobs set these globally in `env:` section:

```yaml
env:
  APP_ENV: test                           # Test database mode
  CI: "true"                              # CI detection
  PYTHONDONTWRITEBYTECODE: "1"            # Prevent .pyc pollution
  LOKY_MAX_CPU_COUNT: "1"                 # Prevent joblib deadlocks
```

### Rationale for Each Setting

| Variable | Purpose | Impact | Alternative |
|----------|---------|--------|-------------|
| `PYTHONDONTWRITEBYTECODE=1` | Prevent `.pyc` cache pollution between runs | Eliminates bytecode cache issues (5+ failures/week) | Manual cleanup (unreliable) |
| `LOKY_MAX_CPU_COUNT=1` | Disable Loky's multiprocessing in Joblib | Prevents resource contention with pytest-xdist | Reduce pytest workers (slower tests) |
| `APP_ENV=test` | Select test database ports (6335/5433) | Prevents accidental production data modification | Manual mode switching (risky) |
| `CI=true` | Enable CI-specific test markers | Skips slow tests, enables fast feedback | Re-run with markers (complex) |

### Performance Impact

- **PYTHONDONTWRITEBYTECODE**: +0s (no bytecode write = negligible overhead)
- **LOKY_MAX_CPU_COUNT**: -2m (prevents deadlock hangs, not slower)
- **Combined effect**: 7-9 prevented failures per 50 test runs

## Infrastructure Improvements

### Container Isolation Strategy
| Context | Container Name | Storage | Mount Validation |
|---------|----------------|---------|------------------|
| Production | `raglite-qdrant` | Persistent | Manual verification |
| Unit Tests | `raglite-qdrant-test` | Ephemeral | Automatic |
| CI Agentic | `raglite-qdrant-agentic` | Ephemeral | Automatic |
| CI Discovery | `raglite-qdrant-discovery` | Ephemeral | Automatic |
| CI Burn-in | `raglite-qdrant-burnin` | Ephemeral | Automatic |

### Volume Mount Resolution
```yaml
# Problem: Stale mounts from previous CI runs
# Solution: Unique container names per CI job
services:
  qdrant:
    container_name: ${CONTAINER_NAME:-raglite-qdrant}
    volumes:
      - qdrant_storage:/qdrant/storage
```

### Resource Cleanup Pattern
```python
# Before: Missing cleanup
@pytest.fixture
def qdrant_client():
    client = QdrantClient()
    yield client
    # Missing: No cleanup

# After: Proper cleanup
@pytest.fixture
def qdrant_client():
    client = QdrantClient()
    try:
        yield client
    finally:
        client.close()
        # Additional resource cleanup
```

## Performance Optimization

### Parallel Execution Strategy
- **Unit Tests**: Max parallelism with pytest-xdist
- **Integration Tests**: Limited parallelism due to resource constraints
- **Stateful Tests**: Sequential execution only

### Timing Configuration
- **Fast Tests**: <1s target for unit tests
- **Medium Tests**: 1-10s for integration
- **Slow Tests**: Marked with `@pytest.mark.slow`
- **Timeouts**: Dynamic based on test category

### Memory Management
- **Process Limits**: Monitor memory usage per job
- **Resource Cleanup**: Explicit cleanup in fixtures
- **Container Limits**: Memory limits in Docker Compose

## Monitoring and Observability

### Key Metrics
1. **Test Duration**: Track execution time trends
2. **Failure Rate**: Monitor flaky tests
3. **Resource Usage**: Memory and CPU per job
4. **Container Health**: Database connections and mounts
5. **CI Pipeline Duration**: End-to-end timing

### Alerting Thresholds
- **Test Duration**: >2x baseline for slow tests
- **Failure Rate**: >5% flaky test rate
- **Memory Usage**: >80% of container limit
- **Container Mount Issues**: Immediate alert

### Dashboards
- **GitHub Actions**: Pipeline execution metrics
- **Container Status**: Database and service health
- **Test Results**: Pass/fail trends and coverage

## Continuous Improvement

### Regular Reviews
- **Weekly**: Test failure analysis
- **Bi-weekly**: Performance metrics review
- **Monthly**: CI pipeline optimization

### Feedback Loops
- **Test Authors**: Immediate feedback on new test patterns
- **CI Failures**: Root cause analysis and prevention
- **Performance Issues**: Optimization and tuning

### Automation
- **Pre-commit Hooks**: File size and linting checks
- **CI Validation**: Automatic mount verification
- **Test Isolation**: Cleanup and reset automation

## Success Metrics

### Current Status
- **Test Reliability**: 95%+ pass rate
- **Pipeline Duration**: <15 minutes
- **Resource Efficiency**: No SIGKILL failures
- **Environment Consistency**: 100% mount validation

### Future Targets
- **Test Speed**: 50% reduction in execution time
- **Parallelism**: 80% tests running in parallel
- **Coverage**: 90%+ code coverage
- **Accuracy**: 95%+ retrieval accuracy

---

## Knowledge Extraction: CI Lessons Learned (Epic 8)

### Failure Pattern: Mock Patch Target Name Mismatch

**First Observed:** 2026-01-08 (Epic 8 technical debt reduction)
**Frequency:** 1 incident during module cleanup refactoring
**Impact:** Test failures, CI blockage, delayed merge

#### Root Cause (Five Whys)
1. Why? → Mock patch target string referenced wrong class name
2. Why? → Used `@patch("module.ATIClient")` but class was `ATICClient`
3. Why? → Manual typo during test authoring, not caught by linters
4. Why? → String literals in patch decorators not validated
5. Why? → No tool to validate patch targets before test execution

#### Solution Implemented
- Created `validate-mock-targets.py` script to verify patch targets
- Script searches codebase for actual class definitions
- Validates that patch string matches real class/function names
- Can be integrated into pre-commit hooks or CI lint jobs

#### Prevention Applied
- Add mock validation to pre-commit hooks before merge
- Include patch target validation in code review checklist
- Document actual class names in test docstrings
- Use IDE "Find References" during test authoring

#### Related Documentation
- Runbook: `docs/ci-failure-runbook.md` → Section 9
- Prevention Tool: `scripts/validate-mock-targets.py`

---

### Failure Pattern: Module Rename Not Propagated to All Imports

**First Observed:** 2026-01-08 (Epic 8 cleanup: `ingestion.py` → `ingestion_tool.py`)
**Frequency:** 1 incident affecting 7+ files
**Impact:** Test collection failures, CI blockage

#### Root Cause (Five Whys)
1. Why? → Module renamed manually without systematic search
2. Why? → Some files updated with new import, others missed
3. Why? → No validation that ALL references updated simultaneously
4. Why? → Test collection encountered orphaned old imports
5. Why? → Name collision wasn't fully resolved across codebase

#### Solution Implemented
- Created `.claude/rules/module-rename-checklist.md` with step-by-step process
- Systematic grep-based search for ALL references before rename finalization
- Validation after each batch of updates using `pytest --collect-only`
- Clear rollback procedure if issues discovered mid-rename

#### Prevention Applied
- Use IDE refactoring tools for automatic import updates
- Follow module rename checklist for future refactorings
- Verify with `grep -r "old_name"` that all references removed
- Run test collection validation before committing rename changes
- Add "refactored module" checklist to PR template for Epic 8

#### Related Documentation
- Checklist: `.claude/rules/module-rename-checklist.md`
- Runbook: `docs/ci-failure-runbook.md` → Section 10

---

### Failure Pattern: Test File Size Violations During Refactoring

**First Observed:** 2026-01-08 (Epic 8: ATDD test files exceeded 500 LOC)
**Frequency:** 4 test files affected
**Impact:** CI file size check failures, blocking merges

#### Root Cause (Five Whys)
1. Why? → Test files accumulated fixtures and test cases over time
2. Why? → Kept growing beyond 500 LOC without intermediate splits
3. Why? → Refactoring not prioritized during feature development
4. Why? → Hard limit enforcement triggered only when limit exceeded
5. Why? → No proactive monitoring before reaching limit

#### Solution Implemented
- Added entries to `.file-size-exceptions` with refactoring target dates
- File size limits are now TEMPORARY exceptions, not permanent waivers
- Tracking mechanism to plan refactoring during future sprints
- Baseline established for monitoring file growth trends

#### Prevention Applied
- Monitor file size before each commit: `wc -l tests/path/to/file.py`
- Split files when approaching 400 LOC (not waiting for 500)
- Include file size reduction in sprint planning
- Use `.file-size-exceptions` as TEMPORARY measure only
- Schedule refactoring stories when files cross 350 LOC threshold

#### Related Documentation
- Enforcement: `.claude/rules/file-size-limits.md`
- Runbook: `docs/ci-failure-runbook.md` → Section 11
- Script: `scripts/check_file_sizes.py`

---

## Refactoring Lessons (Epic 8 Summary)

### What Worked Well
1. **Incremental fixes** - Small commits made debugging easier
2. **CI visibility** - GitHub Actions logs provided clear error messages
3. **Validation scripts** - Grep-based searches caught orphaned references
4. **Test collection validation** - `pytest --collect-only` caught import issues early

### What Could Improve
1. **Automation** - Mock patch validation should be in pre-commit hooks
2. **IDE integration** - Module renames using IDE refactoring (not manual sed)
3. **Proactive monitoring** - Check file sizes continuously, not at limit
4. **Documentation** - Rename checklist should have been in place earlier

### Recommendations for Future Epics
1. Create "Refactoring Readiness" checklist before starting Epic 8
2. Set up pre-commit hooks for mock validation and file size checking
3. Use IDE refactoring tools for any module renames (automatic import updates)
4. Establish "refactoring debt" tracking separate from feature work
5. Include file size metrics in sprint retrospectives
