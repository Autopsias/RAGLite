# Microservices Architecture

## Service Overview

RAGLite consists of **5 independent microservices**, each exposing MCP tools:

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Gateway (FastMCP Aggregator)                           │
│  Route: /mcp/tools                                          │
│  Aggregates: M1 + M2 + M3 + M4 + M5 tool catalogs          │
└──┬────┬────┬────┬────┬──────────────────────────────────────┘
   │    │    │    │    │
   │    │    │    │    └─────────────────────┐
   │    │    │    │                           │
   │    │    │    └──────────────┐            │
   │    │    │                   │            │
   │    │    └───────┐           │            │
   │    │            │           │            │
   │    └─────┐      │           │            │
   │          │      │           │            │
┌──▼───┐ ┌───▼──┐ ┌─▼────┐ ┌───▼───┐ ┌─────▼─────┐
│  M1  │ │  M2  │ │  M3  │ │  M4   │ │    M5     │
│Ingest│ │Retrie│ │Graph │ │Foreca │ │ Insights  │
│      │ │val   │ │RAG   │ │st     │ │           │
└──┬───┘ └───┬──┘ └─┬────┘ └───┬───┘ └─────┬─────┘
   │         │      │          │           │
   └─────────┴──────┴──────────┴───────────┘
                    │
         ┌──────────▼──────────────────┐
         │  Shared Data Layer          │
         │  ├─ Qdrant (Vector DB)      │
         │  ├─ Neo4j (Graph - Phase 2) │
         │  └─ S3 (Documents)          │
         └─────────────────────────────┘
```

## Microservice #1: Ingestion Service

**Port:** 5001
**MCP Path:** `/mcp/ingestion`
**Technology:** FastMCP + Docling + Fin-E5

**Responsibilities:**
1. PDF extraction (Docling) with 97.9% table accuracy
2. Excel parsing (openpyxl + pandas)
3. Contextual chunking (LLM-generated context per chunk)
4. Embedding generation (Fin-E5 model)
5. Vector storage (Qdrant)
6. Metadata extraction and indexing

**MCP Tools Exposed:**

```python
@mcp.tool()
async def ingest_document(file_path: str, document_type: str) -> IngestionJobID:
    """
    Trigger document ingestion pipeline.

    Args:
        file_path: Path to PDF or Excel file
        document_type: "financial_report" | "earnings_transcript" | "excel_data"

    Returns:
        job_id for status tracking
    """

@mcp.tool()
async def get_ingestion_status(job_id: str) -> IngestionStatus:
    """
    Check ingestion job progress.

    Returns:
        status, progress_pct, chunks_processed, errors
    """

@mcp.tool()
async def list_indexed_documents() -> List[Document]:
    """
    List all successfully ingested documents with metadata.

    Returns:
        document_id, filename, type, ingestion_date, chunk_count
    """
```

**Architecture Pattern:**

```
┌────────────────────────────────────────────────┐
│  Ingestion Service (FastMCP Server)           │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  MCP Tool Handler Layer                  │ │
│  │  - ingest_document()                     │ │
│  │  - get_ingestion_status()                │ │
│  │  - list_indexed_documents()              │ │
│  └────────────┬─────────────────────────────┘ │
│               │                                │
│  ┌────────────▼─────────────────────────────┐ │
│  │  Async Worker Pool (Celery/RQ)          │ │
│  │  - Long-running ingestion tasks          │ │
│  │  - Progress reporting via MCP progress() │ │
│  └────────────┬─────────────────────────────┘ │
│               │                                │
│  ┌────────────▼─────────────────────────────┐ │
│  │  Processing Pipeline                     │ │
│  │  1. Docling PDF/Excel extraction         │ │
│  │  2. Contextual chunking (Claude API)     │ │
│  │  3. Fin-E5 embedding generation          │ │
│  │  4. Qdrant vector storage                │ │
│  └────────────┬─────────────────────────────┘ │
└───────────────┼─────────────────────────────┐┘
                │
