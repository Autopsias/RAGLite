# Deployment Architecture

## Overview

RAGLite supports **two deployment modes**:
1. **Local Development** (Docker Compose)
2. **Production Cloud** (AWS ECS/EKS)

## Local Development Deployment

**Target:** Developer workstations for local testing and development

**Architecture:**

```
┌──────────────────────────────────────────────────────┐
│  Docker Compose Network: raglite-network            │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  MCP Gateway Container                       │   │
│  │  Port: 5000 → localhost:5000                 │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐            │
│  │ M1 │  │ M2 │  │ M3 │  │ M4 │  │ M5 │            │
│  │5001│  │5002│  │5003│  │5004│  │5005│            │
│  └────┘  └────┘  └────┘  └────┘  └────┘            │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  Qdrant Container                            │   │
│  │  Port: 6333 → localhost:6333                 │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  Neo4j Container (Phase 2)                   │   │
│  │  Ports: 7474, 7687 → localhost               │   │
│  └──────────────────────────────────────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  AWS Strands Orchestrator (Host Process)     │   │
│  │  Calls MCP Gateway at localhost:5000         │   │
│  └──────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
```

**Docker Compose Configuration:**

```yaml