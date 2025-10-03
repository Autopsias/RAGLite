# Project Brief: RAGLite

---

## Executive Summary

**RAGLite** is a lightweight RAG (Retrieval-Augmented Generation) system designed to unlock financial intelligence from company data through natural language interaction. The system ingests financial documents (PDFs, Excel sheets), processes them into a vector database, and exposes this knowledge via MCP (Model Context Protocol) to enable conversational queries about financial performance and context.

**Primary Problem:** Finance teams currently rely on static performance reports to answer questions about financial data, creating friction, delays, and limiting insight discovery.

**Target Market:** Initially personal use, expanding to CFO, CAO, finance teams, and board members within the organization.

**Key Value Proposition:** Replace manual report navigation with instant, natural language access to comprehensive financial knowledge—ask questions, get contextual answers backed by your company's actual financial data.

---

## Problem Statement

### Current State and Pain Points

Financial decision-makers face a dual challenge that limits both operational efficiency and strategic intelligence:

**Access Problem:**
- **Time-intensive manual searching** - Finance teams spend hours navigating PDFs and Excel spreadsheets to answer specific questions about financial performance
- **Context fragmentation** - Related financial information is scattered across multiple reports, requiring mental synthesis to understand the complete picture
- **Limited accessibility** - Board members and executives depend on finance teams to extract and summarize data, creating bottlenecks

**Intelligence Problem:**
- **Reactive vs. Proactive Analysis** - Current workflows analyze what we ask about, not what we *should* be asking about
- **Limited forecasting capability** - Manual forecasting is time-intensive, limited in scope, and difficult to refresh as new data arrives
- **Hidden insights** - Patterns, trends, and strategic priorities remain buried in data, only surfacing through labor-intensive analysis
- **Strategic ambiguity** - Identifying where to focus attention (biggest risks, opportunities, issues) requires extensive manual synthesis

### Impact of the Problem

**Quantifiable impacts:**
- **Decision latency** - Days or weeks to answer complex financial questions that require data synthesis
- **Missed opportunities** - Strategic issues and opportunities go undetected until they become obvious (or problematic)
- **Resource misallocation** - Finance team time skewed toward manual retrieval and basic analysis vs. strategic work
- **Forecast staleness** - Financial projections quickly become outdated between formal refresh cycles

**Qualitative impacts:**
- **Reduced strategic agility** - Leadership can't quickly explore "what-if" scenarios or pivot based on financial signals
- **Insight poverty** - Valuable patterns and correlations exist in the data but require manual discovery
- **Confidence gaps** - Board and executives lack real-time understanding of financial trajectory and emerging risks
- **Barrier to data-driven culture** - When accessing AND interpreting financial context is difficult, decision-making defaults to intuition

### Why Existing Solutions Fall Short

- **Traditional BI dashboards** - Require predefined queries, don't handle natural language, and provide visualization without intelligence or forecasting
- **Generic LLM chat tools** (e.g., ChatGPT with document upload) - Lack persistent knowledge base, can't handle large document sets, no financial domain optimization, and limited analytical depth
- **Manual analysis workflows** - Don't scale, create human bottlenecks, and can't continuously monitor for emerging patterns
- **Full enterprise analytics platforms** - Too heavyweight, expensive, complex, and still require users to know what questions to ask
- **Standalone forecasting tools** - Operate in isolation from contextual document knowledge, require manual data prep

**The missing piece:** An intelligent system that combines comprehensive financial document knowledge with AI-powered reasoning to both answer questions AND proactively surface insights, forecasts, and strategic priorities.

### Urgency and Importance

Financial agility is critical in today's business environment. The ability to **instantly access, intelligently analyze, and proactively forecast** financial context directly impacts:

- **Strategic decision speed and quality** - From days to minutes for complex financial questions
- **Risk detection** - Proactive identification of financial issues before they escalate
- **Resource allocation effectiveness** - Data-driven prioritization of where to focus attention and investment
- **Board and executive confidence** - Real-time financial intelligence for oversight and governance
- **Finance team value** - Shift from manual data retrieval to strategic advisory and insight generation

Organizations that can ask better financial questions faster—and have AI surface the questions they *should* be asking—gain significant competitive advantage.

---

## Proposed Solution

### Core Concept and Approach

**RAGLite** is an AI-powered financial intelligence platform that transforms how organizations interact with and derive insights from financial data. The solution combines three core capabilities:

**1. Knowledge Foundation (RAG Infrastructure)**
- Ingests financial documents (PDFs, Excel spreadsheets) containing company financial data
- Intelligently chunks and processes content while preserving financial context
- Stores semantic representations in a vector database for efficient retrieval
- Exposes knowledge via Model Context Protocol (MCP) for LLM integration

**2. Conversational Access Layer**
- Natural language interface for querying financial data ("What was Q3 marketing spend vs. Q2?")
- Contextual retrieval that understands financial terminology and relationships
- Synthesizes answers from multiple document sources automatically
- Provides source attribution for transparency and verification

**3. Intelligence & Forecasting Layer**
- AI-powered analysis that identifies trends, patterns, and anomalies in financial data
- Automated forecasting of key financial indicators based on historical patterns
- Proactive insight generation ("Top 3 financial risks based on current data")
- Strategic recommendations highlighting where leadership should focus attention

### Key Differentiators from Existing Solutions

**vs. Traditional BI Dashboards:**
- Natural language interaction (no query building required)
- AI-generated insights vs. passive visualization
- Answers questions you didn't know to ask

