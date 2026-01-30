# MCP Tools - Document Ingestion

RAGLite MCP server supports two input modes for document ingestion.

---

## Ingestion Modes

### Mode 1 - Filesystem Path (Claude Code / CLI)
```python
# Use when MCP server has filesystem access to the document
await ingest_financial_document(doc_path="/path/to/Q3_Report.pdf")
```

### Mode 2 - Base64 Content (Claude.ai / Remote)
```python
# Use when document is uploaded to Claude.ai (no filesystem access)
# The server cannot access Claude.ai's sandbox - pass content directly
await ingest_financial_document(
    file_content="JVBERi0xLjQg...",  # Base64-encoded file content
    filename="Q3_Report.pdf"          # Original filename with extension
)
```

---

## When to Use Each Mode

| Scenario | Mode | Tool |
|----------|------|------|
| Claude Code with local files | Mode 1 (doc_path) | `ingest_financial_document` |
| Claude.ai with uploaded files | Mode 2 (file_content) | `ingest_financial_document` |
| Large files (>50 pages) | Mode 1 or 2 | `ingest_financial_document_async` |

---

## Limitations (Mode 2)

- **Max file size:** 25MB base64 encoded (~18MB decoded)
- **Supported formats:** `.pdf`, `.xlsx`, `.xls` only
- **For larger files:** Save to filesystem and use Mode 1

---

## Example: Claude.ai Document Upload

When a user uploads a file to Claude.ai and asks to ingest it:

1. Read the file content using Claude's file handling
2. Encode to base64
3. Call the ingestion tool with `file_content` and `filename`
4. The MCP server creates a temp file, processes it, then cleans up

---

## Programmatic Tool Invocation (Testing)

**EBITDA bug fix (2026-01-29):** When testing MCP tools programmatically (Python code, not MCP protocol),
use the `.fn` property to access the underlying async function.

### Problem

```python
# WRONG - raises "'FunctionTool' object is not callable"
result = await get_financial_forecast(request)
```

### Solution

```python
# CORRECT - access the underlying function via .fn
result = await get_financial_forecast.fn(request)
```

### Explanation

The `@mcp.tool()` decorator wraps functions in `FunctionTool` objects for MCP protocol handling.
These wrapper objects are not directly callable as functions. The `.fn` property provides
access to the original async function for direct invocation.

| Context | Invocation Method |
|---------|-------------------|
| MCP Protocol (Claude Desktop) | Protocol handles invocation automatically |
| Python Tests | Use `tool_name.fn(args)` |
| Integration Tests | Use `tool_name.fn(args)` with mocked dependencies |

### Affected Tools

All tools decorated with `@mcp.tool()` in `raglite/mcp/tools/`:
- `get_financial_forecast` / `get_financial_forecast_async`
- `ingest_financial_document` / `ingest_financial_document_async`
- `query_financial_documents`
- `get_health_status`
- `validate_forecasting_accuracy`
