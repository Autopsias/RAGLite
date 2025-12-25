# CI/CD Strategy & Memory Architecture

**Last Updated:** 2025-12-24
**Strategic Focus:** Monolithic dependency architecture and memory budgeting
**CI Reliability Target:** 99%+ (currently 98%)
**Documentation Series:** Part of CI Knowledge Base

---

## Executive Summary

RAGLite CI pipeline currently manages a **monolithic dependency architecture** that loads 10-15GB of ML libraries (sentence-transformers, Prophet, PyTorch) when only ~4-5GB is available during test execution. This document captures the strategic approach to solving this constraint and preventing memory-related CI failures.

### Key Challenge
- **Total ML libraries:** 10-15 GB (sentence-transformers, Prophet, PyTorch, Chronos, XGBoost, LightGBM)
- **Available system memory:** ~8 GB (Colima/Docker allocation)
- **Needed for system:** ~2-3 GB (macOS + Docker overhead)
- **Available for tests:** ~4-5 GB (insufficient for full load)

### Strategic Response
Three-tier approach:
1. **Immediate:** Lightweight test mode (mocked ML dependencies)
2. **Medium-term:** Lazy loading for expensive libraries
3. **Long-term:** Conditional dependency loading based on test markers

---

## CI Architecture Overview

### Current State (2024-12-24)

| Component | Value | Status |
|-----------|-------|--------|
| CI workflow size | 2,364 lines | Needs reduction |
| Number of jobs | 13+ | Too many |
| Memory per test job | 6-8 GB | Constrained |
| Success rate | 98% | Target: 99%+ |
| MTTR | <1 hour | Target: <30 min |

### Test Execution Modes

RAGLite uses **conditional test execution** to manage memory constraints:

| Mode | Name | ML Dependencies | Memory | When Used |
|------|------|-----------------|--------|-----------|
| **Lightweight** | Unit tests + mocks | Mocked | <2 GB | PR branches, feature development |
| **Standard** | Integration tests | Real imports | 6-8 GB | main branch only |
| **Full Stack** | Accuracy + Agentic | All libraries | 8-10 GB | Nightly, burn-in tests |

### Memory Budget Breakdown

```
Total macOS Memory: 16 GB
├─ macOS system: 2-3 GB
├─ Docker (Colima): 8 GB
│  ├─ Qdrant container: 1 GB
│  ├─ PostgreSQL container: 512 MB
│  └─ Test workspace: 6-6.5 GB
│     ├─ Python runtime: 200 MB
│     ├─ pytest framework: 300 MB
│     ├─ ML dependencies (conditional):
│     │  ├─ sentence-transformers: 2-3 GB
│     │  ├─ Prophet: 1-2 GB
│     │  ├─ PyTorch: 1 GB
│     │  ├─ Chronos: 1 GB
│     │  └─ XGBoost/LightGBM/CatBoost: 500 MB
│     └─ Test data: 100-200 MB
└─ Buffer: 0 GB (tight)
```

**Key Insight:** Each ML library takes 500MB-3GB individually. Loading all at once exceeds available memory by 2-3x.

---

## Root Cause Analysis: Why Memory Constraints Exist

### Five Whys: Memory OOM Kills (Exit 137)

1. **Why does CI get OOM killed?** → Python process exceeds 6GB during test execution
2. **Why does Python use 6GB?** → ML libraries load all vectors/models into memory on import
3. **Why load all models?** → Libraries designed for production use, not testing
4. **Why are production libraries used in tests?** → No lightweight test doubles available
5. **Why not create mocks?** → Mocks require understanding model interfaces (not documented)

**Root Cause:** Monolithic dependency loading strategy incompatible with memory constraints

### Contributing Factors

| Factor | Impact | Severity |
|--------|--------|----------|
| sentence-transformers loads 380M vectors on import | +2-3 GB | High |
| Prophet + statsmodels imports all trained models | +1-2 GB | High |
| PyTorch imports CUDA libraries even on CPU | +1 GB | Medium |
| Chronos & XGBoost cache pre-built models | +500 MB each | Medium |
| test collection imports all conftest modules | Baseline 200 MB | Low |

---

## Strategic Decisions

