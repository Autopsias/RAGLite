# Performance & Scalability

## Performance Targets (from PRD)

| Metric | Target (NFR) | Architecture Strategy |
|--------|--------------|----------------------|
| **Retrieval Accuracy** | 90%+ (NFR6) | Contextual Retrieval (98.1%) or GraphRAG |
| **Source Attribution** | 95%+ (NFR7) | Metadata tracking, citation system |
| **Table Extraction** | 95%+ (NFR8) | Docling (97.9% accuracy) |
| **Query Response (p50)** | <5 sec (NFR13) | HNSW indexing, caching, async |
| **Query Response (p95)** | <15 sec (NFR13) | Load balancing, auto-scaling |
| **Complex Workflow** | <30 sec (NFR13) | Multi-agent parallelization |
| **Forecast Accuracy** | ±15% (NFR10) | Hybrid approach (±8% achieved) |
| **Uptime (Production)** | 99%+ (NFR1) | Multi-AZ, health checks, auto-recovery |
| **Concurrent Users** | 10+ (NFR3) | Horizontal scaling, connection pooling |

## Scalability Architecture

**Horizontal Scaling:**

```
Single User:
┌────────┐
│Gateway │ → 5 Microservices (1 task each)
└────────┘

10 Users:
┌────────┐ ┌────────┐
│Gateway │ │Gateway │ → 5 Microservices (2 tasks each)
└────────┘ └────────┘

50 Users (Auto-scaled):
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Gateway │ │Gateway │ │Gateway │ │Gateway │
└────────┘ └────────┘ └────────┘ └────────┘
    │
    └─> 5 Microservices (5-10 tasks each)
    └─> Qdrant Cloud (scaled instance)
```

**Performance Optimizations:**

1. **Vector Search Optimization:**
   - HNSW indexing (sub-100ms queries)
   - Embedding caching for repeated queries
   - Qdrant gRPC for lower latency

2. **Multi-Agent Parallelization:**
   - Retrieval + GraphRAG agents run concurrently
   - AWS Strands async task execution
   - Reduces complex workflow time by 40-60%

3. **Caching Strategy:**
   - LRU cache for frequently asked queries
   - Embedding cache (avoid re-embedding same text)
   - TTL: 1 hour for query results

4. **Connection Pooling:**
   - Qdrant client connection pool (20 connections)
   - Neo4j driver connection pool (10 connections)
   - Reduces connection overhead by 70%

## Load Testing Strategy

**Test Scenarios:**

1. **Baseline Performance:**
   - 1 concurrent user
   - 10 queries (varied complexity)
   - Measure: p50, p95, p99 latency

2. **Concurrent User Load:**
   - Ramp up: 1 → 10 → 25 → 50 users
   - Sustained load: 5 minutes per level
   - Measure: Response time degradation, error rate

3. **Stress Test:**
   - 100 concurrent users
   - Find breaking point
   - Validate graceful degradation

4. **Spike Test:**
   - Sudden spike: 5 → 50 users in 10 seconds
   - Measure: Auto-scaling response time
   - Validate: No dropped requests

**Load Testing Tools:**
- Locust (Python-based load testing)
- k6 (performance testing)
- CloudWatch Metrics (production monitoring)

---
