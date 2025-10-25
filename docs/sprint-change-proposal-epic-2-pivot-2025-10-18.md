# Sprint Change Proposal: Epic 2 Pivot to Element-Based RAG Enhancement

**Date:** 2025-10-18
**Trigger:** Story 2.1 Failed AC6 Validation (56% vs ≥70% target)
**Analyst:** Scrum Master (Bob)
**Status:** ✅ **APPROVED** by Ricardo (2025-10-18)
**Mode:** Batch Analysis

---

## Executive Summary

Story 2.1 (BM25 Hybrid Search) failed AC6 validation, achieving only **56% retrieval accuracy** against a ≥70% target. Root cause analysis revealed that **whitespace tokenization is fundamentally inadequate for financial documents** containing complex tables.

**DECISION:** PIVOT to element-based chunking approach with 3-phase sequential implementation:
1. **Story 2.2** (Element Chunking): 56% → 64-68% (+8-12pp, 1 week, LOW risk)
2. **Story 2.3** (Query Preprocessing): 68% → 74-76% (+6-8pp, 2 weeks, MEDIUM risk)
3. **Story 2.4** (Table Summarization): 74% → 78-80% (+4-6pp, 3 weeks, MEDIUM risk)

**RECOMMENDATION:** ✅ **APPROVED** - Research-backed, low-risk, incremental approach with decision gates

---

## 1. Issue Summary

### Triggering Story
Story 2.1 - Hybrid Search (BM25 + Semantic Fusion)

### Problem Statement
Story 2.1 (BM25 Hybrid Search) failed AC6 validation, achieving only **56% retrieval accuracy** against a ≥70% target. Root cause analysis revealed that **whitespace tokenization is fundamentally inadequate for financial documents** containing complex tables.

### Evidence
- ✅ Implementation complete: 13 unit tests passing, 4 integration tests created
- ❌ Validation results (2025-10-18): 56.0% retrieval accuracy (UNCHANGED from baseline)
- ⚠️ Attribution accuracy: 40.0% (+8pp improvement over 32% baseline, but insufficient)
- ✅ Performance: p50=50ms, p95=90ms (within NFR13 <10,000ms limit)

### Root Cause (Technical)
1. **Number/Unit Tokenization**: "23.2 EUR/ton" splits incorrectly with whitespace tokenization
2. **Table Structure Destruction**: Markdown tables become linear token streams, losing semantic coherence
3. **Length Normalization Bias**: Short chunks (confidentiality notices) artificially inflate BM25 scores
4. **Financial Term Sensitivity**: "EBITDA" ≠ "ebitda" ≠ "Ebitda" breaks matching
5. **Low BM25 Coverage**: Most queries matched only 6-8% of documents (non-zero BM25 scores)

---

## 2. Epic & Artifact Impact Analysis

### Epic 2 Impact

**Can Epic 2 Be Completed As Planned?**
✅ **YES** - with significant strategy pivot

**Required Modifications:**

| Component | Status | Change Required |
|-----------|--------|----------------|
| **OLD Story 2.1** (BM25 Hybrid Search) | ❌ FAILED | Mark as CLOSED/PIVOT with lessons learned |
| **OLD Story 2.2** (Financial Embeddings) | ⏸️ DEFERRED | Mark as CONDITIONAL (may revisit if element approach insufficient) |
| **NEW Story 2.2** (Element Chunking) | ✅ DRAFTED | Implement as Phase 1 (56%→64-68%, 1 week, LOW risk) |
| **NEW Story 2.3** (Query Preprocessing) | 📋 PLANNED | Implement as Phase 2 (68%→74-76%, 2 weeks, MEDIUM risk) |
| **NEW Story 2.4** (Table Summarization) | 📋 PLANNED | Implement as Phase 3 (74%→78-80%, 3 weeks, MEDIUM risk) |

