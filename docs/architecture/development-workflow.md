# Development Workflow

**Version:** 2.0 (Updated for Monolithic + UV)
**Last Updated:** October 4, 2025

---

## ⚠️ IMPORTANT: Monolithic Architecture (Phase 1-3)

This document describes the **Phase 1-3 monolithic architecture**. The microservices architecture shown below is **Phase 4 future state**.

For current development, see: `docs/architecture/source-tree.md`

---

## Repository Structure (Phase 1-3 Monolithic)

```
raglite/
├── README.md
├── docker-compose.yml              # Qdrant local development
├── .env.example                    # Environment template
├── .gitignore
├── pyproject.toml                  # Python dependencies (UV - PEP 621)
├── uv.lock                         # Locked dependency versions
│
├── raglite/                        # Main package (~600-800 lines)
│   ├── main.py                    # MCP server entrypoint (~200 lines)
│   ├── ingestion/                 # Document processing (~150 lines)
│   │   ├── pipeline.py
│   │   └── contextual.py
│   ├── retrieval/                 # Search & synthesis (~150 lines)
│   │   ├── search.py
│   │   ├── synthesis.py
│   │   └── attribution.py
│   ├── forecasting/               # Phase 3 (~100 lines)
│   │   └── hybrid.py
│   ├── insights/                  # Phase 3 (~100 lines)
│   │   ├── anomalies.py
│   │   └── trends.py
│   ├── shared/                    # Utilities (~100 lines)
│   │   ├── config.py              # Pydantic Settings
│   │   ├── logging.py             # Structured logging
│   │   ├── models.py              # Data models
│   │   └── clients.py             # Qdrant, Claude clients
│   └── tests/                     # Co-located tests
│       ├── test_ingestion.py
│       ├── test_retrieval.py
│       ├── ground_truth.py        # 50+ Q&A pairs
│       └── fixtures/
│
├── scripts/
│   ├── setup-dev.sh               # One-command local setup
│   ├── init-qdrant.py             # Initialize Qdrant collection
│   └── run-accuracy-tests.py      # Ground truth validation
│
└── docs/
    ├── architecture/              # Sharded architecture docs (30 files)
    ├── prd/                       # Sharded PRD docs (15 files)
    ├── front-end-spec/            # MCP response formats
    ├── stories/                   # Active user stories
    └── qa/                        # Quality gates
```

## Local Development Setup (Phase 1-3)

```bash
# Prerequisites: Python 3.11+, Docker Desktop, UV

# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/RAGLite.git
cd raglite

# 2. Install UV (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync --frozen

# 4. Start Qdrant via Docker Compose
docker-compose up -d

# 5. Initialize Qdrant collection
uv run python scripts/init-qdrant.py

# 6. Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 7. Run tests
uv run pytest

# 8. Start MCP server (for local testing)
uv run python -m raglite.main
```

**Alternative: One-command setup**

```bash
