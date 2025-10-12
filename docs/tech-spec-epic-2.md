# Technical Specification: Epic 2 - Advanced Document Understanding (GraphRAG)

**Epic:** Epic 2 - Advanced Document Understanding
**Phase:** Phase 2 (Weeks 5-8) - **CONDITIONAL**
**Goal:** Handle complex tables, multi-document synthesis, and relational reasoning via Knowledge Graph
**Status:** NOT STARTED (Conditional on Phase 1 decision gate)
**Version:** 1.0
**Date:** 2025-10-12
**Author:** Sarah (Product Owner)

---

## 1. Executive Summary

**⚠️ CONDITIONAL EPIC:** Only implement if Phase 1 accuracy <80% due to multi-hop/relational query failures.

Epic 2 adds Knowledge Graph (Neo4j) to enable relational reasoning, advanced table extraction, and multi-document synthesis. This addresses complex financial queries requiring entity relationships (e.g., "How does marketing spend correlate with revenue across Q2-Q4?").

**Target:** ~300-400 additional lines of Python code
**Timeline:** 4 weeks (conditional on Phase 1 decision gate)
**Decision Gate:** End of Week 5 → GO/NO-GO for Epic 2

---

## 2. Architecture Overview

### 2.1 Hybrid RAG + Knowledge Graph Architecture

```
┌─────────────────────────────────────────────────────────┐
│  RAGLite Monolithic Server (main.py)                   │
│                                                         │
│  ┌────────────────────────────────────────────────────┐│
│  │  MCP Tools Layer                                   ││
│  │  • query_financial_documents() (Epic 1 ✅)        ││
│  │  • query_with_graph() (Epic 2 - NEW)              ││
│  └────────────────────────────────────────────────────┘│
│                                                         │
│  ┌────────────────────────────────────────────────────┐│
│  │  Ingestion Module                                  ││
│  │  ├─ pipeline.py (Epic 1 ✅)                       ││
│  │  ├─ entity_extraction.py (NEW ~100 lines)         ││
│  │  └─ graph_builder.py (NEW ~100 lines)             ││
│  │                                                    ││
│  │  Retrieval Module                                  ││
│  │  ├─ search.py (Epic 1 ✅)                         ││
│  │  └─ hybrid_search.py (NEW ~100 lines)             ││
│  └────────────────────────────────────────────────────┘│
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│  Data Layer                                             │
│  ├─ Qdrant (Vector DB) ✅                              │
│  └─ Neo4j (Knowledge Graph) - NEW (Docker)             │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Key Decision: When to Use Graph vs Vector-Only

**Graph-Enhanced Queries (trigger hybrid retrieval):**
- Entity relationships: "correlation between X and Y"
- Multi-hop reasoning: "Which departments increased hiring after revenue growth?"
- Temporal sequences: "Compare Q2 → Q3 → Q4 trends"

**Vector-Only Queries (skip graph):**
- Simple factual retrieval: "What was Q3 revenue?"
- Single-document extraction: "List all safety incidents in 2024"

---

## 3. Component Specifications

### 3.1 Entity Extraction (raglite/ingestion/entity_extraction.py ~100 lines)

**Purpose:** Extract financial entities (companies, metrics, departments, time periods) from documents using LLM-based extraction.

**Key Function:**
```python
async def extract_entities(chunk: ChunkMetadata) -> List[Entity]:
    """Extract entities from chunk using Claude API.

    Args:
        chunk: Document chunk with text content

    Returns:
        List of Entity objects (company, metric, department, time_period, amount)

    Entity Types:
        - COMPANY: Company names, subsidiaries
        - METRIC: KPIs, performance indicators (revenue, profit, headcount)
        - DEPARTMENT: Business units, divisions
        - TIME_PERIOD: Quarters, fiscal years, dates
        - AMOUNT: Dollar amounts, percentages
    """
```

**Implementation Approach:**
- Use Claude Haiku for fast, cheap entity extraction
- Prompt engineering: Few-shot examples for financial entity recognition
- Store entities with normalization (e.g., "Q3 2024" = "Third Quarter 2024")
- Entity metadata: source_document, page_number, confidence_score

**NFRs:**
- Entity extraction accuracy: 85%+ (manual validation on sample docs)
- Processing time: <2s per chunk (acceptable for batch ingestion)

**Testing:**
- Unit tests: Mock Claude API, validate entity types
- Integration tests: Extract entities from real financial PDFs
- Accuracy tests: Manual validation on 50+ entities

---

### 3.2 Knowledge Graph Construction (raglite/ingestion/graph_builder.py ~100 lines)

**Purpose:** Build Neo4j knowledge graph from extracted entities with relationships.

**Key Functions:**
```python
async def build_graph(entities: List[Entity]) -> None:
    """Construct knowledge graph in Neo4j.

    Creates nodes for entities and edges for relationships:
        - CORRELATES_WITH: Metric-to-metric relationships
        - BELONGS_TO: Department → Company hierarchies
        - MEASURED_IN: Metric → Time Period
        - PRECEDES: Q2 → Q3 temporal sequences
    """

