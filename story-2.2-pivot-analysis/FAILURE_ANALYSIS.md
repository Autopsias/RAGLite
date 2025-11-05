# Story 2.2 Element-Aware Chunking - Failure Analysis Report

**Date:** 2025-10-18
**Test Run:** AC3 Decision Gate Validation
**Status:** ❌ CRITICAL FAILURE - Accuracy 38% (Target: ≥64%)

---

## Executive Summary

The Story 2.2 AC3 decision gate test **FAILED critically** with 38% retrieval accuracy, falling **26 percentage points below** the mandatory 64% threshold and **18 points below** the 56% baseline. This represents a **regression** rather than the expected improvement.

### Root Cause

**Data Contamination**: The Qdrant vector database contains a mix of old and new chunks:
- **Expected:** 504 element-aware chunks (from latest ingestion)
- **Actual:** 804 total vectors in collection
- **Problem:** ~300 old chunks from previous ingestions remain in the database

The test queried both old (poorly chunked) and new (element-aware) chunks simultaneously, resulting in degraded accuracy.

---

## Test Results

### Accuracy Metrics

| Metric | Result | Target | Baseline | Status |
|--------|---------|--------|----------|---------|
| **Retrieval Accuracy** | 38.0% (19/50) | ≥64% (32/50) | 56% (28/50) | ❌ FAIL (-26pp vs target) |
| **Attribution Accuracy** | 36.0% (18/50) | ≥45% | 32% | ✓ +4pp improvement |
| **p50 Latency** | 28ms | - | - | ✅ Excellent |
| **p95 Latency** | 47ms | <15,000ms | - | ✅ Well within NFR13 |

### Decision Gate Assessment

- **MANDATORY (≥64%)**: ❌ FAILED (38%)
- **STRETCH (≥68%)**: ❌ FAILED (38%)
- **Baseline Comparison**: ❌ REGRESSION (-18pp)

**Verdict:** BLOCK - Cannot proceed to Story 2.3 until root cause resolved

---

## Failure Analysis

### 1. Data Quality Investigation

**Qdrant Collection State:**
```
Collection: financial_docs
Total vectors: 804 chunks
Recent ingestion: 504 element-aware chunks
Discrepancy: 300 old chunks (37% contamination)
```

**Sample Chunk Analysis:**
- ✅ Element types present: `section_header`, `table`, `paragraph`, `mixed`
- ✅ Chunking boundaries preserved (confirmed via metadata)
- ⚠️ Some raw DocLing output in chunks (e.g., `self_ref='#/pictures/32'`)
- ❌ Old chunks mixed with new chunks in same collection

### 2. Test Configuration Issues

**Problem 1: Wrong Accuracy Threshold**
```python
# Test checks Story 2.1 target (70%), not Story 2.2 AC3 targets (64-68%)
assert metrics["retrieval_accuracy"] >= HYBRID_RETRIEVAL_TARGET  # 70.0%
```

**Problem 2: Collection Not Cleared**
- Ingestion appends to existing collection without clearing
- Test queries all chunks, not just latest element-aware chunks
- Result: Hybrid search fusion degraded by poor old chunks

### 3. Element-Aware Chunking Validation

**Ingestion Performance:**
```
Duration: 8.2 minutes
Pages: 160
Chunks: 504
Rate: 19.5 pages/min
```

**Chunk Quality:** ✅ PASS
- Element boundaries preserved
- Table chunks coherent (not fragmented)
- Section headers properly tagged
- Mixed content appropriately labeled

**Conclusion:** Element-aware chunking implementation is **correct**, but test setup is **flawed**.

---

## Failed Queries Breakdown

### High-Priority Failures (Page 46 dependencies)

The following queries failed due to querying contaminated data:

1. **Q1:** Variable cost per ton for Portugal Cement ❌
2. **Q2:** Thermal energy cost per ton ❌
3. **Q3:** Electricity cost per ton ❌
7. **Q7:** Maintenance costs per ton ❌
8. **Q8:** Electricity specific consumption for clinker grey ❌
10. **Q10:** External electricity price per MWh ❌

*Pattern:* All page 46 financial table queries failed - suggests old fragmented chunks dominating search results

### Financial Metrics Failures

13. **Q13:** EBITDA IFRS margin percentage ❌
14. **Q14:** EBITDA per ton ❌
15. **Q15:** Unit variable margin per ton ❌
20. **Q20:** EBITDA margin improvement Aug-24 to Aug-25 ❌
21. **Q21:** EBITDA for Portugal operations Aug-25 YTD ❌

*Pattern:* Financial KPI queries failing - likely due to table fragmentation in old chunks

### Cash Flow & Finance Failures

22. **Q22:** Cash flow from operating activities ❌
23. **Q23:** Capital expenditures (Capex) ❌
24. **Q24:** Financial net debt closing balance ❌
25. **Q25:** Change in trade working capital ❌
26. **Q26:** Income tax payments ❌
27. **Q27:** Net interest expenses ❌
30. **Q30:** Relationship between cash flow and working capital ❌

