# 5. Technology Stack (Definitive)

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **PDF Extraction** | Docling | 2.55.1 | Extract text/tables from PDFs | 97.9% table accuracy, DocLayNet-based |
| **PDF Backend** | pypdfium | N/A | Docling backend for faster, lower-memory PDF processing | ✅ APPROVED (Phase 1): 1.7-2.5x speedup, 50-60% memory reduction |
| **Excel Processing** | openpyxl | ≥3.1,<4.0 | Extract tabular data (spreadsheets) | Standard Python library for Excel |
| **Excel Processing** | pandas | ≥2.0,<3.0 | Extract tabular data (data manipulation) | Standard Python library for data analysis |
| **Embedding Model** | sentence-transformers (Fin-E5) | 5.1.1 | Generate semantic vectors | 71.05% financial domain accuracy |
| **Chunking** | Contextual Retrieval | N/A | LLM-generated context per chunk | 98.1% retrieval accuracy |
| **Vector Database** | Qdrant | ≥1.15.1 | Store/search embeddings | HNSW indexing, sub-5s retrieval |
| **SQL Database** | PostgreSQL | 16+ | Structured table storage for financial data | ⚠️ CONDITIONAL (Phase 2B/2C): IF Phase 2A fixed chunking <70% accuracy |
| **Graph Database** | Neo4j | 5.x | Knowledge graph for entity relationships | ⚠️ CONDITIONAL (Phase 2C): IF Phase 2B structured multi-index <75% accuracy |
| **Agent Framework** | LangGraph + AWS Strands | Latest | Multi-agent orchestration for query planning | ⚠️ CONDITIONAL (Phase 3): IF Phase 2 <85% accuracy |
| **MCP Server** | FastMCP (MCP Python SDK) | 2.12.4 | Expose tools via MCP protocol | Official SDK, 19k GitHub stars |
| **LLM (Primary)** | Claude 3.7 Sonnet (Anthropic SDK) | ≥0.18.0,<1.0.0 | Reasoning, analysis, synthesis | State-of-art reasoning, 200K context |
| **Forecasting** | Prophet | 1.1+ | Time-series baseline | Facebook library, seasonal handling |
| **Backend Language** | Python | ≥3.11,<4.0 | All application code | RAG ecosystem standard, async support |
| **Data Validation** | Pydantic | ≥2.0,<3.0 | Data models and validation | Type-safe, runtime validation |
| **Configuration** | Pydantic Settings | ≥2.0,<3.0 | Settings management | Environment variable loading |
| **Environment Variables** | python-dotenv | 1.1.1 | Load .env files | Development environment configuration |
| **HTTP Client** | httpx | ≥0.28.1,<1.0.0 | Async HTTP requests | Modern async HTTP client |
| **API Framework** | FastAPI | 0.115+ (optional) | REST endpoints if needed | High performance, async native |
| **Document Storage** | S3 (cloud) / Local FS (dev) | N/A | Store ingested documents | Scalable, versioning, encryption |
| **Secrets** | AWS Secrets Manager / .env | N/A | API keys, credentials | Secure, rotatable |
| **Containerization** | Docker + Docker Compose | Latest | Local development | Service isolation, reproducible |
| **Cloud Platform** | AWS | N/A | Production deployment (Phase 4) | ECS/Fargate, managed services |
| **IaC** | Terraform | Latest | Infrastructure as Code (Phase 4) | Version-controlled infrastructure |
| **CI/CD** | GitHub Actions | N/A | Testing and deployment | Git-integrated |
| **Monitoring** | CloudWatch + Prometheus | N/A | Performance tracking (Phase 4) | AWS native + open-source |
| **Logging** | Structured JSON | N/A | Application logs, audit trail | CloudWatch-compatible |
| **Testing** | pytest | 8.4.2 | Python unit/integration tests | Standard testing framework |
| **Async Testing** | pytest-asyncio | 1.2.0 | Async test support | Test async functions |
| **Test Coverage** | pytest-cov | ≥4.1,<5.0 | Code coverage reporting | Track test coverage |
| **Test Mocking** | pytest-mock | ≥3.12,<4.0 | Mock external dependencies | Isolated unit testing |
| **Parallel Testing** | pytest-xdist | ≥3.5,<4.0 | Parallel test execution | Faster test runs |
| **Test Timeouts** | pytest-timeout | ≥2.0,<3.0 | Test timeout enforcement | Prevent hanging tests |
| **Code Formatting** | Black | ≥23.3,<24.0 | Python code formatter | Consistent code style |
| **Linting** | Ruff | ≥0.0.270,<1.0.0 | Fast Python linter | Fast, comprehensive linting |
| **Import Sorting** | isort | ≥5.12,<6.0 | Import statement sorting | Organized imports |
| **Type Checking** | mypy | ≥1.4,<2.0 | Static type checking | Type safety (Phase 4) |
| **Pre-commit Hooks** | pre-commit | ≥3.0,<4.0 | Git pre-commit automation | Enforce quality gates |
| **PDF Testing** | pypdf | ≥4.0,<5.0 | PDF file manipulation for tests | Test PDF generation |

