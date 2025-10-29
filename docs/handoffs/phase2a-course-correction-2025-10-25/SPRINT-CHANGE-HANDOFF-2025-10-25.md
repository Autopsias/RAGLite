# Sprint Change Handoff - Phase 2A Course Correction

**Date:** 2025-10-25
**Prepared By:** Product Manager (John)
**Approved By:** User (Ricardo)
**Handoff To:** Scrum Master

---

## Executive Summary

**Sprint Change Proposal APPROVED** for Phase 2A Course Correction.

**Issue:** Phase 2A achieved 52% accuracy (vs ≥70% target)
**Root Cause:** 4 critical issues identified via deep-dive analysis
**Solution:** Add 4 new stories (2.8-2.11) before re-validation
**Timeline Impact:** +2-3 days to Epic 2 (acceptable)
**Expected Outcome:** 65-75% accuracy (meets/near-meets Phase 2A target)

---

## Changes Completed (PM)

### ✅ 1. Story Conflict Resolution

**File:** `docs/stories/story-2.8.md` → `docs/stories/story-2.12-cross-encoder-reranking-phase2b.md`

**Action:** Renamed existing Phase 2B story to avoid numbering conflict with course correction stories.

**Justification:** Original story-2.8.md was for Cross-Encoder Re-Ranking (Phase 2B, CONDITIONAL). New stories 2.8-2.11 are Phase 2A course correction (CRITICAL, immediate execution).

---

### ✅ 2. Epic 2 PRD Updates

**File:** `docs/prd/epic-2-advanced-rag-enhancements.md`

**Changes:**

1. **Story 2.5 Status Update** (line 298-306)
   - Marked as FAILED (52% accuracy)
   - Added note about course correction requirement

2. **New Section: Phase 2A Course Correction** (line 365-441)
   - Added 4 new story summaries (2.8-2.11)
   - Story 2.8: Table-Aware Chunking (6-8 hours)
   - Story 2.9: Fix Ground Truth Page References (3-4 hours)
   - Story 2.10: Fix Query Classification (3-4 hours)
   - Story 2.11: Fix Hybrid Search Scoring (4-6 hours)
   - Added Story 2.5 Re-validation section

3. **Phase 2B Update** (line 444-457)
   - Updated status (Stories 2.6-2.7 complete, 2.12-2.13 on hold)
   - Clarified trigger condition (only if course correction <70%)
   - Noted lower probability due to expected course correction success

4. **Timeline Summary Update** (line 537-565)
   - Best case: 3-4 weeks (was 2-3 weeks)
   - Added course correction timeline (+2-3 days)
   - Updated probability analysis (80% success with course correction)

---

## Actions Required (Scrum Master)

### 🔴 CRITICAL - Immediate Actions

**1. Create Story Files (16-22 hours total effort)**

Based on Sprint Change Proposal sections and PRD summaries, create:

- [ ] `docs/stories/story-2.8.md` - Table-Aware Chunking (6-8 hours)
- [ ] `docs/stories/story-2.9.md` - Fix Ground Truth Page References (3-4 hours)
- [ ] `docs/stories/story-2.10.md` - Fix Query Classification (3-4 hours)
- [ ] `docs/stories/story-2.11.md` - Fix Hybrid Search Scoring (4-6 hours)

**Template:** Use existing story format (see story-2.6.md, story-2.7.md for examples)

**Source Material:**
- Sprint Change Proposal: Section 4 (Detailed Change Proposals)
- Epic 2 PRD: Lines 365-441 (story summaries)
- Root Cause Analysis: `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/phase2a-deep-dive-analysis.md`

---

**2. Add Stories to Backlog**

- [ ] Add all 4 stories to sprint backlog
- [ ] Set priority: Story 2.8 (CRITICAL), 2.9 (CRITICAL), 2.10 (HIGH), 2.11 (MEDIUM)
- [ ] Assign to Development Team
- [ ] Set sprint: Current sprint (Week 3-4)

---

**3. Update Sprint Planning**

- [ ] Communicate +2-3 day timeline extension to stakeholders
- [ ] Adjust Epic 2 completion date estimate (Week 3 → Week 4)
- [ ] Update sprint capacity allocation (16-22 hours for course correction)
- [ ] Schedule daily standups to track progress