**vs. Generic LLM Tools (ChatGPT, etc.):**
- Persistent, optimized knowledge base specific to your financial data
- Handles large document sets efficiently via RAG architecture
- Financial domain optimization and reasoning patterns
- Deeper analytical capabilities tuned for financial intelligence

**vs. Manual Analysis Workflows:**
- Instant access vs. hours/days of manual synthesis
- Continuous monitoring for emerging patterns
- Scalable—handles growing data volume without adding headcount

**vs. Enterprise Analytics Platforms:**
- Lightweight and focused on financial document intelligence
- Faster implementation and lower complexity
- AI-native design vs. bolted-on AI features

### Why This Solution Will Succeed Where Others Haven't

**Technical advantages:**
- **RAG architecture** provides grounding in actual company data (reduces hallucination)
- **MCP integration** enables seamless connectivity with modern LLM clients
- **Vector database** enables semantic search superior to keyword matching
- **Modular design** allows incremental capability building (retrieve → analyze → forecast)

**Business advantages:**
- **Focused scope** on financial documents (not trying to be everything to everyone)
- **User-first design** with natural language interaction (minimal training required)
- **Iterative validation** - Can prove value with retrieval before adding intelligence layer

**Strategic advantages:**
- **Data ownership** - Your financial data stays in your controlled infrastructure
- **Customizable** - Tunable to your company's financial terminology and priorities
- **Extensible** - Platform foundation for future financial AI capabilities

### High-Level Vision for the Product

RAGLite evolves from a smart financial document assistant into a **proactive financial intelligence partner**:

**Phase 1 (MVP):** Complete end-to-end system validation
- Accurate retrieval and conversational access to financial knowledge
- AI-powered analysis and forecasting capabilities
- Agentic workflows for complex multi-step reasoning
- Knowledge graph integration for relational queries (if research spike validates)

**Future Evolution:** Capabilities will be determined after MVP validation based on actual usage patterns and learnings, not speculative planning.

**Ultimate vision:** Every financial stakeholder has an AI partner that not only answers their questions but actively surfaces the insights they need to make better decisions faster.

---

## Target Users

RAGLite serves a tiered user base within the organization, with distinct needs at each level:

### **Primary User Segment: Finance Teams**

**Profile:**
- Financial analysts, controllers, finance managers
- Daily interaction with financial reports and data
- Responsible for answering ad-hoc financial questions from stakeholders
- Technical comfort: Medium (comfortable with spreadsheets, BI tools)

**Current Behaviors and Workflows:**
- Spend 40-60% of time searching through PDFs and Excel files to answer questions
- Manually compile data from multiple sources for analysis
- Create custom reports for board meetings and executive requests
- Maintain institutional knowledge of "where to find" specific financial information

**Specific Needs and Pain Points:**
- **Speed:** "I need answers in minutes, not hours"
- **Accuracy:** "I need to trust the data source and calculations"
- **Context:** "I need to see related information, not just the single data point"
- **Efficiency:** "I want to spend time analyzing, not searching"

**Goals They're Trying to Achieve:**
- Respond quickly to executive and board questions about financial performance
- Identify trends and anomalies proactively
- Prepare accurate, comprehensive reports without manual data hunting
- Free up time for strategic analysis vs. data retrieval

**Success looks like:**
- Answering 80% of routine financial queries via RAGLite in <2 minutes
- Reduction in time spent searching for data by 50%+
- Increased confidence in data accuracy through source attribution

### **Secondary User Segment: Executive Leadership (CFO, CAO)**

**Profile:**
- C-level financial executives
- Strategic decision-makers requiring financial intelligence
- Limited time for deep-dive analysis
- Technical comfort: Low-Medium (comfortable with dashboards, prefer summaries)

**Current Behaviors and Workflows:**
- Request financial data and analysis from finance teams
- Review monthly/quarterly performance reports
- Make strategic decisions based on financial trends
- Wait hours or days for answers to complex financial questions

**Specific Needs and Pain Points:**
- **Direct access:** "I shouldn't need to wait for my team to pull data"
- **Insights, not just data:** "Tell me what matters and why"
- **Strategic focus:** "Where should I be paying attention?"
- **Speed of decision:** "I need answers when I'm in the meeting, not after"

**Goals They're Trying to Achieve:**
- Make informed strategic decisions quickly
- Understand financial trajectory and risks without waiting for reports
- Ask exploratory "what-if" questions naturally
- Stay informed without overburdening finance team

**Success looks like:**
- Ability to self-serve answers to 50% of financial questions
- Proactive alerts on financial trends requiring attention
- Confidence in financial oversight without micromanaging finance team

### **Tertiary User Segment: Board Members**

**Profile:**
- Board directors requiring financial oversight
- Quarterly deep-dive into company performance
- Highest level strategic context needed
- Technical comfort: Low (prefer summaries and visualizations)

**Current Behaviors and Workflows:**
- Review board packets with financial summaries
- Ask clarifying questions during board meetings
- Require historical context for current performance

**Specific Needs and Pain Points:**
- **Preparation efficiency:** "I need to understand the financial story before the meeting"
- **Historical context:** "How does this compare to last year, last quarter?"
- **Question exploration:** "I should be able to dig deeper when something stands out"

**Goals They're Trying to Achieve:**
- Effective governance through informed financial oversight
- Ability to ask intelligent questions during board meetings
- Understanding of company financial health and trajectory

**Success looks like (Phase 2+):**
- Board members can explore financial data independently during prep
- Faster, more informed board discussions
- Reduced time preparing answers to board questions

---

## Goals & Success Metrics

### **Business Objectives**

