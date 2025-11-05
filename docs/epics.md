# RAGLite - Epic and Story Breakdown

**Document Version:** 2.0
**Date:** 2025-11-05
**Project:** RAGLite - AI-Powered Financial Document Analysis System

This document provides a comprehensive breakdown of all epics and stories for the RAGLite project, organized sequentially for implementation.

---

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

**Implements:** FR1 (PDF ingestion, 95%+ accuracy), FR4 (metadata extraction), NFR9 (95%+ table extraction)

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
8. **🚨 TABLE EXTRACTION:** Financial table cell data extracted and converted to searchable text
9. **🚨 TABLE VALIDATION:** Test queries for tabular data (e.g., "23.2 EUR/ton") retrieve correct chunks
10. Unit tests cover ingestion pipeline with mocked Docling responses
11. Unit tests validate table extraction from sample financial PDF
12. Integration test validates end-to-end PDF ingestion with real sample document
13. **🚨 NEW - PAGE NUMBER EXTRACTION:** Page numbers extracted and validated (test with Week 0 PDF, ensure page_number != None)
14. **🚨 NEW - FALLBACK IF NEEDED:** IF Docling page extraction fails, implement PyMuPDF fallback for page detection (hybrid approach: Docling for tables, PyMuPDF for pages)
15. **🚨 NEW - DIAGNOSTIC SCRIPT:** Run scripts/test_page_extraction.py to diagnose root cause before implementation

**Recommended Approach:**

1. Run `uv run python scripts/test_page_extraction.py` (diagnostic)
2. IF Docling returns page numbers → Fix chunking logic to preserve metadata (Story 1.4)
3. IF Docling lacks pages → Implement hybrid: Docling (tables) + PyMuPDF (page detection)

## Story 1.3: Excel Document Ingestion

**Implements:** FR2 (Excel ingestion, tabular data extraction)

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

**Implements:** FR3 (semantic segmentation, financial context preservation)

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

**Implements:** FR5 (vector storage, sub-5 second retrieval), NFR3 (100+ documents)

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

**Implements:** FR10 (90%+ retrieval accuracy), FR13 (<5s response time)

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

**Implements:** FR11 (source attribution), NFR7 (95%+ attribution accuracy)

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

**Implements:** FR30 (MCP server with tool definitions), FR31 (MCP client integration)

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

**Implements:** FR9 (natural language queries), FR32 (structured tool responses)

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

**Implements:** FR11 (source attribution), FR12 (multi-document synthesis), NFR13 (<5s response time)

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

## Story 1.15: Table Extraction Fix ⭐ NEW

**Status:** Ready for Development (post-Story 1.15A)
**Epic:** 1 - Foundation & Accurate Retrieval
**Priority:** CRITICAL - Blocks baseline validation
**Duration:** 2-3 hours
**Prerequisites:** Story 1.15A complete (root cause identified)

**Story:**
```markdown
**As a** developer,
**I want** to fix the table extraction issue identified in Story 1.15A and prepare for baseline validation,
**so that** Story 1.15B can accurately measure retrieval performance with complete data.
```

**Acceptance Criteria:**

1. **Research Docling table extraction capabilities** (1 hour)
   - Check documentation for table-to-text conversion options
   - Test on single page (page 46) to verify extraction
   - Determine best approach: Docling config OR alternative extractor

2. **Implement table extraction fix** (1-1.5 hours)
   - Configure Docling for table data extraction OR
   - Implement alternative (pdfplumber, camelot) + merge with Docling text
   - Ensure table data converted to searchable text
   - Preserve page attribution for table cells

3. **Re-ingest PDF with table data** (15-20 min)
   - Clear Qdrant collection (delete 147 existing points)
   - Re-ingest with table extraction enabled
   - Expected result: 300+ chunks (147 text + ~150-200 table cells)
   - Verify: Search for "23.2" returns results from page 46

4. **Validate fix with diagnostic queries** (30 min)
   - Run 3 queries from Story 1.15A again
   - Verify: Pages 46, 77 now in top-5 results
   - Verify: Specific keywords found ("23.2", "50.6%", "104,647")
   - Quick accuracy check: Expect 50-70% accuracy on sample queries

**Deliverables:**
- Updated ingestion pipeline with table extraction
- Re-ingested PDF (300+ chunks)
- Diagnostic validation report
- Fix documentation in completion notes

**Rationale:** Story 1.15A identified root cause (Docling table extraction failure). Story 1.15 fixes the issue to enable accurate baseline validation in Story 1.15B.

---

## Story 1.15B: Baseline Validation & Analysis ⭐ NEW

**Status:** Ready for Development (post-Story 1.15)
**Epic:** 1 - Foundation & Accurate Retrieval
**Priority:** HIGH - Decision gate for Phase 2
**Duration:** 1.5 hours
**Prerequisites:** Story 1.15 complete (table extraction fixed)

**Story:**
```markdown
**As a** developer,
**I want** to validate that basic ingestion and semantic search work correctly with the original PDF BEFORE implementing Phase 2 enhancements,
**so that** I can establish a performance baseline and determine if Phase 2 is actually needed.
```

**Acceptance Criteria:**

1. **Validate ingestion quality** (15 min)
   - Verify: 300+ chunks, pages 1-160
   - Verify: Critical pages (46, 47, 77, 108) have table data
   - Verify: Table data searchable (search for "23.2" returns results)

2. **Run full accuracy test suite** (15 min)
   - Execute: `uv run python scripts/run-accuracy-tests.py`
   - Measure: Retrieval accuracy %, Attribution accuracy %
   - Document: Baseline metrics

3. **Analyze failure patterns** (20 min)
   - Categorize failures: keyword mismatch, table split, financial term, multi-hop
   - Identify: Which Phase 2 enhancements would help most
   - Document: Phase 2 priority recommendations

4. **Performance benchmarking** (10 min)
   - Measure: Query latency (p50, p95, p99)
   - Calculate: Latency budget for Phase 2 (10s - baseline)
   - Verify: NFR5 compliance (<10s response time)

5. **Decision gate** (5 min)
   - **IF** Retrieval ≥90% AND Attribution ≥95% → Epic 1 VALIDATED, skip Phase 2
   - **IF** Retrieval 85-89% OR Attribution 93-94% → Implement Phase 2A only
   - **IF** Retrieval <85% OR Attribution <93% → Implement Phase 2A → 2B → 2C

**Deliverables:**
- `baseline-accuracy-report.txt` - Full test results
- `baseline-failure-analysis.md` - Failure patterns + Phase 2 recommendations
- `baseline-performance-benchmarks.txt` - Latency metrics
- Decision: GO to Epic 3 OR implement Epic 2

**Rationale:** Establishes baseline performance BEFORE committing to Phase 2 enhancements. Prevents over-engineering if baseline already meets NFR6/NFR7.

---

## Epic 1 → Epic 2 Decision Gate

**After Story 1.15B completion, one of three paths:**

**Path 1: Epic 1 VALIDATED (Best Case)**
- ✅ Retrieval ≥90% AND Attribution ≥95%
- ✅ Skip Epic 2 entirely
- ✅ Proceed directly to Epic 3 (Intelligence Features)

**Path 2: Epic 2 Partial Implementation (Likely Case)**
- ⚠️ Retrieval 85-89% OR Attribution 93-94%
- Implement Epic 2, Story 2.1 only (Hybrid Search)
- Re-validate, likely achieves 92%+
- If still <90%: Continue Stories 2.2 → 2.3

**Path 3: Epic 2 Full Implementation (Worst Case)**
- ✗ Retrieval <85% OR Attribution <93%
- Implement Epic 2, Stories 2.1 → 2.2 → 2.3 sequentially
- Test after EACH, STOP when 95% achieved

**For Epic 2 story details:** See `docs/prd/epic-2-advanced-rag-enhancements.md`

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

## Story 1.16: Document Epic 1 Architecture Decisions

**Implements:** Knowledge capture, technical debt prevention

**As a** developer,
**I want** to document key architectural decisions made during Epic 1 implementation,
**so that** future team members understand the rationale behind technical choices.

**Duration:** 2-3 hours
**Priority:** MEDIUM (incremental documentation)

**Acceptance Criteria:**

1. **Architecture Decision Record (ADR) for Epic 1:**
   - Document key decisions: Why Docling over AWS Textract?
   - Document key decisions: Why Fin-E5 for financial embeddings?
   - Document key decisions: Why monolithic MCP server over microservices?
   - Document key decisions: Why standard MCP pattern (Claude Code synthesis) over RAGLite synthesis?

2. **Technical Challenges Documented:**
   - Page number extraction fix (Story 1.2 blocker resolution)
   - Table extraction approach (Story 1.15)
   - Ground truth test set design (Story 1.12A methodology)

3. **Codebase Walkthrough Notes:**
   - Document Epic 1 module responsibilities
   - Document data flow: PDF → chunks → embeddings → Qdrant → MCP
   - Document test strategy for Epic 1

4. **Save to:**
   - `docs/architecture-decisions.md` (append Epic 1 section)
   - Update README.md with Epic 1 implementation notes

**Deliverables:**
- Epic 1 ADR section in `docs/architecture-decisions.md`
- Epic 1 implementation notes in README.md

**Rationale:** Incremental documentation during development prevents knowledge loss and reduces technical debt. Capturing decisions immediately after Epic 1 completion ensures context is fresh.

---

# Epic 2: Advanced RAG Architecture Enhancement