### AD1: Lightweight Test Mode for PR Branches

**Decision:** PR branches run only unit tests with mocked ML dependencies.

**Rationale:**
- Unit tests validate business logic, not ML accuracy
- Mocking ML libraries reduces memory from 10-15GB to <2GB
- Faster feedback loop (5-10 min vs 30-60 min)
- Cheaper to run (fewer resources)

**Implementation:**
```bash
# In CI job
if [[ "$GITHUB_REF" != "refs/heads/main" ]]; then
  export LIGHTWEIGHT_TESTS=true
  export MOCK_SENTENCE_TRANSFORMERS=true
  export MOCK_PROPHET=true
  pytest tests/unit/ -m "not slow" -n 0
fi
```

**Trade-off:**
- Gain: 12+ minute reduction per PR
- Loss: Don't validate ML library integration on PRs (caught on main merge)

---

### AD2: Main-Branch-Only Expensive Jobs

**Decision:** Integration, accuracy, and agentic tests only run on main branch.

**Rationale:**
- Main branch is merge-qualified (already passed unit tests)
- Full validation only needed before merging
- Reduces CI queuing for feature branches
- Costs contained to weekly main branch runs

**Implementation:**
```yaml
jobs:
  test-integration:
    if: github.ref == 'refs/heads/main'
    ...
```

**Trade-off:**
- Gain: Faster feedback on PRs
- Loss: Integration issues discovered only at merge time (mitigated by mandatory PR unit tests)

---

### AD3: Composite Actions for Code Reuse

**Decision:** Extract common workflows into reusable composite actions.

**Rationale:**
- CI workflow at 2,364 lines is unmaintainable
- PostgreSQL health checks duplicated 4+ times
- Container startup logic duplicated across jobs
- Reduces error surface (one source of truth)

**Composite Actions Created:**
| Action | Purpose | Size | Reused In |
|--------|---------|------|-----------|
| start-containers | Start test containers | 120 lines | 5+ jobs |
| wait-for-postgres | Health check Postgres | 50 lines | 6+ jobs |
| wait-for-qdrant | Health check Qdrant | 50 lines | 6+ jobs |
| test-collection | Pytest discovery | 100 lines | 4+ jobs |

**Expected Reduction:** 2,364 lines → ~1,200 lines (50% reduction)

---

## Prevention Rules

Lessons learned from 15+ CI fixes systematized into rules:

### Rule 1: Always Define Memory Limits Upfront

When adding a new CI job:
1. Profile memory usage: `python -c "import tracemalloc; tracemalloc.start(); import <pkg>; print(tracemalloc.get_traced_memory()[1]/1024/1024, 'MB')"`
2. If >500MB, add to memory budget table
3. If would exceed 4GB available, require LIGHTWEIGHT_TESTS mode
4. Document in CI-STRATEGY.md

**Rationale:** Prevents surprise OOM kills late in CI runs.

---

### Rule 2: Use Lazy Loading for Heavy Libraries

When a library exceeds 500MB:

```python
# WRONG: Loads library immediately
from sentence_transformers import SentenceTransformer

# CORRECT: Loads only when used
def get_embeddings():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('fin-e5-base')
    return model
```

**Rationale:** Reduces baseline memory from 2GB to <100MB until actually needed.

---

### Rule 3: Mark Slow Tests, Don't Skip Them

When a test takes >5 seconds:

```python
# WRONG: Skip the test completely
@pytest.mark.skip(reason="Too slow")
def test_large_document_ingestion():
    ...

# CORRECT: Mark as slow, exclude from PR runs
@pytest.mark.slow
def test_large_document_ingestion():
    ...
```

Then in CI:
```bash
# PRs: exclude slow tests
pytest tests/ -m "not slow"

# Main: include slow tests
pytest tests/ -m ""
```

**Rationale:** Maintains coverage on main branch while keeping PR feedback fast.

---

### Rule 4: Explicit Resource Limits Per Job

Every CI job must declare:

