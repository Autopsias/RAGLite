# Epic 3 Prep - Technical Specification

**Purpose:** Technical debt reduction and preparation work required before Epic 3 feature implementation

**Scope:** Stories 3.0.1 through 3.0.5 (Prep Sprint)

**Status:** Active (Week 1-2 before Epic 3 features)

---

## Overview

Epic 3 (AI Intelligence & Orchestration) requires a clean, well-documented codebase with validated Epic 2 functionality. This prep phase addresses technical debt identified in the Epic 2 retrospective before implementing agentic features.

**Epic 2 Retrospective Findings:**
- Code quality debt: Files exceeding 1000 lines will complicate Epic 3 debugging
- Data validation gap: Ground truth misalignment caused 12% → 77.6% accuracy issue
- Documentation gap: MCP server exists but no user setup guide
- UAT framework missing: No user acceptance testing despite working MCP tool

**Prerequisites for Epic 3 Features:**
1. Codebase refactored to <1000 line modules (maintainability)
2. Data dictionary created for analytical queries (prevent ground truth issues)
3. MCP setup documented (user adoption)
4. UAT framework defined (validate usability)
5. Epic 2 UAT completed (validate foundation before building on it)

---

## Architecture Principles

**KISS Principle Maintained:**
- No new frameworks or abstractions
- Direct refactoring of existing code
- Documentation uses standard markdown
- UAT uses simple test scripts

**Technology Stack:**
- **Refactoring:** Python 3.11+ (existing codebase, no new dependencies)
- **Documentation:** Markdown (standard format)
- **UAT:** Manual testing in Claude Desktop (existing tool)
- **Data Dictionary:** Markdown table (simple, version-controlled)

---

## Story 3.0.1: Refactor Modules to Size Limits

**Goal:** All Python files <1000 lines to prevent maintenance nightmares in Epic 3

**Technical Approach:**

1. **Identify Oversized Files (Day 1 AM - 2 hours):**
   ```bash
   find raglite -name "*.py" -exec wc -l {} \; | sort -rn | head -20
   ```

2. **Refactor Strategy (Day 1 PM - 2 hours):**
   - Split by domain/responsibility
   - Example: `sql_generation/` → `entity_matching.py`, `period_mapping.py`, `metric_calculation.py`
   - Maintain single responsibility per module

3. **Execute Refactoring (Days 2-3 - 1-2 days):**
   - Split oversized modules
   - Update imports
   - Maintain 100% test coverage (run pytest after each refactor)

4. **Architecture Review (Day 3 - 1 hour):**
   - Winston verifies module cohesion
   - Approves for Epic 3

**Acceptance Criteria:**
- ✅ No files >1000 lines in raglite/ directory
- ✅ All tests passing (pytest 100%)
- ✅ Module boundaries documented
- ✅ Winston architecture approval

**Files Created:**
- Refactored modules (varies based on current file sizes)

**Files Modified:**
- Oversized files split into focused modules
- Import statements updated across codebase

---

## Story 3.0.2: Create Epic 3 Data Dictionary

**Goal:** Document available data for analytical queries to prevent Epic 2's ground truth misalignment

**Technical Approach:**

1. **Database Inspection (Day 2 - 4 hours):**
   ```python
   # Script: scripts/inspect-database-for-epic-3.py

   import asyncio
   from raglite.shared.clients import get_db_client

   async def inspect_database():
       db = get_db_client()

       # Query all unique metrics
       metrics = await db.execute("SELECT DISTINCT metric FROM financial_tables;")

       # Query all unique periods
       periods = await db.execute("SELECT DISTINCT period FROM financial_tables;")

       # Query all unique entities
       entities = await db.execute("SELECT DISTINCT entity FROM financial_tables;")

       # Document in markdown format
   ```

2. **Data Dictionary Creation (Day 2 - 2 hours):**
   ```markdown
   # Data Dictionary - Epic 3 Analytical Queries

   ## Available Metrics
   - EBITDA (entity, period, value EUR)
   - Variable Cost (entity, period, value EUR)
   - Revenue (entity, period, value EUR)
   [... complete list]

   ## Available Periods
   - Format: Aug-25, Sep-25, Oct-25
   - Mappings: Q3 2025 → [Jul-25, Aug-25, Sep-25, Aug-25 YTD]
   [... complete catalog]

   ## Available Entities
   - Portugal Cement
   - Tunisia Cement
   - Angola (Secil Angola)
   [... complete list with aliases]

   ## Limitations
   - Currency: EUR only
   - Budget data: Not separately stored
   - Missing metrics: Headcount, G&A expenses
   ```

3. **Winston Architecture Review (Day 2 - 30 min):**
   - Verify completeness
   - Approve for Epic 3 test creation

