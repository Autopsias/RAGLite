# RAGLite Product Backlog

This backlog tracks technical debt, deferred features, and follow-up work identified during development and reviews.

## Format

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
|------|-------|------|------|----------|-------|--------|-------|

## Open Items

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
|------|-------|------|------|----------|-------|--------|-------|
| 2025-10-12 | 1.4 | 1 | Enhancement | MEDIUM | Phase 2 | Deferred | **DECISION: Deferred to Phase 2.** AC3 "where applicable" satisfied by page_number (NFR7). Section headings require Docling structure parsing, adding complexity to MVP. Current page-level attribution sufficient for Phase 1 (90% accuracy target). Consider for Phase 2 if citation granularity becomes issue. Files: raglite/shared/models.py:32 |
| 2025-10-12 | 1.4 | 1 | TechDebt | LOW | TBD | Resolved | Document deferred features explicitly (table-aware chunking, manual QA, performance/integration tests). Related: AC2, AC4, AC5, AC7, AC9. RESOLVED: backlog.md created with comprehensive tracking. |
| 2025-10-12 | 1.4 | 1 | Test | HIGH | Dev | Resolved | Add integration test for page number flow (test_ingestion_integration.py with real PDF). Story 1.5 prerequisite. Files: tests/integration/test_ingestion_integration.py. RESOLVED: test_page_number_flow_through_chunking_pipeline added (lines 174-234). |
| 2025-10-12 | 1.4 | 1 | Test | MEDIUM | Dev | Resolved | Add performance test for 100-page PDF chunking (<30s requirement, AC7). Story 1.5 prerequisite. Files: tests/integration/test_ingestion_integration.py. RESOLVED: test_chunking_performance_validation added (lines 236-281). |
| 2025-10-12 | 1.4 | 1 | QA | LOW | QA/Dev | In Progress | Manual QA checklist: Review chunks from Week 0 PDF (160 pages), verify no mid-sentence splits, document findings. AC5. Story 1.5 prerequisite. PARTIAL: Checklist created (docs/qa/manual-qa-checklist-story-1.4.md), execution pending. |
| 2025-10-12 | 1.4 | 1 | CodeQuality | LOW | Dev | Resolved | Add explanatory comment for async chunk_document pattern (async despite no await statements). Files: raglite/ingestion/pipeline.py:398. RESOLVED: Note section added to docstring (lines 434-437). |
| 2025-10-12 | 1.4 | 1 | Test | LOW | Dev | Open | Create or document sample PDF fixture (tests/fixtures/sample_financial_report.pdf) to enable integration test execution. Tests currently skip gracefully if fixture missing. OP-2 from second review. Files: tests/integration/test_ingestion_integration.py:188, 248 |
| 2025-10-13 | 1.5 | 1 | Optimization | MEDIUM | QA | Open | Remove duplicate ingest_pdf() call in test_embedding_generation_end_to_end() (test_ingestion_integration.py:351-356). Saves 30-60s per test run. AC7 efficiency. |
| 2025-10-13 | 1.5 | 1 | Enhancement | LOW | Dev | Open | Expose chunks in DocumentMetadata for better test validation. Add chunks: list[Chunk] field to enable direct embedding validation in integration tests. Phase 2+ consideration (may increase memory for large docs). AC7/AC8 validation. Files: raglite/shared/models.py:DocumentMetadata |
| 2025-10-13 | 1.5 | 1 | Documentation | LOW | Docs | Open | Standardize model name terminology in docstrings. Use "intfloat/e5-large-v2" consistently or add prominent note about "Fin-E5" marketing name. AC1 clarity. Files: raglite/ingestion/pipeline.py:47, 90 |
| 2025-10-13 | 1.5 | 1 | Enhancement | LOW | Performance | Open | Consider true async for embedding generation in Phase 4. Evaluate asyncio.to_thread() for concurrent processing. Defer to Phase 4 - current synchronous implementation sufficient for MVP. AC9 optimization. |
| 2025-10-18 | 2.1 | 2 | Research | CRITICAL | Dev/PM | Closed - Pivot | **[DECISION GATE] Story 2.1 Failed AC6 - PIVOT TO STORIES 2.2-2.4** - BM25 hybrid search achieved 56% accuracy (target: ≥70%). Root cause: Whitespace tokenization inadequate for financial documents. DECISION: Pivot to element-based chunking + retrieval optimization (Stories 2.2-2.4). Research complete: docs/epic-2-preparation/table-aware-rag-comprehensive-research-2025.md |
| 2025-10-18 | 2.2 | 2 | Enhancement | HIGH | Dev | Open | **Story 2.2: Element-Based Chunking Enhancement** - Replace fixed 512-token chunking with structure-aware boundaries (tables, sections) using Docling. Target: 56%→64-68% accuracy (+8-12pp). Effort: 1 week. Risk: LOW. Files: raglite/ingestion/pipeline.py, raglite/shared/models.py. See: docs/epic-2-preparation/implementation-plan-stories-2.2-2.4.md |
| 2025-10-18 | 2.3 | 2 | Enhancement | HIGH | Dev | Open | **Story 2.3: Query Preprocessing & Retrieval Optimization** - Query expansion (financial acronyms, numbers), metadata boosting, chunk bundling. Target: 68%→74-76% accuracy (+6-8pp). Effort: 2 weeks. Risk: MEDIUM. Depends on: Story 2.2 ≥65%. Files: raglite/retrieval/search.py, new raglite/retrieval/preprocessing.py |
| 2025-10-18 | 2.4 | 2 | Enhancement | MEDIUM | Dev | Open | **Story 2.4: Table-to-Text Summarization** - LLM (Claude 3.7 Sonnet) summaries of financial tables; dual chunk storage (raw + summary). Target: 74%→78-80% accuracy (+4-6pp). Effort: 3 weeks. Risk: MEDIUM. Cost: ~$0.60/doc. Depends on: Story 2.3 ≥74%. Files: raglite/ingestion/pipeline.py, new raglite/ingestion/table_summarization.py |

