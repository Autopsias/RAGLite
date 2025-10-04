# Epic 1: Foundation & Accurate Retrieval

**Epic Goal:** Deliver a working conversational financial Q&A system with 90%+ retrieval accuracy that enables users to ask natural language questions via MCP and receive accurate, source-attributed answers from company financial documents.

**⚠️ RISK MITIGATION: Epic 1 includes Week 0 Integration Spike (Story 0.1) to validate technology stack before committing to 5-week Phase 1 development. See Story 0.1 for mandatory go/no-go criteria.**

## Story 0.1: Week 0 Integration Spike (MANDATORY PRE-PHASE 1) ✅ DONE

**Status:** Done (QA approved with CONCERNS - conditional approval for Phase 1)
**QA Gate:** docs/qa/gates/0.1-week-0-integration-spike.yml

**As a** developer,
**I want** to validate end-to-end technology integration on real financial documents BEFORE starting Phase 1,
**so that** I can identify showstopper issues early and establish accuracy baseline.

**Duration:** 3-5 days
**Priority:** CRITICAL - Blocks all Phase 1 work

**Acceptance Criteria:**

1. Ingest 1 real company financial PDF (100+ pages) with Docling
2. Generate embeddings with Fin-E5 model
3. Store vectors in Qdrant via Docker Compose
4. Implement basic MCP server (FastMCP) exposing query tool
5. Create 15 ground truth Q&A pairs from test document
6. Measure baseline retrieval accuracy (vector search only, no LLM synthesis)
7. Document integration issues, API quirks, version conflicts discovered
8. Establish performance baseline (ingestion time, query latency)

**Success Criteria (GO/NO-GO for Phase 1):**

- ✅ **GO:** Baseline retrieval accuracy ≥70% (10+ out of 15 queries return relevant chunks)
- ✅ **GO:** End-to-end pipeline functional (PDF → Docling → Fin-E5 → Qdrant → FastMCP)
- ✅ **GO:** No major integration blockers requiring >2 days to resolve
- ⚠️ **REASSESS:** Accuracy 50-69% → Investigate root cause, may need chunking/embedding adjustments
- 🛑 **NO-GO:** Accuracy <50% → Technology stack unsuitable, consider alternatives (AWS Textract, different embeddings)

**Deliverables:**

- Working integration spike codebase (throwaway prototype, not production)
- Week 0 Spike Report documenting: accuracy baseline, integration issues, recommendations
- Updated Phase 1 plan based on learnings

**Rationale:** Risk assessment (RISK-001, RISK-002) identifies high probability of integration failures and accuracy shortfalls. Week 0 validation de-risks Phase 1 by surfacing issues early when pivoting is cheap.

## Story 0.0: Production Repository Setup (MANDATORY PRE-PHASE 1) ⭐ NEW

**Status:** In Progress (Pre-Phase 1 Requirement)
**Story File:** docs/stories/0.0.production-repository-setup.md

**As a** developer,
**I want** the production repository fully configured with UV, README, and CI/CD,
**so that** Phase 1 development can start immediately without tooling blockers.

**Duration:** 2-3 hours
**Priority:** BLOCKING - Must complete before Story 1.1
**Assignment:** Developer + AI Assistant

**Acceptance Criteria:**

1. Convert requirements.txt → pyproject.toml (UV migration)
2. Create README.md at project root with setup instructions
3. Update .gitignore for UV (.venv/, uv.lock)
4. Create .github/workflows/tests.yml (GitHub Actions CI/CD)
5. Create .pre-commit-config.yaml (code quality hooks)
6. Verify BMAD standard files exist (coding-standards.md, tech-stack.md, source-tree.md) ✅ DONE
7. Archive requirements.txt to spike/ directory
8. Test installation: uv sync --frozen completes without errors

**Deliverables:**

- ✅ README.md (project overview, quick start)
- ✅ pyproject.toml (UV dependencies - PEP 621)
- ✅ .github/workflows/tests.yml (CI/CD pipeline)
- ✅ .pre-commit-config.yaml (pre-commit hooks)
- ✅ scripts/setup-dev.sh (one-command setup)
- ✅ scripts/test_page_extraction.py (page number diagnostic)

