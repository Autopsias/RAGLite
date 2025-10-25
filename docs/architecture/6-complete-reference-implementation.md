# 6. Complete Reference Implementation

## 6.1 MCP Server (raglite/main.py)

**This is the COMPLETE reference implementation.** AI agents should copy these patterns for all modules.

*[See architecture-v1.1-insert.md for the complete 250-line reference implementation]*

**Key file:** `raglite/main.py` (~200 lines)

**Demonstrates:**
- ✅ FastMCP server setup with lifespan management
- ✅ Pydantic model definitions for MCP tools
- ✅ Structured logging with context (`extra={}`)
- ✅ Error handling with specific exceptions
- ✅ Type hints for all functions
- ✅ Google-style docstrings
- ✅ Async patterns for I/O operations

**Pattern Summary:**
```python
# See architecture-v1.1-insert.md for complete implementation
```

---

## 6.2 Table-Aware Chunking Strategy (raglite/ingestion/)

**Context:** Phase 2A Course Correction (2025-10-25)

Fixed 512-token chunking splits financial tables across multiple chunks (average 8.6 chunks per table), destroying semantic coherence needed for accurate retrieval. Table-aware chunking preserves complete tables as semantic units.

**Key files:** `raglite/ingestion/pipeline.py`, `raglite/ingestion/contextual.py`

**Demonstrates:**
- ✅ Docling TableItem detection
- ✅ Preserving complete tables (<4096 tokens)
- ✅ Table splitting by rows with headers preserved (>4096 tokens)
- ✅ Hybrid approach: table-aware for tables, fixed 512-token for text

### Problem Statement

**Issue:**
Fixed 512-token chunking splits financial tables across multiple chunks, destroying semantic coherence:
- Average table fragmentation: **8.6 chunks per table**
- Total table chunks: 1,466 across 171 tables
- Impact: Retrieval cannot reconstruct table relationships from fragments
- Result: 52% accuracy plateau despite proper metadata extraction

**Example Fragmentation:**
```
Query: "What is the EBITDA margin for Portugal Cement in August 2025?"

Chunk 1: [Headers] "EBITDA | Margin | % | Department"
Chunk 2: [Row label] "Portugal Cement | August 2025"
Chunk 3: [Values] "23.4 | 18.7 | 12.3"
Chunk 4: [Units] "Million EUR | Percentage points"
```

LLM cannot synthesize answer from fragmented table context.

### Solution Approach

**Strategy:** Detect tables during ingestion and preserve them as complete semantic units.

**Decision Logic:**
1. **Tables <4096 tokens:** Keep entire table as single chunk
2. **Tables >4096 tokens:** Split by rows, preserve column headers in each chunk
3. **Non-table content:** Use fixed 512-token chunking (unchanged)

**Expected Outcomes:**
- Tables <4096 tokens: **1 chunk per table** (vs 8.6 currently)
- Large tables: **N chunks with headers preserved**
- Non-table text: **512-token fixed chunks** (unchanged)
- Total chunks: **1,592 → 200-250** (-87% reduction)
- Average chunks per table: **8.6 → 1.2** (-85% reduction)
- **Expected accuracy gain: +10-15pp** (from restored semantic coherence)

### Reference Implementation Pattern

#### Table-Aware Document Chunking

