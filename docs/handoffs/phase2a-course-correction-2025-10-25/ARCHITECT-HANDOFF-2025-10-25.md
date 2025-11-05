# Architect Handoff - Phase 2A Course Correction

**Date:** 2025-10-25
**Prepared By:** Product Manager (John)
**Handoff To:** Architect
**Related:** Sprint Change Proposal (Phase 2A Course Correction)

---

## Executive Summary

**Context:** Phase 2A achieved 52% accuracy due to 4 critical root causes. Sprint Change Proposal approved to add Stories 2.8-2.11 before re-validation.

**Architect Responsibility:** Update architecture documentation to reflect table-aware chunking strategy and course correction decisions.

**Timeline:** 1-2 hours documentation work (can be done in parallel with dev implementation)

---

## Actions Required

### 🔴 CRITICAL - Architecture Documentation Update

**File:** `docs/architecture/6-complete-reference-implementation.md`

**Location:** After existing chunking implementation section (find section on chunking strategy)

---

### Change 1: Add Table-Aware Chunking Pattern

**Context:** Story 2.8 implements table-aware chunking to fix severe table fragmentation (8.6 chunks/table → 1.2 chunks/table).

**Documentation Required:**

Add new section **"Table-Aware Chunking Strategy"** with:

1. **Problem Statement**
   - Fixed 512-token chunking splits financial tables across multiple chunks
   - Average 8.6 chunks per table (1,466 table chunks across 171 tables)
   - Destroys semantic coherence needed for accurate retrieval

2. **Solution Approach**
   - Detect Docling TableItem objects during ingestion
   - Preserve complete tables as single chunks (<4096 tokens)
   - Split large tables by rows with headers preserved (>4096 tokens)
   - Use fixed chunking for non-table content (512 tokens)

3. **Reference Implementation Pattern**

```python
def chunk_document(doc: DoclingDocument, chunk_size: int = 512) -> list[Chunk]:
    """Chunk document with table-aware strategy.

    Args:
        doc: Docling document with elements
        chunk_size: Token size for non-table chunks

    Returns:
        List of chunks with preserved table coherence
    """
    chunks = []

    for element in doc.elements:
        if element.type == ElementType.TABLE:
            # Preserve tables as single chunks
            if token_count(element.text) < 4096:
                chunks.append(create_chunk(element))
            else:
                # Split large tables by rows, preserve headers
                chunks.extend(split_table_by_rows(element))
        else:
            # Use fixed chunking for non-table content
            chunks.extend(fixed_chunk(element.text, size=chunk_size))

    return chunks

def split_table_by_rows(table: TableItem, max_tokens: int = 4096) -> list[Chunk]:
    """Split large table by rows while preserving column headers.

    Args:
        table: Docling table element
        max_tokens: Maximum tokens per chunk

    Returns:
        List of table chunks with headers preserved
    """
    header_row = table.rows[0]
    chunks = []
    current_chunk = [header_row]
    current_tokens = token_count(header_row)

    for row in table.rows[1:]:
        row_tokens = token_count(row)

        if current_tokens + row_tokens < max_tokens:
            current_chunk.append(row)
            current_tokens += row_tokens
        else:
            # Finalize current chunk
            chunks.append(create_table_chunk(current_chunk, table.metadata))
            # Start new chunk with header + current row
            current_chunk = [header_row, row]
            current_tokens = token_count(header_row) + row_tokens

    # Add final chunk
    if len(current_chunk) > 1:  # More than just header
        chunks.append(create_table_chunk(current_chunk, table.metadata))

    return chunks
```

4. **Expected Outcomes**
   - Tables <4096 tokens: 1 chunk per table
   - Large tables: N chunks with headers preserved
   - Non-table text: 512-token fixed chunks
   - Average chunks per table: 8.6 → 1.2 (-85%)
   - Total chunks: 1,592 → 200-250 (-87%)

