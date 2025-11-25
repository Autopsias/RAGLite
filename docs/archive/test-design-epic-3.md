# Test Design: Epic 3 - AI Intelligence & Orchestration

**Epic:** Epic 3 - AI Intelligence & Orchestration
**Status:** Active (Story 3.5 ready-for-dev)
**Test Design Version:** 2.0 (Updated 2025-11-16)
**Original Author:** Ricardo (2025-11-05)
**Updated By:** Bob (Scrum Master via TEA Agent)
**Scope:** Stories 3.1-3.8 test planning with risk assessment

**Change Summary (v2.0):**
- Updated to reflect **AWS Strands v1.15.0** framework (not LangGraph)
- Updated story status: 3.1-3.4 ✅ DONE, 3.5 🚧 READY-FOR-DEV, 3.6-3.8 📋 BACKLOG
- Updated existing test coverage analysis (39 tests passing from Stories 3.1-3.4)
- Removed R-007 (LangGraph learning curve) - no longer applicable
- Updated risk scores based on POC validation (R-001 orchestration overhead = 3.4s validated)
- Aligned test execution order with current implementation status

---

## Executive Summary

This test design provides comprehensive test coverage strategy for Epic 3's agentic orchestration system, which enables multi-step reasoning and complex analytical workflows through **AWS Strands framework** integration.

**Key Objectives:**
- Validate 3-agent orchestration (Retrieval, Analysis, Synthesis)
- Ensure multi-step workflow reliability (>80% success rate)
- Validate performance requirements (<10s p50, <20s p95 query latency)
- Verify graceful degradation (4-tier fallback strategy)

**Current Status:**
- Stories 3.1-3.4: ✅ **DONE** (all agents implemented and tested, 39 tests passing)
- Story 3.5: 🚧 **READY-FOR-DEV** (Multi-step Workflow Orchestration)
- Stories 3.6-3.8: 📋 **BACKLOG**

**Risk Summary:**
- Total risks identified: **10** (reduced from 11 - LangGraph risk removed)
- High-priority risks (≥6): **5** (R-001 to R-005, all have mitigation plans)
- Critical categories: **PERF, BUS, TECH, SEC, OPS**

**Coverage Summary:**
- P0 scenarios: **46** (39 ✅ DONE + 7 remaining for Story 3.5)
- P1 scenarios: **23** (12 ✅ DONE + 11 remaining)
- P2/P3 scenarios: **30** (edge cases and exploratory)
- **Total effort**: **110.5 hours** remaining (~**14 days** for Stories 3.5-3.8)

---

## Risk Assessment

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline | Status |
|---------|----------|-------------|-------------|--------|-------|------------|-------|----------|--------|
| **R-001** | PERF | Orchestration overhead exceeds 5s budget | 2 | 3 | **6** | POC validated 3.4s; parallel retrieval (Pattern 2); monitor OpenTelemetry | Dev | Story 3.5 | ✅ Mitigated (POC) |
| **R-002** | BUS | Workflow success rate <80% | 2 | 3 | **6** | Simple 2-3 step workflows; 3-5 common patterns (YoY, variance); Epic 1 fallback | Dev + QA | Story 3.8 | Planned |
| **R-003** | TECH | Task decomposition failures | 2 | 3 | **6** | Fallback to Epic 1; structured prompts; WorkflowPlan validation; logging | Dev | Story 3.5 | Planned |
| **R-004** | OPS | Claude/Mistral API timeout/rate limits | 2 | 3 | **6** | Retry logic (exponential backoff); fallback on 429/500; connection pooling | Dev | Story 3.1 | ✅ Implemented |
| **R-005** | SEC | Prompt injection in agent instructions | 2 | 3 | **6** | System prompt guardrails; input validation; Pydantic schemas | Dev | Stories 3.2-3.4 | ✅ Implemented |

### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Status |
|---------|----------|-------------|-------------|--------|-------|------------|-------|--------|
| **R-006** | TECH | Agent state management bugs | 2 | 3 | **6** → **4** | AgentState Pydantic validation; structured logging; integration tests | Dev | ✅ Mitigated (Story 3.1) |
| **R-007** | DATA | LLM response parsing failures | 2 | 2 | **4** | Pydantic strict parsing; retry with modified prompt; partial results fallback | Dev | Planned |
| **R-008** | DATA | Data loss in agent execution | 1 | 3 | **3** | Structured logging; intermediate results; partial return | Dev | Planned |

### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
|---------|----------|-------------|-------------|--------|-------|--------|
| **R-009** | OPS | LLM API cost increase | 1 | 1 | **1** | Claude Haiku for Analysis; monitor usage |
| **R-010** | TECH | Framework lock-in (AWS Strands) | 1 | 2 | **2** | Abstract agent interfaces; framework encapsulation |

**Note:** R-007 (LangGraph learning curve) removed - AWS Strands chosen instead, POC validated.

---

## Test Coverage Plan

### Story 3.1: Agentic Framework Integration (✅ DONE)

**Implementation Status:** ✅ COMPLETE (AWS Strands v1.15.0 integrated)

**Existing Test Coverage:**

| Test File | Test Count | Status | Coverage |
|-----------|------------|--------|----------|
| `tests/integration/test_agentic_framework.py` | 7 | ✅ PASS | Framework init, basic workflow, state management, error handling |
| `tests/unit/agentic/test_state_management.py` | 5 | ✅ PASS | AgentState model validation, immutability |
| `tests/unit/agentic/test_error_handling.py` | 3 | ✅ PASS | Timeout handling, fallback logic |

**Total:** 15 tests ✅ PASSING

**Risks Mitigated:**
- R-001 (Orchestration overhead): POC validated 3.4s with Mistral orchestrator ✅
- R-004 (API timeout): Retry logic with exponential backoff implemented ✅
- R-006 (State management): AgentState Pydantic model with comprehensive tests ✅

---

### Story 3.2: Retrieval Agent Implementation (✅ DONE)

**Implementation Status:** ✅ COMPLETE

**Existing Test Coverage:**

| Test File | Test Count | Status | Coverage |
|-----------|------------|--------|----------|
| `tests/unit/agentic/test_retrieval_agent.py` | 7 | ✅ PASS | Agent isolation, input validation, Epic 2 integration |
| `tests/integration/test_retrieval_integration.py` | 2 | ✅ PASS | Multi-index search integration |
| `tests/integration/test_retrieval_synthesis_workflow.py` | 2 | ✅ PASS | 2-step workflow (Retrieval → Synthesis) |

**Total:** 11 tests ✅ PASSING

**Risks Mitigated:**
- R-003 (Agent output format): Pydantic `DocumentChunk` model validated ✅
- R-005 (Prompt injection): Input validation (non-empty query, length limits) ✅

---

### Story 3.3: Analysis Agent Implementation (✅ DONE)

**Implementation Status:** ✅ COMPLETE (Claude Haiku for financial calculations)

**Existing Test Coverage:**

| Test File | Test Count | Status | Coverage |
|-----------|------------|--------|----------|
| `tests/unit/agentic/test_analysis_agent.py` | 6 | ✅ PASS | YoY calculations, variance analysis, trend detection |
| `tests/integration/test_analysis_agent_workflow.py` | 7 | ✅ PASS | LLM integration, structured prompts, AnalysisResult validation |

**Total:** 13 tests ✅ PASSING

**Risks Mitigated:**
- R-001 (Performance): Claude Haiku reduces analysis latency (600-800ms validated) ✅
- R-007 (Response parsing): Pydantic strict parsing with retry logic ✅

---

### Story 3.4: Synthesis Agent Implementation (✅ DONE)

**Implementation Status:** ✅ COMPLETE (Claude Sonnet for high-quality synthesis)

**Existing Test Coverage:**

| Test File | Test Count | Status | Coverage |
|-----------|------------|--------|----------|
| `tests/unit/agentic/test_synthesis_agent.py` | 5 | ✅ PASS | Multi-source aggregation, citation generation |
| `tests/integration/test_retrieval_synthesis_workflow.py` | 3 | ✅ PASS | Retrieval → Analysis → Synthesis workflow |
| `tests/integration/test_mcp_response_validation.py` | 2 | ✅ PASS | MCP JSON format, source attribution |

