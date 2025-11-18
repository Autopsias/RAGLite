# Epic 3: AI Intelligence & Orchestration - Architecture Index

**Epic:** Epic 3 - AI Intelligence & Orchestration
**Status:** ✅ Architecture Design Complete (2025-11-07)
**Framework:** AWS Strands (v1.15.0)
**Stories:** 3.0.8 (DONE) → 3.1-3.8 (Backlog)

---

## Purpose

This index provides a navigation guide to all Epic 3 architecture documentation. These documents were created during **Story 3.0.8 (Agentic Framework Architecture Spike)** and define the technical foundation for Stories 3.1-3.8.

---

## 📚 Reading Order (Start Here)

If you're implementing Epic 3 stories, read in this order:

### 1. Context & Requirements
**Read First:** Understand what Epic 3 is trying to achieve

- **[PRD: Epic 3 - AI Intelligence & Orchestration](../prd/epic-3-ai-intelligence-orchestration.md)**
  - Product requirements and user stories
  - Feature descriptions for Stories 3.1-3.8
  - Success metrics and acceptance criteria

- **[Tech Spec: Epic 3](../tech-spec-epic-3.md)**
  - Technical requirements and constraints
  - Integration with Epic 2 retrieval system
  - Performance budgets and NFRs

### 2. Framework Selection
**Read Second:** Understand why AWS Strands was chosen

- **[epic-3-framework-selection.md](./epic-3-framework-selection.md)** ⭐ START HERE
  - **What:** Architecture Decision Record (ADR) documenting framework selection
  - **Why:** Explains evaluation of Pydantic AI, Simple Functions, and AWS Strands
  - **Decision:** AWS Strands approved by Ricardo (84.5% weighted score)
  - **Key Sections:**
    - Weighted evaluation criteria (7 factors)
    - POC validation results (3.4s orchestration overhead)
    - Team consensus (6/6 agents recommended Strands)
    - Ricardo's approval and Mistral integration confirmation
  - **Read Time:** 15 minutes
  - **Status:** ✅ APPROVED

### 3. System Architecture
**Read Third:** Understand how the 3-agent system is designed

- **[epic-3-orchestration-design.md](./epic-3-orchestration-design.md)** ⭐ CORE DESIGN
  - **What:** Complete orchestration architecture for 3-agent system
  - **Agents:**
    1. Retrieval Agent (wraps Epic 2 multi_index_search) - 50 LOC
    2. Analysis Agent (LLM-powered interpretation) - 80 LOC
    3. Synthesis Agent (answer generation + citations) - 120 LOC
    4. Orchestrator (Strands coordinator) - 100 LOC
  - **Key Sections:**
    - C4 Context and Container diagrams
    - Agent specifications (inputs/outputs/responsibilities)
    - Error handling (4-tier graceful degradation)
    - Performance budget (<10s p50, <20s p95)
    - Integration with Epic 2 retrieval
  - **Read Time:** 25 minutes
  - **Status:** 🚧 DRAFT (In Progress)

### 4. Workflow Patterns
**Read Fourth:** Learn reusable patterns for agent workflows

- **[epic-3-agent-patterns.md](./epic-3-agent-patterns.md)** ⭐ IMPLEMENTATION GUIDE
  - **What:** 5 reusable workflow patterns with production-ready code
  - **Patterns:**
    1. Sequential Chain (primary for Epic 3)
    2. Parallel Execution (optimization)
    3. Conditional Routing (complexity-based branching)
    4. Error Fallback (4-tier degradation strategy)
    5. Hierarchical Orchestration (future Epic 4)
  - **Key Sections:**
    - Code examples using AWS Strands `@tool` decorator
    - Performance characteristics for each pattern
    - When to use / avoid each pattern
    - Trade-offs and best practices
  - **Read Time:** 30 minutes
  - **Status:** ✅ COMPLETE

### 5. Implementation Context
**Read Fifth:** Understand story-level implementation guidance

- **[Story 3.0.8 Context File](../stories/3-0-8-agentic-framework-architecture-spike.context.xml)**
  - **What:** Story context linking all architecture decisions
  - **Includes:**
    - All 3 acceptance criteria with success metrics
    - Complete artifacts section with doc paths and code snippets
    - Decisions section (framework, architecture, error handling)
    - Implementation guidance for Stories 3.1-3.8
    - Risk assessments and mitigation strategies
  - **Read Time:** 20 minutes
  - **Status:** ✅ COMPLETE

---

## 🔗 Cross-References

### Related Documentation

