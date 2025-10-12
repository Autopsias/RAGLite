# Technical Specification: Epic 1 - Foundation & Accurate Retrieval

**Epic:** Epic 1 - Foundation & Accurate Retrieval
**Phase:** Phase 1 (Weeks 1-5)
**Goal:** Working conversational financial Q&A system with 90%+ retrieval accuracy
**Status:** IN PROGRESS (21% complete - Stories 0.0, 0.1, 1.1 done)
**Version:** 1.0
**Date:** 2025-10-12
**Author:** Sarah (Product Owner)

---

## 1. Executive Summary

This technical specification provides detailed implementation guidance for Epic 1, covering all components, APIs, data models, testing requirements, and NFR validation criteria for the foundational RAG system.

**Target:** ~600-800 lines of Python code across 15 files
**Timeline:** 5 weeks (Week 0 spike complete + Weeks 1-5 implementation)
**Current Progress:** Week 0-1 (3/14 stories complete, 1 in progress)

---

## 2. Architecture Overview

### 2.1 Component Diagram

```
┌────────────────────────────────────────────────────────────┐
│  MCP Clients (Claude Code, Claude Desktop)                │
└────────────────────┬───────────────────────────────────────┘
                     │ Model Context Protocol
┌────────────────────▼───────────────────────────────────────┐
│  RAGLite Monolithic Server (raglite/main.py ~200 lines)   │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  MCP Tools Layer                                     │ │
│  │  • ingest_financial_document(doc_path) → Metadata   │ │
│  │  • query_financial_documents(query, top_k) → Results│ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Business Logic (Direct Function Calls)             │ │
│  │                                                      │ │
│  │  Ingestion Module (~150 lines)                      │ │
│  │  ├─ pipeline.py: Docling, chunking, embedding      │ │
│  │  └─ contextual.py: Contextual Retrieval (Week 3)   │ │
│  │                                                      │ │
│  │  Retrieval Module (~150 lines)                      │ │
│  │  ├─ search.py: Qdrant vector search                │ │
│  │  └─ attribution.py: Source citations               │ │
│  │                                                      │ │
│  │  Shared Module (~100 lines) ✅ DONE                │ │
│  │  ├─ config.py: Settings                            │ │
│  │  ├─ logging.py: Structured logging                 │ │
│  │  ├─ models.py: Pydantic data models                │ │
│  │  └─ clients.py: API client factories               │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────┬───────────────────────────────────────┘
                     │
┌────────────────────▼───────────────────────────────────────┐
│  Data Layer                                                │
│  ├─ Qdrant (Vector DB) → Docker container                 │
│  └─ Local Storage / S3 → Documents                        │
└────────────────────────────────────────────────────────────┘
```

### 2.2 Module Dependencies

```
main.py
  ├─> ingestion/pipeline.py
  │     ├─> ingestion/contextual.py (Week 3)
  │     ├─> shared/models.py ✅
  │     ├─> shared/clients.py ✅
  │     └─> shared/logging.py ✅
  ├─> retrieval/search.py
  │     ├─> shared/clients.py ✅
  │     └─> shared/models.py ✅
  ├─> retrieval/attribution.py
  │     └─> shared/models.py ✅
  ├─> shared/config.py ✅
  └─> shared/logging.py ✅
```

---

## 3. Data Models (Pydantic)

### 3.1 Core Models (raglite/shared/models.py) ✅ DONE

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DocumentMetadata(BaseModel):
    """Metadata for ingested document."""
    doc_id: str = Field(..., description="Unique document identifier (UUID)")
    filename: str = Field(..., description="Original filename")
    doc_type: str = Field(..., description="Document type (pdf, excel)")
    pages: int = Field(..., description="Number of pages")
    ingestion_timestamp: datetime = Field(..., description="When ingested")
    char_count: int = Field(..., description="Total characters")
    chunk_count: int = Field(..., description="Number of chunks created")
    table_count: int = Field(0, description="Number of tables extracted")