**Total:** 10 tests ✅ PASSING

**Risks Mitigated:**
- R-003 (Agent output compatibility): Full 3-agent workflow tested ✅
- R-008 (Data loss): Structured logging with intermediate results ✅

---

### Summary: Stories 3.1-3.4 Completed (✅ DONE)

**Total Tests Passing:** **39 tests** (15 + 11 + 13 + 10)
- Unit: 23 tests
- Integration: 16 tests

**Test Execution Time:** ~12 minutes (integration tests with real Qdrant + Claude/Mistral)

**Risks Mitigated:** R-001, R-003, R-004, R-005, R-006, R-007 ✅

---

### Story 3.5: Multi-Step Workflow Orchestration (🚧 READY-FOR-DEV)

**Implementation Status:** 🚧 READY-FOR-DEV (Story 3.5 marked ready in sprint status)

**Planned Test Coverage:**

| Requirement | Test Level | Priority | Risk Link | Test Count | Status | Owner |
|-------------|------------|----------|-----------|------------|--------|-------|
| **AC1:** Query complexity classifier >90% accuracy | Unit | P0 | R-004 | 3 | 🚧 TODO | Dev |
| **AC2:** Workflow planner decomposes queries | Unit | P0 | R-003 | 3 | 🚧 TODO | Dev |
| **AC3:** Sub-tasks routed to specialized agents | Unit | P0 | R-003 | 2 | 🚧 TODO | Dev |
| **AC4:** Agent outputs passed between agents | Integration | P0 | R-003 | 2 | 🚧 TODO | Dev |
| **AC5:** Workflow execution <30s (NFR5) | Integration | P0 | R-001 | 3 | 🚧 TODO | Dev |
| **AC6:** Example workflow tested (YoY growth) | Integration | P0 | R-002 | 1 | 🚧 TODO | Dev |
| **AC7:** Workflow success rate >80% | Integration | P0 | R-002 | 1 | 🚧 TODO | Dev |
| **AC8:** Graceful degradation on failures | Integration | P1 | R-006 | 4 | 🚧 TODO | Dev |

**Planned Test Files:**
- `tests/unit/test_query_complexity_classifier.py` (3 tests) 🚧 TODO
- `tests/unit/test_workflow_planner.py` (3 tests) 🚧 TODO
- `tests/unit/test_agent_routing.py` (2 tests) 🚧 TODO
- `tests/integration/test_workflow_orchestration.py` (11 tests) 🚧 TODO
  - Includes: agent data passing (2), performance (3), YoY example (1), success rate (1), fallback (4)

**Total:** 19 tests planned (7 P0 + 4 P1 + 8 supporting tests)

**Test Estimate:** 32 hours (~4 days) - from Story 3.5 tasks breakdown

---

### Story 3.6: Analytical Query Tool (MCP) (📋 BACKLOG)

**Implementation Status:** 📋 BACKLOG

**Planned Test Coverage:**

| Requirement | Test Level | Priority | Risk Link | Test Count | Status | Owner |
|-------------|------------|----------|-----------|------------|--------|-------|
| MCP tool triggers agentic workflow | Integration | P0 | - | 2 | 📋 BACKLOG | Dev |
| Routes simple → Epic 2, complex → Epic 3 | Integration | P0 | R-004 | 3 | 📋 BACKLOG | Dev |
| Responses include reasoning steps | E2E | P1 | - | 2 | 📋 BACKLOG | Dev |
| Test queries (trend, variance, correlation) | E2E | P1 | R-002 | 5 | 📋 BACKLOG | Dev |
| User testing via Claude Desktop | Manual | P2 | - | N/A | 📋 BACKLOG | QA |

**Planned Test Files:**
- `tests/integration/test_analytical_query_tool_mcp.py` (7 tests) 📋 BACKLOG
- `tests/e2e/test_claude_desktop_integration.py` (5 tests) 📋 BACKLOG