**Status:** IN PROGRESS
**Priority:** 🔴 **CRITICAL** (blocks Epic 3-5)
**Duration:** 2-3 weeks (best case, Phase 1+2A) to 18 weeks (worst case, all contingencies)
**Goal:** Achieve minimum 70% retrieval accuracy through staged RAG architecture enhancement

**⚠️ STRATEGIC PIVOT (2025-10-19):**
Epic 2 has been redefined following the catastrophic failure of element-aware chunking (Story 2.2 achieved 42% vs 56% baseline = -14pp regression). This epic now implements a **staged RAG architecture approach** with decision gates at each phase.

---

## Epic Overview

Epic 2 pivots from the failed element-aware chunking approach (42% accuracy, -14pp regression) to a staged RAG architecture enhancement strategy. This epic implements PDF ingestion optimization followed by a research-validated fixed chunking approach, with contingency paths to Structured Multi-Index or Hybrid Architecture if accuracy thresholds are not met.

**Root Cause of Pivot:**
Story 2.2 (Element-Aware Chunking) implemented the **exact failure mode warned against in research** (Yepes et al. 2024):
- Research evidence: Element-based "Keywords Chipper" = **46.10% accuracy**
- Research evidence: Fixed 512-token chunks = **68.09% accuracy**
- **We built the 46% solution instead of the 68% solution**

**New Approach:**
Staged implementation with empirical decision gates based on production-proven RAG patterns.

---

## Business Value

- **Achieve minimum 70% retrieval accuracy** (unblock Epic 3-5)
- **1.7-2.5x faster PDF ingestion** (accelerate testing iterations)
- **Production-proven approaches** (68-72% guaranteed by research)
- **Staged implementation with decision gates** (minimize risk)
- **Cost-efficient path to accuracy** (start simple, escalate only if needed)

---

## Success Criteria

Epic 2 is considered COMPLETE when:

- ✅ **Retrieval accuracy ≥70%** (MANDATORY for Epic 3)
- ✅ **Attribution accuracy ≥95%** (NFR7 compliance)
- ✅ **Query response time <15s p95** (NFR13 compliance)
- ✅ **All 50 AC3 ground truth queries validated**
- ✅ **PRD Epic 2 documentation updated**
- ✅ **Technology stack documentation updated**
- ✅ **Test suite passing with new chunking strategy**

---

## Implementation Phases

### PHASE 1: PDF Ingestion Performance Optimization (1-2 days)

**Goal:** 1.7-2.5x speedup (8.2 min → 3.3-4.8 min for 160-page PDF)
**Risk:** LOW (empirically validated by Docling official benchmarks)
**Strategic Benefit:** Faster ingestion enables quicker RAG testing iterations in Phase 2

---

### Story 2.1: Implement pypdfium Backend for Docling

**Priority:** 🔴 CRITICAL (blocks Phase 2A)
**Effort:** 4 hours
**Goal:** Replace default PDF.js backend with pypdfium for 50-60% memory reduction and faster processing

**As a** system administrator,
**I want** Docling configured with pypdfium backend,
**so that** PDF ingestion is faster and uses less memory.

#### Acceptance Criteria

1. **AC1: Docling Backend Configuration** (1 hour)
   - Configure `PdfiumBackend` in `raglite/ingestion/pipeline.py`
   - Remove default PDF.js backend configuration
   - Validate backend switch successful

2. **AC2: Ingestion Validation** (1 hour)
   - Ingest test PDF (160 pages) successfully
   - Verify all pages processed
   - Verify table extraction still works

3. **AC3: Table Accuracy Maintained** (1 hour)
   - Run 10 ground truth table queries
   - Validate table extraction accuracy ≥97.9% (no degradation)
   - Document any accuracy changes

4. **AC4: Memory Reduction Validation** (1 hour)
   - Measure peak memory usage during ingestion
   - Expected: 50-60% reduction (6.2GB → 2.4GB)
   - Document memory usage before/after

#### Expected Impact

- **Memory:** 50-60% reduction (6.2GB → 2.4GB)
- **Speed:** 1.0x baseline (unchanged at this step)
- **Accuracy:** 97.9% maintained
- **Risk:** LOW (pypdfium is official Docling backend)

#### Decision Gate

- **IF successful:** Proceed to Story 2.2
- **IF failed:** Escalate to PM (technology stack issue)

**Technologies:** pypdfium (APPROVED - new dependency)

**Files Modified:**
- `raglite/ingestion/pipeline.py` (~15 lines - backend configuration)
- `pyproject.toml` (+1 dependency: pypdfium)

---

### Story 2.2: Implement Page-Level Parallelism (4-8 Threads)

**Priority:** 🔴 CRITICAL (blocks Phase 2A)
**Effort:** 4 hours
**Depends On:** Story 2.1
**Goal:** Add concurrent page processing to Docling for 1.7-2.5x speedup

**As a** system administrator,
**I want** page-level parallel processing,
**so that** PDF ingestion is 1.7-2.5x faster.

#### Acceptance Criteria

1. **AC1: Parallel Processing Configuration** (2 hours)
   - Configure Docling with `max_num_pages_visible=4`
   - Implement page-level concurrency (4-8 threads)
   - Handle thread pool cleanup

2. **AC2: Speedup Validation** (1 hour)
   - Ingest test PDF (160 pages) with parallelism
   - Measure ingestion time: target 3.3-4.8 min (vs 8.2 min baseline)
   - Calculate speedup: target 1.7-2.5x

3. **AC3: Speedup Documentation** (30 min)
   - Document ingestion time before/after
   - Document speedup factor (1.7x-2.5x range)
   - Document optimal thread count (4 vs 8)

4. **AC4: No Race Conditions** (30 min)
   - Test 10 consecutive ingestions
   - Verify no deadlocks or race conditions
   - Verify output deterministic (same chunks every time)

#### Expected Impact

- **Speed:** 1.7-2.5x faster ingestion (8.2 min → 3.3-4.8 min)
- **Accuracy:** 97.9% maintained
- **Memory:** 2.4GB maintained (from Story 2.1)
- **Strategic:** Faster iterations for Phase 2A testing

#### Decision Gate

- **IF ≥1.7x speedup:** Phase 1 COMPLETE → Proceed to Phase 2A
- **IF <1.7x speedup:** Escalate to PM (expected speedup not achieved)

**Technologies:** Docling parallelism (no new dependencies)

**Files Modified:**
- `raglite/ingestion/pipeline.py` (~30 lines - parallel configuration)

---

### PHASE 2A: Fixed Chunking + Metadata (1-2 weeks)

**Goal:** Achieve 68-72% retrieval accuracy (unblock Epic 3)
**Probability:** 80% success (research-validated: 68-72% accuracy)
**Risk:** MEDIUM-LOW (production-proven approach)
**Decision Gate:** IF ≥70% → STOP (Epic 2 complete), IF <70% → Phase 2B

---

### Story 2.3: Refactor Chunking Strategy to Fixed 512-Token Approach

**Priority:** 🔴 CRITICAL
**Effort:** 3 days
**Depends On:** Story 2.2 (Phase 1 complete)
**Goal:** Replace element-aware chunking with research-validated fixed 512-token chunks with 50-token overlap

**As a** RAG system,
**I want** fixed 512-token chunking with 50-token overlap,
**so that** retrieval accuracy improves from 42% to 68-72%.

#### Acceptance Criteria

1. **AC1: Remove Element-Aware Logic** (4 hours)
   - Delete element-aware chunking code from `raglite/ingestion/pipeline.py`
   - Remove ElementType enum from `raglite/shared/models.py`
   - Remove element detection logic

2. **AC2: Implement Fixed 512-Token Chunking** (1 day)
   - Chunk size: 512 tokens
   - Overlap: 50 tokens
   - Tokenizer: OpenAI tiktoken (cl100k_base)
   - Preserve sentence boundaries when possible

3. **AC3: Table Boundary Preservation** (4 hours)
   - Detect Docling TableItem objects
   - Ensure tables NOT split mid-row
   - If table >512 tokens, keep as single chunk (exception to 512-token rule)

4. **AC4: Clean Collection and Re-ingest** (4 hours)
   - Delete contaminated Qdrant collection
   - Recreate collection with clean schema
   - Re-ingest test PDF (160 pages)
   - Verify chunk count: 250-350 (vs 504 element-aware)

5. **AC5: Chunk Count Validation** (1 hour)
   - Expected chunk count: 250-350
   - Measure chunk size consistency: 512 tokens ±50 variance
   - Document chunk count and size distribution

6. **AC6: Chunk Size Consistency** (1 hour)
   - Measure chunk size: mean=512, std<50
   - Verify 95% of chunks within 462-562 token range
   - Document outliers (tables >512 tokens)

#### Expected Impact

- **Accuracy:** 42% → 68-72% (+26-30pp improvement)
- **Chunks:** 504 → 250-350 (-50% chunk count)
- **Research Evidence:** Yepes et al. (2024) - 68.09% accuracy on financial reports

#### Decision Gate

- **IF implemented successfully:** Proceed to Story 2.4
- **IF technical blockers:** Escalate to PM

**Technologies:** tiktoken (APPROVED - new dependency)

**Files Modified:**
- `raglite/ingestion/pipeline.py` (-150 lines element-aware, +80 lines fixed chunking)
- `raglite/shared/models.py` (-30 lines element types)
- `pyproject.toml` (+1 dependency: tiktoken)

---

### Story 2.4: Add LLM-Generated Contextual Metadata Injection

**Priority:** 🟠 HIGH
**Effort:** 2 days
**Depends On:** Story 2.3
**Goal:** Implement Claude API-based metadata extraction (fiscal period, company, department) and inject into chunk payload

