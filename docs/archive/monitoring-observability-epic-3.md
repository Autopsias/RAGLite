# Monitoring & Observability - Epic 3 Graceful Degradation

**Status:** Production-Ready (Story 3.7)
**Target:** Epic 5 CloudWatch/DataDog Integration
**Last Updated:** 2025-11-18

---

## Overview

RAGLite's Epic 3 agentic orchestration includes production-grade observability for monitoring workflow degradation, error rates, and system health. All metrics are logged via structured logging (CloudWatch-ready) and workflow execution metadata.

**Key Observability Features:**
- Structured logging with rich metadata
- Workflow metrics tracking (Story 3.7 AC5)
- Error classification and tier degradation tracking
- OpenTelemetry spans (built-in via AWS Strands)
- CloudWatch/DataDog integration patterns

---

## Structured Logging Fields

All graceful degradation events are logged with structured `extra={}` fields for CloudWatch aggregation.

### Workflow-Level Logging

**Logger:** `raglite.agentic.fallback.handle_workflow_failure()`

```python
logger.warning(
    "Workflow failure - initiating graceful degradation",
    extra={
        "query": str,                    # Original user query
        "complexity": str,                # "simple" | "analytical"
        "error_type": str,                # "timeout" | "connection" | "api_failure" | "unexpected"
        "partial_results_count": int,     # Number of successful agents
        "total_time_ms": int,             # Total execution time
        "degradation_tier": str,          # "full" | "partial" | "epic1_fallback"
    }
)
```

### Agent-Level Logging

**Logger:** `raglite.agentic.fallback.execute_with_timeout()`

```python
logger.warning(
    "Agent execution timeout",
    extra={
        "agent": str,                    # Agent name (retrieval, analysis, synthesis)
        "instruction": str,               # Task instruction (truncated to 100 chars)
        "timeout_seconds": float,         # Timeout threshold (15s)
        "error_type": str,                # "timeout" | "connection" | "api_failure" | "unexpected"
    }
)
```

### Workflow Metrics Logging

**Logger:** `raglite.agentic.fallback.log_workflow_metrics()`

```python
logger.info(
    "Workflow metrics",
    extra={
        "query_id": str,                  # Unique query identifier
        "query": str,                     # Original query
        "tier": str,                      # "full_orchestration" | "partial_analysis" | "epic1_fallback"
        "confidence": str,                # "high" | "medium" | "low" | "none"
        "execution_time_ms": int,         # Total workflow time
        "agents_invoked": list[str],      # ["retrieval", "analysis", "synthesis"]
        "agents_failed": list[str],       # ["synthesis"] for Tier 2
        "error_type": str | None,         # Error classification
        "timestamp": str,                 # ISO 8601 timestamp
    }
)
```

---

## CloudWatch Integration (Epic 5)

### Log Group Configuration

**Recommended Log Groups:**
```yaml
/raglite/application:
  - retention: 30 days
  - fields: level, message, query, tier, error_type, execution_time_ms
  - dimensions: [tier, error_type, agent]

/raglite/metrics:
  - retention: 90 days
  - fields: query_id, tier, confidence, agents_invoked, agents_failed
  - dimensions: [tier, confidence, error_type]
```

### CloudWatch Logs Insights Queries

#### 1. Tier Success Rates (Daily)

```sql
fields @timestamp, tier, confidence
| filter message like /Workflow metrics/
| stats count(*) as total_queries,
        sum(tier = "full_orchestration") as tier_1_count,
        sum(tier = "partial_analysis") as tier_2_count,
        sum(tier = "epic1_fallback") as tier_4_count
  by bin(@timestamp, 1d)
| parse tier_1_count / total_queries * 100 as tier_1_success_rate
| parse tier_2_count / total_queries * 100 as tier_2_fallback_rate
| parse tier_4_count / total_queries * 100 as tier_4_epic1_rate
| sort @timestamp desc
```

**Target Metrics:**
- Tier 1 success rate: ≥95%
- Tier 2 fallback rate: <5%
- Tier 4 Epic 1 rate: <0.1%

#### 2. Error Type Distribution

```sql
fields @timestamp, error_type
| filter message like /Workflow failure/
| stats count(*) as error_count by error_type
| sort error_count desc
```