---

## Technology Stack Approval Status

**Phase 1 (APPROVED - Immediate)**:
- ✅ **pypdfium**: Docling backend for PDF optimization (1.7-2.5x speedup, 97.9% accuracy maintained)
  - **Rationale**: Empirically validated by Docling official benchmarks
  - **Risk**: LOW (production-proven, minimal integration required)
  - **Timeline**: 1-2 days implementation + validation

**Phase 2B-C (CONDITIONAL - Decision Gate Approval)**:
- ⚠️ **PostgreSQL**: ONLY if Phase 2A Fixed Chunking <70% accuracy (requires Structured Multi-Index)
  - **Trigger**: Phase 2A decision gate (T+17, Week 3 Day 3)
  - **Probability**: 15% (research suggests 80% chance Phase 2A achieves 68-72%)
  - **Decision Authority**: PM (John) approves based on accuracy validation results

- ⚠️ **Neo4j 5.x**: ONLY if Phase 2B Structured <75% accuracy (requires Hybrid Architecture)
  - **Trigger**: Phase 2B decision gate (IF triggered)
  - **Probability**: 5% (Phase 2B expected to achieve 70-80%)
  - **Decision Authority**: PM (John) approves based on accuracy validation results

**Phase 3 (CONDITIONAL - Decision Gate Approval)**:
- ⚠️ **LangGraph + AWS Strands**: ONLY if Phase 2 (any path) <85% accuracy (requires agentic coordination)
  - **Trigger**: Phase 2 completion decision gate
  - **Probability**: 20% (Phase 2 paths expected to achieve 70-92%)
  - **Decision Authority**: PM (John) approves based on accuracy validation results

**Decision Authority**: PM (John) approves at each decision gate based on accuracy validation results from AC3 ground truth test suite (50 queries).

**Technology Stack LOCKED Policy**: No additions without user approval (per CLAUDE.md constraints). All conditional technologies have been pre-approved with trigger conditions defined.

---

## Phase 2: Advanced RAG Enhancements (Conditional)

**⚠️ ONLY REQUIRED IF STORY 1.15B DECISION GATE TRIGGERS (Baseline <90% retrieval or <95% attribution)**

