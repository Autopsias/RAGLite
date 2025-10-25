# Story 2.9: Fix Ground Truth Page References

Status: Ready for Development

**⚠️ CRITICAL:** Course correction story to enable proper accuracy validation (Root Cause #2 from Phase 2A deep-dive analysis)

## Story

As a **QA engineer and accuracy validation system**,
I want **correct page references in all 50 ground truth queries**,
so that **accuracy metrics are valid and we can properly measure Story 2.8's impact on retrieval performance**.

## Context

Story 2.9 is the **SECOND of four course correction stories** for Epic 2 Phase 2A following the failed AC3 validation (52% accuracy vs ≥70% target).

**Problem Identified:**
Ground truth test suite has incorrect or missing page references in `expected_page_number` field, making accuracy validation unreliable. Story 2.8 (table-aware chunking) AC4 validation was correctly deferred pending this fix.

**Root Cause Analysis:**
- Manual inspection of ground truth queries revealed page reference discrepancies
- Cannot validate retrieval accuracy without knowing correct source pages
- Attribution accuracy (NFR7: ≥95%) cannot be measured without correct page numbers
- Story 2.8 impact assessment blocked (need to validate +10-15pp improvement claim)

**Dependencies:**
- Prerequisite: Story 2.8 (table-aware chunking) COMPLETE ✅
- Blocks: Story 2.11 (combined accuracy validation and hybrid search fixes)
- Unblocks: Ability to measure actual retrieval accuracy post-Story 2.8

**Strategic Context:**
This fix is **mandatory for Epic 2 Phase 2A validation**. Without correct page references, we cannot:
1. Validate Story 2.8's table query accuracy improvement (40% → 75% claim)
2. Measure overall accuracy improvement (52% → 65% target)
3. Make informed decision about Phase 2B necessity

**Source:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/phase2a-deep-dive-analysis.md` (Validation Issue #2)

## Acceptance Criteria

### AC1: Manual Page Reference Validation (2 hours)

**Goal:** Systematically validate all 50 ground truth queries against the actual PDF to identify correct page numbers

**Technical Specifications:**
- Open source PDF: `docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf` (160 pages)
- For each of 50 queries in `tests/fixtures/ground_truth.py`:
  1. Read the question text
  2. Manually search PDF for the answer content
  3. Record the correct page number(s) where answer appears
  4. Compare to current `expected_page_number` value
  5. Document discrepancies in validation worksheet

**Validation Approach:**

```python
# Validation Workflow (Manual Process)

categories = [
    "cost_analysis",     # Questions 1-12
    "margins",           # Questions 13-20
    "financial_performance",  # Questions 21-30
    "safety_metrics",    # Questions 31-36
    "workforce",         # Questions 37-42
    "operating_expenses" # Questions 43-50
]

validation_results = []

for question in GROUND_TRUTH_QA:
    # Manual steps:
    # 1. Read question text
    # 2. Search PDF (Cmd+F or visual scan)
    # 3. Identify page number where answer content appears
    # 4. Record in validation worksheet

    result = {
        "id": question["id"],
        "question": question["question"],
        "current_page": question["expected_page_number"],
        "actual_page": None,  # TO BE FILLED MANUALLY
        "status": None,       # "correct", "incorrect", "missing"
        "notes": ""
    }

    validation_results.append(result)

# Expected Output: Validation worksheet with actual vs expected pages
```

**Validation Worksheet Format:**

```markdown
| Q# | Category | Current Page | Actual Page | Status | Notes |
|----|----------|--------------|-------------|--------|-------|
| 1  | cost_analysis | 46 | ? | ? | Variable cost per ton, Portugal Cement |
| 2  | cost_analysis | 46 | ? | ? | Thermal energy cost per ton |
| ... | ... | ... | ... | ... | ... |
| 50 | operating_expenses | 46 | ? | ? | Fixed cost breakdown |
```

**Validation Rules:**

1. **Page Number Definition:**
   - Use **PDF page number** (bottom of page), NOT document page number
   - If answer spans multiple pages, record **primary page** (where majority of data appears)
   - For table-based answers, record page with **complete table** (not fragments)

2. **Multi-Page Answers:**
   - If answer requires data from 2+ consecutive pages, use PRIMARY page
   - Document in notes that answer spans pages (e.g., "Pages 46-47, primary: 46")

3. **Table Location Verification:**
   - After Story 2.8 (table-aware chunking), tables should be on single pages
   - If table is split across pages in PDF, record page with **table header**
   - Validate that `expected_section` aligns with page content

4. **Ambiguous Cases:**
   - If answer appears on multiple non-consecutive pages, record **first occurrence**
   - Document ambiguity in notes (e.g., "Also appears on p.52")

**Validation:**
- Manually validate all 50 queries against PDF
- Record actual page numbers in validation worksheet
- Categorize results: correct, incorrect, missing
- Document error rate: % of queries with incorrect page references

**Success Criteria:**
- ✅ All 50 queries reviewed against source PDF
- ✅ Actual page numbers recorded in validation worksheet
- ✅ Discrepancies identified and categorized (correct/incorrect/missing)
- ✅ Error rate calculated (expected: >30% incorrect based on Story 2.8 deferral)
- ✅ Validation worksheet saved: `docs/validation/story-2.9-page-validation.md`

**Files Created:**
- `docs/validation/story-2.9-page-validation.md` (validation worksheet with results)

---

### AC2: Update Ground Truth File (1 hour)

**Goal:** Correct all `expected_page_number` fields in ground truth file based on AC1 validation results

**Technical Specifications:**
- Update file: `tests/fixtures/ground_truth.py`
- For each query with incorrect page number:
  1. Replace `expected_page_number` value with correct page from AC1 validation
  2. Verify `expected_section` still aligns with correct page
  3. Add inline comment documenting change: `# Updated Story 2.9: 46 → 52`

**Update Pattern:**

```python
# BEFORE (Example - Question 1)
{
    "id": 1,
    "question": "What is the variable cost per ton for Portugal Cement in August 2025 YTD?",
    "expected_answer": "Variable costs for Portugal Cement are 23.2 EUR/ton...",
    "expected_keywords": ["variable costs", "23.2", "EUR/ton", "20.3", "29.4"],
    "source_document": "2025-08 Performance Review CONSO_v2.pdf",
    "expected_page_number": 46,  # ← May be incorrect
    "expected_section": "Portugal Cement - Operational Performance",
    "category": "cost_analysis",
    "difficulty": "easy",
},

# AFTER (if validation found page 52)
{
    "id": 1,
    "question": "What is the variable cost per ton for Portugal Cement in August 2025 YTD?",
    "expected_answer": "Variable costs for Portugal Cement are 23.2 EUR/ton...",
    "expected_keywords": ["variable costs", "23.2", "EUR/ton", "20.3", "29.4"],
    "source_document": "2025-08 Performance Review CONSO_v2.pdf",
    "expected_page_number": 52,  # Updated Story 2.9: 46 → 52
    "expected_section": "Portugal Cement - Operational Performance",
    "category": "cost_analysis",
    "difficulty": "easy",
},
```

**Update Workflow:**

```python
# Script: scripts/update-ground-truth-pages.py (optional automation)

import sys
from tests.fixtures.ground_truth import GROUND_TRUTH_QA

# Load validation results from AC1
validation_results = load_validation_worksheet("docs/validation/story-2.9-page-validation.md")

corrections = []

for result in validation_results:
    if result["status"] == "incorrect":
        question_id = result["id"]
        old_page = result["current_page"]
        new_page = result["actual_page"]

        corrections.append({
            "id": question_id,
            "old_page": old_page,
            "new_page": new_page
        })

# Manual edits to ground_truth.py
print(f"Total corrections needed: {len(corrections)}")
print("\nCorrections:")
for corr in corrections:
    print(f"  Q{corr['id']}: page {corr['old_page']} → {corr['new_page']}")
```

**Section Verification:**

After updating page numbers, verify `expected_section` still makes sense:

```python
# Example check:
# Q1: expected_page_number=52, expected_section="Portugal Cement - Operational Performance"
# → Open PDF page 52, verify section header matches "Portugal Cement"
# → If mismatch, update expected_section field as well
```

**Validation:**
- Apply all corrections from AC1 validation worksheet
- Add inline comments documenting changes: `# Updated Story 2.9: old → new`
- Run ground truth file to verify Python syntax still valid
- Spot-check 10 random updated queries against PDF to confirm corrections
- Verify no regressions (queries that were correct remain correct)

**Success Criteria:**
- ✅ All incorrect page numbers corrected (100% of discrepancies from AC1)
- ✅ Inline comments added documenting changes
- ✅ `expected_section` fields verified for alignment with new pages
- ✅ Python file syntax valid (no import errors)
- ✅ 10 spot-checks confirm corrections are accurate
- ✅ No regressions introduced (previously correct queries unchanged)

**Files Modified:**
- `tests/fixtures/ground_truth.py` (page number corrections)

---

### AC3: Validation Documentation (30-60 min)

**Goal:** Document the validation process, corrections made, and impact on accuracy testing

**Technical Specifications:**
Create comprehensive validation report documenting:
1. **Validation Methodology:** How pages were validated
2. **Error Analysis:** % incorrect, error patterns, root causes
3. **Corrections Summary:** List of all changes made
4. **Impact Assessment:** How corrections affect accuracy testing
5. **Recommendations:** Prevent future page reference errors

**Validation Report Structure:**

```markdown
# Story 2.9: Ground Truth Page Reference Validation Report

**Date:** 2025-10-25
**Validator:** Dev Agent (Amelia) - BMM Dev Agent
**Source PDF:** 2025-08 Performance Review CONSO_v2.pdf (160 pages)
**Ground Truth File:** tests/fixtures/ground_truth.py (50 queries)

## Executive Summary

- **Total Queries Validated:** 50
- **Incorrect Page References:** XX (XX%)
- **Corrections Applied:** XX
- **Validation Method:** Manual PDF review with keyword search
- **Impact:** Unblocks Story 2.11 accuracy validation

## Methodology

### Validation Process

1. **Manual PDF Review:**
   - Opened source PDF in Adobe Acrobat / Preview
   - For each query, searched PDF using question keywords
   - Located answer content and recorded page number (PDF footer number)
   - Compared to existing `expected_page_number` field

2. **Page Number Definition:**
   - Used **PDF page number** (visible in document footer)
   - For multi-page answers, recorded **primary page** (majority of data)
   - For table answers, recorded page with **complete table** or **table header**

3. **Verification:**
   - Cross-checked `expected_section` alignment with page content
   - Validated that `expected_keywords` appear on identified page
   - Documented ambiguous cases (multi-page answers, duplicate content)

## Error Analysis

### Overall Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| Total queries | 50 | 100% |
| Correct page references | XX | XX% |
| Incorrect page references | XX | XX% |
| Missing page references | XX | XX% |

### Error Distribution by Category

| Category | Total Queries | Incorrect | Error Rate |
|----------|---------------|-----------|------------|
| Cost Analysis | 12 | XX | XX% |
| Margins | 8 | XX | XX% |
| Financial Performance | 10 | XX | XX% |
| Safety Metrics | 6 | XX | XX% |
| Workforce | 6 | XX | XX% |
| Operating Expenses | 8 | XX | XX% |

### Root Cause Analysis

**Identified Error Patterns:**

1. **Table Fragmentation (Pre-Story 2.8):**
   - Ground truth created before table-aware chunking (Story 2.8)
   - Page references pointed to table fragments, not complete tables
   - **Impact:** XX queries affected

2. **PDF vs Document Page Number Confusion:**
   - Possible confusion between PDF page number and document internal numbering
   - **Impact:** XX queries affected

3. **Multi-Page Content:**
   - Answers spanning multiple pages, page reference ambiguous
   - **Impact:** XX queries affected

4. **Copy-Paste Errors:**
   - Repetitive page numbers (e.g., multiple queries all marked page 46)
   - **Impact:** XX queries affected

## Corrections Summary

### Sample Corrections (First 10)

| Q# | Category | Question (Truncated) | Old Page | New Page | Change |
|----|----------|----------------------|----------|----------|--------|
| 1  | cost_analysis | Variable cost per ton... | 46 | XX | +XX |
| 2  | cost_analysis | Thermal energy cost... | 46 | XX | +XX |
| 3  | cost_analysis | Electricity cost... | 46 | XX | +XX |
| 4  | cost_analysis | Raw materials costs... | 46 | XX | +XX |
| 5  | cost_analysis | Packaging costs... | 46 | XX | +XX |
| ... | ... | ... | ... | ... | ... |

### Full Corrections List

(See Appendix A for complete list of all XX corrections)

## Impact Assessment

### Before Corrections (Estimated)

- **Retrieval Accuracy:** Cannot validate - incorrect page references prevent proper scoring
- **Attribution Accuracy:** Cannot validate - wrong page numbers invalidate citation checks
- **Story 2.8 Impact:** Cannot measure - table query accuracy improvement unverifiable

### After Corrections (Expected)

- **Retrieval Accuracy:** Measurable - correct page references enable proper top-5 scoring
- **Attribution Accuracy:** Measurable - correct pages enable NFR7 (≥95%) validation
- **Story 2.8 Impact:** Quantifiable - can now validate 40% → 75% table query accuracy claim

### Unblocked Validation Workflows

1. **Story 2.11 (Combined Validation):**
   - Re-run accuracy tests with corrected ground truth
   - Measure Story 2.8 + 2.9 combined impact
   - Expected: 52% → 65% overall accuracy (+13pp)

2. **Attribution Accuracy (NFR7):**
   - Validate source citations against correct page numbers
   - Target: ≥95% attribution accuracy

3. **Decision Gate (Epic 2 Phase 2A):**
   - Valid accuracy metrics enable Phase 2B decision
   - IF ≥70% → Epic 2 COMPLETE
   - IF <70% → Proceed to Phase 2B (cross-encoder re-ranking)

## Recommendations

### Short-Term (Story 2.9 Implementation)

1. **Automated Validation Script:**
   - Create `scripts/validate-ground-truth-pages.py`
   - Cross-check page numbers against Qdrant chunk metadata
   - Flag discrepancies for manual review

2. **Page Reference Standards:**
   - Document page numbering convention (PDF vs document page)
   - Add validation step to ground truth creation workflow
   - Require multi-reviewer approval for new queries

### Long-Term (Future Epics)

3. **Automated Ground Truth Generation:**
   - Epic 4: Generate page references automatically from Qdrant chunk metadata
   - Use chunk IDs to reverse-lookup source pages
   - Reduce manual validation burden

4. **Continuous Validation:**
   - Add ground truth validation to CI/CD pipeline
   - Fail build if page references don't match chunk metadata
   - Prevent regressions in future ingestion pipeline changes

## Appendix A: Full Corrections List

(Detailed list of all corrections made, organized by category)

### Cost Analysis (Questions 1-12)

- Q1: Page 46 → XX (Variable cost per ton)
- Q2: Page 46 → XX (Thermal energy cost)
- ...

### Margins (Questions 13-20)

- Q13: Page 46 → XX (EBITDA IFRS margin)
- ...

(Continue for all 50 queries)

---

**Report Generated:** 2025-10-25
**Next Steps:** Proceed to Story 2.11 (combined accuracy validation)
```

**Validation:**
- Create comprehensive validation report documenting methodology, errors, corrections
- Calculate error statistics (% incorrect, error distribution by category)
- Analyze root causes for page reference errors
- Document impact on accuracy testing and unblocked workflows
- Provide recommendations for preventing future errors

**Success Criteria:**
- ✅ Validation report created: `docs/validation/story-2.9-validation-report.md`
- ✅ Error analysis complete (% incorrect, patterns identified)
- ✅ Corrections summary documented (all changes listed)
- ✅ Impact assessment provided (what's now measurable)
- ✅ Recommendations for future improvements included

**Files Created:**
- `docs/validation/story-2.9-validation-report.md` (comprehensive validation report)

---

## Tasks / Subtasks

### Task 1: Manual Page Reference Validation (AC1) - 2 hours

- [ ] 1.1: Set up validation workspace
  - Open source PDF: `docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf`
  - Load ground truth file: `tests/fixtures/ground_truth.py`
  - Create validation worksheet template: `docs/validation/story-2.9-page-validation.md`
  - Prepare tracking spreadsheet or markdown table

- [ ] 1.2: Validate cost analysis queries (Q1-Q12) - 30 min
  - For each query, search PDF using keywords from `expected_keywords`
  - Locate answer content and record PDF page number
  - Compare to current `expected_page_number` value
  - Document status (correct/incorrect/missing) in worksheet
  - Add notes for ambiguous cases (multi-page, duplicate content)

- [ ] 1.3: Validate margins queries (Q13-Q20) - 20 min
  - Same process as 1.2 for margins category
  - Verify table-based answers on correct pages
  - Document discrepancies

- [ ] 1.4: Validate financial performance queries (Q21-Q30) - 30 min
  - Same process for financial performance category
  - Cash flow and EBITDA queries likely table-based
  - Verify page references post-Story 2.8 table-aware chunking

- [ ] 1.5: Validate safety metrics queries (Q31-Q36) - 15 min
  - Same process for safety metrics category
  - Operational metrics, headcount, production capacity

- [ ] 1.6: Validate workforce queries (Q37-Q42) - 15 min
  - Same process for workforce category
  - Employee costs, FTE counts, departmental breakdowns

- [ ] 1.7: Validate operating expenses queries (Q43-Q50) - 20 min
  - Same process for operating expenses category
  - Cost categories, fixed vs variable breakdowns

- [ ] 1.8: Analyze validation results
  - Calculate error statistics (% incorrect by category)
  - Identify error patterns (table fragmentation, page numbering confusion, etc.)
  - Document root causes for discrepancies
  - Save validation worksheet with all results

### Task 2: Update Ground Truth File (AC2) - 1 hour

- [ ] 2.1: Review validation results
  - Load validation worksheet from AC1
  - Identify all queries with incorrect page numbers
  - Create correction list (Q#, old page, new page)
  - Verify correction list accuracy (spot-check 5 random entries against PDF)

- [ ] 2.2: Apply corrections to ground truth file
  - Open `tests/fixtures/ground_truth.py` in editor
  - For each incorrect query:
    - Update `expected_page_number` to correct value from validation
    - Add inline comment: `# Updated Story 2.9: old → new`
    - Verify `expected_section` still aligns with new page
  - Save changes

- [ ] 2.3: Verify Python file syntax
  - Run Python import to check for syntax errors:
    ```bash
    python -c "from tests.fixtures.ground_truth import GROUND_TRUTH_QA; print(f'Loaded {len(GROUND_TRUTH_QA)} questions')"
    ```
  - Expected output: "Loaded 50 questions"
  - Fix any syntax errors introduced during editing

- [ ] 2.4: Spot-check corrections
  - Randomly select 10 corrected queries
  - Open PDF to corrected page number
  - Verify answer content appears on that page
  - Verify `expected_keywords` found on page
  - Verify `expected_section` matches page section header

- [ ] 2.5: Regression check
  - Review queries marked "correct" in AC1 validation
  - Verify these queries unchanged in updated file
  - Confirm no accidental edits to correct entries

### Task 3: Validation Documentation (AC3) - 30-60 min

- [ ] 3.1: Create validation report skeleton
  - Create file: `docs/validation/story-2.9-validation-report.md`
  - Add report structure (sections from AC3 template)
  - Populate metadata (date, validator, source PDF, file)

- [ ] 3.2: Document methodology
  - Write "Methodology" section describing validation process
  - Include page number definition used
  - Document verification steps (keyword search, section alignment)

- [ ] 3.3: Perform error analysis
  - Calculate overall statistics (total, correct, incorrect, missing)
  - Calculate error distribution by category (table with % by category)
  - Identify error patterns (root causes: table fragmentation, numbering confusion, etc.)
  - Write "Error Analysis" section with tables and findings

- [ ] 3.4: Document corrections
  - Create corrections summary table (sample of first 10 changes)
  - Create appendix with full corrections list (all 50 queries if corrections made)
  - Document change patterns (e.g., "90% of cost_analysis queries updated 46 → 52")

- [ ] 3.5: Assess impact
  - Write "Impact Assessment" section
  - Document what's now measurable (retrieval accuracy, attribution accuracy)
  - Explain unblocked workflows (Story 2.11, Phase 2B decision gate)
  - Quantify expected accuracy improvement validation (52% → 65% target)

- [ ] 3.6: Provide recommendations
  - Write "Recommendations" section
  - Short-term: Automated validation script, page reference standards
  - Long-term: Automated ground truth generation (Epic 4), CI/CD validation
  - Document how to prevent future page reference errors

- [ ] 3.7: Review and finalize report
  - Proofread for clarity and completeness
  - Verify all sections complete (methodology, errors, corrections, impact, recommendations)
  - Add report generation date and next steps
  - Save final report

### Task 4: Testing and Validation (30 min)

- [ ] 4.1: Unit test validation (optional)
  - Create test script: `scripts/test-ground-truth-pages.py`
  - Load ground truth queries and Qdrant chunk metadata
  - For each query, verify page number matches at least one chunk's page
  - Report any remaining discrepancies

- [ ] 4.2: Integration test (optional)
  - Run sample accuracy test with corrected ground truth
  - Verify test suite executes without errors
  - Spot-check that corrected page numbers improve attribution accuracy
  - Document any issues for Story 2.11 full validation

- [ ] 4.3: Documentation updates
  - Update `CLAUDE.md` Implementation Notes section
  - Document Story 2.9 completion and impact
  - Reference validation report for audit trail

---

## Dev Notes

### Root Cause Context

**Problem Statement from Deep-Dive Analysis:**

"Ground truth page references are incorrect, making accuracy validation unreliable. Cannot measure Story 2.8 table-aware chunking impact without valid page references."

**Impact:**
1. **Invalid Accuracy Metrics:** Cannot score retrieval accuracy (top-5 correct chunk)
2. **Attribution Validation Blocked:** NFR7 (≥95% attribution accuracy) unmeasurable
3. **Story 2.8 Impact Unknown:** Cannot validate table query accuracy improvement (40% → 75% claim)

**Expected Impact:**
- Valid page references → accurate retrieval scoring
- Attribution accuracy measurable → NFR7 compliance verifiable
- Story 2.8 impact quantifiable → 52% → 65% accuracy validation possible

### Implementation Strategy

**Why Manual Validation Required:**

1. **Automation Insufficient:**
   - PDF extraction variability makes automated page detection unreliable
   - Tables split across pages require human judgment
   - Section headers ambiguous (need domain knowledge to validate)

2. **One-Time Investment:**
   - 50 queries × 3 min/query ≈ 2.5 hours total
   - Corrections persist across future testing
   - Prevents compound errors in accuracy validation

3. **Quality Assurance:**
   - Manual review ensures 100% accuracy
   - Human validation catches edge cases (multi-page answers, duplicate content)
   - Builds confidence in ground truth as "single source of truth"

**Design Decisions:**

1. **PDF Page Number Standard:**
   - Use PDF footer page number (visible when opening PDF)
   - More reliable than document internal numbering
   - Aligns with Qdrant chunk metadata (uses PDF page numbers)

2. **Primary Page for Multi-Page Answers:**
   - Record page where majority of answer content appears
   - For tables, prefer page with table header (enables table-aware retrieval)
   - Document multi-page nature in validation notes

3. **Inline Comments for Traceability:**
   - Add `# Updated Story 2.9: old → new` to every corrected query
   - Enables future reviewers to understand changes
   - Audit trail for quality assurance

**Testing Standards:**

**Manual Validation:**
- Search PDF using `expected_keywords` for each query
- Locate answer content (usually in tables for this financial PDF)
- Record page number from PDF footer
- Compare to `expected_page_number` field
- Document discrepancies

**Correction Verification:**
- Spot-check 10 random corrections against PDF
- Verify `expected_section` alignment with corrected pages
- Regression check: confirm previously correct queries unchanged

**Validation Report:**
- Comprehensive documentation of methodology, errors, corrections
- Error analysis by category (root cause patterns)
- Impact assessment (what's now measurable)
- Recommendations for prevention

### KISS Principle Compliance

**Simplicity Checks:**
- ✅ Manual validation (no complex automation needed)
- ✅ Direct file editing (no parsing/generation scripts unless helpful)
- ✅ Simple markdown validation reports (no fancy tooling)
- ✅ Inline comments for traceability (straightforward documentation)

**Avoid Over-Engineering:**
- ❌ NO automated page reference extraction (unreliable for tables)
- ❌ NO PDF parsing libraries (manual faster for 50 queries)
- ❌ NO machine learning page detection (overkill for one-time fix)
- ❌ NO custom validation frameworks (markdown reports sufficient)

### Project Structure Notes

**Files Modified:**
```
tests/fixtures/
└── ground_truth.py              (updated ~50 lines - page number corrections)

docs/validation/
├── story-2.9-page-validation.md  (new, ~100 lines - validation worksheet)
└── story-2.9-validation-report.md (new, ~300 lines - comprehensive report)
```

**No Changes to:**
- `raglite/` (no code changes needed)
- `scripts/` (optional automation scripts, not required)
- `pyproject.toml` (no new dependencies)

### Performance Considerations

**Validation Time:**
- Manual validation: ~2 hours (50 queries × 2.4 min/query average)
- File updates: ~1 hour (corrections + verification)
- Documentation: ~30-60 min (validation report)
- **Total: 3-4 hours** (matches Epic 2 PRD estimate)

**Impact on Testing:**
- No performance impact (ground truth file unchanged except page numbers)
- Accuracy tests run same speed (no algorithm changes)
- Attribution validation now possible (was blocked before)

**Future Efficiency:**
- Automated validation script (Story 2.11 optional) can prevent regressions
- CI/CD integration ensures page references stay accurate across ingestion changes

### References

**Architecture Documents:**
- [Source: docs/architecture/3-repository-structure-monolithic.md] - Repository structure
- [Source: docs/architecture/6-complete-reference-implementation.md] - Testing patterns

**PRD Documents:**
- [Source: docs/prd/epic-2-advanced-rag-enhancements.md] - Epic 2 Phase 2A course correction
- [Source: docs/prd/epic-2-advanced-rag-enhancements.md#story-29] - Story 2.9 specifications

**Root Cause Analysis:**
- [Source: docs/phase2a-deep-dive-analysis.md] - Validation Issue #2: Incorrect page references
- [Source: docs/handoffs/phase2a-course-correction-2025-10-25/SPRINT-CHANGE-HANDOFF-2025-10-25.md] - PM-approved course correction

**Ground Truth:**
- [Source: tests/fixtures/ground_truth.py] - 50 validated Q&A pairs for accuracy testing
- [Source: docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf] - 160-page source document

### Known Constraints

**Course Correction Context:**
This story is part of a **4-story course correction** to fix Phase 2A accuracy plateau (52%). The stories sequence:

1. **Story 2.8 (COMPLETE):** Fix table fragmentation ✅
2. **Story 2.9 (THIS STORY):** Fix ground truth page references ← CURRENT
3. **Story 2.10:** Fix query classification over-routing
4. **Story 2.11:** Fix hybrid search scoring + validate combined accuracy

**Combined Expected Result:** 65-75% accuracy (meets Phase 2A target)

**Decision Gate:**
After Story 2.11, re-run accuracy tests with all fixes applied:
- IF ≥70% → Epic 2 COMPLETE ✅
- IF 65-70% → Re-evaluate Phase 2B necessity
- IF <65% → Escalate to Phase 2B (PM approval required)

**Validation Dependency Chain:**

```
Story 2.8 (Table Chunking)
    ↓ (unblocks)
Story 2.9 (Page References) ← YOU ARE HERE
    ↓ (unblocks)
Story 2.10 (Query Classification)
    ↓ (all combined)
Story 2.11 (Accuracy Re-Validation)
    ↓ (decision gate)
Epic 2 Phase 2A: COMPLETE or Phase 2B Required
```

### NFR Compliance

**NFR6 (Retrieval Accuracy):**
- Target: 70-80% retrieval accuracy (Phase 2A goal)
- Story 2.9 contribution: Enables accurate measurement (was blocked)
- Unblocks: Story 2.8 impact validation (+10-15pp claim)

**NFR7 (Attribution Accuracy):**
- Target: 95%+ source attribution accuracy
- Story 2.9 contribution: Enables page-level citation validation
- Before: Cannot validate (incorrect page references)
- After: Can validate page number matches in citations

**NFR13 (Performance):**
- Target: <15s p95 query latency
- Story 2.9 impact: None (ground truth update, no runtime changes)

## Dev Agent Record

### Context Reference

- **Story Context XML:** `docs/stories/story-context-2.2.9.xml` (Generated: 2025-10-25)

### Agent Model Used

Claude 3.7 Sonnet (claude-sonnet-4-5-20250929)

### Debug Log References

TBD during implementation

### Completion Notes List

TBD during implementation

### File List

**New Files Created:**
- `docs/validation/story-2.9-page-validation.md` (validation worksheet)
- `docs/validation/story-2.9-validation-report.md` (comprehensive report)

**Modified Files:**
- `tests/fixtures/ground_truth.py` (page number corrections)

**Optional Files:**
- `scripts/validate-ground-truth-pages.py` (automated validation script, optional)

---

**Story Status:** Ready for Development
**Story Owner:** TBD (assign to dev agent)
**Priority:** CRITICAL (blocks Story 2.11 combined validation)
**Estimated Effort:** 3-4 hours
**Epic:** Epic 2 - Phase 2A Course Correction

**Created:** 2025-10-25 (Scrum Master - Bob)
**Source:** PM Sprint Change Handoff (2025-10-25) + Epic 2 PRD

---

## Change Log

### Version 1.0 - 2025-10-25

- Initial story creation based on Epic 2 PRD (Story 2.9 specification)
- Root cause: Incorrect ground truth page references block accuracy validation
- Solution: Manual validation and correction of all 50 page references
- Expected impact: Unblock Story 2.11 (combined accuracy validation)
- Part of 4-story course correction sequence (Stories 2.8-2.11)
- Estimated effort: 3-4 hours (2h validation + 1h updates + 30-60min docs)
- Created by: Scrum Master (Bob) via BMAD workflow execution