#### 3. Agent Failure Breakdown

```sql
fields @timestamp, agents_failed
| filter message like /Workflow metrics/ and ispresent(agents_failed) and agents_failed != []
| stats count(*) as failure_count by agents_failed
| sort failure_count desc
```

#### 4. Execution Time Distribution by Tier

```sql
fields @timestamp, tier, execution_time_ms
| filter message like /Workflow metrics/
| stats avg(execution_time_ms) as avg_time,
        max(execution_time_ms) as max_time,
        pct(execution_time_ms, 50) as p50,
        pct(execution_time_ms, 95) as p95
  by tier
```

#### 5. Degradation Events Over Time

```sql
fields @timestamp, tier, confidence
| filter message like /Workflow failure/ or message like /initiating graceful degradation/
| stats count(*) as degradation_events by bin(@timestamp, 1h)
| sort @timestamp desc
```

---

## CloudWatch Metrics (Custom)

### Metric Namespace: `RAGLite/Workflows`

#### Metric 1: Tier Success Rate

```python
# Example CloudWatch PutMetricData (Epic 5 implementation)
cloudwatch.put_metric_data(
    Namespace='RAGLite/Workflows',
    MetricData=[
        {
            'MetricName': 'TierSuccessRate',
            'Dimensions': [
                {'Name': 'Tier', 'Value': 'tier_1_full_orchestration'},
            ],
            'Value': 96.5,  # Calculated from workflow logs
            'Unit': 'Percent',
            'Timestamp': datetime.utcnow()
        },
    ]
)
```

#### Metric 2: Agent Failure Rate

```python
cloudwatch.put_metric_data(
    Namespace='RAGLite/Workflows',
    MetricData=[
        {
            'MetricName': 'AgentFailureRate',
            'Dimensions': [
                {'Name': 'Agent', 'Value': 'synthesis'},
                {'Name': 'ErrorType', 'Value': 'timeout'},
            ],
            'Value': 3.2,  # Percentage
            'Unit': 'Percent',
            'Timestamp': datetime.utcnow()
        },
    ]
)
```

#### Metric 3: Workflow Execution Time

```python
cloudwatch.put_metric_data(
    Namespace='RAGLite/Workflows',
    MetricData=[
        {
            'MetricName': 'WorkflowExecutionTime',
            'Dimensions': [
                {'Name': 'Tier', 'Value': 'full_orchestration'},
            ],
            'Value': 12450,  # milliseconds
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow(),
            'StatisticValues': {
                'SampleCount': 100,
                'Sum': 1245000,
                'Minimum': 8200,
                'Maximum': 18500
            }
        },
    ]
)
```

---

## CloudWatch Alarms

### Alarm 1: Low Tier 1 Success Rate

**Trigger:** Tier 1 success rate drops below 90%

```yaml
AlarmName: RAGLite-Low-Tier1-Success-Rate
MetricName: TierSuccessRate
Namespace: RAGLite/Workflows
Dimensions:
  - Name: Tier
    Value: tier_1_full_orchestration
Statistic: Average
Period: 300  # 5 minutes
EvaluationPeriods: 3
Threshold: 90.0
ComparisonOperator: LessThanThreshold
TreatMissingData: notBreaching
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:raglite-alerts
AlarmDescription: |
  Tier 1 (full orchestration) success rate below 90%. Indicates degraded
  workflow performance. Check agent failures and error types.
```

### Alarm 2: High Tier 4 Epic 1 Rate

**Trigger:** Complete workflow failures exceed 1%

```yaml
AlarmName: RAGLite-High-Tier4-Failure-Rate
MetricName: TierSuccessRate
Namespace: RAGLite/Workflows
Dimensions:
  - Name: Tier
    Value: tier_4_epic1_fallback
Statistic: Average
Period: 300
EvaluationPeriods: 2  # More urgent
Threshold: 1.0
ComparisonOperator: GreaterThanThreshold
TreatMissingData: notBreaching
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:raglite-critical-alerts
AlarmDescription: |
  CRITICAL: Tier 4 Epic 1 fallback rate exceeds 1%. Complete workflow
  failures indicate systemic issues (Qdrant down, API outages, etc.).
```

### Alarm 3: Agent Timeout Rate Spike