**Impact on Future Epics:**
- Epic 3 (Intelligence Features): ✅ NOT affected - still depends on Epic 2 reaching ≥70%
- Epic 4 (Production Readiness): ✅ NOT affected
- Epic 5 (Real-Time Operations): ✅ NOT affected

**Epic Priority/Sequencing:** ✅ UNCHANGED - Epic 2 remains Phase 2

### PRD Conflicts & Updates Required

**File:** `docs/prd/epic-2-advanced-rag-enhancements.md`

**Conflicts Identified:**
1. ❌ Story Descriptions Outdated (2.1, 2.2)
2. ❌ Expected Progression Mismatch (assumed 90%+, actual 56%)
3. ❌ Decision Gates Invalid (thresholds assume 90%+ start)
4. ✅ Core Goals Still Valid (95-98% target, sequential implementation)

**PRD Updates Executed:**
- ✅ Updated Expected Progression: 56% → 64% → 74% → 78%
- ✅ Updated Story 2.1: Added FAILED status with lessons learned
- ✅ Replaced Story 2.2: Element-Based Chunking (was Financial Embeddings)
- ✅ Added NEW Stories 2.3-2.4: Query Preprocessing + Table Summarization
- ✅ Updated Decision Gates Summary: NEW vs OLD progression tables
- ✅ Archived OLD Stories 2.3-2.6 as Phase 3+ conditional

### Architecture Document Impact

**Files:** `docs/architecture/*.md`

**Conflicts:** ✅ **MINIMAL** - Changes are implementation details, not architectural

**Data Model Additions Required:**
```python
# raglite/shared/models.py (NEW)
class ElementType(str, Enum):
    TABLE = "table"
    SECTION_HEADER = "section_header"
    PARAGRAPH = "paragraph"
    LIST = "list"
    MIXED = "mixed"

@dataclass
class Chunk:
    # ... existing fields ...
    element_type: ElementType = ElementType.MIXED  # NEW
    section_title: Optional[str] = None            # NEW
    parent_chunk_id: Optional[str] = None         # NEW (for Story 2.4)
```

**Technology Stack Verification:**
- ✅ Element chunking: Uses **Docling** (already approved)
- ✅ Query preprocessing: **No new dependencies**
- ✅ Table summarization: Uses **Claude 3.7 Sonnet API** (already approved)
- ✅ **ZERO new dependencies** outside approved stack

---

## 3. Path Forward Evaluation

### Option 1: Direct Adjustment (Implement NEW Stories 2.2-2.4) ✅ SELECTED

**Approach:** Add NEW element-based stories within Epic 2 structure

**Feasibility:** ✅ **HIGHLY VIABLE**
- Timeline: 6 weeks (1 week + 2 weeks + 3 weeks)
- Effort: MEDIUM (well-scoped, research-backed)
- Risk: LOW-MEDIUM (Phase 1 is LOW, Phases 2-3 are MEDIUM)
- Maintains project momentum: Team pivots with clear direction

**Pros:**
- ✅ Research-backed approach (Jimeno Yepes et al. 2024: +16pp page-level recall)
- ✅ Leverages existing Docling infrastructure (minimal new code)
- ✅ Incremental with decision gates (can stop early if targets met)
- ✅ Technology stack compliant (ZERO new dependencies)
- ✅ Clear success metrics at each phase

**Cons:**
- ⚠️ 6-week timeline (vs original 4-6 hours for Story 2.1)
- ⚠️ Requires comprehensive testing at each phase
- ⚠️ Phase 3 (table summarization) has API costs (~$0.60/document)

### Option 2: Potential Rollback

**Status:** ❌ **NOT VIABLE** - Nothing to roll back (Story 2.1 is first Epic 2 story)

### Option 3: PRD MVP Review (Reduce Scope)

**Status:** ⚠️ **PARTIAL** - Can update PRD, but scope reduction NOT recommended
- ❌ Doesn't solve the fundamental problem (poor retrieval accuracy)
- ❌ Epic 3 (Intelligence Features) requires ≥70% accuracy to be useful
- ❌ Undermines project value proposition (accurate financial document RAG)