```yaml
jobs:
  test-integration:
    # REQUIRED: Explicit memory limit
    timeout-minutes: 30
    runs-on: [self-hosted, raglite]  # Resource-controlled runner

    env:
      # REQUIRED: Memory guidance for job
      PYTEST_WORKERS: 4  # Limits to 4 parallel processes
      DOCKER_MEMORY: "6g"  # Container memory limit
```

**Rationale:** Prevents runaway memory consumption from consuming entire runner.

---

### Rule 5: Sequential Execution for Integration Tests

Integration tests must use sequential pytest execution:

```bash
# Integration tests MUST use sequential (-n 0)
pytest tests/integration/ -n 0

# Unit tests CAN use parallel (-n 4)
pytest tests/unit/ -n 4
```

**Rationale:** Session-scoped fixtures incompatible with parallel workers; OOM results when processes share memory.

---

### Rule 6: Health Checks Before Every Test Run

Before pytest discovers tests:

```bash
# REQUIRED: Verify PostgreSQL ready
./scripts/ci/wait-for-service.sh postgresql raglite-postgresql-test 90

# REQUIRED: Verify Qdrant ready
./scripts/ci/wait-for-service.sh qdrant raglite-qdrant-test 90

# THEN: Run test collection
pytest --collect-only tests/
```

**Rationale:** Prevents silent test collection failures from unready services.

---

## Memory Optimization Strategies

### Strategy 1: Dependency Mocking (Implemented)

**What:** Mock ML library imports in unit tests to reduce memory.

**How:**
```python
# conftest.py
import os
if os.getenv("LIGHTWEIGHT_TESTS") == "true":
    # Mock sentence_transformers
    sys.modules['sentence_transformers'] = MagicMock()

    # Mock prophet
    sys.modules['prophet'] = MagicMock()
```

**Impact:** 10-15 GB → <2 GB for unit tests

**Cost:** Requires maintaining mock interfaces (low effort, one-time setup)

---

### Strategy 2: Lazy Loading (Future)

**What:** Import heavy libraries only when needed, not at module level.

**How:**
```python
# BEFORE
from sentence_transformers import SentenceTransformer
embedder = None

def get_embedder():
    global embedder
    if embedder is None:
        embedder = SentenceTransformer('fin-e5-base')
    return embedder

# AFTER (lazy)
embedder = None

def get_embedder():
    global embedder
    if embedder is None:
        # Only import when actually used
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer('fin-e5-base')
    return embedder
```

**Impact:** Baseline memory stays <100MB until embeddings actually called

**Timeline:** Implement after Phase 1 (E2.1) completes

---

### Strategy 3: Test Segmentation (Future)

**What:** Divide test suite by memory requirement and run separately.

**How:**
```bash
# Profile 1: Lightweight (unit tests, <2GB)
pytest tests/unit/ -n 4 -m "not slow"

# Profile 2: Standard (integration, 6GB)
pytest tests/integration/ -n 0

# Profile 3: Full (agentic + accuracy, 8GB, main only)
pytest tests/e2e/ tests/accuracy/ -n 0
```

**Impact:** Allows high-memory jobs to run independently without consuming runner entirely

**Timeline:** Implement for Epic 3 (Phase 4+)

---

## Monitoring & Metrics

### Success Metrics

Track these weekly to monitor CI health:

| Metric | Target | Current | Method |
|--------|--------|---------|--------|
| **Success Rate** | 99%+ | 98% | GitHub Actions dashboard |
| **Mean Time to Resolution** | <30 min | <1 hour | Manual tracking on failures |
| **Memory Peak** | <5 GB | 6-8 GB | `docker stats` during runs |
| **Test Collection Time** | <10s | 8-12s | pytest output |
| **Unit Test Duration** | <10m | 5-8m | GitHub Actions logs |
| **Integration Test Duration** | <15m | 10-12m | GitHub Actions logs |

### Failure Categories to Track

| Category | Root Cause | Recent Trend | Prevention |
|----------|-----------|--------------|-----------|
| Memory OOM (Exit 137) | Monolithic loading | Improving | LIGHTWEIGHT_TESTS mode |
| Test Collection Empty | Service not ready | Stable | Health checks |
| Port Conflicts | Stale processes | Stable | Cleanup script |
| Async Timeouts | Slow services | Improving | Exponential backoff |

---