**Test Estimate:** 12 hours (~1.5 days)

---

### Story 3.7: Graceful Degradation for Workflow Failures (📋 BACKLOG)

**Implementation Status:** 📋 BACKLOG

**Planned Test Coverage:**

| Requirement | Test Level | Priority | Risk Link | Test Count | Status | Owner |
|-------------|------------|----------|-----------|------------|--------|-------|
| Workflow timeout handling (>30s) | Integration | P0 | R-006 | 2 | 📋 BACKLOG | Dev |
| Agent failure detection & logging | Unit | P0 | R-006 | 3 | 📋 BACKLOG | Dev |
| Fallback to Epic 1 retrieval | Integration | P0 | R-006 | 2 | 📋 BACKLOG | Dev |
| Partial results or error message | Integration | P1 | - | 2 | 📋 BACKLOG | Dev |
| Error rates logged for improvement | Integration | P2 | - | 1 | 📋 BACKLOG | Dev |

**Planned Test Files:**
- `tests/integration/test_graceful_degradation.py` (10 tests) 📋 BACKLOG
- `tests/unit/test_timeout_handler.py` (3 tests) 📋 BACKLOG

**Test Estimate:** 13 hours (~1.5 days)

---

### Story 3.8: Agentic Workflow Test Suite (📋 BACKLOG)

**Implementation Status:** 📋 BACKLOG

**Planned Test Coverage:**

| Requirement | Test Level | Priority | Risk Link | Test Count | Status | Owner |
|-------------|------------|----------|-----------|------------|--------|-------|
| Test set with 15+ multi-step queries | E2E | P0 | R-002 | 15 | 📋 BACKLOG | QA |
| Automated test suite execution | E2E | P0 | - | 1 | 📋 BACKLOG | QA |
| Success rate measured (target: 80%+) | E2E | P0 | R-002 | 1 | 📋 BACKLOG | QA |
| Performance measured (workflow latency) | E2E | P0 | R-001 | 1 | 📋 BACKLOG | QA |
| Failure analysis documents reasons | E2E | P1 | R-002 | 1 | 📋 BACKLOG | QA |
| Edge cases (missing data, ambiguous, conflicts) | E2E | P2 | - | 6 | 📋 BACKLOG | QA |

**Planned Test Files:**
- `tests/e2e/test_agentic_workflow_suite.py` (25 tests) 📋 BACKLOG
- `tests/fixtures/epic3_complex_queries.json` (test data) 📋 BACKLOG

**Test Estimate:** 37.5 hours (~5 days)

---

## Test Execution Order

### Phase 1: Smoke Tests (<2 min)

**Purpose:** Fast feedback, verify basic functionality

✅ **Already Passing (Stories 3.1-3.4):**
- Retrieval agent returns chunks (<10s)
- Analysis agent performs YoY calculation (<15s)
- Synthesis agent combines results (<20s)
- AWS Strands orchestrator initializes (<5s)

🚧 **Remaining (Story 3.5):**
- Query classifier distinguishes simple vs analytical (<5s)
- Workflow planner decomposes complex query (<10s)

**Total:** 6 tests (4 ✅ PASS + 2 🚧 TODO)

---

### Phase 2: P0 Tests (<20 min)

**Purpose:** Critical path validation

**✅ Completed (Stories 3.1-3.4):** 39 tests
- Framework integration (7 tests) ✅
- Agent isolation + workflow (11 tests) ✅
- Analysis calculations + workflow (13 tests) ✅
- Synthesis aggregation + formatting (10 tests) ✅

**🚧 Remaining (Story 3.5):** 7 tests
- Query complexity classifier accuracy (1 test)
- Workflow planner decomposition (1 test)
- Agent routing accuracy (1 test)
- Multi-agent data passing (1 test)
- Workflow performance <30s (1 test)
- YoY growth example workflow (1 test)
- Workflow success rate >80% (1 test)

**Total P0 Tests:** 39 completed + 7 remaining = **46 tests**
**Expected Time:** <20 min (including new Story 3.5 tests)

