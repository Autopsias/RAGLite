# CI/CD Strategy

## Executive Summary (Updated 2025-01-12)

**Strategic Analysis Finding:** 80% of recent commits are CI fixes - extremely high churn driven by Colima VM instability on self-hosted macOS runner.

- **Tech stack**: Docker (via Colima on macOS), GitHub Actions, pytest-xdist, Qdrant, PostgreSQL
- **Primary challenge**: Colima daemon socket becomes inaccessible between jobs (self-hosted runner issue)
- **Secondary challenges**: Test isolation, container mount management, resource cleanup
- **Target performance**: <5s p50, <15s p95 for test execution
- **Stability target**: <10% of commits are CI fixes (down from 80%)

## Root Cause Analysis (Updated 2025-01-12)

### Primary Issue: Colima VM Instability (80% of CI failures)

**Problem:** Docker daemon socket at `~/.colima/default/docker.sock` becomes inaccessible between GitHub Actions jobs on self-hosted macOS runner.

**Symptoms:**
- Integration tests fail with "Connection refused" on random jobs
- Same test passes on next retry (suggests transient state)
- `colima status` shows inconsistent state between jobs
- No automatic recovery mechanism

**Root Cause (Five Whys):**
1. Why do tests fail? → Docker socket becomes inaccessible
2. Why does socket become inaccessible? → Colima VM stops or becomes unresponsive
3. Why does VM stop? → No health check or auto-recovery between jobs
4. Why no recovery? → Missing pre-flight validation before container operations
5. Why missing validation? → Self-hosted runner requires manual setup (unlike GitHub-hosted)

**Impact Timeline:**
- 16 of 20 recent commits (80%) are CI fixes
- All failures are Docker/Colima connectivity related
- Same root cause repeated across different test categories
- Pattern emerged since switching to self-hosted runner

### Secondary Issues (Still Active, Lower Priority)

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

## Resource-Based Sharding Strategy (Updated 2026-01-22)

### Problem: Embedding Model Memory in Parallel Execution

Embedding model (Fin-E5, 2GB) cannot run in parallel on 4GB VM:
- 4 workers × 2GB model = 8GB needed
- 4GB VM has only 768MB free after DB containers
- Result: OOM kill, SIGKILL on worker processes

### Solution: Different Shard Allocations

**Retrieval Shard (8GB VM, 2 workers):**
- Contains: Embedding-dependent tests (parallel ingestion, retrieval, hybrid search)
- Memory profile: High (2GB embedding model + parallelization)
- Worker count: 2 (allows embedding model in each worker, 4GB per worker)
- Timeout: 45 minutes (embedding load + parallel ingestion)

**MCP Shard (4GB VM, 4 workers):**
- Contains: Stateless MCP tests (no embedding model)
- Memory profile: Low (no embedding required)
- Worker count: 4 (safe on 4GB VM, no embedding overhead)
- Timeout: 15 minutes (fast tests)

### Test Classification

| Test Category | Embedding Required | Shard | Workers | Timeout |
|---|---|---|---|---|
| Parallel Ingestion | Yes | Retrieval | 2 | 45min |
| Retrieval Core | Yes | Retrieval | 2 | 45min |
| Hybrid Search | Yes | Retrieval | 2 | 45min |
| MCP Tools | No | MCP | 4 | 15min |
| MCP Analytical | No | MCP | 4 | 15min |
| Unit Tests (no embedding) | No | Validate | auto | 10min |

### Validation

**Pre-commit:**
```bash
python scripts/validate-xdist-markers.py
# Ensures all embedding tests marked @pytest.mark.xdist_group(name="embedding_model")
```

**CI Configuration:**
```bash
grep "retrieval.*shard" .github/workflows/ci.yml | grep workers
# Expected: workers: 2

grep "mcp.*shard" .github/workflows/ci.yml | grep workers
# Expected: workers: 4
```

---

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

## Implementation Roadmap: Colima Reliability (Updated 2025-01-12)

### Phase 1: Pre-Flight Validation (P0 - Immediate)
**Target:** Prevent 80% of CI failures via health checks before container operations