| Document | Purpose | Path |
|----------|---------|------|
| **PRD Epic 3** | Product requirements | `docs/prd/epic-3-ai-intelligence-orchestration.md` |
| **Tech Spec Epic 3** | Technical requirements | `docs/tech-spec-epic-3.md` |
| **Data Dictionary Epic 3** | Data models and schemas | `docs/data-dictionary-epic-3.md` |
| **Test Design Epic 3** | Test strategy and cases | `docs/test-design-epic-3.md` |
| **Story 3.0.8** | Spike that generated these docs | `docs/stories/3-0-8-agentic-framework-architecture-spike.md` |
| **POC Code** | Validation proof-of-concept | `strands_poc.py` |

### Epic 2 Dependencies

Epic 3 orchestration builds on Epic 2 retrieval:

- **Multi-Index Search:** `raglite/retrieval/search.py:multi_index_search()` - Used by Retrieval Agent
- **SQL Table Retrieval:** `raglite/retrieval/search.py:retrieve_from_postgresql()` - Structured data queries
- **Hybrid Search:** `raglite/retrieval/search.py:hybrid_search()` - Vector + keyword fusion
- **Source Attribution:** `raglite/retrieval/attribution.py` - Citation generation

### Epic 4 Future Work

Epic 3 patterns enable future Epic 4 forecasting:

- **Hierarchical Orchestration Pattern** → Forecasting multi-agent coordination
- **Parallel Execution Pattern** → Time-series analysis parallelization
- **Conditional Routing Pattern** → Anomaly detection workflows

---

## 📋 Architecture Decisions Summary

### Framework Selection (AC1)

| Decision | Rationale |
|----------|-----------|
| **Primary Framework:** AWS Strands | 84.5% weighted score, 47% code reduction, native MCP integration |
| **Fallback Strategy:** Simple Function Calling | 71.5% score, zero dependencies, 105 LOC implementation |
| **Model:** Mistral Small (tunable to Claude) | Confirmed by Ricardo, no AWS Bedrock required |
| **License:** Apache 2.0 | No vendor lock-in, open-source |

### Architecture Design (AC2)

| Component | Technology | LOC Estimate | Purpose |
|-----------|------------|--------------|---------|
| Retrieval Agent | Strands @tool | 50 LOC | Wrap Epic 2 multi_index_search |
| Analysis Agent | Strands @tool + Claude | 80 LOC | LLM-powered interpretation |
| Synthesis Agent | Strands @tool + Claude | 120 LOC | Answer generation + citations |
| Orchestrator | Strands Agent | 100 LOC | Coordinate agent execution |
| **Total** | | **350 LOC** | Within 600-800 budget |

### Error Handling Strategy

**4-Tier Graceful Degradation:**
1. **Tier 1 (Full):** All 3 agents execute successfully → Complete analytical answer
2. **Tier 2 (Partial):** Analysis fails → Direct synthesis from retrieval results
3. **Tier 3 (Retrieval Only):** Synthesis fails → Return retrieved documents with metadata
4. **Tier 4 (Epic 2 Fallback):** Orchestration fails → Epic 2 simple search with basic synthesis

---

## 🎯 Implementation Roadmap

### ✅ Completed
- **Story 3.0.8:** Agentic Framework Architecture Spike (2025-11-07)
  - AC1: Framework selection (AWS Strands approved)
  - AC2: Orchestration design (3-agent architecture)
  - AC3: Workflow patterns (5 reusable patterns)

### ⏳ Next Steps (Stories 3.1-3.8)

| Story | Title | Architecture References |
|-------|-------|-------------------------|
| **3.1** | Agentic Framework Integration | All 3 docs, Pattern 1 (Sequential Chain) |
| **3.2** | Retrieval Agent Implementation | orchestration-design.md (Agent 1 spec), Pattern 1 |
| **3.3** | Analysis Agent Implementation | orchestration-design.md (Agent 2 spec), Pattern 1 |
| **3.4** | Synthesis Agent Implementation | orchestration-design.md (Agent 3 spec), Pattern 1 |
| **3.5** | Multi-Step Workflow Orchestration | agent-patterns.md (Pattern 2: Parallel), Pattern 3 (Conditional) |
| **3.6** | Analytical Query Tool MCP | orchestration-design.md (MCP integration) |
| **3.7** | Graceful Degradation | orchestration-design.md (Error Handling), Pattern 4 (Fallback) |
| **3.8** | Agentic Workflow Test Suite | All 3 docs (test strategy) |

---

## 🔍 Key Architectural Patterns

### Pattern Reference Quick Lookup

| Pattern | File | Use Case | LOC | Latency |
|---------|------|----------|-----|---------|
| Sequential Chain | agent-patterns.md | Stories 3.1-3.4 (primary) | 50 | 3-5s |
| Parallel Execution | agent-patterns.md | Story 3.5 (optimization) | 40 | 2-3s |
| Conditional Routing | agent-patterns.md | Story 3.5 (branching) | 60 | 2-4s |
| Error Fallback | agent-patterns.md | Story 3.7 (degradation) | 100 | 0-5s |
| Hierarchical | agent-patterns.md | Epic 4 (future) | 120 | 5-10s |