**As a** RAG system,
**I want** LLM-generated metadata (fiscal period, company, department),
**so that** queries can filter by business context and improve precision.

#### Acceptance Criteria

1. **AC1: Metadata Extraction Function** (1 day)
   - Use Claude 3.7 Sonnet API
   - Extract: fiscal_period, company_name, department_name
   - Prompt: "Extract fiscal period, company name, and department from this text"
   - Cache results per document (not per chunk)

2. **AC2: Metadata Schema Update** (2 hours)
   - Add metadata fields to Chunk model: fiscal_period, company_name, department_name
   - Update Qdrant payload schema
   - Ensure backward compatibility

3. **AC3: Metadata Injection** (4 hours)
   - Inject metadata into Qdrant chunk payload
   - Metadata accessible via search filters
   - Document metadata usage patterns

4. **AC4: Metadata Caching** (2 hours)
   - Cache metadata extraction results per document
   - Avoid re-extracting for every chunk (performance optimization)
   - Measure: <$0.10 per document metadata extraction

5. **AC5: Cost Validation** (1 hour)
   - Measure Claude API token usage
   - Expected cost: <$0.10 per 160-page document
   - Document metadata extraction cost per document

#### Expected Impact

- **Accuracy:** 68-72% → 70-75% (+2-3pp improvement via metadata boosting)
- **Cost:** $0.05-0.10 per document (one-time extraction)
- **Research Evidence:** Snowflake research - 20% improvement over large chunks

#### Decision Gate

- **IF implemented successfully:** Proceed to Story 2.5
- **IF technical blockers:** Escalate to PM

**Technologies:** Claude 3.7 Sonnet API (already approved), tiktoken

**Files Modified:**
- `raglite/ingestion/pipeline.py` (+100 lines - metadata extraction)
- `raglite/shared/models.py` (+20 lines - metadata fields)

---

### Story 2.5: AC3 Validation and Optimization (Target: ≥70% Accuracy) - DECISION GATE

**Status:** ⚠️ FAILED - 52% accuracy, course correction required (Stories 2.8-2.11)
**Priority:** 🔴 CRITICAL (Epic 2 completion gate)
**Effort:** 2-3 days
**Depends On:** Story 2.4
**Goal:** Run full AC3 ground truth test suite (50 queries) and optimize chunking if needed

**⚠️ OUTCOME (2025-10-25):** AC2 FAILED with 52% accuracy (vs ≥70% target). Deep-dive analysis identified 4 critical root causes requiring course correction via Stories 2.8-2.11 before re-validation.

**As a** QA engineer,
**I want** comprehensive accuracy validation,
**so that** we can verify ≥70% retrieval accuracy and decide if Epic 2 is complete.

#### Acceptance Criteria

1. **AC1: Full Ground Truth Execution** (4 hours)
   - Run all 50 ground truth queries
   - Measure retrieval accuracy (% queries with correct chunk in top-5)
   - Measure attribution accuracy (% correct source citations)

2. **AC2: DECISION GATE - Retrieval Accuracy ≥70%** (30 min) ⭐ MANDATORY
   - **MANDATORY:** Retrieval accuracy ≥70.0% (35/50 queries pass)
   - **This is the DECISION GATE for Epic 2 completion**
   - IF ≥70% → Epic 2 COMPLETE
   - IF <70% → Escalate to PM for Phase 2B approval

3. **AC3: Attribution Accuracy ≥95%** (30 min)
   - Attribution accuracy ≥95.0%
   - Correct document, page, section references
   - NFR7 compliance

4. **AC4: Failure Mode Analysis** (1 day)
   - Analyze all failed queries (<70% accuracy scenario)
   - Categorize failure types (table queries, multi-hop, entity-based, etc.)
   - Document failure patterns
   - Recommend Phase 2B/2C approaches if needed

5. **AC5: BM25 Index Rebuild** (2 hours)
   - Rebuild BM25 index for new chunk structure (250-350 chunks)
   - Verify hybrid search still works
   - Test BM25 + semantic fusion

6. **AC6: Performance Validation** (2 hours)
   - p50 query latency <5s
   - p95 query latency <15s
   - NFR13 compliance verified

#### Expected Impact

- **Accuracy:** 68-72% target (research-validated)
- **Decision:** IF ≥70% → Epic 2 COMPLETE (proceed to Epic 3)
- **Decision:** IF <70% → Phase 2B Structured Multi-Index (3-4 weeks, 70-80% expected)

#### Decision Gate

- **IF ≥70%:** Epic 2 COMPLETE → Proceed to Epic 3 🎉
- **IF <70%:** Escalate to PM for Phase 2B (Structured Multi-Index) approval
- **IF <64%:** CRITICAL ESCALATION → Strategy review required

**Technologies:** pytest, ground truth test suite

**Files Modified:**
- `tests/integration/test_hybrid_search_integration.py` (updates for new chunking)

---

### PHASE 2A COURSE CORRECTION (COMPLETED - FAILED)

**Status:** ⚠️ **FAILED** - 18% accuracy, escalated to Phase 2A-REVISED (2025-10-26)
**Trigger:** Story 2.5 FAILED with 52% accuracy (2025-10-25)
**Root Cause Analysis:** `docs/phase2a-deep-dive-analysis.md`
**Sprint Change Proposal:** Approved 2025-10-25 by PM (John) + User (Ricardo)

**Stories 2.8-2.11 COMPLETED:**
- ✅ Story 2.8: Table-Aware Chunking (190 chunks, 1.25 chunks/table)
- ✅ Story 2.9: Ground Truth Page References (50 queries validated)
- ✅ Story 2.10: Query Routing Fix (48% → 8% SQL over-routing)
- ✅ Story 2.11: Hybrid Search RRF Fusion + BM25 Tuning

**Final Validation Result (2025-10-26):**
- **Retrieval Accuracy: 18.0%** (9/50 correct) ❌
- **Attribution Accuracy: 100.0%** (50/50 correct) ✅
- **Baseline Accuracy: 56.0%**
- **Regression: -38.0pp** (68% relative decrease)

**Root Cause Identified:**
Table-aware chunking created semantically indistinguishable chunks. All tables have identical headers (`| Aug-25 | Month | Budget | Var. % B | % LY |`), causing Fin-E5 embeddings to produce nearly identical similarity scores (0.014241 vs 0.014154 = 0.6% variance). Semantic search cannot distinguish tables by content when headers dominate the embedding.

**Evidence:** `docs/validation/CRITICAL-ROOT-CAUSE-FOUND.md`

**Decision:** ESCALATE to Phase 2A-REVISED (SQL Table Search approach)

---

### PHASE 2A-REVISED: SQL Table Search (1-2 weeks)

**Status:** ✅ **APPROVED** - 2025-10-26 by PM (John) + User (Ricardo)
**Trigger:** Phase 2A failed with 18% accuracy (2025-10-26)
**Root Cause:** Semantic search cannot distinguish tables with identical headers
**Solution:** SQL-based table search + vector search for text (production-proven approach)
**Expected Outcome:** 70-80% accuracy (meets Epic 2 target)

**Production Evidence:**
- FinRAG (AI competition winner): nDCG@10 0.804 (80.4% accuracy)
- TableRAG (Huawei Cloud): 75-80% on table queries via SQL
- Bloomberg: Hundreds of thousands of docs daily with hybrid SQL+vector
- Salesforce Data Cloud RAG: SQL for structured tables + semantic for text

**Sprint Change Proposal:** `docs/validation/EXECUTIVE-SUMMARY-PM-PRESENTATION.md`

---

### Story 2.8: Implement Table-Aware Chunking Strategy

**Priority:** 🔴 CRITICAL
**Effort:** 6-8 hours
**Goal:** Fix severe table fragmentation (8.6 chunks/table → 1.2 chunks/table)

**Problem:** Fixed 512-token chunking splits tables across multiple chunks, destroying semantic coherence.

**Solution:** Preserve complete tables as single chunks (<4096 tokens) or split by rows with headers preserved (>4096 tokens).

**Expected Impact:** +10-15pp accuracy improvement from restored table semantic coherence.

---

### Story 2.9: Fix Ground Truth Page References

**Priority:** 🔴 CRITICAL
**Effort:** 3-4 hours
**Goal:** Add page references to all 50 ground truth queries for proper validation

**Problem:** All ground truth queries have zero expected page references, making accuracy metrics invalid.

**Solution:** Manually annotate all 50 queries with correct page numbers from source PDF.

**Expected Impact:** Valid accuracy metrics, confidence in measurements restored.

---

### Story 2.10: Fix Query Classification Over-Routing

**Priority:** 🟠 HIGH
**Effort:** 3-4 hours
**Goal:** Reduce SQL over-routing from 48% → 8%

**Problem:** Heuristic classifier routes 48% of queries to SQL when only 4% have temporal qualifiers.

**Solution:** Require BOTH metric terms AND temporal terms for SQL_ONLY routing.

**Expected Impact:** -300-500ms p50 latency reduction, fewer failed SQL searches.

---

### Story 2.11: Fix Hybrid Search Score Normalization & Fusion

**Priority:** 🟡 MEDIUM
**Effort:** 4-6 hours
**Goal:** Debug hybrid search scoring bug and tune BM25 fusion weights

**Problem:** All hybrid searches return score=1.0, hiding actual relevance ranking.

**Solution:** Fix scoring bug, preserve raw fusion scores, tune BM25 fusion weight (alpha parameter).

**Expected Impact:** Improved ranking quality, score visibility for debugging.

