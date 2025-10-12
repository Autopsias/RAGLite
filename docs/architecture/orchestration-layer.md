# Orchestration Layer

## AWS Strands Multi-Agent Architecture

The orchestration layer uses **AWS Strands** to coordinate complex workflows across microservices. Strands agents call MCP tools exposed by services and use LLM reasoning to interpret results.

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  AWS Strands Agent System                                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Supervisor Agent (Orchestrator)                       │ │
│  │  - Receives user query via MCP client                  │ │
│  │  - Decomposes into sub-tasks                           │ │
│  │  - Delegates to specialized agents                     │ │
│  │  - Synthesizes final response                          │ │
│  └──┬────────┬────────┬────────┬────────────────────────┬─┘ │
│     │        │        │        │                        │   │
│  ┌──▼───┐ ┌─▼────┐ ┌─▼─────┐ ┌▼────────┐ ┌────────────▼─┐ │
│  │Retrie││Analys││GraphR ││Forecast ││ Synthesis    │ │
│  │val   ││is    ││AG     ││         ││ Agent        │ │
│  │Agent ││Agent ││Agent  ││Agent    ││              │ │
│  └──┬───┘ └─┬────┘ └─┬─────┘ └┬────────┘ └────────────┬─┘ │
│     │       │        │        │                        │   │
│     │       │        │        │                        │   │
│  Calls   Interpre Navigate  Generate               Combine│
│  M2      ts data  s M3      s M4                  results│
│  tools   (LLM)    tools     tools                          │
└─────┴───────┴────────┴────────┴──────────────────────────┴─┘
       │       │        │        │                        │
       ▼       ▼        ▼        ▼                        ▼
    MCP Gateway (calls appropriate microservice tools)
```

## Agent Definitions

### 1. Retrieval Agent

**Purpose:** Retrieve relevant financial data from documents

**Tools Used:**
- `search_documents()` from Retrieval Service (M2)
- `get_document_chunks()` from Retrieval Service (M2)

**System Prompt:**
```
You are a Retrieval Agent specialized in finding relevant financial information.

Your capabilities:
- Semantic search across financial documents
- Understanding financial terminology and context
- Extracting specific data points with source attribution

When given a query:
1. Formulate effective search queries
2. Call search_documents() tool with appropriate parameters
3. Return retrieved chunks with clear source citations
4. If initial results insufficient, refine search strategy

Always prioritize accuracy and source attribution.
```

**Example Flow:**
```
User Query: "What drove Q3 revenue variance?"

Retrieval Agent:
1. Calls search_documents(query="Q3 revenue variance drivers", top_k=10)
2. Receives 10 chunks with financial data
3. Returns results to Supervisor with source citations
```

### 2. Analysis Agent

**Purpose:** Interpret financial data using LLM reasoning

**Tools Used:**
- No direct tool calls (pure LLM reasoning)
- Receives data from Retrieval Agent or GraphRAG Agent

**System Prompt:**
```
You are a Financial Analysis Agent specialized in interpreting financial data.

Your capabilities:
- Understanding complex financial relationships
- Calculating financial ratios and metrics
- Identifying trends, patterns, and anomalies
- Explaining variance drivers

When given financial data:
1. Analyze the data using financial domain knowledge
2. Identify key insights and drivers
3. Provide clear, actionable interpretations
4. Quantify findings where possible

Use proper financial terminology and provide reasoning steps.
```

**Example Flow:**
```
Input from Retrieval Agent:
- Q3 2024 revenue: $5.2M (down 12% QoQ)
- Q3 2024 marketing spend: $800K (down 30% QoQ)
- Q2 2024 revenue: $5.9M
- Q2 2024 marketing spend: $1.1M

Analysis Agent:
1. Calculates correlation: Revenue drop 12%, Marketing drop 30%
2. Identifies potential causation: Marketing reduction may drive revenue decline
3. Contextualizes: ROI implications (marketing efficiency analysis)
4. Returns interpretation: "Q3 revenue variance primarily driven by 30%
   marketing spend reduction. Revenue declined 12% despite marketing ROI
   remaining stable at ~$6.50 per marketing dollar."
```

### 3. GraphRAG Agent (Phase 2 - Conditional)

**Purpose:** Navigate knowledge graph for multi-hop relational queries

**Tools Used:**
- `navigate_graph()` from GraphRAG Service (M3)
- `find_correlations()` from GraphRAG Service (M3)

**System Prompt:**
```
You are a GraphRAG Agent specialized in multi-hop relational reasoning.

Your capabilities:
- Navigate knowledge graph to discover relationships
- Answer complex queries requiring multiple entity connections
- Identify correlations and causal patterns
- Synthesize information across graph paths

When given a relational query:
1. Identify key entities and relationships needed
2. Plan graph traversal strategy (which hops, which paths)
3. Call navigate_graph() or find_correlations() tools
4. Interpret graph results in context of user question
5. Return findings with evidence from graph traversal

Prioritize accuracy over speed. Explain traversal logic.
```

**Example Flow (if implemented):**
```
User Query: "How does marketing spend correlate with revenue growth
            across all departments?"

GraphRAG Agent:
1. Identifies entities: "Marketing Spend", "Revenue Growth", [Departments]
2. Calls navigate_graph(
     query="marketing_spend correlation revenue_growth",
     max_hops=3
   )
3. Receives graph path:
   Marketing Spend → Department A → Revenue Growth: +0.73 correlation
   Marketing Spend → Department B → Revenue Growth: +0.45 correlation
   Marketing Spend → Department C → Revenue Growth: -0.12 correlation