---

### 🟡 MEDIUM - Follow-Up Actions

**4. Story Context Files** (Optional but Recommended)

Create context XML files for each story (if following existing pattern):
- [ ] `docs/stories/story-context-2.8.xml`
- [ ] `docs/stories/story-context-2.9.xml`
- [ ] `docs/stories/story-context-2.10.xml`
- [ ] `docs/stories/story-context-2.11.xml`

**Note:** These are helpful for development context but not blocking.

---

**5. Update Sprint Status Tracking**

- [ ] Update `docs/sprint-status.yaml` with new stories
- [ ] Mark Stories 2.8-2.11 as "Ready" status
- [ ] Update Epic 2 progress indicators

---

## Implementation Sequence

**Recommended Execution Order:**

1. **Story 2.8** (Day 1 - 6-8 hours) - Table-aware chunking
   - CRITICAL: Blocks accuracy improvement
   - Can run in parallel with Story 2.9

2. **Story 2.9** (Day 1-2 - 3-4 hours) - Ground truth annotation
   - CRITICAL: Enables valid accuracy measurement
   - QA task, can parallel with Story 2.8

3. **Story 2.10** (Day 2 - 3-4 hours) - Query classification fix
   - HIGH: Performance optimization
   - Depends on Stories 2.8-2.9 complete

4. **Story 2.11** (Day 2-3 - 4-6 hours) - Hybrid search scoring
   - MEDIUM: Ranking quality improvement
   - Depends on Stories 2.8-2.9 complete

5. **Story 2.5 RE-VALIDATION** (Day 3 - 4 hours) - Run full AC3 test suite

**Total:** 2-3 days (16-22 hours execution + 4 hours validation)

---

## Success Criteria

**Story-Level Success:**
- ✅ Story 2.8: Chunks per table reduced from 8.6 → 1.2
- ✅ Story 2.9: All 50 queries have page references
- ✅ Story 2.10: SQL routing reduced from 48% → 8%
- ✅ Story 2.11: Hybrid search returns realistic scores (not 1.0)

**Epic-Level Success (After Re-validation):**
- ✅ **Target: ≥70% retrieval accuracy** (Epic 2 complete)
- ✅ Stretch: 65-70% accuracy (re-evaluate Phase 2B necessity)
- ⚠️ Escalation: <65% accuracy (proceed to Phase 2B with PM approval)

---

## Risk Assessment

**Implementation Risks:** LOW
- Fixes are targeted and well-understood
- No architectural changes required
- Builds on completed infrastructure (Stories 2.3-2.7)

**Timeline Risk:** LOW
- 16-22 hours execution (2-3 days)
- No external dependencies
- Parallel execution possible (Stories 2.8-2.9)

**Accuracy Risk:** MEDIUM-LOW
- Expected 65-75% accuracy (research-validated approaches)
- If <70%, Phase 2B path available (already designed)
- 80% probability of avoiding Phase 2B (significant timeline savings: 3-24 weeks)

---

## References

**Sprint Change Proposal:** Full document in PM Agent output (2025-10-25 session)
**Root Cause Analysis:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/phase2a-deep-dive-analysis.md`
**Epic 2 PRD:** `docs/prd/epic-2-advanced-rag-enhancements.md` (updated)
**Story Template:** `docs/stories/story-2.6.md`, `docs/stories/story-2.7.md`

---

## Questions / Clarifications

**For Scrum Master:**
- Do you need PM to provide more detailed story specifications before creation?
- Should we schedule a backlog grooming session for Stories 2.8-2.11?
- Any capacity concerns for the +2-3 day timeline extension?

**Contact:** Product Manager (John) via Slack or email

---

**Handoff Status:** ✅ READY FOR SCRUM MASTER EXECUTION

**Next Steps:**
1. Scrum Master creates 4 story files
2. Scrum Master adds to backlog and assigns to dev team
3. Development team executes Stories 2.8-2.11 (2-3 days)
4. QA runs Story 2.5 re-validation
5. PM reviews results and makes decision gate call (≥70% → Epic 2 complete)

---

**Prepared:** 2025-10-25
**PM Signature:** John (Product Manager)
**User Approval:** Ricardo ✅
