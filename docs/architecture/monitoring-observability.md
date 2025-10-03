# Monitoring & Observability

## Observability Stack

```
┌─────────────────────────────────────────────────────────┐
│  Metrics Layer (CloudWatch + Prometheus)               │
│  ├─ Service health (up/down, errors)                   │
│  ├─ Query latency (p50, p95, p99)                      │
│  ├─ Retrieval accuracy (ongoing validation)            │
│  ├─ Resource utilization (CPU, memory, disk)           │
│  └─ Cost tracking (LLM API usage)                      │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Logging Layer (CloudWatch Logs)                       │
│  ├─ Structured JSON logs (queryable)                   │
│  ├─ Query audit trail (NFR14)                          │
│  ├─ Error logs with stack traces                       │
│  ├─ Performance logs (slow queries)                    │
│  └─ Security logs (auth failures, anomalies)           │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Alerting Layer (CloudWatch Alarms + SNS)              │
│  ├─ Service down alerts (critical)                     │
│  ├─ High error rate alerts (warning)                   │
│  ├─ Slow query alerts (p95 > 15s)                      │
│  ├─ Cost anomaly alerts (LLM overuse)                  │
│  └─ Security alerts (auth failures, injection)         │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Dashboards (CloudWatch Dashboards)                    │
│  ├─ Service health overview                            │
│  ├─ Query performance trends                           │
│  ├─ Accuracy metrics (retrieval, attribution)          │
│  ├─ Cost breakdown (LLM usage, infrastructure)         │
│  └─ User activity (queries/day, users)                 │
└─────────────────────────────────────────────────────────┘
```

## Key Metrics to Monitor

**Service Health Metrics:**
```python