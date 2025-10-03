# Security & Compliance

## Security Architecture

RAGLite implements **defense-in-depth** security to protect sensitive financial data.

## Security Layers

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Network Security                             │
│  ├─ VPC isolation (AWS)                                │
│  ├─ Private subnets for services                       │
│  ├─ Security groups (least privilege)                  │
│  └─ HTTPS/TLS encryption in transit                    │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Layer 2: Application Security                         │
│  ├─ API rate limiting (prevent abuse)                  │
│  ├─ Input validation (prevent injection)               │
│  ├─ Output sanitization (prevent XSS)                  │
│  └─ MCP protocol security (tool authorization)         │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Layer 3: Authentication & Authorization               │
│  ├─ IAM roles (AWS services)                           │
│  ├─ MCP client authentication (API keys)               │
│  ├─ Service-to-service auth (internal)                 │
│  └─ Principle of least privilege                       │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Layer 4: Data Security                                │
│  ├─ Encryption at rest (S3 AES256, NFR12)             │
│  ├─ Encryption in transit (TLS 1.2+)                   │
│  ├─ Secrets management (AWS Secrets Manager)           │
│  └─ Data sanitization (PII detection)                  │
└─────────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────┐
│  Layer 5: Audit & Monitoring                           │
│  ├─ Query audit trail (NFR14)                          │
│  ├─ Access logs (CloudWatch)                           │
│  ├─ Anomaly detection (suspicious queries)             │
│  └─ Security alerts (CloudWatch Alarms)                │
└─────────────────────────────────────────────────────────┘
```

## Security Requirements (from PRD)

**NFR12: Encryption at Rest**
- ✅ S3 bucket server-side encryption (AES256)
- ✅ Qdrant data encryption (if supported by managed service)
- ✅ Neo4j encryption (Aura managed encryption)

**NFR13: Encryption in Transit**
- ✅ HTTPS/TLS 1.2+ for all external communications
- ✅ Service-to-service encrypted connections within VPC
- ✅ MCP protocol over HTTPS (Streamable HTTP transport)

**NFR14: Audit Logging**
- ✅ Query audit trail (who asked what, when)
- ✅ Document access logs (who accessed which documents)
- ✅ Admin action logs (ingestion, configuration changes)
- ✅ Structured JSON logging for queryability

**NFR15: Secrets Management**
- ✅ AWS Secrets Manager for API keys (production)
- ✅ Environment variables with .env (local dev only)
- ✅ Automated secret rotation (90-day policy)
- ✅ No secrets in code or version control

## Threat Modeling

**Threat: Unauthorized Access to Financial Data**
- **Mitigation:**
  - IAM roles with least privilege
  - VPC network isolation
  - MCP client API key authentication
  - Query audit trail for detection

**Threat: Data Exfiltration**
- **Mitigation:**
  - Encryption at rest and in transit
  - Rate limiting on queries
  - Anomaly detection for unusual query patterns
  - CloudWatch alarms for excessive data access

**Threat: Injection Attacks (Prompt Injection, SQL Injection)**
- **Mitigation:**
  - Input validation and sanitization
  - Parameterized queries (Qdrant, Neo4j)
  - LLM output filtering
  - Cypher query sanitization (Neo4j)

**Threat: API Key Compromise**
- **Mitigation:**
  - Secrets Manager with rotation
  - API rate limiting
  - Key scoping (per-client keys)
  - Immediate revocation capability

**Threat: Denial of Service (DoS)**
- **Mitigation:**
  - ALB rate limiting
  - WAF rules (if needed)
  - Auto-scaling (handle legitimate load spikes)
  - Circuit breakers for service protection

## Compliance Considerations

**Data Residency:**
- All data stored in single AWS region (configurable)
- Document retention policies (S3 lifecycle rules)
- GDPR/CCPA deletion capabilities (if required)

**Access Controls:**
- Role-based access (future: multi-user support)
- Audit trail for compliance reporting
- Data lineage tracking (document → chunks → responses)

---
