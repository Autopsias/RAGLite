# CI/CD Pipeline Architecture

## Overview

RAGLite implements a **production-grade CI/CD pipeline** following 2025 best practices for Python microservices, AI/ML systems, and AWS ECS deployments. The pipeline enforces quality gates, security scanning, accuracy regression testing, and zero-downtime deployments.

**⚠️ Pragmatic Implementation Note:**

The CI/CD workflow described below represents the **complete, mature state** of the pipeline. **Start simple and add complexity incrementally:**

**Phase 1 (MVP - Week 1):**
- Basic linting (Black, Ruff)
- Unit tests with coverage
- Manual deployment to dev

**Phase 2 (Weeks 2-3):**
- Add integration tests
- Automated dev deployment
- Docker builds

**Phase 3 (Weeks 4-6):**
- Security scanning (Bandit, Trivy)
- Accuracy regression tests
- Staging environment

**Phase 4 (Production-Ready):**
- Full 5-stage pipeline
- Canary deployments
- Auto-rollback
- Cost tracking

**Anti-pattern:** Implementing all stages upfront delays first deployment and adds maintenance burden before product-market fit.

## CI/CD Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Developer Push/PR                                               │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 1: Code Quality & Security (Parallel)                    │
│  ├─ Linting (Black, Ruff, isort)                                │
│  ├─ Type Checking (mypy)                                        │
│  ├─ Security Scan (Bandit SAST)                                 │
│  ├─ Secret Detection (truffleHog)                               │
│  └─ Dependency Scan (Safety, pip-audit)                         │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 2: Multi-Layer Testing (Parallel Matrix)                 │
│  ├─ Unit Tests (pytest, 80%+ coverage)                          │
│  ├─ Integration Tests (Testcontainers)                          │
│  ├─ Accuracy Regression Tests (Ground truth validation)         │
│  ├─ RAG Pipeline Tests (Retrieval + generation)                 │
│  └─ LLM Cost Tracking (OpenAI usage API)                        │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 3: Docker Build & Scan (Per Service)                     │
│  ├─ Multi-stage build (builder + runtime)                       │
│  ├─ Layer caching (Poetry cache, pip wheels)                    │
│  ├─ Trivy vulnerability scan                                    │
│  ├─ Push to ECR with semantic tags                              │
│  └─ Image size validation (<500MB runtime)                      │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 4: Deployment (Environment-Specific)                     │
│  ├─ Dev: Auto-deploy on merge to main                           │
│  ├─ Staging: Manual approval + smoke tests                      │
│  ├─ Prod: Approval + canary deployment (10% → 50% → 100%)       │
│  └─ Health check validation (30s timeout)                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│  Stage 5: Post-Deployment Validation                            │
│  ├─ Smoke tests (critical endpoints)                            │
│  ├─ Accuracy validation (subset of ground truth)                │
│  ├─ Performance benchmarks (p50, p95 latency)                   │
│  ├─ Cost anomaly detection (LLM spend)                          │
│  └─ Auto-rollback on SLO breach                                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## Complete GitHub Actions Workflows

### Primary CI Workflow

**File:** `.github/workflows/ci.yml`