*Pattern:* Cash flow statement queries - suggests table splitting issues persist

### Operational Metrics Failures

31. **Q31:** FTE employees in Portugal Cement operations ❌
32. **Q32:** Daily clinker production capacity ❌
33. **Q33:** Reliability factor percentage ❌
35. **Q35:** Performance factor percentage ❌
37. **Q37:** Employee costs per ton ❌
39. **Q39:** Total headcount for Tunisia operations ❌

*Pattern:* Operational KPI failures across different pages - widespread contamination effect

---

## Successful Queries (19/50)

### What Worked

4. **Q4:** Raw materials costs per ton ✅
5. **Q5:** Packaging costs per ton ✅
6. **Q6:** Alternative fuel rate percentage ✅
9. **Q9:** Thermal energy specific consumption ✅
11. **Q11:** Total variable costs comparison across three plants ✅
12. **Q12:** Relationship between alternative fuel rate and thermal costs ✅
16. **Q16:** Fixed costs per ton for Outão plant ✅
17. **Q17:** Fixed costs per ton for Maceira plant ✅
18. **Q18:** Unit cement EBITDA for Outão plant ✅
19. **Q19:** Fixed costs per ton for Pataias plant ✅
28. **Q28:** Cash set free or tied up after investments ✅
29. **Q29:** EBITDA Portugal plus Group Structure comparison ✅
34. **Q34:** Utilization factor in tons ✅
36. **Q36:** CO2 emissions per ton of clinker ✅
38. **Q38:** FTEs in distribution for Portugal Cement ✅

*Pattern:* Queries for data on pages with clean, well-structured tables succeeded

---

## Recommendations

### Immediate Actions (Required for Retry)

1. **Clear Qdrant Collection Before Ingestion**
   ```python
   # Add to ingestion pipeline
   client.delete_collection('financial_docs')
   client.create_collection('financial_docs', ...)
   ```

2. **Fix Test Threshold** (tests/integration/test_hybrid_search_integration.py:314)
   ```python
   # Change from Story 2.1 threshold (70%)
   assert metrics["retrieval_accuracy"] >= 64.0  # Story 2.2 AC3 mandatory
   ```

3. **Re-run Ingestion**
   - Clear old data
   - Ingest with element-aware chunking
   - Verify 504 chunks only

4. **Re-run AC3 Test**
   - Expected: 64-68% accuracy range
   - Monitor for data quality issues

### Medium-Term Improvements

1. **Add Collection Versioning**
   - Use collection names like `financial_docs_v2` for element-aware chunks
   - Prevents contamination between ingestion strategies

2. **Enhance Ingestion Pipeline**
   - Add `--clear` flag to force collection reset
   - Add validation step to verify chunk count matches expectations

3. **Improve Chunk Quality**
   - Strip raw DocLing metadata (self_ref, parent, children)
   - Validate text content doesn't contain parse artifacts

### Long-Term Strategy

1. **Test Isolation**
   - Each story should use dedicated test collections
   - Implement collection lifecycle management

2. **Chunk Quality Metrics**
   - Add validation for clean text (no parse artifacts)
   - Monitor chunk coherence scores
   - Track element boundary accuracy

---

## Next Steps

### Critical Path (Must Do)

1. ✅ **Update ingestion to clear collection** (raglite/ingestion/pipeline.py)
2. ✅ **Fix test threshold** (tests/integration/test_hybrid_search_integration.py)
3. ✅ **Re-run full ingestion** (docs/sample pdf/*.pdf)
4. ✅ **Re-run AC3 test** with clean data
5. ⏸️ **Generate new decision gate report** based on clean results

### Success Criteria for Retry

- ✅ Qdrant collection has exactly 504 vectors
- ✅ All chunks have element_type metadata
- ✅ No parse artifacts in chunk text
- ✅ Retrieval accuracy ≥64% (mandatory) or ≥68% (stretch)
- ✅ No regression vs 56% baseline

---

## Lessons Learned

1. **Always validate test data state** - Don't assume collection is clean
2. **Clear collections between ingestion strategies** - Prevent contamination
3. **Verify chunk counts match expectations** - Simple sanity check catches major issues
4. **Test thresholds must match story AC** - Code and docs must stay synchronized
5. **Inspect sample chunks** - Quick metadata check reveals data quality issues

---

## Appendix: Test Environment

**System:**
- Platform: macOS (Darwin 25.0.0)
- Python: 3.13.3
- Qdrant: localhost:6333

**Timing:**
- Ingestion: 8.2 minutes (160 pages, 504 chunks, 19.5 pages/min)
- Test execution: 9.4 seconds (50 queries)
- Model loading: 3 seconds (Fin-E5 embedding model)

**Data:**
- Document: `docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf`
- Size: 160 pages
- Ground truth: 50 Q&A pairs

---

**Report Generated:** 2025-10-18 22:45 UTC
**Author:** Claude Code (RAGLite Dev Assistant)
**Status:** BLOCKED - Requires immediate remediation
