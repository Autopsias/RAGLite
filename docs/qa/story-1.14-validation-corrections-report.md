# Story 1.14: Ground Truth Validation Corrections Report

**Generated:** 2025-10-14
**Validator:** Dev Agent (Amelia)
**Status:** CRITICAL DATA QUALITY ISSUE IDENTIFIED

---

## Executive Summary

Validation of all 50 ground truth questions against the actual PDF content reveals **severe data quality issues**:

- **Total Valid:** 16/50 (32%)
- **Corrections Needed:** 34/50 (68%)
- **NOT FOUND:** 20+ questions (keywords not found in ±10 page window)

This explains the 18% retrieval accuracy observed in Story 1.13. The ground truth questions were created with estimated page numbers and were never manually validated against the PDF (Story 1.12A AC6 was skipped).

---

## Validation Results by Category

### 1. Cost Analysis (Q1-Q12)
**Status:** 6/12 valid (50%)

| Q | Status | Expected Page | Actual Page | Action |
|---|--------|--------------|-------------|--------|
| Q1 | ❌ | 45 | 46 | Update page |
| Q2 | ❌ | 47 | 46 | Update page |
| Q3 | ✅ | 48 | 48 | No change |
| Q4 | ✅ | 46 | 46 | No change |
| Q5 | ✅ | 50 | 50 | No change |
| Q6 | ❌ | 44 | 46 | Update page |
| Q7 | ✅ | 52 | 52 | No change |
| Q8 | ✅ | 49 | 49 | No change |
| Q9 | ❌ | 55 | 48-50 | Update page to 48 |
| Q10 | ✅ | 53 | 53 | No change |
| Q11 | ❌ | 43 | 46 | Update page |
| Q12 | ❌ | 58 | NOT FOUND | Wider search needed |

**Corrections:** 6 questions need page updates

---

### 2. Margins (Q13-Q20)
**Status:** 5/8 valid (62.5%)

| Q | Status | Expected Page | Actual Page | Action |
|---|--------|--------------|-------------|--------|
| Q13 | ❌ | 62 | NOT FOUND | Wider search needed |
| Q14 | ✅ | 63 | 63 | No change |
| Q15 | ✅ | 64 | 64 | No change |
| Q16 | ✅ | 60 | 60 | No change |
| Q17 | ✅ | 67 | 67 | No change |
| Q18 | ✅ | 65 | 65 | No change |
| Q19 | ❌ | 68 | NOT FOUND | Wider search needed |
| Q20 | ❌ | 61 | NOT FOUND | Wider search needed |

**Corrections:** 3 questions need investigation (NOT FOUND)

---

### 3. Financial Performance (Q21-Q30)
**Status:** 2/10 valid (20%) - CRITICAL

| Q | Status | Expected Page | Actual Page | Action |
|---|--------|--------------|-------------|--------|
| Q21 | ✅ | 72 | 72 | No change |
| Q22 | ❌ | 70 | 73 | Update page |
| Q23 | ❌ | 74 | 69-73 (multiple) | Update page to 69 |
| Q24 | ❌ | 78 | 77 | Update page |
| Q25 | ❌ | 73 | NOT FOUND | Wider search needed |
| Q26 | ✅ | 82 | 82 | No change |
| Q27 | ❌ | 80 | NOT FOUND | Wider search needed |
| Q28 | ❌ | 79 | NOT FOUND | Wider search needed |
| Q29 | ❌ | 84 | 82-93 (multiple) | Update page to 82 |
| Q30 | ❌ | 71 | NOT FOUND | Wider search needed |

**Corrections:** 8 questions need updates (4 NOT FOUND)

---

### 4. Safety Metrics (Q31-Q36)
**Status:** 2/6 valid (33%)