- **Reduce time-to-insight for financial queries by 80%** - From hours/days to minutes for complex questions requiring multi-document synthesis
- **Enable self-service financial intelligence** - 50% of executive financial questions answered without finance team intervention by end of Phase 2
- **Increase finance team strategic capacity** - Reallocate 30%+ of finance team time from data retrieval to strategic analysis and insight generation
- **Improve decision quality** - Enable data-driven decisions through instant access to comprehensive financial context
- **Prove AI-powered financial intelligence ROI** - Demonstrate measurable productivity gains to justify Phase 2 investment

### **User Success Metrics**

**MVP (Phase 1) - Retrieval Validation:**
- **Retrieval accuracy:** 90%+ of queries return correct, relevant information
- **Response time:** <5 seconds for standard queries, <15 seconds for complex multi-document queries
- **Source attribution quality:** 95%+ of answers include verifiable source references
- **User satisfaction:** Primary user (you) rates system 8/10+ for accuracy and usefulness
- **Adoption indicator:** System used for 10+ real financial queries per week

**Phase 2 - Intelligence Layer:**
- **Insight relevance:** 75%+ of proactive insights rated "useful" or "critical" by users
- **Forecast accuracy:** Key indicator forecasts within 10% of actual results
- **Query complexity handling:** Successfully answers 80%+ of multi-step analytical questions
- **Executive adoption:** CFO/CAO use system 3+ times per week for strategic questions

**Phase 3 - Strategic Copilot:**
- **Strategic workflow integration:** Used in 100% of board meeting prep cycles
- **Automated report quality:** AI-generated summaries require <20% human editing
- **Early warning effectiveness:** Proactively identifies 80%+ of financial issues before they're manually detected

### **Key Performance Indicators (KPIs)**

#### **Technical KPIs**
- **System Availability:** 99%+ uptime (self-hosted MVP, 99.9% for cloud production)
- **Query Success Rate:** 95%+ of queries complete without errors
- **Average Response Time:** <5 seconds (p50), <15 seconds (p95)
- **Document Coverage:** 100% of monthly financial reports successfully ingested and retrievable

#### **Usage KPIs**
- **Weekly Active Users:** Track adoption across user segments
- **Queries per User per Week:** Measure engagement depth
- **Query Type Distribution:** Monitor balance of retrieval vs. analytical queries
- **Repeat Usage Rate:** % of users who return after first use (target: 80%+)

#### **Quality KPIs**
- **Answer Accuracy:** User-rated accuracy on sample queries (target: 90%+)
- **Source Attribution Rate:** % of answers with valid source references (target: 95%+)
- **Hallucination Rate:** % of queries producing incorrect/fabricated information (target: <5%)
- **User Satisfaction Score (CSAT):** Post-query rating (target: 4.5/5+)

#### **Business Impact KPIs**
- **Time Savings per Query:** Average time saved vs. manual retrieval (target: 80% reduction)
- **Finance Team Capacity Shift:** % of time reallocated from retrieval to analysis (target: 30%+)
- **Self-Service Rate:** % of executive queries answered without finance team help (target: 50% by Phase 2)
- **Decision Velocity:** Time from question to decision for financial matters (qualitative tracking)

---

## MVP Scope

The MVP delivers the **complete RAGLite vision** - from foundational retrieval through advanced intelligence capabilities. This comprehensive approach validates the entire system end-to-end, accepting higher complexity and timeline in exchange for proving the full value proposition.

### **Core Features (Must Have)**

#### **Foundation Layer**

**1. Document Ingestion Pipeline**
- **Description:** Automated processing of financial PDFs and Excel files into structured, searchable format
- **Rationale:** Foundation for all capabilities - must handle real company financial reports with tables, charts, and complex layouts
- **Success criteria:** Successfully ingests 100% of monthly financial reports preserving structure and context
- **Technical components:** Docling integration, Excel parsing, chunking strategy, metadata extraction

**2. Vector Database Storage & Retrieval**
- **Description:** Semantic storage with efficient similarity search and hybrid retrieval
- **Rationale:** Enables context-aware retrieval superior to keyword search
- **Success criteria:** Sub-5 second retrieval, 90%+ relevance for top results
- **Technical components:** Qdrant (Docker initially, cloud migration path), embedding model, indexing

**3. Knowledge Graph Integration**
- **Description:** Graph database capturing financial entities and relationships (departments, metrics, time periods, companies)
- **Rationale:** Enables relational reasoning ("How does marketing spend correlate with revenue?")
- **Success criteria:** Successful entity extraction from documents, accurate relationship traversal for queries
- **Technical components:** Neo4j or lightweight graph DB, entity extraction pipeline, hybrid RAG+KG retrieval
- **Note:** Architecture research spike will validate approach before implementation

**4. Advanced Table Understanding**
- **Description:** Deep parsing and understanding of financial tables including multi-level headers, merged cells, calculations
- **Rationale:** Financial data is heavily table-based; accurate extraction is critical
- **Success criteria:** 95%+ accurate extraction of tabular financial data
- **Technical components:** Enhanced Docling configuration, table-aware chunking, structured data extraction

#### **Access Layer**

**5. MCP Server Integration**
- **Description:** Model Context Protocol server exposing RAGLite to LLM clients with tool definitions
- **Rationale:** Seamless integration with Claude Desktop and other MCP-compatible clients
- **Success criteria:** LLM can query via MCP, use tools, receive structured responses
- **Technical components:** FastAPI-based MCP server, tool/function definitions, protocol compliance

