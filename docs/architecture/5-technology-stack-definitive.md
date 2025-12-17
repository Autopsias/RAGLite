# 5. Technology Stack (Definitive)

**Verification Date:** 2025-11-05 (All versions verified via WebSearch)

| Category | Technology | Version | Verified On | Purpose | Rationale |
|----------|------------|---------|-------------|---------|-----------|
| **PDF Extraction** | Docling | 2.0.0 | 2025-11-05 | Extract text/tables from PDFs | 97.9% table accuracy, DocLayNet-based, latest stable |
| **PDF Backend** | pypdfium | N/A | 2025-11-05 | Docling backend for faster, lower-memory PDF processing | ✅ APPROVED (Phase 1): 1.7-2.5x speedup, 50-60% memory reduction |
| **Excel Processing** | openpyxl | ≥3.1,<4.0 | 2025-11-05 | Extract tabular data (spreadsheets) | Standard Python library for Excel |
| **Excel Processing** | pandas | ≥2.0,<3.0 | 2025-11-05 | Extract tabular data (data manipulation) | Standard Python library for data analysis |
| **Embedding Model** | sentence-transformers | ≥5.1 | 2025-11-05 | Generate semantic vectors | 5.1+ released October 2025, supports Fin-E5 |
| **Finance Embedding** | FinanceMTEB/FinE5 | Latest (Feb 2025) | 2025-11-05 | Financial domain embeddings | 71.05% financial domain accuracy, e5-Mistral-7B fine-tuned |
| **Chunking** | Contextual Retrieval | N/A | 2025-11-05 | LLM-generated context per chunk | 98.1% retrieval accuracy |
| **Vector Database** | Qdrant | ≥1.15.5 | 2025-11-05 | Store/search embeddings | HNSW indexing, sub-5s retrieval, latest: 1.15.5 (Aug 2025) |
| **SQL Database** | PostgreSQL | 16.10 (LTS) | 2025-12-04 | Structured table storage + external data (Epic 6) | ✅ APPROVED (Epic 6): Financial tables (Phase 2B) + external data sources. PG 18 latest, 16.10 stable LTS |
| **Graph Database** | Neo4j | 5.26 LTS | 2025-11-05 | Knowledge graph for entity relationships | ⚠️ CONDITIONAL (Phase 2C): IF Phase 2B structured multi-index <75% accuracy. Latest: 2025.08 (calendar), 5.26 LTS recommended |
| **Agent Framework** | LangGraph + AWS Strands | Latest | 2025-11-05 | Multi-agent orchestration for query planning | ⚠️ CONDITIONAL (Phase 3): IF Phase 2 <85% accuracy |
| **MCP Server** | MCP Python SDK (mcp) | 1.20.0 | 2025-11-05 | Expose tools via MCP protocol | Official SDK by Anthropic, FastMCP 1.0 merged into official SDK |
| **MCP Framework** | FastMCP 2.0 | 2.0 | 2025-11-05 | Production MCP framework (optional) | Extends official SDK with advanced patterns, enterprise auth, testing |
| **LLM (Primary)** | Claude 3.7 Sonnet (Anthropic SDK) | 0.72.0 | 2025-11-05 | Reasoning, analysis, synthesis | Latest SDK (Oct 28, 2025), state-of-art reasoning, 200K context |
| **Forecasting** | Prophet | 1.2.1 | 2025-11-05 | Time-series baseline | Facebook library, seasonal handling, Apple M2 support |
| **Task Scheduler** | APScheduler | 3.10+ | 2025-12-04 | Periodic external data refresh | Lightweight Python scheduler, persistent jobs in PostgreSQL, no external deps |
| **ML Framework** | scikit-learn | 1.5+ | 2025-12-04 | Model ensemble (Linear Regression) | Industry standard ML library, numpy/scipy compatible |
| **Gradient Boosting** | XGBoost | 2.1+ | 2025-12-04 | Advanced forecasting ensemble | State-of-art boosting for time-series, production-proven |
| **Backend Language** | Python | ≥3.11,≤3.13 | 2025-11-05 | All application code | 3.13.5 latest (Oct 2025), 3.11+ for production stability, async support |
| **Data Validation** | Pydantic | 2.12.4 | 2025-11-05 | Data models and validation | Latest (Nov 5, 2025), type-safe, runtime validation, Python 3.14 support |
| **Configuration** | Pydantic Settings | ≥2.0 | 2025-11-05 | Settings management | Environment variable loading |
| **Environment Variables** | python-dotenv | ≥1.0 | 2025-11-05 | Load .env files | Development environment configuration |
| **HTTP Client** | httpx | ≥0.28.1,<1.0.0 | 2025-11-05 | Async HTTP requests | Modern async HTTP client |
| **API Framework** | FastAPI | 0.115+ (optional) | 2025-11-05 | REST endpoints if needed | High performance, async native |
| **Document Storage** | S3 (cloud) / Local FS (dev) | N/A | 2025-11-05 | Store ingested documents | Scalable, versioning, encryption |
| **Secrets** | AWS Secrets Manager / .env | N/A | 2025-11-05 | API keys, credentials | Secure, rotatable |
| **Containerization** | Docker + Docker Compose | Latest | 2025-11-05 | Local development | Service isolation, reproducible |
| **Cloud Platform** | AWS | N/A | 2025-11-05 | Production deployment (Phase 4) | ECS/Fargate, managed services |
| **IaC** | Terraform | Latest | 2025-11-05 | Infrastructure as Code (Phase 4) | Version-controlled infrastructure |
| **CI/CD** | GitHub Actions | N/A | 2025-11-05 | Testing and deployment | Git-integrated |
| **Monitoring** | CloudWatch + Prometheus | N/A | 2025-11-05 | Performance tracking (Phase 4) | AWS native + open-source |
| **Logging** | Structured JSON | N/A | 2025-11-05 | Application logs, audit trail | CloudWatch-compatible |
| **Testing** | pytest | 8.4.2 | 2025-11-05 | Python unit/integration tests | Latest (Sep 4, 2025), standard testing framework |
| **Async Testing** | pytest-asyncio | ≥1.2.0 | 2025-11-05 | Async test support | Test async functions |
| **Test Coverage** | pytest-cov | ≥4.1,<5.0 | 2025-11-05 | Code coverage reporting | Track test coverage |
| **Test Mocking** | pytest-mock | ≥3.12,<4.0 | 2025-11-05 | Mock external dependencies | Isolated unit testing |
| **Parallel Testing** | pytest-xdist | ≥3.5,<4.0 | 2025-11-05 | Parallel test execution | Faster test runs |
| **Test Timeouts** | pytest-timeout | ≥2.0,<3.0 | 2025-11-05 | Test timeout enforcement | Prevent hanging tests |
| **Code Formatting** | Ruff | 0.14.3 | 2025-11-05 | Python formatter + linter | Latest (Oct 30, 2025), 10-100x faster than Black, replaces Black+isort+Flake8 |
| **Type Checking** | mypy | ≥1.4,<2.0 | 2025-11-05 | Static type checking | Type safety (Phase 4) |
| **Pre-commit Hooks** | pre-commit | ≥3.0,<4.0 | 2025-11-05 | Git pre-commit automation | Enforce quality gates |
| **PDF Testing** | pypdf | ≥4.0,<5.0 | 2025-11-05 | PDF file manipulation for tests | Test PDF generation |