## Completed Items

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
|------|-------|------|------|----------|-------|--------|-------|
| 2025-10-18 | 2.1 | 2 | Bug | CRITICAL | Dev | Resolved | **Ingest Financial PDF Document** - Successfully ingested 160-page PDF (321 chunks, 1.0MB BM25 index). Fixed vector naming mismatches in ingestion (`pipeline.py:299`) and search (`search.py:138`). |
| 2025-10-18 | 2.1 | 2 | Test | CRITICAL | Dev | Resolved | **Execute Integration Test Suite** - Ran full suite. Result: 56% retrieval accuracy (FAILED AC6 ≥70% target). Attribution: 40% (vs 32% baseline). Performance: p95=90ms (PASS NFR13). |
| 2025-10-18 | 2.1 | 2 | Documentation | CRITICAL | Dev | Resolved | **Document Validation Results** - Added comprehensive "Validation Results" section with failure analysis, root cause (whitespace tokenization), and recommended next steps. |
| 2025-10-18 | 2.1 | 2 | Test | HIGH | Dev | Resolved | **Measure Performance Latency** - Validated p50=50ms, p95=90ms (well within <10,000ms NFR13 limit). |
| 2025-10-18 | 2.1 | 2 | Debug | HIGH | Dev | Resolved | **Debug BM25 Scores** - Identified Chunk 0 bias (confidentiality notice). Fixed by zeroing Chunk 0 scores. Tuned alpha from 0.7→0.5. Accuracy remained 56% (BM25 ineffective for this document). |
| 2025-10-18 | 2.1 | 2 | Research | HIGH | Dev | Resolved | **Research Alternative RAG Enhancement Approaches (Exa Deep Research)** - Comprehensive research completed using Exa MCP (259s, exa-research-pro). Investigated: element-based chunking, query preprocessing, table-to-text, cross-encoder reranking, VeritasFi, TableRAG. Result: Recommended 3-phase strategy (Stories 2.2-2.4). Files: docs/epic-2-preparation/table-aware-rag-comprehensive-research-2025.md, docs/epic-2-preparation/implementation-plan-stories-2.2-2.4.md |

---

**Last Updated:** 2025-10-18 (Story 2.1 Failed - Pivot to Stories 2.2-2.4)
**Total Open Items:** 11 (5 HIGH, 1 MEDIUM, 5 LOW)
**Total Resolved Items:** 10 (4 HIGH + 3 CRITICAL, 1 MEDIUM, 2 LOW)
**Total Closed Items:** 1 (1 CRITICAL - Story 2.1 pivot decision)
