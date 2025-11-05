# Epic 2 Implementation Plan: Stories 2.2-2.4
## Alternative RAG Enhancement Approaches (Post-BM25 Failure)

**Date:** 2025-10-18
**Context:** Story 2.1 (BM25 Hybrid Search) failed AC6 validation (56% accuracy vs ≥70% target)
**Research Source:** `table-aware-rag-comprehensive-research-2025.md` (Exa Deep Research)
**Decision:** Pivot from BM25 to element-based chunking + retrieval optimization

---

## Executive Summary

Based on comprehensive research of 2024-2025 financial RAG approaches, we've identified a **3-phase strategy** to improve from 56% → 70%+ accuracy:

1. **Story 2.2**: Element-Based Chunking (56% → 64-68%, 1 week, LOW risk)
2. **Story 2.3**: Query Preprocessing & Retrieval Optimization (68% → 74-76%, 2 weeks, MEDIUM risk)
3. **Story 2.4**: Table-to-Text Summarization (74% → 78-80%, 3 weeks, MEDIUM risk)

**Rationale:**
- Element-based chunking leverages Docling's existing table/section detection (minimal new code)
- Kim et al. (ICLR 2025) demonstrated 56% → 72% with retrieval optimization alone
- Table-to-text addresses our complex financial table challenge directly

**Technology Stack Compliance:**
- ✅ Uses existing Docling for element detection
- ✅ No new dependencies for Stories 2.2-2.3
- ⚠️ Story 2.4 requires LLM API calls (Claude 3.7 Sonnet, already in stack)

---

## Story 2.2: Element-Based Chunking Enhancement

### Overview
Replace fixed 512-token chunking with structure-aware boundaries (tables, sections, paragraphs) using Docling's existing element detection.

### Business Value
- **Accuracy Target**: 56% → 64-68% (+8-12 pp)
- **Research Evidence**: Jimeno Yepes et al. (2024) achieved +16 pp (ROUGE/BLEU/Q&A) with element chunking on SEC filings
- **Risk**: LOW - Docling already detects elements; just need to respect boundaries

### Acceptance Criteria

**AC1: Element-Aware Chunk Boundaries**
- Chunks MUST NOT split tables mid-row
- Chunks MUST NOT split section headers from content
- Tables <2,048 tokens stored as single chunk
- Sections >2,048 tokens split at paragraph boundaries

**AC2: Chunk Metadata Enhancement**
- Add `element_type` field: "table" | "section" | "paragraph" | "list"
- Add `section_title` field for context (e.g., "Revenue", "Operating Expenses")
- Preserve existing `page_number`, `chunk_index`, `source_document`

**AC3: Retrieval Accuracy Validation**
- Run 50-query ground truth test suite
- **CRITICAL**: Retrieval accuracy ≥64% (mandatory)
- Target: ≥68% (stretch goal)
- Attribution accuracy ≥45% (maintain baseline)

**AC4: Performance Compliance**
- Ingestion time ≤30s per 100 pages (same as baseline)
- p95 retrieval latency <10,000ms (NFR13)

**AC5: Backward Compatibility**
- Qdrant collection schema unchanged (named vectors: "text-dense")
- Existing queries work without modification

### Technical Specification

#### 1. Docling Element Detection
**Current State** (Story 1.4):
```python
# raglite/ingestion/pipeline.py:130-150
doc_result: ConversionResult = converter.convert(pdf_path)
# Docling detects elements but we flatten to text
text_content = doc_result.document.export_to_markdown()
```

**New Approach**:
```python
# Extract structured elements from Docling
from docling.datamodel.base_models import DoclingDocument, TableItem, SectionHeaderItem

def extract_elements(doc_result: ConversionResult) -> list[DocumentElement]:
    """Extract structured elements (tables, sections, paragraphs) from Docling."""
    elements = []
    for item in doc_result.document.iterate_items():
        if isinstance(item, TableItem):
            elements.append({
                "type": "table",
                "content": item.export_to_markdown(),
                "page_number": item.prov[0].page,  # First page of table
                "section_title": _get_parent_section(item)
            })
        elif isinstance(item, SectionHeaderItem):
            # Section headers group subsequent content
            elements.append({
                "type": "section_header",
                "content": item.text,
                "page_number": item.prov[0].page,
                "level": item.level
            })
        # ... handle paragraphs, lists
    return elements
```