---

### Phase 3: P1 Tests (<40 min)

**Purpose:** Important features and error handling

**✅ Completed:** 12 tests (from Stories 3.1-3.4)
- Error handling for workflow failures (3 tests) ✅
- Agent integration tests (9 tests) ✅

**🚧 Remaining:** 11 tests (Story 3.5-3.7)
- Graceful degradation (4 tests - Story 3.5)
- MCP tool integration (5 tests - Story 3.6)
- Reasoning steps transparency (2 tests - Story 3.6)

**Total P1 Tests:** 12 completed + 11 remaining = **23 tests**
**Expected Time:** <40 min

---

### Phase 4: P2/P3 Tests (<60 min)

**Purpose:** Full regression, edge cases, exploratory

**Includes:**
- Edge case workflows (missing data, ambiguous queries, contradictions) - 6 tests
- Performance benchmarks (latency percentiles) - 3 tests
- Manual Claude Desktop integration testing - N/A
- Failure analysis and logging validation - 1 test
- Comprehensive test suite (15+ analytical queries) - 15 tests

**Total P2/P3 Tests:** ~30 tests
**Expected Time:** <60 min

---

## Resource Estimates

### Test Development Effort

| Story | P0 Tests | P1 Tests | P2 Tests | Effort (Hours) | Days | Status |
|-------|----------|----------|----------|----------------|------|--------|
| **3.1** | 7 | 8 | 0 | **15** (~2 days) | ✅ DONE |
| **3.2** | 7 | 4 | 0 | **11** (~1.5 days) | ✅ DONE |
| **3.3** | 10 | 3 | 0 | **13** (~1.5 days) | ✅ DONE |
| **3.4** | 8 | 4 | 0 | **12** (~1.5 days) | ✅ DONE |
| **3.5** | 7 | 4 | 8 | **32** (~4 days) | 🚧 TODO |
| **3.6** | 5 | 2 | 5 | **12** (~1.5 days) | 📋 BACKLOG |
| **3.7** | 5 | 2 | 3 | **13** (~1.5 days) | 📋 BACKLOG |
| **3.8** | 15 | 5 | 5 | **37.5** (~5 days) | 📋 BACKLOG |
| **Total** | **64** | **32** | **21** | **145.5 hours** | **~18 days** | 51 hrs ✅ DONE |

**Completed (Stories 3.1-3.4):** 51 hours (~6.5 days) ✅
**Remaining (Stories 3.5-3.8):** 94.5 hours (~12 days)

### Test Execution Time

| Phase | Test Count | Execution Time | CI/CD Impact | Status |
|-------|-----------|----------------|--------------|--------|
| Smoke Tests | 6 | <2 min | Every commit | 4 ✅ PASS, 2 🚧 TODO |
| P0 Tests | 46 | <20 min | Every PR | 39 ✅ PASS, 7 🚧 TODO |
| P1 Tests | 23 | <40 min | Nightly | 12 ✅ PASS, 11 🚧 TODO |
| P2/P3 Tests | 30 | <60 min | Weekly | 📋 BACKLOG |
| **Total** | **105** | **~122 min** | Full regression | **51 ✅ PASS, 54 🚧 TODO** |

---

## Quality Gate Criteria

### Epic 3 Completion Gate

**Mandatory Criteria (ALL must pass):**

1. **P0 Test Pass Rate:** 100%
   - All 46 P0 tests pass (current: 39/46 = 85% ✅)
   - Stories 3.1-3.4: ✅ COMPLETE
   - Story 3.5: 🚧 7 remaining tests

2. **P1 Test Pass Rate:** ≥95%
   - ≥22 of 23 P1 tests pass (current: 12/23 = 52%)
   - Story 3.5-3.7: 🚧 11 remaining tests

