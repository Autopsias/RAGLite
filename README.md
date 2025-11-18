# RAGLite - AI-Powered Financial Document Analysis

[![Tests](https://github.com/YOUR_USERNAME/RAGLite/workflows/Tests/badge.svg)](https://github.com/YOUR_USERNAME/RAGLite/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/dependency%20manager-uv-blue)](https://docs.astral.sh/uv/)

**RAGLite** is a monolithic MVP for an AI-powered financial document analysis system using Retrieval-Augmented Generation (RAG). Query financial PDFs and Excel files using natural language via the Model Context Protocol (MCP).

**Current Status:** Phase 1 - Monolithic MVP Development
**Target:** 600-800 lines of Python code across 15 files
**Accuracy Goal:** 90%+ retrieval accuracy with 95%+ source attribution

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Docker & Docker Compose** ([Download](https://www.docker.com/products/docker-desktop))
- **uv** (installed automatically via setup script)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/RAGLite.git
cd RAGLite

# 2. Run setup script (installs uv, dependencies, starts Qdrant)
chmod +x scripts/setup-dev.sh
./scripts/setup-dev.sh

# 3. Configure environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Start the MCP server
uv run python -m raglite.main
```

**Alternative Manual Setup:**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Start Qdrant vector database
docker-compose up -d

# Initialize Qdrant collection
uv run python scripts/init-qdrant.py

# Run the server
uv run python -m raglite.main
```

---

## 📖 Features

### Phase 1 (Current - Weeks 1-5)

- ✅ **PDF Ingestion:** Extract text and tables from financial PDFs using Docling (97.9% accuracy)
- ✅ **Excel Ingestion:** Parse financial spreadsheets with openpyxl + pandas
- ✅ **Semantic Search:** Fin-E5 financial embeddings + Qdrant vector database
- ✅ **Source Attribution:** 95%+ accurate citations (document, page, section)
- ✅ **LLM Synthesis:** Claude 3.7 Sonnet for natural language answers
- ✅ **MCP Server:** FastMCP-based server for Claude Desktop integration

**Known Limitation:** Large file ingestion (>10 pages) may timeout via MCP. Use CLI ingestion for large files (see [Large File Ingestion](#large-file-ingestion) below). Async job queue support planned for Epic 4.

### Phase 2 (Conditional - Weeks 5-8)

- 🔄 **GraphRAG:** Neo4j knowledge graph for multi-hop queries (only if Phase 1 accuracy <80%)

### Phase 3 (Weeks 9-12)

- 🔜 **Forecasting:** Time-series predictions with Prophet + LLM
- 🔜 **Insights:** Anomaly detection and trend analysis

### Phase 4 (Weeks 13-16)

- 🔜 **Production Deployment:** AWS ECS/Fargate, CloudWatch monitoring
- 🔜 **Performance Optimization:** Caching, scaling, infrastructure as code (Terraform)

---

## 🏗️ Architecture

**Approach:** Monolithic Python application with modular structure (evolves to microservices in Phase 4 if needed)

```
┌──────────────────────────────────────────────┐
│  MCP Clients (Claude Desktop, Claude Code)  │
└────────────────┬─────────────────────────────┘
                 │ Model Context Protocol
┌────────────────▼─────────────────────────────┐
│  RAGLite Monolithic Server (FastMCP)        │
│  ├─ ingestion/  (Docling, chunking, Fin-E5) │
│  ├─ retrieval/  (Qdrant search, synthesis)  │
│  ├─ forecasting/ [Phase 3]                  │
│  ├─ insights/    [Phase 3]                  │
│  └─ shared/      (config, logging, clients) │
└────────────────┬─────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────┐
│  Data Layer                                  │
│  ├─ Qdrant (Vector DB) - Docker container   │
│  ├─ S3/Local Storage (Documents)             │
│  └─ Neo4j [Phase 2 - conditional]           │
└──────────────────────────────────────────────┘
```

**Repository Structure:**

```
raglite/
├── raglite/           # Main Python package (~600-800 lines)
│   ├── main.py        # MCP server entrypoint (~200 lines)
│   ├── ingestion/     # Document processing (~150 lines)
│   ├── retrieval/     # Search & synthesis (~150 lines)
│   ├── shared/        # Utilities (~100 lines)
│   └── tests/         # Tests (~200 lines)
├── scripts/           # Utility scripts
├── docs/              # Architecture & PRD (sharded)
└── pyproject.toml     # uv dependencies (+ uv.lock)
```

**See full details:** [docs/architecture/source-tree.md](docs/architecture/source-tree.md)

---

## 📚 Documentation

### For Developers

- **[Architecture Guide](docs/architecture/)** - System design, technology stack, reference implementation
  - [Coding Standards](docs/architecture/coding-standards.md) ⭐ **MUST READ**
  - [Technology Stack](docs/architecture/tech-stack.md) - Approved libraries only
  - [Repository Structure](docs/architecture/source-tree.md) - File organization
- **[PRD](docs/prd/)** - Product requirements, epics, user stories
- **[CLAUDE.md](CLAUDE.md)** - AI-assisted development guidelines (for Claude Code)

### For Product/Planning

- **[Epic 1: Foundation & Accurate Retrieval](docs/prd/epic-1-foundation-accurate-retrieval.md)** - Current phase
- **[Week 0 Spike Report](docs/week-0-spike-report.md)** - Technology validation results
- **[QA Gates](docs/qa/gates/)** - Quality assurance checkpoints

---

## 💻 Usage

### MCP Integration (Claude Desktop)

**Prerequisites:** Configure Claude Desktop with RAGLite MCP server (see [MCP Setup Guide](docs/setup/mcp-configuration.md))

**Small File Ingestion (<10 pages):**

In Claude Desktop, use natural language:
```
Ingest this document: /path/to/small-document.pdf
```

**Querying Documents:**

```
Query the financial documents: What was the EBITDA from Portugal?
```

### Large File Ingestion

**⚠️ Known Limitation:** Files >10 pages may timeout via MCP (~30-60 second timeout)

**Workaround:** Use CLI ingestion for large files (30+ minutes for 100+ page PDFs):

```bash
cd /path/to/RAGLite

# Method 1: Direct Python call
uv run python -c "
import asyncio
from raglite.ingestion.pipeline import ingest_document

async def ingest():
    print('Starting ingestion...')
    result = await ingest_document('/path/to/large-document.pdf')
    print(f'✅ Ingested {result.page_count} pages, {result.chunk_count} chunks')

asyncio.run(ingest())
"

# Method 2: Using script (if available)
uv run python scripts/ingest_large_file.py /path/to/large-document.pdf
```

**Expected Performance:**
- Processing time: ~20-30 seconds per page
- 50-page PDF: ~20-25 minutes
- 100-page PDF: ~40-50 minutes

**After Ingestion Completes:**

Query via Claude Desktop MCP as normal:
```
Use query_financial_documents to search: "What was the EBITDA from Portugal?"
```

**Future Enhancement:** Async job queue with progress tracking planned for Epic 4 (Production Readiness). See [docs/future-enhancements.md](docs/future-enhancements.md) for research roadmap.

---

## 🧪 Development

### Running Tests

**Unit & Integration Tests:**

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=raglite --cov-report=html

# Run specific test file
uv run pytest raglite/tests/test_ingestion.py
```

**Accuracy Validation (Story 1.12B):**

```bash
# Run full accuracy test suite (50+ queries)
uv run python scripts/run-accuracy-tests.py

# Run subset for quick checks
uv run python scripts/run-accuracy-tests.py --subset 15

# Run specific category
uv run python scripts/run-accuracy-tests.py --category cost_analysis

# Save results to file
uv run python scripts/run-accuracy-tests.py --output results.json --verbose

# Daily accuracy check (10-15 queries)
uv run python scripts/daily-accuracy-check.py

# Show historical trend analysis
uv run python scripts/daily-accuracy-check.py --show-trend

# Generate Week 5 final validation report
uv run python scripts/generate-final-validation-report.py
```

**Agentic Workflow Test Suite (Story 3.8 - Epic 3):**

```bash
# Run full agentic workflow test suite (22 analytical queries)
uv run pytest tests/integration/test_agentic_workflow_suite.py -m "slow" -v

# Run with JSON reporting for failure analysis
uv run pytest tests/integration/test_agentic_workflow_suite.py \
    -m "slow" \
    --json-report \
    --json-report-file=test-reports/agentic_workflow_results.json

# Generate failure analysis report with actionable insights
python scripts/generate_failure_report.py \
    test-reports/agentic_workflow_results.json \
    test-reports/agentic_workflow_failures.json

# Run specific edge case tests
uv run pytest tests/integration/test_agentic_workflow_suite.py::test_edge_case_missing_data -v
uv run pytest tests/integration/test_agentic_workflow_suite.py::test_edge_case_ambiguous_query -v
```

**Test Suite Metrics:**
- **Total Queries:** 22 (17 analytical + 5 edge cases)
- **Success Rate Target:** 80%+ (per FR16 interpretation)
- **Performance Target:** p50 <12s, p95 <20s (per NFR5)
- **Test Set:** `tests/fixtures/agentic_workflow_test_set.json`

**Workflow Patterns Tested:**
1. **YoY Growth** (3 queries) - Year-over-year percentage calculations
2. **Variance Analysis** (3 queries) - Actual vs budget/forecast comparisons
3. **Trend Analysis** (3 queries) - Multi-period trend detection
4. **Generic Analytical** (8 queries) - Comparative analysis, percentages

**Edge Cases Tested:**
1. **Missing Data** - Graceful handling of unavailable data
2. **Ambiguous Queries** - Best-effort responses for vague queries
3. **Out-of-Domain** - Appropriate rejection of non-financial queries
4. **Complex Multi-Document** - 4+ document reasoning workflows
5. **Conflicting Information** - Multi-source reconciliation

**Interpreting Results:**

- **Retrieval Accuracy:** % of queries returning correct information (target: ≥90%)
- **Attribution Accuracy:** % of citations with correct page numbers (target: ≥95%)
- **Performance:** p50 <5s, p95 <15s (target per NFR13)
- **Exit Codes:** 0 = pass, 1 = fail or accuracy below targets

### Code Quality

```bash
# Format code (black)
uv run black raglite/

# Lint code (ruff)
uv run ruff check raglite/

# Type check (mypy - Phase 4)
uv run mypy raglite/

# Pre-commit hooks (auto-format on commit)
uv run pre-commit install
```

### Daily Development Workflow

1. **Sync dependencies:** `uv sync`
2. **Make changes** to code
3. **Run tests:** `uv run pytest`
4. **Format code:** `uv run black raglite/`
5. **Commit:** Git pre-commit hooks run automatically
6. **Push:** CI/CD pipeline validates changes

---

## 🔧 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **PDF Extraction** | Docling | Latest |
| **Embeddings** | Fin-E5 (finance-adapted) | Latest |
| **Vector DB** | Qdrant | 1.11+ |
| **MCP Server** | FastMCP | 1.x |
| **LLM** | Claude 3.7 Sonnet | API |
| **Language** | Python | 3.11+ |
| **Package Manager** | uv | Latest |
| **Testing** | pytest + pytest-asyncio | Latest |
| **Container** | Docker + Docker Compose | Latest |

**Full Stack:** [docs/architecture/tech-stack.md](docs/architecture/tech-stack.md)

---

## 📊 Current Status

### Week 0 Integration Spike ✅ DONE

- **Status:** CONDITIONAL GO with fixes
- **Accuracy:** 66.7% (likely 70-80% with manual validation)
- **Performance:** All NFRs met (<5min ingestion, <1s query)
- **Blocker:** Page number extraction (fix in Story 1.2)

### Phase 1 (Weeks 1-5) - In Progress

**Target:** 90%+ retrieval accuracy, 95%+ source attribution

**Week 1:** Ingestion pipeline
**Week 2:** Retrieval & search
**Week 3:** LLM synthesis
**Week 4:** Integration testing
**Week 5:** Validation & decision gate

---

## 🤝 Contributing

### Development Guidelines

1. **Read coding standards:** [docs/architecture/coding-standards.md](docs/architecture/coding-standards.md)
2. **Follow tech stack:** Only use approved libraries in [tech-stack.md](docs/architecture/tech-stack.md)
3. **Write tests:** 50%+ coverage for critical paths
4. **Type hints required:** All functions must have type annotations
5. **Structured logging:** Use `logger` with `extra={}` context
6. **No over-engineering:** Keep it simple (600-800 lines target)

### Pull Request Process

1. Create feature branch: `git checkout -b story-1.2-pdf-ingestion`
2. Make changes following coding standards
3. Run tests and linting: `pytest && black raglite/ && ruff check raglite/`
4. Commit with descriptive message
5. Push and create PR (CI/CD runs automatically)
6. Request review

---

## 🎯 Success Criteria

### Phase 1 Gate (Week 5)

- ✅ Can ingest 5 financial PDFs successfully (≥4/5 succeed)
- ✅ 90%+ retrieval accuracy on 50+ query test set (NFR6)
- ✅ 95%+ source attribution accuracy (NFR7)
- ✅ Query response time <10 seconds (≥8/10 queries)
- ✅ All answers include source citations (50/50)

**IF met:** Proceed to Phase 3 (Forecasting/Insights)
**IF <80%:** Consider Phase 2 (GraphRAG)

---

## 🐛 Troubleshooting

### Common Issues

**1. uv not found**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

**2. Qdrant connection failed**

```bash
docker-compose ps  # Check Qdrant running
docker-compose up -d  # Start if stopped
curl http://localhost:6333/collections  # Test endpoint
```

**3. ANTHROPIC_API_KEY not set**

```bash
cp .env.example .env
# Edit .env and add your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

**4. Tests failing**

```bash
# Ensure Qdrant running
docker-compose up -d

# Reinstall dependencies
uv sync

# Run tests with verbose output
uv run pytest -v
```

---

## 📄 License

[Add your license here - e.g., MIT, Apache 2.0]

---

## 🙏 Acknowledgments

- **Docling** - DS4SD for PDF extraction library
- **Fin-E5** - Finance-adapted embeddings
- **Qdrant** - Vector database
- **FastMCP** - MCP protocol implementation
- **Anthropic** - Claude 3.7 Sonnet LLM

---

## 📞 Contact

- **Project Owner:** [Your Name]
- **Email:** [your.email@example.com]
- **Issues:** [GitHub Issues](https://github.com/YOUR_USERNAME/RAGLite/issues)

---

**Built with ❤️ using AI-assisted development (Claude Code)**
