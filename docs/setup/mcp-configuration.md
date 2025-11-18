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

## Troubleshooting

See full troubleshooting guide in this document for common issues.

**Last Updated:** 2025-11-07
