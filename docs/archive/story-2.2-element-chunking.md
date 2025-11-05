# Story 2.2: Element-Based Chunking Enhancement

**Status:** Ready for Implementation
**Epic:** 2 - Advanced RAG Enhancements
**Priority:** HIGH - Critical path to 70%+ accuracy after Story 2.1 failure
**Duration:** 5-7 days (1 week sprint)
**Assigned:** Dev Agent
**Prerequisites:** Story 2.1 validation complete ✅, Docling element detection API available ✅
**Dependencies:** None (first step in 3-phase strategy)
**Estimated Effort:** 4-5 days implementation + 1-2 days validation

---

## Story

**As a** RAG system processing financial documents,
**I want** structure-aware chunking that respects element boundaries (tables, sections, paragraphs),
**so that** chunks preserve semantic coherence and improve retrieval accuracy from 56% to 64-68%.

---

## Context

### Current State (Post-Story 2.1)
- ❌ Story 2.1 (BM25 Hybrid Search) failed AC6: 56% accuracy vs ≥70% target
- ✅ Root cause identified: BM25 whitespace tokenization inadequate for financial documents
- ✅ Research complete: Exa deep research identified element-based chunking as lowest-risk, highest-ROI alternative
- ✅ Retrieval Accuracy: 56.0% (28/50 queries pass) - BASELINE for Story 2.2
- ✅ Attribution Accuracy: 40.0% (20/50 queries pass)
- ✅ Performance: p50=50ms, p95=90ms (well within NFR13 <10,000ms)

### Problem with Current Fixed-Size Chunking

**Current Approach** (Story 1.4):
- Fixed 512-token chunks with 128-token overlap
- Splits documents at arbitrary token boundaries
- **Issues:**
  1. **Tables split mid-row:** Financial tables broken across chunks lose semantic coherence
  2. **Sections split mid-content:** Headers separated from their content
  3. **No element-type metadata:** Cannot prioritize tables for number-heavy queries

**Example Failure Case** (from ground truth):
```
Query: "What is the thermal energy specific consumption in Portugal Cement?"
Expected: Page 46 (table with specific numbers)
Current Chunks:
  - Chunk 92: [Header] "Energy Consumption"
  - Chunk 93: [Table Rows 1-3] "Portugal | 23.2 EUR/ton..."  ← CORRECT DATA
  - Chunk 94: [Table Rows 4-6] "Spain | 25.1 EUR/ton..."
Result: Semantic search retrieves Chunk 92 (header) instead of Chunk 93 (data)
Issue: Header chunk has high semantic similarity but no actual answer
```

### Research Foundation

**Based on:**
- Exa Deep Research: `docs/epic-2-preparation/table-aware-rag-comprehensive-research-2025.md`
- Implementation Plan: `docs/epic-2-preparation/implementation-plan-stories-2.2-2.4.md`

**Key Research Evidence** (Jimeno Yepes et al., 2024 - arXiv:2402.05131):
- **Element-type chunking vs fixed token chunking:**
  - Page-level recall: 68.1% → 84.4% (+16.3 pp)
  - ROUGE score: 0.455 → 0.568 (+24.8%)
  - BLEU score: 0.250 → 0.452 (+80.8%)
  - End-to-end Q&A accuracy (manual eval): 48.2% → 53.2% (+5.0 pp)
  - End-to-end Q&A accuracy (GPT-4 eval): 41.8% → 43.9% (+2.1 pp)
- **Combined chunking** (element-type + 128/256/512 token fallback) performs best
- **Memory requirement:** ~280 GB for 80 SEC 10-K filings (vision encoder overhead)

**Expected Outcome for Story 2.2:**
- Conservative estimate: 56% → 64% (+8 pp) based on element coherence alone
- Stretch goal: 56% → 68% (+12 pp) if table preservation yields high gains

---

## Acceptance Criteria

### AC1: Element-Aware Chunk Boundaries ⭐ CRITICAL
**Given** a PDF document with tables, sections, and paragraphs,
**When** the ingestion pipeline processes the document,
**Then:**
- ✅ Chunks MUST NOT split tables mid-row (tables are indivisible units)
- ✅ Chunks MUST NOT split section headers from their content (first paragraph)
- ✅ Tables <2,048 tokens MUST be stored as single chunk
- ✅ Tables >2,048 tokens MAY be split at row boundaries as last resort
- ✅ Sections >512 tokens MUST be split at paragraph boundaries (not mid-sentence)
- ✅ Chunk boundaries MUST respect Docling-detected element types

**Validation:**
- Unit test: `test_element_boundaries_respected()` with sample PDF
- Assertion: No chunks contain partial table rows or mid-section splits
- Manual QA: Review 10 table chunks from financial PDF

---

### AC2: Chunk Metadata Enhancement ⭐ CRITICAL
**Given** chunks created with element-aware boundaries,
**When** chunks are stored in Qdrant,
**Then:**
- ✅ Each chunk payload MUST include `element_type` field:
  - Values: `"table"`, `"section_header"`, `"paragraph"`, `"list"`, `"mixed"`