---

## Technology Stack Approval Status

**Phase 1 (APPROVED - Immediate)**:
- ✅ **pypdfium**: Docling backend for PDF optimization (1.7-2.5x speedup, 97.9% accuracy maintained)
  - **Rationale**: Empirically validated by Docling official benchmarks
  - **Risk**: LOW (production-proven, minimal integration required)
  - **Timeline**: 1-2 days implementation + validation

**Epic 6 (COMPLETE - 2025-12-17)**:
- ✅ **PostgreSQL 16.10 LTS**: APPROVED for Epic 6 external data storage
  - **Rationale**: Store Tier 1/2 time-series data (INE, BPstat, OMIE, IPMA, etc.)
  - **Schema**: `external_data_sources` + `external_data_points` tables
  - **Decision Authority**: Ricardo (Product Owner) - SCP-2025-12-04-001

- ✅ **APScheduler 3.10+**: APPROVED for periodic data refresh
  - **Rationale**: Lightweight Python scheduler, persistent jobs in PostgreSQL
  - **Alternative Considered**: AWS EventBridge (cloud-only, rejected for local dev)
  - **Decision Authority**: Ricardo (Product Owner) - SCP-2025-12-04-001

- ✅ **scikit-learn 1.5+**: APPROVED for ML ensemble framework
  - **Rationale**: Industry standard, integrates with Prophet for multi-model forecasting
  - **Models**: Linear Regression with external regressors
  - **Decision Authority**: Ricardo (Product Owner) - SCP-2025-12-04-001

