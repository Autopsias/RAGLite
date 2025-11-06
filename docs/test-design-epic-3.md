# Test Design: Epic 3 - AI Intelligence Orchestration

**Date:** 2025-11-05
**Author:** Ricardo
**Status:** Draft

---

## Executive Summary

**Scope:** full test design for Epic 3 - AI Intelligence Orchestration (Agentic Workflows)

**Risk Summary:**

- Total risks identified: **11**
- High-priority risks (≥6): **6** (1 critical score=9, 5 high score=6)
- Critical categories: **PERF, BUS, TECH, SEC, OPS**

**Coverage Summary:**

- P0 scenarios: **26** (**52 hours**)
- P1 scenarios: **33** (**33 hours**)
- P2/P3 scenarios: **4** (**2 hours**)
- **Total effort**: **87 hours** (~**11 days**)

---

## Risk Assessment

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description   | Probability | Impact | Score | Mitigation   | Owner   | Timeline |
| ------- | -------- | ------------- | ----------- | ------ | ----- | ------------ | ------- | -------- |
| R-001   | PERF     | Workflow execution timeout >30s | 3           | 3      | **9** | Parallel agent execution, Claude Haiku for Analysis, 25s timeout with 5s fallback buffer | Dev | Story 3.5 |
| R-002   | BUS      | Workflow success rate <80% | 2           | 3      | 6     | Simple 2-3 step workflows first, 3-5 common patterns (YoY, variance), refine prompts, Epic 1 fallback | Dev + QA | Story 3.8 |
| R-003   | TECH     | Task decomposition failures | 2           | 3      | 6     | Fallback to Epic 1 on decomposition fail, structured planner prompts, WorkflowPlan schema validation | Dev | Story 3.5 |
| R-004   | OPS      | Claude API timeout/rate limits | 2           | 3      | 6     | Retry logic (exponential backoff), fallback on 429/500, shared connection pooling | Dev | Story 3.1 |
| R-005   | SEC      | Prompt injection in agent instructions | 2           | 3      | 6     | System prompt guardrails, input validation, Pydantic schemas, no user code execution | Dev + Security | Stories 3.2-3.4 |
| R-006   | TECH     | Agent state management bugs | 2           | 3      | 6     | Pydantic validation for AgentResult, structured logging with workflow_id, comprehensive integration tests | Dev | Story 3.5 |

### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description   | Probability | Impact | Score | Mitigation   | Owner   |
| ------- | -------- | ------------- | ----------- | ------ | ----- | ------------ | ------- |
| R-007   | TECH     | LangGraph learning curve | 2           | 2      | 4     | 2-day POC before Epic 3, tutorials, native function calling fallback | Architect |
| R-008   | DATA     | LLM response parsing failures | 2           | 2      | 4     | Pydantic strict parsing, retry with modified prompt, partial results fallback | Dev |
| R-009   | DATA     | Data loss in agent execution | 1           | 3      | 3     | Structured logging captures intermediate results, partial result return | Dev |

### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description   | Probability | Impact | Score | Action  |
| ------- | -------- | ------------- | ----------- | ------ | ----- | ------- |
| R-010   | OPS      | LLM API cost increase | 1           | 1      | 1     | Use Claude Haiku for Analysis Agent, monitor API usage |
| R-011   | TECH      | Framework lock-in (LangGraph) | 1           | 2      | 2     | Abstract agent interfaces, POC validation before commit |

### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

## Test Coverage Plan

### P0 (Critical) - Run on every commit

**Criteria**: Blocks core journey + High risk (≥6) + No workaround

| Requirement   | Test Level | Risk Link | Test Count | Owner | Notes   |
| ------------- | ---------- | --------- | ---------- | ----- | ------- |
| Story 3.1: Framework initialization and 2-step workflow | Unit + Integration | R-001, R-006 | 4 | Dev | LangGraph setup, state validation, timeout handling |
| Story 3.2: Retrieval agent Epic 1 integration | Integration | R-003 | 1 | Dev | Critical dependency on existing retrieval |
| Story 3.3: Financial calculation accuracy (YoY, variance) | Unit + Integration | R-002 | 3 | Dev | Core analytical capabilities |
| Story 3.4: Citation attribution in synthesis | Unit | NFR7 | 1 | Dev | Source attribution requirement |
| Story 3.5: Query classification and workflow execution | Unit + Integration + E2E | R-001, R-002, R-003 | 5 | Dev + QA | Decomposition, routing, performance, fallback |
| Story 3.6: MCP query routing (simple vs analytical) | Integration | R-003 | 2 | Dev | Critical routing logic |
| Story 3.7: Workflow timeout fallback | Integration | R-001 | 1 | Dev | AC 3.7.1 - 30s timeout gate blocker |
| Story 3.8: Success rate validation (80%+ target) | Integration | R-002 | 2 | QA | Epic 3 completion gate |