| Component | Technology | Version | Purpose | Required/Optional | Story |
|-----------|------------|---------|---------|-------------------|-------|
| **Hybrid Search (BM25)** | rank-bm25 | 0.2.2 | BM25 sparse vectors for keyword search | Required (if Phase 2) | Story 2.1 |
| **Hybrid Search (Fusion)** | Qdrant SDK + custom logic | N/A | Combine semantic + keyword search | Required (if Phase 2) | Story 2.1 |
| **Cross-Encoder Re-ranking** | sentence-transformers | ≥2.2,<3.0 | Two-stage retrieval with re-ranking | Required (Story 2.4) | Story 2.4 |
| **Financial Embeddings (Option 1)** | OpenAI API (text-embedding-3-large) | N/A | SOTA embedding quality ($0.13/1M tokens) | Optional (Story 2.2) | Story 2.2 |
| **Financial Embeddings (Option 2)** | FinBERT (ProsusAI/finbert) | N/A | Finance-specific embeddings (free, local) | Optional (Story 2.2) | Story 2.2 |
| **Query Expansion** | Anthropic API (Claude) | ≥0.18.0,<1.0.0 | LLM-generated query variations | Optional (Story 2.5) | Story 2.5 |
| **Multi-Vector Collections** | Qdrant multi-collection | ≥1.15.1 | Multiple embeddings per chunk | Optional (Story 2.6) | Story 2.6 |
| **Metadata Extraction** | Mistral Small (mistralai) | ≥1.9.11,<2.0.0 | LLM-based query metadata extraction (FREE tier) | Required (Story 2.4) | Story 2.4 |

**Phase 2 Technology Notes:**

1. **Hybrid Search (Story 2.1):**
   - **NEW DEPENDENCY APPROVED (2025-10-16):** `rank-bm25` library for BM25 implementation
   - Apache 2.0 license, industry-standard (1,800+ GitHub stars)
   - Used by major AI projects: camel-ai, MetaGPT, mem0ai, crawl4ai
   - BM25 parameters tuned for financial documents (k1=1.7, b=0.6)
   - Weighted sum fusion (alpha=0.7: 70% semantic, 30% BM25)
   - Expected impact: +15-20% retrieval accuracy
   - Latency impact: +70-150ms (well within NFR13 budget)

2. **Cross-Encoder (Story 2.4):**
   - Requires: `sentence-transformers` library
   - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` (pre-trained)
   - Adds ~150ms latency but +3-5% precision improvement
   - Compatible with existing architecture

3. **Financial Embeddings (Story 2.2):**
   - **Option A:** OpenAI API (commercial, best quality, API-based)
   - **Option B:** FinBERT (open-source, local inference, free)
   - **Decision:** A/B test both, adopt if >5% improvement over E5
   - May require Qdrant collection recreation (different vector dimensions)

4. **Query Expansion (Story 2.5):**
   - Reuses existing Anthropic API (already in stack for synthesis)
   - No new infrastructure required
   - Trade-off: +500-800ms latency for +2-5% recall

5. **Multi-Vector (Story 2.6):**
   - Advanced optimization (only if Stories 2.1-2.4 insufficient)
   - Requires 3x storage (3 Qdrant collections)
   - Requires Claude API for keyword/summary extraction
   - Significant complexity increase

6. **Metadata Extraction (Story 2.4):**
   - **NEW DEPENDENCY APPROVED (2025-10-24):** `mistralai` library for metadata extraction
   - Uses Mistral Small API (FREE tier, no cost)
   - Extracts structured metadata filters from natural language queries
   - JSON mode for reliable structured output
   - 15-field rich schema: company_name, metric_category, reporting_period, time_granularity, etc.
   - Latency: ~200-400ms per query (acceptable for metadata classification)
   - Zero cost alternative to GPT-4 or Claude for simple structured extraction
   - Reference: https://docs.mistral.ai/api/

**NOT Approved for OLD Phase 2 (DEPRECATED section below):**
- ❌ LangChain / LangGraph (NOT approved for element-aware chunking approach)
  - **NOTE**: LangGraph IS approved for NEW Epic 2 Phase 3 (Agentic Coordination) - see Technology Stack Approval Status section above
- ❌ LlamaIndex (use Qdrant directly)
- ❌ Haystack (use Qdrant directly)
- ❌ Custom abstraction libraries (keep it simple)
- ❌ Redis/Memcached (not needed for Phase 2)

**Simplicity Principle:** OLD Phase 2 (DEPRECATED) used **direct SDK calls** and **simple Python logic**. No frameworks, no abstraction layers, no over-engineering.

---
