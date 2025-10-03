# 6. Complete Reference Implementation

## 6.1 MCP Server (raglite/main.py)

**This is the COMPLETE reference implementation.** AI agents should copy these patterns for all modules.

*[See architecture-v1.1-insert.md for the complete 250-line reference implementation]*

**Key file:** `raglite/main.py` (~200 lines)

**Demonstrates:**
- ✅ FastMCP server setup with lifespan management
- ✅ Pydantic model definitions for MCP tools
- ✅ Structured logging with context (`extra={}`)
- ✅ Error handling with specific exceptions
- ✅ Type hints for all functions
- ✅ Google-style docstrings
- ✅ Async patterns for I/O operations

**Pattern Summary:**
```python