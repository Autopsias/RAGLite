# Tech Stack Approval Request - Epic 2

**Date:** 2025-10-16
**Requestor:** Winston (Architect)
**Approver:** Ricardo (User)
**Epic:** Epic 2 - Advanced RAG Enhancements
**Story:** Story 2.1 - Hybrid Search

---

## Request Summary

**REQUEST:** Approve `rank_bm25` Python library for BM25 sparse vector implementation

**Urgency:** BLOCKER for Story 2.1 implementation
**Alternative:** Qdrant built-in BM25 (less control, acceptable fallback)
**Decision Needed By:** Before Story 2.1 drafting complete

---

## Library Details

### rank_bm25

**PyPI Package:** `rank-bm25`
**Version:** Latest stable (1.0.9+)
**License:** Apache 2.0 (compatible with RAGLite)
**GitHub:** https://github.com/dorianbrown/rank_bm25
**Stars:** 1,800+ (well-established)
**Last Updated:** Active (2024-2025)

**Installation:**
```bash
uv add rank-bm25
```

**Dependencies:**
- numpy (already in RAGLite)
- No additional dependencies

---

## Justification

### Why rank_bm25 is Needed

**Epic 2 Goal:** Improve retrieval accuracy from 56% → 90%+

**Story 1.15B Findings:**
- Keyword coverage gaps: 44% of failures
- Page ranking issues: 32% attribution failures
- **Root cause:** Single-stage semantic search insufficient for financial domain

**BM25 Solution:**
- Hybrid search combining semantic (Fin-E5) + keyword (BM25)
- Expected improvement: +15-20% retrieval accuracy
- Industry standard: Used by Elasticsearch, Weaviate, Qdrant for hybrid search

---

### Technology Stack Compliance Check

**Current Tech Stack (from docs/architecture/5-technology-stack-definitive.md):**

| Component | Technology | Status |
|-----------|------------|--------|
| PDF Processing | Docling | ✅ Approved |
| Excel Processing | openpyxl + pandas | ✅ Approved |
| Embeddings | Fin-E5 | ✅ Approved |
| Vector DB | Qdrant 1.11+ | ✅ Approved |
| MCP Server | FastMCP | ✅ Approved |
| LLM | Claude 3.7 Sonnet | ✅ Approved |
| Backend | Python 3.11+ | ✅ Approved |
| Testing | pytest + pytest-asyncio | ✅ Approved |

**NOT Currently Approved:**
- ❌ `rank_bm25` - **NEW DEPENDENCY** (requires approval)

**Tech Stack Rule (CLAUDE.md):**
> **RULE 2: Technology Stack is LOCKED**
> - ONLY use libraries listed in `docs/architecture/5-technology-stack-definitive.md`
> - NEVER add SDKs, frameworks, or libraries not documented in the requirements
> - If a library isn't in the tech stack table → ASK FIRST, never assume

**Compliance:** This request follows Rule 2 (asking for approval before adding)

---

## Alternatives Evaluation

### Option A: rank_bm25 Library (RECOMMENDED)

**Pros:**
- ✅ Full BM25 parameter control (k1, b tuning)
- ✅ Proven in production (used by 5+ major AI projects)
- ✅ Simple API (BM25Okapi class, 3 methods)
- ✅ Fast (optimized sparse vector implementation)
- ✅ Apache 2.0 license (compatible)

**Cons:**
- ⚠️ Requires tech stack approval
- ⚠️ BM25 index must be maintained separately

**Code Simplicity:**
```python
from rank_bm25 import BM25Okapi

# Create index
tokenized_docs = [doc.split() for doc in documents]
bm25 = BM25Okapi(tokenized_docs)

# Query
scores = bm25.get_scores(query.split())
```

**Production Usage:**
- camel-ai/camel (Retrieval framework)
- FoundationAgents/MetaGPT (AI agent framework)
- ShishirPatil/gorilla (LLM function calling)
- mem0ai/mem0 (Memory layer for LLMs)
- unclecode/crawl4ai (Web scraping + RAG)

---

### Option B: Qdrant Built-in BM25 (FALLBACK)

**Pros:**
- ✅ **Zero new dependencies** (Qdrant built-in)
- ✅ Automatic sparse vector generation
- ✅ Simplified architecture

**Cons:**
- ⚠️ Less BM25 parameter control
- ⚠️ Limited documentation for tuning
- ⚠️ Unclear tokenization for financial terms
- ⚠️ Less proven in financial domain

**Code Example:**
```python
vector_store = QdrantVectorStore(
    enable_hybrid=True,
    fastembed_sparse_model="Qdrant/bm25",  # Built-in
)
```

**Trade-off:**
- Simpler setup BUT less control over BM25 tuning
- Acceptable IF rank_bm25 approval denied

---

### Option C: No BM25 (Skip Story 2.1)

**Impact:**
- ❌ Cannot implement hybrid search
- ❌ Miss +15-20% accuracy improvement
- ❌ Likely fail to reach 90% NFR6 target
- ❌ Epic 2 primary goal unmet

**Not Recommended:** Story 2.1 is highest-priority Epic 2 story per baseline analysis

---

## Risk Assessment

### IF Approved (rank_bm25)

**Risks:**
- LOW: Library well-established (1.8k stars, active maintenance)
- LOW: Apache 2.0 license compatible with RAGLite
- LOW: Simple dependency (only numpy)