- ✅ **XGBoost 2.1+**: APPROVED for gradient boosting ensemble
  - **Rationale**: State-of-art forecasting accuracy, production-proven
  - **Alternative Considered**: LightGBM (XGBoost chosen for better documentation)
  - **Decision Authority**: Ricardo (Product Owner) - SCP-2025-12-04-001

**Epic 7 (APPROVED - 2025-12-17)**:
- ✅ **pmdarima 2.0+**: APPROVED for Auto-ARIMA model selection
  - **Rationale**: Automatic (p,d,q) selection for ARIMA models, statsmodels wrapper
  - **Purpose**: Per-variable model selection framework (ARIMA/SARIMA)
  - **Alternative Considered**: Manual ARIMA fitting (rejected for complexity)
  - **Decision Authority**: Ricardo (Product Owner) - Correct-Course workflow

- ✅ **statsmodels (already in stack via Prophet)**: Used for ETS, ADF/KPSS tests
  - **Rationale**: Exponential Smoothing (ETS), stationarity tests for data analysis
  - **No new dependency**: Already transitive via Prophet

**Phase 2B-C (CONDITIONAL - Decision Gate Approval)**:
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

## Epic 6: Advanced Forecasting with External Data

**Timeline:** 3-4 weeks (14-20 days)
**Status:** Backlog (waiting for PM to create stories)
**Dependencies:** Epic 4 complete (DONE)

### New Dependencies

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **PostgreSQL** | 16.10 LTS | External data storage | Structured time-series data for 11 Tier 1 sources, 5-year retention |
| **APScheduler** | 3.10+ | Data refresh scheduler | Daily/weekly/monthly refresh for external sources, persistent jobs |
| **scikit-learn** | 1.5+ | ML ensemble | Linear Regression for multi-variate forecasting |
| **XGBoost** | 2.1+ | Gradient boosting | Advanced ensemble for 20-30% accuracy improvement |
| **httpx** | 0.28.1+ | HTTP client | Async API calls to INE, BPstat, OMIE, IPMA (already approved) |
| **pandas** | 2.0+ | Data manipulation | Time-series processing (already approved) |

### External Data Sources (Tier 1)

**11 datasets integrated via API/CSV:**
1. **INE (Portugal Statistics):** Building Permits, Construction Output Index, Construction Cost Index
2. **ATIC:** Cement Consumption (CSV if no API)
3. **Banco de Portugal BPstat:** Mortgage Loans
4. **OMIE:** Electricity Prices (Iberian market)
5. **EU Oil Bulletin:** Diesel Prices
6. **IPMA (Portugal Weather):** Temperature, Rainfall
7. **Base.gov.pt:** Public Works Contracts
8. **Manual/Scraping:** Coal/Petcoke Prices, CO₂ EUA Prices

**Tier 2 Sources (Conditional):** 9 additional datasets IF Story 6.7 accuracy <±12%

### Architecture Impact

**New Modules:**
- `raglite/external_data/` - API clients, data validation, scheduler
- `raglite/forecasting/ensemble.py` - Multi-model framework (Prophet + scikit-learn + XGBoost)

**Enhanced Modules:**
- `raglite/forecasting/hybrid.py` - Add multi-variate Prophet with external regressors
- `raglite/shared/clients.py` - Add PostgreSQL external data client

**Database Schema:**
- PostgreSQL tables: `external_data_sources`, `external_data_points`
- Indexes: (source_id, date), (metric_name)

**MCP Tools:**
- `query_external_data(source, date_range, metric)` - Query external sources
- `refresh_external_data(source_name)` - Manual data refresh trigger
- Enhanced `get_financial_forecast()` - Multi-model support

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