---

## 4. Recommended Path & Rationale

**Selected Approach:** **HYBRID of Option 1 + Option 3 (Documentation Update)**

**Execute:**
1. ✅ Implement NEW Stories 2.2-2.4 (element-based chunking → query preprocessing → table summarization)
2. ✅ Update Epic 2 PRD to document pivot and reset baseline expectations
3. ✅ Maintain full accuracy targets (no scope reduction)

**Rationale:**

| Criterion | Assessment | Weight | Score |
|-----------|------------|--------|-------|
| **Research Evidence** | Strong empirical backing from 3 academic papers (2024-2025) | HIGH | 9/10 |
| **Technical Risk** | LOW for Phase 1, MEDIUM for Phases 2-3; manageable with decision gates | HIGH | 8/10 |
| **Implementation Effort** | 6 weeks total; incremental phases allow early exit if successful | MEDIUM | 7/10 |
| **Technology Stack Compliance** | Perfect - ZERO new dependencies, all within approved stack | HIGH | 10/10 |
| **Team Morale & Momentum** | Data-driven pivot shows professional decision-making | MEDIUM | 8/10 |
| **Business Value** | Clear path to 70%+ accuracy with high probability of success | HIGH | 9/10 |
| **Long-term Sustainability** | Element-based chunking is foundational - benefits ALL future work | HIGH | 9/10 |

**Weighted Score:** **8.7/10** (Strong recommendation)

**Key Success Factors:**
1. **Academic Validation:** Jimeno Yepes et al. (2024) showed +16.3pp page-level recall with element-based chunking on SEC filings
2. **Industry Validation:** Kim et al. (ICLR 2025) achieved 56%→72% with retrieval optimization alone
3. **Financial Domain Fit:** Table-to-text summarization (Min et al. 2024) specifically addresses complex financial tables
4. **Incremental Risk Management:** 3-phase approach with decision gates allows early exit

---

## 5. Detailed Change Proposals

### Proposal 1: Update Epic 2 PRD ✅ COMPLETED

**File:** `docs/prd/epic-2-advanced-rag-enhancements.md`

**Changes Executed:**
- ✅ Updated Expected Progression (lines 23-28)
- ✅ Updated Story 2.1 title and added FAILED status (lines 38-54)
- ✅ Replaced Story 2.2 completely (lines 118-187)
- ✅ Added NEW Story 2.3 (Query Preprocessing) (lines 191-230)
- ✅ Added NEW Story 2.4 (Table Summarization) (lines 234-273)
- ✅ Added "ARCHIVED STORIES" section (line 277)
- ✅ Updated Decision Gates Summary (lines 546-569)

### Proposal 2: Archive OLD Story 2.2 (Financial Embeddings) ✅ COMPLETED

**File:** `docs/stories/story-2.2-financial-embeddings-evaluation.md`

**Changes Executed:**
- ✅ Updated header: Status changed to "DEFERRED TO PHASE 3+"
- ✅ Added deferral notice with full context
- ✅ Explained new priority order (NEW Stories 2.2-2.4 take precedence)
- ✅ Defined revisit conditions (only if NEW stories insufficient)
- ✅ Marked original content as "FOR REFERENCE ONLY"

### Proposal 3: No Changes to Story 2.2 Element Chunking ✅ APPROVED

**File:** `docs/stories/story-2.2-element-chunking.md`

**Status:** ✅ **APPROVED AS-IS** - Comprehensive 1,144-line specification ready for implementation

### Proposal 4: Update Backlog Status ✅ ALREADY CURRENT

**File:** `docs/backlog.md`

**Status:** ✅ **NO ACTION REQUIRED** - Backlog reflects NEW Stories 2.2-2.4 (updated 2025-10-18)

---

## 6. PRD MVP Impact & Action Plan