**Mitigation:**
- Monitor library updates via Dependabot
- Pin version in pyproject.toml
- Fallback to Option B if issues arise

---

### IF Denied (Use Qdrant Built-in)

**Risks:**
- MEDIUM: Less control over BM25 parameters
- MEDIUM: Unclear tokenization for financial terms
- MEDIUM: May not achieve +15-20% target improvement

**Mitigation:**
- Use Qdrant built-in BM25 (Option B)
- Accept limited tuning capability
- Re-evaluate after Story 2.1 validation

---

## Implementation Impact

### Code Changes (IF Approved)

**Files to Modify:**
1. `pyproject.toml` - Add rank-bm25 dependency
2. `raglite/ingestion/pipeline.py` - Generate BM25 sparse vectors during ingestion
3. `raglite/retrieval/search.py` - Implement hybrid fusion (BM25 + semantic)
4. `tests/unit/test_hybrid_search.py` - Add BM25 unit tests

**Estimated Effort:** 6-8 hours (Story 2.1 implementation)

---

### Latency Impact

**Current:**
- p50: 33.20ms
- p95: 63.34ms

**With rank_bm25 Hybrid Search:**
- p50: ~100-150ms (+3-4x)
- p95: ~200-300ms (+3-5x)

**NFR13 Compliance:**
- Target: <10,000ms p95
- After hybrid: ~300ms p95
- **Remaining budget: 9,700ms** (97% available)
- ✅ **WELL WITHIN BUDGET**

---

## Architectural Compliance

### KISS Principle Check

**CLAUDE.md Rule 1:**
> **RULE 1: KISS (Keep It Simple, Stupid)**
> - NO custom base classes, factories, builders, or abstract layers
> - Write simple, direct functions

**rank_bm25 Compliance:**
- ✅ Direct library usage (no wrappers)
- ✅ Simple API (BM25Okapi class)
- ✅ No abstraction layers needed

**Code Pattern (from reference implementation):**
```python
# CORRECT - Direct SDK usage
from rank_bm25 import BM25Okapi
bm25 = BM25Okapi(tokenized_docs)
scores = bm25.get_scores(query_tokens)

# NO custom wrappers or abstractions
```

---

### Over-Engineering Check

**Red Flags to Avoid (from CLAUDE.md):**
- ❌ Creating a "BaseClass" or "AbstractInterface"
- ❌ Writing a "config loader framework"
- ❌ Adding dependency injection
- ❌ Creating a plugin system

**rank_bm25 Usage:**
- ✅ No base classes (direct BM25Okapi usage)
- ✅ No frameworks (simple function calls)
- ✅ No abstractions (straightforward API)
- ✅ **PASSES OVER-ENGINEERING CHECK**

---

## Recommendation

### PRIMARY: Approve rank_bm25

**Justification:**
1. **Highest accuracy potential:** Full BM25 parameter control
2. **Industry-proven:** 5+ major AI projects use it
3. **KISS-compliant:** Direct usage, no abstractions
4. **Low risk:** Apache 2.0 license, active maintenance
5. **Epic 2 blocker:** Story 2.1 cannot proceed without BM25

**Implementation:**
- Add to `pyproject.toml`
- Update tech stack table in `docs/architecture/5-technology-stack-definitive.md`
- Document in Story 2.1 implementation notes

---

### FALLBACK: Use Qdrant Built-in (IF Denied)

**Justification:**
- Zero new dependencies
- Acceptable for Epic 2 MVP
- Can upgrade to rank_bm25 in Epic 3 if needed

**Trade-off:**
- Less control, potentially lower accuracy improvement
- Still better than no hybrid search

---

## Decision Request

**Please approve ONE of the following:**

**Option 1: Approve rank_bm25** ✅ RECOMMENDED
- Add `rank-bm25` to approved tech stack
- Update `docs/architecture/5-technology-stack-definitive.md`
- Proceed with Story 2.1 using rank_bm25

**Option 2: Use Qdrant Built-in** (Fallback)
- No new dependency
- Use Qdrant fastembed BM25
- Accept limited tuning control

**Option 3: Defer Story 2.1** ❌ NOT RECOMMENDED
- Skip hybrid search
- Miss +15-20% accuracy improvement
- Unlikely to reach 90% NFR6 target

---

## Next Steps (AFTER Approval)

1. **IF Option 1 (rank_bm25 approved):**
   - Update `pyproject.toml`: `uv add rank-bm25`
   - Update tech stack doc: Add rank_bm25 to table
   - Draft Story 2.1 with rank_bm25 implementation plan

2. **IF Option 2 (Qdrant built-in):**
   - Draft Story 2.1 with Qdrant fastembed BM25
   - Document limitations in story notes

3. **IF Option 3 (Defer):**
   - Re-prioritize Epic 2 stories
   - Identify alternative accuracy improvement strategies

---

## Approval Form

**Approver:** Ricardo

**Decision:** [✅] Option 1: Approve rank_bm25 | [ ] Option 2: Qdrant Built-in | [ ] Option 3: Defer

**Date:** 2025-10-16

**Notes:** Approved. rank_bm25 added to tech stack for Story 2.1 (Hybrid Search) implementation. Expected +15-20% retrieval accuracy improvement.

---

**Status:** ✅ APPROVED (Option 1)
**Blocker For:** Story 2.1 (Hybrid Search) - UNBLOCKED
**Approved On:** 2025-10-16
**Next Step:** Implement Story 2.1 with rank_bm25
