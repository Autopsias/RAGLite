# Technical Specification: Epic 5 - Production Readiness & Real-Time Operations

**Epic:** Epic 5 - Production Readiness & Real-Time Operations
**Phase:** Phase 4 (Weeks 13-16)
**Goal:** Deploy production-ready cloud infrastructure with real-time updates and monitoring
**Status:** NOT STARTED
**Version:** 1.0
**Date:** 2025-10-12
**Author:** Sarah (Product Owner)

---

## 1. Executive Summary

Epic 5 transitions RAGLite from local development to production cloud deployment, enabling team rollout and daily operational use. Focus on AWS deployment, real-time document updates, performance optimization, and comprehensive monitoring.

**Target:** Infrastructure-as-Code (Terraform), CI/CD pipelines, monitoring dashboards
**Timeline:** 4 weeks (Weeks 13-16)
**Outcome:** Production-ready system with 99%+ uptime, <5s query response, auto-updating knowledge base

**Capabilities Enabled:**
- AWS cloud deployment (ECS/Fargate)
- Real-time document ingestion (file watching)
- Monitoring & alerting (CloudWatch)
- CI/CD automation (GitHub Actions)
- Scalability for 10+ concurrent users
- Disaster recovery & backup

---

## 2. Architecture Overview

### 2.1 Production Cloud Architecture (AWS)

```
┌──────────────────────────────────────────────────────────────┐
│  Internet / Users                                            │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│  AWS Application Load Balancer (ALB)                        │
│  • HTTPS/TLS termination                                    │
│  • Health checks                                            │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│  AWS ECS (Fargate)                                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  RAGLite Container (main.py)                          │ │
│  │  • MCP Server                                         │ │
│  │  • Auto-scaling (2-4 tasks)                          │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│  Data Layer (AWS)                                           │
│  ├─ Qdrant Cloud (managed vector DB)                       │
│  ├─ Neo4j Aura (managed graph DB, if Epic 2)              │
│  ├─ S3 Bucket (document storage with versioning)          │
│  └─ AWS Secrets Manager (API keys, credentials)           │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│  Operations & Monitoring                                    │
│  ├─ CloudWatch (logs, metrics, dashboards)                 │
│  ├─ CloudWatch Alarms (error rate, latency)               │
│  ├─ AWS EventBridge (S3 event → Lambda → ingestion)       │
│  └─ AWS Backup (automated backups)                         │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Real-Time Document Ingestion Flow

```
1. User uploads PDF to S3 bucket (s3://raglite-documents/)
   └─> S3 Event Notification triggered

2. AWS EventBridge routes event to Lambda function
   └─> Lambda: raglite-document-ingestion-trigger

3. Lambda invokes ECS task (run ingestion pipeline)
   └─> ECS Task: python -m raglite.ingestion.pipeline <s3_path>

4. Ingestion pipeline:
   a. Download PDF from S3
   b. Extract text/tables (Docling)
   c. Chunk document
   d. Generate embeddings (Fin-E5)
   e. Store in Qdrant Cloud

5. Knowledge base updated (latency: <5 minutes)
   └─> Queries now return results from new document
```

---

## 3. Component Specifications

### 3.1 Cloud Infrastructure (Terraform ~500 lines)

**Purpose:** Infrastructure-as-Code for reproducible AWS deployment.

**Key Resources:**
```hcl
# terraform/main.tf

# VPC and Networking
resource "aws_vpc" "raglite" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support = true
  enable_dns_hostnames = true
}

# ECS Cluster
resource "aws_ecs_cluster" "raglite" {
  name = "raglite-cluster"
}

# ECS Fargate Service
resource "aws_ecs_service" "raglite" {
  name = "raglite-service"
  cluster = aws_ecs_cluster.raglite.id
  task_definition = aws_ecs_task_definition.raglite.arn
  desired_count = 2  # Min 2 for high availability
  launch_type = "FARGATE"

  load_balancer {
    target_group_arn = aws_lb_target_group.raglite.arn
    container_name = "raglite"
    container_port = 8000
  }
}

# S3 Bucket for Documents
resource "aws_s3_bucket" "documents" {
  bucket = "raglite-documents"
  versioning {
    enabled = true  # Document version history
  }
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"  # Encryption at rest
      }
    }
  }
}

# EventBridge Rule (S3 event → Lambda)
resource "aws_cloudwatch_event_rule" "document_upload" {
  name = "raglite-document-upload"
  event_pattern = jsonencode({
    source = ["aws.s3"],
    detail-type = ["Object Created"],
    detail = {
      bucket = { name = [aws_s3_bucket.documents.id] }
    }
  })
}

