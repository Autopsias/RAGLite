# BM25 Architecture Decision Record (ADR)

**Date:** 2025-10-16
**Status:** PROPOSED
**Researchers:** Winston (Architect) + Amelia (Developer)
**Decision Owner:** Ricardo (User approval required for tech stack)

---

## Context

Epic 2 Story 2.1 (Hybrid Search) requires implementing BM25 + semantic vector fusion to improve retrieval accuracy from 56% → 90%+. Based on baseline failure analysis from Story 1.15B, keyword coverage gaps (44% of failures) indicate BM25 will provide significant improvement.

---

## Research Summary

### Qdrant v1.15+ Sparse Vector Support

**Key Finding:** Qdrant supports sparse vectors (including BM25) but does NOT compute BM25 natively.

**Implementation Approach:**
- Qdrant stores and searches sparse vectors via `SparseVector(indices, values)` format
- BM25 vectors must be pre-computed externally by application code
- Supports hybrid search combining dense + sparse vectors in same collection

**Configuration Example (from Perplexity research):**
```python
from qdrant_client import QdrantClient, models

client.create_collection(
    collection_name="hybrid_collection",
    vectors_config={
        "text-dense": models.VectorParams(
            size=768,  # Fin-E5 dimension
            distance=models.Distance.COSINE,
        )
    },
    sparse_vectors_config={
        "text-sparse": models.SparseVectorParams(
            index=models.SparseIndexParams(on_disk=False),
        )
    }
)
```

---

## Decision Options

### Option A: Qdrant Sparse Vectors + rank_bm25 Library (RECOMMENDED)

**Approach:**
- Use `rank_bm25` Python library to compute BM25 sparse vectors
- Store in Qdrant sparse vector collection
- Query using hybrid search (dense + sparse)

**Pros:**
- ✅ Well-established library (`rank_bm25`) with 1.8k+ GitHub stars
- ✅ Used by major projects (LlamaIndex, Haystack, MetaGPT, mem0ai)
- ✅ Efficient: BM25Okapi algorithm optimized for sparse vectors
- ✅ Qdrant native sparse vector support (fast queries)
- ✅ Clean separation: BM25 computation (app) vs storage (Qdrant)

**Cons:**
- ⚠️ **Requires new dependency** (`rank_bm25`) → TECH STACK APPROVAL NEEDED
- ⚠️ BM25 indexing must be rebuilt when new documents added
- ⚠️ Re-indexing time: ~30-60s for 321 chunks (acceptable)

**Estimated Latency:**
- BM25 query time: ~50-100ms for 321 chunks
- Sparse vector query (Qdrant): ~20-50ms
- Combined (BM25 + semantic): ~70-150ms

**Code Reference (GitHub):**
```python
from rank_bm25 import BM25Okapi

# Tokenize documents (from GitHub: camel-ai/camel)
tokenized_docs = [doc.split() for doc in documents]

# Create BM25 index
bm25 = BM25Okapi(tokenized_docs)

# Query
query_tokens = query.split()
scores = bm25.get_scores(query_tokens)
```

---

### Option B: Qdrant Built-in BM25 (Qdrant/bm25 fastembed model)

**Approach:**
- Use Qdrant's `fastembed_sparse_model="Qdrant/bm25"` for sparse vector generation
- Qdrant handles BM25 computation internally

**Pros:**
- ✅ **Zero new dependencies** (Qdrant built-in)
- ✅ Simplified architecture (no external BM25 library)
- ✅ Automatic BM25 vector generation during ingestion

**Cons:**
- ⚠️ Less control over BM25 parameters (k1, b tuning)
- ⚠️ Limited documentation for parameter tuning
- ⚠️ Unclear if supports custom tokenization for financial terms

**Estimated Latency:**
- Similar to Option A (~70-150ms combined)

**Code Reference (from LlamaIndex):**
```python
from llama_index.vector_stores.qdrant import QdrantVectorStore

vector_store = QdrantVectorStore(
    "hybrid_collection",
    client=client,
    enable_hybrid=True,
    fastembed_sparse_model="Qdrant/bm25",  # Built-in BM25
    batch_size=20,
)
```

---

### Option C: In-Memory BM25 + Qdrant Dense Vectors (Separate)

**Approach:**
- Maintain in-memory BM25 index using `rank_bm25`
- Query BM25 and Qdrant separately, fuse results in Python

**Pros:**
- ✅ Maximum control over BM25 parameters
- ✅ Easy to debug and tune
- ✅ No Qdrant sparse vector setup needed

**Cons:**
- ❌ In-memory BM25 index consumes RAM (~5-10MB for 321 chunks)
- ❌ BM25 index lost on restart (must rebuild)
- ❌ Two separate queries (BM25 + Qdrant) → higher latency
- ❌ Manual score fusion required

**Estimated Latency:**
- BM25 query: ~50-100ms
- Qdrant dense query: ~30-50ms
- Score fusion: ~10-20ms
- **Total: ~90-170ms** (higher than Options A/B)

---

## BM25 Parameter Tuning (Financial Documents)

Based on Perplexity research for dense technical financial content:

| Parameter | Recommended Value | Rationale |
|-----------|------------------|-----------|
| **k1** | 1.5 - 2.0 | Higher than default (1.2) for dense financial docs with legitimate term repetition |
| **b** | 0.5 - 0.7 | Lower than default (0.75) to reduce penalty for longer comprehensive reports |

**Starting Values:**
- k1 = 1.7
- b = 0.6

**Tuning Strategy:**
- Run baseline with k1=1.7, b=0.6
- Adjust ±0.1-0.2 based on ground truth accuracy
- Test with 10-15 financial-heavy queries from ground truth set

---

## Hybrid Search Fusion Strategies