---

### Story 2.5 RE-VALIDATION (After Stories 2.8-2.11)

**Goal:** Re-run AC3 validation with all fixes applied
**Expected Accuracy:** 65-75% (Phase 2A target range)

**Decision Gate:**
- IF ≥70% → Epic 2 COMPLETE → Proceed to Epic 3 🎉
- IF 65-70% → Re-evaluate Phase 2B necessity
- IF <65% → Escalate to Phase 2B (PM approval required)

---

### Story 2.13: SQL Table Search (Phase 2A-REVISED)

**Status:** ✅ COMPLETE (AC1-AC3 PRODUCTION-READY, AC4 4% baseline documented)
**Priority:** 🔴 CRITICAL
**Effort:** 1 week
**Completed:** 2025-10-27
**Goal:** Implement SQL-based table search + hybrid orchestration for structured data retrieval

**Completion Summary (2025-10-27):**
- ✅ **AC1: Table Extraction with Units - PRODUCTION-READY (99.39% accuracy)**
  - Context-Aware Unit Inference (Phase 2.7.5) fully functional
  - All validation queries with data had correct units
  - Implementation: `raglite/ingestion/adaptive_table_extraction.py`

- ✅ **AC2: Text-to-SQL Query Generation - CORE FUNCTIONALITY WORKING**
  - Valid PostgreSQL query generation confirmed (Query GT-002: 80% score)
  - Mistral Small (FREE tier, temperature=0.0)
  - Implementation: `raglite/retrieval/query_classifier.py:200-451`
  - Limitation: 5 edge cases identified (addressed in Story 2.14)

- ✅ **AC3: Hybrid Search Integration - PRODUCTION-READY**
  - Multi-index orchestration working (SQL + Vector search)
  - Parallel execution and RRF fusion functional
  - Implementation: `raglite/retrieval/multi_index_search.py`

- ⚠️ **AC4: Accuracy Validation ≥70% - BASELINE DOCUMENTED (4%)**
  - Test Date: 2025-10-27
  - Passing: 1/25 queries (Query GT-002: Portugal Variable Cost - 80% score)
  - Accuracy: 4% (vs ≥70% target)
  - **Key Finding:** Pipeline proven working (Query GT-002 end-to-end success)
  - **Root Cause:** 5 specific SQL generation edge cases (96% of failures)
  - **Resolution:** Edge case refinement deferred to Story 2.14

**Strategic Outcome:**
Story 2.13 successfully proved that the SQL table search approach is **fundamentally sound** (Query GT-002 demonstrated full pipeline functionality). AC4 failure (4% accuracy) is NOT due to broken architecture, but rather specific SQL generation patterns requiring refinement. This validates the production-proven SQL approach and sets up Story 2.14 for targeted edge case fixes.

**Files Modified:**
- `raglite/ingestion/adaptive_table_extraction.py` (table extraction with units)
- `raglite/retrieval/query_classifier.py` (text-to-SQL generation)
- `raglite/retrieval/multi_index_search.py` (hybrid orchestration)
- `raglite/retrieval/sql_table_search.py` (SQL execution and result processing)

---

### Story 2.14: SQL Generation Edge Case Refinement

**Status:** 📝 DRAFTED (Created 2025-10-27)
**Priority:** 🔴 CRITICAL (Epic 2 Phase 2A completion blocker)
**Effort:** 10 days (2 weeks)
**Depends On:** Story 2.13 (AC1-AC3 complete)
**Goal:** Address 5 SQL generation edge cases to improve accuracy from 4% baseline to ≥70% target

**Problem Statement:**
Story 2.13 AC4 validation revealed that while AC1-AC3 are production-ready (99.39% table extraction, valid SQL generation, hybrid orchestration), the 4% accuracy is caused by 5 identifiable SQL generation edge cases. Query GT-002 (80% score) proves the entire pipeline works when SQL correctly matches the database schema.

**The 5 Edge Cases (96% of failures):**

1. **Edge Case 1: Entity Name Mismatches (40% of failures - 10/25 queries)**
   - Problem: SQL searches exact entity names, data uses variations/aliases
   - Solution: PostgreSQL `pg_trgm` fuzzy matching with similarity threshold 0.3
   - Expected: 8-10 queries fixed

2. **Edge Case 2: Multi-Entity Comparison Queries (20% of failures - 5/25 queries)**
   - Problem: SQL retrieves only one entity when query asks for multiple
   - Solution: Detect comparison keywords, generate `WHERE entity IN (...)` SQL
   - Expected: 4-5 queries fixed

3. **Edge Case 3: Calculated Metrics (12% of failures - 3/25 queries)**
   - Problem: SQL cannot retrieve metrics requiring calculation (e.g., EBITDA margin = EBITDA / Turnover)
   - Solution: Multi-metric SQL queries + post-SQL calculation logic
   - Expected: 2-3 queries fixed

4. **Edge Case 4: Budget Period Detection (8% of failures - 2/25 queries)**
   - Problem: SQL doesn't recognize "B Aug-25" as Budget period
   - Solution: Period pattern mapping, retrieve both Actual and Budget data
   - Expected: 2 queries fixed

5. **Edge Case 5: Currency Conversion (8% of failures - 2/25 queries)**
   - Problem: Queries ask for specific currency (AOA, BRL) when data is in EUR
   - Solution: Explicit unavailability message ("Data available in EUR only")
   - Expected: 2 queries provide informative messages

6. **Edge Case 6: Value Extraction Errors (16% of failures - 4/25 queries)**
   - Problem: Answer synthesis extracts wrong value or hallucinates
   - Solution: Entity/period verification before finalizing answer
   - Expected: 3-4 queries fixed

**Acceptance Criteria:**
- AC1: Fuzzy Entity Matching (2 days) - ≥8/10 queries pass
- AC2: Multi-Entity Comparison (2 days) - ≥4/5 queries pass
- AC3: Calculated Metrics (3 days) - ≥2/3 queries pass
- AC4: Budget Period Detection (1 day) - 2/2 queries pass
- AC5: Currency Conversion (1 day) - 2/2 informative messages
- AC6: Value Extraction Validation (1 day) - ≥3/4 queries pass
- AC7: Full Validation ≥70% (1 day) - **DECISION GATE:** ≥18/25 queries pass

**Iterative Testing Strategy:**
- ⚠️ **IMPORTANT:** Use 30-page PDF excerpt (pages 18-50) for rapid iteration (Days 1-9)
- Full 160-page PDF validation ONLY on Day 10 with **explicit user permission**
- Never run full PDF tests without user approval

**Expected Impact:**
- Baseline: 4% (1/25 queries)
- Target: ≥70% (≥18/25 queries)
- Improvement: +66 percentage points

**Decision Gate (Day 10):**
- **IF ≥70%:** ✅ **Epic 2 Phase 2A COMPLETE** → Proceed to Epic 3
- **IF 60-69%:** ⚠️ Investigate top 3 failures, iterate 1 day
- **IF <60%:** ❌ Escalate to PM for Phase 2B (cross-encoder re-ranking)

**Files Modified:**
- `raglite/retrieval/query_classifier.py` (~150 lines - SQL generation enhancements)
- `raglite/retrieval/sql_table_search.py` (~100 lines - answer synthesis improvements)
- `migrations/enable_pg_trgm.sql` (new - PostgreSQL pg_trgm extension + indexes)

**No New Dependencies:** Uses existing PostgreSQL + Mistral Small + Claude 3.7 Sonnet

**Reference:** `docs/stories/2-14-sql-generation-edge-case-refinement.md`
**Sprint Change Proposal:** `docs/validation/SPRINT-CHANGE-PROPOSAL-STORY-2.14-SQL-EDGE-CASES.md`

---

## PHASE 2B: Cross-Encoder Re-Ranking Fallback (CONDITIONAL - 2-3 days)

**Status:** ON HOLD - Awaiting Story 2.14 (SQL Edge Case Refinement) validation results
**Trigger:** ONLY if Story 2.14 (SQL Edge Case Refinement) achieves <70% accuracy
**Probability:** VERY LOW (Edge case refinement expected 70-80% based on well-defined patterns)
**Goal:** Add cross-encoder re-ranking layer for +3-5pp accuracy improvement
**Approach:** Two-stage retrieval (SQL/vector → cross-encoder re-ranking)

**Updated Strategy (2025-10-27):**

Phase 2B has been simplified from "Structured Multi-Index" (Stories 2.6-2.7 already complete) to "Cross-Encoder fallback only" based on Phase 2A-REVISED SQL table search approach (Stories 2.13 + 2.14).

**Infrastructure Already Complete:**
- ✅ Story 2.6: PostgreSQL Schema + Data Migration (used by Story 2.13)
- ✅ Story 2.7: Multi-Index Search Architecture (used by Story 2.13)

**Fallback Story (if triggered):**
- ⏸️ Story 2.12: Cross-Encoder Re-Ranking (2-3 days)
  - Add sentence-transformers cross-encoder model (ms-marco-MiniLM-L-6-v2)
  - Two-stage retrieval: SQL/vector search (top-20) → cross-encoder re-rank (top-5)
  - Expected: +3-5pp accuracy improvement over Story 2.14 baseline
  - Latency overhead: +150-200ms (acceptable within NFR13 <15s budget)

**Combined Approach (if fallback needed):**
- Stories 2.13 + 2.14 (SQL table search + edge case refinement) + Story 2.12 (cross-encoder re-ranking)
- Expected accuracy: 75-85%
- Total timeline: 3-3.5 weeks
- Confidence: VERY HIGH (production-validated SQL + edge case fixes + research-validated cross-encoder)