**Total P0**: **26 tests**, **52 hours**

### P1 (High) - Run on PR to main

**Criteria**: Important features + Medium risk (3-4) + Common workflows

| Requirement   | Test Level | Risk Link | Test Count | Owner | Notes   |
| ------------- | ---------- | --------- | ---------- | ----- | ------- |
| Story 3.1: State management and error handling | Integration | R-006, R-004 | 2 | Dev | Workflow state persistence, structured error logging |
| Story 3.2: Agent interface validation and resilience | Unit + Integration | R-008, R-004 | 4 | Dev | Input validation, citation format, Qdrant timeout |
| Story 3.3: Trend detection and LLM integration | Unit + Integration | R-002, R-004, R-008 | 4 | Dev | Secondary analytical capability, Claude Haiku, response parsing |
| Story 3.4: Synthesis logic and MCP compliance | Unit + Integration | R-002, R-009 | 4 | Dev | Multi-source aggregation, MCP JSON format, partial results |
| Story 3.5: Agent routing and parallel execution | Unit + Integration | R-003, R-001 | 2 | Dev | Sub-task routing, concurrent retrieval optimization |
| Story 3.6: MCP transparency and user acceptance | Integration + E2E | - | 5 | Dev + QA | Reasoning steps, MCP protocol, trend/variance testing via Claude Desktop |
| Story 3.7: Error detection and partial results | Integration | R-004, R-009 | 4 | Dev | Agent failure logging, Claude API retry, partial results, fallback status |
| Story 3.8: Performance measurement and edge cases | Integration + Doc | R-001, R-003, R-009 | 5 | QA + Dev | Execution time tracking, missing data, ambiguous queries, failure documentation |

**Total P1**: **33 tests**, **33 hours**

### P2 (Medium) - Run nightly/weekly

**Criteria**: Secondary features + Low risk (1-2) + Edge cases

| Requirement   | Test Level | Risk Link | Test Count | Owner | Notes   |
| ------------- | ---------- | --------- | ---------- | ----- | ------- |
| Story 3.2: Input validation defense | Unit | R-005 | 1 | Dev | Non-empty string query validation |
| Story 3.7: UX enhancement (alternative query suggestion) | Integration | - | 1 | Dev | Error message with suggested rephrasing |
| Story 3.8: Edge case - conflicting information | Integration | - | 1 | QA | Documents with contradictory data handling |

**Total P2**: **4 tests** (including 1 from 3.8), **2 hours**

### P3 (Low) - Run on-demand

**Criteria**: Nice-to-have + Exploratory + Performance benchmarks

| Requirement   | Test Level | Test Count | Owner | Notes   |
| ------------- | ---------- | ---------- | ----- | ------- |
| N/A | - | 0 | - | No P3 scenarios identified for Epic 3 |

**Total P3**: **0 tests**, **0 hours**

---

## Execution Order

### Smoke Tests (<5 min)

**Purpose**: Fast feedback, catch build-breaking issues

- [ ] 3.1-INT-001: Basic 2-step workflow (Retrieve → Synthesize) executes successfully (~1 min)
- [ ] 3.5-UNIT-001: Planner classifies queries as SIMPLE vs ANALYTICAL (~30s)
- [ ] 3.6-INT-001: Simple queries routed to Epic 1 (no workflow) (~45s)
- [ ] 3.3-UNIT-001: Analysis agent calculates YoY growth correctly (~30s)

**Total**: **4 scenarios** (~3 min)

### P0 Tests (<15 min)

**Purpose**: Critical path validation

