# Epic 1 Stakeholder Demo Plan

**Date:** 2025-10-16
**Planner:** John (Product Manager)
**Audience:** Project stakeholders, management
**Duration:** 1 hour presentation
**Status:** PLANNED

---

## Demo Objectives

1. **Showcase Epic 1 achievements** (PDF ingestion, semantic search, MCP integration)
2. **Present baseline metrics** (56% retrieval, 32% attribution, 33ms p50 latency)
3. **Explain Epic 2 rationale** (Why hybrid search needed to reach 90%/95% targets)
4. **Gather stakeholder feedback** on priorities and success criteria

---

## Demo Agenda (60 minutes)

### Part 1: Epic 1 Overview (10 min)

**Slide 1: Project Status**
- Epic 1: Foundation & Accurate Retrieval - COMPLETE
- 17/17 stories delivered (3 weeks, 40% faster than planned)
- All acceptance criteria met, zero technical debt

**Slide 2: Key Deliverables**
- PDF ingestion pipeline (321 chunks from 160-page financial report)
- Vector search (Qdrant + Fin-E5 embeddings)
- MCP server integration (FastMCP)
- Validation framework (50-query ground truth suite)

---

### Part 2: Live Demo (20 min)

**Demo 1: PDF Ingestion (5 min)**
- Show: `scripts/ingest-whole-pdf.py` execution
- Highlight: Table extraction working (Story 1.15 achievement)
- Result: 321 chunks indexed in Qdrant

**Demo 2: MCP Query via Claude Desktop (10 min)**
- Query 1: "What is the variable cost per ton for Portugal Cement?"
- Query 2: "What is the EBITDA IFRS margin for Portugal Cement?"
- Query 3: "What was the EBITDA for Portugal in August 2025?"
- Show: MCP response format, source citations, page attribution

**Demo 3: Validation Dashboard (5 min)**
- Run: `scripts/run-accuracy-tests.py`
- Show: Baseline metrics (56% retrieval, 32% attribution)
- Highlight: Performance excellence (p50=33ms, 99.6% budget remaining)

---

### Part 3: Baseline Metrics Presentation (15 min)

**Slide 3: Accuracy Baseline**
- Retrieval Accuracy: **56.0%** (28/50 queries)
  - Target: 90%+ (NFR6)
  - Gap: 34 percentage points
- Attribution Accuracy: **32.0%** (16/50 queries)
  - Target: 95%+ (NFR7)
  - Gap: 63 percentage points

**Slide 4: Performance Metrics**
- p50 Latency: **33.20ms** (150x better than target)
- p95 Latency: **63.34ms** (237x better than target)
- NFR13 Compliance: ✅ PASS (<10s target)
- Latency Budget Remaining: **99.6%** (9,935ms available for Epic 2)

**Slide 5: What's Working Well**
- ✅ Ingestion: 321 chunks, table data extracted (Story 1.15)
- ✅ Semantic search: Retrieving relevant content (56% shows system works)
- ✅ Performance: Excellent latency (33ms p50)
- ✅ Stability: Zero errors during 50-query test execution

**Slide 6: What Needs Improvement**
- ❌ Page ranking: Correct pages not in top-5 results (32% attribution)
- ❌ Keyword coverage: Missing domain-specific financial terms (56% retrieval)
- ❌ Single-stage semantic search: Insufficient for financial domain precision

---

### Part 4: Epic 2 Plan (10 min)

**Slide 7: Decision Gate Result**
- Path 3: Epic 2 Full Implementation Required
- Justification: Retrieval 56% < 85% AND Attribution 32% < 93%
- Next: Stories 2.1 (Hybrid Search) + 2.2 (Financial Embeddings)

**Slide 8: Epic 2 Prioritization**
- **Priority 1:** Story 2.1 (Hybrid Search)
  - Approach: BM25 + semantic vector fusion
  - Expected: +15-20% retrieval accuracy
  - Addresses: Keyword coverage gaps (44% of failures)