### MVP Impact Assessment

**Q: Is the original PRD MVP still achievable?**

**A:** ✅ **YES** - with adjusted timeline and strategy

**Original MVP Goal:**
- 90%+ retrieval accuracy (NFR6)
- 95%+ source attribution accuracy (NFR7)
- <10s query response time (NFR13)

**Reality Check:**
- Current baseline: 56% retrieval, 40% attribution
- Epic 2 (old plan): Assumed 90% starting point → target 95%+
- Epic 2 (new plan): Starting from 56% → target 70-80% → continue if needed

**MVP Adjustment:**
- **Phase 1 Goal:** 70-80% accuracy (vs original 90%+)
- **Rationale:** 56% baseline reveals original assumptions were too optimistic
- **Decision:** If Stories 2.2-2.4 reach 78-80%, reassess if 90%+ is needed for MVP or can be deferred to Phase 3

**Timeline Impact:**
- **Original Epic 2:** 4-10 weeks (assumed 2-3 stories)
- **NEW Epic 2:** 6 weeks (3 stories × 1-3 weeks each)
- **Overall Project:** Still within Phase 2 scope (Weeks 5-12)

### High-Level Action Plan

**Phase 1: Immediate Actions** (This Week) ✅ COMPLETED
1. ✅ User Approval (Ricardo): Sprint Change Proposal approved
2. ✅ PRD Update (SM): Epic 2 PRD updated with pivot documentation
3. ✅ Story Archive (SM): OLD Story 2.2 marked as DEFERRED
4. ⏭️ **NEXT:** Handoff to Dev (SM→Dev): Assign NEW Story 2.2 to Dev Agent

**Phase 2: Story 2.2 Implementation** (Week 1, Days 1-7)
- Day 1-2: Data models & element extraction
- Day 3-4: Smart chunking algorithm
- Day 5: Qdrant integration
- Day 6-7: End-to-end validation & accuracy testing

**Phase 3: Decision Gate 1** (End of Week 1)
- Run 50-query ground truth test suite
- **IF ≥68%:** Proceed to Story 2.3 with high confidence
- **IF 64-68%:** Proceed to Story 2.3 with caution
- **IF <64%:** ESCALATE to PM for strategy review

**Phase 4: Story 2.3 Implementation** (Weeks 2-3, conditional on Gate 1)
- Week 2: Query preprocessing module
- Week 3: Metadata-aware search & chunk bundling
- Validation & Decision Gate 2

**Phase 5: Story 2.4 Implementation** (Weeks 4-6, conditional on Gate 2)
- Week 4-5: Table detection & LLM summarization
- Week 6: Dual chunk ingestion & validation
- Final Decision Gate 3

---

## 7. Agent Handoff Plan

| Role | Agent | Responsibilities | Timeline |
|------|-------|-----------------|----------|
| **Product Owner / Scrum Master** | Bob (SM) | ✅ Update Epic 2 PRD (COMPLETED)<br>✅ Archive OLD Story 2.2 (COMPLETED)<br>✅ Manage backlog<br>⏭️ Facilitate decision gates | This week + gates |
| **Development Team** | Dev Agent (Amelia) | ⏭️ Implement Story 2.2 (Element Chunking)<br>⏭️ Execute test plan<br>⏭️ Report accuracy results at Decision Gate 1<br>⏭️ Implement Stories 2.3-2.4 if approved | Weeks 1-6 |
| **Product Manager / Architect** | PM/Architect | ⏸️ ESCALATION ONLY: If Story 2.2 <64% accuracy<br>⏸️ Review Epic 2 strategy if needed | As needed |
| **QA / Test Architect** | Murat (QA) | ⏭️ Review element chunking test strategy<br>⏭️ Validate ground truth test suite<br>⏭️ Track accuracy trend line | Weeks 1-6 |
| **User (Ricardo)** | Ricardo | ✅ APPROVED Sprint Change Proposal<br>⏭️ Monitor progress at decision gates<br>⏭️ Final sign-off on accuracy targets | This week + gates |