| Q | Status | Expected Page | Actual Page | Action |
|---|--------|--------------|-------------|--------|
| Q31 | ❌ | 90 | 87 or 97 | Update page to 87 |
| Q32 | ✅ | 92 | 92 | No change |
| Q33 | ❌ | 93 | 83, 89, 92 | Review - numbers only |
| Q34 | ❌ | 95 | NOT FOUND | Wider search needed |
| Q35 | ✅ | 94 | 94 | No change |
| Q36 | ❌ | 91 | NOT FOUND | Wider search needed |

**Corrections:** 4 questions need updates (2 NOT FOUND)

---

### 5. Workforce (Q37-Q42)
**Status:** 0/6 valid (0%) - WORST CATEGORY

| Q | Status | Expected Page | Actual Page | Action |
|---|--------|--------------|-------------|--------|
| Q37 | ❌ | 100 | NOT FOUND | Wider search needed |
| Q38 | ❌ | 102 | NOT FOUND | Wider search needed |
| Q39 | ❌ | 105 | 95-115 (multiple) | Generic numbers - review |
| Q40 | ❌ | 101 | 93-110 (multiple) | Generic numbers - review |
| Q41 | ❌ | 103 | 93-112 (multiple) | Generic numbers - review |
| Q42 | ❌ | 104 | NOT FOUND | Wider search needed |

**Corrections:** All 6 questions need updates (3 NOT FOUND, 3 ambiguous)

---

### 6. Operating Expenses (Q43-Q50)
**Status:** 1/8 valid (12.5%) - SECOND WORST

| Q | Status | Expected Page | Actual Page | Action |
|---|--------|--------------|-------------|--------|
| Q43 | ❌ | 110 | NOT FOUND | Wider search needed |
| Q44 | ✅ | 115 | 115 | No change |
| Q45 | ❌ | 112 | 102, 110, 111 | Update page to 111 |
| Q46 | ❌ | 114 | NOT FOUND | Wider search needed |
| Q47 | ❌ | 113 | NOT FOUND | Wider search needed |
| Q48 | ❌ | 116 | NOT FOUND | Wider search needed |
| Q49 | ❌ | 117 | NOT FOUND | Wider search needed |
| Q50 | ❌ | 118 | NOT FOUND | Wider search needed |

**Corrections:** 7 questions need updates (6 NOT FOUND!)

---

## Critical Issues Identified

### Issue 1: Mass "NOT FOUND" (20+ questions)

**Problem:** Keywords for these questions don't appear in the ±10 page window around expected pages.

**Possible Causes:**
1. Questions reference content that doesn't exist in the PDF
2. Keywords are too specific or incorrectly phrased
3. Content is in a completely different section of the PDF
4. Questions were generated without PDF reference

**Affected Questions:** Q12, Q13, Q19, Q20, Q25, Q27, Q28, Q30, Q34, Q36, Q37, Q38, Q42, Q43, Q46, Q47, Q48, Q49, Q50

**Recommendation:**
- Expand search to entire PDF (pages 1-160)
- If still not found, mark questions as INVALID and rewrite based on actual PDF content
- Alternative: Remove these questions and replace with validated questions

---

### Issue 2: Generic Number Matches

**Problem:** Some questions match numbers (8, 12, 70, 30, etc.) that appear across many pages but lack context.

**Examples:**
- Q39: "8" and "12" appear on 16+ pages
- Q40: "5.7", "5.1", "3.9" appear on multiple pages
- Q41: "ratio 70/30" appears across Angola and Tunisia sections

**Recommendation:**
- Refine keywords to include contextual terms (e.g., "employee turnover" not just "8", "12")
- Verify the question actually asks about content present in the PDF
- Consider rewriting questions for specificity

---

### Issue 3: Multi-Country Document Structure

**Observation:** The PDF contains sections for Portugal, Angola, Tunisia, etc. Many keywords appear in multiple country sections.

**Impact:** Questions need to specify WHICH country/section they're asking about, otherwise they're ambiguous.

**Recommendation:**
- Update expected_section to include country (e.g., "Portugal Cement - Cost Analysis")
- Refine questions to be country-specific
- Update keywords to include country identifiers

