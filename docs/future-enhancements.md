# Future Enhancements & Research Roadmap

This document tracks known limitations and planned enhancements for future epics.

---

## Epic 4: Production Readiness - Async Ingestion Queue

**Status:** Planned for Epic 4 (post-MVP)
**Priority:** High (UX improvement)
**Estimated Effort:** ~150-200 lines, 1-2 weeks

### Current Limitation

**Problem:** Large PDF ingestion (>10 pages) via MCP times out after ~60 seconds. Current workaround requires CLI ingestion for files >10 pages, creating a two-interface experience.

**Impact:**
- Files >10 pages: Must use CLI instead of MCP
- No progress tracking during ingestion
- User waits without feedback for 10-30 minutes

**Current Workaround:**
```bash
# Large files via CLI
uv run python -c "
import asyncio
from raglite.ingestion.pipeline import ingest_document
asyncio.run(ingest_document('/path/to/large.pdf'))
"

# Then query via MCP
```

---

### Research Questions (Epic 4 Planning)

Before implementing async ingestion, research these architectural options:

#### 1. Job Queue Architecture
- **Question:** Which job queue fits RAGLite's simplicity constraints?
  - Celery + Redis (industry standard, heavy)
  - Python threading + SQLite (lightweight, no Redis)
  - FastAPI BackgroundTasks (simplest, no persistence)
- **Tradeoffs:** Complexity vs. features vs. persistence
- **Research:** Compare overhead, LOC impact, operational complexity

#### 2. Progress Tracking Strategy
- **Question:** How to expose ingestion progress to MCP clients?
  - PostgreSQL jobs table (persistent, queryable)
  - File-based status (/tmp/raglite_jobs/{id}.json)
  - In-memory dict (simplest, lost on restart)
- **Tradeoffs:** Persistence vs. simplicity vs. cleanup overhead
- **Research:** MCP best practices for long-running operations

#### 3. MCP Async Patterns
- **Question:** What's the best MCP tool design for async operations?
  ```python
  # Option A: Separate start/check tools
  start_ingestion(path) -> {job_id}
  check_status(job_id) -> {status, progress}

  # Option B: Single tool with callbacks
  ingest_with_callback(path, webhook_url)

  # Option C: Streaming responses (if MCP supports)
  ```
- **Tradeoffs:** API complexity vs. user experience
- **Research:** MCP protocol capabilities, streaming support

#### 4. Concurrent Ingestion Handling
- **Question:** Should we support multiple concurrent ingestions?
  - Yes: Better UX, but need resource limits (CPU, memory)
  - No: Simpler, but blocks users during long ingestions
- **Tradeoffs:** UX vs. resource management complexity
- **Research:** Typical usage patterns, resource profiles

#### 5. Error Recovery & Cleanup
- **Question:** How to handle failed/abandoned ingestion jobs?
  - Auto-cleanup after N days
  - Manual cleanup tool
  - Persist failure logs for debugging
- **Tradeoffs:** Automation vs. control
- **Research:** Common failure modes, debugging needs

---

### Proposed Epic 4 Stories (Draft)

**Story 4.1:** Research Async Ingestion Architectures (3 days)
- AC1: Compare 3+ job queue options with LOC/complexity analysis
- AC2: Prototype each approach in separate branch
- AC3: Document decision with tradeoffs in ADR (Architecture Decision Record)

**Story 4.2:** Implement Async Ingestion Queue (5 days)
- AC1: `start_ingestion(path)` returns job_id immediately
- AC2: `check_ingestion_status(job_id)` returns progress %
- AC3: Jobs persisted in PostgreSQL (survives restarts)
- AC4: Max 3 concurrent ingestions (configurable)

**Story 4.3:** Progress Tracking & Error Handling (3 days)
- AC1: Real-time progress updates (page X of Y)
- AC2: Failed jobs include error message + stack trace
- AC3: Auto-cleanup completed jobs after 7 days

**Story 4.4:** MCP Tool Integration & Testing (2 days)
- AC1: Update MCP tools to use async ingestion
- AC2: E2E test with 50-page PDF (15+ min ingestion)
- AC3: Update documentation with new workflow

---

### Design Constraints (Maintain MVP Principles)

1. **Simplicity First:** No external infrastructure if avoidable
   - Prefer: Python threading + SQLite
   - Avoid: Redis, RabbitMQ, Kafka (unless scale requires)

2. **Code Budget:** Keep async queue <200 lines
   - Total target: 600-800 lines → 25% max for job queue

3. **Operational Simplicity:** Zero-config for local dev
   - Must work with `docker-compose up`
   - No manual queue setup

4. **Testability:** All async paths must be testable
   - Mock time.sleep() for fast tests
   - Test timeout scenarios

---

### Success Metrics (Epic 4)

- ✅ 100-page PDF ingestion completes without timeout
- ✅ User sees progress updates every 10 seconds
- ✅ Failed ingestions show clear error messages
- ✅ <5% code overhead for async infrastructure
- ✅ Zero external dependencies beyond PostgreSQL

---

### Related Issues

- Issue #XX: "MCP ingestion timeout on large PDFs"
- Issue #XX: "No progress feedback during ingestion"
- Epic 4: Production Readiness & Real-Time Operations

---

### References

- [MCP Protocol Spec](https://modelcontextprotocol.io/docs/specification/)
- [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Celery Architecture](https://docs.celeryq.dev/en/stable/getting-started/introduction.html)
- Python threading: `threading.Thread` for lightweight async

---

**Last Updated:** 2025-11-07
**Next Review:** Epic 3 completion (estimated Week 8-10)