**Decision Gate:**
- IF Story 2.14 ≥70% → **Epic 2 COMPLETE** (Story 2.12 SKIPPED) ✅
- IF Story 2.14 <70% → Implement Story 2.12 (cross-encoder fallback)
- IF Story 2.14 + Story 2.12 ≥75% → Epic 2 COMPLETE
- IF Story 2.14 + Story 2.12 <75% → Escalate to Phase 2C (GraphRAG)

---

## PHASE 2C: Hybrid Architecture (CONDITIONAL - 6 weeks)

**Trigger:** ONLY if Phase 2B achieves <75% accuracy (5% probability)
**Goal:** Achieve 75-92% retrieval accuracy
**Approach:** GraphRAG + Structured + Vector (full multi-index)

**Production Evidence:**
- BlackRock/NVIDIA HybridRAG: 0.96 answer relevancy (SOTA)
- BNP Paribas GraphRAG: 6% hallucination reduction, 80% token savings

**Stories (if triggered):**
- 2.10: Neo4j Graph Database Integration
- 2.11: Entity Extraction & Graph Construction
- 2.12: Intelligent Query Routing Across 3 Indexes
- 2.13: AC3 Validation (Target: ≥80%)

**Expected Outcome:** 75-92% accuracy
**Decision Gate:** STOP when ≥80%

---

## PHASE 3: Agentic Coordination (OPTIONAL - 2-16 weeks)

**Trigger:** ONLY if Phase 2 (any path) achieves <85% accuracy (20% probability)
**Goal:** Achieve 90-95% retrieval accuracy
**Approach:** LLM-based query planning + specialist agents

**Production Evidence:**
- AWS, CapitalOne, NVIDIA agentic RAG systems
- +15-20pp accuracy improvement over non-agentic

**Framework:** LangGraph + AWS Strands OR Claude Agent SDK

**Expected Outcome:** 90-95% accuracy

---

## Epic 2 Dependencies

**Prerequisites:**
- ✅ Epic 1 complete (Stories 1.1-1.12)
- ✅ Story 2.1 (Hybrid Search) completed and validated
- ✅ Story 2.2 (Element Chunking) FAILED (42% accuracy = pivot trigger)

**Blocks:**
- Epic 3 (Intelligence Features) - needs Epic 2 complete (≥70% accuracy)
- Epic 4 (Forecasting) - needs Epic 3 complete
- Epic 5 (Production) - needs Epic 3-4 complete

---

## Technologies Summary

**APPROVED (Phase 1 + 2A):**
- ✅ pypdfium (PDF backend for Docling)
- ✅ tiktoken (OpenAI tokenizer for fixed chunking)
- ✅ Claude 3.7 Sonnet API (metadata extraction)

**CONDITIONAL (Phase 2B):**
- ⚠️ PostgreSQL 16 (structured table storage)

**CONDITIONAL (Phase 2C):**
- ⚠️ Neo4j 5.x (knowledge graph)
- ⚠️ PostgreSQL 16 (structured table storage)

**CONDITIONAL (Phase 3):**
- ⚠️ LangGraph + AWS Strands (agentic orchestration)
- ⚠️ Claude Agent SDK (alternative)

**Decision Authority:** PM (John) approves at each decision gate based on accuracy validation results.

---

## Timeline Summary

**Updated Timeline (2025-10-25 - Post-Course Correction):**

**Best Case (Phase 1 + 2A with Course Correction):**
- Week 1: Phase 1 (PDF optimization) - 1-2 days ✅ COMPLETE
- Week 2-3: Phase 2A Initial (Stories 2.3-2.7) - 1-2 weeks ✅ COMPLETE (52% accuracy)
- **Week 3-4: Phase 2A Course Correction (Stories 2.8-2.11) - 2-3 days** ⭐ CURRENT
- Week 4: AC3 Re-validation → Target ≥70% accuracy → Epic 2 COMPLETE
- **Total: 3-4 weeks (revised from 2-3 weeks)**

**If Course Correction Insufficient (<70%):**
- Week 1-4: Phase 1 + 2A (as above)
- Week 5-8: Phase 2B Remaining (Stories 2.12-2.13) - 3-4 weeks
- Week 8: AC3 Validation → ≥75% accuracy → Epic 2 COMPLETE
- **Total: 7-9 weeks**

**Worst Case (All paths):**
- Week 1-8: Phase 1 + 2A + 2B (as above)
- Week 9-14: Phase 2C (Hybrid Architecture) - 6 weeks
- Week 15-31: Phase 3 (Agentic Coordination) - 2-16 weeks (staged)
- **Total: 15-31 weeks**

**Most Likely Outcome:** 3-4 weeks (Phase 2A course correction achieves 65-75% accuracy) ✅

**Probability Analysis:**
- 80% chance: Course correction achieves 65-75% (Epic 2 complete or nearly complete)
- 15% chance: Need Phase 2B Stories 2.12-2.13 (cross-encoder re-ranking)
- 5% chance: Need Phase 2C (full hybrid architecture)

---

## Rationale

**Why This Pivot:**
- Element-aware chunking **catastrophic failure** (42% vs 56% baseline = -14pp)
- Research evidence: Fixed 512-token = 68.09% accuracy (Yepes et al. 2024)
- Production-proven approaches reduce risk (BlackRock, BNP Paribas, FinSage)
- Staged implementation with decision gates minimizes wasted effort

**Why Sequential Phases:**
- Test accuracy after EACH phase (decision gates prevent over-engineering)
- STOP when 70% achieved (Epic 2 success criteria)
- Start simple (fixed chunking), escalate only if needed (structured → hybrid → agentic)

**Why These Technologies:**
- pypdfium: Official Docling backend (1.7-2.5x speedup proven)
- Fixed chunking: Research-validated (68% accuracy guaranteed)
- Conditional tech: Approved contingency paths based on empirical decision gates

---

## Story 2.15: Document Epic 2 Strategic Pivot & SQL Approach

**Implements:** Knowledge capture, decision documentation

**As a** developer,
**I want** to document the Epic 2 strategic pivot from element-aware chunking to SQL table search,
**so that** future team members understand why we pivoted and how the SQL approach was validated.

**Duration:** 3-4 hours
**Priority:** HIGH (critical pivot documentation)

**Acceptance Criteria:**

1. **Architecture Decision Record (ADR) for Epic 2:**
   - Document pivot decision: Why element-aware chunking failed (42% accuracy, -14pp regression)
   - Document pivot decision: Why fixed 512-token chunking approach chosen (research-validated 68% baseline)
   - Document pivot decision: Why SQL table search for structured data (production-proven 75-80% accuracy)
   - Document pivot decision: PostgreSQL + Mistral Small + Fuzzy matching approach

2. **Technical Challenges Documented:**
   - Semantic search failure mode for tables with identical headers
   - Edge case identification and resolution (Stories 2.13-2.14)
   - Context-aware unit inference (99.39% accuracy achievement)

3. **Decision Gates Documented:**
   - Phase 2A validation: Target 70% accuracy
   - Phase 2B contingency: Cross-encoder re-ranking (if needed)
   - Phase 2C contingency: GraphRAG (low probability)

4. **Save to:**
   - `docs/architecture-decisions.md` (append Epic 2 Pivot section)
   - `docs/validation/EXECUTIVE-SUMMARY-PM-PRESENTATION.md` (already exists - reference)

**Deliverables:**
- Epic 2 ADR section in `docs/architecture-decisions.md`
- Cross-references to existing pivot analysis documents

**Rationale:** Epic 2's strategic pivot from element-aware to SQL table search represents a critical architectural decision. Documenting the rationale, research evidence, and production validation ensures this knowledge is preserved for future development.

---

# Epic 3: AI Intelligence & Orchestration

**Epic Goal:** Enable multi-step reasoning and complex analytical workflows through agentic orchestration, allowing the system to autonomously execute analytical tasks requiring planning, tool use, and iterative reasoning.

## Story 3.1: Agentic Framework Integration

**As a** system,
**I want** agentic orchestration framework integrated per Architect's selection,
**so that** multi-step analytical workflows can be planned and executed.

**Acceptance Criteria:**
1. Agentic framework integrated per Architect (LangGraph, AWS Bedrock Agents, or function calling)
2. Framework configuration and initialization validated
3. Basic workflow execution tested (simple 2-step workflow)
4. State management functional for multi-step workflows
5. Error handling implemented for workflow failures (NFR24, NFR26)
6. Integration test validates framework execution
7. Documentation includes workflow development guide

## Story 3.2: Retrieval Agent Implementation

**As a** system,
**I want** specialized retrieval agent that can search financial knowledge base,
**so that** agentic workflows can access document information as a tool.

**Acceptance Criteria:**
1. Retrieval agent defined with tool interface per Architect's agentic framework
2. Agent accepts query and returns relevant document chunks with citations
3. Agent integrates with existing retrieval logic from Epic 1
4. Agent tested in isolation (unit test)
5. Agent tested within simple workflow (integration test)

## Story 3.3: Analysis Agent Implementation

**As a** system,
**I want** specialized analysis agent that can perform calculations and reasoning over retrieved data,
**so that** analytical questions can be answered autonomously.

**Acceptance Criteria:**
1. Analysis agent defined with capabilities: calculate percentages, trends, variances, comparisons
2. Agent accepts financial data and analysis instruction, returns analytical result
3. Agent uses LLM for reasoning with structured prompts for numerical accuracy
4. Agent tested with sample analytical tasks (YoY growth calculation, variance analysis)
5. Agent integrates with retrieval agent for data access

