# CRITICAL ANALYSIS: Why Retrieval Fails Despite Correct Ground Truth

## Executive Summary

**Finding:** Page 46 contains ALL the correct operational data, but hybrid search fails to retrieve it (18% accuracy).

**Root Cause:** Semantic search cannot match queries to page 46 content, despite both text and embeddings being present.

## Evidence

### 1. Page 46 Content Verification (PDF Direct Reading)

Page 46 DEFINITELY contains:
- Variable Costs: `23,2 EUR/ton` ✅
- Termic Energy: `5,8 EUR/ton` ✅
- External Electricity: `61,4 EUR/MWh` ✅
- Raw Materials: `3,5 EUR/ton` ✅
- Alternative Fuel: `50%` ✅
- Maintenance: `11,1 EUR/ton` ✅
- FTEs: `232` ✅
- CO2: `763 kg/ton` ✅

**Conclusion:** Ground truth was 100% correct. We should NEVER have changed it.

### 2. Qdrant Database Verification

- Page 46: ✅ Present (1 chunk, 20,423 characters)
- Chunk contains: "variable cost" ✅, "23.2" ✅, "5.8" ✅
- All critical pages present: 1, 3, 7, 17, 31, 42, 43, 46 ✅

**Conclusion:** Data ingestion worked. Page 46 IS in the database.

### 3. Retrieval Test Results

With correct ground truth (page 46):
- Accuracy: **18%** (9/50 queries)
- Page 46 retrieved for: **0 queries**
- Instead retrieved: pages 42, 30, 17, 43, 31, etc.

Query examples:
- Q1 "Variable costs per ton" → Retrieved pages [42, 30, 17, 43, 15] ❌ (page 46 missing)
- Q2 "Thermal energy costs" → Retrieved pages [31, 43, 17, 18, 19] ❌ (page 46 missing)
- Q3 "Electricity costs" → Retrieved pages [31, 43, 17, 19, 18] ❌ (page 46 missing)

**Conclusion:** Semantic search fails to find page 46 despite correct embeddings.

## Root Cause Analysis

### Hypothesis 1: Table Structure Interferes with Embeddings ❓

Page 46 chunk text shows markdown table formatting:
```
| Aug-25  | Month  B Aug-25 | Aug-24  | Var. % B | % LY |
```

**Problem:** Table structure (pipes, dashes) may dominate the text representation, reducing semantic similarity for content queries.

**Evidence:**
- Page 31, 43 (also tables) ARE being retrieved
- Suggests table structure alone isn't the issue

### Hypothesis 2: Chunk Too Large / Dense ❗

- Page 46 chunk: 20,423 characters
- Contains 304 numbers and dozens of metrics
- May be "semantically diffuse" - no single dominant topic

**Problem:** When chunk contains EVERYTHING (all costs, margins, production metrics), it may score lower for ANY specific query than chunks with focused content.

**Evidence:**
- Page 31 (focused on P&L) retrieved for EBITDA queries ✅
- Page 43 (focused on capex) retrieved for capex queries ✅
- Page 46 (contains everything) retrieved for nothing ❌

### Hypothesis 3: Fin-E5 Embedding Model Limitation ❗❗

Fin-E5 is trained on financial documents, but may struggle with:
- Dense tabular content
- Multi-metric pages (50+ different KPIs on one page)
- Distinguishing between column headers and data values

**Problem:** Embedding may not capture the specific metric relationships needed for precise retrieval.

## What Went Wrong in Our Debugging

1. **Circular Validation:** Changed ground truth to match search results
2. **No PDF Verification:** Didn't verify actual page content
3. **Trusted Search Results:** Assumed if search returned page X, that page must be correct
4. **Missed Root Cause:** Focused on ground truth instead of search algorithm

**Lesson:** Always verify ground truth against source documents FIRST, before debugging search.

## Next Steps - Options

### Option A: Fix Search Algorithm (Recommended)

**Goal:** Make search correctly retrieve page 46

**Approaches:**
1. **Better Chunking:** Split page 46 into topic-focused chunks
   - One chunk for variable costs
   - One chunk for fixed costs
   - One chunk for production metrics
   - Reduces semantic diffusion

2. **Contextual Metadata:** Add LLM-generated chunk descriptions
   - "This chunk contains variable costs per ton for Portugal Cement"
   - Improves semantic matching

3. **Hybrid Weight Tuning:** Adjust alpha parameter
   - Current: alpha=0.7 (70% dense, 30% BM25)
   - Try: alpha=0.5 or alpha=0.3 (more BM25 weight)
   - BM25 better for exact number/term matching

4. **Query Expansion:** Rewrite queries to include table context
   - "Portugal Cement operational performance variable costs EUR/ton"
   - Instead of just "variable costs per ton"

### Option B: Different Embedding Model (Risky)

**Goal:** Use model better suited for dense tabular data

**Candidates:**
- ColBERT: Token-level matching, better for tables
- text-embedding-3-large: Proven better on T₂-RAGBench (R@1 33.8%)

**Risk:** Requires re-ingestion, may not solve semantic diffusion

### Option C: Accept Current State & Document (Not Recommended)

**Reality:** 18% accuracy unacceptable for production

---

## Recommended Action Plan

**IMMEDIATE (Next 2 hours):**
1. Implement topic-focused chunking for page 46
2. Re-ingest with 3-5 smaller chunks per page
3. Retest accuracy

**IF >60% accuracy:** Proceed with Option A approach 1-3

**IF <60% accuracy:** Escalate to PM - Phase 2B Multi-Index approach needed

**Cost:** Option A = $500, 4 hours | Phase 2B = $30-40K, 3-4 weeks

---

**Status:** DECISION GATE FAILED (18% vs 70% target)
**Blocker:** Semantic search cannot retrieve correct page despite valid ground truth
**Owner:** Development team
**Next Review:** After implementing Option A chunking fix