```python
from docling.datamodel.document import DoclingDocument
from docling.datamodel.base_models import ElementType, TableItem
from typing import List
import tiktoken

def chunk_document(doc: DoclingDocument, chunk_size: int = 512) -> List[Chunk]:
    """Chunk document with table-aware strategy.

    Preserves complete financial tables as semantic units while using
    fixed 512-token chunking for non-table content.

    Args:
        doc: Docling document with parsed elements
        chunk_size: Token size for non-table chunks (default: 512)

    Returns:
        List of chunks with preserved table coherence

    Raises:
        ChunkingError: If table processing fails
    """
    chunks = []
    tokenizer = tiktoken.get_encoding("cl100k_base")  # OpenAI tokenizer

    for element in doc.elements:
        if element.type == ElementType.TABLE:
            # Table-aware chunking: preserve semantic coherence
            table_tokens = count_tokens(element.text, tokenizer)

            if table_tokens < 4096:
                # Keep small/medium tables intact as single chunk
                chunks.append(create_chunk(
                    text=element.text,
                    metadata={
                        "chunk_type": "table",
                        "table_preserved": True,
                        "original_size": table_tokens
                    }
                ))
                logger.info(
                    "Table preserved intact",
                    extra={
                        "table_id": element.id,
                        "tokens": table_tokens,
                        "chunks": 1
                    }
                )
            else:
                # Split large tables by rows, preserve headers
                table_chunks = split_table_by_rows(
                    element,
                    max_tokens=4096,
                    tokenizer=tokenizer
                )
                chunks.extend(table_chunks)
                logger.info(
                    "Large table split by rows",
                    extra={
                        "table_id": element.id,
                        "tokens": table_tokens,
                        "chunks": len(table_chunks)
                    }
                )
        else:
            # Use fixed 512-token chunking for non-table content
            text_chunks = fixed_chunk(
                element.text,
                size=chunk_size,
                overlap=50,
                tokenizer=tokenizer
            )
            chunks.extend(text_chunks)

    return chunks


def split_table_by_rows(
    table: TableItem,
    max_tokens: int = 4096,
    tokenizer=None
) -> List[Chunk]:
    """Split large table by rows while preserving column headers.

    Ensures each chunk contains column headers + subset of rows,
    maintaining table structure for LLM interpretation.

    Args:
        table: Docling table element
        max_tokens: Maximum tokens per chunk (default: 4096)
        tokenizer: Token counter (default: OpenAI cl100k_base)

    Returns:
        List of table chunks with headers preserved in each

    Raises:
        TableSplitError: If header extraction fails
    """
    if tokenizer is None:
        tokenizer = tiktoken.get_encoding("cl100k_base")

    # Extract table structure
    header_row = table.rows[0]
    header_tokens = count_tokens(str(header_row), tokenizer)

    chunks = []
    current_chunk = [header_row]  # Always start with headers
    current_tokens = header_tokens

    for row in table.rows[1:]:
        row_text = str(row)
        row_tokens = count_tokens(row_text, tokenizer)

        if current_tokens + row_tokens < max_tokens:
            # Add row to current chunk
            current_chunk.append(row)
            current_tokens += row_tokens
        else:
            # Finalize current chunk
            if len(current_chunk) > 1:  # More than just header
                chunks.append(create_table_chunk(
                    rows=current_chunk,
                    table_metadata=table.metadata,
                    chunk_index=len(chunks)
                ))

            # Start new chunk with header + current row
            current_chunk = [header_row, row]
            current_tokens = header_tokens + row_tokens

    # Add final chunk
    if len(current_chunk) > 1:  # More than just header
        chunks.append(create_table_chunk(
            rows=current_chunk,
            table_metadata=table.metadata,
            chunk_index=len(chunks)
        ))

    return chunks


def create_table_chunk(
    rows: List,
    table_metadata: dict,
    chunk_index: int
) -> Chunk:
    """Create chunk from table rows with preserved structure.

    Args:
        rows: List of table rows (header + data rows)
        table_metadata: Original table metadata from Docling
        chunk_index: Index of this chunk within split table

    Returns:
        Chunk with table content and metadata
    """
    # Reconstruct table structure
    table_text = "\n".join(str(row) for row in rows)

    return Chunk(
        text=table_text,
        metadata={
            "chunk_type": "table_fragment",
            "table_id": table_metadata.get("table_id"),
            "chunk_index": chunk_index,
            "total_chunks": None,  # Set after all chunks created
            "has_headers": True,
            "row_count": len(rows) - 1,  # Exclude header
            **table_metadata  # Preserve original table metadata
        }
    )


def count_tokens(text: str, tokenizer) -> int:
    """Count tokens in text using specified tokenizer.

    Args:
        text: Input text
        tokenizer: Tokenizer instance (e.g., tiktoken)

    Returns:
        Token count
    """
    return len(tokenizer.encode(text))


def fixed_chunk(
    text: str,
    size: int = 512,
    overlap: int = 50,
    tokenizer=None
) -> List[Chunk]:
    """Split text into fixed-size chunks with overlap.

    Standard implementation for non-table content.

    Args:
        text: Input text to chunk
        size: Target chunk size in tokens
        overlap: Token overlap between chunks
        tokenizer: Token counter

    Returns:
        List of fixed-size chunks
    """
    if tokenizer is None:
        tokenizer = tiktoken.get_encoding("cl100k_base")

    tokens = tokenizer.encode(text)
    chunks = []
    stride = size - overlap

    for i in range(0, len(tokens), stride):
        chunk_tokens = tokens[i:i + size]
        chunk_text = tokenizer.decode(chunk_tokens)

        chunks.append(Chunk(
            text=chunk_text,
            metadata={
                "chunk_type": "text",
                "chunk_index": len(chunks),
                "token_count": len(chunk_tokens)
            }
        ))

    return chunks
```

### Implementation Files

**Primary:**
- `raglite/ingestion/pipeline.py` - Table detection and routing
- `raglite/ingestion/contextual.py` - Table-aware chunking logic

**Supporting:**
- `raglite/shared/models.py` - Chunk metadata schema
- `pyproject.toml` - tiktoken dependency (already added in Story 2.3)

### Trade-offs

**Pros:**
- ✅ Preserves semantic coherence of financial tables
- ✅ Expected +10-15pp accuracy improvement
- ✅ Reduces total chunks by 87% (1,592 → 200-250)
- ✅ Industry best practice (BlackRock, BNP Paribas, FinSage)
- ✅ Maintains LLM interpretability of tabular data

**Cons:**
- ⚠️ Variable chunk sizes (512 tokens to 4096 tokens)
- ⚠️ Slightly more complex ingestion logic (table detection)
- ⚠️ Re-ingestion required (delete + rebuild Qdrant collection)

**Decision Rationale:**
Semantic coherence is more important than uniform chunk size for financial document retrieval. LLMs require complete table context to answer queries like "What is the EBITDA margin for Portugal Cement in August 2025?"

### Expected Performance

**Chunk Metrics:**
- Small tables (<4096 tokens): 1 chunk per table
- Large tables (>4096 tokens): N chunks with headers preserved
- Non-table text: 512-token fixed chunks
- **Total chunk reduction: -87%** (1,592 → 200-250)

**Accuracy Impact:**
- **Expected gain: +10-15pp** (52% → 62-67%)
- Combined with other fixes (Stories 2.9-2.11): **65-75% total**
- Meets Phase 2A threshold: ≥70% accuracy

**Resource Impact:**
- Ingestion time: +5-10% (table detection overhead)
- Memory usage: Unchanged (tables streamed row-by-row if large)
- Storage: -87% (fewer chunks in Qdrant)
- Query latency: -10-15% (fewer chunks to process)

### Related Stories

- **Story 2.8:** Implements this table-aware chunking strategy (6-8 hours)
- **Story 2.3:** Original fixed 512-token chunking (causes fragmentation)
- **Story 2.4:** LLM metadata extraction (works well, enhanced by fewer chunks)
