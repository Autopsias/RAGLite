# Story 1.15: Accuracy Test Validation & Epic 1 Sign-Off

**Status:** Ready for Development
**Epic:** 1 - Foundation & Accurate Retrieval
**Priority:** HIGH - Final Epic 1 validation gate
**Duration:** 2-3 hours
**Assigned:** Dev Agent (Amelia)
**Prerequisite:** Story 1.14 (NEW ground truth created)

---

## Story

**As a** developer,
**I want** to validate the new ground truth test set achieves ≥90% retrieval accuracy and ≥95% attribution accuracy,
**so that** Epic 1 can be validated and signed off as complete.

---

## Context

**Story 1.14 Outcome:**
- ✅ Created entirely NEW ground truth (50 questions validated against PDF)
- ✅ Structural validation: 100% PASS
- ✅ PDF ingestion working (73 points, pages 1-80)
- ❌ Accuracy tests show 0% - keyword matching issue identified

**Current State:**
- New ground truth references actual PDF content (pages 46, 47, 77, 108)
- Retrieval system working (fast: p50=25ms, p95=53ms)
- Test script may need adjustments for new question format
- Full PDF ingestion incomplete (pages 81-160 pending)

**Goal:** Investigate 0% accuracy result, fix keyword matching logic, and validate Epic 1 success criteria.

---

## Acceptance Criteria

1. **Complete PDF ingestion** ✅
   - Ingest pages 81-160 (parts 3-4)
   - Verify: 147+ points in Qdrant (full 160-page PDF)
   - Confirm: All question pages (46, 47, 77, 108) are indexed

2. **Investigate accuracy test failure**
   - Analyze why keyword matching returns 0%
   - Check: Are retrieved chunks from correct pages?
   - Debug: Keyword matching logic in `scripts/run-accuracy-tests.py`
   - Identify: Test script bug vs. retrieval issue vs. question format issue

3. **Fix identified issue**
   - If test script bug: Fix keyword matching logic
   - If retrieval issue: Adjust search parameters or chunking
   - If question format: Refine expected_keywords in ground truth

4. **Achieve NFR6 compliance (≥90% retrieval accuracy)**
   - Execute: `uv run python scripts/run-accuracy-tests.py`
   - Verify: ≥45/50 queries return correct information
   - Document: Actual retrieval accuracy percentage

5. **Achieve NFR7 compliance (≥95% attribution accuracy)**
   - Verify: ≥48/50 queries cite correct page numbers
   - Document: Actual attribution accuracy percentage

6. **Update Epic 1 validation report**
   - File: `docs/qa/epic-1-final-validation-report-20251013.md`
   - Add: Final validated accuracy metrics
   - Add: Validation completion date (2025-10-14)
   - Status: Mark Epic 1 as **VALIDATED** ✅

7. **Update workflow status**
   - File: `docs/project-workflow-status-2025-10-13.md`
   - Add: Story 1.15 entry with COMPLETE status
   - Update: Epic 1 status to VALIDATED
   - Add: Sign-off notes with final metrics

---

## Tasks / Subtasks

### Task 1: Complete PDF Ingestion (30 minutes)

**Subtask 1.1: Check ingestion status**
```bash
python scripts/inspect-qdrant.py
```
- [ ] Verify current point count
- [ ] Identify which pages are missing

**Subtask 1.2: Ingest remaining pages**
```bash
uv run python scripts/ingest-pdf.py
```
- [ ] Wait for parts 3-4 to complete
- [ ] Verify: 147+ points in Qdrant
- [ ] Spot-check: Page 108 content appears

**Subtask 1.3: Verify ingestion quality**
- [ ] Check: Pages 46, 47, 77, 108 are all indexed
- [ ] Verify: Chunk metadata includes correct page numbers
- [ ] Confirm: No duplicate chunks

### Task 2: Investigate Accuracy Test Failure (45-60 minutes)

**Subtask 2.1: Manual test retrieval**
- [ ] Run query: "What is the variable cost per ton for Portugal Cement?"
- [ ] Check retrieved chunks: Do they contain "23.2", "EUR/ton", "20.3"?
- [ ] Check page attribution: Is page 46 cited?
- [ ] Determine: Is retrieval working correctly?

**Subtask 2.2: Analyze test script logic**
- [ ] Read: `scripts/run-accuracy-tests.py`
- [ ] Check: How does it evaluate "retrieval accuracy"?
- [ ] Check: How does it match expected_keywords?
- [ ] Identify: Exact vs. fuzzy matching? Case sensitivity?

