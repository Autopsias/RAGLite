# Framework Update: AWS Strands & Claude Agent SDK Analysis

**Date**: 2025-10-18
**Context**: Critical addition to framework analysis - AWS Strands and Claude Agent SDK
**Impact**: CHANGES RECOMMENDATION for Phase 2-3 implementation

---

## Executive Summary

**CRITICAL FINDING**: The AWS financial analysis blog post uses **LangGraph + Strands Agents together** - this is a **proven production pattern** for financial RAG.

**NEW RECOMMENDATION**:
- **Phase 2**: **LangGraph (orchestration) + AWS Strands OR Claude Agent SDK (agents)**
- **Phase 3**: **Hybrid approach** - LangGraph workflows with Strands/Claude agents as specialists

**Why This Changes Everything**:
1. ✅ **We're using Claude** → Claude Agent SDK has native integration
2. ✅ **Deploying to AWS (Phase 4)** → Strands has native AWS tools
3. ✅ **Production pattern proven** → AWS blog shows LangGraph + Strands for financial analysis
4. ✅ **MCP support** → Both frameworks support Model Context Protocol (future-proofing)

---

## 1. AWS Strands Agents (CRITICAL ADDITION)

### Overview

**Developer**: AWS (Open Source)
**Release**: August 2025
**Philosophy**: Model-driven orchestration (let LLM plan, not hardcoded workflows)

**Production Deployments**:
- ✅ **Amazon Q Developer** (coding assistant)
- ✅ **AWS Glue** (data integration)
- ✅ **Kiro** (AWS tool)
- ✅ **AWS Financial Analysis Agent** (with LangGraph - exact our use case!)

### Core Architecture

```python
from strands import Agent, tool

# Define tools
@tool
def search_neo4j(query: str) -> dict:
    """Search Neo4j graph database."""
    return neo4j_client.search(query)

@tool
def query_postgres(query: str) -> dict:
    """Query PostgreSQL tables."""
    return postgres_client.query(query)

@tool
def search_qdrant(query: str) -> dict:
    """Search Qdrant vector store."""
    return qdrant_client.search(query)

# Create agent - MODEL decides tool usage
agent = Agent(
    model="anthropic.claude-3-5-sonnet-20241022",  # Bedrock model
    tools=[search_neo4j, query_postgres, search_qdrant],
    system_prompt="""You are a financial data retrieval agent.
    Use graph search for entity relationships, SQL for structured data,
    and vector search for semantic queries. Combine results as needed."""
)

# Agent orchestrates itself (no workflow needed!)
response = agent.chat("What is Portugal Aug-25 EBITDA margin trend?")
# Agent decides: "I'll use query_postgres for EBITDA data, then calculate margin"
```

**Key Innovation**: **Model-Driven Orchestration**
- NO hardcoded workflows (LangGraph-style graphs)
- LLM decides which tools to call, in what order
- Simpler code, more adaptive behavior

### Why It's Perfect for RAGLite

1. **Proven for Financial RAG**
   - AWS blog: "Build an intelligent financial analysis agent with LangGraph and Strands"
   - Combines LangGraph (workflow) + Strands (agent reasoning)
   - **Exact our use case**: Multi-source financial data retrieval

2. **AWS Native Integration**
   - Deploy to Lambda, ECS, EKS (Phase 4)
   - Built-in AWS service tools
   - Bedrock integration (Claude via AWS)

3. **MCP Support**
   - Native MCP tool integration
   - Future-proof for tool ecosystem

4. **Model-Agnostic**
   - Works with Bedrock, Anthropic API, OpenAI, local models
   - Switch providers without code changes

5. **Multi-Agent Primitives**
   - Handoffs (pass task to specialist agent)
   - Swarms (multiple agents collaborate)
   - A2A protocol (agent-to-agent communication)

### LangGraph + Strands Pattern (AWS Production)