**Rationale:** Week 0 spike used pip for quick validation. Production requires UV (per architecture), README for onboarding, and CI/CD for quality gates.

**Dependencies:**

- Blocks: Story 1.1 (Project Setup)
- Can run in parallel with: Story 0.2 (API Setup)

---

## 🗑️ Story 0.2: API Account & Cloud Infrastructure Setup (DEPRECATED)

**STATUS: REMOVED - NOT NEEDED FOR STANDARD MCP ARCHITECTURE**

**Why This Story Was Removed:**

This story originally required setting up:
- Anthropic Claude API account (for RAGLite to call Claude for answer synthesis)
- AWS account (conditional)
- Qdrant Cloud account (Phase 4 only)

**Architecture Change:**

RAGLite now follows the **standard MCP pattern** where:
- **RAGLite MCP tools return:** Raw chunks + metadata (no synthesis in RAGLite)
- **Claude Code (LLM client) synthesizes:** Coherent answers from chunks

**Result:** No Claude API account needed because the user already has Claude Code subscription. The LLM client (Claude Code) handles synthesis, not RAGLite.

**What's Still Needed (No Story Required):**

- ✅ Local Qdrant via Docker Compose (already configured in Story 0.0)
- ✅ `.env.example` for future Phase 4 cloud credentials (can be added in Story 1.1 if needed)
- ⏭️ AWS/Qdrant Cloud accounts deferred to Phase 4 (production deployment)

**See:** Story 1.11 (Enhanced Chunk Metadata & MCP Response Formatting) for the new approach

---

## Story 1.1: Project Setup & Development Environment ✅ DONE

**Status:** Done (QA approved with PASS - production ready)
**QA Gate:** docs/qa/gates/1.1-project-setup-development-environment.yml

**As a** developer,
**I want** a configured development environment with all necessary tools and dependencies,
**so that** I can begin implementation immediately without setup friction.

**Acceptance Criteria:**

1. Python virtual environment created with dependencies managed via UV (uv sync)
2. Git repository initialized with .gitignore configured for Python, secrets, and IDE files
3. Docker and Docker Compose installed and validated on macOS development machine
4. Project directory structure established per Architect's design
5. Environment variables template (.env.example) created for API keys and configuration
6. README.md includes setup instructions, architecture overview, and development workflow
7. Pre-commit hooks configured for formatting and linting (Ruff) and type checking (MyPy)

## Story 1.2: PDF Document Ingestion with Docling ⭐ ENHANCED

**As a** system,
**I want** to ingest financial PDF documents and extract text, tables, and structure accurately,
**so that** financial data is available for retrieval and analysis.

**⚠️ WEEK 0 BLOCKER FIX:** Page number extraction failed in Week 0 spike (docs/week-0-spike-report.md Section 2.2). MUST resolve to meet NFR7 (95%+ source attribution accuracy).

**Acceptance Criteria:**

1. Docling library integrated and configured per Architect's specifications
2. PDF ingestion pipeline accepts file path and extracts text content with 95%+ accuracy
3. Financial tables extracted with structure preserved (rows, columns, headers, merged cells)
4. Document metadata captured (filename, ingestion timestamp, document type if detectable)
5. Ingestion errors logged with clear error messages for malformed or corrupted PDFs
6. Successfully ingests sample company financial PDFs provided for testing
7. Ingestion performance meets <5 minutes for 100-page financial report (NFR2)
8. Unit tests cover ingestion pipeline with mocked Docling responses
9. Integration test validates end-to-end PDF ingestion with real sample document
10. **🚨 NEW - PAGE NUMBER EXTRACTION:** Page numbers extracted and validated (test with Week 0 PDF, ensure page_number != None)
11. **🚨 NEW - FALLBACK IF NEEDED:** IF Docling page extraction fails, implement PyMuPDF fallback for page detection (hybrid approach: Docling for tables, PyMuPDF for pages)
12. **🚨 NEW - DIAGNOSTIC SCRIPT:** Run scripts/test_page_extraction.py to diagnose root cause before implementation