async def infer_relationships(entities: List[Entity]) -> List[Relationship]:
    """Infer entity relationships using LLM reasoning.

    Example: If "Marketing spend increased 20%" and "Revenue grew 15%"
    appear in same document, infer CORRELATES_WITH relationship.
    """
```

**Graph Schema (Neo4j):**
```cypher
// Nodes
(:Company {name, industry})
(:Metric {name, value, unit, time_period})
(:Department {name, company_id})
(:TimePeriod {quarter, year, fiscal_period})

// Relationships
(Metric)-[:CORRELATES_WITH]->(Metric)
(Department)-[:BELONGS_TO]->(Company)
(Metric)-[:MEASURED_IN]->(TimePeriod)
(TimePeriod)-[:PRECEDES]->(TimePeriod)
```

**NFRs:**
- Graph construction time: <5 min for 100-page PDF
- Relationship accuracy: 80%+ (manual validation)

**Testing:**
- Unit tests: Mock Neo4j client
- Integration tests: Build graph from sample financial docs
- Query tests: Validate Cypher queries return correct relationships

---

### 3.3 Hybrid Search (raglite/retrieval/hybrid_search.py ~100 lines)

**Purpose:** Combine vector similarity (Qdrant) with graph traversal (Neo4j) for relational queries.

**Key Function:**
```python
async def hybrid_search(query: str, top_k: int = 5) -> List[QueryResult]:
    """Hybrid retrieval combining vector + graph search.

    Steps:
        1. Detect if query requires graph (entity extraction from query)
        2. If graph-needed:
           a. Vector search for initial seed chunks (top_k=10)
           b. Extract entities from seed chunks
           c. Graph traversal to find related entities
           d. Re-rank results combining vector score + graph relevance
        3. If vector-only: Use standard vector search (Epic 1)

    Returns:
        List of QueryResult objects (augmented with graph context)
    """
```

**Orchestration Logic:**
```python
def query_requires_graph(query: str) -> bool:
    """Detect if query needs graph-enhanced retrieval.

    Indicators:
        - Keywords: "correlation", "relationship", "compare", "trend"
        - Multi-entity queries: mentions 2+ metrics/departments/time periods
        - Multi-hop reasoning: "after", "because", "led to"
    """
```

**NFRs:**
- NFR13: <15s query response time (p95) for complex hybrid queries
- Accuracy improvement: +10% for relational queries vs vector-only

**Testing:**
- Unit tests: Mock Qdrant + Neo4j clients
- Integration tests: End-to-end hybrid queries with real graph
- Accuracy tests: Validate relational query accuracy (80%+ target)

---

### 3.4 Advanced Table Extraction (raglite/ingestion/pipeline.py updates ~50 lines)

**Purpose:** Enhanced Docling configuration for complex table handling (multi-level headers, merged cells).

**Enhancements:**
```python
# Update extract_pdf() in pipeline.py
converter = DocumentConverter(
    table_structure_config={
        "preserve_headers": True,
        "detect_merged_cells": True,
        "multi_level_headers": True
    }
)