### Strategy 1: Weighted Sum (RECOMMENDED)

**Formula:**
```
hybrid_score = alpha * semantic_score + (1 - alpha) * bm25_score
```

**Recommended Weight:**
- alpha = 0.7 (70% semantic, 30% BM25)
- Rationale: Semantic captures context, BM25 ensures keyword precision

**Pros:**
- ✅ Simple to implement
- ✅ Interpretable (clear weight tradeoff)
- ✅ Fast (no re-ranking needed)

**Cons:**
- ⚠️ Requires score normalization (BM25 vs cosine similarity ranges differ)
- ⚠️ Alpha requires tuning per dataset

**Code Pattern:**
```python
def weighted_fusion(semantic_results, bm25_results, alpha=0.7):
    # Normalize scores to [0, 1]
    semantic_norm = normalize_scores(semantic_results)
    bm25_norm = normalize_scores(bm25_results)

    # Combine
    hybrid_scores = alpha * semantic_norm + (1 - alpha) * bm25_norm
    return hybrid_scores
```

---

### Strategy 2: Reciprocal Rank Fusion (RRF)

**Formula:**
```
RRF_score(doc) = sum(1 / (k + rank_i(doc)))
```
where k = 60 (standard constant)

**Pros:**
- ✅ No score normalization needed
- ✅ Rank-based (more robust to score scale differences)
- ✅ Used by Weaviate, Elasticsearch for hybrid search

**Cons:**
- ⚠️ Slightly more complex than weighted sum
- ⚠️ Less intuitive than alpha weighting

**Code Pattern:**
```python
def reciprocal_rank_fusion(semantic_results, bm25_results, k=60):
    scores = {}
    for rank, doc_id in enumerate(semantic_results):
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    for rank, doc_id in enumerate(bm25_results):
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

---

## Research Findings from Real-World Implementations

**GitHub Search Results:**
- **rank_bm25 adoption:** Used by camel-ai, MetaGPT, gorilla, mem0ai, crawl4ai (5+ major projects)
- **Qdrant hybrid search:** Supported in LlamaIndex, implemented in multiple production systems
- **Fusion strategies:** Weighted sum and RRF both common, RRF gaining adoption

**ArXiv Research (2024-2025):**
- Hybrid search outperforms single-method retrieval by 15-25% (arXiv:2508.01405v1)
- RRF and weighted sum perform similarly, with RRF slightly better for multi-lingual
- Tensor-based re-ranking (TRF) emerging but computationally expensive

**Weaviate/Qdrant Documentation:**
- Both recommend starting with weighted sum (alpha=0.7)
- Both support BM25F variant (field-weighted BM25)

---

## Recommended Decision

### PRIMARY RECOMMENDATION: Option A (Qdrant Sparse Vectors + rank_bm25)

**Justification:**
1. **Best performance-control tradeoff:** Full BM25 parameter tuning + Qdrant sparse vector speed
2. **Industry-proven:** Used by major AI projects (LlamaIndex, Haystack, mem0ai)
3. **Clear separation of concerns:** BM25 computation (app) vs storage (Qdrant)
4. **Future-proof:** Can upgrade to SPLADE or other sparse models later

**Implementation Plan:**
1. Install `rank_bm25` library (REQUIRES USER APPROVAL - see Task 3)
2. Create BM25 index during PDF ingestion (chunk_by_docling_items step)
3. Store sparse vectors in Qdrant alongside dense Fin-E5 vectors
4. Implement weighted sum fusion (alpha=0.7) in search.py
5. A/B test against RRF fusion

**Estimated Latency Impact:**
- Current p50: 33.20ms
- With hybrid search: ~100-150ms p50 (3-4x increase)
- Still well within 10s NFR13 budget (9,935ms remaining)

---

### FALLBACK: Option B (Qdrant Built-in BM25)

**When to use:**
- IF `rank_bm25` approval delayed/denied
- IF simplicity prioritized over control

**Trade-offs:**
- Lose BM25 parameter tuning flexibility
- Unclear tokenization for financial terms
- Less documentation for debugging

---

## Open Questions for User (Ricardo)

1. **Tech Stack Approval:** Approve `rank_bm25` library for Option A? (See Task 3)
2. **Fusion Strategy Preference:** Weighted sum (alpha=0.7) or RRF?
3. **BM25 Parameter Tuning:** Start with k1=1.7, b=0.6 and iterate?
4. **Latency Budget:** Confirm 100-150ms p50 acceptable for hybrid search?

---

## Next Steps

1. **Task 3:** Request tech stack approval for `rank_bm25` (Winston)
2. **Story 2.1 Drafting:** Use this ADR to create detailed acceptance criteria (Bob)
3. **Implementation Spike:** Test Option A vs Option B on 10-query sample (Amelia)
4. **Fusion A/B Test:** Benchmark weighted sum vs RRF on ground truth set (Murat)

---

## References

**Research Sources:**
- Perplexity AI: Qdrant v1.15+ sparse vector support, BM25 parameter tuning
- Exa AI: Hybrid search fusion strategies, RRF comparison
- GitHub Code Search: rank_bm25 usage patterns (camel-ai, MetaGPT, mem0ai)
- ArXiv: "Balancing the Blend: An Experimental Analysis of Trade-offs in Hybrid Search" (2024)
- Weaviate Blog: "Hybrid Search Explained" (2025)
- Qdrant Docs: Sparse vectors, hybrid search implementation

**Key Papers:**
- arXiv:2508.01405v1 - Hybrid search trade-offs analysis
- Qdrant sparse vectors article (2024)
- FinMTEB benchmark (2025)

---

**Decision Status:** PENDING USER APPROVAL (Tech Stack)
**Expected Approval Date:** 2025-10-17
**Blocker for:** Epic 2 Story 2.1 implementation