**Recommended Approach:**

1. Run `uv run python scripts/test_page_extraction.py` (diagnostic)
2. IF Docling returns page numbers → Fix chunking logic to preserve metadata (Story 1.4)
3. IF Docling lacks pages → Implement hybrid: Docling (tables) + PyMuPDF (page detection)

## Story 1.3: Excel Document Ingestion

**As a** system,
**I want** to ingest Excel spreadsheets and extract tabular financial data,
**so that** financial data from Excel files is available alongside PDF content.

**Acceptance Criteria:**

1. Excel parsing library integrated (openpyxl, pandas, or Architect-specified tool)
2. Excel ingestion pipeline accepts file path and extracts sheet data preserving formulas and relationships
3. Multi-sheet workbooks handled with sheet names preserved as metadata
4. Numeric formatting preserved (currencies, percentages, dates)
5. Successfully ingests sample company Excel financial files
6. Errors handled gracefully for password-protected or corrupted files
7. Unit tests cover Excel parsing logic
8. Integration test validates end-to-end Excel ingestion

## Story 1.4: Document Chunking & Semantic Segmentation ⭐ ENHANCED

**As a** system,
**I want** to chunk ingested documents using semantic segmentation optimized for financial context,
**so that** retrieval returns relevant, complete information without context fragmentation.

**Acceptance Criteria:**

1. Chunking strategy implemented per Architect's specification (size, overlap, semantic boundaries)
2. Financial context preserved across chunks (tables not split mid-row, sections kept together)
3. Chunk metadata includes source document, page number, section heading where applicable
4. Chunking handles both narrative text and structured tables appropriately
5. Chunk quality validated manually on sample documents (no mid-sentence splits, logical boundaries)
6. Unit tests cover chunking logic with various document structures
7. Performance acceptable for 100-page documents (<30 seconds chunking time)
8. **🚨 NEW - PAGE NUMBER PRESERVATION:** Chunk metadata MUST include page_number (validate != None for all chunks)
9. **🚨 NEW - PAGE NUMBER VALIDATION:** Unit test verifies page numbers preserved across chunking pipeline (ingestion → chunking → Qdrant storage)

## Story 1.5: Embedding Model Integration & Vector Generation

**As a** system,
**I want** to generate vector embeddings for document chunks using the Architect-selected embedding model,
**so that** semantic similarity search is possible for retrieval.

**Acceptance Criteria:**

1. Embedding model integrated per Architect's selection from research spike
2. Vector embeddings generated for all document chunks
3. Embedding generation handles batch processing for efficiency
4. Embeddings cached to avoid redundant computation on re-ingestion
5. API rate limiting respected if using external embedding service
6. Unit tests cover embedding generation with mocked model responses
7. Integration test validates embeddings generated for sample document chunks

## Story 1.6: Qdrant Vector Database Setup & Storage

**As a** system,
**I want** to store document chunk embeddings in Qdrant vector database with efficient indexing,
**so that** sub-5 second semantic search retrieval is possible.

**Acceptance Criteria:**

1. Qdrant deployed via Docker Compose in local development environment
2. Collection created with appropriate vector dimensions and distance metric per Architect's specification
3. Document chunks and embeddings stored with metadata (document name, page, section)
4. Indexing configured for optimal retrieval performance (HNSW or IVF per Architect)
5. Storage handles 100+ documents without performance degradation (NFR3)
6. Connection management and error handling implemented (retries, connection pooling)
7. Unit tests cover Qdrant client operations with mocked database
8. Integration test validates storage and retrieval from actual Qdrant instance

## Story 1.7: Vector Similarity Search & Retrieval

**As a** system,
**I want** to perform vector similarity search and retrieve relevant document chunks for user queries,
**so that** accurate financial information can be surfaced conversationally.

**Acceptance Criteria:**

