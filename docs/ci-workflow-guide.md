# RAGLite CI/CD Workflow Guide

**Last Updated:** 2025-10-12
**Based On:** Powerpoint Agent Generator CI best practices

---

## Overview

RAGLite uses a comprehensive CI/CD pipeline that runs 8 parallel jobs to ensure code quality, security, and test coverage. The workflow is optimized with UV package manager for 10-100x faster dependency installation.

---

## CI Pipeline Architecture

### Job Execution Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Code Push/PR                          │
└────────────────────┬────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
┌─────▼────┐  ┌─────▼────┐  ┌─────▼────┐
│   Lint   │  │   Type   │  │ Security │  ← Parallel
│          │  │  Check   │  │          │    Execution
└─────┬────┘  └─────┬────┘  └─────┬────┘    Phase 1
      │              │              │
      └──────────────┼──────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
┌─────▼────┐  ┌─────▼────┐  ┌─────▼────┐
│   Unit   │  │Integration│ │   E2E    │  ← Parallel
│  Tests   │  │  Tests   │  │  Tests   │    Execution
└─────┬────┘  └─────┬────┘  └─────┬────┘    Phase 2
      │              │              │
      └──────────────┼──────────────┘
                     │
            ┌────────▼────────┐
            │      Docs       │         ← Phase 3
            │   Validation    │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │   CI Summary    │         ← Phase 4
            │   (Blocking)    │
            └─────────────────┘
```

---

## Jobs Description

### 1. **Lint & Format Check** (5 min timeout)

**Purpose:** Ensure code style consistency

**Checks:**
- Ruff linting (syntax, style, best practices)
- Black formatting (line length, code style)
- isort import ordering

**Blocking:** Yes (must pass for merge)

**Continue on Error:** Individual checks continue but job fails if any check fails

---

### 2. **Type Checking** (5 min timeout)

**Purpose:** Static type analysis with mypy

**Checks:**
- Type annotations on raglite/ package
- Ignores missing imports for external libraries
- Excludes test files

**Blocking:** No (warnings only)

**Continue on Error:** Yes

---

### 3. **Security Scanning** (5 min timeout)

**Purpose:** Detect security vulnerabilities

**Tools:**
- **Bandit:** Python security linter (finds hardcoded secrets, SQL injection risks, etc.)
- **Safety:** Dependency vulnerability scanner

**Artifacts:**
- `bandit-report.json` (retained 30 days)

**Blocking:** No (warnings only)

**Continue on Error:** Yes

---

### 4. **Unit Tests** (10 min timeout)

**Purpose:** Fast, isolated tests with no external dependencies

**Features:**
- Parallel execution with pytest-xdist (`-n auto`)
- Work-stealing distribution strategy
- Coverage reporting (XML + HTML + terminal)
- JUnit XML for test result visualization

**Artifacts:**
- `coverage.xml`
- `htmlcov/` directory
- `pytest-unit-report.xml`

**Blocking:** Yes (must pass for merge)

---

### 5. **Integration Tests** (15 min timeout)

**Purpose:** Tests requiring external services (Qdrant)

**Dependencies:**
- Requires unit tests to pass first (`needs: [test-unit]`)
- Qdrant must be running on localhost:6333

**Qdrant Setup:**
```bash
docker run -d -p 6333:6333 --name raglite-qdrant qdrant/qdrant:v1.11.0
```

**Blocking:** No (warnings only)

**Continue on Error:** Yes

---

### 6. **E2E Tests** (15 min timeout)

**Purpose:** End-to-end validation of complete workflows

**Dependencies:**
- Requires unit tests to pass first (`needs: [test-unit]`)

**Test Coverage:**
- Ground truth validation
- Document ingestion workflows
- MCP server integration

**Blocking:** No (warnings only)

**Continue on Error:** No (fails on error)

---

### 7. **Documentation Validation** (5 min timeout)

**Purpose:** Ensure required documentation exists

**Required Files:**
- `docs/architecture/1-introduction-vision.md`
- `docs/architecture/2-executive-summary.md`
- `docs/architecture/6-complete-reference-implementation.md`
- `docs/prd/index.md`
- `CLAUDE.md`
- `README.md`

**Blocking:** Yes (must pass for merge)

---

### 8. **CI Summary** (no timeout)

**Purpose:** Aggregate all job results and enforce merge rules

**Blocking Rules:**
- **MUST PASS:**
  - Unit tests
  - Linting
  - Documentation validation

- **WARNINGS ONLY:**
  - Type checking
  - Security scanning
  - Integration tests
  - E2E tests

**Output:** Comprehensive status summary with actionable feedback

---

## Pre-commit Hooks

Pre-commit hooks run locally before each commit to catch issues early.

### Installation

```bash
# Install pre-commit
source .venv/bin/activate
pip install pre-commit

