# CI/CD Pipeline Architecture

**Version:** 2.0 (Aligned with Actual Implementation)
**Last Updated:** October 4, 2025
**Status:** Active (Week 0 / Pre-Phase 1)

---

## Overview

RAGLite implements a **pragmatic, high-performance CI/CD pipeline** using **self-hosted macOS runners** with **UV package management** and **Ruff formatting/linting**. The pipeline prioritizes **speed** (<5 min total), **developer experience**, and **incremental complexity**.

**Current Implementation:** 3-stage pipeline for Week 0 validation
**Future State:** 5-stage enterprise pipeline (Phase 4)

---

## Architecture Philosophy

### Start Simple, Scale Gradually

**❌ ANTI-PATTERN:** Implementing enterprise CI/CD before product-market fit
**✅ PATTERN:** Begin with essentials, add stages as project matures

**Phase Progression:**

| Phase | CI/CD Complexity | Duration | Features |
|-------|-----------------|----------|----------|
| **Week 0 (Current)** | 3-stage pipeline | <5 min | Quality checks, test matrix, basic deploy |
| **Phase 1 (Weeks 1-5)** | + Integration tests | <8 min | Add Qdrant integration tests |
| **Phase 2 (Conditional)** | + GraphRAG tests | <12 min | Neo4j integration if needed |
| **Phase 3 (Weeks 9-12)** | + Performance tests | <15 min | Forecasting, insights validation |
| **Phase 4 (Prod-Ready)** | 5-stage enterprise | <20 min | Canary, auto-rollback, cost tracking |

---

## Current CI/CD Pipeline (Week 0)

**File:** `.github/workflows/ci.yml`

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────┐
│  Developer Push/PR                                               │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 1: Code Quality & Security (~2 min)                      │
│  ├─ Ruff linting (Black, isort rules)                           │
│  ├─ Security scan (Safety)                                      │
│  └─ BMAD standard files verification                            │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 2: Test Matrix (Parallel - ~3 min)                       │
│  ├─ Unit tests                                                  │
│  ├─ Integration tests (Qdrant required)                         │
│  ├─ E2E tests                                                   │
│  ├─ API tests                                                   │
│  ├─ Database tests                                              │
│  └─ Performance tests                                           │
│  Note: Tests run in parallel with pytest-xdist (-n 4)           │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 3: Deploy (Main branch only)                             │
│  └─ Placeholder for Phase 4 AWS deployment                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Infrastructure

**Self-Hosted Runners (macOS):**
- **Why?** Persistent Qdrant instance, faster builds, no GitHub runner limits
- **Pre-installed:** Python 3.13, UV 0.8.22, Docker Desktop
- **Qdrant:** Runs persistently via Docker on localhost:6333
- **Limitations:** No container actions (TruffleHog, markdown link checker disabled)

### Dependency Management

**UV (NOT Poetry):**

```yaml
- name: Install dependencies
  run: uv sync --frozen

- name: Run tests
  run: uv run pytest -n 4 --dist worksteal
```

**Why UV?**
- 10-100× faster than Poetry
- Zero Python dependencies (Rust binary)
- Built-in parallel installs
- PEP 621/PEP 735 compliant

---

## Stage 1: Code Quality & Security

**Execution Time:** ~2 minutes

```yaml
quality:
  name: Code Quality & Security
  runs-on: self-hosted

  steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Install dependencies
      run: uv sync --frozen

    - name: Linting (Black compatibility)
      run: uv run black --check spike/ tests/

    - name: Linting (Ruff)
      run: uv run ruff check spike/ tests/

    - name: Linting (isort)
      run: uv run isort --check-only spike/ tests/

    - name: Verify BMAD standard files exist
      run: |
        test -f docs/architecture/coding-standards.md
        test -f docs/architecture/tech-stack.md
        test -f docs/architecture/source-tree.md
        echo "✅ All BMAD standard files present"

    - name: Security scan (Safety)
      run: |
        pip install safety
        safety check --json || true
      continue-on-error: true
```

**Notes:**
- **Ruff** handles formatting (replaces Black) + linting + import sorting
- **Black check** still runs for compatibility verification (Week 0)
- **TruffleHog** secret scanning disabled (macOS self-hosted limitation)
  - Alternative: Gitleaks in pre-commit hook
- **MyPy** type checking disabled (will enable Phase 1 for `raglite/` code)

---

## Stage 2: Test Matrix (Parallel Execution)

**Execution Time:** ~3 minutes (parallel across 6 test suites)