- ✅ Each chunk payload MUST include `section_title` field:
  - Example: `"Revenue by Segment"`, `"Operating Expenses"`, `"Cash Flow Statement"`
  - Value: Parent section header text (or `null` if no parent)
- ✅ Existing fields preserved: `page_number`, `chunk_index`, `source_document`, `word_count`
- ✅ Qdrant schema remains backward compatible (no breaking changes)

**Validation:**
- Integration test: `test_element_metadata_stored()` verifies all fields present
- Query test: Filter by `element_type="table"` returns only table chunks

---

### AC3: Retrieval Accuracy Validation ⭐ CRITICAL (DECISION GATE)
**Given** the 50-query ground truth test suite from Story 1.15B,
**When** hybrid search runs with element-based chunks,
**Then:**
- ✅ **MANDATORY:** Retrieval accuracy ≥64.0% (32/50 queries pass) - minimum viable improvement
- ✅ **TARGET:** Retrieval accuracy ≥68.0% (34/50 queries pass) - research-backed stretch goal
- ✅ Attribution accuracy ≥45.0% (maintain or improve over 40% baseline)
- ✅ No regression on performance: p95 latency <10,000ms (NFR13)

**Decision Gate:**
- If accuracy <64%: ESCALATE to PM for strategy review (approach may be insufficient)
- If accuracy ≥64% and <68%: PROCEED to Story 2.3 with caution flag
- If accuracy ≥68%: PROCEED to Story 2.3 with high confidence

**Validation:**
- Integration test: `tests/integration/test_hybrid_search_integration.py::test_hybrid_search_full_ground_truth`
- Report: Document results in "Validation Results" section below

---

### AC4: Performance & Scalability (NFR Compliance)
**Given** a 160-page financial document (Week 0 baseline),
**When** element-based chunking is applied,
**Then:**
- ✅ Ingestion time ≤30s per 100 pages (same as Story 1.4 baseline)
- ✅ Memory usage ≤4 GB during ingestion (no vision encoder overhead like Jimeno Yepes)
- ✅ Chunk count within 20% of baseline (321 chunks ± 64 chunks)
- ✅ p95 retrieval latency <10,000ms (NFR13 compliance)

**Validation:**
- Performance test: `test_element_chunking_performance()` measures ingestion time
- Memory profiling: Monitor RSS during `ingest_whole_pdf.py` execution

---

### AC5: Backward Compatibility
**Given** existing Qdrant collection schema and API contracts,
**When** element-based chunking is deployed,
**Then:**
- ✅ Qdrant collection schema remains compatible (additive changes only)
- ✅ `hybrid_search()` API signature unchanged (no breaking changes)
- ✅ Existing queries work without modification
- ✅ Old semantic-only search (`search_documents()`) continues to function

**Validation:**
- Regression test: Run Story 1.15B baseline tests against new chunks
- API compatibility test: Existing test suite passes without modification

---

## Technical Specification

### Overview: Element Detection → Smart Chunking → Enhanced Metadata

```
┌─────────────────────────────────────────────────────────────────────┐
│ Docling PDF Parsing                                                 │
│ ┌─────────┐  ┌─────────┐  ┌────────────┐  ┌────────┐               │
│ │ Table 1 │  │ Section │  │ Paragraph  │  │ Table 2│               │
│ │ (46 tok)│→ │ Header  │→ │ (120 tok)  │→ │ (800   │               │
│ │         │  │ (15 tok)│  │            │  │ tokens)│               │
│ └─────────┘  └─────────┘  └────────────┘  └────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Element Extraction (NEW)                                            │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │ elements = [                                                   │  │
│ │   {type: "table", content: "...", page: 46, section: "Rev"},  │  │
│ │   {type: "section_header", content: "Operating Exp", page: 47}│  │
│ │   {type: "paragraph", content: "...", page: 47},              │  │
│ │   {type: "table", content: "...", page: 48, section: "CF"}    │  │
│ │ ]                                                              │  │
│ └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Smart Chunking Algorithm (NEW)                                      │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │ Chunk 1: Table 1 (46 tok) ← single table chunk                │  │
│ │ Chunk 2: Section Header + Paragraph (135 tok) ← grouped       │  │
│ │ Chunk 3: Table 2 Part 1 (512 tok) ← split at row boundary    │  │
│ │ Chunk 4: Table 2 Part 2 (288 tok) ← remainder                 │  │
│ └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Qdrant Storage (ENHANCED)                                           │
│ ┌────────────────────────────────────────────────────────────────┐  │
│ │ {                                                              │  │
│ │   vector: {"text-dense": [1024-dim embedding]},               │  │
│ │   payload: {                                                   │  │
│ │     text: "...",                                               │  │
│ │     element_type: "table",           ← NEW                    │  │
│ │     section_title: "Revenue",        ← NEW                    │  │
│ │     page_number: 46,                                           │  │
│ │     chunk_index: 92,                                           │  │
│ │     source_document: "semapa_annual_report_2023.pdf"           │  │
│ │   }                                                            │  │
│ │ }                                                              │  │
│ └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 1. Data Model Changes

#### 1.1 New Models (`raglite/shared/models.py`)

```python
from enum import Enum
from typing import Optional