# Install git hooks
pre-commit install
```

### Hooks Configured

1. **File Quality** (~1s)
   - Trailing whitespace removal
   - End-of-file fixer
   - YAML/JSON/TOML validation
   - Merge conflict detection
   - Large file detection (max 1MB)
   - Mixed line ending detection

2. **Python Linting** (~2s)
   - Ruff (with auto-fix)
   - Ruff format

3. **Type Checking** (~2s)
   - mypy on raglite/ package only

4. **Security** (~4s)
   - Gitleaks secret detection
   - Bandit Python security linter
   - Safety dependency vulnerability scanner

**Total Execution Time:** ~12-15 seconds

---

## CI Triggers

### Automatic Triggers

- **Push to branches:**
  - `main`
  - `develop`
  - `story/**` (feature branches)
  - `epic/**` (epic branches)

- **Pull Requests:**
  - Target: `main` or `develop`

### Manual Trigger

Use the "Run workflow" button in GitHub Actions to manually trigger CI on any branch.

---

## Environment Setup

### Self-Hosted Runner Requirements

- **OS:** macOS
- **Python:** 3.11+
- **UV:** Package manager (pre-installed)
- **Docker:** For Qdrant integration tests
- **Persistent Services:**
  - Qdrant on localhost:6333

### Required Secrets

Configure in GitHub repository settings:

- `ANTHROPIC_API_KEY` - For Claude API integration tests

---

## Local Development Workflow

### 1. Pre-commit Validation

```bash
# Test hooks before committing
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
```

### 2. Manual CI Simulation

```bash
# Activate environment
source .venv/bin/activate

# Lint checks
ruff check .
black --check raglite/ tests/ scripts/
isort --check-only raglite/ tests/ scripts/

# Type checking
mypy raglite/ --ignore-missing-imports

# Security scanning
bandit -r raglite/ -f screen
safety check

# Unit tests
pytest tests/unit/ -n auto --cov=raglite

# Integration tests (requires Qdrant)
pytest tests/integration/ -v

# E2E tests
pytest tests/e2e/ -v
```

### 3. Test Coverage Analysis

```bash
# Generate coverage report
pytest tests/unit/ --cov=raglite --cov-report=html

# View HTML report
open htmlcov/index.html
```

---

## Troubleshooting

### Pre-commit Hooks Fail

**Issue:** Hooks modify files and fail

**Solution:**
1. Pre-commit auto-fixes many issues
2. Review changes: `git diff`
3. Stage fixed files: `git add .`
4. Retry commit

### CI Jobs Timeout

**Issue:** Jobs exceed timeout limits

**Cause:** Usually integration tests with Qdrant connectivity issues

**Solution:**
1. Verify Qdrant is running: `curl http://localhost:6333/collections`
2. Restart Qdrant: `docker restart raglite-qdrant`
3. Re-run failed jobs in GitHub Actions

### Security Scan False Positives

**Issue:** Bandit reports false positives

**Solution:**
Add inline comment to suppress:
```python
result = eval(user_input)  # nosec B307 - validated input
```

Or configure in `pyproject.toml`:
```toml
[tool.bandit.skips]
B101 = "Allow assert statements"
```

---

## Comparison with Original CI

### Improvements from Powerpoint Agent Generator

1. **Parallel Job Execution**
   - Old: 2 sequential jobs
   - New: 8 parallel jobs

2. **Explicit Security Scanning**
   - Old: Basic safety check
   - New: Bandit + Safety with artifact reporting

3. **Separated Concerns**
   - Old: Mixed quality checks
   - New: Dedicated lint, type-check, security jobs

4. **Better Artifact Management**
   - Old: Coverage only
   - New: Test reports, security reports, coverage

5. **Documentation Validation**
   - Old: Manual check
   - New: Automated validation of required docs

6. **Non-Blocking Warnings**
   - Old: All checks blocking
   - New: Strategic blocking (tests + lint) vs warnings (types + security)

---

## CI Performance Metrics

| Job | Typical Duration | Timeout |
|-----|------------------|---------|
| Lint | 2-3 min | 5 min |
| Type Check | 2-3 min | 5 min |
| Security | 2-3 min | 5 min |
| Unit Tests | 5-7 min | 10 min |
| Integration | 8-10 min | 15 min |
| E2E Tests | 8-10 min | 15 min |
| Docs Validation | 10 sec | 5 min |
| CI Summary | 5 sec | none |

**Total Pipeline:** 10-15 minutes (parallel execution)

---

## Best Practices

1. **Before Pushing:**
   - Run pre-commit hooks: `pre-commit run --all-files`
   - Run unit tests locally: `pytest tests/unit/`

2. **PR Creation:**
   - Ensure CI passes before requesting review
   - Address linting/formatting issues immediately
   - Security warnings require investigation

3. **Failed CI:**
   - Check logs in GitHub Actions
   - Reproduce failure locally
   - Fix and force-push (use `--force-with-lease`)

4. **Dependency Updates:**
   - Run safety check after updates
   - Update pre-commit hooks monthly: `pre-commit autoupdate`

---

## Future Enhancements

- [ ] Add Codecov integration for coverage tracking
- [ ] Add performance benchmarking job
- [ ] Add dependency license scanning
- [ ] Add Docker image building
- [ ] Add deployment automation (Phase 4)

---

## References

- **Powerpoint Agent Generator CI:** `/Users/ricardocarvalho/DeveloperFolder/Powerpoint Agent Generator/.github/workflows/ci.yml`
- **Pre-commit Framework:** https://pre-commit.com/
- **UV Package Manager:** https://github.com/astral-sh/uv
- **Ruff Linter:** https://github.com/astral-sh/ruff
- **Bandit Security:** https://bandit.readthedocs.io/