1. Query embedding generation using same model as document embeddings
2. Similarity search returns top-k relevant chunks (k configurable, default per Architect)
3. Retrieval performance <5 seconds (p50) for standard queries (NFR13)
4. Filtering by metadata supported (date range, document type) if specified in query
5. Relevance scoring included in results for downstream ranking
6. Unit tests cover retrieval logic with mocked vector search
7. Integration test validates end-to-end retrieval accuracy on ground truth query set
8. Retrieval accuracy measured and documented (target: 90%+ on test set per NFR6)

## Story 1.8: Source Attribution & Citation Generation

**As a** system,
**I want** to provide verifiable source citations for all retrieved information,
**so that** users can validate answers against original financial documents.

**Acceptance Criteria:**

1. Each retrieved chunk includes source metadata (document name, page number, section heading)
2. Citation format clearly identifies source: "(Source: Q3_Report.pdf, page 12, Revenue section)"
3. Source attribution accuracy 95%+ validated on test queries (NFR7)
4. Multiple sources cited when answer synthesizes information from multiple chunks
5. Citations included in final response format for MCP client display
6. Unit tests validate citation generation from metadata
7. Manual validation confirms citations point to correct document locations

## Story 1.9: MCP Server Foundation & Protocol Compliance

**As a** system,
**I want** to expose RAGLite capabilities via Model Context Protocol server,
**so that** Claude Desktop and other MCP clients can interact with the financial knowledge base.

**Acceptance Criteria:**

1. FastAPI-based MCP server implemented per Architect's design
2. MCP protocol compliance validated (server initialization, tool discovery, tool execution)
3. Health check endpoint responds with server status
4. Error handling returns proper MCP error responses
5. Server starts successfully via Docker Compose
6. Integration test validates MCP client can connect and discover tools
7. Server logs requests and responses for debugging

## Story 1.10: Natural Language Query Tool (MCP)

**As a** user,
**I want** to ask natural language financial questions via MCP client,
**so that** I can access financial knowledge conversationally without learning query syntax.

**Acceptance Criteria:**

1. MCP tool defined: `query_financial_documents` with natural language query parameter and `top_k` (default: 5)
2. Tool receives query, generates embedding, performs vector similarity search in Qdrant
3. Response includes retrieved chunks with metadata (score, text, source_document, page_number, chunk_index)
4. Query embedding handles financial terminology correctly (via Fin-E5 model)
5. Response format follows Week 0 spike pattern (QueryResponse with list of QueryResult objects)
6. Tool tested via Claude Desktop or MCP-compatible test client
7. End-to-end test: Ask question → Claude Code synthesizes answer from returned chunks
8. 10+ sample queries from ground truth test set validated for retrieval accuracy (chunks contain answer)

## Story 1.11: Enhanced Chunk Metadata & MCP Response Formatting

**As a** system,
**I want** to return well-structured chunk metadata via MCP tools,
**so that** Claude Code (the LLM client) can synthesize accurate, well-cited answers from the raw data.

**⚠️ ARCHITECTURE CHANGE:** This story was originally "Answer Synthesis & Response Generation" requiring Claude API integration. That approach has been **deprecated** in favor of the standard MCP pattern where:
- **RAGLite MCP tools return:** Raw chunks + metadata (scores, text, citations)
- **Claude Code (LLM client) synthesizes:** Coherent answers from chunks

**Rationale:** Standard MCP architecture, cost-effective (user already has Claude Code subscription), flexible (works with any MCP-compatible LLM client).

**Acceptance Criteria:**

1. MCP tool response includes comprehensive chunk metadata:
   - `score`: Similarity score (0-1, higher is better)
   - `text`: Full chunk content
   - `source_document`: Document filename
   - `page_number`: Page in source document (**MUST be populated**, not None)
   - `chunk_index`: Position in document
   - `word_count`: Chunk size
2. Response format follows Week 0 spike pattern (see `spike/mcp_server.py` QueryResult model)
3. Metadata validation: All required fields populated (no None values for critical fields like page_number)
4. Response JSON structure optimized for LLM synthesis (clear, consistent field names)
5. Integration with Story 1.8 (Source Attribution) - citations include all necessary data
6. Testing: Verify LLM client (Claude Code) can synthesize accurate answers from returned chunks
7. Performance: Response generated in <5 seconds for standard queries (NFR13)
8. Unit tests cover response formatting and metadata validation

