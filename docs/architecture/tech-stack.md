# RAGLite Technology Stack

**Version:** 1.1 (Definitive)
**Status:** LOCKED - No additions without user approval
**Last Updated:** October 3, 2025

---

## Overview

This document defines the **complete and definitive** technology stack for RAGLite. All technologies listed here have been validated through Week 0 Integration Spike and are approved for use.

**🔒 CRITICAL:** NO additional libraries, frameworks, or dependencies may be added without explicit user approval. This constraint ensures MVP simplicity and prevents over-engineering.

---

## Core Technology Stack

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **PDF Extraction** | Docling | Latest | Extract text/tables from PDFs | 97.9% table accuracy, DocLayNet-based |
| **Excel Processing** | openpyxl + pandas | Latest | Extract tabular data | Standard Python libraries |
| **Embedding Model** | Fin-E5 (finance-adapted) | Latest | Generate semantic vectors | 71.05% financial domain accuracy |
| **Chunking** | Contextual Retrieval | N/A | LLM-generated context per chunk | 98.1% retrieval accuracy |
| **Vector Database** | Qdrant | 1.11+ | Store/search embeddings | HNSW indexing, sub-5s retrieval |
| **Graph Database** | Neo4j | 5.x | Knowledge graph (Phase 2 conditional) | Cypher queries, managed cloud option |
| **MCP Server** | FastMCP (MCP Python SDK) | 1.x | Expose tools via MCP protocol | Official SDK, 19k GitHub stars |
| **LLM (Primary)** | Claude 3.7 Sonnet | via API | Reasoning, analysis, synthesis | State-of-art reasoning, 200K context |
| **Forecasting** | Prophet | 1.1+ | Time-series baseline | Facebook library, seasonal handling |
| **Backend Language** | Python | 3.11+ | All application code | RAG ecosystem standard, async support |
| **API Framework** | FastAPI | 0.115+ (optional) | REST endpoints if needed | High performance, async native |
| **Document Storage** | S3 (cloud) / Local FS (dev) | N/A | Store ingested documents | Scalable, versioning, encryption |
| **Secrets** | AWS Secrets Manager / .env | N/A | API keys, credentials | Secure, rotatable |
| **Containerization** | Docker + Docker Compose | Latest | Local development | Service isolation, reproducible |
| **Cloud Platform** | AWS | N/A | Production deployment (Phase 4) | ECS/Fargate, managed services |
| **IaC** | Terraform | Latest | Infrastructure as Code (Phase 4) | Version-controlled infrastructure |
| **CI/CD** | GitHub Actions | N/A | Testing and deployment | Git-integrated |
| **Monitoring** | CloudWatch + Prometheus | N/A | Performance tracking (Phase 4) | AWS native + open-source |
| **Logging** | Structured JSON | N/A | Application logs, audit trail | CloudWatch-compatible |
| **Testing** | pytest + pytest-asyncio | Latest | Python unit/integration tests | Standard testing stack |

---

## Development Dependencies

| Category | Tool | Version | Purpose | Phase |
|----------|------|---------|---------|-------|
| **Package Manager** | uv | Latest | Fast Python dependency management | Phase 1+ |
| **Formatter** | Black | 23.3+ | Code formatting | Phase 1+ |
| **Linter** | Ruff | 0.0.270+ | Fast Python linter | Phase 1+ |
| **Type Checker** | mypy | 1.4+ (optional) | Static type checking | Phase 4 |
| **Pre-commit** | pre-commit | 3.x | Git hooks for quality | Phase 1+ |

---

## Phase-Specific Technology Usage

### Phase 1: Monolithic MVP (Weeks 1-5)

**Active Technologies:**

- Python 3.11+
- Docling (PDF extraction)
- Fin-E5 (embeddings)
- Qdrant (vector DB via Docker Compose)
- FastMCP (MCP server)
- Claude 3.7 Sonnet API (synthesis)
- pytest + pytest-asyncio (testing)
- uv (fast dependency management)
- Docker + Docker Compose (local development)

**NOT Used in Phase 1:**

- Neo4j (Phase 2 conditional)
- Prophet (Phase 3 forecasting)
- AWS services (Phase 4 deployment)
- Terraform (Phase 4 IaC)
- CloudWatch/Prometheus (Phase 4 monitoring)

---

### Phase 2: GraphRAG (Weeks 5-8) - CONDITIONAL

**ONLY IMPLEMENT IF Phase 1 accuracy <80%**

**Additional Technologies:**

- Neo4j 5.x (knowledge graph)
- Neo4j Python Driver (graph queries)

**Rationale:** Multi-hop relational queries may require graph database. Only add if vector search proves insufficient.

---

### Phase 3: Intelligence Features (Weeks 9-12 or 5-8)

**Additional Technologies:**

- Prophet 1.1+ (time-series forecasting)
- NumPy/Pandas (data manipulation for forecasting)

**Rationale:** Forecasting and trend analysis features require time-series library.

---

### Phase 4: Production Readiness (Weeks 13-16)

**Additional Technologies:**

- AWS ECS/Fargate (container orchestration)
- AWS S3 (document storage)
- AWS Secrets Manager (credential management)
- AWS CloudWatch (monitoring, logging)
- Terraform (infrastructure as code)
- Prometheus + Grafana (metrics dashboards)

**Rationale:** Production deployment requires cloud infrastructure, monitoring, and IaC.

---

## NOT Approved (Do Not Use)