**Acceptance Criteria:**
- ✅ Data dictionary created: `docs/data-dictionary-epic-3.md`
- ✅ All metrics, periods, entities documented
- ✅ Limitations explicitly listed
- ✅ Winston architecture approval

**Files Created:**
- `docs/data-dictionary-epic-3.md`
- `scripts/inspect-database-for-epic-3.py` (optional - if automation useful)

---

## Story 3.0.3: Document MCP Setup Guide

**Goal:** Enable users (Ricardo, stakeholders) to connect to RAGLite MCP server

**Technical Approach:**

1. **Create Setup Guide (Day 1 - 1 hour):**
   ```markdown
   # RAGLite MCP Server - Setup Guide

   ## Prerequisites
   - Claude Desktop installed
   - Qdrant running (docker-compose up -d)
   - PostgreSQL running
   - Environment variables configured (.env)

   ## Configuration

   Add to `~/.claude/mcp.json`:

   ```json
   {
     "mcpServers": {
       "raglite": {
         "command": "uv",
         "args": ["run", "python", "-m", "raglite.main"],
         "cwd": "/path/to/RAGLite",
         "env": {"PYTHONPATH": "/path/to/RAGLite"}
       }
     }
   }
   ```

   ## Verification
   1. Restart Claude Desktop
   2. Check Settings > MCP for "RAGLite"
   3. Test query: "What is the EBITDA for Portugal Cement?"

   ## Troubleshooting
   [Common issues and solutions]
   ```

**Acceptance Criteria:**
- ✅ Setup guide created: `docs/setup/mcp-configuration.md`
- ✅ Step-by-step instructions for macOS/Linux/Windows
- ✅ Troubleshooting section
- ✅ Ricardo successfully connects using guide (validated in Story 3.0.5)

**Files Created:**
- `docs/setup/mcp-configuration.md`

---

## Story 3.0.4: Create UAT Framework Templates

**Goal:** Define user acceptance testing workflow for all future epics

**Technical Approach:**

1. **UAT Workflow Documentation (Day 1 - 1 hour):**
   ```markdown
   # User Acceptance Testing (UAT) Framework

   ## When to Use UAT
   - After every epic, before marking "complete"
   - For any user-facing feature (MCP tools, UI)

   ## UAT Workflow
   1. UAT Readiness: Identify testable features
   2. UAT Script Creation: Bob + Murat (1-2 hours)
   3. UAT Execution: Ricardo (30-60 min)
   4. UAT Review: Team (30 min)

   ## Pass/Fail Criteria
   - ≥80% pass: Epic approved
   - 60-79% pass: Create UX improvement stories
   - <60% pass: Epic NOT complete - fix blockers
   ```

2. **UAT Script Template (Day 1 - 1 hour):**
   ```markdown
   # UAT Script - [Epic Name]

   ## Prerequisites
   - [ ] System requirements
   - [ ] Configuration
   - [ ] Setup verification

   ## Test Scenarios

   ### Test 1: [Feature Name]
   **Action:** [What to do]
   **Expected:** [What should happen]
   **Actual:** [Tester fills in]
   **Pass/Fail:** [Tester marks]

   [... 8-10 test scenarios]

   ## Results Summary
   - Tests passed: ___/10
   - Overall: PASS / PARTIAL / FAIL
   ```

**Acceptance Criteria:**
- ✅ UAT workflow documented: `docs/process/uat-framework.md`
- ✅ UAT script template created: `docs/templates/uat-script-template.md`
- ✅ Data dictionary template: `docs/templates/data-dictionary-template.md`
- ✅ Module size guidelines: `docs/coding-standards/module-size.md`

**Files Created:**
- `docs/process/uat-framework.md`
- `docs/templates/uat-script-template.md`
- `docs/templates/data-dictionary-template.md`
- `docs/coding-standards/module-size.md`

---

## Story 3.0.5: Execute Epic 2 UAT

**Goal:** Validate Epic 2 MCP tool usability before building Epic 3 on top of it

**Technical Approach:**

1. **Setup MCP Server (Ricardo - 10 min):**
   - Use Story 3.0.3's setup guide
   - Add configuration to `~/.claude/mcp.json`
   - Restart Claude Desktop
   - Verify connection

2. **Execute UAT Script (Ricardo - 30-60 min):**
   - Use existing script: `docs/uat/epic-2-financial-queries-uat.md`
   - Test 10 scenarios
   - Record actual results
   - Mark pass/fail for each test

3. **Results Review (Team - 30 min):**
   - Evaluate pass rate
   - Decision: PASS (≥80%) / PARTIAL (60-79%) / FAIL (<60%)
   - Create follow-up stories if needed

**Acceptance Criteria:**
- ✅ MCP server configured and connected (validated by Ricardo)
- ✅ All 10 test scenarios executed
- ✅ UAT results documented
- ✅ Decision: Epic 2 approved OR improvement stories created
- ✅ Epic 2 officially complete (if ≥80% pass)

