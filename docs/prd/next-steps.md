# Next Steps

## UX Expert Prompt

**Status:** Not required for RAGLite MVP.

**Rationale:** RAGLite delivers intelligence through MCP-compatible clients (Claude Desktop) with no custom UI. UX is defined by conversational interaction patterns and response formats documented in the UI Design Goals section. The MCP client handles all visual presentation.

**If custom web UI is pursued post-MVP:** Re-engage UX Expert to design conversational interface, dashboard visualizations, and team collaboration features.

## Architect Prompt

**Prompt for Architect:**

I need you to create the complete architecture for **RAGLite** - an AI-powered financial intelligence platform. The PRD is ready at `docs/prd.md` and the Project Brief is at `docs/brief.md`.

**Critical First Step - Research Spike (FR33):**

Before designing the architecture, you MUST execute a 1-2 week research spike to validate all critical technical decisions:

1. **Docling PDF Extraction & Embedding Model Selection**
   - Test Docling on sample company financial PDFs
   - Validate table extraction accuracy (target: 95%+)
   - Benchmark and select embedding model during Docling evaluation
   - Decide: Is Docling sufficient, or do we need AWS Textract fallback?

2. **Knowledge Graph Necessity Assessment**
   - Benchmark RAG-only vs. Hybrid RAG+KG on sample queries
   - Evaluate entity extraction quality from financial documents
   - Decide: Implement KG in MVP, defer to Phase 2, or skip entirely?

3. **Agentic Framework Selection**
   - Define required workflow complexity
   - Prototype simple multi-step workflow in: LangGraph, AWS Bedrock Agents, Claude function calling
   - Decide: Which framework (if any) balances complexity vs. capability?

4. **Forecasting Implementation Strategy**
   - Inventory KPIs to forecast and data availability
   - Benchmark LLM-based vs. statistical forecasting accuracy
   - Decide: LLM-based, statistical, hybrid, or simple trend projection?

5. **Architecture & Repository Structure**
   - Based on findings from 1-4, design system architecture
   - Decide: Monorepo vs. multi-repo, service boundaries, component interactions
   - Create skeleton project structure

**Research Spike Deliverable:** Architecture decision document with go/no-go recommendations for each major component, selected technologies, and updated MVP scope based on validated feasibility.

**Architecture Requirements:**

- **Deployment:** Local Docker MVP → Cloud production (AWS or equivalent) migration path
- **Performance:** <5 sec queries (p50), <30 sec complex workflows, 90% retrieval accuracy, 95% source attribution
- **Security:** Financial data on controlled infrastructure, encryption at rest (production), secrets management, audit logging
- **Scalability:** 100+ documents, 50+ queries/day (MVP) → 10+ concurrent users (production)
- **Stack:** Python throughout, Qdrant vector DB, MCP protocol compliance
- **Testing:** Full pyramid (unit, integration, accuracy, manual, performance)

**Design for Graceful Degradation (NFR32):** System must operate with vector-only retrieval if KG fails, basic Q&A if agentic workflows fail, and without forecasting if models prove inaccurate.

**Epic Structure for Implementation:**
1. Foundation & Accurate Retrieval (3-4 weeks)
2. Advanced Document Understanding (2-3 weeks, KG conditional on research spike)
3. AI Intelligence & Orchestration (2-3 weeks)
4. Forecasting & Proactive Insights (2-3 weeks)
5. Production Readiness (2-3 weeks)

**Timeline:** 10-12 weeks total (research spike + implementation)

**Output Required:** Complete architecture document including system design, data flow diagrams, technology stack, deployment architecture, schema design (if applicable), API specifications, and implementation guidance for dev team.

---

*🤖 Generated with [Claude Code](https://claude.com/claude-code)*

*Co-Authored-By: Claude <noreply@anthropic.com>*