**From AWS Blog**:
```python
# LangGraph defines HIGH-LEVEL workflow
from langgraph.graph import StateGraph

workflow = StateGraph(State)

# Strands agents handle REASONING at each node
from strands import Agent

financial_agent = Agent(
    model="claude-3-5-sonnet",
    tools=[stock_tool, news_tool, fundamental_tool],
    system_prompt="Financial analysis specialist"
)

# LangGraph node uses Strands agent
def execute_financial_analysis(state: State):
    response = financial_agent.chat(state["query"])
    return {"analysis": response}

workflow.add_node("financial_analysis", execute_financial_analysis)
```

**Why This Pattern?**
- **LangGraph**: Manages complex state, workflow branching, conditional edges
- **Strands**: Agents reason about tool usage, adapt to query complexity
- **Best of both**: Structured workflows + intelligent agents

### Strands vs LangGraph Comparison

| Aspect | LangGraph | Strands | Hybrid (Both) |
|--------|-----------|---------|---------------|
| **Workflow Control** | ✅ Explicit (graphs) | ⚠️ Model-driven | ✅ Explicit + Adaptive |
| **State Management** | ✅ GraphState | ⚠️ Agent memory | ✅ GraphState |
| **Tool Orchestration** | ⚠️ Manual | ✅ Auto (model) | ✅ Best of both |
| **Complexity** | ⚠️ High (graphs) | ✅ Low (just tools) | ⚠️ Medium |
| **AWS Integration** | ⚠️ Custom | ✅ Native | ✅ Native |
| **Production Evidence** | ✅ AWS, CapitalOne | ✅ Amazon Q, Glue | ✅ AWS Financial Agent |

---

## 2. Claude Agent SDK (STRATEGIC ALIGNMENT)

### Overview

**Developer**: Anthropic (Claude creators)
**Release**: September 29, 2025 (alongside Claude Sonnet 4.5)
**Philosophy**: "Give Claude a computer" (bash, file system, tools)

**Production Deployments**:
- ✅ **Claude Code** (powers the IDE agent)
- ✅ **Anthropic internal** (research, video creation, note-taking)
- ✅ **Finance agents, personal assistants** (documented use cases)

### Core Architecture

```python
from claude_agent_sdk import Agent, tool

# Define tools
@tool
def neo4j_search(query: str) -> str:
    """Search Neo4j knowledge graph."""
    results = neo4j_client.query(query)
    return json.dumps(results)

@tool
def postgres_query(sql: str) -> str:
    """Execute SQL query on PostgreSQL."""
    results = postgres_client.execute(sql)
    return json.dumps(results)

# Bash tool included by default (file system, execution)
agent = Agent(
    model="claude-3-5-sonnet-20241022",
    tools=[neo4j_search, postgres_query],  # + bash (automatic)
    system_prompt="Financial data analysis agent..."
)

# Agent uses bash + tools
response = agent.chat("""
Analyze Portugal EBITDA margin trend:
1. Query Neo4j for entity data
2. Get EBITDA from PostgreSQL
3. Save results to CSV
4. Calculate YoY change
""")
# Agent: Uses postgres_query → bash (CSV write) → bash (calculate)
```

**Key Innovation**: **Bash + File System Access**
- Claude can write files, run scripts, iterate
- Works like a human with terminal access
- Not just tool calls - full computer access

### Why It's Strategic for RAGLite

1. **Native Claude Integration**
   - Built by Anthropic (Claude creators)
   - Optimized for Claude's capabilities
   - Latest features (Sonnet 4.5, extended thinking)

2. **Computer Use Paradigm**
   - Bash execution (run calculations, scripts)
   - File system (save results, load data)
   - Iterative workflows (write → test → fix)

3. **MCP Support**
   - First-class MCP integration
   - Claude Desktop uses MCP servers
   - Ecosystem alignment

4. **Production-Proven**
   - Powers Claude Code (millions of users)
   - Anthropic's internal agents
   - State-of-the-art coding performance