4. Interprets: "Strong positive correlation in Dept A (0.73), moderate in
   Dept B (0.45), weak negative in Dept C (-0.12). Suggests marketing
   effectiveness varies significantly by department."
5. Returns analysis to Supervisor
```

### 4. Forecast Agent

**Purpose:** Generate predictive insights for financial KPIs

**Tools Used:**
- `forecast_kpi()` from Forecasting Service (M4)
- `update_forecast()` from Forecasting Service (M4)

**System Prompt:**
```
You are a Forecast Agent specialized in financial predictions.

Your capabilities:
- Generate forecasts for revenue, expenses, cash flow, KPIs
- Provide confidence intervals and accuracy estimates
- Explain forecast rationale and assumptions
- Update forecasts with new data

When asked to forecast:
1. Identify the specific metric and horizon
2. Call forecast_kpi() tool with appropriate parameters
3. Interpret forecast results with confidence intervals
4. Explain methodology and key assumptions
5. Note any data quality limitations

Always provide context for forecast reliability.
```

**Example Flow:**
```
User Query: "What's the Q4 2025 revenue forecast?"

Forecast Agent:
1. Calls forecast_kpi(metric="Revenue", horizon=1, method="hybrid")
2. Receives:
   - Forecast: $5.8M
   - Confidence Interval: [$5.2M, $6.4M]
   - Accuracy Estimate: ±8%
   - Rationale: "Based on Q1-Q3 trend (12% growth) + qualitative
                 adjustment for seasonal patterns"
3. Returns to user: "Q4 2025 revenue forecast: $5.8M (range: $5.2M-$6.4M,
   ±8% typical error). Forecast assumes continued quarterly growth trend
   observed in first 3 quarters, adjusted for typical Q4 seasonality."
```

### 5. Synthesis Agent

**Purpose:** Combine results from multiple agents into coherent answer

**Tools Used:**
- No direct tool calls (aggregation and synthesis)

**System Prompt:**
```
You are a Synthesis Agent responsible for combining multi-agent findings.

Your capabilities:
- Integrate results from retrieval, analysis, graph, forecast agents
- Resolve conflicting information
- Create coherent, comprehensive responses
- Maintain source attribution across all findings

When given results from multiple agents:
1. Identify key insights from each agent
2. Synthesize into a unified narrative
3. Preserve all source citations
4. Structure response for clarity (summary → details → sources)
5. Flag any uncertainties or conflicts

Prioritize clarity and completeness.
```

**Example Flow:**
```
Inputs from agents:
- Retrieval Agent: Q3 revenue data with citations
- Analysis Agent: Variance interpretation (marketing driver)
- Forecast Agent: Q4 forecast based on trend

Synthesis Agent:
1. Combines findings:
   "Q3 2024 revenue declined 12% to $5.2M, primarily driven by a 30%
    reduction in marketing spend (Analysis: marketing ROI remained stable
    at $6.50 per dollar). Based on this trend and Q4 seasonality, forecasted
    Q4 revenue is $5.8M (±8% confidence interval: $5.2M-$6.4M)."

2. Adds source attribution:
   "Sources: Q3_Financial_Report.pdf (p.3, Revenue section),
    Q3_Marketing_Analysis.xlsx (Marketing Spend tab)"

3. Returns complete answer to user
```

## Multi-Agent Workflow Example

**Complex User Query:**
```
"Why did Q3 revenue drop, and what should we expect for Q4?"
```

**Orchestration Flow:**

```
User Query → Supervisor Agent (AWS Strands)
    │
    ├─> Task Decomposition:
    │   1. Find Q3 revenue data (Retrieval)
    │   2. Explain variance drivers (Analysis + optional GraphRAG)
    │   3. Generate Q4 forecast (Forecast)
    │   4. Synthesize complete answer (Synthesis)
    │
    ├─> Step 1: Retrieval Agent
    │   ├─ Calls search_documents("Q3 revenue variance")
    │   └─ Returns: Q3 revenue $5.2M (-12% QoQ), marketing $800K (-30% QoQ)
    │
    ├─> Step 2: Analysis Agent
    │   ├─ Receives data from Retrieval Agent
    │   └─ Interprets: "Revenue drop primarily driven by marketing reduction"
    │
    ├─> Step 2b: GraphRAG Agent (OPTIONAL - Phase 2)
    │   ├─ If needed for deeper relational analysis
    │   ├─ Calls navigate_graph("marketing revenue correlation")
    │   └─ Returns: Department-level correlation data
    │
    ├─> Step 3: Forecast Agent
    │   ├─ Calls forecast_kpi(metric="Revenue", horizon=1)
    │   └─ Returns: Q4 forecast $5.8M (±8%)
    │
    └─> Step 4: Synthesis Agent
        ├─ Combines all findings
        ├─ Preserves source citations
        └─ Returns to user:
            "Q3 revenue declined 12% to $5.2M, primarily due to 30%
             marketing spend reduction. Marketing ROI remained stable at
             $6.50 per dollar. Q4 forecast: $5.8M (confidence range:
             $5.2M-$6.4M, ±8%). Suggests recovery if marketing spend
             resumes normal levels.

             Sources: Q3_Financial_Report.pdf (p.3),
             Q3_Marketing_Analysis.xlsx"
```

**Agent Coordination Benefits:**
- **Parallel execution:** Retrieval + GraphRAG can run simultaneously
- **Specialization:** Each agent optimized for specific reasoning type
- **Graceful degradation:** If GraphRAG unavailable, workflow continues with Retrieval + Analysis
- **LLM flexibility:** AWS Strands allows testing Claude, GPT-4, Gemini without code changes

## AWS Strands Configuration

```python