---

## Proposed Correction Strategy

### Phase 1: Apply Confirmed Corrections (13 questions)
**Target: 30 minutes**

Questions with clear page corrections:
- Cost Analysis: Q1→46, Q2→46, Q6→46, Q9→48, Q11→46
- Financial Performance: Q22→73, Q23→69, Q24→77, Q29→82
- Safety: Q31→87
- Operating Expenses: Q45→111

### Phase 2: Expand Search for NOT FOUND (20 questions)
**Target: 1 hour**

- Search entire PDF (pages 1-160) for each NOT FOUND question
- Document: (a) page found, (b) keywords need refinement, or (c) content doesn't exist
- For (c): Mark question as INVALID, propose rewrite or removal

### Phase 3: Refine Ambiguous Questions (11 questions)
**Target: 30 minutes**

- Questions with generic number matches need keyword refinement
- Add contextual keywords
- Test refined keywords against PDF

### Phase 4: Re-validate All Corrections
**Target: 30 minutes**

- Apply all corrections to ground_truth.py
- Run structural validation
- Run accuracy tests
- Verify ≥90% accuracy achieved

---

## Rollback Decision Point

**If accuracy still <80% after corrections:**

This indicates the ground truth questions are fundamentally misaligned with the PDF content. Options:

1. **Create entirely new ground truth** (6-8 hours)
   - Open PDF, read through sections
   - Write 50 NEW questions based on actual content
   - Validate as we write

2. **Reduce scope to validated subset** (30 questions)
   - Use only the 16 validated questions + 14 corrected questions
   - Document risk of smaller test set

3. **Use different PDF**
   - Locate the correct PDF from Week 0 spike
   - Validate questions against correct PDF

---

## Next Steps

**Immediate Actions:**

1. ✅ Complete validation of all 50 questions (DONE)
2. 🔄 Apply Phase 1 corrections (13 clear updates)
3. 🔄 Expand search for NOT FOUND questions
4. 🔄 Apply all corrections to ground_truth.py
5. 🔄 Run accuracy tests
6. 🔄 Update documentation

**Decision Point:** After Phase 2, if >15 questions are still INVALID, escalate to Ricardo for guidance on whether to:
- Rewrite invalid questions
- Replace with new questions based on PDF content
- Reduce test set scope

---

## Detailed Corrections Log

### Cost Analysis Corrections

**Q1: Fixed costs per ton**
- Current: Page 45 (contains "Fogos Licenciados")
- Correct: Page 46 (has "fixed costs EUR/ton" in operational performance table)
- Update: `"expected_page_number": 46`

**Q2: Distribution cost per ton**
- Current: Page 47
- Correct: Page 46 (has "distribution costs EUR/ton 14.3" in performance table)
- Update: `"expected_page_number": 46`

**Q6: Variable costs comparison**
- Current: Page 44
- Correct: Page 46 (has "variable costs EUR/ton" comparison)
- Update: `"expected_page_number": 46`

**Q9: Production costs by cement type**
- Current: Page 55
- Correct: Page 48 (Outão plant has "production costs EUR/ton" data)
- Update: `"expected_page_number": 48`

**Q11: YoY cost change and drivers**
- Current: Page 43
- Correct: Page 46 (has cost trends with "energy" and "fixed costs" YoY data)
- Update: `"expected_page_number": 46`

**Q12: Cost savings initiatives**
- Current: Page 58
- Status: NOT FOUND - needs wider search or question rewrite

---

*[Additional corrections to be documented as they are validated]*

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Questions | 50 |
| Valid (no changes) | 16 (32%) |
| Needs Page Update | 14 (28%) |
| NOT FOUND | 20 (40%) |
| Estimated Time to Fix | 2.5-3 hours |
| Risk of <90% accuracy after fix | MODERATE-HIGH |

---

**Generated by:** Dev Agent (Amelia)
**Date:** 2025-10-14
**Story:** 1.14 - Fix Ground Truth Test Set