3. **High-Risk Mitigations:** 100%
   - R-001: Orchestration overhead <5s ✅ VALIDATED (POC: 3.4s)
   - R-002: Workflow success rate ≥80% 🚧 TODO (Story 3.8)
   - R-003: Task decomposition fallback 🚧 TODO (Story 3.5)
   - R-004: API retry logic ✅ IMPLEMENTED (Story 3.1)
   - R-005: Prompt injection defense ✅ IMPLEMENTED (Stories 3.2-3.4)

4. **Workflow Success Rate:** ≥80%
   - Story 3.5 AC7: 13+ of 15 complex queries succeed
   - Measured in `test_workflow_orchestration.py` 🚧 TODO

5. **Test Coverage:** ≥80%
   - Current: `raglite/agentic/` module coverage (Stories 3.1-3.4)
   - Remaining: Planner + executor coverage (Story 3.5)

**Current Gate Status:** 🚧 **IN PROGRESS** (Stories 3.1-3.4 complete, 3.5-3.8 remaining)

---

## Mitigation Plans

### R-001: Orchestration Overhead Exceeds 5s Budget (Score: 6) ✅ MITIGATED

**Status:** ✅ VALIDATED in POC (Story 3.0.8 - Agentic Framework Architecture Spike)

**POC Results:**
- Orchestration overhead: **3.4s** (Mistral Small orchestrator)
- Well below 5s budget ✅
- AWS Strands OpenTelemetry tracing validated

**Ongoing Monitoring:**
- OpenTelemetry spans track orchestration latency per workflow
- Performance assertions in `test_workflow_orchestration.py` (Story 3.5)
- Alert threshold: >8s p95

**Owner:** Dev (Story 3.5)
**Timeline:** Ongoing monitoring
**Verification:** Test 3.5-INT-001 (workflow <30s with 5-step example)

---

### R-002: Workflow Success Rate <80% (Score: 6)

**Status:** 🚧 PLANNED (Story 3.8 validation gate)

**Mitigation Strategy:**
1. **Incremental Complexity:** Simple 2-3 step workflows first (Stories 3.1-3.4 ✅ DONE)
2. **Pattern Focus:** Limit Epic 3 MVP to 3-5 common patterns:
   - YoY growth calculation
   - Variance analysis
   - Trend detection
   - Percentage calculations
   - Comparative analysis
3. **Prompt Refinement:** Iterate on planner decomposition prompts based on failure analysis
4. **Graceful Degradation:** Epic 1 fallback ensures baseline UX (Story 3.7)

**Owner:** Dev (Stories 3.5, 3.8) + QA (Story 3.8)
**Timeline:** Story 3.8 completion (Week 4 of Epic 3)
**Verification:** Test 3.8-INT-001/002 (15+ queries from `epic3_complex_queries.json`, ≥80% success)

---

### R-003: Task Decomposition Failures (Score: 6)

**Status:** 🚧 PLANNED (Story 3.5 implementation)

**Mitigation Strategy:**
1. **Fallback to Epic 1:** If planner cannot decompose → `query_financial_documents()`
2. **Structured Prompts:** Well-defined system prompts with successful decomposition examples
3. **WorkflowPlan Validation:** Pydantic schema validation before execution
4. **Decomposition Logging:** All attempts logged with `workflow_id` for pattern analysis

**Owner:** Dev (Story 3.5)
**Timeline:** Story 3.5 completion (Week 2-3)
**Verification:**
- Test 3.5-UNIT-002 (Planner decomposes complex query)
- Test 3.5-INT-004 (Failed workflow falls back to Epic 1)
- Test 3.8-INT-005 (Edge case: Ambiguous query decomposition)

---

### R-004: Claude/Mistral API Timeout/Rate Limits (Score: 6) ✅ IMPLEMENTED

**Status:** ✅ IMPLEMENTED (Story 3.1)

**Implementation:**
- Retry logic with exponential backoff (1s, 2s, 4s delays, max 3 retries)
- Connection pooling via `raglite/shared/clients.py` (reuses Epic 1-2 infrastructure)
- Fallback to Epic 1 on all retries exhausted
- Rate limit monitoring in structured logs