**Framework & Agents:**
- [ ] 3.1-UNIT-001: LangGraph initializes with valid state schema (Unit)
- [ ] 3.1-INT-002: Workflow timeout handler triggers at 30s (Integration)
- [ ] 3.2-INT-001: Retrieval agent integrates with Epic 1 search.py (Integration)
- [ ] 3.3-UNIT-001/002: YoY growth + variance calculations (Unit)
- [ ] 3.3-INT-003: Analysis agent numerical accuracy ≤0.01% error (Integration)
- [ ] 3.4-UNIT-002: Synthesis includes all source citations (Unit)

**Orchestration & Routing:**
- [ ] 3.5-UNIT-001/002: Query classification + task decomposition (Unit)
- [ ] 3.5-INT-001: YoY variance workflow <30s (5-step example) (Integration)
- [ ] 3.5-INT-003: "Calculate YoY revenue growth" test query succeeds (Integration)
- [ ] 3.5-INT-004: Failed workflow falls back to Epic 1 (Integration)
- [ ] 3.5-E2E-001: Complete analytical workflow end-to-end with MCP (E2E)
- [ ] 3.6-INT-001/002: Simple/analytical query routing (Integration)
- [ ] 3.7-INT-001: Workflow timeout fallback to Epic 1 (Integration)

**Validation:**
- [ ] 3.8-INT-001/002: 15+ analytical queries, 80%+ success rate (Integration)

**Total**: **26 scenarios** (~15 min excluding E2E)

### P1 Tests (<40 min)

**Purpose**: Important feature coverage

**State & Error Handling:**
- [ ] 3.1-INT-003/004: State persistence + structured error logging (Integration)
- [ ] 3.2-UNIT-001/002 + INT-002/003/005: Agent interfaces, citations, Qdrant timeout (Unit + Integration)
- [ ] 3.7-INT-002/003/004/006: Agent failure detection, Claude API retry, partial results, fallback status (Integration)

**Agent Capabilities:**
- [ ] 3.3-UNIT-003/004 + INT-001/002: Trend detection, AnalysisResult schema, Claude Haiku, LLM parsing (Unit + Integration)
- [ ] 3.4-UNIT-001/003 + INT-001/002: Multi-source synthesis, query intent, MCP JSON, partial results (Unit + Integration)
- [ ] 3.5-UNIT-003 + INT-002: Agent routing, parallel execution (Unit + Integration)

**User Acceptance:**
- [ ] 3.6-UNIT-001 + INT-003/004 + E2E-001/002: MCP validation, reasoning steps, trend/variance via Claude Desktop (All levels)

**Performance & Edge Cases:**
- [ ] 3.8-INT-003/004/005: Performance measurement, missing data, ambiguous queries (Integration)
- [ ] 3.8-DOC-001: Failure analysis documentation (Documentation)

**Total**: **33 scenarios** (~40 min)

### P2/P3 Tests (<5 min)

**Purpose**: Full regression coverage

**P2 Edge Cases:**
- [ ] 3.2-UNIT-002: Input validation (non-empty query) (Unit)
- [ ] 3.7-INT-005: Alternative query suggestion (Integration)
- [ ] 3.8-INT-006: Conflicting information handling (Integration)

**P3:** None

**Total**: **4 scenarios** (~5 min)

---

## Resource Estimates

### Test Development Effort

| Priority  | Count   | Hours/Test | Total Hours | Notes                                    |
| --------- | ------- | ---------- | ----------- | ---------------------------------------- |
| P0        | 26      | 2.0        | 52          | Complex agentic workflows, LangGraph integration, timeout validation, multi-agent orchestration |
| P1        | 33      | 1.0        | 33          | Agent interface testing, LLM mocking, MCP protocol validation, error handling |
| P2        | 4       | 0.5        | 2           | Edge cases (conflicting data, input validation) |
| P3        | 0       | 0.25       | 0           | None identified for Epic 3 |
| **Total** | **63**  | **-**      | **87**      | **~11 days** (assuming 1 QA engineer) |

### Prerequisites

**Test Data:**

- `tests/fixtures/ground_truth_analytical.json` - 15+ analytical Q&A pairs for Story 3.8 validation
- Reuse Epic 1-2 financial documents (Q3 2023/2024 reports for YoY/variance tests)
- `WorkflowPlanFactory` - Mock factory for WorkflowPlan objects (pytest-factory-boy)
- `AgentResultFactory` - Mock factory for AgentResult objects
- `AnalysisResultFactory` - Mock factory for AnalysisResult objects (financial calculations)