```yaml
name: RAGLite CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  POETRY_VERSION: "1.8.2"
  AWS_REGION: us-east-1

jobs:
  # ============================================================
  # STAGE 1: Code Quality & Security
  # ============================================================
  code-quality:
    name: Code Quality & Linting
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: ${{ env.POETRY_VERSION }}
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Cache Poetry dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pypoetry
            .venv
          key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
          restore-keys: |
            ${{ runner.os }}-poetry-

      - name: Install dependencies
        run: poetry install --no-interaction --no-ansi --with dev

      - name: Format check (Black)
        run: poetry run black --check .

      - name: Import sort check (isort)
        run: poetry run isort --check-only .

      - name: Lint (Ruff)
        run: poetry run ruff check .

      - name: Type check (mypy)
        run: poetry run mypy services/ orchestrator/ shared/
        continue-on-error: true  # Warn but don't fail on type errors initially

  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    permissions:
      security-events: write  # For uploading to Security tab
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1

      - name: Install dependencies
        run: poetry install --no-interaction --with dev

      - name: SAST with Bandit
        run: |
          poetry run bandit -r services/ orchestrator/ shared/ -f json -o bandit-report.json
        continue-on-error: true

      - name: Upload Bandit results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: bandit-security-report
          path: bandit-report.json

      - name: Dependency vulnerability scan (Safety)
        run: |
          poetry run safety check --json > safety-report.json
        continue-on-error: true

      - name: Secret detection (truffleHog)
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD

      - name: Python dependency audit (pip-audit)
        run: |
          poetry run pip-audit --format json > pip-audit-report.json
        continue-on-error: true

  # ============================================================
  # STAGE 2: Multi-Layer Testing
  # ============================================================
  unit-tests:
    name: Unit Tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Poetry
        uses: snok/install-poetry@v1

      - name: Cache Poetry dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pypoetry
            .venv
          key: ${{ runner.os }}-poetry-${{ matrix.python-version }}-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        run: poetry install --no-interaction --with dev,test

      - name: Run unit tests with coverage
        run: |
          poetry run pytest \
            --cov=services \
            --cov=orchestrator \
            --cov=shared \
            --cov-report=xml \
            --cov-report=term \
            --cov-branch \
            --junitxml=pytest-report.xml \
            -v \
            services/*/tests/ \
            orchestrator/tests/ \
            shared/tests/

      - name: Coverage threshold enforcement (80%)
        run: |
          poetry run coverage report --fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          flags: unit-tests-py${{ matrix.python-version }}
          name: unit-coverage

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: pytest-results-${{ matrix.python-version }}
          path: pytest-report.xml

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
      neo4j:
        image: neo4j:5-community
        env:
          NEO4J_AUTH: neo4j/test-password
        ports:
          - 7687:7687
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1

      - name: Install dependencies
        run: poetry install --no-interaction --with dev,test

      - name: Run integration tests
        env:
          QDRANT_HOST: localhost
          QDRANT_PORT: 6333
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          NEO4J_PASSWORD: test-password
        run: |
          poetry run pytest \
            --cov=services \
            --cov-append \
            --cov-report=xml \
            -v \
            -m integration \
            tests/integration/

      - name: Upload integration coverage
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          flags: integration-tests

  accuracy-regression:
    name: Accuracy Regression Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1

      - name: Install dependencies
        run: poetry install --no-interaction --with test

      - name: Run accuracy validation (ground truth)
        env:
          CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
        run: |
          poetry run python scripts/run-accuracy-tests.py \
            --threshold 0.90 \
            --output accuracy-report.json

      - name: Validate accuracy threshold
        run: |
          poetry run python scripts/validate-accuracy.py \
            --input accuracy-report.json \
            --retrieval-threshold 0.90 \
            --attribution-threshold 0.95

      - name: Upload accuracy report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: accuracy-regression-report
          path: accuracy-report.json

  llm-cost-tracking:
    name: LLM Cost Tracking
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4

      - name: Track LLM API usage
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # Run test suite and capture API call metrics
          poetry run python scripts/track-llm-costs.py \
            --output llm-cost-report.json

      - name: Comment cost estimate on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('llm-cost-report.json', 'utf8'));
            const body = `## 💰 LLM Cost Estimate

            **Total estimated cost for this PR:** $${report.total_cost.toFixed(4)}

            | Service | Tokens (Input) | Tokens (Output) | Cost |
            |---------|----------------|-----------------|------|
            | Claude 3.7 Sonnet | ${report.claude.input_tokens.toLocaleString()} | ${report.claude.output_tokens.toLocaleString()} | $${report.claude.cost.toFixed(4)} |
            | Embeddings (Fin-E5) | ${report.embeddings.tokens.toLocaleString()} | - | $${report.embeddings.cost.toFixed(4)} |

            **Warning threshold:** $5.00 per PR
            ${report.total_cost > 5.0 ? '⚠️ **Cost exceeds threshold!**' : '✅ Within budget'}
            `;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });

  # ============================================================
  # STAGE 3: Docker Build & Security Scan
  # ============================================================
  docker-build:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: [code-quality, security-scan, unit-tests]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    strategy:
      matrix:
        service:
          - ingestion
          - retrieval
          - graphrag
          - forecasting
          - insights
          - gateway
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Extract metadata (tags, labels)
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.login-ecr.outputs.registry }}/raglite-${{ matrix.service }}
          tags: |
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=ref,event=branch
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Cache Docker layers
        uses: actions/cache@v4
        with:
          path: /tmp/.buildx-cache
          key: ${{ runner.os }}-buildx-${{ matrix.service }}-${{ github.sha }}
          restore-keys: |
            ${{ runner.os }}-buildx-${{ matrix.service }}-

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ./services/${{ matrix.service }}
          file: ./services/${{ matrix.service }}/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=local,src=/tmp/.buildx-cache
          cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max
          build-args: |
            PYTHON_VERSION=${{ env.PYTHON_VERSION }}
            POETRY_VERSION=${{ env.POETRY_VERSION }}

      - name: Move cache
        run: |
          rm -rf /tmp/.buildx-cache
          mv /tmp/.buildx-cache-new /tmp/.buildx-cache

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.login-ecr.outputs.registry }}/raglite-${{ matrix.service }}:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results-${{ matrix.service }}.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results-${{ matrix.service }}.sarif'
          category: 'trivy-${{ matrix.service }}'

      - name: Validate image size
        run: |
          IMAGE_SIZE=$(docker image inspect ${{ steps.login-ecr.outputs.registry }}/raglite-${{ matrix.service }}:${{ github.sha }} --format='{{.Size}}')
          MAX_SIZE=524288000  # 500MB
          if [ $IMAGE_SIZE -gt $MAX_SIZE ]; then
            echo "Error: Image size ${IMAGE_SIZE} bytes exceeds maximum ${MAX_SIZE} bytes"
            exit 1
          fi
          echo "✅ Image size: $(($IMAGE_SIZE / 1024 / 1024))MB (within limit)"

  # ============================================================
  # STAGE 4: Deployment
  # ============================================================
  deploy-dev:
    name: Deploy to Development
    runs-on: ubuntu-latest
    needs: [docker-build, integration-tests, accuracy-regression]
    if: github.ref == 'refs/heads/main'
    environment:
      name: development
      url: https://dev.raglite.internal
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to ECS (Development)
        run: |
          for service in gateway ingestion retrieval forecasting insights; do
            aws ecs update-service \
              --cluster raglite-dev-cluster \
              --service raglite-dev-${service} \
              --force-new-deployment \
              --region ${{ env.AWS_REGION }}
          done

      - name: Wait for deployment stabilization
        run: |
          for service in gateway ingestion retrieval forecasting insights; do
            aws ecs wait services-stable \
              --cluster raglite-dev-cluster \
              --services raglite-dev-${service} \
              --region ${{ env.AWS_REGION }}
          done

      - name: Run smoke tests
        run: |
          poetry run python scripts/smoke-tests.py \
            --env development \
            --endpoint https://dev.raglite.internal

  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [deploy-dev]
    if: github.ref == 'refs/heads/main'
    environment:
      name: staging
      url: https://staging.raglite.internal
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Deploy to ECS (Staging) with canary
        run: |
          # Canary deployment: 10% → 50% → 100%
          ./scripts/canary-deploy.sh staging 10 50 100

      - name: Validate staging deployment
        run: |
          poetry run pytest tests/e2e/ \
            --env staging \
            --endpoint https://staging.raglite.internal

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://raglite.production
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Blue/Green deployment (Production)
        run: |
          # Use AWS CodeDeploy for blue/green deployment
          aws deploy create-deployment \
            --application-name raglite-prod \
            --deployment-group-name raglite-prod-dg \
            --deployment-config-name CodeDeployDefault.ECSCanary10Percent5Minutes \
            --region ${{ env.AWS_REGION }}

      - name: Monitor deployment health
        run: |
          ./scripts/monitor-deployment.sh production 300

      - name: Run production smoke tests
        run: |
          poetry run python scripts/smoke-tests.py \
            --env production \
            --endpoint https://raglite.production

  # ============================================================
  # STAGE 5: Post-Deployment Validation
  # ============================================================
  post-deploy-validation:
    name: Post-Deployment Validation
    runs-on: ubuntu-latest
    needs: [deploy-production]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Run accuracy validation (production subset)
        env:
          CLAUDE_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
        run: |
          poetry run python scripts/run-accuracy-tests.py \
            --env production \
            --subset critical \
            --threshold 0.90

      - name: Performance benchmark
        run: |
          poetry run python scripts/performance-benchmark.py \
            --env production \
            --duration 300 \
            --concurrent-users 10

      - name: Cost anomaly check
        env:
          AWS_COST_EXPLORER_ENABLED: true
        run: |
          poetry run python scripts/check-cost-anomalies.py \
            --lookback-days 7 \
            --threshold-increase 50

      - name: Notify deployment status
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: ${{ secrets.SLACK_CHANNEL_ID }}
          slack-message: |
            ✅ RAGLite deployed to production successfully!

            **Commit:** ${{ github.sha }}
            **Author:** ${{ github.actor }}
            **Accuracy:** Validated ✓
            **Performance:** Within SLO ✓
            **Cost:** No anomalies ✓
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

---

## Multi-Stage Dockerfile Example

**File:** `services/retrieval/Dockerfile`

```dockerfile