#### 2. Smart Chunking Algorithm
**Strategy**:
- Tables <2,048 tokens → single chunk
- Sections → group header + content until token limit
- Respect element boundaries (no mid-table/mid-section splits)

**Pseudocode**:
```python
def chunk_elements(elements: list[DocumentElement], max_tokens: int = 512) -> list[Chunk]:
    chunks = []
    current_chunk = []
    current_tokens = 0
    current_section = None

    for elem in elements:
        elem_tokens = count_tokens(elem["content"])

        if elem["type"] == "table":
            # Tables are indivisible
            if elem_tokens > max_tokens:
                # Store large table as single chunk (up to 2,048 tokens)
                chunks.append(create_chunk(elem, section=current_section))
            else:
                # Small table - try to include with context
                if current_tokens + elem_tokens > max_tokens:
                    chunks.append(create_chunk(current_chunk, section=current_section))
                    current_chunk = [elem]
                    current_tokens = elem_tokens
                else:
                    current_chunk.append(elem)
                    current_tokens += elem_tokens

        elif elem["type"] == "section_header":
            # Flush previous section
            if current_chunk:
                chunks.append(create_chunk(current_chunk, section=current_section))
            current_section = elem["content"]
            current_chunk = [elem]
            current_tokens = elem_tokens

        else:  # paragraph, list
            if current_tokens + elem_tokens > max_tokens:
                chunks.append(create_chunk(current_chunk, section=current_section))
                current_chunk = [elem]
                current_tokens = elem_tokens
            else:
                current_chunk.append(elem)
                current_tokens += elem_tokens

    # Flush final chunk
    if current_chunk:
        chunks.append(create_chunk(current_chunk, section=current_section))

    return chunks
```

#### 3. Qdrant Schema Update
**Current**:
```python
payload = {
    "text": chunk.content,
    "page_number": chunk.page_number,
    "chunk_index": chunk.chunk_index,
    "word_count": word_count,
    "source_document": chunk.metadata.filename,
}
```

**Enhanced**:
```python
payload = {
    "text": chunk.content,
    "page_number": chunk.page_number,
    "chunk_index": chunk.chunk_index,
    "word_count": word_count,
    "source_document": chunk.metadata.filename,
    # NEW FIELDS
    "element_type": chunk.element_type,  # "table" | "section" | "paragraph"
    "section_title": chunk.section_title,  # e.g., "Revenue", "Cash Flow"
}
```

### Implementation Steps

**Step 1: Docling Element Extraction (2 days)**
- Modify `raglite/ingestion/pipeline.py:chunk_document()` to extract elements
- Add `DocumentElement` dataclass in `raglite/shared/models.py`
- Unit tests: `tests/unit/test_element_extraction.py`

**Step 2: Smart Chunking Logic (2 days)**
- Implement `chunk_elements()` algorithm
- Add `element_type` and `section_title` to `Chunk` model
- Unit tests: `tests/unit/test_element_chunking.py`

**Step 3: Qdrant Integration (1 day)**
- Update payload schema in `create_embeddings()`
- Verify Qdrant accepts new metadata fields
- Integration test: `tests/integration/test_element_metadata.py`

**Step 4: End-to-End Validation (1 day)**
- Re-ingest 160-page financial PDF
- Run 50-query ground truth test suite
- Measure accuracy improvement
- Document results in `docs/stories/story-2.2-element-chunking.md`

### Expected Outcomes

**Metrics (from Research)**:
- Page-level recall: 68% → 84% (+16 pp) [Jimeno Yepes et al.]
- ROUGE: 0.455 → 0.568 (+25%)
- BLEU: 0.250 → 0.452 (+81%)
- **End-to-end Q&A accuracy: 56% → 64-68%**

