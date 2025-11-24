# MCP Configuration Guide

This guide explains how to configure Claude Desktop to connect to the RAGLite MCP server.

---

## Configuration Steps

### 1. Locate Claude Desktop Config File

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### 2. Add RAGLite MCP Server Configuration

Replace `/path/to/RAGLite` with your actual installation path:

```json
{
  "mcpServers": {
    "raglite": {
      "command": "/path/to/RAGLite/.venv/bin/python",
      "args": ["-m", "raglite.main"],
      "cwd": "/path/to/RAGLite",
      "env": {
        "PYTHONPATH": "/path/to/RAGLite",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "QDRANT_COLLECTION_NAME": "financial_docs",
        "EMBEDDING_MODEL": "intfloat/e5-large-v2",
        "EMBEDDING_DIMENSION": "1024",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "raglite",
        "POSTGRES_USER": "raglite",
        "POSTGRES_PASSWORD": "raglite"
      }
    }
  }
}
```

### 3. Initialize Databases

```bash
cd /path/to/RAGLite
uv run python scripts/init-qdrant.py
uv run python scripts/init-postgresql.py
```

### 4. Restart Claude Desktop

Completely quit and reopen Claude Desktop.

### 5. Verify Connection

- Click 🔌 icon in Claude Desktop
- Should see "raglite" server with 2 tools available

---

## Document Ingestion Performance & Timeouts

### Overview

RAGLite provides two ingestion methods to handle documents of all sizes:

1. **Sync Ingestion** (`ingest_financial_document`) - Small/medium documents (<50 pages)
2. **Async Ingestion** (`ingest_financial_document_async`) - Large documents (>50 pages)

### Expected Ingestion Times

Based on performance testing (Story 4.0.3), typical ingestion times:

| Document Size | Estimated Time | Recommended Method | Timeout Risk |
|---------------|----------------|-------------------|--------------|
| 4 pages | ~30s | Sync | ✅ Safe |
| 10 pages | ~73s | Sync | ⚠️ Borderline (60s timeout) |
| 30 pages | ~219s (3.6 min) | **Async** | ❌ Will timeout |
| 50 pages | ~365s (6 min) | **Async** | ❌ Will timeout |
| 100 pages | ~729s (12 min) | **Async** | ❌ Will timeout |
| 150 pages | ~1094s (18 min) | **Async** | ❌ Will timeout |
| 200 pages | ~1458s (24 min) | **Async** | ❌ Will timeout |

**Performance Factors:**
- Speed: ~7.3 seconds/page (with pypdfium backend + parallelism)
- Bottlenecks: 62% Docling processing, 17% embeddings, 8% storage
- Already optimized: pypdfium backend (Story 2.1), page-level parallelism (Story 2.2)

### MCP Timeout Limits

**Default MCP Timeout:** 60-120 seconds (varies by client)

⚠️ **Critical:** Any document ≥30 pages will exceed the MCP timeout window, even with all optimizations enabled.

### Using Async Ingestion

For documents >50 pages, use the async ingestion workflow:

**Step 1: Start Async Ingestion**
```python
response = await ingest_financial_document_async("/path/to/large-report.pdf")
print(response.job_id)  # Save this for polling
# Output: "a3f8b2c1-4d5e-6f7g-8h9i-0j1k2l3m4n5o"
```

**Step 2: Poll Job Status**
```python
import time

while True:
    status = await get_ingestion_status(response.job_id)
    print(f"Status: {status.status}, Progress: {status.progress}%")

    if status.status in ["completed", "failed"]:
        break

    time.sleep(60)  # Check every 1 minute
```

**Step 3: Query After Completion**
```python
if status.status == "completed":
    # Document is now ready for querying
    query_resp = await query_financial_documents(
        QueryRequest(query="What was Q3 revenue?")
    )
```

### Timeout Configuration

**Note:** MCP timeout limits are controlled by the MCP client (Claude Desktop), not RAGLite.