class ElementType(str, Enum):
    """Element types detected by Docling."""
    TABLE = "table"
    SECTION_HEADER = "section_header"
    PARAGRAPH = "paragraph"
    LIST = "list"
    FIGURE = "figure"
    MIXED = "mixed"  # Chunk contains multiple element types

@dataclass
class DocumentElement:
    """Structured element from Docling parsing.

    Represents a single document element (table, section, paragraph)
    with its content, type, and position metadata.
    """
    element_id: str  # Unique ID from Docling
    type: ElementType
    content: str  # Raw Markdown content
    page_number: int
    section_title: Optional[str] = None  # Parent section header
    token_count: int = 0  # Estimated tokens via tiktoken
    metadata: dict = field(default_factory=dict)

@dataclass
class Chunk:
    """Enhanced chunk with element-type metadata."""
    chunk_id: str
    content: str
    page_number: int
    chunk_index: int
    word_count: int
    embedding: Optional[list[float]] = None
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)

    # NEW FIELDS for Story 2.2
    element_type: ElementType = ElementType.MIXED  # Primary element type
    section_title: Optional[str] = None  # Parent section for context
    parent_chunk_id: Optional[str] = None  # For Story 2.4 (table summaries)
```

---

### 2. Element Extraction (`raglite/ingestion/pipeline.py`)

#### 2.1 Docling Element Extraction

**Current Implementation** (Story 1.4):
```python
# raglite/ingestion/pipeline.py:130-150
doc_result: ConversionResult = converter.convert(pdf_path)
text_content = doc_result.document.export_to_markdown()  # Flatten to text
```

**New Approach** (Story 2.2):
```python
# raglite/ingestion/pipeline.py (NEW FUNCTION)

from docling.datamodel.base_models import (
    DoclingDocument,
    TableItem,
    SectionHeaderItem,
    ParagraphItem,
    ListItem,
)
import tiktoken

encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")  # Token counting

def extract_elements(doc_result: ConversionResult) -> list[DocumentElement]:
    """Extract structured elements from Docling parsing result.

    Iterates through Docling document items and converts them to
    DocumentElement objects with type, content, and metadata.

    Args:
        doc_result: Docling conversion result with parsed document

    Returns:
        List of DocumentElement objects sorted by page/position

    Strategy:
        - Use doc_result.document.iterate_items() to traverse elements
        - Map Docling types to ElementType enum
        - Track parent section headers for context
        - Count tokens for chunking decisions

    Example:
        >>> doc_result = converter.convert("report.pdf")
        >>> elements = extract_elements(doc_result)
        >>> elements[0].type
        ElementType.TABLE
    """
    elements = []
    current_section = None

    for item in doc_result.document.iterate_items():
        # Determine element type
        if isinstance(item, TableItem):
            element_type = ElementType.TABLE
            content = item.export_to_markdown()
        elif isinstance(item, SectionHeaderItem):
            element_type = ElementType.SECTION_HEADER
            content = item.text
            current_section = content  # Update context
        elif isinstance(item, ParagraphItem):
            element_type = ElementType.PARAGRAPH
            content = item.text
        elif isinstance(item, ListItem):
            element_type = ElementType.LIST
            content = item.export_to_markdown()
        else:
            # Unknown element type - treat as paragraph
            element_type = ElementType.PARAGRAPH
            content = str(item)

        # Get page number (first page if spans multiple)
        page_number = item.prov[0].page if item.prov else 0

        # Count tokens for chunking decisions
        token_count = len(encoding.encode(content))

        elements.append(DocumentElement(
            element_id=item.id if hasattr(item, 'id') else f"elem_{len(elements)}",
            type=element_type,
            content=content,
            page_number=page_number,
            section_title=current_section,
            token_count=token_count,
            metadata={"docling_type": type(item).__name__}
        ))

    logger.info(
        f"Extracted {len(elements)} elements",
        extra={
            "tables": sum(1 for e in elements if e.type == ElementType.TABLE),
            "sections": sum(1 for e in elements if e.type == ElementType.SECTION_HEADER),
            "paragraphs": sum(1 for e in elements if e.type == ElementType.PARAGRAPH),
        }
    )

    return elements
```

---

### 3. Smart Chunking Algorithm

#### 3.1 Element-Aware Chunking Logic

```python
# raglite/ingestion/pipeline.py (NEW FUNCTION)