The following technologies are **explicitly forbidden** to prevent over-engineering:

| Technology | Why Forbidden | Use Instead |
|------------|---------------|-------------|
| ❌ LangChain / LangGraph | Over-abstraction for MVP | Direct SDK calls (Claude API, Qdrant) |
| ❌ LlamaIndex | Unnecessary RAG framework | Qdrant + custom retrieval logic |
| ❌ Haystack | Complex framework | Qdrant directly |
| ❌ Semantic Kernel | Over-engineering | Direct SDK calls |
| ❌ SQLAlchemy | ORM not needed | Pydantic models only |
| ❌ Redis / Memcached | Premature optimization | Add in Phase 4 if needed |
| ❌ Celery / RQ | Task queue not needed | Async Python sufficient for monolith |
| ❌ Custom abstraction libraries | Over-engineering | Write direct, simple code |

**Rationale:** RAGLite is a 600-800 line MVP. Additional frameworks add complexity without value. Use SDK documentation directly.

---

## Dependency Management

### uv (pyproject.toml + uv.lock)

**Why uv?** 10-100× faster than Poetry, Rust-based, PEP 517 compliant, built-in caching.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "raglite"
version = "1.1.0"
description = "AI-powered financial document analysis via RAG"
authors = [{name = "Your Name", email = "you@example.com"}]
requires-python = ">=3.11,<4.0"

dependencies = [
    "fastmcp==2.12.4",
    "docling==2.55.1",
    "qdrant-client==1.15.1",
    "pydantic>=2.0,<3.0",
    "pydantic-settings>=2.0,<3.0",
    "anthropic>=0.18.0,<1.0.0",
    "openpyxl>=3.1,<4.0",
    "pandas>=2.0,<3.0",
]

[dependency-groups]
dev = [
    "pytest==8.4.2",
    "pytest-asyncio==1.2.0",
    "black>=23.3,<24.0",
    "ruff>=0.0.270,<1.0.0",
    "pytest-cov>=4.1,<5.0",
]
```

### Installation

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies from uv.lock (typical workflow)
uv sync --frozen

# Add new dependency (ONLY with user approval)
uv add <package-name>

# Add dev dependency
uv add --group dev <package-name>

# Run commands
uv run pytest
uv run black raglite/
uv run ruff check raglite/
```

---

## Version Pinning Strategy

**Week 0 Spike Recommendation:** Pin all dependency versions to avoid breaking changes.

### Pinning Levels

- **Exact pins (==x.y.z):** Critical dependencies (FastMCP, Qdrant, Claude SDK)
- **Compatible pins (^x.y):** Stable libraries (Pydantic, pandas)
- **Latest:** Only for development tools (black, ruff)

**Example:**

```toml
fastmcp = "==1.0.5"  # Exact pin (critical)
qdrant-client = "^1.11.0"  # Compatible pin
pytest = "*"  # Latest (dev tool)
```

---

## SDK Documentation References

Always use **official documentation** when integrating these technologies:

| Technology | Official Docs |
|------------|---------------|
| FastMCP | <https://github.com/jlowin/fastmcp> |
| Qdrant | <https://qdrant.tech/documentation/> |
| Docling | <https://github.com/DS4SD/docling> |
| Claude API | <https://docs.anthropic.com/> |
| Pydantic | <https://docs.pydantic.dev/> |
| Prophet | <https://facebook.github.io/prophet/> |
| Neo4j | <https://neo4j.com/docs/> |

**CRITICAL:** Use SDK examples from official docs, not blog posts or tutorials. No custom wrappers or "convenience layers" allowed.

---

## Technology Decision Gates

### Week 0 (Integration Spike) - COMPLETE ✅

**Goal:** Validate core stack (Docling + Fin-E5 + Qdrant + FastMCP)
**Result:** APPROVED with conditional fixes (page number extraction)

### Week 5 (Phase 1 Completion)

**Decision:** Neo4j (Phase 2) needed?

- **IF accuracy ≥90%:** SKIP Phase 2 (GraphRAG) → Proceed to Phase 3
- **IF accuracy 80-89%:** ACCEPTABLE, defer Neo4j
- **IF accuracy <80% + multi-hop failures:** ADD Neo4j (Phase 2)

### Week 12 (Phase 3 Completion)

**Decision:** Microservices migration needed?

- **IF performance issues:** Consider microservices (Phase 4)
- **IF no issues:** Keep monolith, optimize in place

---

## Technology Swap Rules

**IF a technology proves unsuitable, follow this process:**

1. **Document failure mode** (accuracy, performance, integration blocker)
2. **Get user approval** for alternative technology
3. **Update this document** with rationale for swap
4. **Re-run affected tests** to validate swap

**Example:** Week 0 found Docling page number extraction failing. IF unfixable:

- Proposed alternative: PyMuPDF for page detection + Docling for tables
- Rationale: NFR7 (95%+ source attribution) requires page numbers
- Approval: User decision required

---

## Summary

**Approved Stack (Phase 1):** 15 technologies
**Forbidden Alternatives:** 8+ frameworks explicitly banned
**Version Strategy:** Pin critical dependencies
**Decision Gates:** Week 5 (Neo4j), Week 12 (microservices)

**Questions or Technology Requests?**

- Check: Is it in this document? NO → Ask user first
- Check: Is there a simpler approach? YES → Use that instead
- Check: Does the reference implementation show it? NO → Don't add it

**Source of Truth:** This document (tech-stack.md) + Week 0 Spike Report validation
