# High-Level Architecture

## System Overview

RAGLite follows a **layered microservices architecture** with clear separation of concerns:

**Layer 1: Client Layer** (External)
- MCP-compatible clients (Claude Code, Claude Desktop, custom applications)
- Interact via Model Context Protocol
- No custom frontend in MVP

**Layer 2: Gateway Layer** (Aggregation)
- MCP Gateway (FastMCP) aggregates all microservices
- Exposes unified tool catalog to clients
- Handles routing to appropriate service

**Layer 3: Microservices Layer** (Business Logic)
- 5 independent MCP servers, each exposing domain-specific tools
- Services communicate via shared data layer (not direct service-to-service)
- Each service independently scalable

**Layer 4: Orchestration Layer** (Intelligence)
- AWS Strands agents coordinate complex workflows
- Multi-agent patterns: Retrieval Agent, Analysis Agent, GraphRAG Agent, Synthesis Agent
- LLM-based reasoning and interpretation happen here

**Layer 5: Data Layer** (Persistence)
- Qdrant: Vector database for embeddings
- Neo4j: Graph database (Phase 2 conditional)
- S3/Local Storage: Documents, metadata, artifacts

## Architectural Patterns

**1. Microservices Architecture**
- **Pattern:** Domain-driven microservices with MCP interface
- **Rationale:** Independent scaling, clear boundaries, graceful degradation

**2. Model Context Protocol (MCP) Integration**
- **Pattern:** All services expose capabilities via MCP tools
- **Rationale:** Standard protocol, client flexibility, future-proof

**3. Phased Complexity Introduction**
- **Pattern:** Start simple (Contextual Retrieval), add complexity only if proven necessary (GraphRAG)
- **Rationale:** Minimize risk, validate value before investment

**4. Multi-Agent Orchestration**
- **Pattern:** AWS Strands agents coordinate across microservices
- **Rationale:** Complex workflows, multi-step reasoning, LLM flexibility

**5. Graceful Degradation**
- **Pattern:** System continues operating with reduced capabilities if advanced features fail
- **Rationale:** Reliability, user experience continuity

---