```yaml
test-matrix:
  name: Tests - ${{ matrix.test-suite }}
  runs-on: self-hosted
  strategy:
    fail-fast: false
    matrix:
      test-suite: ["unit", "integration", "e2e", "api", "database", "performance"]

  steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Install dependencies
      run: uv sync --frozen

    - name: Verify Qdrant is available
      run: |
        if curl -sf http://localhost:6333/collections > /dev/null; then
          echo "✅ Qdrant is available at localhost:6333"
        else
          echo "⚠️  Qdrant not available - tests may fail"
        fi
      if: matrix.test-suite != 'unit'

    - name: Run tests
      env:
        QDRANT_HOST: localhost
        QDRANT_PORT: 6333
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      run: |
        # Skip if test directory doesn't exist yet
        if [ ! -d "tests/${{ matrix.test-suite }}" ]; then
          echo "⚠️  Test directory doesn't exist yet, skipping..."
          exit 0
        fi

        # Run pytest with parallel execution
        uv run pytest tests/${{ matrix.test-suite }}/ \
          -n 4 \
          --dist worksteal \
          --cov=spike --cov=src --cov=raglite \
          --cov-report=xml \
          --cov-report=term-missing \
          -v

    - name: Upload coverage
      uses: actions/upload-artifact@v4
      with:
        name: coverage-${{ matrix.test-suite }}
        path: coverage.xml
        retention-days: 1
```

**Key Features:**
- **Parallel execution:** 6 test suites run concurrently
- **pytest-xdist:** Each suite uses 4 workers (`-n 4 --dist worksteal`)
- **Graceful skipping:** Tests not created yet don't fail the build
- **Persistent Qdrant:** Integration tests connect to localhost:6333
- **Coverage tracking:** XML reports uploaded as artifacts

**Disabled Features (Week 0):**
- ❌ Codecov upload (re-enable Phase 1 with token configuration)
- ❌ Accuracy regression tests (waiting for ground truth dataset)

---

## Stage 3: Deploy

**Current:** Placeholder only (main branch)
**Phase 4:** AWS ECS deployment with canary releases

```yaml
deploy:
  name: Deploy to Production
  needs: [quality, test-matrix]
  runs-on: self-hosted
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'

  steps:
    - name: Deploy
      run: |
        echo "Deployment steps go here"
        # Phase 4: Terraform apply, ECS task updates, etc.
```

---

## Pre-commit Hooks (Local Development)

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  # Universal file checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json

  # Ruff (formatting + linting)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format  # Replaces Black

  # MyPy type checking (enabled Phase 1)
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        files: ^raglite/  # Only production code
        args: [--show-error-codes, --ignore-missing-imports]
        additional_dependencies: [pydantic, types-requests]

  # Secret detection
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
```

**Execution Time:** <5 seconds (optimized for developer experience)

---

## Phase 4: Future Enterprise Pipeline

**NOT IMPLEMENTED YET** - Documented for future reference

### 5-Stage Enterprise Pipeline

```
Stage 1: Quality (Parallel)
  ├─ Ruff (format + lint)
  ├─ MyPy (strict type checking)
  ├─ Bandit (SAST)
  ├─ TruffleHog (secret scanning)
  └─ Safety + pip-audit (dependency vulnerabilities)

Stage 2: Multi-Layer Testing (Parallel)
  ├─ Unit tests (80%+ coverage)
  ├─ Integration tests (Testcontainers)
  ├─ Accuracy regression (ground truth)
  ├─ RAG pipeline tests
  └─ LLM cost tracking

Stage 3: Docker Build & Scan (Per Service)
  ├─ Multi-stage build (UV cache optimization)
  ├─ Trivy vulnerability scan
  ├─ Push to ECR with semantic tags
  └─ Image size validation (<500MB)

Stage 4: Deployment (Environment-Specific)
  ├─ Dev: Auto-deploy on merge
  ├─ Staging: Manual approval + smoke tests
  ├─ Prod: Canary deployment (10% → 50% → 100%)
  └─ Health check validation (30s timeout)

Stage 5: Post-Deployment Validation
  ├─ Smoke tests (critical endpoints)
  ├─ Accuracy validation (subset of ground truth)
  ├─ Performance benchmarks (p50, p95 latency)
  ├─ Cost anomaly detection (LLM spend)
  └─ Auto-rollback on SLO breach