**Tooling:**

- pytest + pytest-asyncio (existing from Epic 1-2)
- pytest-mock for LLM response mocking (Claude API calls in unit tests)
- pytest-timeout for 30s workflow validation (Story 3.5 AC4)
- pytest-cov for coverage reporting (target: 80%+ for orchestration module)
- Docker Compose: Qdrant + PostgreSQL (existing infrastructure, no changes)

**Environment:**

- Claude API key (existing, shared from Epic 1-2 via `.env`)
- LangGraph library (`langgraph>=0.0.20,<1.0.0` per tech spec conditional approval)
- FastMCP MCP server running locally for E2E tests (port 3000)
- Python 3.11+ with UV package manager (existing setup)

---

## Quality Gate Criteria

### Pass/Fail Thresholds

- **P0 pass rate**: 100% (no exceptions - Epic 3 blocks on any P0 failure)
- **P1 pass rate**: ≥95% (waivers required for failures, max 1-2 waivable P1 tests)
- **P2/P3 pass rate**: ≥90% (informational, does not block release)
- **High-risk mitigations**: 100% complete or approved waivers (6 risks: R-001 to R-006)

### Coverage Targets

- **Critical paths** (agentic workflows): ≥80% unit + integration coverage
- **Security scenarios** (R-005 prompt injection): 100% tested
- **Business logic** (financial calculations): ≥90% accuracy validated
- **Performance** (NFR5 <30s target): 100% P0 workflows measured and pass
- **Edge cases**: ≥60% (missing data, ambiguous queries, conflicting info)

### Non-Negotiable Requirements

- [ ] All P0 tests pass (26/26)
- [ ] No high-risk (≥6) items unmitigated (R-001 to R-006 all addressed)
- [ ] **R-001 (score=9)**: Workflow timeout <30s validated (CRITICAL BLOCKER)
- [ ] **R-002 (score=6)**: Workflow success rate ≥80% on 15+ test queries (Epic 3 completion gate)
- [ ] Security tests (SEC category - R-005) pass 100%
- [ ] Performance targets met (PERF category - R-001): p95 <30s for analytical workflows

---

## Mitigation Plans

### R-001: Workflow Execution Timeout >30s (Score: 9 - CRITICAL BLOCKER)

**Mitigation Strategy:**
1. **Parallel Agent Execution**: Execute independent retrieval agents concurrently (2+ searches in parallel)
2. **Claude Haiku for Analysis**: Use faster Claude Haiku ($0.25/MTok) instead of Sonnet for Analysis Agent calculations
3. **Timeout Enforcement**: Implement 25s workflow timeout with 5s buffer for fallback response generation
4. **Performance Budget**: Monitor execution time per agent, alert if p95 >20s for any single agent

**Owner:** Dev (Story 3.5 orchestration implementation)

**Timeline:** Story 3.5 completion (Week 2-3 of Epic 3)

**Status:** Planned

**Verification:**
- **Test:** 3.5-INT-001 (YoY variance workflow <30s with 5-step example)
- **Test:** 3.1-INT-002 (Timeout handler triggers at 30s)
- **Measurement:** All P0 analytical workflows log execution_time_ms, p95 <30s validated

---

### R-002: Workflow Success Rate <80% (Score: 6)

**Mitigation Strategy:**
1. **Incremental Complexity**: Start with simple 2-3 step workflows (Retrieve → Synthesize), gradually add complexity
2. **Pattern Focus**: Limit Epic 3 MVP to 3-5 common analytical patterns (YoY growth, variance analysis, trend detection, percentage calculations, comparative analysis)
3. **Prompt Refinement**: Iterate on planner decomposition prompts based on failure analysis (Story 3.8)
4. **Graceful Degradation**: Fallback to Epic 1 retrieval ensures user always gets results (NFR17)

**Owner:** Dev (Stories 3.5, 3.8) + QA (Story 3.8 validation)

**Timeline:** Story 3.8 completion (Week 4 of Epic 3)

**Status:** Planned

**Verification:**
- **Test:** 3.8-INT-001/002 (15+ analytical queries from ground_truth_analytical.json, success rate measured)
- **Gate:** Epic 3 completion blocked until ≥80% success rate achieved
- **Documentation:** Failure analysis in `docs/epic-3-failure-analysis.md` (AC 3.8.5)

