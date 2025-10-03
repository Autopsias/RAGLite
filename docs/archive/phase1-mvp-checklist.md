# Phase 1 MVP: What You're ACTUALLY Building

**Reality Check:** This is NOT enterprise software. This is a 4-week solo dev MVP to validate that RAG works for financial documents.

---

## Week 1: Make Ingestion Work

**Goal:** PDF → Qdrant (that's it)

### Files to Create (5 files max)

```
raglite/
├── main.py                    # 1. MCP server (FastMCP boilerplate)
├── ingestion.py               # 2. PDF → chunks → embeddings → Qdrant
├── config.py                  # 3. Settings (Qdrant host, API keys)
└── tests/
    └── test_ingestion.py      # 4. One test: "Can I ingest a PDF?"
```

### What You're Building

**ingestion.py (< 150 lines):**
```python
def ingest_pdf(file_path: str) -> str:
    """PDF → Qdrant. Return job_id."""
    # 1. Docling: Extract text
    # 2. Split into chunks (simple: 500 words, 50 overlap)
    # 3. Fin-E5: Generate embeddings
    # 4. Qdrant: Store with metadata
    return job_id

# SKIP for Week 1:
# - Contextual Retrieval (just split text)
# - Excel support (PDFs only)
# - Fancy chunking (use simple splitting)
# - Error handling beyond try/except
```

**Success:** You can run `ingest_pdf("Q3_report.pdf")` and see chunks in Qdrant UI.

---

## Week 2: Make Search Work

**Goal:** Query → Qdrant → Results (that's it)

### Files to Add (2 files)

```
raglite/
├── main.py                    # UPDATE: Add search MCP tool
├── retrieval.py               # 5. NEW: Query → Qdrant search
└── tests/
    └── test_retrieval.py      # 6. NEW: One test: "Can I search?"
```

### What You're Building

**retrieval.py (< 100 lines):**
```python
def search(query: str, top_k: int = 10) -> List[dict]:
    """Query → Qdrant results. Return chunks with sources."""
    # 1. Fin-E5: Embed query
    # 2. Qdrant: Vector search
    # 3. Format: [{content, source, page}]
    return results

# SKIP for Week 2:
# - LLM synthesis (return raw chunks)
# - Reranking (Qdrant ranking is fine)
# - Fancy citation formatting
```

**Success:** You can ask "What was Q3 revenue?" and get relevant chunks back.

---

## Week 3: Make It Answer Questions

**Goal:** Query → LLM synthesizes answer from chunks

### Files to Add (1 file)

```
raglite/
├── main.py                    # UPDATE: Synthesis in search tool
├── synthesis.py               # 7. NEW: Chunks → LLM → Answer
└── tests/
    └── test_synthesis.py      # 8. NEW: "Does LLM cite sources?"
```

### What You're Building

**synthesis.py (< 80 lines):**
```python
def synthesize_answer(query: str, chunks: List[dict]) -> str:
    """Chunks → LLM prompt → Answer with citations."""
    # 1. Build prompt: "Answer based on these chunks: {chunks}"
    # 2. Claude API: Get answer
    # 3. Append sources: "Sources: Q3_Report.pdf, page 3"
    return answer_with_citations

# SKIP for Week 3:
# - Multi-agent orchestration (direct LLM call)
# - Complex prompting (simple template)
# - Streaming responses
```

**Success:** You ask "What drove Q3 revenue?" and get a coherent answer with sources.

---

## Week 4: Validate Accuracy

**Goal:** Does this actually work? (measure accuracy)

### Files to Add (1 file)

```
raglite/
└── tests/
    └── ground_truth.py        # 9. NEW: 20 test queries with answers
```

### What You're Building

**ground_truth.py:**
```python
TEST_QUERIES = [
    {
        "query": "What was Q3 2024 revenue?",
        "expected_answer": "$6.2M",  # From your actual test doc
        "source": "Q3_Report.pdf"
    },
    # ... 19 more queries
]

def run_accuracy_test():
    """Run all queries, manually check if answers match."""
    for test in TEST_QUERIES:
        result = query_financial_documents(test["query"])
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected_answer']}")
        print(f"Got: {result}")
        print(f"PASS? (y/n): ", end="")
        user_validates = input()

    accuracy = passed / total
    return accuracy

# SKIP for Week 4:
# - Automated accuracy measurement (manual is fine)
# - 50+ queries (20 is enough for MVP)
# - Statistical analysis
```

**Success:** You run accuracy test, manually validate answers, get ≥80% (not 90% - this is MVP).

---

## What You're NOT Building (Phase 1)

❌ **Microservices** - 1 Python file with all logic
❌ **AWS Strands** - Direct function calls
❌ **Forecasting** - Phase 3
❌ **Insights** - Phase 3
❌ **GraphRAG** - Phase 2 (conditional)
❌ **Contextual Retrieval** - Use simple chunking first, optimize later
❌ **Excel support** - PDFs only
❌ **Production deployment** - Docker Compose locally
❌ **CloudWatch monitoring** - Print statements are fine
❌ **Structured logging** - `logger.info()` is fine
❌ **Circuit breakers** - Retry 3 times is sufficient
❌ **Automated tests for everything** - 3-4 key tests only
❌ **Type hints everywhere** - Add them, but don't obsess
❌ **Perfect docstrings** - Comments are fine
❌ **Error handling for edge cases** - Handle happy path + file-not-found

---

## The ONLY Metrics That Matter (Week 4)

1. **Can you ingest 5 financial PDFs?** (Yes/No)
2. **Can you ask 20 questions and get useful answers?** (Accuracy %)
3. **Do answers cite sources correctly?** (Yes/No)
4. **Is query response <10 seconds?** (Yes/No - not <5s, MVP tolerance)

If all 4 are "Yes" or ">70%" → **MVP SUCCESS** → Proceed to Phase 2/3

If any are "No" → **Fix that ONE thing** → Don't add features

---

## Technologies Used (Minimal Set)

| Need | Technology | Why |
|------|------------|-----|
| **PDF extraction** | Docling | Research validated (97.9% accuracy) |
| **Embeddings** | Fin-E5 | Research validated (71.05% financial accuracy) |
| **Vector DB** | Qdrant (Docker) | Research validated (fast, accurate) |
| **LLM** | Claude 3.7 Sonnet | Best reasoning for synthesis |
| **MCP Server** | FastMCP | Official SDK, simple setup |
| **Testing** | pytest | Standard Python testing |
| **Formatting** | black | Auto-format, no config needed |

**Total dependencies:** ~8 libraries (not 30)

---

## Deployment (Week 4)

**Local Development:**
```bash
# docker-compose.yml (3 services max)
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]

  raglite:
    build: .
    ports: ["5000:5000"]
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
```

**That's it.** No Kubernetes, no Terraform, no AWS until Phase 4.

---

## Time Budget (Brutal Honesty)

| Week | Task | Time |
|------|------|------|
| Week 1 | Ingestion pipeline | 15-20 hours |
| Week 2 | Search + MCP tools | 10-15 hours |
| Week 3 | LLM synthesis | 8-10 hours |
| Week 4 | Accuracy testing | 10-12 hours |
| **Total** | **Full Phase 1** | **45-55 hours** |

**Reality:** Probably 60-80 hours with debugging. Still doable in 4 weeks part-time.

**If you're spending >80 hours:** You're over-engineering. Stop adding features.

---

## The Only Question That Matters

**Week 4 Decision:**

> "Can I show this to a finance person, have them ask 10 questions about their actual financial reports, and have them say 'This is useful'?"

If **YES** → Phase 1 SUCCESS → Continue to Phase 2/3
If **NO** → What ONE thing would make it useful? → Fix that → Re-test

---

## Anti-Over-Engineering Mantras

1. **"Will deleting this break the MVP?"** → If no, delete it
2. **"Can I build this in 1 day?"** → If no, scope it down
3. **"Does this solve a problem I actually have right now?"** → If no, defer it
4. **"Would a user notice if this was missing?"** → If no, skip it

---

## Week 1 Starter Code (Copy This)

```python
# raglite/main.py - COMPLETE MVP SERVER (~100 lines)

from mcp.server.fastmcp import FastMCP
from raglite.ingestion import ingest_pdf
from raglite.retrieval import search
from raglite.synthesis import synthesize_answer

mcp = FastMCP("RAGLite")

@mcp.tool()
def ingest_document(file_path: str) -> dict:
    """Ingest PDF into knowledge base."""
    job_id = ingest_pdf(file_path)
    return {"job_id": job_id, "status": "processing"}

@mcp.tool()
def query_documents(query: str, top_k: int = 10) -> dict:
    """Search financial documents and get synthesized answer."""
    chunks = search(query, top_k)
    answer = synthesize_answer(query, chunks)
    return {"answer": answer, "chunks": chunks}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.app, host="0.0.0.0", port=5000)
```

**That's the ENTIRE server.** Everything else is just implementation details.

---

**Bottom Line:** 9 Python files, 600-800 lines of code total, 4 weeks. That's the MVP. No more, no less.

If you're writing more than this, you're building Phase 2/3/4 too early. Stop and refocus on the MVP.

---

*"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away." - Antoine de Saint-Exupéry*

*"Make it work, make it right, make it fast - in that order." - Kent Beck*