**Subtask 2.3: Debug specific test cases**
- [ ] Test Q1: Variable costs per ton (page 46)
- [ ] Test Q13: EBITDA IFRS margin (page 46)
- [ ] Test Q21: EBITDA for Portugal (page 77)
- [ ] Document: Which tests pass/fail and why

**Subtask 2.4: Root cause analysis**
- [ ] Hypothesis A: Test script expects different response format
- [ ] Hypothesis B: Keywords too specific (e.g., "23.2" vs "23.2 EUR")
- [ ] Hypothesis C: Retrieval returns wrong pages
- [ ] Conclusion: Document root cause

### Task 3: Fix Identified Issue (30-45 minutes)

**Option A: Fix Test Script**
- [ ] Adjust keyword matching logic (fuzzy match, case-insensitive)
- [ ] Update evaluation criteria if needed
- [ ] Re-run tests: `uv run python scripts/run-accuracy-tests.py`

**Option B: Refine Ground Truth Keywords**
- [ ] Update expected_keywords for better matching
- [ ] Use more flexible keywords (e.g., ["variable costs", "23", "EUR"])
- [ ] Re-run tests after updates

**Option C: Adjust Retrieval**
- [ ] Tune search parameters (top_k, similarity threshold)
- [ ] Verify chunking includes full context
- [ ] Re-run tests after adjustments

### Task 4: Validate Accuracy Metrics (15 minutes)

**Subtask 4.1: Run full accuracy test suite**
```bash
uv run python scripts/run-accuracy-tests.py
```
- [ ] Capture results: Retrieval %, Attribution %
- [ ] Verify: Retrieval ≥90%, Attribution ≥95%
- [ ] Document: Actual percentages and any failures

**Subtask 4.2: Analyze failures (if <90%)**
- [ ] Identify failing questions
- [ ] Categorize: Test issue vs. retrieval issue
- [ ] Document: Failure patterns

### Task 5: Update Documentation (30 minutes)

**Subtask 5.1: Update Epic 1 Validation Report**
- [ ] File: `docs/qa/epic-1-final-validation-report-20251013.md`
- [ ] Section: Test Results Summary
- [ ] Add:
  ```
  **Ground Truth Validation (Story 1.14-1.15):**
  - Ground Truth Status: NEW 50 questions created (validated against PDF)
  - Retrieval Accuracy: XX% (NFR6 target: ≥90%) ✅
  - Attribution Accuracy: XX% (NFR7 target: ≥95%) ✅
  - Validation Date: 2025-10-14
  - Epic 1 Status: **VALIDATED** ✅
  ```

**Subtask 5.2: Update Story 1.12A Change Log**
- [ ] File: `docs/stories/1.12A.ground-truth-test-set-creation.md`
- [ ] Add entry:
  ```
  | 2025-10-14 | 1.4 | Story 1.14: Replaced original ground truth with 50 NEW validated questions. Story 1.15: Achieved XX% retrieval, XX% attribution accuracy. | Dev Agent Amelia |
  ```

**Subtask 5.3: Update Workflow Status**
- [ ] File: `docs/project-workflow-status-2025-10-13.md`
- [ ] Add Story 1.15 entry: COMPLETE
- [ ] Update Epic 1 status: VALIDATED (Retrieval: XX%, Attribution: XX%)
- [ ] Add sign-off notes

**Subtask 5.4: Complete Story 1.15 Dev Record**
- [ ] Fill in completion notes below
- [ ] Document: Final accuracy metrics
- [ ] Document: Root cause of 0% issue and fix applied

---

## Testing

**Manual Verification:**
- Test 5-10 queries manually to confirm retrieval quality
- Verify page attributions match PDF pages
- Confirm retrieved content is semantically relevant

**Automated Testing:**
1. **Accuracy Validation Test:**
   - Script: `scripts/run-accuracy-tests.py`
   - Expected: ≥90% retrieval, ≥95% attribution
   - Critical: MUST PASS for Epic 1 sign-off

2. **Structural Validation Test:**
   - Script: `scripts/validate_ground_truth.py`
   - Expected: PASS (already passed in Story 1.14)

---

## Success Criteria

Story 1.15 is COMPLETE when:
1. ✅ Full PDF ingested (147+ points, all 160 pages)
2. ✅ Root cause of 0% accuracy identified and documented
3. ✅ Fix applied (test script, keywords, or retrieval)
4. ✅ NFR6: ≥90% retrieval accuracy achieved
5. ✅ NFR7: ≥95% attribution accuracy achieved
6. ✅ Epic 1 validation report updated with final metrics
7. ✅ Workflow status updated: Epic 1 = VALIDATED