## Story 1.12A: Ground Truth Test Set Creation ⭐ MOVED TO WEEK 1

**As a** developer,
**I want** to create a comprehensive ground truth test set early in Phase 1,
**so that** I can track accuracy daily throughout development and catch regressions immediately.

**Duration:** 4-6 hours
**Week:** Week 1 (after Story 1.1)
**Priority:** HIGH - Enables daily accuracy tracking

**Acceptance Criteria:**

1. Expand Week 0 ground truth (15 queries) to **50+ representative financial queries**
2. Cover all categories: cost_analysis, margins, financial_performance, safety_metrics, workforce, operating_expenses
3. Difficulty distribution: 40% easy, 40% medium, 20% hard
4. Store in `raglite/tests/ground_truth.py` as structured data (JSON or Python dict)
5. Each query includes:
   - Question text (natural language)
   - Expected answer (or answer criteria)
   - Source document reference
   - Expected page number (for attribution validation)
   - Expected chunk/section identifier
6. Manual validation: All answers verified against Week 0 test PDF
7. Documentation: README explains ground truth structure and maintenance

**Deliverables:**

- `raglite/tests/ground_truth.py` with 50+ Q&A pairs
- Documentation for adding new test queries
- Baseline for daily/weekly accuracy tracking

**Rationale:** Week 0 had only 15 queries (too small). Creating 50+ queries in Week 1 enables robust daily tracking throughout Phase 1 and prevents last-minute test creation rush in Week 5.

---

## Story 1.12B: Continuous Accuracy Tracking & Final Validation ⭐ WEEK 5

**As a** developer,
**I want** to run continuous accuracy validation throughout Phase 1 and perform final testing in Week 5,
**so that** I can make data-driven decisions about Phase 2/3 readiness.

**Duration:** 2-3 days
**Week:** Week 5 (after all Stories 1.1-1.11 complete)
**Priority:** CRITICAL - GO/NO-GO decision gate
**Dependencies:** Story 1.12A (test set must exist), All Stories 1.1-1.11

**Acceptance Criteria:**

1. Automated test suite runs all 50+ queries from Story 1.12A
2. Retrieval accuracy measured: % of queries returning correct information (target: 90%+ per NFR6)
3. Source attribution accuracy measured: % of citations pointing to correct documents (target: 95%+ per NFR7)
4. Performance metrics captured (p50, p95 response times)
5. Test results documented with failure analysis for inaccurate queries
6. Test suite executable via CLI command: `uv run python scripts/run-accuracy-tests.py`
7. **ENHANCED - DAILY TRACKING:** Daily accuracy tracking report generated (Week 1-5 trend line)
8. **ENHANCED - DECISION GATE:** GO/NO-GO report for Phase 2/3:
   - IF accuracy ≥90% → GO to Phase 3 (skip GraphRAG)
   - IF accuracy 80-89% → ACCEPTABLE, proceed to Phase 3 (defer improvements)
   - IF accuracy <80% → HALT, analyze failures, consider Phase 2 (GraphRAG)

**Daily Tracking (Weeks 1-5):**

- Run subset of 10-15 test queries daily against work-in-progress system
- Track accuracy trend line (should improve as components mature)
- **Early warning trigger:** If accuracy drops below 70% mid-phase, HALT feature work and debug root cause

**Weekly Accuracy Review:**

- Week 1 end: Ingestion quality validated (Docling extraction accurate? Page numbers working?)
- Week 2 end: Retrieval baseline ≥70% (chunking/embeddings working?)
- Week 3 end: Synthesis quality good (LLM prompts effective?)
- Week 4 end: Integration testing complete, trending toward 90%
- Week 5 end: Final validation ≥90% → Phase 1 SUCCESS

**Deliverables:**

- `scripts/run-accuracy-tests.py` (automated test runner)
- Week 5 validation report (accuracy, performance, decision gate)
- Daily tracking log (Week 1-5 trend data)

