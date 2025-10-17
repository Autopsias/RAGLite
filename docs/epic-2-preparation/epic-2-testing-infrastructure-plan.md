# Epic 2 Testing Infrastructure Plan

**Date:** 2025-10-16
**Planner:** Murat (Test Architect)
**Duration:** 2 hours
**Status:** PLANNED (Ready for implementation)

---

## Overview

This plan outlines the testing infrastructure enhancements needed to track Epic 2 accuracy improvements incrementally and detect regressions early.

---

## Deliverable 1: Epic 2 Progress Tracking Script

**File:** `scripts/track-epic-2-progress.py`

**Purpose:**
- Track accuracy metrics after each Epic 2 story
- Compare against Epic 1 baseline (56% retrieval, 32% attribution)
- Visualize improvement trend

**Features:**
1. Load baseline metrics from `baseline-accuracy-report-FINAL.txt`
2. Run current accuracy tests via `scripts/run-accuracy-tests.py`
3. Calculate delta (current - baseline)
4. Log results with timestamp and story ID
5. Generate trend visualization (ASCII chart or matplotlib)

**Output Format:**
```
Epic 2 Progress Tracker
=======================
Baseline (Epic 1): 56.0% retrieval, 32.0% attribution
Story 2.1: 72.0% retrieval (+16.0%), 45.0% attribution (+13.0%)
Story 2.2: 75.0% retrieval (+19.0%), 48.0% attribution (+16.0%)
...
Target: 90.0% retrieval, 95.0% attribution
Progress: 84% toward retrieval goal, 25% toward attribution goal
```

**Implementation Estimate:** 1 hour

---

## Deliverable 2: Hybrid Search Diagnostics

**File:** `scripts/hybrid-search-diagnostics.py`

**Purpose:**
- Analyze BM25 vs semantic score contributions per query
- Identify which retrieval method (BM25 or semantic) drives accuracy
- Tune fusion alpha parameter (weighted sum)

**Features:**
1. Run hybrid search with score breakdown
2. Track BM25 score vs semantic score per query
3. Identify queries where BM25 dominates vs semantic dominates
4. Generate fusion parameter recommendations

**Output Format:**
```
Hybrid Search Diagnostics (50 queries)
======================================
BM25 Dominant: 18 queries (36%)
  - Example: "What is the variable cost per ton?" (BM25: 0.85, Semantic: 0.42)
Semantic Dominant: 22 queries (44%)
  - Example: "Explain the EBITDA margin trend" (BM25: 0.31, Semantic: 0.78)
Balanced: 10 queries (20%)

Recommended Fusion Alpha: 0.65 (65% semantic, 35% BM25)
```

**Implementation Estimate:** 45 minutes

---

## Deliverable 3: Regression Test Suite

**File:** `tests/integration/test_epic2_regression.py`

**Purpose:**
- Ensure Epic 2 changes don't degrade Epic 1 baseline
- Set accuracy floor (56% retrieval minimum)
- Set latency ceiling (10s p95 maximum)

**Test Cases:**
1. **test_retrieval_accuracy_floor()**
   - Run ground truth suite
   - Assert: retrieval_accuracy >= 0.56 (56%)
   - **Regression threshold:** Fails if <56%

2. **test_attribution_accuracy_floor()**
   - Run ground truth suite
   - Assert: attribution_accuracy >= 0.32 (32%)
   - **Regression threshold:** Fails if <32%

3. **test_latency_ceiling()**
   - Run 10-query performance test
   - Assert: p95_latency < 10,000ms
   - **Regression threshold:** Fails if >10s

4. **test_hybrid_fusion_quality()**
   - Run 10 hybrid-specific queries
   - Assert: hybrid_score > max(bm25_score, semantic_score)
   - **Sanity check:** Hybrid should outperform single methods

**Implementation Estimate:** 15 minutes

---

## Implementation Plan

### Phase 1: Script Development (1 hour)

**Task 1.1: Create track-epic-2-progress.py** (45 min)
- Load baseline metrics from previous reports
- Integrate with run-accuracy-tests.py
- Calculate deltas and generate trend output
- Save progress log to `docs/epic-2-progress.log`

**Task 1.2: Create hybrid-search-diagnostics.py** (15 min)
- Extend search.py to return score breakdown
- Analyze BM25 vs semantic contributions
- Generate fusion parameter recommendations

### Phase 2: Regression Tests (45 min)

**Task 2.1: Create test_epic2_regression.py** (30 min)
- Write 4 regression test cases
- Integrate with pytest suite
- Set regression thresholds

**Task 2.2: Update CI/CD** (15 min)
- Add regression tests to GitHub Actions (if applicable)
- Document regression testing strategy

### Phase 3: Documentation (15 min)

**Task 3.1: Testing Strategy Doc** (15 min)
- Document Epic 2 validation approach
- Add regression threshold rationale
- Create troubleshooting guide

---

## Testing Standards (from Retrospective)

**From Epic 1 Lessons:**
1. **Unit tests for new functions** - BM25 indexing, score fusion, hybrid query
2. **Integration tests for accuracy** - End-to-end validation after each story
3. **Performance tests for latency** - p50/p95 tracking per story
4. **Regression tests for Epic 1** - Ensure no degradation below 56%/32%

---

## Success Criteria

Epic 2 testing infrastructure is COMPLETE when:
1. ✅ `track-epic-2-progress.py` generates accuracy trend reports
2. ✅ `hybrid-search-diagnostics.py` analyzes BM25 vs semantic contributions
3. ✅ `test_epic2_regression.py` has 4 regression tests passing
4. ✅ All tests documented in Epic 2 test plan

---

## Next Steps

1. **Murat:** Implement testing infrastructure (2 hours)
2. **Amelia:** Integrate scripts into Story 2.1 validation workflow
3. **Bob:** Add regression testing to Story 2.1 acceptance criteria

---

**Status:** PLANNED
**Implementation By:** Before Story 2.1 starts
**Estimated Effort:** 2 hours
