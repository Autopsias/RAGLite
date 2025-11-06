# Story 3.0.3: Document MCP Setup Guide

**Status:** ready-for-dev
**Epic:** Epic 3 - AI Intelligence & Orchestration (Prep Sprint)
**Priority:** 🟡 IMPORTANT (Enables user adoption)
**Effort:** 1 hour
**Owner:** Charlie (Dev)

## Story

As a **user or stakeholder**,
I want **clear documentation for connecting to the RAGLite MCP server**,
so that **I can use the financial query tool in Claude Desktop without configuration confusion**.

## Context

**From Epic 2 Retrospective (2025-11-05):**

Ricardo (Project Lead): "I don't think we have anything to test just yet? The MCP part comes later, isn't it?"

**Root Cause:**
- MCP server working since Epic 1 (`raglite/main.py`)
- No user-facing documentation created
- Project Lead unaware tool existed and couldn't connect

**Impact:**
- Built features but users can't access them
- Documentation gap blocks adoption
- UAT impossible without setup guide

**Strategic Decision:**
- Create user-facing setup documentation
- Enable Ricardo (and future stakeholders) to connect
- Prerequisite for Story 3.0.5 (Epic 2 UAT)

## Acceptance Criteria

### AC1: Create MCP Setup Guide (1 hour)

**Goal:** Step-by-step guide for connecting Claude Desktop to RAGLite MCP server

**Technical Approach:**

Create comprehensive guide: `docs/setup/mcp-configuration.md`

**Content Structure:**

```markdown
# RAGLite MCP Server - Setup Guide

**Purpose:** Connect Claude Desktop to RAGLite for natural language financial queries

**Audience:** Users, stakeholders, QA testers

---

## Prerequisites

Before starting, verify you have:

- ✅ **Claude Desktop installed** ([Download](https://claude.ai/download))
- ✅ **RAGLite project cloned** to local machine
- ✅ **Qdrant running:** `docker ps` shows qdrant/qdrant container
- ✅ **PostgreSQL running:** `docker ps` shows postgres container (port 5432)
- ✅ **Environment variables configured:** `.env` file exists with `ANTHROPIC_API_KEY`
- ✅ **Dependencies installed:** `uv sync` completed successfully

---

## Step 1: Locate Claude Desktop Config File

**macOS/Linux:**
```bash
~/.claude/mcp.json
```

**Windows:**
```
%APPDATA%\Claude\mcp.json
```

**If file doesn't exist:** Create it with `{}`

---

## Step 2: Add RAGLite MCP Configuration

Add the following to your `mcp.json` file:

**macOS/Linux:**
```json
{
  "mcpServers": {
    "raglite": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "raglite.main"
      ],
      "cwd": "/ABSOLUTE/PATH/TO/RAGLite",
      "env": {
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/RAGLite"
      }
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "raglite": {
      "command": "uv.exe",
      "args": [
        "run",
        "python",
        "-m",
        "raglite.main"
      ],
      "cwd": "C:\\ABSOLUTE\\PATH\\TO\\RAGLite",
      "env": {
        "PYTHONPATH": "C:\\ABSOLUTE\\PATH\\TO\\RAGLite"
      }
    }
  }
}
```

**⚠️ IMPORTANT:** Replace `/ABSOLUTE/PATH/TO/RAGLite` with your actual project path.

**Example (macOS):**
```json
"cwd": "/Users/ricardo/DeveloperFolder/RAGLite",
"env": {
  "PYTHONPATH": "/Users/ricardo/DeveloperFolder/RAGLite"
}
```

---

## Step 3: Restart Claude Desktop

1. **Quit Claude Desktop completely** (not just close window)
   - macOS: Cmd+Q or Claude > Quit
   - Windows: Right-click tray icon > Quit

2. **Reopen Claude Desktop**

3. **Wait 5-10 seconds** for MCP server to initialize

---

## Step 4: Verify Connection

**Check MCP Server List:**
1. Open Claude Desktop
2. Go to: **Settings > MCP** (or **Developer > MCP**)
3. Look for "**RAGLite**" in the list of connected servers

**If "RAGLite" appears:** ✅ Connection successful!

**If NOT appearing:** See Troubleshooting section below

---

## Step 5: Test Query

Ask Claude a financial question:

**Example queries:**
```
What is the EBITDA for Portugal Cement in August 2025?

Compare variable costs for Portugal and Tunisia