**Files Modified**:
- `raglite/ingestion/pipeline.py` (~80 lines added)
- `raglite/shared/models.py` (~30 lines added)
- `tests/unit/test_element_chunking.py` (new, ~150 lines)
- `tests/integration/test_element_metadata.py` (new, ~100 lines)

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Docling doesn't expose element API | Low | High | Fallback: parse Markdown output with regex (lower quality) |
| Large tables (>2,048 tokens) | Medium | Medium | Split at row boundaries as last resort |
| Section detection fails | Low | Low | Fallback to paragraph chunking |
| Accuracy <64% | Low | High | Proceed to Story 2.3 immediately |

---

## Story 2.3: Query Preprocessing & Retrieval Optimization

### Overview
Implement pre-retrieval query enhancement and post-retrieval optimization without fine-tuning embeddings.

### Business Value
- **Accuracy Target**: 68% → 74-76% (+6-8 pp)
- **Research Evidence**: Kim et al. (ICLR 2025) achieved 56% → 72% with retrieval optimization
- **Risk**: MEDIUM - requires domain-specific query patterns

### Acceptance Criteria

**AC1: Query Rewriting for Financial Terms**
- Expand financial acronyms: "EBITDA" → "EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)"
- Number normalization: "23.2" → "23.2 | twenty-three point two | 23.20"
- Unit expansion: "EUR/ton" → "EUR/ton | euros per ton"

**AC2: Metadata-Aware Filtering**
- Queries with numbers prioritize `element_type="table"` results
- Queries with "trend" | "change" | "growth" expand to adjacent time periods
- Section-aware boosting: "revenue" query boosts chunks with `section_title="Revenue"`

**AC3: Chunk Bundling for Context**
- Retrieve top-k candidates (e.g., top-20)
- Expand each candidate with ±1 adjacent chunk (same section)
- Re-rank expanded bundles
- Return top-5 after bundling

**AC4: Retrieval Accuracy Validation**
- Run 50-query ground truth test suite
- **CRITICAL**: Retrieval accuracy ≥74% (mandatory)
- Attribution accuracy ≥50% (target)
- p95 latency <10,000ms (NFR13)

**AC5: Backward Compatibility**
- Add `enable_preprocessing=True` flag to `hybrid_search()` / `search_documents()`
- Default behavior unchanged (preprocessing OFF)

### Technical Specification

#### 1. Query Rewriting Module
```python
# raglite/retrieval/preprocessing.py (new file)

FINANCIAL_ACRONYMS = {
    "EBITDA": "EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)",
    "ROI": "ROI (Return on Investment)",
    "CAGR": "CAGR (Compound Annual Growth Rate)",
    # ... 50+ financial terms from domain dictionary
}

def expand_query(query: str) -> str:
    """Expand financial acronyms and normalize numbers."""
    expanded = query

    # Expand acronyms
    for acronym, expansion in FINANCIAL_ACRONYMS.items():
        if acronym in expanded:
            expanded = expanded.replace(acronym, expansion)

    # Normalize numbers (23.2 → "23.2 | twenty-three point two")
    numbers = re.findall(r'\d+\.\d+|\d+', expanded)
    for num in numbers:
        num_text = num_to_words(num)  # "23.2" → "twenty-three point two"
        expanded += f" | {num_text}"

    return expanded
```

#### 2. Metadata-Aware Boosting
```python
# raglite/retrieval/search.py (modify)

async def search_documents_optimized(
    query: str,
    top_k: int = 5,
    enable_preprocessing: bool = True,
    filters: dict[str, str] | None = None,
) -> list[QueryResult]:
    """Enhanced search with query preprocessing and metadata boosting."""

    if enable_preprocessing:
        # Query expansion
        expanded_query = expand_query(query)

        # Metadata filter inference
        if has_numbers(query):
            # Prioritize tables for number-heavy queries
            filters = filters or {}
            filters["element_type"] = "table"

        query_embedding = await generate_query_embedding(expanded_query)
    else:
        query_embedding = await generate_query_embedding(query)

    # Retrieve wider candidate set (top-20 for bundling)
    candidates = qdrant.query_points(
        collection_name=settings.qdrant_collection_name,
        query=query_embedding,
        using="text-dense",
        limit=top_k * 4,  # Cast wider net
        query_filter=build_filter(filters),
        with_payload=True,
    )

    # Post-retrieval: Chunk bundling
    if enable_preprocessing:
        candidates = bundle_adjacent_chunks(candidates, tau_bundle=0.7)

    # Re-rank and return top-k
    return rerank_by_hybrid_score(candidates)[:top_k]
```