- **Priority 2:** Story 2.2 (Financial Embeddings) - CONDITIONAL
  - Approach: Evaluate Fin-E5 alternatives
  - Expected: +10-15% retrieval accuracy
  - Status: Defer pending Story 2.1 results

**Slide 9: Epic 2 Timeline**
- Preparation Sprint: 1.5-2 days (research, story drafting)
- Story 2.1 Implementation: 2-3 days
- Story 2.2 Implementation: 1-2 days (if needed)
- Total: 5-7 days to reach 80-85% accuracy target

---

### Part 5: Q&A & Feedback (5 min)

**Questions to Ask Stakeholders:**
1. Is 90%/95% accuracy target still appropriate for MVP?
2. Should we continue Epic 2 if 80-85% achieved after Stories 2.1+2.2?
3. Any specific query types or use cases to prioritize in validation?
4. Timeline: Is 5-7 days acceptable for Epic 2 completion?

**Feedback Topics:**
- Success criteria validation
- Priority adjustments
- Additional requirements or constraints

---

## Demo Preparation Checklist

**Technical Setup (30 min before demo):**
- [ ] Qdrant running and accessible
- [ ] 321 chunks ingested (verify via `scripts/inspect-qdrant.py`)
- [ ] MCP server configured in Claude Desktop
- [ ] Sample queries ready (3 queries prepared)
- [ ] Baseline reports available (`baseline-accuracy-report-FINAL.txt`)

**Presentation Materials (1 hour before demo):**
- [ ] Slides created (9 slides total)
- [ ] Backup screenshots of MCP responses (in case live demo fails)
- [ ] Metrics dashboard ready (accuracy charts, latency graphs)
- [ ] Epic 2 plan summary (1-page handout)

**Contingency Plans:**
- If MCP demo fails → Use pre-recorded screenshots
- If Qdrant down → Show ingestion logs and explain architecture
- If accuracy tests fail → Use baseline reports (already generated)

---

## Key Messages

**Message 1: Epic 1 Success**
> "We've built a solid foundation. PDF ingestion works, semantic search is operational, and performance is excellent. The system reliably processes financial documents and returns relevant results."

**Message 2: Accuracy Gap is Expected**
> "56% retrieval accuracy is a realistic baseline for single-stage semantic search on complex financial documents. This is why we designed a decision gate—to determine Epic 2 scope based on real data, not assumptions."

**Message 3: Epic 2 is Data-Driven**
> "Baseline failure analysis shows keyword coverage gaps (44% of failures). Hybrid search (BM25 + semantic) directly addresses this root cause. We expect 15-20% improvement from Story 2.1 alone."

**Message 4: Performance Budget is Healthy**
> "We have 99.6% of our latency budget remaining. Epic 2 enhancements can add 5-10x latency and still meet NFR13 targets. Performance is not a constraint—accuracy is."

---

## Post-Demo Actions

1. **Collect Feedback** (during demo)
   - Document stakeholder questions
   - Note any priority changes or new requirements
   - Capture timeline concerns

2. **Update Epic 2 Plan** (after demo)
   - Adjust success criteria if stakeholder input requires
   - Refine Story 2.1 scope based on feedback
   - Update timeline estimates if needed

3. **Communicate Next Steps** (within 24 hours)
   - Email: Epic 2 preparation sprint kickoff (1.5-2 days)
   - Slack: Story 2.1 drafting complete, ready for implementation
   - Jira: Update Epic 2 status to "In Progress"

---

## Success Criteria

Demo is SUCCESSFUL when:
1. ✅ Stakeholders understand Epic 1 achievements
2. ✅ Baseline metrics (56%/32%) accepted as valid
3. ✅ Epic 2 rationale (hybrid search) understood
4. ✅ Feedback collected on priorities and timeline
5. ✅ Approval to proceed with Epic 2 received

---

## Estimated Effort

- Slide preparation: 30 minutes
- Technical setup: 30 minutes
- Demo execution: 60 minutes
- **Total: 2 hours**

---

**Status:** PLANNED
**Scheduled For:** Before Epic 2 Story 2.1 starts
**Owner:** John (Product Manager)