5. **TypeScript + Python SDKs**
   - Official SDKs from Anthropic
   - Well-documented, maintained

### Claude SDK vs Others

| Framework | Claude Integration | Computer Access | MCP Support | Anthropic Backing |
|-----------|-------------------|-----------------|-------------|-------------------|
| **Claude Agent SDK** | ✅ Native | ✅ Bash + Files | ✅ Yes | ✅ Official |
| LangGraph | ✅ Works well | ❌ No | ⚠️ Via tools | ❌ LangChain |
| Strands | ✅ Via Bedrock | ❌ No | ✅ Yes | ❌ AWS |
| AutoGen | ✅ Works | ❌ No | ⚠️ Partial | ❌ Microsoft |

---

## 3. Updated Framework Comparison (All 6 Options)

### For RAGLite: Multi-Index Hybrid RAG (GraphRAG + Structured + Vector)

| Framework | Production Financial RAG | State Mgmt | AWS Deploy | Claude Native | MCP | Complexity |
|-----------|--------------------------|------------|------------|---------------|-----|------------|
| **LangGraph + Strands** | ✅ AWS Blog (proven) | ✅ GraphState | ✅ Native | ✅ Via Bedrock | ✅ Yes | Medium |
| **LangGraph + Claude SDK** | ⚠️ No examples | ✅ GraphState | ⚠️ Custom | ✅ Official | ✅ Yes | Medium |
| **LangGraph (standalone)** | ✅ AWS, CapitalOne | ✅ GraphState | ⚠️ Custom | ✅ Works | ⚠️ Via tools | Medium-High |
| **Strands (standalone)** | ✅ AWS examples | ⚠️ Agent memory | ✅ Native | ✅ Via Bedrock | ✅ Yes | Low |
| **Claude SDK (standalone)** | ⚠️ General examples | ⚠️ Agent memory | ⚠️ Custom | ✅ Official | ✅ Yes | Low |
| **LlamaIndex** | ✅ Invoice, contracts | ⚠️ Query engines | ⚠️ Custom | ✅ Works | ⚠️ Via tools | Medium |

---

## 4. REVISED RECOMMENDATIONS

### Phase 1: Non-Agentic (UNCHANGED)
- Pure Python, no framework
- Direct SDK calls (Neo4j, PostgreSQL, Qdrant)

### Phase 2: Lightweight Router (UPDATED)

**Option A: LangGraph + Strands (RECOMMENDED)**

**Why**:
- ✅ **Production-proven pattern** (AWS financial analysis blog)
- ✅ **Best of both**: LangGraph state + Strands model-driven tools
- ✅ **AWS deployment ready** (Phase 4 alignment)
- ✅ **Lower complexity** than pure LangGraph (agents self-orchestrate)

**Architecture**:
```python
from langgraph.graph import StateGraph
from strands import Agent

# Strands agent with multi-index tools
retrieval_agent = Agent(
    model="anthropic.claude-3-5-sonnet",  # via Bedrock
    tools=[neo4j_tool, postgres_tool, qdrant_tool],
    system_prompt="Multi-index financial data retrieval specialist"
)

# LangGraph workflow
workflow = StateGraph(Phase2State)

# Planning node (lightweight routing)
workflow.add_node("plan", lambda s: planner_agent.chat(s["query"]))

# Execution node (Strands agent)
workflow.add_node("retrieve", lambda s: retrieval_agent.chat(s["plan"]))

# Synthesis
workflow.add_node("synthesize", synthesis_node)
```

**Option B: Claude Agent SDK (If prefer simplicity)**

**Why**:
- ✅ **Native Claude integration** (Anthropic official)
- ✅ **Simpler** (no LangGraph graphs)
- ✅ **Computer access** (bash, file system)
- ⚠️ **Less state management** than LangGraph
- ⚠️ **Custom AWS deployment** (not native like Strands)

**Use If**:
- Simplicity > structured workflows
- Want official Anthropic support
- Computer access valuable (calculations, file handling)