#### 3. Chunk Bundling Algorithm
```python
def bundle_adjacent_chunks(
    candidates: list[QueryResult],
    tau_bundle: float = 0.7
) -> list[QueryResult]:
    """Expand retrieval candidates with adjacent chunks for context."""
    bundled = []

    for candidate in candidates:
        # Find adjacent chunks (same document, section, chunk_index ±1)
        adjacent = find_adjacent_chunks(
            source_document=candidate.source_document,
            section_title=candidate.section_title,
            chunk_index=candidate.chunk_index,
            delta=1,  # ±1 chunk
        )

        # Combine text if semantic similarity > threshold
        if adjacent and similarity(candidate, adjacent[0]) > tau_bundle:
            bundled_text = f"{adjacent[0].text}\n\n{candidate.text}"
            bundled.append(QueryResult(
                score=candidate.score,
                text=bundled_text,
                source_document=candidate.source_document,
                page_number=candidate.page_number,
                chunk_index=candidate.chunk_index,
                word_count=len(bundled_text.split()),
            ))
        else:
            bundled.append(candidate)

    return bundled
```

### Implementation Steps

**Step 1: Query Preprocessing Module (2 days)**
- Create `raglite/retrieval/preprocessing.py`
- Implement `expand_query()` with financial acronym dictionary
- Unit tests: `tests/unit/test_query_preprocessing.py`

**Step 2: Metadata-Aware Search (2 days)**
- Modify `search_documents()` to add `enable_preprocessing` flag
- Implement filter inference (numbers → tables)
- Integration test: `tests/integration/test_metadata_filtering.py`

**Step 3: Chunk Bundling (3 days)**
- Implement `bundle_adjacent_chunks()` algorithm
- Add `find_adjacent_chunks()` Qdrant query helper
- Unit tests: `tests/unit/test_chunk_bundling.py`

**Step 4: End-to-End Validation (2 days)**
- Re-run 50-query ground truth suite with preprocessing enabled
- Measure accuracy improvement over Story 2.2 baseline
- Document results in `docs/stories/story-2.3-retrieval-optimization.md`

### Expected Outcomes

**Metrics (from Research)**:
- Retrieval recall: 68% → 83% (+15 pp) [Kim et al.]
- End-to-end Q&A accuracy: 68% → 74-76%
- Attribution accuracy: 45% → 50%

**Files Modified**:
- `raglite/retrieval/search.py` (~100 lines modified)
- `raglite/retrieval/preprocessing.py` (new, ~200 lines)
- `tests/unit/test_query_preprocessing.py` (new, ~120 lines)
- `tests/integration/test_metadata_filtering.py` (new, ~80 lines)

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Query expansion too verbose (>1,000 tokens) | Medium | Low | Truncate to 512 tokens max |
| Bundle similarity threshold too aggressive | Medium | Medium | A/B test tau ∈ [0.5, 0.7, 0.9] |
| Latency increase from bundling | Low | Low | Cache adjacent chunks; async fetch |
| Accuracy <74% | Low | Medium | Proceed to Story 2.4 |

---

## Story 2.4: Table-to-Text Summarization

### Overview
Generate LLM summaries of financial tables and embed both raw table + summary for improved semantic matching.

### Business Value
- **Accuracy Target**: 74% → 78-80% (+4-6 pp)
- **Research Evidence**: Min et al. (2024) achieved +9 pp RAG human score with LLM-based table-to-text
- **Risk**: MEDIUM - API costs, latency, data leakage concerns

### Acceptance Criteria

**AC1: Table Detection & Extraction**
- Identify all chunks with `element_type="table"`
- Extract raw Markdown table from Docling
- Parse into structured format (headers, rows, cells)

**AC2: LLM-Based Table Summarization**
- Use Claude 3.7 Sonnet (already in stack) to generate summaries
- Prompt: "Summarize this financial table in 2-3 sentences, focusing on key figures, trends, and insights."
- Summary length: 50-150 words
- Include table context: section title, page number