**Actions:**
1. Create `scripts/ensure-colima-health.sh` script:
   - Check if Docker daemon responds: `docker info`
   - If unavailable: restart Colima with `colima stop && colima start`
   - Verify socket accessibility: `ls ~/.colima/default/docker.sock`
   - Create symlink: `sudo ln -s ~/.colima/default/docker.sock /var/run/docker.sock`
   - Wait for Docker readiness with exponential backoff (max 60s)

2. Add to CI workflow (`lint-gate` job):
   ```yaml
   - name: Validate Colima Health
     run: ./scripts/ensure-colima-health.sh
   ```

3. Add to local development (`scripts/start-dev.sh`):
   - Run health check before docker-compose commands
   - Provide clear error messages if recovery fails

**Success Criteria:**
- Health check completes in <15s
- Colima auto-starts if stopped
- Socket symlink created for standard Docker path
- No timeout failures due to Docker unavailability

### Phase 2: Container Startup Resilience (P1 - Next Week)
**Target:** Improve container health check and readiness detection

**Actions:**
1. Increase health check timeout in docker-compose.yml:
   - From: 30s timeout
   - To: 60s timeout
   - Add: 5 retries before considering container unhealthy

2. Add port-in-use validation:
   - Before starting containers, check: `netstat -tuln | grep PORT`
   - If port in use, run: `docker-compose down -v` (cleanup)
   - Then retry startup

3. Verify container readiness:
   - Qdrant: `curl http://localhost:6333/health`
   - PostgreSQL: `pg_isready -h localhost -p 5432`
   - Wait for both before proceeding with tests

**Success Criteria:**
- Containers start reliably within 60s
- No "port already in use" errors
- Readiness verified before test execution

### Phase 3: Self-Hosted Runner Setup Documentation (P1 - This Week)
**Target:** Provide clear setup instructions to prevent future issues

**Actions:**
1. Document in `docs/ci-knowledge/self-hosted-runner-guide.md`:
   - One-time setup steps for macOS runner
   - Socket symlink creation
   - Colima configuration
   - Periodic health check cron job

2. Create setup script: `scripts/setup-runner.sh`
   - Installs/configures Colima
   - Creates required symlinks
   - Sets up cron job for periodic health checks

3. Add to runner onboarding checklist:
   - [ ] Run `./scripts/setup-runner.sh`
   - [ ] Verify: `colima status` shows running
   - [ ] Verify: `ls -la /var/run/docker.sock` exists
   - [ ] Run test job: `./scripts/ensure-colima-health.sh`

**Success Criteria:**
- New runners can be set up in <5 minutes
- Setup script is idempotent (safe to run multiple times)
- Documentation covers troubleshooting

### Phase 4: Monitoring and Alerting (P2 - Sprint Planning)
**Target:** Early detection of Colima issues before they affect CI

**Actions:**
1. Add periodic health check (cron job on runner):
   ```bash
   */30 * * * * /home/runner/scripts/ensure-colima-health.sh >> /tmp/colima-health.log 2>&1
   ```

2. Log Colima state to file for debugging:
   - Record timestamp, colima status, docker info output
   - Archive logs weekly

3. Add alert when health check fails:
   - Send notification to team Slack/email
   - Include Colima status and suggested fixes

**Success Criteria:**
- Health checks run every 30 minutes
- Logs available for debugging
- Team notified of persistent issues

---

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

---

## Knowledge Extraction: Test Validation Patterns (Epic 8 Strategic Analysis 2025-01-11)

### Failure Pattern: Fixture Validation Range Too Strict

**First Observed:** 2025-01-11 (Epic 8: PDF optimization fixture validation)
**Frequency:** 949-test cascade failure from single root cause
**Impact:** Test reliability dropped 52% due to non-deterministic chunk boundaries
**Strategic Impact:** Revealed systemic validation anti-pattern

#### Root Cause (Five Whys)
1. Why? → Session fixture used hardcoded chunk count range (10, 55)
2. Why? → Range was arbitrary, not based on actual chunk distribution
3. Why? → Document processors produce non-deterministic chunk boundaries
4. Why? → No tolerance mechanism for valid variations
5. Why? → Hard assertion on narrow range instead of acceptance criteria

#### Solution Applied
- Replaced hardcoded ranges with tolerance-based validation
- Calculate expected range as: baseline ± 15% tolerance
- Allow document-specific variance within tolerance band
- Example: 80 chunks baseline accepts 68-92 range

