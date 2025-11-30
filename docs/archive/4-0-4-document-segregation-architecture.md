# Story 4.0.4: Document Segregation Architecture

Status: done

## Story

As an **architect**,
I want **clear documentation and validation of how documents are segregated in the vector and SQL databases**,
so that **the team understands document provenance, query scoping, and test isolation strategies**.

## Acceptance Criteria

1. **AC1: Architecture Document Created**
   - Create `docs/architecture/document-segregation-strategy.md` documenting:
     - How documents are identified (doc_id, filename, metadata schema)
     - How chunks are tagged with document provenance
     - Query scoping capabilities (filter by document, date range, source)
     - Multi-document search behavior (all docs vs specific doc)

2. **AC2: Qdrant Schema Validation**
   - Verify Qdrant collection schema includes document identification fields in payload
   - Document which metadata fields enable document-scoped queries
   - Validate chunks can be filtered by `source_document` or equivalent

3. **AC3: PostgreSQL Schema Validation**
   - Verify PostgreSQL table schema tracks document-level metadata
   - Document SQL table columns for document identification
   - Validate SQL queries can filter by document source

4. **AC4: Integration Test - Document Attribution**
   - Create test: Ingest 2 different PDFs, verify chunks have correct document attribution
   - Validate each chunk's metadata correctly identifies its source document
   - Test that query results include accurate source citations

5. **AC5: Test Isolation Strategy Documented**
   - Document how tests avoid data pollution (unique collections, cleanup fixtures)
   - Reference Story 4.0.5 environment separation strategy
   - Provide guidance for future test authors on maintaining isolation

## Tasks / Subtasks