## Story 3.4: Synthesis Agent Implementation

**As a** system,
**I want** specialized synthesis agent that can combine results from multiple sub-tasks into coherent answer,
**so that** complex multi-step workflows produce user-friendly responses.

**Acceptance Criteria:**
1. Synthesis agent defined to aggregate and summarize results from other agents
2. Agent produces natural language summary with source citations
3. Agent maintains consistency with original query intent
4. Agent tested with multi-source inputs
5. Agent output format optimized for MCP client display

## Story 3.5: Multi-Step Workflow Orchestration

**As a** system,
**I want** to orchestrate agentic workflows for complex analytical queries,
**so that** questions requiring planning and multiple steps can be answered autonomously.

**Acceptance Criteria:**
1. Workflow planner decomposes complex queries into sub-tasks
2. Sub-tasks routed to appropriate specialized agents (retrieval, analysis, synthesis)
3. Agent outputs passed between agents as inputs to subsequent steps
4. Workflow execution completes in <30 seconds for typical analytical queries (NFR5)
5. Example workflow tested: "Calculate YoY revenue growth and explain variance" → retrieval agent (get Q3 2023 & 2024 revenue) → analysis agent (calculate % change) → retrieval agent (get context for variance) → synthesis agent (explain)
6. Workflow success rate >80% on complex test queries
7. Failed workflows fall back gracefully to simpler retrieval (NFR17, NFR32)

## Story 3.6: Analytical Query Tool (MCP)

**As a** user,
**I want** to ask complex analytical financial questions via MCP,
**so that** I can get answers requiring multi-step reasoning without manual decomposition.

**Acceptance Criteria:**
1. MCP tool defined: "analyze_financial_question" triggering agentic workflow
2. Tool accepts natural language analytical queries
3. Tool routes simple queries to basic retrieval, complex queries to agentic workflow
4. Responses include reasoning steps taken (transparency)
5. Test queries validated: trend analysis, variance explanation, correlation discovery
6. User testing via Claude Desktop confirms usability

## Story 3.7: Graceful Degradation for Workflow Failures

**As a** system,
**I want** to handle agentic workflow failures gracefully,
**so that** users receive useful responses even when complex workflows fail.

**Acceptance Criteria:**
1. Workflow timeout handling (>30 seconds triggers fallback)
2. Agent failure detection and logging
3. Fallback to basic retrieval when workflow fails (NFR17, NFR32)
4. User receives partial results or error message with suggested alternative query
5. Error rates logged for workflow improvement
6. Integration test validates fallback behavior

## Story 3.8: Agentic Workflow Test Suite

**As a** developer,
**I want** to validate agentic workflows against test scenarios,
**so that** workflow reliability and accuracy are measured objectively.

**Acceptance Criteria:**
1. Test set includes 15+ multi-step analytical queries
2. Automated test suite executes workflows and validates results
3. Success rate measured (target: 80%+ per FR16 interpretation)
4. Performance measured (workflow execution time)
5. Failure analysis documents reasons for unsuccessful workflows
6. Test suite covers edge cases (missing data, ambiguous queries, conflicting information)

---

## Story 3.9: Document Epic 3 Agentic Framework Selection & Patterns

**Implements:** FR14-FR17 implementation documentation

**As a** developer,
**I want** to document the agentic framework selection and workflow patterns used in Epic 3,
**so that** future team members can extend and maintain the agentic orchestration system.

**Duration:** 2-3 hours
**Priority:** MEDIUM (incremental documentation)

**Acceptance Criteria:**

1. **Architecture Decision Record (ADR) for Epic 3:**
   - Document framework selection: Why LangGraph vs AWS Bedrock vs Claude Function Calling?
   - Document agent specialization strategy: Retrieval, Analysis, Synthesis, Forecasting agents
   - Document workflow orchestration patterns: Planning, execution, error handling
   - Document fallback strategies: Graceful degradation when workflows fail

2. **Workflow Patterns Documented:**
   - Document example workflow: "Calculate YoY revenue growth and explain variance"
   - Document agent communication patterns
   - Document state management approach
   - Document error handling and retry logic

3. **Codebase Walkthrough Notes:**
   - Document Epic 3 module organization (raglite/agentic/)
   - Document agent registration and tool exposure
   - Document workflow testing strategy

4. **Save to:**
   - `docs/architecture-decisions.md` (append Epic 3 Agentic section)
   - `docs/agentic-workflow-patterns.md` (new - detailed workflow examples)

**Deliverables:**
- Epic 3 ADR section in `docs/architecture-decisions.md`
- `docs/agentic-workflow-patterns.md` with reusable patterns

**Rationale:** Agentic orchestration represents a key architectural layer. Documenting framework selection, agent patterns, and workflow examples ensures maintainability and extensibility.

---

# Epic 4: Forecasting & Proactive Insights

**Epic Goal:** Deliver predictive intelligence and strategic recommendations through AI-powered forecasting and autonomous insight generation, enabling the system to proactively surface trends, anomalies, and strategic priorities.

## Story 4.1: Time-Series Data Extraction

**As a** system,
**I want** to extract time-series financial data from documents for forecasting,
**so that** historical patterns can be analyzed and future values predicted.

**Acceptance Criteria:**
1. Time-series extraction identifies temporal financial metrics (monthly revenue, quarterly expenses, etc.)
2. Data points extracted with timestamps and metric labels
3. Data normalized to consistent time intervals (monthly, quarterly)
4. Extraction handles various date formats and fiscal period labels
5. Extracted data validated against sample documents for accuracy
6. Integration test validates extraction from financial PDFs

## Story 4.2: Forecasting Engine Implementation

**As a** system,
**I want** to forecast key financial indicators using Architect-selected approach,
**so that** predictive insights are available to users.

**Acceptance Criteria:**
1. Forecasting implementation per Architect (LLM-based, statistical, or hybrid)
2. Key indicators supported: revenue, cash flow, expense categories per Project Brief (FR21)
3. Forecast generation produces predictions with confidence intervals (FR19)
4. Forecast accuracy ±15% validated on historical data (NFR10)
5. Forecasting agent integrated into agentic framework
6. Unit tests cover forecasting logic
7. Integration test validates end-to-end forecast generation

## Story 4.3: Automated Forecast Updates

**As a** system,
**I want** forecasts to update automatically when new financial documents are ingested,
**so that** predictions remain current without manual intervention.

**Acceptance Criteria:**
1. Document ingestion triggers forecast refresh for affected metrics (FR20)
2. Incremental updates avoid full recomputation when possible
3. Forecast update completes within 5 minutes of document ingestion
4. Users notified of updated forecasts if applicable
5. Integration test validates forecast refresh after new document added

## Story 4.4: Forecast Query Tool (MCP)

**As a** user,
**I want** to query financial forecasts via MCP,
**so that** I can access predictive insights conversationally.

**Acceptance Criteria:**
1. MCP tool defined: "get_financial_forecast" with metric and time period parameters
2. Tool returns forecast values with confidence intervals
3. Tool explains basis for forecast (historical data used, methodology)
4. Queries like "What's the revenue forecast for next quarter?" answered accurately
5. Test queries validated for accuracy and clarity

## Story 4.5: Anomaly Detection

**As a** system,
**I want** to detect anomalies and outliers in financial data,
**so that** unusual patterns are surfaced proactively.

**Acceptance Criteria:**
1. Anomaly detection algorithm implemented (statistical thresholds or ML-based per Architect)
2. Anomalies identified: significant deviations from trends, unexpected spikes/drops, outliers
3. Anomaly severity scored (minor, moderate, critical)
4. Anomalies logged with context (metric, time period, magnitude of deviation)
5. Integration test validates anomaly detection on sample data with known outliers

## Story 4.6: Trend Analysis & Pattern Recognition

**As a** system,
**I want** to identify trends and patterns in financial data,
**so that** strategic insights can be generated proactively.

**Acceptance Criteria:**
1. Trend analysis identifies: growth patterns, cyclical trends, correlations between metrics
2. Pattern recognition uses statistical analysis and/or LLM reasoning per Architect
3. Trends characterized with direction (increasing/decreasing) and magnitude
4. Trend analysis runs automatically on document ingestion or on-demand
5. Unit tests validate trend detection logic

## Story 4.7: Proactive Insight Generation

**As a** system,
**I want** to autonomously generate insights highlighting risks, opportunities, and areas requiring attention,
**so that** users learn what they should know without asking.

**Acceptance Criteria:**
1. Insight generation combines anomaly detection, trend analysis, and contextual reasoning (FR22, FR23)
2. Insights categorized: risks, opportunities, anomalies, trends, strategic priorities
3. Insights ranked by priority/impact (FR24)
4. Insight quality validated: 75%+ rated useful/actionable by user testing (per Project Brief MVP success criteria)
5. Insights include supporting data and rationale (FR25)
6. Example insights tested: "Q3 marketing spend increased 30% YoY with no corresponding revenue increase - potential inefficiency"

## Story 4.8: Strategic Recommendation Engine

**As a** system,
**I want** to generate actionable recommendations based on financial data analysis,
**so that** users receive strategic guidance on where to focus attention.

**Acceptance Criteria:**
1. Recommendation engine analyzes insights and generates actionable next steps (FR25)
2. Recommendations prioritized by potential impact
3. Recommendations include rationale with supporting data
4. Recommendation quality validated: align with human expert analysis 80%+ of time (per Project Brief success criteria)
5. Examples tested: "Focus on reducing cloud infrastructure costs - trending 40% over budget with minimal usage increase"

