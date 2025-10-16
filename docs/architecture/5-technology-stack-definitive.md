# 5. Technology Stack (Definitive)

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **PDF Extraction** | Docling | 2.55.1 | Extract text/tables from PDFs | 97.9% table accuracy, DocLayNet-based |
| **Excel Processing** | openpyxl | ≥3.1,<4.0 | Extract tabular data (spreadsheets) | Standard Python library for Excel |
| **Excel Processing** | pandas | ≥2.0,<3.0 | Extract tabular data (data manipulation) | Standard Python library for data analysis |
| **Embedding Model** | sentence-transformers (Fin-E5) | 5.1.1 | Generate semantic vectors | 71.05% financial domain accuracy |
| **Chunking** | Contextual Retrieval | N/A | LLM-generated context per chunk | 98.1% retrieval accuracy |
| **Vector Database** | Qdrant | ≥1.15.1 | Store/search embeddings | HNSW indexing, sub-5s retrieval |
| **Graph Database** | Neo4j | 5.x | Knowledge graph (Phase 2 conditional) | Cypher queries, managed cloud option |
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

## Phase 2: Advanced RAG Enhancements (Conditional)

**⚠️ ONLY REQUIRED IF STORY 1.15B DECISION GATE TRIGGERS (Baseline <90% retrieval or <95% attribution)**

| Component | Technology | Version | Purpose | Required/Optional | Story |
|-----------|------------|---------|---------|-------------------|-------|
| **Hybrid Search** | Qdrant SDK + custom logic | N/A | Combine semantic + keyword search | Required (if Phase 2) | Story 2.1 |
| **Cross-Encoder Re-ranking** | sentence-transformers | ≥2.2,<3.0 | Two-stage retrieval with re-ranking | Required (Story 2.4) | Story 2.4 |
| **Financial Embeddings (Option 1)** | OpenAI API (text-embedding-3-large) | N/A | SOTA embedding quality ($0.13/1M tokens) | Optional (Story 2.2) | Story 2.2 |
| **Financial Embeddings (Option 2)** | FinBERT (ProsusAI/finbert) | N/A | Finance-specific embeddings (free, local) | Optional (Story 2.2) | Story 2.2 |
| **Query Expansion** | Anthropic API (Claude) | ≥0.18.0,<1.0.0 | LLM-generated query variations | Optional (Story 2.5) | Story 2.5 |
| **Multi-Vector Collections** | Qdrant multi-collection | ≥1.15.1 | Multiple embeddings per chunk | Optional (Story 2.6) | Story 2.6 |

**Phase 2 Technology Notes:**

1. **Hybrid Search (Story 2.1):**
   - No new dependencies required
   - Uses existing Qdrant SDK for vector search
   - Custom Python logic for keyword extraction and score fusion
   - Minimal complexity, high impact (+5-10% accuracy)

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

**NOT Approved for Phase 2:**
- ❌ LangChain / LangGraph (use direct SDK calls instead)
- ❌ LlamaIndex (use Qdrant directly)
- ❌ Haystack (use Qdrant directly)
- ❌ Custom abstraction libraries (keep it simple)
- ❌ Redis/Memcached (not needed for Phase 2)

**Simplicity Principle:** Phase 2 uses **direct SDK calls** and **simple Python logic**. No frameworks, no abstraction layers, no over-engineering.

---