What are all metrics available for Brazil in Q3 2025?
```

**Expected response:**
- Numeric values with units (e.g., "191.8 million EUR")
- Clear citations (page number, table reference)
- Response time <5 seconds

---

## Troubleshooting

### Issue: "RAGLite" not appearing in MCP servers

**Solutions:**

1. **Check file path:**
   - Verify `cwd` path is absolute (not relative)
   - Ensure path has no typos
   - Use forward slashes `/` even on Windows in JSON

2. **Check uv installation:**
   ```bash
   which uv  # macOS/Linux
   where uv  # Windows
   ```
   If not found: Install uv ([instructions](https://docs.astral.sh/uv/))

3. **Check environment variables:**
   ```bash
   cd /path/to/RAGLite
   cat .env  # Verify ANTHROPIC_API_KEY exists
   ```

4. **Check Qdrant/PostgreSQL:**
   ```bash
   docker ps  # Should show qdrant/qdrant and postgres containers
   ```
   If not running: `docker-compose up -d`

5. **Check server logs:**
   ```bash
   cd /path/to/RAGLite
   uv run python -m raglite.main
   # Should start without errors
   # Press Ctrl+C to stop
   ```

### Issue: Server connects but queries fail

**Solutions:**

1. **Check document ingestion:**
   - Have you ingested any PDFs/Excel files?
   - Run: `scripts/ingest-sample-data.sh` (if available)

2. **Check database:**
   ```bash
   docker exec -it raglite-postgres-1 psql -U postgres -d raglite
   SELECT COUNT(*) FROM financial_tables;
   # Should show >0 rows
   ```

3. **Check vector database:**
   - Qdrant should have collection "documents"
   - Verify via: http://localhost:6333/dashboard

### Issue: Slow response times (>10 seconds)

**Solutions:**

1. **Check Docker resources:**
   - Allocate more CPU/memory to Docker
   - Docker Desktop > Settings > Resources

2. **Check network:**
   - Slow API calls to Anthropic Claude API
   - Verify internet connection stable

---

## Advanced Configuration

### Use Custom Qdrant Port

If Qdrant runs on non-default port:

```json
"env": {
  "PYTHONPATH": "/path/to/RAGLite",
  "QDRANT_URL": "http://localhost:CUSTOM_PORT"
}
```

### Use Custom PostgreSQL Connection

If PostgreSQL on different host/port:

```json
"env": {
  "PYTHONPATH": "/path/to/RAGLite",
  "DATABASE_URL": "postgresql://user:pass@host:port/dbname"
}
```

---

## Uninstalling

To remove RAGLite MCP server from Claude Desktop:

1. Edit `~/.claude/mcp.json`
2. Remove the "raglite" entry from "mcpServers"
3. Restart Claude Desktop

---

## Support

**Issues or Questions:**
- Check: [GitHub Issues](https://github.com/YOUR_USERNAME/RAGLite/issues)
- Documentation: [RAGLite README](../README.md)
- Architecture: [docs/architecture/](../architecture/)

---

**Last Updated:** 2025-11-05
**Tested With:** Claude Desktop 1.x, RAGLite Epic 2
```

**Success Criteria:**
- ✅ Setup guide created: `docs/setup/mcp-configuration.md`
- ✅ Step-by-step instructions for macOS/Linux/Windows
- ✅ Troubleshooting section with common issues
- ✅ Ricardo can successfully connect using guide (validated in Story 3.0.5)

**Files Created:**
- `docs/setup/mcp-configuration.md` (~300 lines)

## Tasks / Subtasks

### Task 1: Create Setup Guide (AC1) - 1 hour

- [ ] **Subtask 1.1:** Write prerequisites section
  - Claude Desktop, dependencies, services running

- [ ] **Subtask 1.2:** Write configuration steps
  - Locate mcp.json
  - Add RAGLite configuration
  - Platform-specific instructions (macOS/Linux/Windows)

- [ ] **Subtask 1.3:** Write verification steps
  - Check MCP connection
  - Test queries
  - Expected responses

- [ ] **Subtask 1.4:** Write troubleshooting section
  - Common issues and solutions
  - Server logs, database checks

- [ ] **Subtask 1.5:** Review and finalize
  - Ensure clarity (non-technical users can follow)
  - Test guide with fresh setup

- [ ] **Subtask 1.6:** Testing - Validate guide clarity (Testing)
  - Non-technical user review (clarity check)
  - Verify prerequisites section completeness
  - Confirm step numbering logical

- [ ] **Subtask 1.7:** Testing - Verify OS instructions (Testing)
  - Validate macOS paths and commands
  - Validate Windows paths and commands
  - Validate Linux paths and commands

- [ ] **Subtask 1.8:** Testing - Troubleshooting completeness (Testing)
  - Test each troubleshooting scenario
  - Verify solutions are actionable
  - Check error message coverage

## Dev Notes

### Architecture Patterns and Constraints

**Documentation Location:**
- File: `docs/setup/mcp-configuration.md`
- Directory structure: `docs/setup/` (user-facing setup guides)
- Follows established pattern from architecture docs

**Markdown Format Standards:**
- Clear hierarchical structure (H1 for title, H2 for sections)
- Code blocks with language tags (```json, ```bash)
- Platform-specific instructions clearly labeled (macOS/Linux/Windows)
- Inline warnings for critical steps (⚠️ prefix)
- Cross-references to other documentation (README, architecture)

**Cross-Platform Considerations:**
- Absolute paths required for `cwd` and `PYTHONPATH` (not relative)
- Path separators: Forward slashes `/` in JSON (even on Windows)
- Command differences: `uv` vs `uv.exe`, `which` vs `where`
- Line ending compatibility (LF preferred, CRLF acceptable)

**User Audience:**
- Non-technical stakeholders (Ricardo, future users)
- Assume minimal command-line experience
- Provide explanations for technical terms (MCP, Qdrant, PostgreSQL)
- Include visual confirmation steps ("Check MCP Server List")