┌───────────────▼─────────────────────────────┐
│  Data Layer                                 │
│  ├─ Qdrant: Store embeddings + metadata    │
│  └─ S3: Store original documents + chunks  │
└─────────────────────────────────────────────┘
```

**Performance Targets:**
- Ingestion: <5 minutes for 100-page financial report (NFR2)
- Concurrent jobs: 3+ documents simultaneously
- Error rate: <3% for well-formed documents

---

## Microservice #2: Retrieval Service

**Port:** 5002
**MCP Path:** `/mcp/retrieval`
**Technology:** FastMCP + Qdrant + Fin-E5

**Responsibilities:**
1. Vector similarity search (semantic retrieval)
2. Contextual retrieval (leverage pre-generated contexts)
3. BM25 hybrid search (if needed for Phase 1 optimization)
4. Source attribution (document, page, section)
5. Result ranking and reranking

**MCP Tools Exposed:**

```python
@mcp.tool()
async def search_documents(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict] = None,
    rerank: bool = True
) -> SearchResults:
    """
    Semantic search across indexed financial documents.

    Args:
        query: Natural language financial question
        top_k: Number of results to return (default 10)
        filters: Optional metadata filters (date_range, document_type)
        rerank: Apply reranking for improved accuracy

    Returns:
        chunks with content, source attribution, relevance scores
    """

@mcp.tool()
async def get_document_chunks(
    document_id: str,
    section: Optional[str] = None
) -> List[Chunk]:
    """
    Retrieve specific chunks from a document by section.

    Args:
        document_id: Unique document identifier
        section: Optional section filter (e.g., "Revenue Analysis")

    Returns:
        chunks with full context and metadata
    """
```

**Retrieval Flow:**

```
User Query: "What drove Q3 revenue variance?"
            │
            ▼
┌───────────────────────────────────────────────┐
│ 1. Query Embedding (Fin-E5)                  │
│    - Generate 1024-dim vector for query      │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 2. Vector Search (Qdrant)                    │
│    - HNSW similarity search                   │
│    - Apply metadata filters if provided      │
│    - Return top 20 candidates                 │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 3. Contextual Enhancement                    │
│    - Prepend LLM-generated context to chunks │
│    - Improves downstream LLM interpretation  │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 4. Optional Reranking                        │
│    - Cross-encoder reranking for top 20      │
│    - Return top 10 highest relevance         │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 5. Source Attribution                        │
│    - Attach (document, page, section) refs   │
│    - Format citations                        │
└───────────────┬───────────────────────────────┘
                │
                ▼
        Return SearchResults to caller
```

**Performance Targets:**
- Query response: <5 sec (p50), <15 sec (p95) - NFR13
- Retrieval accuracy: 90%+ on ground truth test set (NFR6)
- Source attribution accuracy: 95%+ (NFR7)

---

## Microservice #3: GraphRAG Service (Phase 2 - Conditional)

**Port:** 5003
**MCP Path:** `/mcp/graphrag`
**Technology:** FastMCP + Neo4j + Claude API (for entity extraction & agent navigation)

**⚠️ IMPLEMENTATION CONDITIONAL ON PHASE 1 RESULTS:**
- Only implement if Contextual Retrieval achieves <95% accuracy on multi-hop queries
- Decision gate: Week 4 of development after Contextual Retrieval validation

**Responsibilities (if implemented):**
1. Entity extraction (companies, departments, metrics, KPIs, time periods)
2. Knowledge graph construction (relationships, hierarchies, correlations)
3. Community detection (Microsoft GraphRAG approach)
4. Agentic graph navigation (multi-hop reasoning)
5. Graph updates (incremental when new documents ingested)

**MCP Tools Exposed (if implemented):**

```python
@mcp.tool()
async def navigate_graph(
    query: str,
    max_hops: int = 3,
    entities: Optional[List[str]] = None
) -> GraphNavigationResult:
    """
    Navigate knowledge graph for multi-hop relational queries.

    Args:
        query: Relational question (e.g., "How does marketing correlate with revenue?")
        max_hops: Maximum graph traversal depth
        entities: Optional seed entities to start traversal

    Returns:
        traversal_path, related_entities, relationships, supporting_data
    """

@mcp.tool()
async def find_correlations(
    entity_a: str,
    entity_b: str,
    time_range: Optional[DateRange] = None
) -> CorrelationResult:
    """
    Discover relationships between financial entities.

    Args:
        entity_a: First entity (e.g., "Marketing Spend")
        entity_b: Second entity (e.g., "Revenue Growth")
        time_range: Optional temporal filter

    Returns:
        correlation_strength, causal_indicators, time_series_data
    """

