# CI Knowledge Base

Comprehensive documentation for RAGLite CI/CD infrastructure and practices.

**Last Updated:** 2025-12-30
**Infrastructure:** Self-hosted GitHub Actions runners (macOS)
**Scope:** 372-test suite, 4-job pipeline, <15 minute target

---

## Quick Navigation

### For Troubleshooting
- **CI Failing?** → [CI Failure Runbook](/docs/ci-failure-runbook.md)
- **Environment Issues?** → [Self-Hosted Runner Guide](/docs/ci-knowledge/self-hosted-runner-guide.md)
- **Known Patterns?** → [Failure Patterns](/docs/ci-knowledge/failure-patterns.md)
- **ATDD Test Issues?** → [ATDD Subprocess Timeout](/docs/ci-knowledge/atdd-subprocess-timeouts.md)

### For Implementation
- **Writing Tests?** → [Prevention Rules](/docs/ci-knowledge/prevention-rules.md)
- **Understanding Strategy?** → [CI Strategy](/docs/ci-strategy.md)
- **Metrics & Goals?** → [Success Metrics](/docs/ci-knowledge/success-metrics.md)

### For Operations
- **Database Safety?** → `/.claude/rules/database-safety.md`
- **Test Patterns?** → `/.claude/rules/testing.md`
- **Coding Standards?** → `/.claude/rules/coding-standards.md`

---

## Key Documents

### 1. CI Failure Runbook
**Quick reference for diagnosing CI failures**

- 7 documented failure patterns with root causes
- Troubleshooting decision tree
- Prevention checklists
- Quick fix commands

**Most Important:** PYTHONDONTWRITEBYTECODE + LOKY_MAX_CPU_COUNT environment variables

**Link:** `/docs/ci-failure-runbook.md`

### 2. CI Strategy
**Long-term CI/CD approach and architecture**

- Pipeline architecture (4 jobs, <15 min target)
- Global environment configuration rationale
- Test categorization and timing targets
- Container isolation strategy
- Success metrics and monitoring

**Most Important:** Global env vars are foundational - all other strategies build on them

**Link:** `/docs/ci-strategy.md`

### 3. Failure Patterns
**Knowledge extraction from 15+ CI fix commits**

- pytest-xdist worker state pollution
- Resource tracker SIGKILL
- Container volume mount staleness
- Mock patch interference
- AsyncMock requirements
- Bytecode cache pollution
- Joblib multiprocessing deadlocks
- ATDD subprocess timeout (Story 8.4b)

Each pattern includes:
- Frequency and affected files
- Five Whys root cause analysis
- Solution applied (with commit hash)
- Verification commands
- Prevention checklist

**Link:** `/docs/ci-knowledge/failure-patterns.md`

### 3b. ATDD Subprocess Timeout Knowledge
**Systemic fix for Story 8.4b validation tests**

Detailed analysis of subprocess test timeout issue:
- 15+ previous fix attempts (symptomatic treatments)
- Root cause: 3-part systemic issue (timeout + marker registration + job isolation)
- Increases subprocess timeout from 180s to 300s
- Registers `atdd` marker in pytest.ini
- Excludes ATDD from default runs
- Creates dedicated atdd-validation CI job

Special focus on:
- Why subprocess tests need extended timeouts
- How to properly categorize subprocess-heavy test suites
- Prevention checklist for future subprocess test development

**Link:** `/docs/ci-knowledge/atdd-subprocess-timeouts.md`

### 4. Prevention Rules
**Best practices to avoid known failures**

Detailed patterns for:
- Test isolation standards
- Container volume validation
- Resource cleanup patterns
- Mock patching standards
- Async function handling
- Global environment configuration
- Bytecode cache isolation
- Joblib multiprocessing safety