- [x] **Task 1: Audit current document metadata implementation** (AC: #2, #3)
  - [x] Subtask 1.1: Review `raglite/shared/models.py` - DocumentMetadata, Chunk models
  - [x] Subtask 1.2: Review Qdrant storage in `raglite/retrieval/search.py` - payload structure
  - [x] Subtask 1.3: Review PostgreSQL storage in `raglite/ingestion/pipeline.py` - table schema
  - [x] Subtask 1.4: Document current implementation findings

- [x] **Task 2: Validate document-scoped query capability** (AC: #2, #3)
  - [x] Subtask 2.1: Test Qdrant filter by `source_document` field
  - [x] Subtask 2.2: Test PostgreSQL query with document filter
  - [x] Subtask 2.3: Document query scoping capabilities and limitations

- [x] **Task 3: Create integration test for document attribution** (AC: #4)
  - [x] Subtask 3.1: Create test file `tests/integration/test_document_segregation.py`
  - [x] Subtask 3.2: Test: Ingest PDF-A, verify chunks attributed to PDF-A
  - [x] Subtask 3.3: Test: Ingest PDF-B, verify chunks attributed to PDF-B
  - [x] Subtask 3.4: Test: Query and validate source citations are accurate

- [x] **Task 4: Create architecture document** (AC: #1)
  - [x] Subtask 4.1: Create `docs/architecture/document-segregation-strategy.md`
  - [x] Subtask 4.2: Document document identification approach
  - [x] Subtask 4.3: Document query scoping capabilities
  - [x] Subtask 4.4: Document multi-document search behavior
  - [x] Subtask 4.5: Include code examples and schema diagrams

- [x] **Task 5: Document test isolation strategy** (AC: #5)
  - [x] Subtask 5.1: Add test isolation section to architecture document
  - [x] Subtask 5.2: Reference Story 4.0.5 environment separation
  - [x] Subtask 5.3: Document test fixture best practices
  - [x] Subtask 5.4: Provide guidance for future test authors

## Dev Notes

### Context from Epic 3 Retrospective

**Issue 4 (ACTION ITEM 4):** Document Segregation Strategy Unclear

**Problem:** Unclear how multiple ingested documents are segregated vs mixed in vector/SQL databases.

**Questions Requiring Answers:**
1. Are chunks from different documents tagged with `doc_id` or `document_name`?
2. Can users query "only from Q3_2024_Report.pdf" (document-scoped queries)?
3. Do searches return chunks from all documents or can they be filtered by document?
4. How is document provenance tracked in metadata?
5. How do tests avoid data pollution when ingesting multiple test fixtures?

**Impact:**
- Affects Epic 4 data model design (forecasting may need document-level filtering)
- Affects test isolation (tests may pollute each other's data)
- Unclear if current architecture supports document-scoped retrieval

### Current Implementation Analysis (Pre-Task)

**From `raglite/shared/models.py` (lines 11-23):**

```python
class DocumentMetadata(BaseModel):
    filename: str = Field(..., description="Original document filename")
    doc_type: str = Field(..., description="Document type (PDF, Excel)")
    ingestion_timestamp: str = Field(..., description="ISO8601 timestamp of ingestion")
    page_count: int = Field(default=0, description="Number of pages/sheets in document")
    source_path: str = Field(default="", description="Original file path")
    chunk_count: int = Field(default=0, description="Number of chunks created from document")
```

**From `raglite/shared/models.py` (Chunk model, lines 138-141):**
```python
class Chunk(BaseModel):
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    metadata: DocumentMetadata = Field(..., description="Parent document metadata")
```

**Preliminary Finding:** Document provenance IS tracked via `Chunk.metadata.filename`. Full validation required in Tasks 1-2.

### Learnings from Previous Story (4-0-3)

**From Story 4-0-3: Fix MCP Ingestion Timeout (Status: done)**

- **Environment Separation (from Story 4.0.5):**
  - Test databases on different ports: Qdrant (6335), PostgreSQL (5433)
  - Production databases: Qdrant (6333), PostgreSQL (5432)
  - `configure_test_environment()` fixture ensures tests use test databases
  - Small test fixture: `tests/fixtures/sample-small-3-pages.pdf`

- **Key Patterns:**
  - Use `APP_ENV` environment variable for environment-based routing
  - Tests should use small fixtures for fast execution
  - Production database should not be affected by test runs

[Source: docs/sprint-artifacts/4-0-3-fix-mcp-ingestion-timeout.md#Dev-Notes]

### Architecture Patterns and Constraints

**Document Provenance Fields (from models.py analysis):**
- `DocumentMetadata.filename` - Original document filename (primary identifier)
- `DocumentMetadata.source_path` - Original file path
- `DocumentMetadata.doc_type` - Document type (PDF, Excel)
- `DocumentMetadata.ingestion_timestamp` - When document was ingested

**Query Result Attribution (from QueryResult model):**
- `QueryResult.source_document` - Source document filename for citations
- `QueryResult.page_number` - Page number where chunk appears

**Testing Standards:**
- Use small test fixture (`sample-small-3-pages.pdf`) for integration tests
- Use test database environment (port 6335/5433) for automated tests
- Tests should clean up or use isolated collections to avoid pollution

### Project Structure Notes

**Files to Investigate:**
- `raglite/shared/models.py` - Data models (already reviewed)
- `raglite/retrieval/search.py` - Qdrant search implementation
- `raglite/ingestion/pipeline.py` - Ingestion and Qdrant/PostgreSQL storage
- `raglite/shared/clients.py` - Qdrant client configuration

**Files to Create:**
- `docs/architecture/document-segregation-strategy.md` - Architecture document
- `tests/integration/test_document_segregation.py` - Integration tests

**Files to Reference:**
- `docs/sprint-artifacts/4-0-5-test-prod-database-separation.md` - Environment separation
- `tests/conftest.py` - Test environment setup patterns
- `tests/fixtures/sample-small-3-pages.pdf` - Small test fixture

### References

- [Source: docs/sprint-artifacts/epic-3-retrospective-2025-11-18.md#ACTION-ITEM-4] - Document segregation issue definition
- [Source: docs/sprint-artifacts/4-0-3-fix-mcp-ingestion-timeout.md] - Previous story learnings
- [Source: docs/architecture/7-data-layer.md] - Data layer architecture
- [Source: raglite/shared/models.py] - Current data models with document metadata

## Dev Agent Record

### Context Reference

- `docs/sprint-artifacts/4-0-4-document-segregation-architecture.context.xml`

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

**Task 1 Audit (2025-11-25):**
- Subtask 1.1: Reviewed `raglite/shared/models.py` - DocumentMetadata (lines 11-22), Chunk (lines 109-168), QueryResult (lines 182-198)
- Subtask 1.2: Reviewed `raglite/retrieval/search.py` - Qdrant filter support (lines 137-173), `source_document` field filtering
- Subtask 1.3: Reviewed `raglite/ingestion/storage_operations.py` - Qdrant payload (lines 246-271), PostgreSQL tables (lines 461-470, 621-629)
- Subtask 1.4: Documented findings below

**Key Findings:**
1. Primary identifier: `filename` from DocumentMetadata stored as `source_document` (Qdrant) / `document_id` (PostgreSQL)
2. Every chunk stores parent document via `chunk.metadata.filename` → Qdrant payload `source_document`
3. Qdrant: Full filter support via `filters={'source_document': 'filename.pdf'}`
4. PostgreSQL: Full filter support via `WHERE document_id = 'filename.pdf'`
5. Multi-document: Default returns ALL docs; filter scopes to specific document

**Task 2 Validation (2025-11-25):**
- Subtask 2.1: Qdrant filter by `source_document` - VERIFIED in `search.py` lines 162-168
  - `search_documents(query, filters={'source_document': 'filename.pdf'})` supported
  - Uses Qdrant FieldCondition with MatchValue for exact filename match
- Subtask 2.2: PostgreSQL filter by `document_id` - VERIFIED in `sql_table_search.py`
  - `SELECT * FROM financial_tables WHERE document_id = 'filename.pdf'` supported
  - `_ensure_attribution_columns()` guarantees document_id in SELECT clause (lines 28-92)
- Subtask 2.3: Query scoping capabilities documented below

**Query Scoping Capabilities:**
- Qdrant: 16 filterable fields (source_document + 15 rich metadata)
- PostgreSQL: document_id column for WHERE clause filtering
- Hybrid Search: SQL+Vector fusion preserves source attribution
- Limitations: No date range filtering on ingestion_timestamp (would require index)

**Task 3 Integration Tests (2025-11-25):**
- Created `tests/integration/test_document_segregation.py` (6 tests, all passing)
- TestDocumentSegregation class: 4 Qdrant tests (attribution, filter, citation, multi-doc)
- TestPostgreSQLDocumentSegregation class: 2 PostgreSQL tests (attribution, filter)
- All tests use `session_ingested_collection` fixture for existing test data
- Tests validate AC2, AC3, AC4 requirements

**Task 4 Architecture Document (2025-11-25):**
- Created `docs/architecture/document-segregation-strategy.md`
- Documented: Document identification (filename as primary ID)
- Documented: Chunk provenance tagging (metadata.filename → source_document)
- Documented: Query scoping capabilities (16 filterable fields)
- Documented: Multi-document search behavior (default vs filtered)
- Included: Code examples, table schemas, code references

**Task 5 Test Isolation Documentation (2025-11-25):**
- Expanded test isolation section in architecture document
- Referenced Story 4.0.5: Test vs Production Database Separation
- Documented: Environment separation (ports, collections, credentials)
- Documented: Fixture isolation patterns (session/module/function scoped)
- Documented: Test markers (@preserve_collection, @manages_collection_state)
- Documented: Best practices for future test authors (lazy imports, small fixtures, mocks)
- Documented: Data pollution prevention mechanisms

### Completion Notes List

- All 5 tasks completed successfully
- 6 new integration tests created, all passing
- Architecture document created with comprehensive documentation
- Test isolation strategy documented with best practices
- Full regression test suite passed (859 passed, 64 skipped)

### File List

- `tests/integration/test_document_segregation.py` - 6 integration tests (NEW)
- `docs/architecture/document-segregation-strategy.md` - Architecture document (NEW)
- `docs/sprint-artifacts/4-0-4-document-segregation-architecture.md` - Story file (UPDATED)

---

**Story Created:** 2025-11-25
**Created By:** Bob (Scrum Master)
**Epic:** Epic 4.0 (Prep Sprint)
**Priority:** MEDIUM-HIGH
**Estimated Effort:** 2-3 hours (investigation + documentation)

---

## Senior Developer Review (AI)

### Review Details

- **Reviewer:** Ricardo
- **Date:** 2025-11-25
- **Outcome:** ✅ **APPROVE**

### Summary

Story 4.0.4 successfully documents the document segregation architecture, validates both Qdrant and PostgreSQL schemas, implements comprehensive integration tests, and provides thorough test isolation guidance. All acceptance criteria are fully implemented with evidence-backed validation.

### Key Findings

**No HIGH or MEDIUM severity findings.** Implementation is complete and follows established patterns.

### Acceptance Criteria Coverage

| AC# | Description | Status | Evidence |
|-----|-------------|--------|----------|
| AC1 | Architecture Document Created | ✅ IMPLEMENTED | `docs/architecture/document-segregation-strategy.md` (378 lines) - Documents identification, provenance, query scoping, multi-document behavior |
| AC2 | Qdrant Schema Validation | ✅ IMPLEMENTED | `raglite/ingestion/storage_operations.py:189,250` - `source_document: chunk.metadata.filename`; `raglite/retrieval/search.py:143-163` - 16 filterable fields including `source_document` |
| AC3 | PostgreSQL Schema Validation | ✅ IMPLEMENTED | `raglite/retrieval/sql_table_search.py:28-92` - `_ensure_attribution_columns()` guarantees `document_id`; Architecture doc shows schema with `document_id VARCHAR NOT NULL` |
| AC4 | Integration Test - Document Attribution | ✅ IMPLEMENTED | `tests/integration/test_document_segregation.py` - 6 tests, all passing (33.19s runtime) |
| AC5 | Test Isolation Strategy Documented | ✅ IMPLEMENTED | Architecture doc section "Test Isolation Strategy" (lines 244-378) - References Story 4.0.5, documents fixture patterns, markers, best practices |

**Summary:** 5 of 5 acceptance criteria fully implemented

### Task Completion Validation

| Task | Marked As | Verified As | Evidence |
|------|-----------|-------------|----------|
| Task 1: Audit document metadata implementation | ✅ Complete | ✅ VERIFIED | `models.py:11-22` (DocumentMetadata), `models.py:109-168` (Chunk), `storage_operations.py:189,250` (Qdrant), `sql_table_search.py` (PostgreSQL) |
| Task 2: Validate document-scoped query capability | ✅ Complete | ✅ VERIFIED | `search.py:143-173` (Qdrant filter), `sql_table_search.py:351-356` (PostgreSQL WHERE clause), tests passing |
| Task 3: Create integration test for document attribution | ✅ Complete | ✅ VERIFIED | `tests/integration/test_document_segregation.py` - 6 tests (4 Qdrant, 2 PostgreSQL), all passing |
| Task 4: Create architecture document | ✅ Complete | ✅ VERIFIED | `docs/architecture/document-segregation-strategy.md` - Comprehensive (378 lines), covers all AC1 requirements |
| Task 5: Document test isolation strategy | ✅ Complete | ✅ VERIFIED | Architecture doc lines 244-378 - Environment separation, fixture patterns, markers, best practices |

**Summary:** 5 of 5 completed tasks verified, 0 questionable, 0 false completions

### Test Coverage and Gaps

- **Test File:** `tests/integration/test_document_segregation.py`
- **Test Count:** 6 integration tests
- **Test Results:** All passing (6 passed in 33.19s)
- **Test Quality:**
  - Proper pytest markers (`@pytest.mark.priority`, `@pytest.mark.asyncio`, `@pytest.mark.integration`)
  - Lazy imports for performance optimization
  - Uses session fixture for shared expensive resources
  - Appropriate `pytest.skip()` for unavailable resources
  - Clear docstrings with AC references
- **Coverage Gaps:** None identified for story scope

### Architectural Alignment

- **Tech Stack:** Uses approved dependencies only (qdrant-client, psycopg2-binary, pydantic)
- **Patterns:** Follows established singleton patterns for database clients
- **Environment Separation:** Correctly references Story 4.0.5 patterns (ports 6335/5433 for test)
- **Architecture Violations:** None

### Security Notes

- No security concerns identified
- Tests use parameterized queries (psycopg2 `%s` placeholders) - SQL injection safe
- Test code properly handles connection lifecycle

### Best-Practices and References

- [Qdrant Filtering Documentation](https://qdrant.tech/documentation/concepts/filtering/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [RAGLite Architecture Document](docs/architecture/document-segregation-strategy.md)

### Action Items

**Code Changes Required:**
- None required

**Advisory Notes:**
- Note: Consider adding date range filtering on `ingestion_timestamp` in future epics if needed (currently documented as limitation)
- Note: Bare `except Exception` in test skip logic (lines 294, 362) is acceptable but could be more specific in production code

---

### Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2025-11-25 | 1.0 | Story created |
| 2025-11-25 | 1.1 | All tasks completed, moved to review |
| 2025-11-25 | 1.2 | Senior Developer Review - APPROVED |