**AC3: Dual Embedding Storage**
- Store TWO chunks per table in Qdrant:
  1. Raw Markdown table (`element_type="table"`)
  2. LLM summary (`element_type="table_summary"`)
- Link chunks via `parent_chunk_id` field

**AC4: Retrieval Accuracy Validation**
- Run 50-query ground truth test suite
- **CRITICAL**: Retrieval accuracy ≥78% (mandatory)
- Attribution accuracy ≥55% (target)
- p95 latency <10,000ms (NFR13)

**AC5: Cost & Performance Monitoring**
- Log API token usage per table
- Track summarization latency (target: <5s per table)
- Budget: <$10 API cost for 160-page document (~30-40 tables)

### Technical Specification

#### 1. Table Detection
```python
# raglite/ingestion/pipeline.py (modify)

async def detect_tables(chunks: list[Chunk]) -> list[Chunk]:
    """Identify table chunks for summarization."""
    table_chunks = [c for c in chunks if c.element_type == "table"]
    logger.info(f"Detected {len(table_chunks)} table chunks for summarization")
    return table_chunks
```

#### 2. LLM Table Summarization
```python
# raglite/ingestion/table_summarization.py (new file)

from anthropic import Anthropic

client = Anthropic(api_key=settings.claude_api_key)

async def summarize_table(
    table_markdown: str,
    section_title: str,
    page_number: int,
) -> str:
    """Generate LLM summary of financial table.

    Args:
        table_markdown: Raw Markdown table from Docling
        section_title: Parent section (e.g., "Revenue by Segment")
        page_number: Source page for context

    Returns:
        2-3 sentence summary focusing on key figures and trends
    """
    prompt = f"""You are analyzing a financial table from page {page_number}, section "{section_title}".

Table (Markdown format):
{table_markdown}

Task: Summarize this table in 2-3 sentences (50-150 words). Focus on:
1. Key figures (exact numbers with units)
2. Trends (increases, decreases, comparisons)
3. Important insights (outliers, notable changes)

Be specific and quantitative. Include units (EUR, %, million, etc.).
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    summary = response.content[0].text

    logger.info(
        "Table summarized",
        extra={
            "page": page_number,
            "section": section_title,
            "tokens_in": len(table_markdown.split()),
            "tokens_out": len(summary.split()),
            "api_cost": estimate_cost(response.usage),
        }
    )

    return summary
```

#### 3. Dual Chunk Storage
```python
# raglite/ingestion/pipeline.py (modify)

async def create_table_chunks(table_chunk: Chunk) -> list[Chunk]:
    """Create dual chunks: raw table + LLM summary."""

    # 1. Original table chunk (Markdown)
    table_chunk.element_type = "table"

    # 2. Generate summary
    summary_text = await summarize_table(
        table_markdown=table_chunk.content,
        section_title=table_chunk.section_title,
        page_number=table_chunk.page_number,
    )

    # 3. Create summary chunk
    summary_chunk = Chunk(
        chunk_id=f"{table_chunk.chunk_id}_summary",
        content=summary_text,
        element_type="table_summary",
        section_title=table_chunk.section_title,
        page_number=table_chunk.page_number,
        chunk_index=table_chunk.chunk_index,
        parent_chunk_id=table_chunk.chunk_id,  # Link to parent
        metadata=table_chunk.metadata,
    )

    return [table_chunk, summary_chunk]
```

#### 4. Qdrant Schema Update
```python
payload = {
    "text": chunk.content,
    "page_number": chunk.page_number,
    "chunk_index": chunk.chunk_index,
    "word_count": word_count,
    "source_document": chunk.metadata.filename,
    "element_type": chunk.element_type,  # "table" | "table_summary" | ...
    "section_title": chunk.section_title,
    # NEW FIELD
    "parent_chunk_id": chunk.parent_chunk_id,  # Link summary → raw table
}
```

### Implementation Steps

**Step 1: Table Detection (1 day)**
- Modify `chunk_document()` to separate table chunks
- Add `parent_chunk_id` field to `Chunk` model
- Unit tests: `tests/unit/test_table_detection.py`

