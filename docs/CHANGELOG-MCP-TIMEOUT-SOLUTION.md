# MCP Timeout Solution - Documentation Update

**Date:** 2025-11-07
**Issue:** Large file ingestion (>10 pages) times out via MCP
**Solution Approach:** Option 2 (CLI Ingestion + MCP Query Pattern)

---

## Changes Made

### 1. Code Updates

**File:** `raglite/main.py`
- **Line 51-98:** Updated `ingest_financial_document()` docstring
- **Added:** Performance & timeout considerations section
- **Added:** CLI ingestion instructions for large files
- **Added:** Reference to Epic 4 async job queue enhancement

**File:** `raglite/shared/logging.py` (Earlier fix)
- **Line 28:** Changed `logging.StreamHandler(sys.stdout)` → `sys.stderr`
- **Reason:** MCP protocol requires stdout for JSON-RPC only, logs must go to stderr

---

### 2. Documentation Created

#### A. Future Enhancements Roadmap
**File:** `docs/future-enhancements.md` (NEW)
- **Purpose:** Research roadmap for Epic 4 async ingestion queue
- **Content:**
  - Current limitation analysis
  - 5 research questions for Epic 4 planning
  - Draft stories (4.1-4.4) with acceptance criteria
  - Design constraints (maintain MVP simplicity)
  - Success metrics
- **Audience:** Product team, future sprint planning

#### B. MCP Configuration Guide
**File:** `docs/setup/mcp-configuration.md` (NEW)
- **Purpose:** End-user guide for Claude Desktop integration
- **Content:**
  - Step-by-step configuration instructions
  - Environment variable reference
  - Tool usage examples
  - Troubleshooting common issues
  - Security considerations
- **Audience:** Users setting up RAGLite with Claude Desktop

#### C. README Updates
**File:** `README.md`
- **Line 74:** Added "Known Limitation" note with link to Large File Ingestion
- **Lines 156-213:** Added "Usage" section (NEW)
  - MCP Integration subsection
  - Large File Ingestion subsection with CLI workflow
  - Performance expectations (20-30 sec/page)
  - Future enhancement note

---

## Decision Rationale

### Why Option 2 (CLI + MCP) vs. Async Job Queue?

**MVP Constraints:**
- Target: 600-800 lines total code
- Async job queue: +150-200 lines (25% overhead)
- Violates KISS principle for MVP phase

**Alignment with Architecture:**
- Ingestion: **Batch operation** (do once per document)
- Querying: **Real-time operation** (do many times)
- MCP designed for interactive queries, not 30-minute batch jobs

**Usage Patterns:**
- Large files: Rare, one-time ingestion
- Queries: Frequent, repeated use
- Local dev: Users have CLI access by design

**Epic Roadmap:**
- Epic 1-3: Focus on retrieval accuracy
- Epic 4: Production readiness features (async queue fits here)

---

## User Impact

### Current Workaround

**For Files <10 pages:**
```
# Claude Desktop (MCP)
"Ingest this document: /path/to/small.pdf"
```

**For Files >10 pages:**
```bash
# Terminal (CLI)
cd /path/to/RAGLite
uv run python -c "
import asyncio
from raglite.ingestion.pipeline import ingest_document
asyncio.run(ingest_document('/path/to/large.pdf'))
"

# Then query via Claude Desktop
```

### Future Solution (Epic 4)

```
# Claude Desktop (MCP with async)
"Start ingesting: /path/to/large.pdf"
→ Returns: job_id=abc123, status=pending

"Check ingestion status: abc123"
→ Returns: 45% complete, page 72 of 160

# 30 minutes later...
"Check ingestion status: abc123"
→ Returns: Completed! 160 pages, 342 chunks
```

---

## Testing Performed

### 1. Small File Test (10 pages)
```bash
✅ SUCCESS
File: test-10-pages.pdf
Pages: 10
Chunks: 14
Time: ~3 minutes
```

### 2. Query Test
```bash
✅ SUCCESS
Query: "What is the total revenue?"
Results: 3 chunks
Found: Revenue 497 M EUR, Revenue 488 M EUR
Time: 2.4 seconds
```

### 3. MCP Connection Test
```bash
✅ Claude Desktop connected
✅ 2 tools available
✅ Logs go to stderr (no JSON corruption)
```

---

## Epic 4 Research Questions

Before implementing async ingestion queue, research:

1. **Job Queue Architecture:**
   - Celery + Redis vs. Python threading vs. FastAPI BackgroundTasks?
   - Tradeoff: Complexity vs. features vs. persistence

2. **Progress Tracking:**
   - PostgreSQL jobs table vs. file-based vs. in-memory?
   - How to expose progress to MCP clients?

3. **MCP Async Patterns:**
   - Best practice for long-running operations in MCP?
   - Streaming support in MCP protocol?

4. **Concurrent Ingestion:**
   - Support multiple concurrent jobs? Resource limits?

5. **Error Recovery:**
   - Auto-cleanup vs. manual? Failure log persistence?

---

## Files Modified

```
raglite/main.py                        (docstring update)
raglite/shared/logging.py              (stderr fix - earlier)
README.md                              (usage section added)
docs/future-enhancements.md            (NEW - research roadmap)
docs/setup/mcp-configuration.md        (NEW - user guide)
docs/CHANGELOG-MCP-TIMEOUT-SOLUTION.md (NEW - this file)
```

---

## Next Steps

1. **Epic 1-3:** Continue focus on retrieval accuracy (current priority)
2. **Epic 4 Sprint Planning:** Use `docs/future-enhancements.md` for research stories
3. **User Feedback:** Monitor if CLI workaround is acceptable or if async queue needed sooner

---

## References

- Issue: MCP ingestion timeout on large PDFs
- Architecture: `docs/architecture/8-phased-implementation-strategy-v11-simplified.md`
- PRD: `docs/prd/epic-4-production-readiness.md` (future)
- MCP Protocol: https://modelcontextprotocol.io/docs/specification/

---

**Status:** ✅ Documented and Merged
**Next Review:** Epic 3 completion (Week 8-10)