**6. Natural Language Query Interface**
- **Description:** Conversational interface supporting complex, multi-step financial questions
- **Rationale:** Core UX - eliminates query language barriers
- **Success criteria:** 90%+ query understanding and accurate responses
- **Technical components:** Query parsing, intent detection, RAG orchestration

**7. Source Attribution & Verification**
- **Description:** All answers include verifiable source references (documents, pages, sections)
- **Rationale:** Critical for financial data trust and compliance
- **Success criteria:** 95%+ source accuracy
- **Technical components:** Metadata tracking, citation formatting, confidence scoring

#### **Intelligence Layer**

**8. Agentic Workflow Orchestration**
- **Description:** Multi-agent system for complex analysis requiring multiple steps, tools, and reasoning paths
- **Rationale:** Financial intelligence requires planning, tool use, and iterative reasoning
- **Success criteria:** Successfully executes multi-step analytical workflows
- **Technical components:** LangGraph OR AWS Bedrock Agents (decided in research spike), custom tools, state management
- **Agents:** Retrieval agent, analysis agent, forecasting agent, synthesis agent

**9. AI-Powered Forecasting**
- **Description:** Automated forecasting of key financial indicators based on historical patterns and trends
- **Rationale:** Predictive insight is core value proposition
- **Success criteria:** Forecasts within ±15% of actuals (refined over time)
- **Technical components:** Time-series extraction, Prophet/statsmodels OR LLM-based forecasting, confidence intervals
- **Forecasting targets:** Revenue, cash flow, key expense categories, custom KPIs

**10. Proactive Insight Generation**
- **Description:** System autonomously identifies anomalies, trends, risks, and opportunities from financial data
- **Rationale:** "Tell me what I should know" vs. "answer what I ask"
- **Success criteria:** 75%+ of insights rated useful/actionable by users
- **Technical components:** Pattern detection algorithms, anomaly detection, trend analysis, LLM-powered synthesis, insight ranking

**11. Strategic Recommendation Engine**
- **Description:** AI generates actionable recommendations on where to focus attention based on financial data
- **Rationale:** From insight to action - highest value intelligence capability
- **Success criteria:** Recommendations align with human expert analysis 80%+ of the time
- **Technical components:** Multi-factor analysis, priority scoring, recommendation templates

#### **Infrastructure & Operations**

**12. Cloud Deployment Architecture**
- **Description:** Production-ready cloud infrastructure (AWS or equivalent)
- **Rationale:** Enable team access, scalability, reliability beyond local development
- **Success criteria:** 99%+ uptime, supports 10+ concurrent users
- **Technical components:** Container orchestration (ECS/EKS), managed vector DB (Qdrant Cloud or OpenSearch), monitoring, logging

**13. Real-Time Document Updates**
- **Description:** Automated detection and re-ingestion of updated financial documents
- **Rationale:** Keep knowledge base current without manual intervention
- **Success criteria:** New/updated documents reflected in queries within 5 minutes
- **Technical components:** File watching, incremental indexing, change detection, update notifications

### **Out of Scope for MVP**

- ❌ **Multi-user authentication & RBAC** - Single-user initially; add auth for team rollout post-MVP
- ❌ **Custom Web UI** - MCP client (Claude Desktop) sufficient; custom interface is Phase 2+
- ❌ **Advanced visualization/dashboards** - Text/conversational interface is primary; viz deferred
- ❌ **Integration with financial systems** (ERP, accounting software) - Start with document-based knowledge
- ❌ **Automated board report generation** - Phase 2 (requires proven insight quality first)
- ❌ **Multi-scenario financial modeling** - Phase 2 advanced capability

### **MVP Success Criteria**

**The MVP is successful if ALL of the following are achieved:**

✅ **Retrieval Excellence:** 90%+ accuracy on 50 diverse financial queries

✅ **Intelligence Validation:** Forecasts and insights demonstrate clear value in at least 3 real-world scenarios

✅ **Agentic Capability:** System successfully handles 10+ multi-step analytical workflows autonomously

✅ **Knowledge Graph Value:** Relational queries (correlations, dependencies) answered accurately using graph traversal

✅ **Performance:** Typical queries <5 sec, complex workflows <30 sec

✅ **Trust:** Source attribution 95%+ accurate; insights are verifiable

✅ **Adoption Readiness:** You use RAGLite for 90%+ of financial queries, replacing manual methods

✅ **Technical Foundation:** Architecture is production-ready for team rollout with minimal refactoring

### **Phased Implementation Strategy (Recommended)**

Given the ambitious scope, sequential validation within the MVP is recommended:

**Phase 1A: Foundation (Weeks 1-3)**
- Document ingestion + Vector DB + Basic retrieval + MCP server
- **Validation checkpoint:** Can we retrieve accurately? If no, fix before proceeding.

**Phase 1B: Knowledge Enhancement (Weeks 4-5)**
- Knowledge graph integration + Advanced table understanding
- **Validation checkpoint:** Does KG improve relational query quality? Quantify improvement.

**Phase 1C: Intelligence Layer (Weeks 6-8)**
- Agentic workflows + Forecasting + Insight generation
- **Validation checkpoint:** Are forecasts/insights useful? Measure accuracy and user value.

**Phase 1D: Production Hardening (Weeks 9-10)**
- Cloud deployment + Real-time updates + Performance optimization
- **Validation checkpoint:** System reliable enough for daily use?

---

## Technical Considerations

This section documents technical direction for the MVP, informed by the upcoming architecture research spike.

### **Platform Requirements**