#### Prevention Applied
- Always use tolerance-based assertions for non-deterministic values
- Document baseline expectations in test comments
- Test with multiple document sizes and types
- Use parametrized tests to catch edge cases
- Never hardcode expected ranges without statistical reasoning

#### Related Documentation
- Runbook: `docs/ci-failure-runbook.md` → Section 14
- Success Metrics: `docs/ci-knowledge/success-metrics.md` → Fixture Validation

---

### Failure Pattern: API Contract Drift - Signature Changes Not Propagated

**First Observed:** 2025-01-11 (Epic 8: Epic 6 forecast API changes)
**Frequency:** 5 test methods failed from single signature change
**Impact:** Test suite blocked on API integration
**Strategic Impact:** Revealed missing API contract enforcement

#### Root Cause (Five Whys)
1. Why? → Function signature changed (added required `historical_data` parameter)
2. Why? → Test calls not updated systematically
3. Why? → Change was localized to one module (forecast execution)
4. Why? → No automated check for function signature changes
5. Why? → Tests passed locally before Epic 6 merge but failed after

#### Solution Applied
- Added API contract tests to detect signature drift early
- Updated all function calls to pass required parameters
- Removed obsolete mock patches referencing old signatures
- 11 mock patches simplified when signatures stabilized

#### Prevention Applied
- Add contract tests for public API functions (detect changes early)
- Include function signature in docstring
- Document required vs optional parameters
- Use type hints to make contracts explicit
- Run contract tests on every merge to main

#### Related Documentation
- Runbook: `docs/ci-failure-runbook.md` → Section 15
- Prevention Rules: `docs/ci-knowledge/prevention-rules.md` (add API contract validation)

---

### Failure Pattern: Config-Test Synchronization Drift

**First Observed:** 2025-01-11 (Epic 8: Metric configuration references)
**Frequency:** 3 tests failed due to missing configured metric (`cement_demand`)
**Impact:** Test initialization errors during fixture setup
**Strategic Impact:** Revealed lack of cross-file validation

#### Root Cause (Five Whys)
1. Why? → Metric removed from config.yaml but test fixtures still reference it
2. Why? → Configuration changes made without updating dependent tests
3. Why? → No validation that configured metrics exist in test expectations
4. Why? → No CI job to verify config-test synchronization
5. Why? → Metrics added/removed without cross-file impact analysis

#### Solution Applied
- Added config-test synchronization verification
- Implemented metric validation in test fixtures
- Documented metric definitions in both config and tests
- Added CI job to verify consistency

#### Prevention Applied
- Run config-test sync verification before every merge
- Include config changes in test review checklist
- Document metric definitions in both config and tests
- Use shared constants for metric names (avoid duplication)
- Add validation to config loader (verify referenced metrics exist)

#### Related Documentation
- Runbook: `docs/ci-failure-runbook.md` → Section 16
- Prevention Rules: `docs/ci-knowledge/prevention-rules.md` (add config-test sync)

---

## Test Validation Lessons Learned (Epic 8 Summary)

### Key Insights

1. **Non-Deterministic Validation Pattern**
   - Lesson: Document expected baselines, not hardcoded ranges
   - Impact: Allows for legitimate variance while catching real errors
   - Applied to: Chunk count validation, metrics accumulation tests

2. **API Contract Testing Pattern**
   - Lesson: Signature changes must be caught before test execution
   - Impact: Prevent cascade failures from missing required parameters
   - Applied to: Forecast execution, statistical calculations

3. **Configuration Synchronization Pattern**
   - Lesson: Config and test files must be validated together
   - Impact: Prevent runtime errors from drift between systems
   - Applied to: Metric definitions, feature flags, model parameters

### Recommendations for Future Development

1. **Implement Tolerance-Based Assertions**
   - Use for: measurements, counts, performance metrics
   - Document: baseline and tolerance in test comments
   - Review: quarterly to ensure tolerances remain valid

2. **Add API Contract Tests**
   - For: all public functions that change frequently
   - Check: required parameters, return types, exception contracts
   - Run: automatically on each merge to catch drift early

3. **Establish Config-Test Synchronization**
   - Verify: all configured items are tested
   - Verify: all tested items are configured
   - Frequency: before each merge to main branch