---

## 8. Success Criteria & Risks

### Success Criteria

**Sprint Change Proposal Approved:** ✅ **COMPLETE**
- ✅ Ricardo approved pivot to element-based chunking approach
- ✅ Epic 2 PRD updated to reflect new strategy
- ⏭️ NEW Story 2.2 ready for assignment to Dev Agent

**Epic 2 Success** (Overall):
- ✅ Retrieval accuracy ≥70% (minimum MVP threshold)
- ✅ Retrieval accuracy ≥78-80% (target with 3-phase approach)
- ✅ Attribution accuracy ≥50%+ (maintaining improvement trend)
- ✅ p95 latency <10,000ms (NFR13 compliance)
- ✅ Technology stack unchanged (no new dependencies)

**Story 2.2 Success** (Phase 1):
- ✅ Retrieval accuracy ≥64% (minimum viable) or ≥68% (stretch)
- ✅ Element boundaries respected (no mid-table/mid-section splits)
- ✅ Chunk metadata enhanced (`element_type`, `section_title`)
- ✅ Performance maintained (ingestion ≤30s per 100 pages)

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Story 2.2 <64% accuracy** | LOW (20%) | HIGH | Research strongly supports element approach; if occurs, escalate to PM for alternative strategy |
| **Docling element API limitations** | LOW (15%) | MEDIUM | Fallback: Parse Markdown output with regex (lower quality but functional) |
| **Large tables >2,048 tokens** | MEDIUM (40%) | MEDIUM | Split at row boundaries; validated in research (Jimeno Yepes approach) |
| **Timeline extension beyond 6 weeks** | LOW (25%) | MEDIUM | Incremental approach allows early exit if targets met |
| **API costs for Story 2.4** | LOW (10%) | LOW | Estimated $0.60/document (well within budget); can optimize if needed |
| **Team morale from pivot** | LOW (15%) | MEDIUM | Transparent communication; data-driven decision shows professionalism |

---

## 9. References

**Research Foundation:**
1. Jimeno Yepes et al. (2024) - arXiv:2402.05131 - Element-based chunking on SEC filings: +16.3pp page-level recall
2. Kim et al. (ICLR 2025 Workshop) - arXiv:2503.15191 - Retrieval optimization: 56%→72% on financial Q&A
3. Min et al. (NAACL 2024) - ACL Anthology - Table-to-text methods: +9pp RAG human score

**Project Documents:**
- `docs/stories/story-2.1-hybrid-search.md` - Failed Story 2.1 with comprehensive validation results
- `docs/stories/story-2.2-element-chunking.md` - NEW Story 2.2 specification (1,144 lines)
- `docs/epic-2-preparation/table-aware-rag-comprehensive-research-2025.md` - Exa Deep Research (259s)
- `docs/epic-2-preparation/implementation-plan-stories-2.2-2.4.md` - Detailed 3-phase plan
- `docs/backlog.md` - Updated backlog with NEW Stories 2.2-2.4

---

## 10. Approval & Sign-off

**Prepared By:** Bob (Scrum Master)
**Date:** 2025-10-18
**Status:** ✅ **APPROVED**

**Approved By:** Ricardo (Product Owner)
**Approval Date:** 2025-10-18
**Approval Decision:** APPROVED - Proceed with NEW Stories 2.2-2.4

**Next Actions:**
1. ⏭️ Scrum Master: Assign NEW Story 2.2 to Dev Agent (Amelia)
2. ⏭️ Dev Agent: Begin Story 2.2 implementation (Week 1)
3. ⏭️ All: Monitor Decision Gate 1 at end of Week 1

---

**Document Version:** 1.0
**Last Updated:** 2025-10-18
**Location:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/sprint-change-proposal-epic-2-pivot-2025-10-18.md`
