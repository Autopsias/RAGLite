# 3. Repository Structure (Monolithic)

```
raglite/
├── pyproject.toml              # Poetry dependencies
├── poetry.lock
├── docker-compose.yml          # Qdrant + app containers
├── Dockerfile
├── .env.example
├── .gitignore
├── README.md
│
├── raglite/                    # Main Python package (600-800 lines total)
│   ├── __init__.py
│   ├── main.py                # MCP server entrypoint (~200 lines)
│   │
│   ├── ingestion/             # Ingestion module (~150 lines)
│   │   ├── __init__.py
│   │   ├── pipeline.py        # Docling + chunking + embedding
│   │   └── contextual.py      # Contextual Retrieval chunking
│   │
│   ├── retrieval/             # Retrieval module (~150 lines)
│   │   ├── __init__.py
│   │   ├── search.py          # Qdrant vector search
│   │   ├── synthesis.py       # LLM answer synthesis
│   │   └── attribution.py     # Source citation
│   │
│   ├── forecasting/           # Forecasting module (Phase 3, ~100 lines)
│   │   ├── __init__.py
│   │   └── hybrid.py          # Prophet + LLM adjustment
│   │
│   ├── insights/              # Insights module (Phase 3, ~100 lines)
│   │   ├── __init__.py
│   │   ├── anomalies.py       # Statistical anomaly detection
│   │   └── trends.py          # Trend analysis
│   │
│   ├── shared/                # Shared utilities (~100 lines)
│   │   ├── __init__.py
│   │   ├── config.py          # Settings (Pydantic BaseSettings)
│   │   ├── logging.py         # Structured logging setup
│   │   ├── models.py          # Pydantic data models
│   │   └── clients.py         # Qdrant, Claude API clients
│   │
│   └── tests/                 # Tests co-located (~200 lines)
│       ├── test_ingestion.py
│       ├── test_retrieval.py
│       ├── test_synthesis.py
│       ├── ground_truth.py    # Accuracy validation (50+ queries)
│       └── fixtures/
│           └── sample_financial_report.pdf
│
├── scripts/
│   ├── setup-dev.sh           # One-command local setup
│   ├── init-qdrant.py         # Initialize Qdrant collection
│   └── run-accuracy-tests.py  # Ground truth validation
│
└── docs/
    ├── architecture.md         # This document
    ├── prd.md                  # Product requirements
    └── front-end-spec.md       # MCP response format spec
```

**Total Files:** ~15 Python files
**Total Lines:** 600-800 lines (vs 3000+ for microservices)
**Complexity:** LOW (direct function calls, single deployment)

---