**KISS Principle:**
- ✅ No custom configuration scripts (direct JSON editing)
- ✅ No installation automation (manual steps preferred for clarity)
- ✅ Standard markdown (no custom doc frameworks)
- ✅ Simple troubleshooting (command-line checks, no complex diagnostics)

**References:**
- [Source: Coding Standards](docs/architecture/coding-standards.md) - Markdown formatting guidelines
- [Source: MCP Protocol Specification](https://modelcontextprotocol.io/) - Configuration schema

### Documentation Standards

**Audience:** Non-technical users (stakeholders, QA testers)

**Writing Style:**
- Clear, step-by-step instructions
- No assumed knowledge
- Include screenshots (optional, if helpful)
- Test each step yourself before documenting

### Validation Method

**Story 3.0.5 (Epic 2 UAT) will validate this guide:**
- Ricardo uses this guide to connect
- If connection succeeds → Guide is clear
- If connection fails → Guide needs improvement

**Testing Standards Compliance:**
- Per `testing-strategy.md`, documentation requires user acceptance validation
- Manual testing approach (non-technical user walkthrough)
- Testing subtasks (1.6-1.8) ensure guide clarity and OS coverage
- Pass criteria: Ricardo successfully connects without external help

### Learnings from Previous Story

**From Story 3.0.2 (Create Epic 3 Data Dictionary):**

Story 3.0.2 created comprehensive data validation infrastructure for Epic 3 analytical queries:

**Files Created:**
- `scripts/inspect_database_for_epic_3.py` - Database inspection script (165 lines)
- `docs/data-dictionary-epic-3.json` - JSON catalog (28 metrics, 152 periods, 36 entities, 38 units)
- `docs/data-dictionary-epic-3.md` - Comprehensive markdown dictionary (500 lines)

**Key Achievements:**
- Data-first approach prevented Epic 2's ground truth misalignment (12% → 77.6% accuracy gap)
- 4-step validation process established (Metric → Period → Entity → Unit)
- Winston Architecture Review: APPROVED
- Epic 3 test creation UNBLOCKED

**Architectural Decisions:**
- Synchronous database inspection using `psycopg2` (not asyncpg)
- Markdown + JSON dual format (human-readable + programmatic access)
- KISS principle maintained (no ORMs, simple SELECT DISTINCT queries)

**Relevance to Story 3.0.3:**
- Data dictionary provides context for UAT test scenarios (Story 3.0.5)
- UAT queries should validate against data dictionary (ensure realistic test data)
- MCP setup guide enables UAT execution (Ricardo connects to test analytical queries)

**Unresolved Items:**
- ✅ NO blocking items (all advisory notes are informational)
- ℹ️ Dataset size monitoring (low priority, not blocking)
- ℹ️ Epic 3 test creation guidance (for future stories, not this one)

**Reference:** [Story 3.0.2](docs/stories/3-0-2-create-epic-3-data-dictionary.md)

### References

**Source Documents:**
- [Epic 3 - AI Intelligence & Orchestration](docs/epics.md#epic-3-ai-intelligence--orchestration) - Epic goal: Multi-step reasoning and agentic orchestration
- [Epic 2 Retrospective](docs/retrospectives/epic-2-retro-2025-11-05.md) - Documentation gap identified
- [Epic 3 Prep Tech Spec](docs/tech-spec-epic-3-prep.md#story-303) - MCP setup guide spec
- [Action Item 5](docs/retrospectives/epic-2-retro-2025-11-05.md#action-item-5-documentation-improvements) - Documentation improvements
- [Testing Strategy](docs/architecture/testing-strategy.md) - Manual testing approach for documentation validation
- [Coding Standards](docs/architecture/coding-standards.md) - Markdown formatting guidelines

**MCP Protocol:**
- [Model Context Protocol Docs](https://modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)

## Dev Agent Record

### Context Reference

- **Story Context XML**: `docs/stories/3-0-3-document-mcp-setup-guide.context.xml` (Generated: 2025-11-06)

### Agent Model Used

Claude 3.7 Sonnet (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

### Change Log

**2025-11-05:** Story created by Bob (Scrum Master) - Batch create from Epic 3 Prep tech spec

**2025-11-06:** Story quality validation completed - Auto-improvements applied:
- Added "Architecture patterns and constraints" subsection (documentation location, format standards, cross-platform considerations)
- Added "Learnings from Previous Story" subsection (Story 3.0.2 data dictionary context)
- Added Epic 3 citation to References (epics.md link)
- Added testing-strategy.md and coding-standards.md citations to References
- Added formal testing subtasks: 1.6 (guide clarity), 1.7 (OS instructions), 1.8 (troubleshooting)
- Initialized Change Log section
- **Validation Result:** All critical/major/minor issues resolved → Story ready for development

---

**Story Created:** 2025-11-05
**Created By:** Bob (Scrum Master) - Batch create from Epic 3 Prep tech spec
**Last Updated:** 2025-11-06 (Auto-improved via story validation workflow)
**Next Step:** Review story, then run `story-ready` or `story-context` to mark ready for dev