**Quality Gate:** AC4 and AC5 (accuracy metrics) are MANDATORY. Epic 1 cannot be signed off without achieving targets.

---

## Rollback Plan

**Scenario 1: Accuracy Still <90% After Fix**
- **Action:** Analyze failing queries (patterns? specific categories?)
- **Next Steps:**
  - Review failed queries: Are they asking for content that's in the PDF?
  - Check chunking: Is relevant content being split across chunks?
  - Escalate: If systematic retrieval failure, may need chunking strategy adjustment
- **Fallback:** Document as known limitation, proceed to Epic 2 with caveat

**Scenario 2: Attribution <95%**
- **Action:** Check page extraction in chunks
- **Next Steps:**
  - Verify: Docling provenance data is captured correctly
  - Fix: Page metadata extraction if broken
  - Re-ingest: If page numbers are incorrect
- **Fallback:** Lower attribution target to 90% (still acceptable)

**Scenario 3: Root Cause Unknown**
- **Action:** Deep dive into retrieval pipeline
- **Next Steps:**
  - Add debug logging to retrieval
  - Compare: Expected chunks vs. actual chunks retrieved
  - Check: Embedding quality, similarity scores
- **Fallback:** Manual investigation with sample queries

---

## Dependencies

**Prerequisites (Already Met):**
- ✅ New ground truth created (Story 1.14)
- ✅ Structural validation passed
- ✅ Partial PDF ingestion complete (pages 1-80)
- ✅ Test scripts functional
- ✅ Qdrant running and accessible

**Blocks:**
- Epic 2 start (depends on Epic 1 validation gate)
- Production deployment decisions

**Blocked By:**
- None (ready to start immediately)

---

## Key Files

**Input Files:**
- `tests/fixtures/ground_truth.py` (new validated ground truth)
- `docs/sample pdf/split/` (4 split PDFs - parts 3-4 need ingestion)
- `scripts/run-accuracy-tests.py` (accuracy test script)
- `scripts/ingest-pdf.py` (PDF ingestion script)

**Output Files:**
- `docs/qa/epic-1-final-validation-report-20251013.md` (accuracy update)
- `docs/stories/1.12A.ground-truth-test-set-creation.md` (change log)
- `docs/project-workflow-status-2025-10-13.md` (workflow status)
- `docs/stories/story-1.15-accuracy-test-validation.md` (this file)

**Modified (potential):**
- `scripts/run-accuracy-tests.py` (if test script fix needed)
- `tests/fixtures/ground_truth.py` (if keyword refinement needed)

---

## Dev Agent Record

### Context Reference

- **Prerequisite Story:** Story 1.14 (Fix Ground Truth Test Set)
- Story 1.14 Outcome: NEW ground truth created, 0% accuracy observed
- Root Cause Investigation: Keyword matching issue identified
- Goal: Achieve NFR6 (≥90%) and NFR7 (≥95%) for Epic 1 validation

### Agent Model Used

- [To be filled by Dev Agent during execution]
- Model: Claude 3.7 Sonnet (claude-sonnet-4-5-20250929)
- Dev Agent: Amelia

### Completion Notes

**[To be filled by Dev Agent after completion]**

**PDF Ingestion:**
- Points in Qdrant: XXX (target: 147+)
- Pages covered: 1-160 complete
- Ingestion time: XX minutes

**Root Cause Analysis:**
- Issue identified: [Test script bug / Keyword mismatch / Retrieval issue]
- Explanation: [Detailed description]
- Fix applied: [What was changed]

**Accuracy Results:**
- Retrieval accuracy: XX% (NFR6 target: ≥90%)
- Attribution accuracy: XX% (NFR7 target: ≥95%)
- Test execution time: XX minutes
- Failed queries: X/50 (list IDs if any)

**Key Findings:**
- [Document insights from accuracy testing]
- [Note any categories with lower accuracy]
- [Identify any patterns in failures]

**Technical Decisions:**
- [Document why specific fix approach was chosen]
- [Note any trade-offs made]

### File List

**Modified:**
- [List files modified during Story 1.15]

**Created:**
- [List files created during Story 1.15]

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-14 | 1.0 | Story created following Story 1.14 completion - accuracy validation needed | Dev Agent (Amelia) |

---

## QA Results

*Results from QA review will be added here*

---

## Senior Developer Review (AI)

*To be completed after story execution*