class ChunkMetadata(BaseModel):
    """Metadata for document chunk."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Parent document ID")
    source_document: str = Field(..., description="Document filename")
    page_number: int = Field(..., description="Page in source document")
    chunk_index: int = Field(..., description="Chunk position in document")
    word_count: int = Field(..., description="Words in chunk")
    text: str = Field(..., description="Chunk text content")

class QueryResult(BaseModel):
    """Single query result (chunk with relevance)."""
    score: float = Field(..., description="Similarity score (0-1, higher better)")
    text: str = Field(..., description="Chunk text content")
    source_document: str = Field(..., description="Document filename")
    page_number: int = Field(..., description="Page in source")
    chunk_index: int = Field(..., description="Chunk position")
    word_count: int = Field(..., description="Chunk size")

class QueryRequest(BaseModel):
    """MCP tool input for query."""
    query: str = Field(..., description="Natural language query")
    top_k: int = Field(5, description="Number of results (default 5)")

class QueryResponse(BaseModel):
    """MCP tool output for query."""
    results: List[QueryResult] = Field(..., description="Retrieved chunks")
    query: str = Field(..., description="Original query")
    retrieval_time_ms: float = Field(..., description="Query latency")
```

---

## 4. Component Specifications

### 4.1 MCP Server (raglite/main.py ~200 lines)

**Purpose:** FastMCP server exposing RAG tools via Model Context Protocol

**Key Functions:**
- Server initialization with lifespan management
- Tool definitions (`ingest_financial_document`, `query_financial_documents`)
- Error handling and logging
- MCP protocol compliance

**Implementation Pattern:**

```python
from fastmcp import FastMCP
from raglite.shared.config import settings
from raglite.shared.logging import logger
from raglite.shared.models import QueryRequest, QueryResponse, DocumentMetadata
from raglite.ingestion.pipeline import ingest_document
from raglite.retrieval.search import search_documents
from raglite.retrieval.attribution import generate_citations

mcp = FastMCP("RAGLite")

@mcp.tool()
async def ingest_financial_document(doc_path: str) -> DocumentMetadata:
    """Ingest financial PDF or Excel document.

    Args:
        doc_path: Path to document file

    Returns:
        DocumentMetadata with ingestion results

    Raises:
        DocumentProcessingError: If ingestion fails
    """
    logger.info("Ingesting document", extra={"path": doc_path})
    try:
        metadata = await ingest_document(doc_path)
        logger.info("Ingestion complete", extra={
            "doc_id": metadata.doc_id,
            "chunks": metadata.chunk_count
        })
        return metadata
    except Exception as e:
        logger.error("Ingestion failed", extra={"error": str(e)}, exc_info=True)
        raise DocumentProcessingError(f"Failed to ingest {doc_path}: {e}")

@mcp.tool()
async def query_financial_documents(request: QueryRequest) -> QueryResponse:
    """Query financial documents using natural language.

    Args:
        request: Query parameters (query, top_k)

    Returns:
        QueryResponse with retrieved chunks and metadata
    """
    logger.info("Query received", extra={"query": request.query, "top_k": request.top_k})
    try:
        results = await search_documents(request.query, request.top_k)
        cited_results = await generate_citations(results)

        return QueryResponse(
            results=cited_results,
            query=request.query,
            retrieval_time_ms=results.latency_ms
        )
    except Exception as e:
        logger.error("Query failed", extra={"error": str(e)}, exc_info=True)
        raise QueryError(f"Query failed: {e}")
```

**NFRs:**
- NFR30: MCP protocol compliance
- NFR31: Claude Desktop integration
- NFR32: Structured tool responses

**Testing:**
- Unit tests: Mock ingestion/retrieval functions
- Integration tests: End-to-end with real Qdrant
- MCP client tests: Validate tool discovery and execution

**Architecture References:**
- `arch/6-complete-reference-implementation.md:1-21` - Reference patterns
- `arch/2-executive-summary.md:46-54` - MCP Tools Layer

---

### 4.2 Ingestion Pipeline (raglite/ingestion/pipeline.py ~100 lines)

**Purpose:** Document processing (PDF/Excel), chunking, embedding generation

**Key Functions:**
- `ingest_document(doc_path: str) -> DocumentMetadata`
- `extract_pdf(doc_path: str) -> ExtractedContent`
- `extract_excel(doc_path: str) -> ExtractedContent`
- `chunk_document(content: ExtractedContent) -> List[ChunkMetadata]`
- `generate_embeddings(chunks: List[ChunkMetadata]) -> List[np.ndarray]`
- `store_in_qdrant(chunks, embeddings) -> None`

**Implementation Approach:**

```python
import asyncio
from pathlib import Path
from docling.document_converter import DocumentConverter
import openpyxl
import pandas as pd
from sentence_transformers import SentenceTransformer
from raglite.shared.config import settings
from raglite.shared.models import DocumentMetadata, ChunkMetadata
from raglite.shared.clients import get_qdrant_client, get_embedding_model
from raglite.shared.logging import logger

async def ingest_document(doc_path: str) -> DocumentMetadata:
    """Main ingestion pipeline.

    Args:
        doc_path: Path to PDF or Excel file

    Returns:
        DocumentMetadata with ingestion results

    Raises:
        DocumentProcessingError: If extraction/processing fails
    """
    path = Path(doc_path)

    # Validate file exists
    if not path.exists():
        raise DocumentProcessingError(f"File not found: {doc_path}")

    # Extract based on file type
    if path.suffix.lower() == ".pdf":
        content = await extract_pdf(doc_path)
    elif path.suffix.lower() in [".xlsx", ".xls"]:
        content = await extract_excel(doc_path)
    else:
        raise DocumentProcessingError(f"Unsupported file type: {path.suffix}")

    # Chunk document
    chunks = await chunk_document(content)
    logger.info(f"Created {len(chunks)} chunks", extra={"doc_path": doc_path})

    # Generate embeddings
    embeddings = await generate_embeddings(chunks)
    logger.info(f"Generated {len(embeddings)} embeddings")

    # Store in Qdrant
    await store_in_qdrant(chunks, embeddings)
    logger.info(f"Stored {len(chunks)} chunks in Qdrant")

    return DocumentMetadata(
        doc_id=content.doc_id,
        filename=path.name,
        doc_type=path.suffix[1:],
        pages=content.pages,
        ingestion_timestamp=datetime.now(),
        char_count=content.char_count,
        chunk_count=len(chunks),
        table_count=content.table_count
    )

async def extract_pdf(doc_path: str) -> ExtractedContent:
    """Extract text and tables from PDF using Docling.

    Args:
        doc_path: Path to PDF file

    Returns:
        ExtractedContent with text, tables, metadata

    Raises:
        DocumentProcessingError: If Docling extraction fails
    """
    try:
        converter = DocumentConverter()
        result = converter.convert(doc_path)

        # Extract full text
        full_text = result.document.export_to_markdown()

        # Extract page numbers (CRITICAL: Story 1.2 blocker fix)
        # TODO: Implement proper Docling page attribution API
        # Current: Estimate page boundaries (acceptable for MVP)
        pages = len(result.pages) if hasattr(result, 'pages') else 1

        # Extract tables
        tables = []
        for table in result.document.tables:
            tables.append({
                "data": table.export_to_dataframe(),
                "page": table.page_number if hasattr(table, 'page_number') else None
            })

        return ExtractedContent(
            doc_id=str(uuid.uuid4()),
            full_text=full_text,
            pages=pages,
            char_count=len(full_text),
            tables=tables,
            table_count=len(tables)
        )
    except Exception as e:
        logger.error(f"Docling extraction failed: {e}", exc_info=True)
        raise DocumentProcessingError(f"PDF extraction failed: {e}")

async def chunk_document(content: ExtractedContent) -> List[ChunkMetadata]:
    """Chunk document with semantic segmentation.

    Args:
        content: Extracted document content

    Returns:
        List of ChunkMetadata objects

    Strategy:
        - 500 words per chunk
        - 50 word overlap
        - Preserve page numbers (CRITICAL for NFR7)
        - Respect paragraph boundaries where possible
    """
    chunks = []
    words = content.full_text.split()
    chunk_size = 500
    overlap = 50

    estimated_chars_per_page = content.char_count / content.pages

    idx = 0
    chunk_index = 0
    while idx < len(words):
        chunk_words = words[idx:idx + chunk_size]
        chunk_text = " ".join(chunk_words)

        # Estimate page number based on character position
        char_pos = len(" ".join(words[:idx]))
        estimated_page = int(char_pos / estimated_chars_per_page) + 1
        estimated_page = min(estimated_page, content.pages)  # Cap at max pages

        chunks.append(ChunkMetadata(
            chunk_id=f"{content.doc_id}_{chunk_index}",
            doc_id=content.doc_id,
            source_document=content.filename,
            page_number=estimated_page,
            chunk_index=chunk_index,
            word_count=len(chunk_words),
            text=chunk_text
        ))

        idx += (chunk_size - overlap)
        chunk_index += 1

    return chunks
```

**NFRs:**
- NFR2: <5 min processing for 100-page PDFs (Week 0: 4.28 min ✅)
- NFR7: 95%+ source attribution accuracy (requires page numbers)
- NFR9: 95%+ table extraction accuracy (Docling: 97.9% ✅)
- NFR27: Data quality validation during ingestion

**Week 0 Blocker Resolution:**
- **Issue:** Page number extraction complexity (Docling API)
- **Temporary Solution:** Estimated page boundaries (acceptable for MVP)
- **Production Fix (Story 1.2):** Implement proper Docling page attribution API

**Testing:**
- Unit tests: Mock Docling, test chunking logic
- Integration tests: Real PDF ingestion end-to-end
- Accuracy tests: Validate page numbers against ground truth

**Architecture References:**
- `arch/3-repository-structure-monolithic.md:18-20` - Module structure
- `arch/5-technology-stack-definitive.md:5-8` - Docling, openpyxl, pandas, Fin-E5
- `docs/stories/1.2.pdf-document-ingestion.md` - Story 1.2 requirements

---

### 4.3 Contextual Retrieval (raglite/ingestion/contextual.py ~50 lines)

**Purpose:** LLM-generated context per chunk (Week 3 enhancement)

**Status:** PLANNED (Story 1.4, Week 3)

**Key Function:**
- `add_contextual_prefix(chunk: ChunkMetadata, full_doc: str) -> ChunkMetadata`

**Implementation Approach:**

```python
from anthropic import Anthropic
from raglite.shared.config import settings
from raglite.shared.models import ChunkMetadata
from raglite.shared.logging import logger

async def add_contextual_prefix(chunk: ChunkMetadata, full_doc: str) -> ChunkMetadata:
    """Add LLM-generated context to chunk for improved retrieval.

    Args:
        chunk: Original chunk metadata
        full_doc: Full document text for context

    Returns:
        ChunkMetadata with contextual prefix added

    Strategy:
        - Use Claude API to generate 1-2 sentence context
        - Context describes what the chunk is about in document context
        - Prepend context to chunk text before embedding
        - Improves retrieval accuracy from 90% → 98.1%
    """
    client = Anthropic(api_key=settings.claude_api_key)

    prompt = f"""
    Document context (first 2000 chars):
    {full_doc[:2000]}

    Chunk to contextualize:
    {chunk.text}

    Please provide 1-2 sentences describing what this chunk discusses
    within the context of the larger document. Focus on key topics and
    how this chunk relates to the overall document theme.
    """

    try:
        response = await client.messages.create(
            model="claude-3-haiku-20240307",  # Fast, cheap for context generation
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        context_prefix = response.content[0].text.strip()

        # Prepend context to chunk text
        chunk.text = f"{context_prefix}\n\n{chunk.text}"

        logger.info("Added contextual prefix", extra={"chunk_id": chunk.chunk_id})
        return chunk

    except Exception as e:
        logger.warning(f"Contextual Retrieval failed, using original chunk: {e}")
        return chunk  # Graceful degradation
```

**NFRs:**
- NFR6: 90%+ retrieval accuracy → 98.1% with Contextual Retrieval
- FR8: Contextual chunking for financial context

**Cost Analysis:**
- Claude Haiku: ~$0.25 per 1M input tokens, ~$1.25 per 1M output tokens
- 100 tokens per chunk × 300 chunks = 30,000 tokens = $0.0375 per 100-page PDF
- Acceptable for MVP

**Testing:**
- Unit tests: Mock Claude API
- Integration tests: Validate accuracy improvement (90% → 95%+)
- Cost tests: Measure token usage

**Architecture References:**
- `arch/4-research-findings-summary.md` - Contextual Retrieval research (98.1% accuracy, $0.82/100 docs)

---

### 4.4 Retrieval Search (raglite/retrieval/search.py ~50 lines)

**Purpose:** Qdrant vector similarity search

**Key Functions:**
- `search_documents(query: str, top_k: int) -> List[QueryResult]`
- `generate_query_embedding(query: str) -> np.ndarray`

**Implementation Approach:**

```python
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from raglite.shared.config import settings
from raglite.shared.models import QueryResult
from raglite.shared.clients import get_qdrant_client, get_embedding_model
from raglite.shared.logging import logger
import time

async def search_documents(query: str, top_k: int = 5) -> List[QueryResult]:
    """Search documents using vector similarity.

    Args:
        query: Natural language query
        top_k: Number of results to return

    Returns:
        List of QueryResult objects sorted by relevance

    Raises:
        QueryError: If search fails
    """
    start_time = time.time()

    try:
        # Generate query embedding
        embedding = await generate_query_embedding(query)
        logger.info("Query embedding generated", extra={"query": query[:50]})

        # Search Qdrant
        qdrant = get_qdrant_client()
        search_result = qdrant.query_points(
            collection_name=settings.qdrant_collection,
            query=embedding.tolist(),
            limit=top_k,
            with_payload=True
        )

        # Convert to QueryResult objects
        results = []
        for point in search_result.points:
            results.append(QueryResult(
                score=point.score,
                text=point.payload["text"],
                source_document=point.payload["source_document"],
                page_number=point.payload["page_number"],
                chunk_index=point.payload["chunk_index"],
                word_count=point.payload["word_count"]
            ))

        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"Search complete: {len(results)} results in {latency_ms:.2f}ms")

        return results

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise QueryError(f"Vector search failed: {e}")

async def generate_query_embedding(query: str) -> np.ndarray:
    """Generate embedding for query using Fin-E5 model.

    Args:
        query: Natural language query

    Returns:
        1024-dimensional embedding vector
    """
    model = get_embedding_model()  # sentence-transformers Fin-E5
    embedding = model.encode([query])[0]
    return embedding
```

**NFRs:**
- NFR5: Sub-5s retrieval performance (Week 0: 0.83s ✅)
- NFR13: <5s query response (p50), <15s (p95)

**Testing:**
- Unit tests: Mock Qdrant client
- Integration tests: Real Qdrant search
- Performance tests: Measure p50/p95 latency

**Architecture References:**
- `arch/7-data-layer.md` - Qdrant configuration
- `arch/5-technology-stack-definitive.md:10` - Qdrant 1.15.1

---

### 4.5 Source Attribution (raglite/retrieval/attribution.py ~50 lines)

**Purpose:** Generate source citations for retrieved chunks

**Key Function:**
- `generate_citations(results: List[QueryResult]) -> List[QueryResult]`

**Implementation Approach:**

```python
from raglite.shared.models import QueryResult
from raglite.shared.logging import logger

async def generate_citations(results: List[QueryResult]) -> List[QueryResult]:
    """Add formatted citations to query results.

    Args:
        results: List of QueryResult objects from search

    Returns:
        Same list with citation strings added to text

    Citation Format:
        "(Source: document.pdf, page 12, chunk 5)"
    """
    for result in results:
        citation = (
            f"(Source: {result.source_document}, "
            f"page {result.page_number}, "
            f"chunk {result.chunk_index})"
        )

        # Append citation to chunk text
        result.text = f"{result.text}\n\n{citation}"

        logger.debug("Citation added", extra={
            "doc": result.source_document,
            "page": result.page_number
        })

    return results
```

**NFRs:**
- NFR7: 95%+ source attribution accuracy
- NFR11: All retrieved information includes source citations
- NFR23: "How to verify" guidance via citations

**Testing:**
- Unit tests: Validate citation format
- Integration tests: End-to-end citation validation
- Accuracy tests: Verify citations point to correct document locations

**Architecture References:**
- `arch/6-complete-reference-implementation.md` - Citation patterns

---

### 4.6 Shared Utilities (raglite/shared/) ✅ DONE

**Status:** COMPLETE (Story 1.1, QA approved PASS)

**Components:**
- `config.py` (~30 lines): Pydantic Settings for environment variable loading
- `logging.py` (~20 lines): Structured JSON logging setup
- `models.py` (~30 lines): Pydantic data models (DocumentMetadata, QueryRequest, QueryResponse, QueryResult)
- `clients.py` (~20 lines): Qdrant client factory, embedding model loader

**Testing:** 14/14 tests passing (100% pass rate, Story 1.1 QA gate)

**Architecture References:**
- `docs/qa/gates/1.1-project-setup-development-environment.yml` - QA validation

---

## 5. API Contracts

### 5.1 MCP Tool: ingest_financial_document

**Input:**
```json
{
  "doc_path": "/path/to/document.pdf"
}
```

**Output:**
```json
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "Q3_Report.pdf",
  "doc_type": "pdf",
  "pages": 160,
  "ingestion_timestamp": "2025-10-12T14:30:00Z",
  "char_count": 1046722,
  "chunk_count": 348,
  "table_count": 157
}
```

**Errors:**
- `DocumentProcessingError`: File not found, extraction failed, storage failed

---

### 5.2 MCP Tool: query_financial_documents

**Input:**
```json
{
  "query": "What was the total revenue in Q3 2024?",
  "top_k": 5
}
```

**Output:**
```json
{
  "results": [
    {
      "score": 0.8405,
      "text": "Revenue for Q3 2024 was $45.2 million...\n\n(Source: Q3_Report.pdf, page 12, chunk 45)",
      "source_document": "Q3_Report.pdf",
      "page_number": 12,
      "chunk_index": 45,
      "word_count": 498
    }
  ],
  "query": "What was the total revenue in Q3 2024?",
  "retrieval_time_ms": 830.5
}
```

**Errors:**
- `QueryError`: Embedding generation failed, Qdrant search failed

---

## 6. NFR Validation Criteria

### NFR6: 90%+ Retrieval Accuracy

**Validation Method:**
- Ground truth test set (Story 1.12A, Week 1): 50+ Q&A pairs
- Daily accuracy tracking during Phase 1
- Week 5 final validation

**Measurement:**
```
Accuracy = (Queries returning correct information / Total queries) × 100%
Target: ≥90%
```

**Week 0 Baseline:** 60% (9/15 queries, 0.84 avg semantic score)

**Expected Trajectory:**
- Week 1: 70% (baseline with proper page extraction)
- Week 2: 75% (improved chunking)
- Week 3: 90% (Contextual Retrieval added)
- Week 5: 92% (final validation)

---

### NFR7: 95%+ Source Attribution Accuracy

**Validation Method:**
- Verify citations point to correct document and page
- Manual validation on 50+ test queries

**Measurement:**
```
Attribution Accuracy = (Correct citations / Total citations) × 100%
Target: ≥95%
```

**Dependencies:**
- Story 1.2: Page number extraction (BLOCKER - in progress)
- Story 1.4: Page preservation in chunking
- Story 1.8: Citation generation

---

### NFR13: <10s Query Response Time

**Validation Method:**
- Performance tests measuring p50 and p95 latency

**Measurement:**
```
p50 (median): ≤5 seconds
p95 (95th percentile): ≤10 seconds
```

**Week 0 Baseline:** 0.83s avg (EXCEEDS target)

---

## 7. Testing Strategy

### 7.1 Unit Tests (80% target coverage)

**Test Files:**
- `tests/test_ingestion.py` (~50 lines)
  - Test PDF extraction (mock Docling)
  - Test Excel extraction (mock openpyxl)
  - Test chunking logic
  - Test embedding generation (mock sentence-transformers)
- `tests/test_retrieval.py` (~50 lines)
  - Test vector search (mock Qdrant)
  - Test query embedding generation
  - Test result ranking
- `tests/test_attribution.py` (~30 lines)
  - Test citation formatting
  - Test multi-source citations

**Mocking Strategy:**
- Mock external APIs: Docling, sentence-transformers, Qdrant, Claude API
- Use pytest fixtures for test data
- Isolate units completely

**Tools:**
- pytest 8.4.2
- pytest-asyncio 1.2.0 (async test support)
- pytest-mock ≥3.12 (mocking)

---

### 7.2 Integration Tests (15% target coverage)

**Test Files:**
- `tests/test_integration_ingestion.py` (~50 lines)
  - End-to-end PDF ingestion with real Qdrant
  - Validate chunks stored correctly
  - Validate page numbers preserved
- `tests/test_integration_retrieval.py` (~50 lines)
  - End-to-end query with real Qdrant
  - Validate search results quality
  - Validate citations

**Setup:**
- Docker Compose with Qdrant test container
- Teardown: Clear collection after tests

**Tools:**
- pytest fixtures for Qdrant setup/teardown
- pytest-xdist ≥3.5 (parallel test execution)

---

### 7.3 Accuracy Tests (Ground Truth Validation)

**Test File:**
- `tests/ground_truth.py` (~200 lines, Story 1.12A)
  - 50+ Q&A pairs covering:
    - Cost analysis (40%)
    - Financial performance (40%)
    - Safety metrics, workforce, operating expenses (20%)
  - Difficulty distribution: 40% easy, 40% medium, 20% hard

**Validation Script:**
- `scripts/run-accuracy-tests.py`
  - Automated daily tracking
  - Generate accuracy trend report
  - Flag regressions

**Week 5 Final Validation:**
- Run full test set (50+ queries)
- Measure retrieval accuracy (target: 90%+)
- Measure attribution accuracy (target: 95%+)
- Generate decision gate report

**Architecture References:**
- `arch/testing-strategy.md` - Testing pyramid
- `PRD/epic-1:328-409` - Story 1.12A/1.12B requirements

---

## 8. Implementation Timeline

### Week 0: Integration Spike ✅ DONE

**Deliverables:**
- ✅ Spike code validated tech stack
- ✅ Week 0 Spike Report (60% accuracy, 0.84 semantic score → GO)
- ✅ Integration issues documented
- ✅ 15 ground truth Q&A pairs created

**Decision:** GO for Phase 1

---

### Week 1: Ingestion Pipeline

**Stories:**
- ✅ Story 1.1: Project Setup & Development Environment (DONE - PASS)
- 🔄 Story 1.2: PDF Document Ingestion with Docling (IN PROGRESS)
- 📋 Story 1.3: Excel Document Ingestion
- 📋 Story 1.12A: Ground Truth Test Set Creation (50+ queries)

**Deliverables:**
- `raglite/ingestion/pipeline.py` (PDF + Excel extraction, chunking)
- Resolved page number extraction blocker
- 50+ ground truth Q&A pairs

**Daily Tracking:** Run 10-15 test queries, track accuracy trend

---

### Week 2: Retrieval & Search

**Stories:**
- 📋 Story 1.5: Embedding Model Integration
- 📋 Story 1.6: Qdrant Vector Database Setup
- 📋 Story 1.7: Vector Similarity Search & Retrieval
- 📋 Story 1.8: Source Attribution & Citation Generation

**Deliverables:**
- `raglite/retrieval/search.py` (Qdrant vector search)
- `raglite/retrieval/attribution.py` (citation generation)

**Baseline Target:** 70%+ retrieval accuracy by end of Week 2

---

### Week 3: MCP Server & Integration

**Stories:**
- 📋 Story 1.4: Document Chunking & Semantic Segmentation (Contextual Retrieval)
- 📋 Story 1.9: MCP Server Foundation & Protocol Compliance
- 📋 Story 1.10: Natural Language Query Tool (MCP)
- 📋 Story 1.11: Enhanced Chunk Metadata & MCP Response Formatting

**Deliverables:**
- `raglite/ingestion/contextual.py` (Contextual Retrieval, 98.1% accuracy)
- `raglite/main.py` (FastMCP server with 2 tools)

**Accuracy Target:** 90%+ with Contextual Retrieval

---

### Week 4: Integration Testing

**Focus:**
- Daily accuracy checks (10-15 queries)
- Integration testing across all components
- Performance optimization if needed
- Bug fixes

**Accuracy Target:** Trending toward 90%+

---

### Week 5: Validation & Decision Gate

**Story:**
- 📋 Story 1.12B: Continuous Accuracy Tracking & Final Validation

**Activities:**
- Run full ground truth test set (50+ queries)
- Measure retrieval accuracy (target: 90%+)
- Measure attribution accuracy (target: 95%+)
- Performance testing (p50, p95 latency)
- User testing with real documents
- Document failure modes

**Deliverables:**
- Validation report with accuracy metrics
- Phase 2 decision recommendation:
  - ✅ **≥90% accuracy** → SKIP Phase 2 (GraphRAG), proceed to Phase 3
  - ⚠️ **80-89% accuracy** → ACCEPTABLE, proceed to Phase 3 (defer GraphRAG)
  - 🛑 **<80% accuracy** → HALT, analyze failures, consider Phase 2 (GraphRAG)

---

## 9. Dependencies & Blockers

### Current Blockers

**Story 1.2: Page Number Extraction (MEDIUM)**
- **Issue:** Docling page attribution API complexity (Week 0 workaround implemented)
- **Impact:** Blocks NFR7 validation (95%+ source attribution)
- **Mitigation:** Estimated page boundaries acceptable for MVP
- **Production Fix:** Implement proper Docling page attribution API (Story 1.2)
- **Estimated Effort:** 3-4 hours (in progress)

---

### External Dependencies

**Required Accounts/Access:**
- ✅ Claude API account (user has Claude Code subscription)
- ✅ Docker installed (Story 1.1 complete)
- ✅ Qdrant running locally (Docker Compose, Story 1.1 complete)

**Phase 1 Self-Contained:** No AWS account needed until Phase 4

---

## 10. Success Criteria

### Epic 1 Completion Criteria (End of Week 5)

**Must Meet (GO Criteria):**
1. ✅ 90%+ retrieval accuracy on 50+ query test set (NFR6)
2. ✅ 95%+ source attribution accuracy (NFR7)
3. ✅ <10s query response time (≥8/10 queries) (NFR13)
4. ✅ All answers include source citations (50/50)
5. ✅ Can ingest 5 financial PDFs successfully (≥4/5 succeed)

**Decision Gate:**
- **IF** all criteria met → **SKIP Phase 2** (GraphRAG), proceed to Phase 3 (Forecasting)
- **IF** 80-89% accuracy → **ACCEPTABLE**, proceed to Phase 3 (defer GraphRAG improvements)
- **IF** <80% accuracy AND multi-hop query failures → **REQUIRE Phase 2** (GraphRAG)

---

## 11. Risks & Mitigation

### Risk 1: Accuracy Below 90% (MEDIUM)

**Probability:** Medium (Week 0: 60%, but high semantic similarity)
**Impact:** HIGH (blocks Phase 3, triggers Phase 2 GraphRAG)

**Mitigation:**
1. **Week 3 Contextual Retrieval:** Add 8% accuracy boost (90% → 98.1%)
2. **Chunking Optimization:** Tune chunk size/overlap based on Week 2 results
3. **Query Preprocessing:** Add query normalization, synonym expansion
4. **Daily Tracking:** Catch accuracy regressions early

**Fallback:** If <80% by Week 5, activate Phase 2 (GraphRAG)

---

### Risk 2: Page Number Extraction Blocker (LOW - IN PROGRESS)

**Probability:** Low (diagnostic script available, workaround implemented)
**Impact:** MEDIUM (blocks NFR7, source attribution)

**Mitigation:**
1. **Story 1.2 Priority:** Resolve in Week 1
2. **Workaround Acceptable:** Estimated pages sufficient for MVP
3. **Hybrid Approach:** Docling (tables) + PyMuPDF (pages) if needed

**Status:** IN PROGRESS (diagnostic script: `scripts/test_page_extraction.py`)

---

### Risk 3: Performance Degradation (LOW)

**Probability:** Low (Week 0 baseline: 0.83s avg, EXCEEDS <10s target)
**Impact:** MEDIUM (blocks NFR13)

**Mitigation:**
1. **Qdrant HNSW Indexing:** Sub-5s retrieval guaranteed
2. **Batch Embedding:** Optimize embedding generation if needed
3. **Caching:** Add query embedding cache if performance issues

**Week 0 Baseline:** 0.83s (12x better than target)

---

## 12. References

### Architecture Documents
- `docs/architecture/1-introduction-vision.md` - Epic 1 vision and scope
- `docs/architecture/2-executive-summary.md` - Monolithic architecture
- `docs/architecture/3-repository-structure-monolithic.md` - File organization
- `docs/architecture/5-technology-stack-definitive.md` - Locked tech stack
- `docs/architecture/6-complete-reference-implementation.md` - Coding patterns
- `docs/architecture/7-data-layer.md` - Qdrant configuration
- `docs/architecture/8-phased-implementation-strategy-v11-simplified.md` - Timeline

### PRD Documents
- `docs/prd/requirements.md` - FR1-FR13, NFR1-NFR32
- `docs/prd/epic-1-foundation-accurate-retrieval.md` - Epic 1 stories

### Story Documents
- `docs/stories/0.1.week-0-integration-spike.md` - Week 0 validation
- `docs/stories/1.1.project-setup-development-environment.md` - Story 1.1 (DONE)
- `docs/stories/1.2.pdf-document-ingestion.md` - Story 1.2 (IN PROGRESS)

### QA Gates
- `docs/qa/gates/0.1-week-0-integration-spike.yml` - Week 0 QA (CONCERNS → GO)
- `docs/qa/gates/1.1-project-setup-development-environment.yml` - Story 1.1 QA (PASS)

---

## 13. Appendix

### A. Week 0 Spike Lessons Learned

**Technology Validation:**
- ✅ Docling: 97.9% table accuracy validated
- ✅ Fin-E5: 0.84 avg semantic score (high quality)
- ✅ Qdrant: 0.83s avg query latency (EXCEEDS target)
- ✅ FastMCP: 100% test success rate (3/3 queries)

**Challenges:**
- ⚠️ Page number extraction complexity (workaround implemented)
- ⚠️ Accuracy 60% vs 70% threshold (high semantic similarity suggests measurement artifact)
- ⚠️ Dependency version conflicts (resolved with pinning)
- ⚠️ Qdrant API deprecation (migrated to `query_points()`)

**Recommendations:**
1. Implement Contextual Retrieval (Week 3) for 90%+ accuracy
2. Resolve page extraction blocker (Story 1.2)
3. Expand ground truth test set to 50+ queries (Story 1.12A)
4. Track accuracy daily throughout Phase 1

---

### B. Code Quality Standards

**All Code Must Include:**
- ✅ Type hints (all functions, variables)
- ✅ Google-style docstrings (all public functions)
- ✅ Structured logging with context (`extra={}`)
- ✅ Error handling with specific exceptions
- ✅ Async/await for I/O operations

**Forbidden Patterns (Anti-Over-Engineering):**
- ❌ NO custom wrappers around SDKs
- ❌ NO abstract base classes for 600-line MVP
- ❌ NO configuration frameworks (use Pydantic Settings)
- ❌ NO custom decorators (except SDK-provided like `@mcp.tool()`)

**Reference:** `CLAUDE.md:95-165` - Anti-over-engineering rules

---

### C. Development Commands

**Setup:**
```bash
# Install dependencies (UV)
uv sync --frozen

# Start Qdrant
docker-compose up -d

# Initialize Qdrant collection
python scripts/init-qdrant.py

# Run tests
uv run pytest

# Run MCP server (local testing)
uv run python -m raglite.main
```

**Testing:**
```bash
# Unit tests only
uv run pytest raglite/tests/ -m unit

# Integration tests (requires Qdrant)
uv run pytest raglite/tests/ -m integration

# Accuracy tests (ground truth)
uv run python scripts/run-accuracy-tests.py

# With coverage
uv run pytest --cov=raglite --cov-report=html
```

---

**Document Version:** 1.0
**Created:** 2025-10-12
**Author:** Sarah (Product Owner)
**Next Update:** After Story 1.2 completion or Week 5 validation