**Owner:** Dev
**Timeline:** ✅ COMPLETE (Story 3.1)
**Verification:**
- Test 3.7-INT-003 (Claude API 429 error retry) ✅ IMPLEMENTED
- Test 3.2-INT-003 (Qdrant timeout handling) ✅ IMPLEMENTED

---

### R-005: Prompt Injection in Agent Instructions (Score: 6) ✅ IMPLEMENTED

**Status:** ✅ IMPLEMENTED (Stories 3.2-3.4)

**Implementation:**
- System prompt guardrails in all agents (Retrieval, Analysis, Synthesis)
- Input validation (non-empty query, length limits, no code execution)
- Pydantic strict schemas for all agent responses
- No user code execution (only structured LLM calls)

**Owner:** Dev + Security
**Timeline:** ✅ COMPLETE (Stories 3.2-3.4)
**Verification:**
- Test 3.2-UNIT-002 (Input validation) ✅ IMPLEMENTED
- Test 3.6-UNIT-001 (MCP schema validation) 🚧 TODO (Story 3.6)

---

### R-006: Agent State Management Bugs (Score: 6 → 4) ✅ MITIGATED

**Status:** ✅ MITIGATED (Story 3.1 - downgraded to score 4)

**Implementation:**
- `AgentState` Pydantic model with immutable task results (Story 3.1)
- Structured logging with `workflow_id` for all intermediate results
- Comprehensive integration tests validate data flow (Stories 3.1-3.4)
- Stateless workflow execution (no persistent agent state)

**Owner:** Dev
**Timeline:** ✅ COMPLETE (Story 3.1)
**Verification:**
- Test 3.1-INT-003 (State persistence) ✅ PASS
- Test 3.5-INT-003 (YoY growth data flow) 🚧 TODO (Story 3.5)
- Test 3.8-INT-001 (15+ queries validate state management) 🚧 TODO (Story 3.8)

---

## Assumptions and Dependencies

### Assumptions

1. **Epic 2 Completion:** ✅ VALIDATED - Epic 2 achieved 90% accuracy (UAT PASSED)
2. **Analytical Query Volume:** 20-30% of queries are analytical (simple → Epic 2 for speed)
3. **AWS Strands Stability:** v1.15.0 is production-ready (POC validated)
4. **LLM API Availability:** Claude/Mistral maintain 99.9% uptime
5. **Workflow Pattern Simplicity:** 3-5 common patterns cover 80%+ analytical queries
6. **User Latency Tolerance:** Users accept 10-30s for complex queries vs 5s for simple
7. **Graceful Degradation Acceptable:** Partial results + Epic 1 fallback maintain UX

### Dependencies

| Dependency | Required For | Status | Notes |
|------------|--------------|--------|-------|
| Epic 1-2 Retrieval Logic | Retrieval Agent (Story 3.2) | ✅ COMPLETE | 90% accuracy baseline |
| Qdrant + PostgreSQL | All integration tests | ✅ EXISTING | From Epic 1-2 |
| AWS Strands v1.15.0 | Framework (Story 3.1) | ✅ COMPLETE | POC validated 3.4s overhead |
| Ground Truth Analytical Queries | Story 3.8 validation | 🚧 PENDING | QA creating `epic3_complex_queries.json` |
| Claude API Access | Analysis + Synthesis | ✅ EXISTING | Shared from Epic 1-2 |
| Mistral API Access | Orchestrator | ✅ EXISTING | Configured in Story 3.1 |

### Risks to Plan

**Risk:** Workflow success rate <80% in Story 3.8 blocks Epic 3 completion (R-002)
- **Impact:** Epic 3 cannot be marked COMPLETE until target achieved
- **Contingency:** Incremental prompt refinement, Epic 1 fallback ensures baseline

**Risk:** Ground truth analytical queries not ready by Story 3.8 start
- **Impact:** Cannot validate 80% success rate
- **Contingency:** QA creates ground truth in parallel with Stories 3.5-3.7

---

## Test Artifacts

### Test Reports

**Location:** `docs/qa/epic-3/`