### Phase 3: Full Multi-Agent (UPDATED)

**Option A: LangGraph + Strands Multi-Agent (RECOMMENDED)**

**Architecture**:
```python
# Specialist Strands agents
graph_agent = Agent(
    model="claude-3-5-sonnet",
    tools=[neo4j_tool],
    system_prompt="Neo4j graph specialist"
)

table_agent = Agent(
    model="claude-3-5-sonnet",
    tools=[postgres_tool],
    system_prompt="SQL table specialist"
)

critic_agent = Agent(
    model="claude-3-5-sonnet",
    tools=[],  # No tools, just reasoning
    system_prompt="Validate retrieval results for confidence"
)

# LangGraph orchestrates agents
workflow = StateGraph(Phase3State)
workflow.add_node("planner", planner_agent_node)
workflow.add_node("graph", lambda s: graph_agent.chat(s["plan"]))
workflow.add_node("table", lambda s: table_agent.chat(s["plan"]))
workflow.add_node("critic", lambda s: critic_agent.chat(s["results"]))
workflow.add_node("synthesize", synthesis_node)

# Complex conditional edges (LangGraph strength)
workflow.add_conditional_edge("critic", confidence_check, ...)
```

**Why**:
- ✅ LangGraph handles complex state + workflow branching
- ✅ Strands agents handle tool reasoning + adaptation
- ✅ Production pattern (AWS proven)
- ✅ AWS deployment ready

**Option B: Claude Agent SDK Multi-Agent**

- **Use If**: Want Anthropic's official agent framework
- **Trade-off**: Less structured workflow control vs LangGraph
- **Benefit**: Simpler code, computer access, official support

---

## 5. Decision Matrix (UPDATED)

### Choose LangGraph + Strands If:
- ✅ Want production-proven pattern (AWS blog)
- ✅ Need complex state management (GraphState)
- ✅ Deploying to AWS (Phase 4)
- ✅ Want structured workflows + adaptive agents
- ✅ Multi-agent coordination critical

### Choose Claude Agent SDK If:
- ✅ Want official Anthropic support
- ✅ Simplicity > complex workflows
- ✅ Computer access valuable (bash, files)
- ✅ MCP integration priority
- ✅ Rapid prototyping

### Choose LangGraph (standalone) If:
- ⚠️ Don't want additional framework (Strands)
- ✅ Maximum workflow control
- ⚠️ Willing to hand-code tool orchestration

### Choose Strands (standalone) If:
- ✅ Want simplest code (no graphs)
- ✅ Model-driven orchestration preferred
- ✅ AWS deployment critical
- ⚠️ Don't need complex state management

---

## 6. Cost & Effort Comparison

| Framework Combination | Learning Curve | Code Complexity | AWS Alignment | Claude Alignment |
|----------------------|----------------|-----------------|---------------|------------------|
| **LangGraph + Strands** | Medium | Medium | ✅ Excellent | ✅ Good (via Bedrock) |
| **LangGraph + Claude SDK** | Medium | Medium | ⚠️ Custom | ✅ Excellent (native) |
| **Strands only** | Low | Low | ✅ Excellent | ✅ Good (via Bedrock) |
| **Claude SDK only** | Low | Low | ⚠️ Custom | ✅ Excellent (native) |
| **LangGraph only** | Medium-High | Medium-High | ⚠️ Custom | ✅ Good |

---

## 7. FINAL RECOMMENDATION (REVISED)

### Phase 2 (Weeks 7-9): **LangGraph + AWS Strands**

**Rationale**:
1. ✅ **Production-proven** → AWS blog shows exact this pattern for financial RAG
2. ✅ **Best of both worlds** → LangGraph state + Strands model-driven tools
3. ✅ **AWS deployment ready** → Phase 4 alignment
4. ✅ **Lower complexity** → Agents self-orchestrate tools (vs hand-coding)
5. ✅ **We're using Claude via Bedrock** → Natural fit

