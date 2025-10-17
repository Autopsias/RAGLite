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

## Completed Items

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
|------|-------|------|------|----------|-------|--------|-------|
| - | - | - | - | - | - | - | (No completed backlog items yet) |

---

**Last Updated:** 2025-10-13 (Story 1.5 Review)
**Total Open Items:** 6 (0 HIGH, 1 MEDIUM, 5 LOW)
**Total Resolved Items:** 4 (1 HIGH, 1 MEDIUM, 2 LOW)
**Total In Progress Items:** 1 (0 HIGH, 0 MEDIUM, 1 LOW)