## Implementation Timeline

### Phase 1: Immediate (2025-12-24 - 2025-12-31)
- [x] Document memory architecture
- [x] Implement LIGHTWEIGHT_TESTS mode
- [ ] Extract composite actions (50% reduction in workflow size)
- [ ] Add memory monitoring to CI output

### Phase 2: Short-term (2026-01-01 - 2026-01-31)
- [ ] Implement lazy loading for sentence-transformers
- [ ] Implement lazy loading for Prophet
- [ ] Validate memory reduction in CI runs
- [ ] Update prevention rules based on results

### Phase 3: Medium-term (2026-02-01 - 2026-02-28)
- [ ] Implement test segmentation by memory profile
- [ ] Decouple agentic tests to separate job
- [ ] Optimize container resource requests
- [ ] Full CI workflow refactor (<1,200 lines)

### Phase 4: Long-term (Post-Phase 3)
- [ ] Implement distributed CI (multiple runners)
- [ ] Add resource pooling for heavy jobs
- [ ] Implement dynamic test scheduling based on available memory

---

## Related Architecture Decisions

This strategy implements or references:

| ADR | Title | Relevant Sections |
|-----|-------|-------------------|
| AD1 | Lightweight Test Mode | Prevention Rules, Memory Budget |
| AD2 | Main-Only Expensive Jobs | Prevention Rules, CI Architecture |
| AD3 | Composite Actions | Code Reuse, Future Implementation |

---

## Dependency Management

### Current ML Dependencies (Epic 1-3 scope)

| Library | Version | Memory | When Used | Conditional? |
|---------|---------|--------|-----------|--------------|
| sentence-transformers | 2.7+ | 2-3 GB | Embeddings (always) | No |
| fin-e5-base | Latest | 1.2 GB | Embeddings (always) | No |
| openpyxl | 3.10+ | <100 MB | Excel parsing | No |
| pandas | 2.0+ | <200 MB | Data manipulation | No |
| docling | 0.30+ | 500 MB | PDF extraction | No |
| pypdfium | 1.12+ | <50 MB | PDF backend | No |
| qdrant-client | 2.7+ | <100 MB | Vector DB | No |
| fastmcp | 1.0+ | <50 MB | MCP server | No |
| pydantic | 2.5+ | <50 MB | Validation | No |

### Conditional Dependencies (Phase 2+)

| Library | Phase | Memory | Lazy Load? | Notes |
|---------|-------|--------|-----------|-------|
| prophet | 2 | 1-2 GB | Yes (implement S2.3) | Time series forecasting |
| pytorch | 2 | 1 GB | Yes (implement S2.3) | ML model backend |
| chronos | 2 | 1 GB | Yes (implement S2.3) | Time series forecasting |
| xgboost | 2 | 500 MB | Yes (implement S2.3) | Gradient boosting |
| lightgbm | 2 | 500 MB | Yes (implement S2.3) | Gradient boosting |
| catboost | 2 | 500 MB | Yes (implement S2.3) | Gradient boosting |

**Strategy:** Phase 2 dependencies only imported in agentic tests, not in unit/integration tests (unless explicitly requested).

---

## Troubleshooting Connection

For specific failure resolutions, see:
- **Quick fixes:** `troubleshooting-runbook.md` → Quick Reference Table
- **Architecture questions:** `infrastructure-architecture.md`
- **Prevention principles:** `lessons-learned.md`

Example: "How do I fix OOM (Exit 137) error?"
1. Start: `troubleshooting-runbook.md` → Search for "Exit 137"
2. Follow: Step-by-step diagnosis procedure
3. Understand: Back to this document → Section "Root Cause Analysis: Why Memory Constraints Exist"

---

## Approval & Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| DevOps Lead | Ricardo | 2025-12-24 | Draft |
| Architecture | Team | TBD | Pending Review |
| Product | PM | TBD | Pending Review |

---

## Document Control

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-24 | Initial creation - Memory architecture strategy | Claude Agent |

---

**Document Status:** ACTIVE
**Audience:** Developers, DevOps, Architecture Team
**Review Frequency:** Quarterly (or when major CI changes occur)
**Next Review Date:** 2026-03-24