**Step 2: LLM Summarization (3 days)**
- Create `raglite/ingestion/table_summarization.py`
- Implement `summarize_table()` with Claude 3.7 Sonnet
- Add cost/latency monitoring
- Unit tests: `tests/unit/test_table_summarization.py` (mocked API)

**Step 3: Dual Chunk Ingestion (2 days)**
- Modify `create_embeddings()` to handle table + summary pairs
- Update Qdrant upsert to store both chunks
- Integration test: `tests/integration/test_dual_table_chunks.py`

**Step 4: End-to-End Validation (2 days)**
- Re-ingest 160-page financial PDF with table summarization
- Measure API costs and latency
- Run 50-query ground truth suite
- Document results in `docs/stories/story-2.4-table-summarization.md`

### Expected Outcomes

**Metrics (from Research)**:
- RAG human score: +9 pp [Min et al.]
- End-to-end Q&A accuracy: 74% → 78-80%
- Attribution accuracy: 50% → 55%

**Cost Estimates**:
- 160-page document: ~35 tables
- ~200 tokens/table (input) + 100 tokens/summary (output)
- Claude 3.7 Sonnet pricing: $3/M input, $15/M output
- **Total: ~$0.60 per document** (well within budget)

**Files Modified**:
- `raglite/ingestion/pipeline.py` (~60 lines modified)
- `raglite/ingestion/table_summarization.py` (new, ~150 lines)
- `raglite/shared/models.py` (~10 lines added for `parent_chunk_id`)
- `tests/unit/test_table_summarization.py` (new, ~120 lines)
- `tests/integration/test_dual_table_chunks.py` (new, ~100 lines)

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API rate limits | Low | Medium | Batch processing with exponential backoff |
| Summary quality varies | Medium | Medium | Validate summaries with manual QA (10 samples) |
| Data leakage (LLM training) | Low | High | Use Claude's data retention policy (30-day opt-out) |
| Latency >5s per table | Low | Low | Async processing; parallelize with asyncio.gather() |
| Accuracy <78% | Medium | High | Escalate to PM for Epic 2 strategy review |

---

## Summary: 3-Phase Roadmap

| Story | Approach | Effort | Risk | Gain | Cumulative Accuracy |
|-------|----------|--------|------|------|---------------------|
| **2.2** | Element-Based Chunking | 1 week | LOW | +8-12 pp | 64-68% |
| **2.3** | Query Preprocessing + Retrieval Optimization | 2 weeks | MEDIUM | +6-8 pp | 74-76% |
| **2.4** | Table-to-Text Summarization | 3 weeks | MEDIUM | +4-6 pp | 78-80% |

**Total Timeline**: 6 weeks (Phase 1 complete by Week 8)

**Decision Gates**:
1. After Story 2.2: If <65%, escalate to PM
2. After Story 2.3: If <74%, consider alternative approaches (VeritasFi, TableRAG)
3. After Story 2.4: If <78%, Epic 2 strategy review required

**Technology Stack Compliance**:
- ✅ All approaches use existing stack (Docling, Claude, Qdrant)
- ✅ No new dependencies for Stories 2.2-2.3
- ✅ Story 2.4 uses Claude API (already approved)

---

## Alternative: High-Risk, High-Reward (Defer)

If Stories 2.2-2.3 fail to reach 70%, consider:

### Story 2.X: VeritasFi-Inspired Multi-Stage Reranking
- **Approach**: Context-Aware Knowledge Curation + Two-Stage Reranking
- **Gain**: +20-40 pp (research shows 56% → 90%+)
- **Difficulty**: ★★★★☆
- **Risk**: HIGH - requires contrastive fine-tuning, multi-model pipeline
- **Effort**: 4-6 weeks
- **Defer**: Only if Phase 1-3 < 70%

---

## Next Steps

1. **User Decision**: Approve Story 2.2 for implementation (recommend YES)
2. **Story Creation**: Create `docs/stories/story-2.2-element-chunking.md` with full ACs
3. **Implementation**: Start Story 2.2 (target: 1 week)
4. **Validation**: Run 50-query test suite after each story
5. **Backlog Update**: Add Stories 2.3, 2.4 to `docs/backlog.md`