**Trigger:** Agent timeouts exceed 5%

```yaml
AlarmName: RAGLite-High-Agent-Timeout-Rate
MetricName: AgentFailureRate
Namespace: RAGLite/Workflows
Dimensions:
  - Name: ErrorType
    Value: timeout
Statistic: Average
Period: 300
EvaluationPeriods: 3
Threshold: 5.0
ComparisonOperator: GreaterThanThreshold
TreatMissingData: notBreaching
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:raglite-alerts
AlarmDescription: |
  Agent timeout rate exceeds 5%. Indicates slow LLM inference or
  large document sets. Consider scaling or query optimization.
```

### Alarm 4: Workflow Execution Time P95

**Trigger:** P95 execution time exceeds 20s

```yaml
AlarmName: RAGLite-Slow-Workflow-Execution
MetricName: WorkflowExecutionTime
Namespace: RAGLite/Workflows
ExtendedStatistic: p95
Period: 300
EvaluationPeriods: 2
Threshold: 20000  # milliseconds
ComparisonOperator: GreaterThanThreshold
TreatMissingData: notBreaching
AlarmActions:
  - arn:aws:sns:us-east-1:123456789012:raglite-alerts
AlarmDescription: |
  P95 workflow execution time exceeds 20s (NFR5 target: <20s).
  Check orchestration overhead and agent latency.
```

---

## Example CloudWatch Dashboard (JSON)