@mcp.tool()
async def build_graph(document_ids: List[str]) -> GraphBuildJobID:
    """
    Trigger knowledge graph construction for documents.

    Args:
        document_ids: Documents to extract entities and build graph from

    Returns:
        job_id for async graph construction tracking
    """
```

**GraphRAG Architecture (if implemented):**

```
┌────────────────────────────────────────────────┐
│  GraphRAG Service (FastMCP Server)            │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  MCP Tool Handler Layer                  │ │
│  │  - navigate_graph()                      │ │
│  │  - find_correlations()                   │ │
│  │  - build_graph()                         │ │
│  └────────────┬─────────────────────────────┘ │
│               │                                │
│  ┌────────────▼─────────────────────────────┐ │
│  │  Graph Agent Navigator                   │ │
│  │  - LLM-powered traversal planning        │ │
│  │  - Multi-hop query decomposition         │ │
│  │  - Community summary retrieval           │ │
│  └────────────┬─────────────────────────────┘ │
│               │                                │
│  ┌────────────▼─────────────────────────────┐ │
│  │  Graph Construction Pipeline             │ │
│  │  1. Entity extraction (Claude API)       │ │
│  │  2. Relationship extraction               │ │
│  │  3. Community detection (Louvain)        │ │
│  │  4. Hierarchical summarization (LLM)     │ │
│  └────────────┬─────────────────────────────┘ │
└───────────────┼─────────────────────────────┐┘
                │
┌───────────────▼─────────────────────────────┐
│  Data Layer                                 │
│  └─ Neo4j: Knowledge graph storage          │
│     - Nodes: Entities (Company, Metric...)  │
│     - Edges: Relationships (CORRELATES...)  │
│     - Properties: Metadata, temporal data   │
└─────────────────────────────────────────────┘
```

**Cost (if implemented):**
- Graph construction: $9 one-time for 100 documents
- Multi-hop queries: $0.02 per query (2 LLM calls per hop average)

**Fallback Strategy:**
- If graph construction fails → Degrade to Contextual Retrieval (Service M2)
- If graph traversal fails → Return vector search results
- System continues operating without graph functionality (NFR32)

---

## Microservice #4: Forecasting Service

**Port:** 5004
**MCP Path:** `/mcp/forecasting`
**Technology:** FastMCP + Prophet + Claude API

**Responsibilities:**
1. Time-series data extraction from documents
2. Statistical baseline forecasting (Prophet/ARIMA)
3. LLM-based forecast adjustment
4. Confidence interval calculation
5. Forecast accuracy tracking

**MCP Tools Exposed:**

```python
@mcp.tool()
async def forecast_kpi(
    metric: str,
    horizon: int = 4,
    method: str = "hybrid"
) -> ForecastResult:
    """
    Generate financial forecast for specified KPI.

    Args:
        metric: KPI to forecast (e.g., "Revenue", "Cash Flow", "Marketing Spend")
        horizon: Number of periods ahead (quarters or months)
        method: "statistical" | "llm" | "hybrid" (default: hybrid)

    Returns:
        forecast_values, confidence_intervals, accuracy_estimate, rationale
    """

@mcp.tool()
async def update_forecast(
    metric: str,
    new_data: TimeSeriesData
) -> UpdatedForecast:
    """
    Refresh forecast with newly ingested data.

    Args:
        metric: KPI being forecasted
        new_data: Latest time-series data points

    Returns:
        updated_forecast, accuracy_comparison, data_quality_score
    """

@mcp.tool()
async def get_forecast_accuracy(
    metric: str,
    lookback_periods: int = 4
) -> AccuracyMetrics:
    """
    Evaluate historical forecast accuracy.

    Args:
        metric: KPI to analyze
        lookback_periods: How many past forecasts to evaluate

    Returns:
        mae, rmse, mape, forecast_vs_actuals
    """
```

**Hybrid Forecasting Flow:**

```
User Request: "Forecast Q4 2025 revenue"
            │
            ▼
