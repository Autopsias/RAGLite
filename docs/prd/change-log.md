# PRD Change Log

**Project:** RAGLite - AI-Powered Financial Document Analysis
**Purpose:** Track PRD updates driven by architectural discoveries, implementation learnings, and validation results
**Date:** 2025-10-12

---

## Overview

This change log documents all modifications to the PRD (Product Requirements Document) that occurred after initial creation, particularly changes driven by:
- Week 0 Integration Spike findings
- Architecture design decisions
- Story implementation discoveries
- QA gate feedback

---

## Change History

### 2025-10-04: Story 1.2 Enhancement (Page Number Extraction)

**Source:** Week 0 Spike Report, Integration Issues Document
**Trigger:** Page number extraction blocker identified in Week 0 spike

**Changes Made:**

**File:** `docs/prd/epic-1-foundation-accurate-retrieval.md`

**Story 1.2: PDF Document Ingestion with Docling**

**Added Acceptance Criteria:**
- AC10: 🚨 NEW - PAGE NUMBER EXTRACTION: Page numbers extracted and validated (test with Week 0 PDF, ensure page_number != None)
- AC11: 🚨 NEW - FALLBACK IF NEEDED: IF Docling page extraction fails, implement PyMuPDF fallback for page detection (hybrid approach: Docling for tables, PyMuPDF for pages)
- AC12: 🚨 NEW - DIAGNOSTIC SCRIPT: Run scripts/test_page_extraction.py to diagnose root cause before implementation

**Rationale:**
Week 0 spike discovered Docling page attribution API complexity. Page numbers are critical for NFR7 (95%+ source attribution accuracy). Story 1.2 must resolve this blocker.

**Impact:**
- Blocks Story 1.4 (chunking must preserve page metadata)
- Blocks Story 1.8 (citations require page numbers)
- Critical for NFR7 validation

**Evidence:**
- `docs/week-0-spike-report.md` Section 2.2: "Page number extraction failed"
- `docs/integration-issues.md` DATA-001: CRITICAL severity issue
- `docs/qa/gates/0.1-week-0-integration-spike.yml`: Workaround implemented, production fix needed

---

### 2025-10-04: Story 1.4 Enhancement (Page Number Preservation)

**Source:** Week 0 Spike learnings, Story 1.2 page extraction requirements

**Changes Made:**

**File:** `docs/prd/epic-1-foundation-accurate-retrieval.md`

**Story 1.4: Document Chunking & Semantic Segmentation**

**Added Acceptance Criteria:**
- AC8: 🚨 NEW - PAGE NUMBER PRESERVATION: Chunk metadata MUST include page_number (validate != None for all chunks)
- AC9: 🚨 NEW - PAGE NUMBER VALIDATION: Unit test verifies page numbers preserved across chunking pipeline (ingestion → chunking → Qdrant storage)

**Rationale:**
Page numbers must flow through entire pipeline: ingestion → chunking → vector storage → retrieval responses. Story 1.4 chunking must preserve page metadata from Story 1.2 ingestion.

**Impact:**
- Depends on Story 1.2 (page numbers must exist before chunking)
- Enables Story 1.8 (citations need page numbers)
- Critical for NFR7 (source attribution accuracy)

---

### 2025-10-03: Story 1.11 Architecture Change (MCP Response Format)

**Source:** MCP architecture best practices, cost optimization

**Changes Made:**

**File:** `docs/prd/epic-1-foundation-accurate-retrieval.md`

**Story 1.11: Enhanced Chunk Metadata & MCP Response Formatting**

**ARCHITECTURE CHANGE:** Story originally titled "Answer Synthesis & Response Generation" with Claude API integration for answer synthesis.

**Deprecated Approach:**
- RAGLite calls Claude API to synthesize answers
- RAGLite MCP tools return synthesized text responses

**New Approach (Standard MCP Pattern):**
- RAGLite MCP tools return RAW chunks + metadata (scores, text, citations)
- Claude Code (LLM client) synthesizes coherent answers from chunks

**Rationale:**
1. **Standard MCP Architecture:** Follows official MCP pattern where tools return data, LLM client synthesizes
2. **Cost-Effective:** User already has Claude Code subscription (no additional Claude API costs for RAGLite)
3. **Flexible:** Works with any MCP-compatible LLM client (not locked to Claude)

**Updated Acceptance Criteria:**
- AC1: MCP tool response includes comprehensive chunk metadata (score, text, source_document, page_number, chunk_index, word_count)
- AC2: Response format follows Week 0 spike pattern (QueryResponse with list of QueryResult objects)
- AC3: Metadata validation - All required fields populated (no None values for critical fields)
- AC4: Response JSON structure optimized for LLM synthesis (clear, consistent field names)
- AC5: Integration with Story 1.8 (Source Attribution) - citations include all necessary data
- AC6: Testing - Verify LLM client (Claude Code) can synthesize accurate answers from returned chunks
- AC7: Performance - Response generated in <5 seconds for standard queries (NFR13)
- AC8: Unit tests cover response formatting and metadata validation

**Impact:**
- Removes Claude API dependency from RAGLite
- Simplifies architecture (no answer synthesis in server)
- Reduces operational costs (user pays for Claude Code, not RAGLite API calls)
- Improves flexibility (works with any MCP client)