---

### R-003: Task Decomposition Failures (Score: 6)

**Mitigation Strategy:**
1. **Fallback to Epic 1**: If planner cannot decompose query, route to `query_financial_documents()` (Epic 1 tool)
2. **Structured Planner Prompts**: Use well-defined system prompts with examples of successful decompositions
3. **WorkflowPlan Validation**: Pydantic schema validation catches malformed decomposition before execution
4. **Decomposition Logging**: Log all decomposition attempts with `workflow_id` for failure pattern analysis

**Owner:** Dev (Story 3.5 planner implementation)

**Timeline:** Story 3.5 completion (Week 2-3 of Epic 3)

**Status:** Planned

**Verification:**
- **Test:** 3.5-UNIT-002 (Planner decomposes complex query into sub-tasks)
- **Test:** 3.5-INT-004 (Failed workflow falls back to Epic 1)
- **Test:** 3.8-INT-005 (Edge case: Ambiguous query decomposition)

---

### R-004: Claude API Timeout/Rate Limits (Score: 6)

**Mitigation Strategy:**
1. **Retry Logic**: Exponential backoff (1s, 2s, 4s delays) for 429/500 errors (max 3 retries)
2. **Connection Pooling**: Reuse shared Claude API client from `raglite/shared/clients.py` (existing Epic 1-2 infrastructure)
3. **Fallback on API Failure**: If all retries fail, fallback to Epic 1 retrieval (NFR17)
4. **Rate Limit Monitoring**: Log API usage metrics, alert if approaching 1000 RPM limit

**Owner:** Dev (Story 3.1 framework integration + Stories 3.3-3.4 agent implementation)

**Timeline:** Story 3.1 completion (Week 1 of Epic 3)

**Status:** Planned

**Verification:**
- **Test:** 3.7-INT-003 (Claude API 429 error retries with exponential backoff)
- **Test:** 3.2-INT-003 (Retrieval agent handles Qdrant timeout gracefully - reuses Epic 1 logic)
- **Monitoring:** Structured logs include Claude API response times and error rates

---

### R-005: Prompt Injection in Agent Instructions (Score: 6)

**Mitigation Strategy:**
1. **System Prompt Guardrails**: Agent system prompts include instructions to ignore user attempts to modify agent behavior
2. **Input Validation**: Validate user queries before passing to agents (non-empty string, length limits, no code execution)
3. **Pydantic Schemas**: All agent responses validated against strict Pydantic models (type safety, prevents malformed data)
4. **No User Code Execution**: Agents never execute user-provided code, only structured LLM calls

**Owner:** Dev (Stories 3.2-3.4 agent implementation) + Security (review)

**Timeline:** Stories 3.2-3.4 completion (Week 2 of Epic 3)

**Status:** Planned

**Verification:**
- **Test:** 3.2-UNIT-002 (Retrieval agent validates input query - non-empty string)
- **Test:** 3.6-UNIT-001 (MCP tool validates AnalyticalQueryRequest schema)
- **Security Review:** Manual security review of agent system prompts before Story 3.4 completion

---

### R-006: Agent State Management Bugs (Score: 6)

**Mitigation Strategy:**
1. **Pydantic Validation**: All `AgentResult` objects validated against Pydantic schema before passing to next agent
2. **Structured Logging**: Log all intermediate agent results with `workflow_id` for debugging (NFR26)
3. **Integration Tests**: Comprehensive multi-step workflow tests validate correct data flow (Stories 3.5, 3.8)
4. **State Isolation**: Each workflow execution is stateless (no persistent agent state between requests)

**Owner:** Dev (Story 3.5 orchestration implementation)

**Timeline:** Story 3.5 completion (Week 2-3 of Epic 3)

**Status:** Planned

**Verification:**
- **Test:** 3.1-INT-003 (Workflow state persists between agent steps)
- **Test:** 3.5-INT-003 ("Calculate YoY revenue growth" test query succeeds - validates full data flow)
- **Test:** 3.8-INT-001 (15+ analytical queries validate state management across diverse workflows)

---

## Assumptions and Dependencies

### Assumptions