```

**Estimated Total Time:** 15-20 minutes

---

## Monitoring & Observability

### Current (Week 0)

- ✅ GitHub Actions run logs
- ✅ Coverage artifacts uploaded
- ✅ Test failure summaries

### Phase 1 Additions

- Codecov integration (re-enable with `CODECOV_TOKEN`)
- Daily accuracy tracking reports
- Test execution time trends

### Phase 4 Additions

- CloudWatch metrics (ECS health, API latency)
- Prometheus + Grafana dashboards
- LLM cost tracking (Anthropic API usage)
- Accuracy regression alerts (Slack notifications)
- Auto-rollback on SLO violations

---

## Performance Characteristics

### Current Pipeline Benchmarks

| Stage | Execution Time | Parallelization | Bottleneck |
|-------|----------------|-----------------|------------|
| Quality | ~2 min | Single runner | Ruff linting |
| Test Matrix | ~3 min | 6 suites × 4 workers | Qdrant integration tests |
| Deploy | <1 min | N/A | Placeholder only |
| **TOTAL** | **<5 min** | High | Well-optimized |

### Optimization Strategies

**UV Dependency Caching:**
- UV automatically caches downloads in `~/.cache/uv`
- Self-hosted runners persist cache across builds
- **Result:** Dependency install ~5-10s (vs 60-90s with Poetry)

**pytest-xdist Parallelization:**
- Each test suite uses 4 workers (`-n 4`)
- `--dist worksteal` dynamically balances load
- **Result:** 4× faster test execution

**Qdrant Persistence:**
- Docker container runs continuously on self-hosted runner
- No service startup overhead (vs Testcontainers: 20-30s)
- **Result:** Integration tests start immediately

---

## Migration Path (Week 0 → Phase 4)

### Week 1-5 (Phase 1)

**Add:**
- MyPy type checking in pre-commit (already in config, just uncomment)
- Codecov upload (set `CODECOV_TOKEN` secret)
- Accuracy regression tests (after Story 1.12A creates ground truth)

**No changes to:**
- UV (already optimal)
- Ruff (already configured)
- Test matrix (already comprehensive)

### Week 9-12 (Phase 3)

**Add:**
- Performance benchmarking tests
- Forecasting validation tests

### Week 13-16 (Phase 4)

**Major refactor:**
- Migrate to GitHub-hosted runners (ubuntu-latest)
- Add Docker build + Trivy scan stage
- Implement AWS ECS deployment
- Add canary release logic
- Implement auto-rollback on failures

---

## Security Considerations

### Current Safeguards

- ✅ Gitleaks in pre-commit (secret detection)
- ✅ Safety dependency scan (continue-on-error: true)
- ✅ BMAD standard files verification

### Disabled (Self-Hosted Runner Limitations)

- ❌ TruffleHog (container action, not supported on macOS)
- ❌ Trivy (Docker scanning, deferred to Phase 4)
- ❌ Bandit SAST (deferred to Phase 1)

### Manual Alternatives (Week 0)

```bash
# Secret scanning (local)
brew install trufflesecurity/trufflehog/trufflehog
trufflehog git file://. --since-commit HEAD~1

# Markdown link checking (local)
npm install -g markdown-link-check
markdown-link-check docs/**/*.md
```

---

## Troubleshooting

### Common Issues

**1. Qdrant connection failures in integration tests**

```bash
# Verify Qdrant is running
docker ps | grep qdrant

# Start Qdrant if not running
docker run -d -p 6333:6333 --name raglite-qdrant qdrant/qdrant:v1.11.0
```

**2. UV sync fails with "lock file out of sync"**

```bash
# Re-lock dependencies
uv lock

# Force sync
uv sync --frozen
```

**3. Pre-commit hooks fail locally but CI passes**

```bash
# Update pre-commit hooks to CI versions
pre-commit autoupdate

# Re-run
pre-commit run --all-files
```

---

## References

- **Actual CI Workflow:** `.github/workflows/ci.yml`
- **Pre-commit Config:** `.pre-commit-config.yaml`
- **UV Documentation:** https://github.com/astral-sh/uv
- **Ruff Documentation:** https://github.com/astral-sh/ruff
- **pytest-xdist:** https://pytest-xdist.readthedocs.io/

---

## Summary

**Current State (Week 0):**
- ✅ Fast (<5 min total)
- ✅ Developer-friendly (UV, Ruff, self-hosted)
- ✅ Pragmatic (test suites scale as code grows)
- ✅ Future-proof (clear migration path to Phase 4)

**Key Differentiators:**
- **UV replaces Poetry:** 10-100× faster
- **Ruff replaces Black + isort:** Single tool, Rust-based
- **Self-hosted macOS runners:** Persistent Qdrant, faster builds
- **pytest-xdist:** 4× parallelization per test suite

**Next Steps (Phase 1):**
1. Enable MyPy in pre-commit (uncomment config)
2. Add Codecov token secret
3. Create ground truth dataset (Story 1.12A)
4. Measure accuracy regression daily
