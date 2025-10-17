# Data Layer

## Overview

The data layer consists of **3 primary storage systems**, each optimized for specific data types:

```
┌─────────────────────────────────────────────────────────┐
│  Data Layer                                             │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Qdrant (Vector Database)                          │ │
│  │  - Embeddings (1024-dim Fin-E5 vectors)            │ │
│  │  - Chunk metadata (doc_id, page, section)          │ │
│  │  - HNSW indexing for sub-5s retrieval              │ │
│  │  - Collections: financial_documents                 │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Neo4j (Graph Database - Phase 2)                  │ │
│  │  - Knowledge graph (entities, relationships)        │ │
│  │  - Nodes: Company, Department, Metric, KPI, Period │ │
│  │  - Edges: CORRELATES, BELONGS_TO, MEASURED_BY      │ │
│  │  - Community summaries for GraphRAG                │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  S3 / Local Storage (Document Store)               │ │
│  │  - Original PDFs and Excel files                    │ │
│  │  - Extracted chunks (text, tables)                  │ │
│  │  - Ingestion artifacts (metadata, logs)            │ │
│  │  - Versioning for document updates                 │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## Qdrant (Vector Database)

**Purpose:** Store and search document embeddings for semantic retrieval

**Schema:**

```python