**Generated Reports:**
- Test execution summary (pytest HTML report)
- Coverage report (pytest-cov HTML)
- Performance metrics (OpenTelemetry latency percentiles)
- Workflow success rate analysis (Story 3.8)
- Risk mitigation validation

### Test Data

**Location:** `tests/fixtures/`

**Existing:**
- Ground truth datasets from Epic 1-2 ✅
- Mock agent responses for unit tests ✅

**Pending:**
- `epic3_complex_queries.json` - 15+ analytical queries 🚧 TODO (Story 3.8)

---

## Monitoring & Observability

### Key Metrics to Track

| Metric | Target | Alert Threshold | Measurement | Status |
|--------|--------|-----------------|-------------|--------|
| Orchestration Overhead | <5s | >8s | OpenTelemetry span | ✅ 3.4s (POC) |
| Total Query Latency (p50) | <10s | >15s | Test execution time | 🚧 TODO (Story 3.5) |
| Total Query Latency (p95) | <20s | >30s | Test execution time | 🚧 TODO (Story 3.5) |
| Workflow Success Rate | ≥80% | <70% | Story 3.8 tests | 🚧 TODO |
| Agent Error Rate | <5% | >10% | Structured logs | ✅ Tracked |
| Graceful Degradation Rate | <10% | >25% | Fallback trigger count | 🚧 TODO (Story 3.7) |
| P0 Test Pass Rate | 100% | <95% | CI/CD | 39/46 = 85% |

### Logging Strategy

**Structured Logging (raglite.shared.logging):**

```python
# Agent entry (all agents)
logger.info("Agent invoked", extra={
    "agent": "retrieval",
    "query": query,
    "story": "3.5"
})

# Agent success
logger.info("Agent completed", extra={
    "agent": "retrieval",
    "chunks_found": len(chunks),
    "latency_ms": latency,
    "story": "3.5"
})

# Agent failure
logger.error("Agent failed", extra={
    "agent": "retrieval",
    "error": str(e),
    "tier": "degraded",
    "story": "3.7"
})
```

---

## References

**Epic 3 Documentation:**
- **PRD:** `docs/prd/epic-3-ai-intelligence-orchestration.md`
- **Architecture Index:** `docs/architecture/epic-3-index.md`
- **Orchestration Design:** `docs/architecture/epic-3-orchestration-design.md` ⭐ CRITICAL
- **Agent Patterns:** `docs/architecture/epic-3-agent-patterns.md` ⭐ CRITICAL
- **Framework Selection:** `docs/architecture/epic-3-framework-selection.md`

**Story References:**
- **Story 3.1:** `docs/stories/3-1-agentic-framework-integration.md` ✅ DONE
- **Story 3.2:** `docs/stories/3-2-retrieval-agent-implementation.md` ✅ DONE
- **Story 3.3:** `docs/stories/3-3-analysis-agent-implementation.md` ✅ DONE
- **Story 3.4:** `docs/stories/3-4-synthesis-agent-implementation.md` ✅ DONE
- **Story 3.5:** `docs/stories/3-5-multi-step-workflow-orchestration.md` 🚧 READY-FOR-DEV

**Test Framework:**
- AWS Strands: https://github.com/awslabs/agents-for-amazon-bedrock-strands
- pytest: https://docs.pytest.org/
- OpenTelemetry: https://opentelemetry.io/

---

## Approval

**Test Design Approved By:**

- [ ] Product Manager: ______________________ Date: __________
- [ ] Tech Lead: ____________________________ Date: __________
- [ ] QA Lead: ______________________________ Date: __________

**Comments:**

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2025-11-05 | 1.0.0 | Initial test design (LangGraph-based) | Ricardo |
| 2025-11-16 | 2.0.0 | Updated to AWS Strands framework; Stories 3.1-3.4 DONE status; risk updates | Bob (SM via TEA) |

---

**Created By:** Ricardo (2025-11-05)
**Updated By:** Bob (Scrum Master) via TEA Agent (2025-11-16)
**Workflow:** `bmad/bmm/workflows/testarch/test-design`
**Next Step:** Review with Ricardo, proceed with Story 3.5 implementation