### Code Pattern Reference

**Agent Definition:**
```python
from strands import Agent, tool

@tool
async def retrieval_agent(query: str) -> str:
    """Agent 1: Retrieve relevant documents."""
    # Implementation in Story 3.2
```

**Orchestrator Initialization:**
```python
from strands.models.mistral import MistralModel
from raglite.shared.config import settings

mistral = MistralModel(
    api_key=settings.mistral_api_key,
    model_id="mistral-small-latest"
)

orchestrator = Agent(
    model=mistral,
    tools=[retrieval_agent, analysis_agent, synthesis_agent],
    system_prompt="..."
)
```

**Invocation:**
```python
result = await orchestrator.invoke_async(query)
answer = str(result)  # Extract text from AgentResult
```

---

## 📊 Performance Budget

| Metric | Target | Validation |
|--------|--------|------------|
| **Orchestration Overhead** | <5s | 3.4s (POC validated) |
| **Total Query Latency (p50)** | <10s | To be validated in Story 3.8 |
| **Total Query Latency (p95)** | <20s | To be validated in Story 3.8 |
| **Code Size (Total)** | 350 LOC | Within 600-800 budget |
| **Framework Dependencies** | 1 (strands-agents) | Added to pyproject.toml |

---

## 🛠️ Development Resources

### Proof-of-Concept Code

- **File:** `strands_poc.py` (250 lines)
- **Purpose:** Validates AWS Strands + Mistral integration
- **Key Validations:**
  - MistralModel initialization with `settings.mistral_api_key`
  - @tool decorator pattern for agent definitions
  - Agent.invoke_async() method usage
  - AgentResult string extraction via `str(result)`
- **Status:** ✅ POC SUCCESSFUL (2025-11-07)

### Dependencies Added

```toml
# pyproject.toml
dependencies = [
    "strands-agents>=1.10.0,<2.0.0",  # Epic 3: AWS Strands agentic framework
]
```

**Installation:**
```bash
uv sync  # Install strands-agents v1.15.0 + 15 dependencies
```

---

## ❓ FAQ

### When should I read framework-selection.md vs orchestration-design.md?

- **framework-selection.md:** Understand WHY AWS Strands was chosen (ADR)
- **orchestration-design.md:** Understand HOW the system is architected (design)

### Do I need to read all patterns in agent-patterns.md?

**For Stories 3.1-3.4:** Read Pattern 1 (Sequential Chain) only
**For Story 3.5:** Read Patterns 2 (Parallel) and 3 (Conditional)
**For Story 3.7:** Read Pattern 4 (Error Fallback)
**For Epic 4:** Read Pattern 5 (Hierarchical)

### Where do I find code examples?

- **Patterns:** `docs/architecture/epic-3-agent-patterns.md` (production-ready snippets)
- **POC:** `strands_poc.py` (working validation code)
- **Story Context:** `docs/stories/3-0-8-agentic-framework-architecture-spike.context.xml` (key patterns)

### How does Epic 3 integrate with Epic 2?

Epic 3 Retrieval Agent wraps Epic 2's `multi_index_search()` function. See:
- **Architecture:** `epic-3-orchestration-design.md` → Agent 1 Specification
- **Code Reference:** `raglite/retrieval/search.py:multi_index_search()` (Epic 2)

### What if orchestration fails?

Use 4-tier graceful degradation (Pattern 4):
1. Full orchestration
2. Partial (skip Analysis)
3. Retrieval only
4. Epic 2 fallback

Details in: `epic-3-orchestration-design.md` → Error Handling Strategy

---

## 📝 Document Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-11-07 | Initial creation during 4-step remediation | BMad Master |
| 2025-11-07 | Story 3.0.8 completed (all ACs done) | Multi-agent team |
| 2025-11-07 | AWS Strands approved by Ricardo | Ricardo (Project Lead) |

---

## 🔗 Navigation

**Parent:** [Architecture Documentation](./README.md)
**Epic:** [Epic 3 PRD](../prd/epic-3-ai-intelligence-orchestration.md)
**Tech Spec:** [Epic 3 Technical Specification](../tech-spec-epic-3.md)
**Story:** [3.0.8 - Agentic Framework Architecture Spike](../stories/3-0-8-agentic-framework-architecture-spike.md)
**Next Story:** [3.1 - Agentic Framework Integration](../stories/) (to be drafted)

---

**Last Updated:** 2025-11-07
**Maintained By:** BMad Master + Scrum Master
**Questions?** Reference Story 3.0.8 context file or consult architecture docs listed above.