**Target Deployment:**
- **Development:** Local Docker environment (macOS)
- **MVP Production:** Self-hosted (local server or single cloud instance)
- **Future:** Cloud infrastructure (AWS or equivalent) for team access

**Performance Requirements:**
- **Query Response Time:** <5 seconds (p50), <15 seconds (p95) for standard queries
- **Complex Workflow Time:** <30 seconds for multi-step agentic analysis
- **Document Ingestion:** Process monthly financial report (<100 pages) in <5 minutes
- **Uptime:** 95%+ for MVP (self-hosted), 99%+ for cloud production

**Scalability Requirements (MVP):**
- Support 100+ financial documents in knowledge base
- Handle 50+ queries per day
- Single concurrent user (you)

### **Technology Preferences**

**Document Processing:**
- **Primary:** Docling (https://github.com/docling-project/docling)
  - Proven for complex PDF layouts, tables, charts
  - Needs validation with sample company financial PDFs
  - Embedding model selection will be part of Docling evaluation
- **Backup option:** AWS Textract (if Docling insufficient for table extraction)
- **Excel parsing:** Python libraries (openpyxl, pandas) or specialized tools TBD

**Vector Database:**
- **Primary:** Qdrant (open-source)
  - Docker deployment for MVP
  - Cloud-hosted option (Qdrant Cloud) for production
  - Strong Python SDK and performance characteristics
- **Consideration:** Evaluate storage requirements and indexing performance during research spike

**Knowledge Graph (Pending Research Spike):**
- **Options to evaluate:**
  - Neo4j (industry standard, mature, heavier weight)
  - Lightweight alternatives (SQLite-based graph extensions, in-memory graphs)
  - Hybrid approach (vector DB with metadata relationships vs. separate graph DB)
- **Decision criteria:** Complexity vs. value for financial entity relationships

**LLM Integration:**
- **Primary:** Claude (via Anthropic API or AWS Bedrock)
- **MCP Server:** FastAPI-based implementation
- **Embedding Model:** To be determined during Docling evaluation in research spike
- **Consideration:** Evaluate whether to use single model or specialized models for different tasks

**Agentic Framework (Pending Research Spike):**
- **Option A:** LangGraph
  - Full control, open-source, Python-native
  - Requires building orchestration logic
- **Option B:** AWS Bedrock Agents
  - Managed service, lower DevOps overhead
  - AWS lock-in, less control
- **Option C:** Claude function calling
  - Simplest, no framework needed
  - Limited to what Claude supports natively
- **Decision criteria:** Complexity of workflows vs. development speed vs. control requirements

**Forecasting Approach (Pending Research Spike):**
- **Option A:** LLM-based forecasting (prompt engineering)
- **Option B:** Traditional time-series (Prophet, statsmodels)
- **Option C:** Hybrid (extract data with LLM, forecast with specialized models)
- **Decision criteria:** Accuracy vs. ease of implementation vs. explainability

### **Architecture Considerations**

**Repository Structure:**
- **Decision deferred:** Monorepo vs. multi-repo, service boundaries, and project structure will be determined after completing technical requirements analysis and deep research spike

**Service Architecture:**
- **MVP:** Approach to be determined in research spike (monolithic vs. modular vs. microservices)
- **Future consideration:** Architecture decisions deferred until technical requirements are fully understood

**Integration Requirements:**
- **MCP Protocol:** Compliance with Model Context Protocol specification
- **Data sources:** File system (PDFs, Excel files) for MVP
- **Future integrations:** Cloud storage (S3), financial systems (deferred)

**Security & Compliance:**
- **Data security:**
  - Financial documents remain on controlled infrastructure (no external API uploads)
  - Encryption at rest (for cloud deployment)
  - Secure API keys management (environment variables, secrets manager)
- **Compliance considerations:**
  - Audit logging for queries and answers
  - Data retention policies (TBD based on company requirements)
  - Access controls for production deployment

### **Critical Architecture Decisions Requiring Research Spike**

Before beginning MVP implementation, the following technical decisions must be validated:

1. **Docling PDF Extraction Quality & Embedding Model**
   - Test with sample company financial PDFs
   - Validate table extraction accuracy
   - Select optimal embedding model during Docling evaluation
   - Assess if custom preprocessing needed

2. **Knowledge Graph Necessity & Approach**
   - Benchmark RAG-only vs. Hybrid RAG+KG on sample queries
   - Evaluate entity extraction quality from financial documents
   - Determine if KG complexity is justified by performance gains

3. **Agentic Framework Selection**
   - Define required workflow complexity
   - Compare LangGraph vs. Bedrock Agents vs. simple tool calling
   - Prototype simple multi-step workflow in each approach

4. **Forecasting Implementation Strategy**
   - Inventory KPIs to forecast and data availability
   - Benchmark LLM vs. statistical forecasting accuracy
   - Determine hybrid approach viability

5. **Architecture & Repository Structure**
   - Determine monorepo vs. multi-repo approach
   - Define service boundaries based on validated technical requirements
   - Complete deep research on all technical components before finalizing structure

---

## Constraints & Assumptions

### **Constraints**

**Budget:**
- **Infrastructure:** Minimal cost for MVP (self-hosted Docker, open-source tools)
- **LLM API costs:** Estimated $50-200/month during development (Claude API usage)
- **Cloud costs:** Deferred to post-MVP (migration to cloud after validation)
- **Total MVP budget:** <$500 (primarily API costs)

**Timeline:**
- **Research Spike:** 1-2 weeks (complete before MVP implementation begins)
- **MVP Development:** 8-10 weeks (phased implementation with validation checkpoints)
- **Total time to MVP:** ~10-12 weeks from start of research spike
- **Note:** Timeline assumes development with Claude Code for acceleration

**Resources:**
- **Developer:** Solo developer (you) using Claude Code as AI pair programmer
- **Expertise:** Learning curve on RAG, vector databases, knowledge graphs, agentic frameworks
- **Infrastructure:** Personal development machine (macOS) for MVP
- **Data access:** Company financial PDFs available for testing

**Technical:**
- **Document formats:** PDFs (primary), Excel files (secondary priority)
- **Document complexity:** Financial reports with tables, charts, complex layouts
- **Data volume:** ~12-24 monthly reports initially, growing to 100+ documents
- **Privacy requirement:** Financial data cannot leave controlled infrastructure (no public API uploads during processing)
- **Development environment:** Local/self-hosted only until proven, then cloud migration

### **Key Assumptions**

**Technical Assumptions:**
- Docling can accurately extract text, tables, and structure from company financial PDFs (requires validation in research spike)
- Qdrant vector database performance is sufficient for 100+ document knowledge base
- Embedding models selected during Docling evaluation will provide adequate retrieval quality for financial text
- Claude API (or Bedrock) provides sufficient reasoning capability for analysis and forecasting
- MCP protocol implementation complexity is manageable with available documentation
- Python ecosystem provides necessary libraries for all required functionality

**Product Assumptions:**
- Accurate retrieval (90%+ accuracy) will be immediately valuable even without forecasting/insights
- Natural language query interface is preferred over dashboard/BI tool approach
- Source attribution is critical for financial data trust
- Single-user MVP is sufficient to validate value before team rollout
- MCP client (Claude Desktop) is acceptable interface for MVP vs. custom web UI

**Business Assumptions:**
- Time savings from instant retrieval will justify development investment
- Finance team will adopt tool if it demonstrably saves time
- Executive adoption follows finance team validation, not simultaneous
- MVP success will secure resources for Phase 2 expansion
- Company financial data volume is sufficient to train/validate forecasting models

**User Assumptions:**
- You (primary user) can effectively validate accuracy and usefulness during MVP
- Finance team queries are answerable from document knowledge (vs. requiring live system integration)
- Most valuable questions are historical/contextual (what happened, why) vs. real-time (what's happening now)
- Users will tolerate 5-15 second response times for complex queries

**Data Assumptions:**
- Monthly financial reports contain sufficient historical data for meaningful forecasting
- Financial documents are relatively consistent in structure and terminology
- Tables in PDFs are machine-readable (not scanned images requiring OCR)
- Document quality is good enough for automated processing without extensive manual cleanup

**Organizational Assumptions:**
- Company is supportive of AI experimentation with financial data
- No compliance blockers for self-hosted MVP (regulations allow controlled AI usage)
- Financial data access policies permit this use case
- Team rollout will be gradual, allowing refinement based on feedback

---

## Risks & Open Questions

### **Key Risks**

**1. Technical Complexity Risk (HIGH)**
- **Risk:** MVP scope includes multiple complex, unproven technologies (knowledge graphs, agentic workflows, forecasting) that may not integrate well or deliver expected value
- **Impact:** Development timeline extends significantly, or features must be descoped mid-development
- **Mitigation:**
  - Mandatory research spike before implementation to validate feasibility
  - Phased implementation with validation checkpoints to enable early failure detection
  - Willingness to descope features (e.g., remove KG) if they prove too complex

**2. Document Processing Quality Risk (HIGH)**
- **Risk:** Docling (or alternative tools) cannot accurately extract financial data from company PDFs, especially complex tables and charts
- **Impact:** Retrieval accuracy below acceptable threshold, entire system foundation fails
- **Mitigation:**
  - Test Docling with sample company financial PDFs during research spike (Week 1)
  - Have backup processing approaches ready (AWS Textract, custom parsers)
  - Define acceptable accuracy threshold (90%) and stop/pivot if not achievable

**3. Retrieval Accuracy Risk (MEDIUM-HIGH)**
- **Risk:** Vector similarity search doesn't provide sufficient accuracy for financial queries, leading to wrong answers or missed information
- **Impact:** Users lose trust, system adoption fails
- **Mitigation:**
  - Benchmark multiple embedding models and chunking strategies
  - Implement hybrid search (vector + keyword) if pure semantic search insufficient
  - Strong source attribution allows users to verify answers

**4. Forecasting Accuracy Risk (MEDIUM)**
- **Risk:** AI-generated forecasts are inaccurate or unreliable, undermining intelligence layer value
- **Impact:** Users distrust all AI-generated insights, limit system to retrieval-only usage
- **Mitigation:**
  - Start with simple forecasts (trend projection) before complex modeling
  - Clearly communicate forecast confidence intervals
  - Allow users to provide feedback to improve models over time
  - Consider traditional statistical methods as baseline/fallback

**5. Knowledge Graph Complexity Risk (MEDIUM-HIGH)**
- **Risk:** Building and maintaining knowledge graph adds significant complexity without proportional value for financial queries
- **Impact:** Development time consumed by KG work, other features delayed
- **Mitigation:**
  - Research spike must demonstrate clear KG value vs. RAG-only
  - Start with minimal graph (key entities only), expand if proven valuable
  - Be willing to defer KG to post-MVP if research shows marginal gains

**6. Agentic Workflow Reliability Risk (MEDIUM)**
- **Risk:** Multi-step agentic workflows fail, produce incorrect results, or are too slow for practical use
- **Impact:** Advanced analysis features unusable, system limited to simple Q&A
- **Mitigation:**
  - Start with simple workflows, add complexity incrementally
  - Implement robust error handling and fallback to simpler approaches
  - Claude's native function calling as fallback if complex frameworks fail

**7. Scope Creep Risk (HIGH)**
- **Risk:** Ambitious MVP scope expands further during development, preventing completion
- **Impact:** Never-ending development, no validated system to show
- **Mitigation:**
  - Strict adherence to defined MVP scope
  - Validation checkpoints force go/no-go decisions
  - Track "nice-to-have" features separately for post-MVP consideration

**8. Solo Developer Bandwidth Risk (MEDIUM)**
- **Risk:** Single developer, even with Claude Code, cannot deliver full vision MVP in reasonable timeframe
- **Impact:** Burnout, abandoned project, or significant timeline extension
- **Mitigation:**
  - Realistic timeline expectations (10-12 weeks)
  - Phased approach allows reducing scope if progress slower than expected
  - Claude Code significantly accelerates development vs. traditional coding

**9. Data Privacy/Compliance Risk (LOW-MEDIUM)**
- **Risk:** Company policies or regulations restrict use of LLM APIs with financial data, even self-hosted
- **Impact:** Project blocked or severely constrained
- **Mitigation:**
  - Clarify data usage policies early
  - Consider fully local LLM deployment if API usage prohibited
  - Architecture supports swapping LLM providers if needed

**10. Validation Difficulty Risk (MEDIUM)**
- **Risk:** Hard to objectively measure success (especially insight quality, forecast accuracy) with single user in MVP
- **Impact:** Unclear if system is "good enough" to proceed to team rollout
- **Mitigation:**
  - Define concrete success metrics with numeric thresholds
  - Manual testing with representative query set
  - Track accuracy on known ground truth questions

### **Open Questions**

**Technical Questions:**
1. Can Docling handle our specific financial PDF formats and table structures?
2. Which embedding model provides best retrieval accuracy for financial text?
3. Is knowledge graph integration necessary, or is RAG-only sufficient?
4. Which agentic framework (LangGraph vs. Bedrock vs. simple function calling) best fits our workflow complexity?
5. What forecasting approach (LLM-based vs. statistical vs. hybrid) provides acceptable accuracy?
6. What's the optimal chunking strategy for financial documents (size, overlap, semantic boundaries)?
7. Do we need separate services/repositories, or is monolithic architecture acceptable?

**Product Questions:**
1. What are the 20 most important financial questions users need answered?
2. What forecast accuracy threshold (±10%? ±20%?) is acceptable for MVP?
3. What types of insights are most valuable (anomalies, trends, comparisons, correlations)?
4. How often do financial documents update, and how critical is real-time synchronization?
5. What level of explanation/transparency is needed for AI-generated forecasts and insights?

**Business Questions:**
1. Are there compliance or regulatory constraints on using AI with financial data?
2. What's the approval process for cloud deployment and associated costs post-MVP?
3. Who are the key stakeholders to involve once MVP is ready for demonstration?
4. What success metrics would convince leadership to invest in team rollout?

**Data Questions:**
1. How much historical data exists in accessible digital format (vs. older records that may require digitization)?
2. Are financial PDFs text-based or scanned images requiring OCR?
3. What's the consistency of financial document formats over time (standardized templates vs. varying formats)?
4. Are there sensitive fields that should be excluded or masked?

### **Areas Needing Further Research**

**Priority 1 (Research Spike - Week 1-2):**
1. **Docling PDF extraction validation** - Test on 5-10 sample company financial PDFs
2. **Embedding model benchmarking** - Compare 2-3 models on financial text retrieval
3. **RAG baseline performance** - Build simple RAG pipeline, measure retrieval accuracy
4. **Knowledge graph value assessment** - Test sample queries with and without graph, quantify improvement
5. **Agentic framework comparison** - Prototype simple workflow in LangGraph, Bedrock, and function calling

**Priority 2 (During MVP Development):**
1. **Chunking strategy optimization** - Iterate on chunk size, overlap, and semantic segmentation
2. **Prompt engineering for financial domain** - Optimize prompts for accuracy and format
3. **Forecasting approach selection** - Compare LLM vs. statistical forecasting on sample KPIs
4. **Insight generation quality** - Define and test insight relevance scoring

**Priority 3 (Post-MVP):**
1. **Scalability testing** - Performance with 100+ documents, concurrent users
2. **Cloud deployment architecture** - AWS service selection, cost optimization
3. **Security hardening** - Encryption, access controls, audit logging for production
4. **Advanced table understanding** - If Docling baseline insufficient

---

## Next Steps

### **Immediate Actions**

**1. Complete Technical Research Spike (Week 1-2)**

Conduct comprehensive technical validation before any MVP implementation begins. This spike will inform all major architecture decisions and de-risk the MVP.

**Research Spike Tasks:**

**a) Document Processing Validation**
- Obtain 5-10 representative company financial PDF samples
- Test Docling extraction on each document
- Measure table extraction accuracy (target: 95%+)
- Identify any preprocessing needs or Docling configuration tuning
- Document extraction failures and alternative approaches if needed
- **Go/No-Go Decision:** Is Docling sufficient, or do we need alternatives?

**b) Embedding Model & RAG Baseline**
- Set up basic Qdrant instance (Docker)
- Test 2-3 embedding models as part of Docling evaluation
- Implement simple RAG pipeline (embed → store → retrieve → generate)
- Create test query set (20 representative financial questions with known answers)
- Measure retrieval accuracy for each embedding model
- **Go/No-Go Decision:** Can we achieve 80%+ retrieval accuracy with basic RAG?