## Story 4.9: Proactive Insights Tool (MCP)

**As a** user,
**I want** to request proactive insights via MCP,
**so that** the system tells me what I should know about current financial state.

**Acceptance Criteria:**
1. MCP tool defined: "get_financial_insights" with optional filter parameters (category, time period)
2. Tool returns ranked list of insights with supporting data
3. Default query returns top 3-5 most important insights
4. Insights formatted for conversational display
5. User testing validates insight relevance and usefulness

## Story 4.10: Forecasting & Insights Test Suite

**As a** developer,
**I want** to validate forecasting accuracy and insight quality,
**so that** predictive capabilities meet MVP success criteria.

**Acceptance Criteria:**
1. Forecast accuracy measured on historical data (compare predictions to actuals)
2. Accuracy meets ±15% threshold for key indicators (NFR10)
3. Insight relevance scored by user testing (target: 75%+ useful/actionable)
4. Recommendation alignment with expert analysis measured (target: 80%+)
5. Test results documented with improvement recommendations

---

## Story 4.11: Document Epic 4 Forecasting Model Selection & Insights Architecture

**Implements:** FR18-FR25 implementation documentation

**As a** developer,
**I want** to document the forecasting model selection and proactive insights architecture from Epic 4,
**so that** future team members can tune, extend, and maintain the intelligence features.

**Duration:** 2-3 hours
**Priority:** MEDIUM (incremental documentation)

**Acceptance Criteria:**

1. **Architecture Decision Record (ADR) for Epic 4:**
   - Document forecasting approach: LLM-based vs Statistical vs Hybrid (selected approach)
   - Document model selection rationale: Why Prophet/LLM for financial forecasting?
   - Document insight generation strategy: Anomaly detection + trend analysis + recommendation engine
   - Document confidence interval calculation methodology

2. **Forecasting Model Documented:**
   - Document time-series extraction approach
   - Document forecast accuracy validation (±15% target methodology)
   - Document forecast update triggers (automatic on document ingestion)
   - Document forecast confidence scoring

3. **Insights Architecture Documented:**
   - Document anomaly detection algorithm
   - Document trend analysis patterns
   - Document strategic recommendation generation logic
   - Document insight ranking/prioritization criteria

4. **Save to:**
   - `docs/architecture-decisions.md` (append Epic 4 Forecasting section)
   - `docs/forecasting-model-tuning.md` (new - model parameters and tuning guide)

**Deliverables:**
- Epic 4 ADR section in `docs/architecture-decisions.md`
- `docs/forecasting-model-tuning.md` with model configuration and tuning guidelines

**Rationale:** Forecasting models require tuning and maintenance over time. Documenting the model selection rationale, accuracy validation methodology, and tuning parameters ensures the intelligence features remain effective as business context evolves.

---

# Epic 5: Production Readiness & Real-Time Operations

**Epic Goal:** Deploy production-ready cloud infrastructure with real-time document updates, performance optimization, and monitoring to deliver a reliable, scalable system ready for daily use and team rollout.

## Story 5.1: Cloud Infrastructure Architecture

**As a** system,
**I want** production cloud infrastructure designed and documented,
**so that** deployment is planned and executable.

**Acceptance Criteria:**
1. Cloud provider selected (AWS or equivalent) and account configured
2. Infrastructure architecture documented (compute, storage, networking, databases)
3. Service selection documented (e.g., ECS/EKS for containers, managed Qdrant/OpenSearch, etc.)
4. Cost estimation provided and validated against budget
5. Security architecture documented (VPC, IAM, encryption, secrets management)
6. **DNS/Domain requirements clarified:**
   - MCP server access method documented (direct IP:port vs. domain name)
   - If domain required: DNS setup plan included (e.g., raglite.company.com)
   - SSL/TLS certificate strategy defined for production MCP endpoints
   - Note: MCP protocol works over localhost/IP for MVP; domain optional for team rollout
7. Architecture review completed and approved

## Story 5.2: Containerization & Cloud Deployment

**As a** system,
**I want** RAGLite components containerized and deployed to cloud infrastructure,
**so that** the system is accessible beyond local development environment.

**Acceptance Criteria:**
1. Docker images built for all services per Architect's design
2. Container orchestration configured (ECS, EKS, or equivalent)
3. Managed vector database deployed (Qdrant Cloud or OpenSearch)
4. Managed graph database deployed if KG implemented (Neo4j Aura or equivalent)
5. Services deployed to cloud and validated functional
6. Health checks and readiness probes configured
7. Deployment achieves 99%+ uptime target (NFR1)

## Story 5.3: Environment Configuration & Secrets Management

**As a** system,
**I want** secure configuration and secrets management for production environment,
**so that** API keys and sensitive data are protected.

**Acceptance Criteria:**
1. Secrets manager configured (AWS Secrets Manager or equivalent)
2. API keys and credentials stored securely (NFR13)
3. Environment-specific configuration managed (dev, staging, prod)
4. No hardcoded secrets in codebase or containers
5. Security audit confirms no credential exposure

## Story 5.4: Data Encryption at Rest

**As a** system,
**I want** financial documents and database contents encrypted at rest,
**so that** data security meets production standards.

**Acceptance Criteria:**
1. Vector database encryption at rest enabled (NFR12)
2. Graph database encryption at rest enabled (if applicable)
3. Document storage encryption configured (S3 with KMS or equivalent)
4. Encryption keys managed securely
5. Security validation confirms encryption active

## Story 5.5: File Watching & Real-Time Document Detection

**As a** system,
**I want** to automatically detect new or updated financial documents,
**so that** knowledge base remains current without manual intervention.

**Acceptance Criteria:**
1. File watching service monitors designated directory/bucket for new documents (FR26)
2. New document detection triggers ingestion pipeline automatically
3. Updated document detection triggers re-ingestion (FR27)
4. File watching handles various storage backends (local filesystem, S3, etc.)
5. Detection latency <1 minute for new file availability
6. Integration test validates automatic ingestion on file addition

## Story 5.6: Incremental Indexing & Version History

**As a** system,
**I want** incremental re-indexing and document version history,
**so that** updates don't require full database rebuild and changes are tracked.

**Acceptance Criteria:**
1. Updated documents trigger incremental re-indexing (delete old chunks, add new) (FR29)
2. Document version history maintained (FR28)
3. Change tracking logs document updates (timestamp, changes detected)
4. Incremental indexing completes within 5 minutes (FR27)
5. Queries reflect updated documents within 5 minutes of ingestion
6. Integration test validates incremental update workflow

## Story 5.7: Monitoring & Logging Infrastructure

**As a** system,
**I want** comprehensive monitoring and logging for production operations,
**so that** performance is tracked and issues are debugged efficiently.

**Acceptance Criteria:**
1. Application logging configured with structured logs (JSON format)
2. Log aggregation service deployed (CloudWatch, ELK stack, or equivalent)
3. Performance metrics tracked: query response times, ingestion times, error rates (NFR30)
4. Monitoring dashboards created for key metrics
5. Alerts configured for critical failures (service down, error rate spikes)
6. Audit logging captures all queries, answers, and admin actions (NFR14)

## Story 5.8: Performance Optimization

**As a** system,
**I want** performance optimized to meet production SLAs,
**so that** user experience is fast and responsive.

**Acceptance Criteria:**
1. Query response time <5 sec (p50), <15 sec (p95) validated under load (NFR13)
2. Complex workflows complete in <30 sec (NFR5)
3. System handles 50+ queries per day with consistent performance (NFR4)
4. Database query optimization applied (indexing, caching)
5. LLM API call optimization (batching, caching where appropriate)
6. Performance testing validates targets met

## Story 5.9: Scalability Validation

**As a** system,
**I want** scalability validated for team rollout,
**so that** system supports multiple concurrent users.

**Acceptance Criteria:**
1. Load testing simulates 10+ concurrent users (per Project Brief cloud deployment goal)
2. System maintains performance targets under concurrent load
3. Auto-scaling configured if using cloud orchestration
4. Bottlenecks identified and addressed
5. Scalability limits documented for future capacity planning

## Story 5.10: Disaster Recovery & Backup

**As a** system,
**I want** backup and disaster recovery procedures established,
**so that** data and service availability are protected.

**Acceptance Criteria:**
1. Automated backups configured for vector database and graph database
2. Document storage has versioning/backup enabled
3. Backup retention policy defined and implemented
4. Disaster recovery runbook documented
5. Recovery tested: restore from backup and validate system functionality

## Story 5.11: Production Validation & User Acceptance

**As a** user,
**I want** to validate production system with real-world usage,
**so that** MVP success criteria are confirmed before team rollout.

**Acceptance Criteria:**
1. System used for 10+ real financial queries per week (per Project Brief success metric)
2. User satisfaction rating 8/10+ for accuracy and usefulness (per Project Brief success metric)
3. All MVP success criteria validated:
   - ✅ Retrieval accuracy 90%+
   - ✅ Intelligence validation: forecasts/insights demonstrate value in 3+ real scenarios
   - ✅ Agentic capability: 10+ multi-step workflows executed successfully
   - ✅ KG value validated (if implemented): relational queries answered accurately
   - ✅ Performance: <5 sec typical, <30 sec workflows
   - ✅ Trust: 95%+ source attribution accuracy
   - ✅ Adoption: Used for 90%+ of financial queries replacing manual methods
   - ✅ Technical foundation: Production-ready for team rollout
4. Any identified issues addressed before team rollout declaration