def chunk_elements(
    elements: list[DocumentElement],
    max_tokens: int = 512,
    overlap_tokens: int = 128,
) -> list[Chunk]:
    """Create chunks respecting element boundaries.

    Strategy:
        1. Tables <2,048 tokens → single chunk (indivisible)
        2. Tables >2,048 tokens → split at row boundaries (parse Markdown)
        3. Section headers → group with first paragraph
        4. Paragraphs → accumulate until max_tokens, no mid-sentence splits
        5. Preserve section_title context for all chunks

    Args:
        elements: List of DocumentElement from Docling
        max_tokens: Target chunk size (default: 512)
        overlap_tokens: Overlap between chunks (default: 128)

    Returns:
        List of Chunk objects with element-type metadata

    Example:
        >>> elements = extract_elements(doc_result)
        >>> chunks = chunk_elements(elements, max_tokens=512)
        >>> chunks[0].element_type
        ElementType.TABLE
    """
    chunks = []
    current_buffer = []
    current_tokens = 0
    current_section = None
    chunk_index = 0

    for elem in elements:
        # Update section context
        if elem.type == ElementType.SECTION_HEADER:
            current_section = elem.content

        # Strategy 1: Tables are indivisible (unless >2,048 tokens)
        if elem.type == ElementType.TABLE:
            if elem.token_count > 2048:
                # Large table - split at row boundaries
                table_chunks = _split_large_table(elem, max_tokens=512)
                for table_chunk in table_chunks:
                    chunks.append(_create_chunk(
                        content=table_chunk,
                        element_type=ElementType.TABLE,
                        section_title=current_section,
                        page_number=elem.page_number,
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
            else:
                # Small/medium table - single chunk
                if current_buffer:
                    # Flush buffer first
                    chunks.append(_create_chunk_from_buffer(
                        buffer=current_buffer,
                        section_title=current_section,
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
                    current_buffer = []
                    current_tokens = 0

                # Store table as standalone chunk
                chunks.append(_create_chunk(
                    content=elem.content,
                    element_type=ElementType.TABLE,
                    section_title=current_section,
                    page_number=elem.page_number,
                    chunk_index=chunk_index
                ))
                chunk_index += 1

        # Strategy 2: Section headers - group with first paragraph
        elif elem.type == ElementType.SECTION_HEADER:
            # Start new chunk with section header
            if current_buffer:
                chunks.append(_create_chunk_from_buffer(
                    buffer=current_buffer,
                    section_title=current_section,
                    chunk_index=chunk_index
                ))
                chunk_index += 1
            current_buffer = [elem]
            current_tokens = elem.token_count

        # Strategy 3: Paragraphs - accumulate until limit
        else:
            if current_tokens + elem.token_count > max_tokens:
                # Flush buffer
                chunks.append(_create_chunk_from_buffer(
                    buffer=current_buffer,
                    section_title=current_section,
                    chunk_index=chunk_index
                ))
                chunk_index += 1

                # Start new chunk with overlap
                overlap_buffer = _get_overlap(current_buffer, overlap_tokens)
                current_buffer = overlap_buffer + [elem]
                current_tokens = sum(e.token_count for e in current_buffer)
            else:
                current_buffer.append(elem)
                current_tokens += elem.token_count

    # Flush final buffer
    if current_buffer:
        chunks.append(_create_chunk_from_buffer(
            buffer=current_buffer,
            section_title=current_section,
            chunk_index=chunk_index
        ))

    logger.info(
        f"Created {len(chunks)} element-aware chunks",
        extra={
            "avg_tokens": sum(c.word_count for c in chunks) / len(chunks),
            "table_chunks": sum(1 for c in chunks if c.element_type == ElementType.TABLE),
        }
    )

    return chunks


def _split_large_table(elem: DocumentElement, max_tokens: int) -> list[str]:
    """Split table >2,048 tokens at row boundaries.

    Parses Markdown table, preserves header row, splits at row boundaries.
    """
    lines = elem.content.split('\n')
    header = lines[0:2]  # Header row + separator (|---|---|)
    rows = lines[2:]

    chunks = []
    current_chunk = header.copy()
    current_tokens = len(encoding.encode('\n'.join(current_chunk)))

    for row in rows:
        row_tokens = len(encoding.encode(row))
        if current_tokens + row_tokens > max_tokens:
            chunks.append('\n'.join(current_chunk))
            current_chunk = header.copy() + [row]
            current_tokens = len(encoding.encode('\n'.join(current_chunk)))
        else:
            current_chunk.append(row)
            current_tokens += row_tokens

    if len(current_chunk) > 2:  # More than just header
        chunks.append('\n'.join(current_chunk))

    logger.warning(
        f"Split large table into {len(chunks)} chunks",
        extra={"original_tokens": elem.token_count}
    )

    return chunks


def _create_chunk_from_buffer(
    buffer: list[DocumentElement],
    section_title: Optional[str],
    chunk_index: int
) -> Chunk:
    """Create Chunk from element buffer."""
    content = '\n\n'.join(e.content for e in buffer)

    # Determine primary element type
    element_counts = {}
    for elem in buffer:
        element_counts[elem.type] = element_counts.get(elem.type, 0) + 1

    # Primary type = most frequent (or MIXED if tied)
    if len(element_counts) == 1:
        element_type = list(element_counts.keys())[0]
    else:
        element_type = ElementType.MIXED

    # Page number = first element's page
    page_number = buffer[0].page_number

    return Chunk(
        chunk_id=f"chunk_{chunk_index}",
        content=content,
        page_number=page_number,
        chunk_index=chunk_index,
        word_count=len(content.split()),
        element_type=element_type,
        section_title=section_title,
    )


def _create_chunk(
    content: str,
    element_type: ElementType,
    section_title: Optional[str],
    page_number: int,
    chunk_index: int
) -> Chunk:
    """Create single Chunk from element."""
    return Chunk(
        chunk_id=f"chunk_{chunk_index}",
        content=content,
        page_number=page_number,
        chunk_index=chunk_index,
        word_count=len(content.split()),
        element_type=element_type,
        section_title=section_title,
    )


def _get_overlap(buffer: list[DocumentElement], overlap_tokens: int) -> list[DocumentElement]:
    """Get last N tokens from buffer for overlap."""
    overlap = []
    tokens = 0

    for elem in reversed(buffer):
        if tokens + elem.token_count <= overlap_tokens:
            overlap.insert(0, elem)
            tokens += elem.token_count
        else:
            break

    return overlap
```

---

### 4. Qdrant Integration

#### 4.1 Enhanced Payload Schema

```python
# raglite/ingestion/pipeline.py (MODIFY)

async def create_embeddings(chunks: list[Chunk]) -> list[PointStruct]:
    """Create Qdrant points with enhanced metadata.

    MODIFIED for Story 2.2: Add element_type and section_title fields.
    """
    model = get_embedding_model()
    points = []

    for chunk in chunks:
        # Generate embedding
        embedding = model.encode([chunk.content])[0].tolist()
        chunk.embedding = embedding

        # Create Qdrant point with ENHANCED metadata
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector={"text-dense": embedding},  # Named vector from Story 2.1
            payload={
                "chunk_id": chunk.chunk_id,
                "text": chunk.content,
                "word_count": chunk.word_count,
                "source_document": chunk.metadata.filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                # NEW FIELDS for Story 2.2
                "element_type": chunk.element_type.value,  # Enum → string
                "section_title": chunk.section_title,
            },
        )
        points.append(point)

    logger.info(
        f"Created {len(points)} embeddings with element metadata",
        extra={
            "table_chunks": sum(1 for p in points if p.payload["element_type"] == "table"),
        }
    )

    return points
```

---

### 5. Integration with Existing Pipeline

**Modify `chunk_document()` function:**

```python
# raglite/ingestion/pipeline.py (MODIFY)

async def chunk_document(doc_result: ConversionResult) -> list[Chunk]:
    """Chunk document using element-aware boundaries.

    MODIFIED for Story 2.2: Replace fixed-size chunking with element-aware.

    Strategy (NEW):
        1. Extract elements from Docling
        2. Apply smart chunking algorithm
        3. Return chunks with element metadata

    Old Strategy (Story 1.4):
        1. Flatten to Markdown text
        2. Split at fixed 512-token boundaries with 128-token overlap
    """
    logger.info("Chunking document with element-aware boundaries")

    # NEW: Extract structured elements
    elements = extract_elements(doc_result)

    # NEW: Apply smart chunking
    chunks = chunk_elements(
        elements=elements,
        max_tokens=512,
        overlap_tokens=128
    )

    logger.info(
        f"Document chunked: {len(chunks)} chunks",
        extra={
            "table_chunks": sum(1 for c in chunks if c.element_type == ElementType.TABLE),
            "section_chunks": sum(1 for c in chunks if c.element_type == ElementType.SECTION_HEADER),
            "avg_word_count": sum(c.word_count for c in chunks) / len(chunks),
        }
    )

    return chunks
```

---

## Test Plan

### Unit Tests

#### 1. `tests/unit/test_element_extraction.py` (NEW)

```python
"""Unit tests for Docling element extraction."""

import pytest
from raglite.ingestion.pipeline import extract_elements
from raglite.shared.models import ElementType

def test_extract_elements_from_sample_pdf():
    """Test element extraction detects tables, sections, paragraphs."""
    # Use sample fixture with known structure
    doc_result = converter.convert("tests/fixtures/sample_financial_report.pdf")
    elements = extract_elements(doc_result)

    # Validate element types detected
    assert any(e.type == ElementType.TABLE for e in elements), "No tables detected"
    assert any(e.type == ElementType.SECTION_HEADER for e in elements), "No sections detected"
    assert any(e.type == ElementType.PARAGRAPH for e in elements), "No paragraphs detected"

    # Validate metadata
    for elem in elements:
        assert elem.page_number > 0, "Invalid page number"
        assert elem.token_count > 0, "Invalid token count"
        assert elem.content, "Empty content"

def test_section_context_preserved():
    """Test section headers update current_section context."""
    doc_result = converter.convert("tests/fixtures/sample_financial_report.pdf")
    elements = extract_elements(doc_result)

    # Find section header
    section_idx = next(i for i, e in enumerate(elements) if e.type == ElementType.SECTION_HEADER)
    section_title = elements[section_idx].content

    # Subsequent elements should reference this section
    next_elem = elements[section_idx + 1]
    assert next_elem.section_title == section_title
```

#### 2. `tests/unit/test_element_chunking.py` (NEW)

```python
"""Unit tests for element-aware chunking algorithm."""

import pytest
from raglite.ingestion.pipeline import chunk_elements, _split_large_table
from raglite.shared.models import DocumentElement, ElementType

def test_table_not_split_under_2048_tokens():
    """Test tables <2,048 tokens stored as single chunk."""
    table_elem = DocumentElement(
        element_id="table_1",
        type=ElementType.TABLE,
        content="| Col1 | Col2 |\n|------|------|\n| A | B |",
        page_number=46,
        section_title="Revenue",
        token_count=50
    )

    chunks = chunk_elements([table_elem], max_tokens=512)

    assert len(chunks) == 1, "Table split incorrectly"
    assert chunks[0].element_type == ElementType.TABLE
    assert chunks[0].section_title == "Revenue"

def test_large_table_split_at_row_boundaries():
    """Test tables >2,048 tokens split at row boundaries."""
    large_table = "| Col1 | Col2 |\n|------|------|\n" + "\n".join(
        f"| Row{i} | Data{i} |" for i in range(100)
    )

    table_elem = DocumentElement(
        element_id="large_table",
        type=ElementType.TABLE,
        content=large_table,
        page_number=48,
        section_title="Cash Flow",
        token_count=2500  # Exceeds 2,048 limit
    )

    chunks = chunk_elements([table_elem], max_tokens=512)

    assert len(chunks) > 1, "Large table not split"
    for chunk in chunks:
        assert chunk.element_type == ElementType.TABLE
        assert "| Col1 | Col2 |" in chunk.content, "Header row missing"

def test_section_header_grouped_with_paragraph():
    """Test section headers grouped with first paragraph."""
    section = DocumentElement(
        element_id="sec_1",
        type=ElementType.SECTION_HEADER,
        content="Operating Expenses",
        page_number=50,
        token_count=5
    )
    paragraph = DocumentElement(
        element_id="para_1",
        type=ElementType.PARAGRAPH,
        content="Our operating expenses increased by 12% year-over-year...",
        page_number=50,
        section_title="Operating Expenses",
        token_count=100
    )

    chunks = chunk_elements([section, paragraph], max_tokens=512)

    assert len(chunks) == 1, "Section + paragraph split incorrectly"
    assert "Operating Expenses" in chunks[0].content
    assert "12% year-over-year" in chunks[0].content
```

---

### Integration Tests

#### 3. `tests/integration/test_element_metadata.py` (NEW)

```python
"""Integration tests for element metadata in Qdrant."""

import pytest
from raglite.ingestion.pipeline import ingest_pdf
from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings

@pytest.mark.asyncio
async def test_element_metadata_stored_in_qdrant():
    """Test element_type and section_title stored in Qdrant."""
    # Ingest sample PDF
    await ingest_pdf("tests/fixtures/sample_financial_report.pdf")

    # Query Qdrant for table chunks
    qdrant = get_qdrant_client()
    results = qdrant.scroll(
        collection_name=settings.qdrant_collection_name,
        scroll_filter=Filter(
            must=[FieldCondition(key="element_type", match=MatchValue(value="table"))]
        ),
        limit=10,
        with_payload=True,
    )

    # Validate metadata
    assert len(results[0]) > 0, "No table chunks found"
    for point in results[0]:
        assert point.payload["element_type"] == "table"
        assert "section_title" in point.payload
        assert point.payload["page_number"] > 0

@pytest.mark.asyncio
async def test_element_chunking_end_to_end():
    """Test end-to-end ingestion with element-aware chunking."""
    # Ingest full 160-page financial PDF
    metadata = await ingest_pdf(
        "tests/fixtures/semapa_annual_report_2023.pdf"
    )

    # Validate chunk counts (expect ±20% of baseline 321 chunks)
    qdrant = get_qdrant_client()
    count = qdrant.count(collection_name=settings.qdrant_collection_name)

    assert 257 <= count.count <= 385, f"Chunk count {count.count} outside expected range"

    # Validate element type distribution
    table_count = qdrant.count(
        collection_name=settings.qdrant_collection_name,
        count_filter=Filter(
            must=[FieldCondition(key="element_type", match=MatchValue(value="table"))]
        )
    )

    assert table_count.count > 0, "No table chunks stored"
    assert table_count.count < count.count * 0.3, "Too many table chunks (>30%)"
```

---

### Accuracy Validation

#### 4. `tests/integration/test_hybrid_search_integration.py` (RERUN)

```python
"""Rerun Story 2.1 integration tests with element-based chunks.

This test validates AC3 (Retrieval Accuracy) by running the full
50-query ground truth suite against element-aware chunks.

Expected Results:
    - Retrieval accuracy: 56% → 64-68% (AC3 target)
    - Attribution accuracy: 40% → 45%+ (AC3 target)
    - p95 latency: <10,000ms (NFR13)
"""

@pytest.mark.asyncio
async def test_hybrid_search_full_ground_truth():
    """Test hybrid search on full 50-query ground truth suite.

    This is the CRITICAL test for Story 2.2 AC3 success criteria:
    - Retrieval accuracy ≥64% (mandatory) or ≥68% (stretch)
    - Attribution accuracy ≥45%

    DECISION GATE:
        - <64%: ESCALATE to PM
        - 64-67%: PROCEED with caution
        - ≥68%: PROCEED with high confidence
    """
    # [Same test code as Story 2.1, lines 167-267]
    # Run against NEW element-aware chunks

    # ASSERTION updated for Story 2.2 targets
    assert metrics["retrieval_accuracy"] >= 64.0, (
        f"STORY 2.2 AC3 FAILED: Retrieval accuracy {metrics['retrieval_accuracy']:.1f}% "
        f"is below 64% minimum target. Element-based chunking insufficient."
    )
```

---

## Validation Checklist

### Before Merge (Developer)

- [ ] All unit tests pass (`pytest tests/unit/test_element_*.py -v`)
- [ ] All integration tests pass (`pytest tests/integration/test_element_metadata.py -v`)
- [ ] Accuracy test runs successfully (may fail AC3 - document results)
- [ ] No regressions in Story 1.15B baseline tests
- [ ] Code coverage ≥80% for new functions
- [ ] Type hints validated with `mypy raglite/ingestion/`
- [ ] Docstrings complete (Google style)
- [ ] Logging includes structured context (`extra={}`)

### Validation Results (Post-Deployment)

**To be completed during Story 2.2 execution:**

#### AC3: Retrieval Accuracy Results

| Metric | Baseline (Story 1.15B) | Target (AC3) | Actual | Pass/Fail |
|--------|------------------------|--------------|--------|-----------|
| Retrieval Accuracy | 56.0% (28/50) | ≥64.0% (32/50) | TBD | TBD |
| Retrieval Accuracy (Stretch) | 56.0% (28/50) | ≥68.0% (34/50) | TBD | TBD |
| Attribution Accuracy | 40.0% (20/50) | ≥45.0% (23/50) | TBD | TBD |
| p50 Latency | 50ms | <10,000ms | TBD | TBD |
| p95 Latency | 90ms | <10,000ms (NFR13) | TBD | TBD |

**Decision:**
- [ ] <64%: ESCALATE to PM for strategy review
- [ ] 64-67%: PROCEED to Story 2.3 with caution flag
- [ ] ≥68%: PROCEED to Story 2.3 with high confidence

#### AC4: Performance Results

| Metric | Baseline | Target | Actual | Pass/Fail |
|--------|----------|--------|--------|-----------|
| Ingestion Time (160 pages) | 960s (16 min) | ≤30s per 100 pages | TBD | TBD |
| Memory Usage | ~2 GB | ≤4 GB | TBD | TBD |
| Chunk Count | 321 chunks | 257-385 chunks (±20%) | TBD | TBD |

---

## Implementation Timeline

### Day 1-2: Data Models & Element Extraction
- [ ] Add `ElementType` enum and `DocumentElement` model
- [ ] Implement `extract_elements()` function
- [ ] Unit tests: `test_element_extraction.py`
- [ ] Manual QA: Review extracted elements from sample PDF

### Day 3-4: Smart Chunking Algorithm
- [ ] Implement `chunk_elements()` with table/section logic
- [ ] Implement `_split_large_table()` helper
- [ ] Unit tests: `test_element_chunking.py`
- [ ] Manual QA: Review 10 table chunks for boundary correctness

### Day 5: Qdrant Integration
- [ ] Update `Chunk` model with new fields
- [ ] Modify `create_embeddings()` for enhanced payload
- [ ] Integration tests: `test_element_metadata.py`

### Day 6: End-to-End Validation
- [ ] Re-ingest 160-page financial PDF with element chunking
- [ ] Run full 50-query ground truth test suite
- [ ] Measure accuracy, latency, performance
- [ ] Document results in "Validation Results" section

### Day 7: Documentation & Handoff
- [ ] Update Story 2.2 status based on AC3 results
- [ ] Document decision gate outcome
- [ ] Update backlog with next steps
- [ ] Code review and merge

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Docling API doesn't expose element types | Low | High | Fallback: Parse Markdown output with regex (lower quality) |
| Large tables (>2,048 tokens) split incorrectly | Medium | Medium | Implement robust Markdown table parser; validate with manual QA |
| Section detection fails for some documents | Low | Low | Fallback: Use paragraph chunking without section context |
| Accuracy <64% (AC3 failure) | Medium | High | Escalate to PM; consider Stories 2.3-2.4 in parallel |
| Chunk count increases >20% | Low | Low | Acceptable if accuracy improves; monitor Qdrant storage |
| Performance regression (ingestion time) | Low | Medium | Profile bottlenecks; optimize Docling element iteration |

---

## Success Metrics

### Mandatory (AC3 - Decision Gate)
- ✅ Retrieval accuracy ≥64.0% (minimum viable improvement)
- ✅ Attribution accuracy ≥45.0% (maintain or improve)
- ✅ p95 latency <10,000ms (NFR13 compliance)

### Stretch Goals
- 🎯 Retrieval accuracy ≥68.0% (research-backed target)
- 🎯 Table chunks show higher precision for number-heavy queries
- 🎯 Section context improves attribution accuracy

### Leading Indicators (Monitor During Implementation)
- Element extraction detects >30 tables in 160-page document
- Chunk count within 20% of baseline (257-385 chunks)
- No table chunks contain partial rows (manual QA validation)

---

## References

1. **Research Foundation:**
   - Exa Deep Research: `docs/epic-2-preparation/table-aware-rag-comprehensive-research-2025.md`
   - Implementation Plan: `docs/epic-2-preparation/implementation-plan-stories-2.2-2.4.md`

2. **Academic Research:**
   - Jimeno Yepes et al. (2024): "Financial Report Chunking" - arXiv:2402.05131
   - Element-type chunking: +16.3 pp page recall, +24.8% ROUGE, +80.8% BLEU

3. **Related Stories:**
   - Story 1.4: Contextual Chunking (baseline 512-token fixed chunks)
   - Story 1.15B: Ground Truth Validation (56% baseline accuracy)
   - Story 2.1: BM25 Hybrid Search (failed at 56%, pivot trigger)
   - Story 2.3: Query Preprocessing (next in 3-phase strategy)
   - Story 2.4: Table-to-Text Summarization (final phase)

---

## Appendix: Example Element Extraction

**Sample PDF Section:**
```
Page 46:
┌────────────────────────────────────────┐
│ Revenue by Segment                     │ ← Section Header
│                                        │
│ Our revenue breakdown by business      │ ← Paragraph
│ segment shows strong growth in...      │
│                                        │
│ | Segment    | 2023 (M€) | 2022 (M€) |│ ← Table
│ |------------|-----------|-----------|│
│ | Cement     | 1,234     | 1,120     |│
│ | Paper      | 567       | 543       |│
│ | Environment| 89        | 76        |│
└────────────────────────────────────────┘
```

**Extracted Elements:**
```python
[
    DocumentElement(
        element_id="elem_1",
        type=ElementType.SECTION_HEADER,
        content="Revenue by Segment",
        page_number=46,
        section_title=None,
        token_count=5
    ),
    DocumentElement(
        element_id="elem_2",
        type=ElementType.PARAGRAPH,
        content="Our revenue breakdown by business segment shows strong growth in...",
        page_number=46,
        section_title="Revenue by Segment",
        token_count=120
    ),
    DocumentElement(
        element_id="elem_3",
        type=ElementType.TABLE,
        content="| Segment | 2023 (M€) | 2022 (M€) |\n|---|---|---|\n| Cement | 1,234 | 1,120 |\n...",
        page_number=46,
        section_title="Revenue by Segment",
        token_count=95
    )
]
```

**Resulting Chunks:**
```python
[
    Chunk(
        chunk_id="chunk_92",
        content="Revenue by Segment\n\nOur revenue breakdown by business segment shows strong growth in...",
        element_type=ElementType.MIXED,  # Section header + paragraph
        section_title="Revenue by Segment",
        page_number=46,
        chunk_index=92
    ),
    Chunk(
        chunk_id="chunk_93",
        content="| Segment | 2023 (M€) | 2022 (M€) |\n|---|---|---|\n| Cement | 1,234 | 1,120 |\n...",
        element_type=ElementType.TABLE,
        section_title="Revenue by Segment",
        page_number=46,
        chunk_index=93
    )
]
```

**Query Result (After Story 2.2):**
```
Query: "What is the 2023 revenue for the Cement segment?"
Top-3 Results:
  1. Chunk 93 (score: 0.89) ← TABLE with exact data
  2. Chunk 92 (score: 0.76) ← Context paragraph
  3. Chunk 87 (score: 0.71) ← Related section

Result: ✅ IMPROVED - Table chunk ranked #1 (was #3 in Story 2.1)
```

---

**Story Status:** Ready for Implementation
**Next Action:** Assign to Dev Agent and begin Day 1 tasks

---

## Dev Agent Record

### Context Reference

- **Story Context XML:** `docs/stories/story-context-2.2.xml`
  - Generated: 2025-10-18
  - Version: 1.0
  - Contains: Acceptance criteria, documentation artifacts, code artifacts, dependencies, constraints, interfaces, and test ideas
  - Use this context file for comprehensive implementation guidance