# Lambda Function (ingestion trigger)
resource "aws_lambda_function" "ingestion_trigger" {
  function_name = "raglite-ingestion-trigger"
  runtime = "python3.11"
  handler = "lambda_function.lambda_handler"
  role = aws_iam_role.lambda_exec.arn

  environment {
    variables = {
      ECS_CLUSTER = aws_ecs_cluster.raglite.name
      ECS_TASK_DEFINITION = aws_ecs_task_definition.raglite.arn
    }
  }
}

# Secrets Manager
resource "aws_secretsmanager_secret" "api_keys" {
  name = "raglite/api-keys"
}
```

**NFRs:**
- NFR1: 99%+ uptime (multi-AZ deployment, health checks)
- NFR12: Encryption at rest (S3 KMS, Qdrant encryption)
- NFR13: Secrets management (AWS Secrets Manager)

**Testing:**
- `terraform plan` → validate infrastructure changes
- `terraform apply` → deploy to staging environment
- Integration tests: Validate ECS service, S3 events, Lambda triggers

---

### 3.2 CI/CD Pipeline (GitHub Actions ~300 lines)

**Purpose:** Automated testing, building, and deployment.

**Workflow File:** `.github/workflows/ci-cd.yml`

```yaml
name: RAGLite CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-and-format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install Ruff
        run: pip install ruff mypy
      - name: Ruff format check
        run: ruff format --check .
      - name: Ruff lint
        run: ruff check .
      - name: MyPy type check
        run: mypy raglite/

  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run pytest with coverage
        run: pytest --cov=raglite --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          token: ${{ secrets.CODECOV_TOKEN }}

  integration-tests:
    runs-on: ubuntu-latest
    services:
      qdrant:
        image: qdrant/qdrant:v1.15.1
        ports:
          - 6333:6333
    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        run: pytest tests/integration/

  accuracy-validation:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    steps:
      - uses: actions/checkout@v3
      - name: Run ground truth test set
        run: python scripts/run-accuracy-tests.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - name: Check accuracy threshold
        run: |
          ACCURACY=$(cat accuracy_report.json | jq '.accuracy')
          if (( $(echo "$ACCURACY < 0.70" | bc -l) )); then
            echo "FAIL: Accuracy $ACCURACY < 70%"
            exit 1
          elif (( $(echo "$ACCURACY < 0.90" | bc -l) )); then
            echo "WARN: Accuracy $ACCURACY < 90% (target not met)"
          fi

  build-and-push:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    needs: [lint-and-format, unit-tests, integration-tests, accuracy-validation]
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t raglite:${{ github.sha }} .
      - name: Push to Docker Hub
        run: |
          echo ${{ secrets.DOCKERHUB_TOKEN }} | docker login -u ${{ secrets.DOCKERHUB_USERNAME }} --password-stdin
          docker push raglite:${{ github.sha }}
          docker tag raglite:${{ github.sha }} raglite:latest
          docker push raglite:latest

  deploy-production:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    needs: [build-and-push]
    environment: production
    steps:
      - name: Deploy to AWS ECS
        run: |
          aws ecs update-service \
            --cluster raglite-cluster \
            --service raglite-service \
            --force-new-deployment
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**Pre-Commit Hooks:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.16.1
    hooks:
      - id: gitleaks
```

**NFRs:**
- Automated testing: 70%+ unit test coverage
- Accuracy gate: <70% blocks deployment
- Pipeline performance: <25 min full run

**Testing:**
- Local pre-commit validation: `pre-commit run --all-files`
- CI/CD dry run: Create PR, validate pipeline passes
- Deployment validation: Verify ECS task updated, health checks pass

---

### 3.3 Real-Time Document Ingestion (Lambda ~50 lines)

**Purpose:** Trigger automatic ingestion on S3 document upload.

**Lambda Function:** `lambda/ingestion_trigger.py`

```python
import boto3
import os

ecs_client = boto3.client('ecs')

def lambda_handler(event, context):
    """Trigger ECS task to ingest new S3 document.

    Args:
        event: S3 event notification (ObjectCreated)
        context: Lambda context

    Returns:
        Status response
    """
    # Extract S3 bucket and key from event
    bucket = event['detail']['bucket']['name']
    key = event['detail']['object']['key']
    s3_path = f"s3://{bucket}/{key}"

    # Run ECS task (ingestion pipeline)
    response = ecs_client.run_task(
        cluster=os.environ['ECS_CLUSTER'],
        taskDefinition=os.environ['ECS_TASK_DEFINITION'],
        launchType='FARGATE',
        overrides={
            'containerOverrides': [{
                'name': 'raglite',
                'command': [
                    'python', '-m', 'raglite.ingestion.pipeline',
                    '--s3-path', s3_path
                ]
            }]
        }
    )

    print(f"Triggered ingestion for {s3_path}: {response['taskArn']}")
    return {
        'statusCode': 200,
        'body': f"Ingestion triggered for {s3_path}"
    }