**c) Knowledge Graph Value Assessment**
- Manually identify key entities in sample documents (companies, departments, metrics, time periods)
- Test retrieval-only vs. relationship-aware queries
- Prototype lightweight entity extraction (using LLM or spaCy)
- Evaluate whether graph adds meaningful value for target queries
- Estimate implementation complexity (entity extraction, graph DB setup, hybrid retrieval)
- **Decision:** Implement KG in MVP, defer to Phase 2, or skip entirely?

**d) Agentic Framework Comparison**
- Define 2-3 representative multi-step workflows (e.g., "Calculate YoY revenue growth and explain variance")
- Prototype each workflow using:
  - Claude function calling (native)
  - LangGraph (if pursuing full framework)
  - AWS Bedrock Agents (if considering managed approach)
- Compare development complexity, performance, and reliability
- **Decision:** Which framework (if any) for agentic workflows?

**e) Forecasting Approach Exploration**
- Identify 2-3 key metrics to forecast (e.g., monthly revenue, cash flow)
- Extract historical data from sample PDFs
- Test LLM-based forecasting (prompt: "Based on this data, forecast next month")
- Test statistical forecasting (Prophet or simple trend projection)
- Compare accuracy and explainability
- **Decision:** LLM-based, statistical, or hybrid forecasting approach?