**Alternative**: Claude Agent SDK if prefer Anthropic-native simplicity

### Phase 3 (Weeks 10-16): **LangGraph + Strands Multi-Agent**

**Rationale**:
1. ✅ Scales from Phase 2 (same pattern, more agents)
2. ✅ LangGraph handles complex workflows (critic loops, conditional routing)
3. ✅ Strands agents handle tool reasoning
4. ✅ Production deployment path clear (AWS native)

---

## 8. Implementation Roadmap (UPDATED)

### Week 7 (Phase 2 Start):

**Setup**:
```bash
# Install both frameworks
pip install langgraph langsmith  # LangGraph + observability
pip install strands-agents        # AWS Strands

# Configure AWS Bedrock access (for Claude via Strands)
aws configure
```

**Prototype** (2 days):
```python
# Day 1: Simple Strands agent with 3 tools
from strands import Agent, tool

@tool
def neo4j_search(query: str): ...
@tool
def postgres_query(sql: str): ...
@tool
def qdrant_search(query: str): ...

agent = Agent(
    model="anthropic.claude-3-5-sonnet-20241022",
    tools=[neo4j_search, postgres_query, qdrant_search]
)

# Test: Does agent choose right tools?
response = agent.chat("What is Portugal Aug-25 EBITDA?")

# Day 2: Add LangGraph workflow around agent
from langgraph.graph import StateGraph

workflow = StateGraph(State)
workflow.add_node("retrieve", lambda s: agent.chat(s["query"]))
workflow.add_node("synthesize", synthesis_node)
```

**Decision Point** (End of Day 2):
- If Strands agent handles tool selection well → Continue hybrid
- If too simple → Consider more LangGraph control
- If too complex → Consider pure Claude Agent SDK

---

## 9. Key Takeaways

1. **AWS Pattern is Proven**: LangGraph + Strands for financial analysis (AWS blog)
2. **Claude Alignment**: Both Strands (via Bedrock) and Claude SDK support our LLM choice
3. **Hybrid > Standalone**: Combining frameworks gets best of both (proven pattern)
4. **AWS Deployment**: Strands has native tools (Lambda, ECS, EKS)
5. **MCP Future-Proof**: Both Strands and Claude SDK support MCP

---

## 10. Comparison Summary Table

| Aspect | LangGraph + Strands | LangGraph + Claude SDK | Strands Only | Claude SDK Only |
|--------|---------------------|------------------------|--------------|-----------------|
| **Production Financial RAG** | ✅ AWS proven | ⚠️ No examples | ✅ AWS examples | ⚠️ General |
| **State Management** | ✅ GraphState | ✅ GraphState | ⚠️ Agent memory | ⚠️ Agent memory |
| **Tool Orchestration** | ✅ Auto (Strands) | ⚠️ Manual | ✅ Auto | ✅ Auto |
| **AWS Deployment** | ✅ Native | ⚠️ Custom | ✅ Native | ⚠️ Custom |
| **Claude Integration** | ✅ Bedrock | ✅ Native API | ✅ Bedrock | ✅ Native API |
| **MCP Support** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Complexity** | Medium | Medium | Low | Low |
| **Learning Curve** | Medium | Medium | Low | Low |
| **Computer Access** | ❌ No | ✅ Bash/Files | ❌ No | ✅ Bash/Files |
| **Framework Overhead** | 2 frameworks | 2 frameworks | 1 framework | 1 framework |

**RECOMMENDED**: **LangGraph + Strands** for production hybrid RAG with structured workflows and intelligent agent reasoning.

---

**Analysis By**: Developer Agent (Updated framework analysis 2025-10-18)
**Critical Addition**: AWS Strands + Claude Agent SDK change recommendations
**New Recommendation**: LangGraph + Strands (proven AWS pattern) OR Claude SDK (Anthropic native)
**Confidence**: HIGH (AWS blog shows exact production pattern for our use case)