Save as: `cloudwatch-dashboard-epic3-graceful-degradation.json`

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Tier Success Rates (Last 24h)",
        "metrics": [
          [ "RAGLite/Workflows", "TierSuccessRate", { "stat": "Average", "label": "Tier 1 (Full)", "color": "#2ca02c" } ],
          [ "...", { "stat": "Average", "label": "Tier 2 (Partial)", "color": "#ff7f0e" } ],
          [ "...", { "stat": "Average", "label": "Tier 4 (Epic 1)", "color": "#d62728" } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "period": 300,
        "yAxis": {
          "left": {
            "min": 0,
            "max": 100,
            "label": "Success Rate (%)"
          }
        },
        "annotations": {
          "horizontal": [
            {
              "value": 95,
              "label": "Tier 1 Target (≥95%)",
              "fill": "above"
            },
            {
              "value": 5,
              "label": "Tier 2 Threshold (<5%)",
              "fill": "below"
            },
            {
              "value": 1,
              "label": "Tier 4 Critical (>1%)",
              "fill": "above"
            }
          ]
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Error Type Distribution (Last 24h)",
        "metrics": [
          [ "RAGLite/Workflows", "AgentFailureRate", { "stat": "Sum", "label": "Timeout" } ],
          [ "...", { "stat": "Sum", "label": "Connection Error" } ],
          [ "...", { "stat": "Sum", "label": "API Failure" } ],
          [ "...", { "stat": "Sum", "label": "Unexpected" } ]
        ],
        "view": "pie",
        "region": "us-east-1",
        "period": 86400
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Workflow Execution Time (P50, P95)",
        "metrics": [
          [ "RAGLite/Workflows", "WorkflowExecutionTime", { "stat": "p50", "label": "P50" } ],
          [ "...", { "stat": "p95", "label": "P95" } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "period": 300,
        "yAxis": {
          "left": {
            "min": 0,
            "label": "Latency (ms)"
          }
        },
        "annotations": {
          "horizontal": [
            {
              "value": 10000,
              "label": "P50 Target (<10s)"
            },
            {
              "value": 20000,
              "label": "P95 Target (<20s)"
            }
          ]
        }
      }
    },
    {
      "type": "log",
      "properties": {
        "title": "Recent Degradation Events",
        "query": "SOURCE '/raglite/application'\n| fields @timestamp, tier, error_type, query\n| filter message like /Workflow failure/\n| sort @timestamp desc\n| limit 20",
        "region": "us-east-1"
      }
    }
  ]
}
```

---

## OpenTelemetry Spans (AWS Strands Built-In)

AWS Strands automatically generates OpenTelemetry spans for all agent executions.

### Span Structure

```
Span: analytical_query (root)
  ├─ Span: orchestrator.invoke_async
  │   ├─ Span: retrieval_agent.execute
  │   │   ├─ duration_ms: 2847
  │   │   ├─ status: success
  │   │   └─ attributes: {agent_type: "retrieval", query: "..."}
  │   ├─ Span: analysis_agent.execute
  │   │   ├─ duration_ms: 5123
  │   │   ├─ status: success
  │   │   └─ attributes: {agent_type: "analysis", chunks_count: 5}
  │   └─ Span: synthesis_agent.execute
  │       ├─ duration_ms: 4012
  │       ├─ status: error (timeout)
  │       └─ attributes: {agent_type: "synthesis", error_type: "timeout"}
  └─ Span: graceful_degradation
      ├─ duration_ms: 350
      ├─ status: success
      └─ attributes: {fallback_tier: "partial", confidence: "medium"}
```

### Custom Span Attributes (Story 3.7)

Add custom degradation tier attributes to spans:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def handle_workflow_failure(...) -> FallbackResponse:
    """Handle workflow failure with OpenTelemetry span attributes."""

    current_span = trace.get_current_span()

    # Add custom degradation tier attribute
    current_span.set_attribute("raglite.degradation_tier", fallback_tier.value)
    current_span.set_attribute("raglite.error_type", error_type.value)
    current_span.set_attribute("raglite.confidence", confidence)
    current_span.set_attribute("raglite.agents_failed_count", len(agents_failed))

    # ... rest of graceful degradation logic
```

**Epic 5 Integration:** Export spans to AWS X-Ray for distributed tracing visualization.

---

## DataDog Integration (Alternative to CloudWatch)

If using DataDog instead of CloudWatch:

### DataDog Agent Configuration

```yaml
# /etc/datadog-agent/conf.d/raglite.d/conf.yaml
logs:
  - type: file
    path: /var/log/raglite/application.log
    service: raglite
    source: python
    sourcecategory: agentic-orchestration
    tags:
      - env:production
      - epic:3
      - feature:graceful-degradation

  - type: file
    path: /var/log/raglite/metrics.log
    service: raglite-metrics
    source: python
    sourcecategory: workflow-metrics
    tags:
      - env:production
      - metrics:workflow-degradation
```

### DataDog Custom Metrics

```python
from datadog import statsd

# Tier success rate
statsd.gauge('raglite.workflow.tier_1_success_rate', 96.5, tags=['tier:full_orchestration'])

# Agent failure rate
statsd.increment('raglite.agent.failure', tags=['agent:synthesis', 'error:timeout'])

# Execution time histogram
statsd.histogram('raglite.workflow.execution_time_ms', 12450, tags=['tier:full'])
```

---

## Production Monitoring Checklist (Epic 5)

### Pre-Deployment

- [ ] Configure CloudWatch Log Groups (`/raglite/application`, `/raglite/metrics`)
- [ ] Set up CloudWatch Alarms (Tier 1 success rate, Tier 4 failure rate, etc.)
- [ ] Create CloudWatch Dashboard (4-tier success rates, error distribution)
- [ ] Configure SNS topics for alarm notifications
- [ ] Set up OpenTelemetry exporter to AWS X-Ray
- [ ] Test log aggregation queries (Logs Insights)

### Post-Deployment

- [ ] Monitor Tier 1 success rate ≥95%
- [ ] Validate Tier 2 fallback rate <5%
- [ ] Ensure Tier 4 Epic 1 rate <0.1%
- [ ] Check P50/P95 workflow execution times (<10s/<20s)
- [ ] Review error type distribution for patterns
- [ ] Verify alarm triggers correctly
- [ ] Set up weekly metrics review cadence

---

## References

- **Architecture:** `docs/architecture/epic-3-orchestration-design.md` (Error Handling Strategy section)
- **User Guide:** `docs/user-guide-graceful-degradation.md`
- **Story 3.7:** `docs/sprint-artifacts/3-7-graceful-degradation-for-workflow-failures.md`
- **CloudWatch Logs Insights:** https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html
- **OpenTelemetry:** https://opentelemetry.io/docs/instrumentation/python/
- **AWS X-Ray:** https://docs.aws.amazon.com/xray/latest/devguide/

---

**Created By:** Dev (Ricardo)
**Date:** 2025-11-18
**Next Step:** Epic 5 production deployment and CloudWatch integration