**f) Architecture & Repository Structure**
- Based on findings from a-e, design system architecture
- Decide: Monorepo vs. multi-repo
- Define service boundaries (if any)
- Document data flow and component interactions
- Create skeleton project structure
- **Deliverable:** Architecture decision document and initial repo setup

**Research Spike Deliverables:**
- Technical feasibility report with go/no-go recommendations for each major component
- Chosen embedding model and performance benchmarks
- Decision on knowledge graph inclusion (yes/no/defer)
- Selected agentic framework (if any)
- Forecasting implementation strategy
- Initial architecture diagram and repository structure
- Updated MVP scope based on research findings (descope if necessary)

**2. Gather Sample Financial Documents (Week 1)**
- Collect 10-20 representative monthly financial PDFs from company archives
- Ensure documents cover various time periods and report types
- Validate that PDFs are text-based (not scanned images)
- Organize documents for testing and validation

**3. Define Ground Truth Query Set (Week 1-2)**
- Create list of 50 representative financial questions spanning:
  - Simple retrieval ("What was Q3 marketing spend?")
  - Multi-document synthesis ("Compare Q3 vs Q2 revenue")
  - Analytical questions ("What drove the variance in operating expenses?")
  - Relational queries ("How does headcount growth correlate with revenue?")
- Document known correct answers for validation
- Prioritize questions by importance to actual use cases