**Rationale:** Splitting into 1.12A (Week 1 test creation) and 1.12B (Week 5 validation) distributes workload, enables daily tracking, and provides early warning system for accuracy issues.

---

## Epic 1 Story Dependencies & Sequencing

**CRITICAL:** The following stories have dependencies that MUST be completed in order. Violating this sequence will cause blockers.

### Dependency Graph

```
Pre-Phase 1 (Parallel Execution Allowed):
├─ Story 0.1: Week 0 Integration Spike ✅ DONE
└─ Story 0.0: Production Repository Setup (2-3 hours) ✅ DONE

Week 1 (Sequential + Some Parallel):
├─ Story 1.1: Project Setup (REQUIRES Story 0.0 complete)
├─ Story 1.12A: Ground Truth Test Set Creation (4-6 hours, after 1.1)
├─ Story 1.2: PDF Ingestion (MUST FIX page numbers - Week 0 blocker)
├─ Story 1.3: Excel Ingestion (can run parallel with 1.2)
├─ Story 1.4: Chunking (REQUIRES 1.2 page numbers, MUST preserve metadata)
├─ Story 1.5: Embeddings (REQUIRES 1.4)
└─ Story 1.6: Qdrant Storage (REQUIRES 1.5)

Week 2 (Sequential):
├─ Story 1.7: Vector Search (REQUIRES 1.6)
├─ Story 1.8: Source Attribution (REQUIRES 1.2 page numbers, REQUIRES 1.7)
├─ Story 1.9: MCP Server Foundation
└─ Story 1.10: Query Tool (REQUIRES 1.9, REQUIRES 1.7)

Week 3:
└─ Story 1.11: Enhanced Chunk Metadata & Response Formatting (REQUIRES 1.10)

Week 4-5 (Integration & Validation):
├─ Integration Testing (continuous)
├─ Daily Accuracy Tracking (using Story 1.12A test set)
└─ Story 1.12B: Final Validation (REQUIRES ALL Stories 1.1-1.11)
```

### Critical Path Stories

| Story | Blocks | Rationale |
|-------|--------|-----------|
| **Story 0.0** | Story 1.1 | UV, README, BMAD files required |
| **Story 1.2** | Story 1.8 | Page numbers MUST extract for source attribution (NFR7) |
| **Story 1.4** | Story 1.5 | Chunks needed before embedding generation |
| **Story 1.6** | Story 1.7 | Vector DB needed before search |
| **Story 1.10** | Story 1.11 | Query tool needed before response formatting |
| **Story 1.12A** | Daily tracking | Test set enables Week 1-5 accuracy monitoring |
| **ALL 1.1-1.11** | Story 1.12B | Full pipeline needed for final validation |

### Parallel Execution Opportunities

**Pre-Phase 1:**

- Story 0.0 completed ✅ (no remaining pre-Phase 1 stories)

**Week 1:**

- Story 1.2 (PDF) + Story 1.3 (Excel) can run **in parallel** (independent ingestion paths)

**Week 2:**

- Story 1.9 (MCP Server) can start while finalizing Story 1.7/1.8 (independent of retrieval logic)

### Risk Mitigation Checkpoints

**Week 1 Gate:**

- ✅ Page numbers extracted (Story 1.2)? → IF NO, HALT and fix before Story 1.4
- ✅ Ground truth test set complete (Story 1.12A)? → IF NO, cannot track accuracy

**Week 2 Gate:**

- ✅ Retrieval baseline ≥70% (Story 1.7)? → IF NO, debug chunking/embeddings before proceeding

**Week 3 Gate:**

- ✅ MCP tool response format complete? → Chunks have all required metadata (page_number, source_document)
- ✅ Claude Code synthesis working? → Test with 5-10 queries from Story 1.12A (LLM client synthesizes answers from chunks)

**Week 5 Gate (Decision):**

- ✅ Accuracy ≥90%? → **GO to Phase 3** (Forecasting/Insights)
- ⚠️ Accuracy 80-89%? → **ACCEPTABLE**, proceed with notes
- 🛑 Accuracy <80%? → **REASSESS**, consider Phase 2 (GraphRAG)

---