```

**NFRs:**
- FR26: Detect new documents automatically
- FR27: <5 min ingestion latency (detection → Qdrant update)

**Testing:**
- Unit test: Mock ECS client, validate task invocation
- Integration test: Upload file to S3, verify Lambda triggered, check Qdrant for new chunks

---

### 3.4 Monitoring & Logging (CloudWatch ~100 lines)

**Purpose:** Comprehensive observability for production operations.

**CloudWatch Dashboard (Terraform):**

```hcl
resource "aws_cloudwatch_dashboard" "raglite" {
  dashboard_name = "RAGLite-Production"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric",
        properties = {
          title = "Query Response Time (p50, p95)",
          metrics = [
            ["RAGLite", "QueryLatency", { stat = "p50" }],
            ["RAGLite", "QueryLatency", { stat = "p95" }]
          ],
          yAxis = { left = { min = 0, max = 15000 } }  # 0-15s
        }
      },
      {
        type = "metric",
        properties = {
          title = "Error Rate",
          metrics = [
            ["RAGLite", "Errors", { stat = "Sum" }]
          ]
        }
      },
      {
        type = "metric",
        properties = {
          title = "ECS Service Health",
          metrics = [
            ["AWS/ECS", "RunningTasksCount"],
            ["AWS/ECS", "DesiredTasksCount"]
          ]
        }
      },
      {
        type = "log",
        properties = {
          title = "Recent Errors (Last 1 hour)",
          query = "fields @timestamp, @message | filter level = 'ERROR' | sort @timestamp desc | limit 20"
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name = "raglite-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods = 2
  metric_name = "Errors"
  namespace = "RAGLite"
  period = 300  # 5 minutes
  statistic = "Sum"
  threshold = 10  # >10 errors in 5 min
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name = "raglite-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods = 2
  metric_name = "QueryLatency"
  namespace = "RAGLite"
  period = 300
  statistic = "p95"
  threshold = 15000  # 15 seconds
  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

**Application Logging (Python):**

```python
# Emit custom CloudWatch metrics
import boto3

cloudwatch = boto3.client('cloudwatch')

def emit_query_latency(latency_ms: float):
    cloudwatch.put_metric_data(
        Namespace='RAGLite',
        MetricData=[{
            'MetricName': 'QueryLatency',
            'Value': latency_ms,
            'Unit': 'Milliseconds'
        }]
    )
```

**NFRs:**
- NFR30: Performance metrics tracked (query latency, error rate)
- NFR14: Audit logging (all queries, answers, admin actions)

**Testing:**
- Validation: View dashboard, verify metrics populating
- Alert testing: Trigger error condition, verify SNS notification

---

### 3.5 Scalability & Performance (Auto-Scaling ~50 lines)

**Purpose:** Handle 10+ concurrent users with auto-scaling.

**ECS Auto-Scaling (Terraform):**

```hcl
resource "aws_appautoscaling_target" "ecs" {
  max_capacity = 4
  min_capacity = 2
  resource_id = "service/${aws_ecs_cluster.raglite.name}/${aws_ecs_service.raglite.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_cpu" {
  name = "cpu-scaling"
  policy_type = "TargetTrackingScaling"
  resource_id = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0  # Target 70% CPU utilization
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
```

**Load Testing (Locust):**

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class RAGLiteUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def query_documents(self):
        self.client.post("/mcp/query_financial_documents", json={
            "query": "What was Q3 2024 revenue?",
            "top_k": 5
        })
```

**Run:** `locust -f tests/load/locustfile.py --users 10 --spawn-rate 2`

**NFRs:**
- NFR4: 50+ queries per day with consistent performance
- Scalability: 10+ concurrent users (auto-scale to 4 tasks)

**Testing:**
- Load testing: Simulate 10 concurrent users for 10 minutes
- Validation: Query response time <5s (p50), <15s (p95)
- Auto-scaling: Verify ECS scales from 2 → 4 tasks under load

---

### 3.6 Disaster Recovery (AWS Backup ~50 lines)

**Purpose:** Automated backups for data protection.

**Backup Plan (Terraform):**

```hcl
resource "aws_backup_vault" "raglite" {
  name = "raglite-backup-vault"
}

resource "aws_backup_plan" "raglite" {
  name = "raglite-backup-plan"

  rule {
    rule_name = "daily-backup"
    target_vault_name = aws_backup_vault.raglite.name
    schedule = "cron(0 2 * * ? *)"  # 2 AM UTC daily

    lifecycle {
      delete_after = 30  # Retain 30 days
    }
  }
}

resource "aws_backup_selection" "raglite" {
  plan_id = aws_backup_plan.raglite.id
  name = "raglite-resources"

  resources = [
    aws_s3_bucket.documents.arn,
    # Note: Qdrant Cloud / Neo4j Aura have built-in backups
  ]
}
```

**NFRs:**
- Backup retention: 30 days
- Recovery Time Objective (RTO): <4 hours
- Recovery Point Objective (RPO): <24 hours (daily backups)

**Testing:**
- Restore testing: Backup → delete data → restore → validate
- Validation: Restored system functional, queries return correct results

---

## 4. Implementation Timeline

### Week 13: Cloud Infrastructure & CI/CD

**Stories:**
- Story 5.1: Cloud Infrastructure Architecture
- Story 5.3: Environment Configuration & Secrets Management
- Story 5.12: CI/CD Pipeline Setup & Automation

**Deliverables:**
- Terraform infrastructure-as-code (VPC, ECS, S3, Lambda)
- GitHub Actions CI/CD pipeline (lint, test, build, deploy)
- Pre-commit hooks (Ruff, MyPy, Gitleaks)
- AWS Secrets Manager configured

---

### Week 14: Deployment & Real-Time Operations

**Stories:**
- Story 5.2: Containerization & Cloud Deployment
- Story 5.4: Data Encryption at Rest
- Story 5.5: File Watching & Real-Time Document Detection
- Story 5.6: Incremental Indexing & Version History

**Deliverables:**
- ECS service deployed to AWS
- S3 event → Lambda → ECS ingestion pipeline
- Document versioning enabled
- Encryption at rest validated

---

### Week 15: Monitoring & Performance

**Stories:**
- Story 5.7: Monitoring & Logging Infrastructure
- Story 5.8: Performance Optimization
- Story 5.9: Scalability Validation

**Deliverables:**
- CloudWatch dashboard with metrics
- Auto-scaling configured (2-4 ECS tasks)
- Load testing validated (10 concurrent users)
- Performance: <5s (p50), <15s (p95) query latency

---

### Week 16: Validation & Documentation

**Stories:**
- Story 5.10: Disaster Recovery & Backup
- Story 5.11: Production Validation & User Acceptance
- Story 5.13: API Documentation & MCP Tool Reference
- Story 5.14: Knowledge Transfer & Team Onboarding Documentation

**Deliverables:**
- Automated backups configured
- MVP success criteria validated (90%+ accuracy, user satisfaction 8/10+)
- API reference documentation
- Developer onboarding guide

**Success Criteria:**
- 99%+ uptime (multi-AZ, health checks)
- <5s query response (p50), <15s (p95)
- 10+ queries per week (real usage)
- User satisfaction 8/10+
- Team rollout ready

---

## 5. Success Criteria

### Phase 4 Completion Criteria (End of Week 16)

**Must Meet (GO Criteria):**
1. ✅ 99%+ uptime (validated over 1 week)
2. ✅ <5s query response time (p50), <15s (p95) under load
3. ✅ Real-time document updates (<5 min ingestion latency)
4. ✅ Auto-scaling handles 10+ concurrent users
5. ✅ CI/CD pipeline functional (automated testing, deployment)
6. ✅ Monitoring dashboards operational (CloudWatch)
7. ✅ Disaster recovery tested (backup → restore validated)
8. ✅ MVP success criteria met:
   - 90%+ retrieval accuracy
   - User satisfaction 8/10+
   - Used for 90%+ of financial queries (replacing manual methods)

**Decision Gate:**
- **IF** all criteria met → **TEAM ROLLOUT APPROVED**
- **IF** uptime <95% or performance degraded → **EXTEND Phase 4** (infrastructure debugging)

---

## 6. References

### Architecture Documents
- `docs/architecture/8-phased-implementation-strategy-v11-simplified.md` - Phase 4 timeline
- `docs/architecture/5-technology-stack-definitive.md` - AWS, Terraform, CloudWatch

### PRD Documents
- `docs/prd/epic-5-production-readiness-real-time-operations.md` - Epic 5 stories

### AWS Documentation
- ECS Fargate: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
- CloudWatch: https://docs.aws.amazon.com/cloudwatch/
- Terraform AWS Provider: https://registry.terraform.io/providers/hashicorp/aws/latest/docs

---

**Document Version:** 1.0
**Created:** 2025-10-12
**Author:** Sarah (Product Owner)
**Next Update:** After Epic 4 completion (before Week 13)