**4. Set Up Development Environment (Week 1)**
- Install Docker Desktop
- Clone/create RAGLite repository
- Set up Python environment and dependencies
- Configure Claude API or Bedrock access
- Install development tools (IDE, git, etc.)
- Create basic project README

**5. Stakeholder Alignment (Week 2)**
- Review this Project Brief with key stakeholders (if applicable)
- Clarify data usage policies and compliance requirements
- Confirm access to necessary financial documents
- Set expectations for MVP timeline and success criteria
- Identify who should receive MVP demonstration when ready

### **MVP Implementation Roadmap (Post Research Spike)**

Assuming research spike validates feasibility, proceed with phased MVP implementation:

**Phase 1A: Foundation (Weeks 3-5)**
- Document ingestion pipeline (Docling integration)
- Vector database setup (Qdrant)
- Basic RAG retrieval
- MCP server implementation
- Source attribution
- **Validation:** Can answer simple retrieval queries accurately?

**Phase 1B: Knowledge Enhancement (Weeks 5-7)**
- Knowledge graph integration (if research spike recommends)
- Advanced table understanding
- Context synthesis across documents
- **Validation:** Can handle complex multi-document queries?

**Phase 1C: Intelligence Layer (Weeks 7-9)**
- Agentic workflow implementation
- Forecasting capability
- Insight generation
- Strategic recommendations
- **Validation:** Are forecasts/insights useful and accurate?

**Phase 1D: Production Readiness (Weeks 10-12)**
- Cloud deployment (if pursuing)
- Real-time document updates
- Performance optimization
- Error handling and reliability improvements
- Documentation and user guide
- **Validation:** System ready for daily use?

### **PM Handoff**

This Project Brief provides comprehensive context for **RAGLite** - an AI-powered financial intelligence platform that combines retrieval, analysis, and forecasting capabilities to transform how the organization interacts with financial data.

**Critical Context for Next Phase:**

1. **Research spike is mandatory** before any implementation - too many unknowns to proceed without validation
2. **Ambitious MVP scope** - includes full vision (retrieval + intelligence), high complexity, requires phased approach with validation checkpoints
3. **Solo developer + Claude Code** - timeline assumes AI-accelerated development
4. **Self-hosted MVP** - cloud migration deferred to post-validation
5. **Be prepared to descope** - if research spike reveals blockers, reduce MVP scope rather than extend timeline indefinitely

**When working with the PM (Product Manager agent):**
- Start in **PRD Generation Mode** to translate this brief into detailed product requirements
- Ensure PRD reflects research spike findings and any scope adjustments
- Maintain focus on MVP delivery, deferring post-MVP speculation
- Validate all technical decisions against research spike outcomes

**Recommendation:** Begin with technical research spike immediately. Schedule PRD creation session after spike completion, informed by validated architecture decisions.

---

*Generated with Claude Code*