**Evidence:**
- MCP Protocol Documentation: Tools return structured data, clients synthesize
- Architecture best practice: Separation of concerns (data retrieval vs synthesis)

---

### 2025-10-03: Story 0.2 Deprecation (API Setup)

**Source:** Architecture alignment, standard MCP pattern adoption

**Changes Made:**

**File:** `docs/prd/epic-1-foundation-accurate-retrieval.md`

**Story 0.2: API Account & Cloud Infrastructure Setup**

**Status:** 🗑️ DEPRECATED - NOT NEEDED FOR STANDARD MCP ARCHITECTURE

**Reason for Removal:**

Story originally required:
- Anthropic Claude API account (for RAGLite to call Claude for answer synthesis)
- AWS account (conditional)
- Qdrant Cloud account (Phase 4 only)

**Architecture Change:**
RAGLite now follows **standard MCP pattern**:
- RAGLite MCP tools return: Raw chunks + metadata (no synthesis)
- Claude Code (LLM client) synthesizes: Coherent answers from chunks

**Result:**
No Claude API account needed for RAGLite because:
1. User already has Claude Code subscription
2. LLM client (Claude Code) handles synthesis
3. RAGLite only retrieves and returns data

**What's Still Needed (No Story Required):**
- ✅ Local Qdrant via Docker Compose (already configured in Story 0.0)
- ✅ `.env.example` for future Phase 4 cloud credentials (can be added in Story 1.1 if needed)
- ⏭️ AWS/Qdrant Cloud accounts deferred to Phase 4 (production deployment)

**Impact:**
- Simplifies Phase 1 setup (no API accounts needed)
- Reduces costs (no Claude API usage in RAGLite)
- Accelerates development (one less setup dependency)

---

### 2025-10-03: Story 1.12 Split (Ground Truth Creation vs Validation)

**Source:** Development workflow optimization, risk mitigation

**Changes Made:**

**File:** `docs/prd/epic-1-foundation-accurate-retrieval.md`

**Original:** Story 1.12 - Ground Truth Validation (Week 5 only)

**Split Into:**
1. **Story 1.12A: Ground Truth Test Set Creation** (Week 1)
2. **Story 1.12B: Continuous Accuracy Tracking & Final Validation** (Week 5)

**Rationale:**

**Problem:** Week 0 had only 15 queries (too small for robust validation). Creating 50+ queries in Week 5 causes last-minute rush.

**Solution:**
- **Story 1.12A (Week 1):** Create 50+ query test set early
- **Story 1.12B (Week 5):** Run validation with existing test set

**Benefits:**
1. **Daily Tracking:** Enable accuracy monitoring throughout Phase 1 (catch regressions early)
2. **Risk Mitigation:** 50+ query test set ready by Week 1 prevents Week 5 bottleneck
3. **Continuous Improvement:** Track accuracy trend line (Week 1: 70% → Week 5: 90%+)
4. **Early Warning System:** If accuracy drops below 70% mid-phase, HALT and debug

**Story 1.12A Details:**
- Duration: 4-6 hours
- Week: Week 1 (after Story 1.1)
- Deliverables: 50+ Q&A pairs in `raglite/tests/ground_truth.py`
- Categories: cost_analysis, margins, financial_performance, safety_metrics, workforce, operating_expenses
- Difficulty: 40% easy, 40% medium, 20% hard

**Story 1.12B Details:**
- Duration: 2-3 days
- Week: Week 5 (after all Stories 1.1-1.11 complete)
- Dependencies: Story 1.12A (test set must exist)
- Deliverables: Validation report, accuracy metrics, decision gate recommendation

**Impact:**
- Enables daily/weekly accuracy tracking
- Prevents Week 5 test creation bottleneck
- Provides early warning for accuracy issues

---

## Summary Statistics

**Total PRD Changes:** 5 major updates
**Stories Enhanced:** 4 (Story 1.2, 1.4, 1.11, 1.12)
**Stories Deprecated:** 1 (Story 0.2)
**Stories Created:** 1 (Story 1.12A split from 1.12)

**Change Categories:**
- Architecture-driven: 2 (Story 1.11 MCP pattern, Story 0.2 deprecation)
- Week 0 findings: 2 (Story 1.2 page extraction, Story 1.4 page preservation)
- Development workflow: 1 (Story 1.12 split)

**Impact Summary:**
- ✅ Simplified architecture (standard MCP pattern)
- ✅ Reduced costs (no Claude API in RAGLite)
- ✅ Improved quality (page number extraction addressed)
- ✅ Better tracking (daily accuracy monitoring)
- ✅ Risk mitigation (early test set creation)

---

## Future Change Management

**Process:**
1. **Source Tracking:** Document what triggered the change (spike findings, QA feedback, architecture decision)
2. **Impact Analysis:** Assess dependencies and downstream effects
3. **Update PRD:** Modify affected stories/requirements
4. **Update Change Log:** Record change with rationale and evidence
5. **Notify Stakeholders:** Communicate significant changes

**Change Approval:**
- Minor enhancements (AC additions): Product Owner approval
- Architecture changes: Product Owner + Architect approval
- Story deprecation: Product Owner + Scrum Master approval

---

**Document Version:** 1.0
**Created:** 2025-10-12
**Author:** Sarah (Product Owner)
**Next Update:** After Story 1.2 completion or Phase 1 Week 5 validation