1. **Epic 2 Completion**: Epic 3 assumes Epic 2 achieved 70-80% retrieval accuracy (✅ VALIDATED per tech spec)
2. **Analytical Query Volume**: Analytical queries represent 20-30% of total queries (simple queries routed to Epic 1 for fast performance)
3. **LangGraph Stability**: LangGraph library (version ≥0.0.20) is production-ready despite being pre-1.0 (conditional approval per tech stack)
4. **Claude API Availability**: Claude API maintains 99.9% uptime (historical Anthropic SLA assumption)
5. **Workflow Pattern Simplicity**: Most analytical queries fit 3-5 common patterns (YoY growth, variance, trend, percentage, comparison)
6. **User Latency Tolerance**: Users accept 10-30s response time for complex analytical queries vs 5s for simple queries (UX trade-off)
7. **Graceful Degradation Acceptable**: Users satisfied with partial results + error message when workflows fail (Epic 1 fallback maintains baseline UX)

### Dependencies

1. **Epic 1-2 Retrieval Logic** - Required for Retrieval Agent (Story 3.2) - **COMPLETE** ✅
2. **Qdrant + PostgreSQL Infrastructure** - Required for all integration tests - **EXISTING** ✅ (from Epic 1-2)
3. **LangGraph Decision** - Architect must choose LangGraph vs native function calling before Story 3.1 - **PENDING** ⚠️
4. **Ground Truth Analytical Queries** - QA must create `tests/fixtures/ground_truth_analytical.json` with 15+ Q&A pairs before Story 3.8 - **PENDING** ⚠️
5. **Claude API Access** - Required for Analysis and Synthesis agents - **EXISTING** ✅ (shared from Epic 1-2)

### Risks to Plan

- **Risk**: LangGraph learning curve delays Story 3.1 by 2-3 days (R-007 score=4)
  - **Impact**: Extends Epic 3 timeline from 4 weeks to 4.5 weeks
  - **Contingency**: 2-day POC validation before Epic 3 starts, native function calling fallback available

- **Risk**: Workflow success rate <80% in Story 3.8 blocks Epic 3 completion (R-002 score=6)
  - **Impact**: Epic 3 cannot be marked COMPLETE until success rate target achieved
  - **Contingency**: Incremental prompt refinement, focus on 3-5 common patterns, Epic 1 fallback ensures baseline functionality

- **Risk**: Ground truth analytical queries not ready by Story 3.8 start
  - **Impact**: Cannot validate 80% success rate, blocks Epic 3 completion
  - **Contingency**: QA creates ground truth in parallel with Stories 3.1-3.7 (1 week lead time)

---

## Approval

**Test Design Approved By:**

- [ ] Product Manager: ****____**** Date: ****____****
- [ ] Tech Lead: ****____**** Date: ****____****
- [ ] QA Lead: ****____**** Date: ****____****

**Comments:**

---

---

---

## Appendix

### Knowledge Base References

- `bmad/bmm/testarch/knowledge/risk-governance.md` - Risk classification framework, gate decision engine
- `bmad/bmm/testarch/knowledge/probability-impact.md` - Risk scoring methodology (probability × impact matrix)
- `bmad/bmm/testarch/knowledge/test-levels-framework.md` - Test level selection (unit vs integration vs E2E)
- `bmad/bmm/testarch/knowledge/test-priorities-matrix.md` - P0-P3 prioritization criteria

### Related Documents

- **PRD:** `docs/prd/epic-3-ai-intelligence-orchestration.md` - Epic 3 product requirements, stories, acceptance criteria
- **Tech Spec:** `docs/tech-spec-epic-3.md` - Epic 3 technical specification, agentic architecture, LangGraph design
- **Architecture:** `docs/architecture/6-complete-reference-implementation.md` - RAGLite architecture, coding patterns
- **Epic 1-2 Foundation:** `docs/prd/epic-1-foundation-accurate-retrieval.md` + `docs/prd/epic-2-advanced-rag-enhancements.md`
- **Test Fixtures:** `tests/fixtures/ground_truth_analytical.json` (TBD - Story 3.8 dependency)
- **Testing Guidelines:** `docs/testing-guidelines.md` - Project testing standards

---

**Generated by**: BMad TEA Agent - Test Architect Module
**Workflow**: `bmad/bmm/testarch/test-design`
**Version**: 4.0 (BMad v6)
