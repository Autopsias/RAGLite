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
