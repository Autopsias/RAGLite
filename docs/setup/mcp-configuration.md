# RAGLite MCP Server - Setup Guide

**Purpose:** Connect Claude Desktop to RAGLite for natural language financial queries

**Audience:** Users, stakeholders, QA testers

---

## Prerequisites

Before starting, verify you have:

- ✅ **Claude Desktop installed** ([Download](https://claude.ai/download))
- ✅ **RAGLite project cloned** to local machine
- ✅ **Qdrant running:** `docker ps` shows qdrant/qdrant container
- ✅ **PostgreSQL running:** `docker ps` shows postgres container (port 5432)
- ✅ **Environment variables configured:** `.env` file exists with `ANTHROPIC_API_KEY`
- ✅ **Dependencies installed:** `uv sync` completed successfully

---

## Step 1: Locate Claude Desktop Config File

**macOS/Linux:**
```bash
~/.claude/mcp.json
```

**Windows:**
```
%APPDATA%\Claude\mcp.json
```

**If file doesn't exist:** Create it with `{}`

---

## Step 2: Add RAGLite MCP Configuration

Add the following to your `mcp.json` file:

**macOS/Linux:**
```json
{
  "mcpServers": {
    "raglite": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "raglite.main"
      ],
      "cwd": "/ABSOLUTE/PATH/TO/RAGLite",
      "env": {
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/RAGLite"
      }
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "raglite": {
      "command": "uv.exe",
      "args": [
        "run",
        "python",
        "-m",
        "raglite.main"
      ],
      "cwd": "C:\\ABSOLUTE\\PATH\\TO\\RAGLite",
      "env": {
        "PYTHONPATH": "C:\\ABSOLUTE\\PATH\\TO\\RAGLite"
      }
    }
  }
}
```

**⚠️ IMPORTANT:** Replace `/ABSOLUTE/PATH/TO/RAGLite` with your actual project path.

**Example (macOS):**
```json
"cwd": "/Users/ricardo/DeveloperFolder/RAGLite",
"env": {
  "PYTHONPATH": "/Users/ricardo/DeveloperFolder/RAGLite"
}
```

---

## Step 3: Restart Claude Desktop

1. **Quit Claude Desktop completely** (not just close window)
   - macOS: Cmd+Q or Claude > Quit
   - Windows: Right-click tray icon > Quit

2. **Reopen Claude Desktop**

3. **Wait 5-10 seconds** for MCP server to initialize

---

## Step 4: Verify Connection

**Check MCP Server List:**
1. Open Claude Desktop
2. Go to: **Settings > MCP** (or **Developer > MCP**)
3. Look for "**RAGLite**" in the list of connected servers

**If "RAGLite" appears:** ✅ Connection successful!

**If NOT appearing:** See Troubleshooting section below

---

## Step 5: Test Query

Ask Claude a financial question:

**Example queries:**
```
What is the EBITDA for Portugal Cement in August 2025?

Compare variable costs for Portugal and Tunisia

What are all metrics available for Brazil in Q3 2025?
```

**Expected response:**
- Numeric values with units (e.g., "191.8 million EUR")
- Clear citations (page number, table reference)
- Response time <5 seconds

---

## Troubleshooting

### Issue: "RAGLite" not appearing in MCP servers

**Solutions:**

1. **Check file path:**
   - Verify `cwd` path is absolute (not relative)
   - Ensure path has no typos
   - Use forward slashes `/` even on Windows in JSON

2. **Check uv installation:**
   ```bash
   which uv  # macOS/Linux
   where uv  # Windows
   ```
   If not found: Install uv ([instructions](https://docs.astral.sh/uv/))

3. **Check environment variables:**
   ```bash
   cd /path/to/RAGLite
   cat .env  # Verify ANTHROPIC_API_KEY exists
   ```

4. **Check Qdrant/PostgreSQL:**
   ```bash
   docker ps  # Should show qdrant/qdrant and postgres containers
   ```
   If not running: `docker-compose up -d`

5. **Check server logs:**
   ```bash
   cd /path/to/RAGLite
   uv run python -m raglite.main
   # Should start without errors
   # Press Ctrl+C to stop
   ```

### Issue: Server connects but queries fail

**Solutions:**

1. **Check document ingestion:**
   - Have you ingested any PDFs/Excel files?
   - Run: `scripts/ingest-sample-data.sh` (if available)

2. **Check database:**
   ```bash
   docker exec -it raglite-postgres-1 psql -U postgres -d raglite
   SELECT COUNT(*) FROM financial_tables;
   # Should show >0 rows
   ```

3. **Check vector database:**
   - Qdrant should have collection "documents"
   - Verify via: http://localhost:6333/dashboard

### Issue: Slow response times (>10 seconds)

**Solutions:**

1. **Check Docker resources:**
   - Allocate more CPU/memory to Docker
   - Docker Desktop > Settings > Resources

2. **Check network:**
   - Slow API calls to Anthropic Claude API
   - Verify internet connection stable

---

## Advanced Configuration

### Use Custom Qdrant Port

If Qdrant runs on non-default port:

```json
"env": {
  "PYTHONPATH": "/path/to/RAGLite",
  "QDRANT_URL": "http://localhost:CUSTOM_PORT"
}
```

### Use Custom PostgreSQL Connection

If PostgreSQL on different host/port:

```json
"env": {
  "PYTHONPATH": "/path/to/RAGLite",
  "DATABASE_URL": "postgresql://user:pass@host:port/dbname"
}
```

---

## Uninstalling

To remove RAGLite MCP server from Claude Desktop:

1. Edit `~/.claude/mcp.json`
2. Remove the "raglite" entry from "mcpServers"
3. Restart Claude Desktop

---

## Support

**Issues or Questions:**
- Check: [GitHub Issues](https://github.com/YOUR_USERNAME/RAGLite/issues)
- Documentation: [RAGLite README](../README.md)
- Architecture: [docs/architecture/](../architecture/)

---

**Last Updated:** 2025-11-06
**Tested With:** Claude Desktop 1.x, RAGLite Epic 2