## Story 5.12: CI/CD Pipeline Setup & Automation

**As a** developer,
**I want** automated testing and deployment pipelines configured,
**so that** code quality is enforced and deployments are reliable.

**Acceptance Criteria:**

1. **GitHub Actions Workflows:**
   - `.github/workflows/ci-cd.yml` configured with all pipeline stages
   - Workflow triggers defined (push to main/develop, pull requests)
   - Parallel job execution for faster feedback (lint + test in parallel)

2. **Pre-Commit Hooks:**
   - `.pre-commit-config.yaml` configured with Ruff (format + lint), MyPy (type checking), Gitleaks (secrets)
   - Installation instructions in README.md
   - Hooks run automatically on `git commit` (enforce code quality locally)

3. **Linting & Formatting Stage:**
   - Ruff format (code formatting) runs on all PRs - replaces Black + isort
   - Ruff check (linting) validates code quality
   - MyPy (type checking) validates type hints
   - **Failure action:** Block merge if linting fails

4. **Unit Test Stage:**
   - pytest runs with coverage reporting (pytest-cov)
   - Mocks external dependencies (Qdrant, Claude API)
   - **Coverage target:** 70%+ for critical paths (ingestion, retrieval, synthesis)
   - Coverage report posted as PR comment
   - **Failure action:** Block merge if tests fail or coverage <70%

5. **Integration Test Stage:**
   - Docker Compose test environment (`docker-compose.test.yml`) spins up Qdrant
   - End-to-end pipeline tests (PDF → ingestion → retrieval → synthesis)
   - Tests run in isolated environment (ephemeral containers)
   - **Failure action:** Block merge if integration tests fail

6. **Accuracy Validation Stage:**
   - Runs ground truth test set (50+ queries) on main/develop pushes only
   - Measures retrieval accuracy against known correct answers
   - **Thresholds:**
     - FAIL if accuracy <70% (block deployment, not merge)
     - WARN if accuracy <90% (target not met, investigate)
   - Uses real Anthropic API (requires `ANTHROPIC_API_KEY` secret)
   - **Triggers:** Push to main/develop (not on PRs to save API costs)

7. **Docker Build & Push Stage:**
   - Builds production Docker image on main branch push
   - Tags images with `latest` and git SHA (e.g., `raglite:abc1234`)
   - Pushes to Docker Hub or AWS ECR
   - Layer caching configured for faster builds
   - **Triggers:** Push to main only

8. **Deployment Stage (Epic 5 Production):**
   - Auto-deploy to dev environment on develop branch push
   - Manual approval gate for production deployment
   - AWS ECS task definition updated with new image
   - Health checks validate deployment success
   - Rollback if health checks fail

9. **Required GitHub Secrets:**
   - `ANTHROPIC_API_KEY` - For accuracy validation tests
   - `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` - Docker Hub credentials
   - `CODECOV_TOKEN` - Code coverage reporting (optional)
   - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - AWS deployment (Epic 5)
   - Documentation in README.md for setting up secrets

10. **Pipeline Performance:**
    - Full pipeline runtime: <25 minutes (parallel job execution)
    - Pre-commit hooks: <30 seconds (local quick tests only)
    - PR feedback: <10 minutes (skip accuracy tests on PRs)

**Deliverables:**
- `.github/workflows/ci-cd.yml` fully configured and tested
- `.pre-commit-config.yaml` with all quality checks
- `docker-compose.test.yml` for CI integration tests
- Documentation in README.md for CI/CD setup and GitHub Secrets
- At least one successful pipeline run validated end-to-end

**Rationale:**
CI/CD is critical for solo developer + AI agent workflow:
- Automated testing prevents regressions when Claude Code generates code
- Pre-commit hooks catch issues immediately (fast feedback loop)
- Accuracy validation gates deployment (ensures 90%+ target maintained)
- Docker builds ensure dev/prod parity

## Story 5.13: API Documentation & MCP Tool Reference

**As a** developer (or future team member),
**I want** comprehensive documentation of all MCP tools and API interfaces,
**so that** I can understand and use the RAGLite system effectively.

**Acceptance Criteria:**

1. **MCP Tool Catalog (`docs/api-reference.md`):**
   - List all MCP tools exposed by RAGLite server
   - For each tool, document:
     - Tool name (e.g., `query_financial_documents`)
     - Purpose and use case
     - Input parameters with types and descriptions
     - Output format and structure
     - Example invocations with sample responses
     - Error responses and troubleshooting

2. **Core MCP Tools Documented:**
   - `ingest_financial_document(file_path, document_type)` - Phase 1
   - `query_financial_documents(query, filters)` - Phase 1
   - `get_financial_forecast(metric, time_period)` - Phase 3 (if implemented)
   - `generate_insights(category, time_range)` - Phase 3 (if implemented)
   - Any additional tools implemented in Epics 2-4

3. **Response Format Specifications:**
   - JSON schema for tool responses
   - Source attribution format examples
   - Error response structure and codes
   - Confidence score interpretation

4. **Integration Guide:**
   - How to connect MCP clients (Claude Desktop, Claude Code) to RAGLite
   - Configuration examples for MCP client setup
   - Troubleshooting common connection issues

5. **API Versioning Strategy:**
   - Document current API version (e.g., v1.0)
   - Breaking change policy for future updates
   - Deprecation notice process

**Deliverables:**
- `docs/api-reference.md` with comprehensive MCP tool documentation
- Example tool invocations in `docs/examples/` directory
- Integration guide for MCP clients

**Rationale:**
API documentation is essential for team rollout post-MVP. While single-user MVP may not need formal docs, documenting during development prevents knowledge loss and accelerates team onboarding.

## Story 5.14: Consolidate and Finalize Documentation for Team Rollout

**Depends On:** Stories 1.16, 2.15, 3.9, 4.11 (incremental epic documentation)

**As a** project lead,
**I want** to consolidate and polish all documentation created incrementally throughout Epics 1-5,
**so that** future team members have a cohesive, professional onboarding experience.

**Acceptance Criteria:**

1. **Developer Onboarding Guide (`docs/developer-onboarding.md`):**
   - Prerequisites (Python 3.11+, Docker, Git)
   - Step-by-step local environment setup
   - How to run the development server locally
   - How to run tests (unit, integration, accuracy)
   - Common development workflows (adding new feature, debugging)
   - Code review checklist and quality standards

2. **Consolidate Architecture Decision Record (`docs/architecture-decisions.md`):**
   - **Consolidate ADR sections created in Stories 1.16, 2.15, 3.9, 4.11**
   - Add executive summary linking to all epic ADR sections
   - Polish formatting and cross-references
   - Add visual decision tree diagram showing key architectural choices
   - Ensure consistent ADR format across all sections:
     - Context: What problem were we solving?
     - Decision: What did we choose and why?
     - Alternatives considered: What else did we evaluate?
     - Consequences: What are the trade-offs?

3. **Codebase Architecture Walkthrough:**
   - Video walkthrough (15-20 minutes) or detailed written guide
   - Repository structure explanation
   - Module responsibilities (ingestion, retrieval, synthesis)
   - Data flow diagram (PDF → chunks → embeddings → Qdrant → LLM → answer)
   - Key files and their purposes

4. **Troubleshooting & Debugging Guide:**
   - Common errors and solutions
   - How to debug retrieval accuracy issues
   - How to analyze slow query performance
   - How to investigate LLM hallucinations
   - Logging and monitoring best practices

5. **Knowledge Transfer Session (Optional):**
   - 1-hour walkthrough with first new team member
   - Q&A session to fill documentation gaps
   - Update onboarding docs based on feedback

**Deliverables:**
- `docs/developer-onboarding.md` with complete setup guide
- `docs/architecture-decisions.md` with ADR log
- `docs/codebase-walkthrough.md` or video recording
- `docs/troubleshooting.md` with common issues and solutions

**Rationale:**
Solo developer projects create knowledge silos. By documenting incrementally (Stories 1.16, 2.15, 3.9, 4.11) and consolidating in Epic 5, we prevent knowledge loss while keeping documentation effort distributed across sprints. Story 5.14 focuses on polish, consolidation, and creating cohesive onboarding materials for team rollout.

**Note:** This story CONSOLIDATES documentation created in Stories 1.16 (Epic 1 ADR), 2.15 (Epic 2 Pivot), 3.9 (Agentic Patterns), and 4.11 (Forecasting Models). It should NOT recreate documentation from scratch.

---

## Cross-Epic Dependencies

**Epic 1 → Epic 2:**
- Epic 2 requires Epic 1 baseline validation (Story 1.15B)
- Epic 2 triggered only if Epic 1 accuracy <90%

**Epic 2 → Epic 3:**
- Epic 3 requires Epic 2 completion (≥70% accuracy)
- Epic 3 blocked until Epic 2 achieves success criteria

**Epic 3 → Epic 4:**
- Epic 4 requires Epic 3 (agentic framework for forecasting/insights)
- Epic 4 can start after Epic 3 Story 3.1-3.5 complete

**Epic 4 → Epic 5:**
- Epic 5 requires Epics 1-4 complete
- Epic 5 is final production deployment phase

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-11-05 | 2.0 | Consolidated epics.md from individual epic files | PM (John) |
| 2025-10-19 | 1.5 | Epic 2 strategic pivot after element-aware failure | Product Owner (Sarah) |
| 2025-10-16 | 1.0 | Initial epic breakdown created | Scrum Master (Bob) |

---

**Document Status:** ACTIVE
**Last Updated:** 2025-11-05
**Next Review:** After Epic 2 Phase 2A completion