┌───────────────────────────────────────────────┐
│ 1. Extract Time-Series Data                  │
│    - Query documents for historical revenue   │
│    - Normalize to quarterly intervals         │
│    - Validate data quality                    │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 2. Statistical Baseline (Prophet)            │
│    - Fit time-series model                    │
│    - Generate forecast with confidence        │
│    - Handle seasonality, trends               │
│    - Error: ±10-13% typically                 │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 3. LLM Contextual Adjustment (Claude)        │
│    - Provide baseline forecast + context      │
│    - LLM considers qualitative factors        │
│    - Adjust forecast based on reasoning       │
│    - Residual correction approach             │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 4. Hybrid Result                             │
│    - Combined forecast: ±8% error             │
│    - Confidence intervals                     │
│    - Rationale from LLM                       │
│    - Meets NFR10 target (±15%)                │
└───────────────┬───────────────────────────────┘
                │
                ▼
        Return ForecastResult
```

**Performance Targets:**
- Forecast accuracy: ±8% (beats ±15% PRD target)
- Generation time: <10 seconds
- Cost: $0.015 per forecast

---

## Microservice #5: Insights Service

**Port:** 5005
**MCP Path:** `/mcp/insights`
**Technology:** FastMCP + Claude API + Statistical analysis libraries

**Responsibilities:**
1. Anomaly detection (statistical thresholds, outlier identification)
2. Trend analysis (growth patterns, cyclical trends)
3. Strategic recommendations (LLM-powered)
4. Insight priority ranking
5. Proactive alert generation

**MCP Tools Exposed:**

```python
@mcp.tool()
async def generate_insights(
    scope: str = "all",
    priority_threshold: str = "medium"
) -> InsightsList:
    """
    Generate proactive financial insights from indexed data.

    Args:
        scope: "all" | "risks" | "opportunities" | "anomalies" | "trends"
        priority_threshold: "low" | "medium" | "high" | "critical"

    Returns:
        insights with category, priority, evidence, recommendations
    """

@mcp.tool()
async def analyze_anomalies(
    time_range: DateRange,
    sensitivity: float = 2.0
) -> AnomalyReport:
    """
    Detect and explain financial anomalies.

    Args:
        time_range: Period to analyze
        sensitivity: Standard deviations for anomaly threshold (default: 2.0)

    Returns:
        anomalies with magnitude, context, potential causes
    """

@mcp.tool()
async def get_recommendations(
    focus_area: Optional[str] = None
) -> RecommendationList:
    """
    Strategic recommendations based on financial analysis.

    Args:
        focus_area: Optional filter (e.g., "cost_reduction", "revenue_growth")

    Returns:
        recommendations with rationale, impact_estimate, supporting_data
    """
```

**Insight Generation Architecture:**

```
Scheduled Job (Daily) or User Request
            │
            ▼
┌───────────────────────────────────────────────┐
│ 1. Data Aggregation                          │
│    - Query recent financial data              │
│    - Pull forecasts, trends, anomalies        │
│    - Gather external context (if available)   │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 2. Statistical Analysis                      │
│    - Anomaly detection (Z-score, IQR)        │
│    - Trend identification (linear regression)│
│    - Correlation analysis                    │
│    - Variance decomposition                  │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 3. LLM Strategic Reasoning (Claude)          │
│    - Interpret statistical findings           │
│    - Generate strategic insights              │
│    - Provide actionable recommendations      │
│    - Rank by priority and impact              │
└───────────────┬───────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│ 4. Insight Ranking & Filtering               │
│    - Score by priority (critical→low)         │
│    - Filter by user threshold                 │
│    - Attach supporting evidence               │
└───────────────┬───────────────────────────────┘
                │
                ▼
        Return InsightsList
```

**Performance Targets:**
- Insight quality: 75%+ rated useful/actionable by user
- Recommendation alignment: 80%+ match expert analysis
- Generation time: <15 seconds for comprehensive analysis

---

## MCP Gateway (Service Aggregator)

**Port:** 5000
**MCP Path:** `/mcp`
**Technology:** FastMCP

**Purpose:**
Aggregates all 5 microservices into a unified MCP server, exposing a single tool catalog to MCP clients.

**Implementation:**

```python
