# CI/CD Pipeline Guide

**RAGLite Continuous Integration & Deployment**

This document describes the CI/CD pipeline setup, configuration, and best practices for RAGLite.

---

## Table of Contents

- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Pipeline Stages](#pipeline-stages)
- [Local Development](#local-development)
- [Debugging CI Failures](#debugging-ci-failures)
- [Configuration & Secrets](#configuration--secrets)
- [Performance Targets](#performance-targets)
- [Best Practices](#best-practices)

---

## Overview

RAGLite uses **GitHub Actions** for CI/CD with self-hosted runners optimized for Python testing. The pipeline is designed for:

- **Fast feedback**: ~20-30 min for full pipeline (including burn-in)
- **High confidence**: Burn-in loops detect flaky tests before merge
- **Resource efficiency**: UV package manager (10-100x faster than pip)
- **Selective testing**: Run only affected tests when possible

**Pipeline Files:**
- **Main CI**: `.github/workflows/ci.yml` - Primary quality pipeline
- **Accuracy Validation**: `.github/workflows/accuracy-validation.yml` - NFR6/NFR7 checks
- **Priority-Based**: `.github/workflows/test-priority-based.yml` - Smart test execution

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions                          │
│                   (Self-Hosted Runners)                      │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
    ┌───────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
    │ Code Quality │ │   Tests   │ │ Quality Gates│
    └──────────────┘ └───────────┘ └─────────────┘
    │ - Ruff       │ │ - Unit    │ │ - Burn-In   │
    │ - Black      │ │ - Integ.  │ │ - Coverage  │
    │ - isort      │ │ - E2E     │ │ - Accuracy  │
    │ - mypy       │ │ - Perf.   │ │             │
    │ - Security   │ │           │ │             │
    └──────────────┘ └───────────┘ └─────────────┘
```

**Runner Configuration:**
- **Labels**: `[self-hosted, raglite]`
- **Isolation**: Dedicated runners prevent cross-project contention
- **Resources**: Limited to 4 pytest workers (prevents MacBook freeze)

---

## Pipeline Stages

### Stage 1: Code Quality (5-10 min)

**Jobs:**
1. **Lint & Format** - Ruff, Black, isort
2. **Type Check** - mypy strict mode
3. **Security Scan** - Bandit, Safety

**Key Features:**
- All jobs run in parallel
- Non-blocking (continue-on-error for type check & security)
- Artifact upload for security reports

**Local Execution:**
```bash
# Run all code quality checks
ruff check .
black --check raglite/ tests/ scripts/
isort --check-only raglite/ tests/ scripts/
mypy raglite/
```

---

### Stage 2: Test Execution (10-20 min)

**Jobs:**
4. **Unit Tests** (~200 tests, 4 workers, <10 min)
   - Parallel execution with pytest-xdist
   - Coverage enforcement (80% threshold)
   - No external dependencies

5. **Integration Tests** (~115 tests, 1 worker, 45-50 min)
   - Sequential execution (shared Qdrant collection)
   - Requires Qdrant + PostgreSQL
   - Fast mode: 10-page PDF (~10-15s ingestion)

6. **E2E Tests** (~28 tests, sequential, <15 min)
   - Full isolation, no parallelism
   - MCP protocol compliance

**Test Organization:**
```
tests/
├── unit/          # Fast, isolated, no dependencies
├── integration/   # Qdrant + PostgreSQL required
└── e2e/           # Full system validation
```

**Local Execution:**
```bash
# Unit tests (fast)
pytest tests/unit/ -n 4 --dist loadfile -m "not slow"

# Integration tests (requires services)
docker run -d -p 6333:6333 --name raglite-qdrant qdrant/qdrant:v1.15.0
pytest tests/integration/ -n 1 -m "not slow"

# E2E tests
pytest tests/e2e/ -n 0 -m "not slow"
```

---

### Stage 3: Quality Gates (5-30 min)

**Jobs:**
7. **Performance Validation** (NFR13)
   - Query response time: <5s p50, <15s p95
   - Non-blocking warnings

8. **Test Discovery Validation**
   - Ensures all tests are discovered by pytest
   - Prevents shadow test suites
   - Minimum 390 tests expected

9. **Documentation Validation**
   - Verifies required docs exist
   - Blocks merge if architecture/PRD missing

10. **Burn-In Loop** (NEW - Flaky Test Detection)
    - **Trigger**: PRs to main/develop only
    - **Iterations**: 3 (quick feedback, ~15-20 min)
    - **Scope**: Full test suite (unit + integration + e2e)
    - **Failure Policy**: ANY failure = FLAKY
    - **Artifacts**: Logs + JUnit XML on failure

**Burn-In Philosophy:**
> Even ONE failure in burn-in = tests are flaky. Fix before merging.

**Local Execution:**
```bash
# Run burn-in loop locally
./scripts/burn-in.sh 10 tests/  # 10 iterations, full suite
./scripts/burn-in.sh 20 tests/unit  # 20 iterations, unit only
```

---

### Stage 4: Summary & Reporting

**Job 11: Build Summary**
- Aggregates all job results
- Blocks merge if critical checks fail
- Provides actionable feedback

**Critical Checks (blocking):**
- ✅ Unit tests must pass
- ✅ Linting must pass
- ✅ Test discovery must pass
- ✅ Documentation must exist

**Warning Checks (non-blocking):**
- ⚠️ Type checking issues
- ⚠️ Security scan findings
- ⚠️ Integration test failures
- ⚠️ E2E test failures
- ⚠️ Performance degradation
- ⚠️ Burn-in loop flakiness

---

## Local Development

### Helper Scripts

Three helper scripts mirror CI behavior locally:

#### 1. **test-changed.sh** - Selective Testing

Runs only tests affected by changed files.

```bash
# Compare against HEAD~1 (default)
./scripts/test-changed.sh

# Compare against main branch
./scripts/test-changed.sh main

# Compare against develop branch
./scripts/test-changed.sh develop
```

**Smart Detection:**
- Maps source files to test files
- Runs full suite for critical infrastructure changes
- Skips tests for documentation-only changes

**Speedup:** 50-80% faster for focused PRs

---

#### 2. **ci-local.sh** - Full CI Mirror

Mirrors the complete CI pipeline locally for debugging.

```bash
# Standard run (3-iteration burn-in)
./scripts/ci-local.sh

# Full run (10-iteration burn-in)
./scripts/ci-local.sh --full

# Skip burn-in loop
./scripts/ci-local.sh --skip-burn-in

# Skip linting checks
./scripts/ci-local.sh --skip-lint
```

**Stages:**
1. Code quality (lint, format, imports)
2. Test execution (unit, integration, e2e)
3. Burn-in loop (flaky test detection)

**Exit Code:** 0 = all passed, 1 = failures detected

---

#### 3. **burn-in.sh** - Standalone Burn-In

Dedicated burn-in loop for detecting flaky tests.

```bash
# 10 iterations, full suite (default)
./scripts/burn-in.sh

# 20 iterations, full suite
./scripts/burn-in.sh 20

# 10 iterations, unit tests only
./scripts/burn-in.sh 10 tests/unit

# 100 iterations, single test file (high confidence)
./scripts/burn-in.sh 100 tests/integration/test_retrieval_integration.py
```

**Features:**
- Saves results to timestamped directory
- Tracks failure rate and patterns
- Provides confidence level assessment
- Actionable next steps on failure

**Confidence Levels:**
- **Basic**: 3-9 iterations
- **Good**: 10-19 iterations (standard)
- **High**: 20-99 iterations
- **Very High**: 100+ iterations (production-grade)

---

## Debugging CI Failures

### Common Failure Patterns

#### 1. **Linting Failures**

**Symptom:** Ruff, Black, or isort checks fail

**Fix:**
```bash
# Auto-fix formatting
black raglite/ tests/ scripts/
isort raglite/ tests/ scripts/

# Auto-fix linting (safe fixes only)
ruff check --fix .
```

---

#### 2. **Test Failures (Not in Local)**

**Symptom:** Tests pass locally but fail in CI

**Possible Causes:**
- Different Python version
- Missing dependencies
- Service timing issues
- State leakage between tests

**Debugging:**
```bash
# Mirror CI environment exactly
./scripts/ci-local.sh

# Check Python version
python --version  # Should be 3.11+

# Verify services
curl http://localhost:6333/collections  # Qdrant
docker ps  # PostgreSQL
```

---

#### 3. **Burn-In Failures (Flaky Tests)**

**Symptom:** Burn-in loop detects non-deterministic failures

**Common Causes:**
1. **Race conditions** in async code
2. **Timing dependencies** (sleeps, timeouts)
3. **Shared mutable state** between tests
4. **External service flakiness** (Qdrant, PostgreSQL)
5. **Non-deterministic data generation**

**Debugging Steps:**
1. Download burn-in artifacts from CI
2. Compare logs across iterations
3. Identify which tests failed in which iterations
4. Look for patterns (always same test? random?)
5. Run local burn-in on suspect tests:
   ```bash
   ./scripts/burn-in.sh 50 tests/integration/test_flaky.py
   ```

**Fixes:**
- Add proper test isolation (pytest fixtures)
- Use deterministic data (factories, not random)
- Add explicit waits (not sleeps)
- Clean up state in teardown
- Use `pytest-rerunfailures` only for known external flakiness

---

#### 4. **Integration Test Hangs**

**Symptom:** Integration tests timeout after 90 minutes

**Possible Causes:**
- Qdrant service not responding
- PostgreSQL connection issues
- Mistral API rate limiting (sequential execution prevents this)

**Fix:**
```bash
# Restart services
docker restart raglite-qdrant
docker restart raglite-postgresql

# Check service health
curl http://localhost:6333/telemetry  # Check for 500 errors
docker logs raglite-postgresql --tail 50
```

---

#### 5. **Coverage Drops**

**Symptom:** Coverage enforcement fails (<80%)

**Fix:**
```bash
# Generate local coverage report
pytest tests/unit/ -n 4 --cov=raglite --cov-report=html

# Open HTML report
open htmlcov/index.html

# Add tests for uncovered lines
```

---

## Configuration & Secrets

### Environment Variables

**Test Execution:**
```bash
# Use full 160-page PDF (CI default: false for speed)
TEST_USE_FULL_PDF=true

# Qdrant configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333

# PostgreSQL configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=raglite
POSTGRES_USER=raglite
POSTGRES_PASSWORD=raglite
```

### Secrets (GitHub Actions)

**Required Secrets:**
- None currently (all services run locally)

**Future Secrets** (if adding external integrations):
- `SLACK_WEBHOOK` - Failure notifications
- `CODECOV_TOKEN` - Coverage reporting
- `ANTHROPIC_API_KEY` - Claude API (if testing real LLM)

See `docs/ci-secrets-checklist.md` for complete list.

---

## Performance Targets

### Pipeline Execution Times

| Stage                  | Target Time | Actual (Self-Hosted) |
|------------------------|-------------|----------------------|
| Code Quality           | <5 min      | ~3 min               |
| Unit Tests             | <10 min     | ~8 min               |
| Integration Tests      | <50 min     | 45-50 min            |
| E2E Tests              | <15 min     | ~10 min              |
| Burn-In Loop (3 iter)  | <20 min     | ~15-18 min           |
| **Total (with burn-in)**| **<60 min** | **~50-55 min**       |
| **Total (without)**    | **<45 min** | **~35-40 min**       |

**Speedup Strategies:**
- ✅ UV package manager (10-100x faster pip)
- ✅ Parallel unit tests (4 workers)
- ✅ Dependency caching (npm, browsers)
- ✅ Fast mode PDF (10-page vs 160-page)
- ✅ Selective testing (test-changed.sh)

---

## Best Practices

### 1. **Test Reliability**

**DO:**
- ✅ Use pytest fixtures for setup/teardown
- ✅ Generate deterministic test data
- ✅ Add explicit waits (not sleeps)
- ✅ Isolate tests (no shared state)
- ✅ Run burn-in locally before pushing

**DON'T:**
- ❌ Use `time.sleep()` for synchronization
- ❌ Depend on execution order
- ❌ Share mutable fixtures
- ❌ Ignore burn-in failures

---

### 2. **Performance**

**DO:**
- ✅ Mark slow tests with `@pytest.mark.slow`
- ✅ Use fast fixtures (module/session scope)
- ✅ Cache external API calls
- ✅ Run unit tests in parallel

**DON'T:**
- ❌ Re-ingest PDFs in every test
- ❌ Make unnecessary API calls
- ❌ Use full 160-page PDF locally

---

### 3. **CI Hygiene**

**DO:**
- ✅ Run `./scripts/ci-local.sh` before pushing
- ✅ Fix linting issues immediately
- ✅ Keep coverage above 80%
- ✅ Fix burn-in failures before merging

**DON'T:**
- ❌ Push without local validation
- ❌ Disable linting rules without approval
- ❌ Merge with burn-in failures
- ❌ Ignore CI warnings

---

### 4. **Burn-In Strategy**

**When to Run:**
- ✅ Before merging to main/develop (automatic in CI)
- ✅ After fixing flaky tests (verify fix)
- ✅ After major test infrastructure changes
- ✅ When adding new integration tests

**Iteration Guidelines:**
- **3 iterations**: Quick feedback (PR default)
- **10 iterations**: Standard confidence
- **20 iterations**: High confidence
- **100 iterations**: Production-grade stability

**Failure Threshold:**
- Even ONE failure = flaky test
- Must fix before merging
- No exceptions

---

## Badge URLs

Add these badges to your README.md:

```markdown
![CI Status](https://github.com/Autopsias/RAGLite/actions/workflows/ci.yml/badge.svg)
![Accuracy Validation](https://github.com/Autopsias/RAGLite/actions/workflows/accuracy-validation.yml/badge.svg)
![Test Count](https://img.shields.io/badge/tests-394-blue)
![Coverage](https://img.shields.io/badge/coverage-80%25-green)
```

---

## Additional Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **pytest-xdist**: https://pytest-xdist.readthedocs.io/
- **GitHub Actions**: https://docs.github.com/en/actions
- **UV Package Manager**: https://github.com/astral-sh/uv

---

## Changelog

**2025-11-05**: Added burn-in loop job, helper scripts, comprehensive documentation
**2025-10-29**: Added runner isolation (raglite label), resource limits
**2025-10-28**: Test suite consolidation (tests/ directory)
**2025-10-25**: Initial CI/CD pipeline setup

---

**Questions or Issues?**

If you encounter CI/CD problems:
1. Check this guide first
2. Run `./scripts/ci-local.sh` to debug locally
3. Review GitHub Actions logs
4. Check service health (Qdrant, PostgreSQL)
5. Contact the team if stuck
