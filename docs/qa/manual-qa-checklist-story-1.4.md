# Manual QA Checklist - Story 1.4: Document Chunking

**Story:** 1.4 - Document Chunking & Semantic Segmentation
**Reviewer:** _______________
**Date:** _______________
**Test Document:** `tests/fixtures/sample_financial_report.pdf` (10 pages)

## Purpose

This checklist validates Acceptance Criterion 5 (AC5): "Chunk quality validated manually on sample documents (no mid-sentence splits, logical boundaries)."

Manual review complements automated testing by validating subjective quality aspects that are difficult to automate.

---

## Pre-Test Setup

- [ ] Verify test environment is set up: `uv sync`
- [ ] Verify sample PDF exists: `tests/fixtures/sample_financial_report.pdf`
- [ ] Run ingestion to generate chunks: `uv run python -m raglite.ingestion.pipeline tests/fixtures/sample_financial_report.pdf`

---

## Test Execution

### 1. Chunk Boundary Quality

Review first 10 chunks manually and validate:

| Chunk # | No Mid-Sentence Split? | Logical Boundary? | Notes |
|---------|------------------------|-------------------|-------|
| 0       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |
| 1       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |
| 2       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |
| 3       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |
| 4       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |
| 5       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |
| 6       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |
| 7       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |
| 8       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |
| 9       | [ ] Yes / [ ] No       | [ ] Yes / [ ] No  |       |

**Definition:**
- **No Mid-Sentence Split:** Chunk ends at sentence boundary (period, question mark, exclamation)
- **Logical Boundary:** Chunk doesn't split paragraphs, tables, or semantic sections unnaturally

### 2. Table Preservation

Identify chunks containing tables and validate:

| Chunk # | Contains Table? | Table Complete? | Table Split? | Notes |
|---------|-----------------|-----------------|--------------|-------|
|         | [ ] Yes         | [ ] Yes / [ ] No| [ ] Yes / [ ] No |     |
|         | [ ] Yes         | [ ] Yes / [ ] No| [ ] Yes / [ ] No |     |
|         | [ ] Yes         | [ ] Yes / [ ] No| [ ] Yes / [ ] No |     |

**Expected:** Tables should NOT be split mid-row. Complete tables should stay within single chunks (AC2).

### 3. Page Number Accuracy

Sample 5 random chunks and validate page numbers:

| Chunk # | Reported Page # | Actual Page # (Manual Check) | Match? | Notes |
|---------|-----------------|------------------------------|--------|-------|
|         |                 |                              | [ ] Yes / [ ] No | |
|         |                 |                              | [ ] Yes / [ ] No | |
|         |                 |                              | [ ] Yes / [ ] No | |
|         |                 |                              | [ ] Yes / [ ] No | |
|         |                 |                              | [ ] Yes / [ ] No | |

**Method:** Open PDF in viewer, locate chunk content, verify page number matches reported value.

**Tolerance:** ±1 page acceptable for chunks near page boundaries.

### 4. Financial Context Preservation

Review chunks containing financial data:

- [ ] **Currency values:** Not split across chunks (e.g., "$1,234" not broken)
- [ ] **Percentages:** Not split across chunks (e.g., "12.5%" not broken)
- [ ] **Dates:** Not split across chunks (e.g., "Q3 2024" not broken)
- [ ] **Financial metrics:** Complete metric + value in same chunk (e.g., "Revenue: $5M")

### 5. Chunk Size Consistency

- [ ] **Average chunk size:** Review ~10 chunks - most should be 400-600 words
- [ ] **Outliers identified:** Note any chunks <100 words or >800 words (may indicate issues)
- [ ] **Last chunk handling:** Last chunk of document can be shorter - this is expected

### 6. Content Completeness

- [ ] **No missing content:** Spot-check that document content is fully covered by chunks
- [ ] **No duplicate content:** Chunks have overlap (50 words) but no full duplication
- [ ] **No garbled text:** All chunks have readable, coherent text (no encoding issues)

---

## Pass/Fail Criteria

**PASS if:**
-  80%+ chunks have no mid-sentence splits (8/10 or better)
-  100% of tables are not split mid-row (0 table splits)
-  80%+ page numbers match manual verification (4/5 or better)
-  All financial context preserved (no broken currency/percentage values)

**FAIL if:**
- L >20% chunks have mid-sentence splits (3+ out of 10)
- L Any table split mid-row
- L >20% page numbers incorrect (2+ out of 5)
- L Financial data frequently broken across chunks

---

## Test Result

- [ ] **PASS** - All criteria met, AC5 validated
- [ ] **FAIL** - Issues found, requires fixes

**Overall Notes:**

```
(Record overall observations, issues found, and recommendations)




```

---

## Action Items (If Failed)

- [ ] Document specific failures with chunk IDs
- [ ] Create bug report with examples
- [ ] Update Story 1.4 with findings
- [ ] Retest after fixes

---

**Checklist Version:** 1.0
**Last Updated:** 2025-10-12
**Owned By:** QA/Dev Team