# Store table structure metadata
table_metadata = {
    "headers": table.headers,  # Multi-level header hierarchy
    "row_labels": table.row_labels,
    "column_count": table.column_count,
    "table_title": table.caption,
    "has_merged_cells": table.has_merged_cells
}
```

**NFRs:**
- NFR9: 95%+ table extraction accuracy (complex financial tables)

**Testing:**
- Unit tests: Mock Docling with complex table structures
- Integration tests: Real financial reports with multi-level tables
- Accuracy tests: Manual validation on 20+ complex tables

---

## 4. API Contracts

### 4.1 New MCP Tool: query_with_graph

**Input:**
```json
{
  "query": "How does marketing spend correlate with revenue across Q2-Q4 2024?",
  "top_k": 5,
  "use_graph": true
}
```

**Output:**
```json
{
  "results": [
    {
      "score": 0.89,
      "text": "Marketing spend Q2: $2M, Revenue Q2: $10M...",
      "source_document": "Q2_Report.pdf",
      "page_number": 12,
      "graph_context": {
        "entities": ["Marketing Spend", "Revenue", "Q2 2024"],
        "relationships": ["CORRELATES_WITH (r=0.85)"]
      }
    }
  ],
  "query": "How does marketing spend correlate...",
  "retrieval_time_ms": 1250,
  "graph_enhanced": true
}
```

---

## 5. NFR Validation Criteria

### Accuracy Improvement (Phase 2 Goal)
**Target:** 80% → 90%+ for relational/multi-hop queries

**Validation Method:**
- Expanded test set: 20+ relational queries (Story 2.7)
- Comparison: Vector-only vs Hybrid RAG accuracy
- Measure accuracy gain for entity-based queries

### Performance (NFR13)
**Target:** <15s query response time (p95) for hybrid queries

**Validation Method:**
- Performance tests with Neo4j + Qdrant
- Measure graph traversal overhead
- Optimize Cypher queries if needed

---

## 6. Implementation Timeline

### Week 5: Decision Gate + Neo4j Setup
**Activities:**
- Phase 1 validation (accuracy measurement)
- **IF <80% accuracy** → Analyze failure modes
- **IF multi-hop failures** → GO for Epic 2
- Deploy Neo4j via Docker Compose
- Update repository structure

**Deliverables:**
- Phase 1 validation report
- Neo4j deployment (if GO decision)

---

### Week 6: Entity Extraction + Graph Construction
**Stories:**
- Story 2.3: Entity Extraction (LLM-based)
- Story 2.4: Knowledge Graph Construction (Neo4j)

**Deliverables:**
- `raglite/ingestion/entity_extraction.py`
- `raglite/ingestion/graph_builder.py`
- Entity extraction accuracy: 85%+

---

### Week 7: Hybrid Retrieval + Table Enhancements
**Stories:**
- Story 2.5: Hybrid RAG + Knowledge Graph Retrieval
- Story 2.1: Advanced Table Extraction
- Story 2.6: Context Preservation

**Deliverables:**
- `raglite/retrieval/hybrid_search.py`
- Enhanced table extraction in `pipeline.py`
- Hybrid query accuracy: 80%+

---

### Week 8: Integration Testing + Validation
**Stories:**
- Story 2.2: Multi-Document Query Synthesis
- Story 2.7: Enhanced Test Set

**Deliverables:**
- Expanded test set (20+ relational queries)
- Integration testing (vector + graph)
- Phase 2 validation report

**Success Criteria:**
- 90%+ accuracy on relational queries
- <15s query response time (p95)
- All multi-hop queries answered correctly

---

## 7. Dependencies & Blockers

### External Dependencies
**New Technologies:**
- Neo4j 5.x (Docker container)
- neo4j-python-driver 5.x (Python client)

**Existing Dependencies (Epic 1):**
- Qdrant ✅
- Claude API ✅
- Docling ✅

### Decision Dependency
**CRITICAL:** Epic 2 only proceeds if Phase 1 decision gate triggers (accuracy <80% AND multi-hop failures).

**Decision Criteria:**
- ✅ **≥90% accuracy** → SKIP Epic 2, proceed to Epic 3
- ⚠️ **80-89% accuracy** → DEFER Epic 2, proceed to Epic 3
- 🛑 **<80% accuracy + multi-hop failures** → IMPLEMENT Epic 2

---

## 8. Success Criteria

### Phase 2 Completion Criteria (End of Week 8)

**Must Meet (GO Criteria):**
1. ✅ 90%+ accuracy on relational/multi-hop queries (20+ test queries)
2. ✅ <15s query response time for hybrid queries (p95)
3. ✅ Knowledge graph correctly models entity relationships (manual validation)
4. ✅ Advanced table extraction: 95%+ accuracy on complex tables
5. ✅ Multi-document synthesis: Accurate comparisons across 3+ documents

**Decision Gate:**
- **IF** all criteria met → **PROCEED to Epic 3** (AI Orchestration)
- **IF** accuracy still <85% → **REASSESS** (consider alternate approaches)

---

## 9. Risks & Mitigation

### Risk 1: Graph Construction Complexity (MEDIUM)
**Probability:** Medium (entity extraction + relationship inference non-trivial)
**Impact:** HIGH (could delay Phase 2 by 1-2 weeks)

**Mitigation:**
1. Use LLM-based entity extraction (simpler than NER training)
2. Start with simple relationships (BELONGS_TO, MEASURED_IN)
3. Iterative refinement: Add complex relationships (CORRELATES_WITH) in Week 7

### Risk 2: Performance Overhead (MEDIUM)
**Probability:** Medium (Neo4j queries + Qdrant search = 2x latency)
**Impact:** MEDIUM (could breach <15s NFR13 target)

**Mitigation:**
1. Optimize Cypher queries (indexed lookups)
2. Cache entity extractions for common queries
3. Parallel execution: Vector + Graph searches in parallel

### Risk 3: Accuracy Improvement Insufficient (HIGH)
**Probability:** Medium (graph may not solve all multi-hop failures)
**Impact:** VERY HIGH (Epic 2 fails to justify investment)

**Mitigation:**
1. Week 6 early validation: Test graph on 10 sample queries
2. If accuracy doesn't improve by +5%, HALT and reassess
3. Fallback: Improve prompt engineering for Claude synthesis (Epic 1)

---

## 10. References

### Architecture Documents
- `docs/architecture/8-phased-implementation-strategy-v11-simplified.md` - Phase 2 timeline
- `docs/architecture/5-technology-stack-definitive.md` - Technology stack

### PRD Documents
- `docs/prd/epic-2-advanced-document-understanding.md` - Epic 2 stories

### Research
- Anthropic Contextual Retrieval (98.1% accuracy, +8% improvement)
- GraphRAG (Microsoft Research) - Knowledge Graph + Vector RAG hybrid

---

**Document Version:** 1.0
**Created:** 2025-10-12
**Author:** Sarah (Product Owner)
**Next Update:** After Phase 1 decision gate (Week 5)