5. **Implementation Files**
   - `raglite/ingestion/pipeline.py` (table detection)
   - `raglite/ingestion/contextual.py` (table-aware chunking logic)

6. **Trade-offs**
   - **Pros:** Preserves semantic coherence, improves retrieval accuracy (+10-15pp expected)
   - **Cons:** Variable chunk sizes (512 tokens to 4096 tokens), slightly more complex ingestion logic
   - **Decision:** Semantic coherence > uniform chunk size for financial tables

---

### 🟡 MEDIUM - Architecture Decision Record

**Optional:** Create ADR (Architecture Decision Record) for table-aware chunking

**File:** `docs/architecture/decisions/ADR-003-table-aware-chunking.md` (if using ADR pattern)

**Template:**
```markdown
# ADR-003: Table-Aware Chunking Strategy

**Date:** 2025-10-25
**Status:** Accepted
**Context:** Phase 2A Course Correction

## Decision
Implement table-aware chunking to preserve complete tables as semantic units instead of splitting them across fixed 512-token chunks.

## Context
Fixed 512-token chunking resulted in severe table fragmentation (8.6 chunks per table average), destroying semantic coherence and contributing to 52% retrieval accuracy failure.

## Considered Alternatives
1. Keep fixed 512-token chunking (rejected - proven to fragment tables)
2. Increase chunk size to 4096 tokens (rejected - too coarse for non-table content)
3. Table-aware hybrid chunking (SELECTED)

## Consequences
- **Positive:** Semantic coherence preserved, expected +10-15pp accuracy gain
- **Negative:** Variable chunk sizes, slightly more complex ingestion
- **Risk:** LOW - standard practice in document processing
```

---

### 🟢 LOW - Update Architecture Diagrams (Optional)

**If architecture diagrams exist:** Update ingestion pipeline diagram to show table detection → table-aware chunking decision point

**Files (if exist):**
- `docs/architecture/diagrams/ingestion-pipeline.png`
- `docs/architecture/diagrams/chunking-strategy.png`

**Note:** Only if diagrams currently exist. Don't create new diagrams unless needed.

---

## Reference Materials

**Sprint Change Proposal:** Section 4.B - Architecture Documentation Changes
**Root Cause Analysis:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/phase2a-deep-dive-analysis.md` - Root Cause #1
**Story:** Story 2.8 (to be created by SM) - Implementation details
**Existing Architecture:** `docs/architecture/6-complete-reference-implementation.md` - Current chunking patterns

---

## Validation Criteria

**Documentation Quality:**
- ✅ Table-aware chunking pattern clearly documented
- ✅ Code examples provided (copy-paste ready)
- ✅ Expected outcomes quantified (8.6 → 1.2 chunks/table)
- ✅ Trade-offs explicitly stated
- ✅ Links to implementation files

**Completeness:**
- ✅ Problem statement explains WHY change was needed
- ✅ Solution approach explains HOW it works
- ✅ Reference implementation shows WHAT to code
- ✅ Expected outcomes show IMPACT

---

## Timeline

**Priority:** MEDIUM (not blocking dev work, but should complete before Story 2.8 finishes)

**Estimated Effort:** 1-2 hours

**Sequence:**
1. Review existing chunking documentation (30 min)
2. Add table-aware chunking section (1 hour)
3. Optional: Create ADR (30 min)
4. Optional: Update diagrams if they exist (30 min)

---

## Questions / Clarifications

**For Architect:**
- Do we follow ADR pattern for architecture decisions in this project?
- Are there existing architecture diagrams that need updating?
- Should this be added to a specific section or as a new subsection?

**Contact:** Product Manager (John) via Slack or email

---

**Handoff Status:** ✅ READY FOR ARCHITECT EXECUTION

**Next Steps:**
1. Architect reviews existing architecture documentation
2. Architect adds table-aware chunking pattern section
3. Architect optionally creates ADR-003
4. Architect commits documentation updates

---

**Prepared:** 2025-10-25
**PM Signature:** John (Product Manager)
