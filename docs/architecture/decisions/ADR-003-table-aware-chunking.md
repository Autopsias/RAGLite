# ADR-003: Table-Aware Chunking Strategy

**Date:** 2025-10-25
**Status:** ✅ Accepted
**Context:** Phase 2A Course Correction
**Related Stories:** Story 2.8 (Implementation), Story 2.5 (Validation Failure)

---

## Decision

Implement **table-aware chunking** to preserve complete financial tables as semantic units instead of splitting them across fixed 512-token chunks.

---

## Context

### Problem Discovery

Phase 2A implementation achieved **52% accuracy**, failing to meet the ≥70% threshold despite implementing:
- Fixed 512-token chunking with 50-token overlap
- LLM metadata extraction (94-99% success rate)
- PostgreSQL structured storage
- Multi-index search orchestration

Deep-dive analysis identified **severe table fragmentation** as the primary root cause:
- Average **8.6 chunks per table** (1,466 table chunks across 171 tables)
- Financial tables split mid-row, mid-column, destroying semantic coherence
- LLM cannot reconstruct table relationships from fragments
- Expected +26-30pp improvement (68-72% accuracy) not realized

### Research Evidence

Table-aware chunking is production-proven in financial RAG systems:
- **BlackRock/NVIDIA HybridRAG:** Table preservation + graph structure (96% answer relevancy)
- **BNP Paribas GraphRAG:** Document-level chunking prevents table splits (80% token savings, 6% hallucination reduction)
- **FinSage (SingHealth):** Table-aware chunking standard practice

**Academic Validation:**
- Yepes et al. (2024): Element-based chunking (keywords/sentences) = **46.10% accuracy**
- Yepes et al. (2024): Fixed 512-token chunking = **68.09% accuracy**
- We built the 46% solution (element-aware) → pivoted to 68% solution (fixed) → now fixing table fragmentation

---

## Considered Alternatives

### Alternative 1: Keep Fixed 512-Token Chunking
**Rejected** - Proven to fragment tables (8.6 chunks/table), causes 52% accuracy plateau

### Alternative 2: Increase Chunk Size to 4096 Tokens Globally
**Rejected** - Too coarse for non-table content, loses precision for narrative text

### Alternative 3: Table-Aware Hybrid Chunking
**SELECTED** - Best of both worlds:
- Tables: Preserved as semantic units (<4096 tokens) or split by rows (>4096 tokens)
- Text: Fixed 512-token chunking (unchanged)

---

## Consequences

### Positive

- ✅ **Semantic coherence restored:** Tables interpretable by LLM
- ✅ **Expected +10-15pp accuracy gain** (52% → 62-67%)
- ✅ **-87% chunk reduction** (1,592 → 200-250 chunks)
- ✅ **Industry best practice:** Aligned with BlackRock, BNP Paribas patterns
- ✅ **Query latency improvement:** -10-15% (fewer chunks to process)

### Negative

- ⚠️ **Variable chunk sizes:** 512 tokens to 4096 tokens (non-uniform)
- ⚠️ **Increased ingestion complexity:** Table detection + split logic (+30 lines code)
- ⚠️ **Re-ingestion required:** Delete + rebuild Qdrant collection

### Risk Assessment

**Risk Level:** **LOW**

**Mitigation:**
- Table detection: Uses Docling's built-in `ElementType.TABLE` (reliable)
- Row splitting: Preserves headers in each chunk (maintains interpretability)
- Backward compatibility: Metadata schema supports both chunk types
- Rollback: Can revert to fixed chunking if validation fails

---

## Implementation

**Files Modified:**
- `raglite/ingestion/pipeline.py` (~30 lines - table detection)
- `raglite/ingestion/contextual.py` (~80 lines - table-aware logic)

**Dependencies:**
- tiktoken (already approved in Story 2.3)
- Docling TableItem API (already in use)

**Estimated Effort:** 6-8 hours (Story 2.8)

---

## Validation Criteria

**Story 2.8 Acceptance Criteria:**
- ✅ Tables <4096 tokens: 1 chunk per table
- ✅ Large tables: N chunks with headers preserved
- ✅ Total chunks: 1,592 → 200-250 (-87%)
- ✅ Chunks per table: 8.6 → 1.2 (-85%)

**Story 2.5 Re-Validation (After Story 2.8):**
- ✅ Target: ≥70% retrieval accuracy (unblock Epic 3)
- ✅ Expected: 65-75% accuracy (combined with Stories 2.9-2.11 fixes)

---

## References

**Analysis:**
- `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/phase2a-deep-dive-analysis.md` (Root Cause #1)

**Stories:**
- Story 2.8: Implement Table-Aware Chunking Strategy
- Story 2.5: AC3 Validation (re-run after fixes)

**Research:**
- BlackRock/NVIDIA: "HybridRAG: Integrating Knowledge Graphs and Vector Retrieval" (2024)
- BNP Paribas: "GraphRAG for Financial Document Analysis" (2024)
- Yepes et al.: "Chunking Strategies for Financial Document Retrieval" (2024)

---

**Decision Maker:** Product Manager (John) + Architect (Winston)
**Approved By:** User (Ricardo)
**Implementation:** Development Team (Amelia)

---

**Status:** ✅ Accepted | **Implementation:** Story 2.8 (PENDING)