**Files Modified:**
- `docs/uat/epic-2-financial-queries-uat.md` (filled in with results)

**Files Created:**
- None (uses existing UAT script)

---

## Dependencies & Blockers

**Story Dependencies:**
- Stories 3.0.1, 3.0.2, 3.0.3, 3.0.4 can run in **parallel** (no dependencies)
- Story 3.0.5 **BLOCKED** until 3.0.3 complete (needs MCP setup guide)

**Epic 3 Feature Stories Blocked:**
- Stories 3.1+ (Agentic Framework, Agents) **BLOCKED** until 3.0.1-3.0.5 complete
- Reason: Epic 3 features require clean codebase, data dictionary, validated Epic 2 foundation

**Critical Path:**
```
Week 1:
Day 1-3: Story 3.0.1 (Refactor) → CRITICAL (blocks Epic 3 implementation)
Day 2: Story 3.0.2 (Data Dictionary) → CRITICAL (blocks Epic 3 test creation)
Day 1: Story 3.0.3 (MCP Setup) → Blocks Story 3.0.5
Day 1: Story 3.0.4 (UAT Templates) → Blocks Story 3.0.5

Week 2:
Day 1-2: Story 3.0.5 (Epic 2 UAT) → CRITICAL (validates Epic 2 complete)
Day 1-2: Epic 3 Full Tech Context (Winston) → Enables Stories 3.1+
Day 3: Epic 3 Sprint Planning → Kickoff Epic 3 features
```

---

## NFR Compliance

**NFR Impact:**
- No impact on accuracy, latency, or attribution (prep work only)
- **NFR Enablement:** Clean codebase enables Epic 3 development velocity
- **NFR Protection:** Data dictionary prevents accuracy regressions

---

## Testing Standards

**Story 3.0.1 Testing:**
- Run full pytest suite after each refactor
- Verify 100% test pass rate maintained
- No functionality changes (refactor only)

**Story 3.0.2 Testing:**
- Manual verification: Query database, confirm data exists
- Cross-check with Epic 2 ground truth (should match)

**Story 3.0.3 Testing:**
- Ricardo executes setup guide (validates clarity)
- Successful MCP connection = test pass

**Story 3.0.4 Testing:**
- Templates reviewed by team (Bob, Murat, Winston)
- Usability validated by applying to Epic 2 UAT

**Story 3.0.5 Testing:**
- 10 UAT scenarios executed
- ≥80% pass rate = Epic 2 validated

---

## Success Criteria (Prep Sprint Complete)

**When are we done?**
- ✅ All 5 prep stories (3.0.1-3.0.5) marked "done"
- ✅ Codebase refactored (<1000 lines per file)
- ✅ Data dictionary created
- ✅ Documentation complete (MCP setup, UAT framework, templates)
- ✅ Epic 2 UAT passed (≥80%)
- ✅ Epic 3 feature stories ready to start

**What happens next?**
- Epic 3 feature implementation begins (Stories 3.1+)
- Full Epic 3 tech context created (agentic architecture)
- Zero Epic 2 technical debt carried forward

---

## Risks & Mitigations

**Risk 1: Refactoring breaks tests**
- Mitigation: Run pytest after each module split
- Fallback: Revert changes, try smaller refactor
- Escalation: If tests fail repeatedly, pause to debug

**Risk 2: Epic 2 UAT fails (<60%)**
- Mitigation: Fix blocking issues before Epic 3
- Fallback: Delay Epic 3 by 1 week to address failures
- Escalation: Re-run UAT after fixes

**Risk 3: Data dictionary incomplete**
- Mitigation: Thorough database inspection script
- Fallback: Update dictionary mid-Epic 3 if gaps found
- Escalation: Pause Epic 3 to complete dictionary

**Risk 4: Prep takes longer than 2 weeks**
- Mitigation: Parallel execution (Stories 3.0.1-3.0.4)
- Fallback: Extend prep sprint by 1 week if needed
- Escalation: Re-prioritize Epic 3 features if timeline critical

---

## References

**Epic 2 Retrospective:** `docs/retrospectives/epic-2-retro-2025-11-05.md`
**Epic 3 PRD:** `docs/prd/epic-3-ai-intelligence-orchestration.md`
**Epic 2 UAT Script:** `docs/uat/epic-2-financial-queries-uat.md`
**Coding Standards (Future):** `docs/coding-standards/module-size.md` (created in Story 3.0.4)

---

**Tech Spec Status:** Active (Prep Phase Only)
**Full Epic 3 Tech Context:** Deferred to Week 2 (after prep complete)
**Created:** 2025-11-05
**Owner:** Bob (Scrum Master)