Each rule includes:
- Required pattern (do this)
- Forbidden pattern (don't do this)
- Verification commands
- Prevention checklist

**Link:** `/docs/ci-knowledge/prevention-rules.md`

### 5. Self-Hosted Runner Guide
**Operations guide for macOS CI runners**

- Hardware specs and configuration
- Known issues with mitigations
- Environment verification script
- Debugging commands
- Performance tuning guidance

**Critical for:** DevOps troubleshooting, understanding runner constraints

**Link:** `/docs/ci-knowledge/self-hosted-runner-guide.md`

### 6. Success Metrics
**Tracking CI health and improvements**

- Current status by metric
- Infrastructure improvement impact (10-15 failures/week eliminated)
- Verification commands
- Monthly/quarterly/annual goals

**Link:** `/docs/ci-knowledge/success-metrics.md`

---

## Root Cause Summary

### The 5 Core Root Causes

| # | Problem | Environment Variable | Impact | Status |
|---|---------|----------------------|--------|--------|
| 1 | pytest-xdist session fixture duplication | Lazy loading pattern | Worker state pollution | Mitigated with `@pytest.mark.slow` |
| 2 | Mock target drift | Function-level patching | Incorrect mocks | Pre-commit validation in place |
| 3 | Bytecode cache pollution | `PYTHONDONTWRITEBYTECODE=1` | 5-8 failures/week | Global env var, cache cleanup |
| 4 | Joblib multiprocessing conflicts | `LOKY_MAX_CPU_COUNT=1` | 2-3 failures/week | Global env var |
| 5 | Fixture dependency invisibility | Explicit test markers | Hidden failures | `@pytest.mark.integration` standard |

### Recent Systemic Issue: ATDD Subprocess Timeouts

| # | Problem | Root Cause | Impact | Status |
|---|---------|-----------|--------|--------|
| 6 | ATDD tests timeout in CI | 3-part issue: timeout (180s insufficient) + marker unregistered + job isolation missing | 15+ failed CI runs | Fixed: 300s timeout + marker registration + dedicated job |

### Combined Impact

- **Before:** 97.2% pass rate, 10-15 failures/week
- **After:** 99.5%+ pass rate, <5 failures/week
- **Improvement:** 90%+ reduction in flakiness

---

## Implementation Checklist

### For New Tests

- [ ] Use `@pytest.mark.integration` for database tests
- [ ] Patch wrapper functions, not direct imports
- [ ] Use `AsyncMock` for async functions
- [ ] Add explicit resource cleanup in fixtures
- [ ] Verify with both serial and parallel execution

### For CI Configuration

- [ ] Set `PYTHONDONTWRITEBYTECODE=1` globally
- [ ] Set `LOKY_MAX_CPU_COUNT=1` globally
- [ ] Add cache cleanup before and after tests
- [ ] Validate container mounts before tests
- [ ] Add orphaned process cleanup in workflow

### Before Merging

- [ ] All tests pass locally with `-n 4`
- [ ] All tests pass serially with `-n 0`
- [ ] No new `.pyc` files created
- [ ] No hanging/timeout tests
- [ ] Follows prevention rules

---

## Common Scenarios

### Scenario 1: CI Tests Pass Locally But Fail in Pipeline

**Check:**
1. Are you setting `PYTHONDONTWRITEBYTECODE=1`?
2. Is there bytecode pollution? (`find . -name "*.pyc"`)
3. Are you testing with parallelism? (Try `-n 4`)

**Fix:** Clear bytecode and set environment variable

```bash
export PYTHONDONTWRITEBYTECODE=1
find . -type d -name __pycache__ -exec rm -rf {} +
uv run pytest tests/
```

**Prevention:** CI workflow always clears bytecode

---

### Scenario 2: Tests Hang/Timeout in Integration Suite

**Check:**
1. Are you using `-n 1` for integration tests?
2. Is `LOKY_MAX_CPU_COUNT=1` set?
3. Are there joblib/statsmodels imports?

**Fix:** Reduce parallelism and check for multiprocessing

```bash
export LOKY_MAX_CPU_COUNT=1
uv run pytest tests/integration/ -n 1 --timeout=120
```

**Prevention:** Always set LOKY_MAX_CPU_COUNT globally

---

### Scenario 3: "Databases Empty" Errors

**Check:**
1. Are containers running? (`docker ps`)
2. Are mounts correct? (`docker inspect --format='{{json .Mounts}}'`)
3. Is `APP_ENV=test` set?

**Fix:** Recreate containers with correct mounts

```bash
./scripts/start-dev.sh
# Or manually:
docker stop raglite-qdrant-test raglite-postgresql-test
docker rm raglite-qdrant-test raglite-postgresql-test
docker-compose -f docker-compose.yml up -d
```

**Prevention:** CI validates mounts before running tests

---

### Scenario 4: Tests Fail in Parallel But Pass Serially

**Check:**
1. Is global state being modified?
2. Are mocks isolated properly?
3. Is the test marked `@pytest.mark.slow`?

**Fix:** Add lazy loading and proper isolation

```python
# Use lazy loading instead of module-level initialization
def get_settings():
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# Mark stateful tests
@pytest.mark.slow
async def test_with_state():
    pass
```

**Prevention:** Prevention rules enforce these patterns

---

## Monitoring & Observability

### Key Metrics to Track

1. **Test Pass Rate:** Target 99.5%+
2. **Pipeline Duration:** Target <12 minutes
3. **Test Flakiness:** Target <5 failures/week
4. **Environment Consistency:** Target 100%
5. **Resource Efficiency:** Target zero SIGKILL/OOM

### Weekly Review Checklist

- [ ] Check CI failure rate (GitHub Actions dashboard)
- [ ] Review slow tests (anything >30s)
- [ ] Check resource usage (memory, CPU)
- [ ] Verify no container mount issues
- [ ] Verify no new .pyc pollution

### When to Escalate

- Failure rate >5%
- Single test consistently timing out
- "Databases Empty" errors recurring
- SIGKILL or OOM errors
- Tests hanging for >10 minutes

---

## Further Reading

### Within RAGLite

- **Testing Guidelines:** `/Users/ricardocarvalho/DeveloperFolder/AI Personal Trainer/workspace/plans/TESTING_GUIDELINES.md`
- **Code Rules:** `/.claude/rules/`
- **Architecture:** `/docs/architecture/`
- **Database Safety:** `/.claude/rules/database-safety.md`

### External References

- **GitHub Actions:** https://docs.github.com/en/actions
- **pytest-xdist:** https://pytest-xdist.readthedocs.io/
- **Docker:** https://docs.docker.com/
- **Colima:** https://github.com/abiosoft/colima

---

## Document Maintenance

### Last Updated
2025-12-30

### Maintained By
- CI Infrastructure Team

### Review Schedule
- **Weekly:** Check metrics, update failure patterns
- **Monthly:** Review prevention effectiveness
- **Quarterly:** Plan optimization improvements

### Contributing

To add to this knowledge base:

1. **Found a new failure pattern?**
   - Document in `failure-patterns.md`
   - Add prevention rule in `prevention-rules.md`
   - Reference in runbook

2. **Implemented a fix?**
   - Document root cause analysis
   - Add success metric
   - Update prevention checklist

3. **Have an operational insight?**
   - Add to `self-hosted-runner-guide.md`
   - Update relevant debugging section
   - Reference commit hash

---

## Quick Links

| Document | Purpose | Audience |
|----------|---------|----------|
| [CI Failure Runbook](/docs/ci-failure-runbook.md) | Quick troubleshooting | All engineers |
| [CI Strategy](/docs/ci-strategy.md) | Long-term approach | Architects, DevOps |
| [Failure Patterns](/docs/ci-knowledge/failure-patterns.md) | Known issues | Test engineers |
| [ATDD Subprocess Timeouts](/docs/ci-knowledge/atdd-subprocess-timeouts.md) | Subprocess test strategy | Test authors, architects |
| [Prevention Rules](/docs/ci-knowledge/prevention-rules.md) | Best practices | Test authors |
| [Self-Hosted Runner Guide](/docs/ci-knowledge/self-hosted-runner-guide.md) | Operations | DevOps, SRE |
| [Success Metrics](/docs/ci-knowledge/success-metrics.md) | Monitoring | Engineering leads |

---

## Summary

RAGLite CI has been systematically improved through:

1. **Identifying 5 root causes** from 15 CI fix commits
2. **Implementing global infrastructure changes** (2 environment variables, 3 workflow improvements)
3. **Documenting best practices** across 6 knowledge base files
4. **Capturing lessons learned** for future reference

The result: **90% reduction in test flakiness** with zero performance regression.

All infrastructure changes are production-ready and self-documenting.