Current behavior:
- Small documents (<50 pages): Use sync ingestion
- Large documents (>50 pages): Use async ingestion (required)

Future (Epic 5 - Production):
- Persistent job storage (Redis)
- Progress tracking
- Job expiration policies

### Choosing Sync vs Async

**Use Sync Ingestion When:**
- Document <10 pages (safe, <60s)
- Document 10-30 pages (borderline, may timeout)
- Quick testing with small samples

**Use Async Ingestion When:**
- Document >50 pages (required, will timeout otherwise)
- Production quarterly/annual reports (150-200 pages)
- Any document that previously timed out

**Auto-Detection (Coming Soon):**
- Automatic page count detection before ingestion
- Recommendation to use async for large files

---

## Troubleshooting

### Issue: Ingestion Times Out

**Symptoms:**
- MCP client shows timeout error after 60-120s
- Ingestion doesn't complete
- Large PDF reports fail to ingest

**Solution:**

1. **Check document size:**
   ```bash
   pdfinfo /path/to/document.pdf | grep Pages
   ```

2. **If >30 pages, use async ingestion:**
   - Use `ingest_financial_document_async` instead of `ingest_financial_document`
   - Poll with `get_ingestion_status` until complete

3. **For small documents timing out:**
   - Check database connectivity (Qdrant port 6333, PostgreSQL port 5432)
   - Verify pypdfium backend enabled (check logs for "pypdfium" message)
   - Check system resources (CPU, memory)

### Issue: Async Job Status "Pending" Forever

**Symptoms:**
- `get_ingestion_status` always shows `status="pending"`
- Job never progresses to "in_progress"

**Solution:**

1. **Check background task started:**
   - Server logs should show "Background ingestion job started"
   - If missing, server may have crashed during job creation

2. **Restart MCP server:**
   - Quit Claude Desktop completely
   - Reopen Claude Desktop
   - Job state is lost (in-memory only in MVP)

3. **Re-ingest document:**
   - Start new async ingestion job
   - Save new job ID

### Issue: Async Job Fails with Error

**Symptoms:**
- `get_ingestion_status` shows `status="failed"`
- Error message in `status.error` field

**Common Errors:**

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Document not found" | Invalid file path | Check path is absolute, file exists |
| "Failed to ingest: ..." | Parsing/processing error | Check PDF is valid, not corrupted |
| "Embedding generation failure" | Fin-E5 model issue | Check model loaded, GPU/CPU available |
| "Qdrant connection error" | Database unavailable | Check Qdrant running on port 6333 |
| "PostgreSQL connection error" | Database unavailable | Check PostgreSQL running on port 5432 |

### Issue: Job ID Not Found

**Symptoms:**
- `get_ingestion_status` returns "Job not found" error

**Causes:**
1. **Invalid job ID:** Check ID was copied correctly (UUID format)
2. **Server restarted:** Jobs stored in-memory only (MVP limitation)
3. **Job expired:** (Not implemented in MVP, but planned for Epic 5)

**Solution:**
- Re-ingest document and save new job ID
- For production, Epic 5 will add persistent storage

---

## Performance Monitoring

### Check Current Optimizations

Verify optimizations are enabled in server logs:

```bash
# Check pypdfium backend
grep "pypdfium" /path/to/logs

# Check page-level parallelism
grep "num_threads" /path/to/logs
```

Expected:
- Backend: "pypdfium" (Story 2.1 - 1.7-2.5x speedup)
- Threads: "num_threads=8" (Story 2.2 - concurrent page processing)

### Ingestion Performance Baseline

Run performance measurement:

```bash
cd /path/to/RAGLite
uv run python scripts/measure-ingestion-performance.py
```

Expected results:
- 4-page PDF: ~30s
- Average speed: ~7.3s/page
- Timeout risk analysis for 10-200 page documents

---

**Last Updated:** 2025-11-23 (Story 4.0.3)
