"""RAGLite MCP Server - Model Context Protocol entry point.

This module implements the FastMCP server that exposes RAGLite capabilities
to MCP clients (Claude Desktop, etc.). Provides seven core tools:
  1. ingest_financial_document - Ingest PDF/Excel documents (sync, <50 pages)
  2. ingest_financial_document_async - Async ingestion for large documents (>50 pages, Story 4.0.3)
  3. get_ingestion_status - Poll async ingestion job status (Story 4.0.3)
  4. query_financial_documents - Query documents using natural language (Epic 1-2)
  5. analytical_query_financial_documents - Advanced multi-step analytical queries (Epic 3)
  6. get_financial_forecast - Query financial forecasts via natural language (Epic 4, Story 4.4)
  7. get_financial_insights - Request proactive insights combining anomalies, trends, recommendations (Epic 4, Story 4.9)

The server follows standard MCP pattern: tools return raw data (chunks with metadata),
and the LLM client (Claude) synthesizes natural language answers.

Example:
    Start server locally:
    $ uv run python -m raglite.main

    Connect Claude Desktop to:
    - Server Name: RAGLite
    - Transport: stdio
"""

import time
from pathlib import Path

from fastmcp import FastMCP

from raglite.agentic.fallback import FallbackResponse, handle_workflow_failure
from raglite.agentic.orchestrator import WorkflowExecutor
from raglite.agentic.planner import QueryComplexity, classify_query_complexity, decompose_query
from raglite.forecasting.auto_update import trigger_forecast_refresh
from raglite.forecasting.hybrid import InsufficientDataError, generate_forecast
from raglite.forecasting.timeseries_extract import (
    ExtractionError,
    extract_timeseries,
    extract_timeseries_from_sql,
)
from raglite.ingestion.document_ingestion import temp_file_from_base64, temp_file_from_url
from raglite.ingestion.job_tracker import create_job, get_job_status, start_background_job
from raglite.ingestion.pipeline import ingest_document
from raglite.retrieval.attribution import generate_citations
from raglite.retrieval.multi_index_search import MultiIndexSearchError, multi_index_search
from raglite.retrieval.search import QueryError
from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import (
    AnalyticalQueryRequest,
    AnalyticalQueryResponse,
    AsyncIngestionResponse,
    DocumentMetadata,
    ForecastQueryRequest,
    ForecastQueryResponse,
    IngestionJobStatus,
    IngestionResult,
    Insight,
    InsightCategory,
    InsightsQueryRequest,
    InsightsQueryResponse,
    QueryRequest,
    QueryResponse,
    Recommendation,
)

# Initialize structured logger
logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("RAGLite")


class DocumentProcessingError(Exception):
    """Raised when document ingestion or processing fails.

    This exception is raised for any failure during document processing,
    including file not found, parsing errors, embedding generation failures,
    and vector storage errors.
    """

    pass


async def _perform_forecast_refresh(
    metadata: DocumentMetadata,
    auto_forecast: bool,
) -> IngestionResult:
    """Perform forecast refresh after ingestion and return enriched result.

    Story 4.3 AC1/AC3/AC4: Post-ingestion forecast refresh with timeout.

    Args:
        metadata: Document metadata from ingestion
        auto_forecast: Whether to attempt forecast refresh

    Returns:
        IngestionResult with forecast refresh status
    """
    forecasts_updated: list[str] | None = None
    forecast_skip_reason: str | None = None

    if not auto_forecast:
        forecast_skip_reason = "auto_forecast=False"
    elif not settings.enable_forecast_auto_update:
        forecast_skip_reason = "forecast_auto_update disabled in settings"
    else:
        # Attempt forecast refresh with timeout protection (AC3)
        try:
            refresh_result = await trigger_forecast_refresh(
                metadata, timeout_seconds=settings.forecast_refresh_timeout
            )

            if refresh_result.success:
                forecasts_updated = refresh_result.metrics_refreshed
                if refresh_result.metrics_skipped:
                    logger.info(
                        "Some metrics skipped during forecast refresh",
                        extra={
                            "doc_filename": metadata.filename,
                            "skipped": refresh_result.metrics_skipped,
                        },
                    )
            else:
                forecast_skip_reason = refresh_result.error_message or "refresh failed"
                logger.warning(
                    "Forecast refresh failed",
                    extra={
                        "doc_filename": metadata.filename,
                        "error": forecast_skip_reason,
                    },
                )

        except Exception as e:
            # AC3: Graceful degradation - don't fail ingestion if forecast refresh fails
            forecast_skip_reason = f"unexpected error: {type(e).__name__}"
            logger.warning(
                "Forecast refresh failed unexpectedly",
                extra={"doc_filename": metadata.filename, "error": str(e)},
            )

    return IngestionResult.from_metadata(
        metadata,
        forecasts_updated=forecasts_updated,
        forecast_refresh_skipped_reason=forecast_skip_reason,
    )


@mcp.tool()
async def ingest_financial_document(
    doc_path: str | None = None,
    file_content: str | None = None,
    filename: str | None = None,
    doc_url: str | None = None,
    auto_forecast: bool = True,
) -> IngestionResult:
    """Ingest financial PDF or Excel document into RAGLite knowledge base.

    Story 4.0.7/4.0.8: Supports THREE input modes for maximum compatibility.

    ╔══════════════════════════════════════════════════════════════════════════╗
    ║  IMPORTANT: CHOOSING THE RIGHT MODE FOR YOUR CLAUDE CLIENT               ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║                                                                          ║
    ║  🖥️  CLAUDE CODE (this terminal):                                        ║
    ║      → Use Mode 1 (doc_path) - Full filesystem access                    ║
    ║      → Example: doc_path="/Users/you/Documents/report.pdf"               ║
    ║                                                                          ║
    ║  🖥️  CLAUDE DESKTOP with Filesystem MCP Server configured:               ║
    ║      → Use Mode 1 (doc_path) - Access configured directories             ║
    ║      → Do NOT drag files into conversation (creates sandboxed path)      ║
    ║      → Instead, reference files by their REAL filesystem path            ║
    ║                                                                          ║
    ║  🌐  CLAUDE DESKTOP (file dragged into conversation):                    ║
    ║      → ❌ WILL NOT WORK - Files are sandboxed at /mnt/user-data/uploads/ ║
    ║      → ✅ Use Mode 3 (doc_url) instead - Upload to cloud, provide URL    ║
    ║                                                                          ║
    ║  🌐  CLAUDE.AI (web interface):                                          ║
    ║      → ❌ WILL NOT WORK - Files are sandboxed, MCP cannot access         ║
    ║      → ✅ Use Mode 3 (doc_url) - Upload to Google Drive/Dropbox/S3       ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    **Mode 1 - Filesystem Path (Claude Code / Desktop with Filesystem MCP):**
        Provide `doc_path` for documents accessible via MCP server filesystem.
        Best for: Local development, configured directories, CI/CD pipelines.

    **Mode 2 - Base64 Content (Programmatic / API):**
        Provide `file_content` (base64-encoded) and `filename`.
        Best for: Programmatic ingestion, API integrations, small files (<18MB).
        Note: Claude.ai/Desktop CANNOT automatically encode uploaded files.

    **Mode 3 - URL Download (Claude.ai / Desktop - RECOMMENDED):**
        Provide `doc_url` with direct download link to the document.
        Best for: Claude.ai, Claude Desktop when files are uploaded to conversation.
        Supports: Google Drive, Dropbox, S3 presigned URLs, any direct file URL.

    **Why Mode 3 for Claude.ai/Desktop uploaded files?**
        When you drag a file into Claude.ai or Claude Desktop, it gets stored in
        a sandboxed location (/mnt/user-data/uploads/) that MCP servers cannot
        access. The MCP protocol doesn't support file transfer from client to
        server. URL-based ingestion sidesteps this limitation entirely.

    **Workflow for Claude.ai / Claude Desktop users:**
        1. Upload your file to cloud storage (Google Drive, Dropbox, S3, etc.)
        2. Get a direct/shareable download link
        3. Use this tool with doc_url parameter

    Processes the document through the complete ingestion pipeline:
      1. Extract text/tables (Docling for PDF, openpyxl for Excel)
      2. Chunk content into semantic units
      3. Generate embeddings (Fin-E5 model)
      4. Store vectors in Qdrant with metadata

    **Performance & Timeout Considerations:**
      - Small files (<10 pages): ~2-5 minutes (MCP timeout safe)
      - Large files (>10 pages): May timeout - use async version
      - URL downloads: Additional time for network transfer

    **For Large Files:** Use async ingestion to avoid MCP timeouts:
        >>> response = await ingest_financial_document_async(doc_path="...")
        >>> # Poll status until complete

    Args:
        doc_path: Absolute or relative path to document file (.pdf, .xlsx, .xls).
                  Use for Mode 1 (filesystem access).
                  Cannot be combined with file_content or doc_url.

        file_content: Base64-encoded file content. Use for Mode 2.
                      Max size: 25MB encoded (~18MB decoded).
                      Requires `filename` parameter.
                      Cannot be combined with doc_path or doc_url.

        filename: Original filename with extension (e.g., "Q3_Report.pdf").
                  Required when using file_content.

        doc_url: HTTP/HTTPS URL to download document from. Use for Mode 3.
                 Max file size: 50MB. Timeout: 5 minutes.
                 Supports Google Drive export links, Dropbox (dl=1), S3 presigned.
                 Cannot be combined with doc_path or file_content.

        auto_forecast: If True, automatically refresh forecasts after ingestion
                       (Story 4.3). Default True. Set False to skip forecast refresh
                       (e.g., for batch ingestion or when forecasting not needed).

    Returns:
        IngestionResult with ingestion results including:
          - filename: Original document name
          - doc_type: PDF or Excel
          - ingestion_timestamp: ISO8601 timestamp
          - page_count: Number of pages/sheets
          - chunk_count: Number of chunks created
          - forecasts_updated: List of refreshed metrics (Story 4.3 AC4)
          - forecast_refresh_skipped_reason: Why refresh was skipped (if applicable)

    Raises:
        DocumentProcessingError: If ingestion fails due to:
          - Invalid input combination
          - File not found / URL download failure
          - Unsupported file extension
          - File size exceeds limits
          - Parsing or embedding generation failure

    Example (Mode 1 - filesystem path):
        >>> metadata = await ingest_financial_document(doc_path="/data/Q3_Report.pdf")
        >>> print(f"Ingested {metadata.chunk_count} chunks")

    Example (Mode 2 - base64 content):
        >>> metadata = await ingest_financial_document(
        ...     file_content="JVBERi0xLjQg...",
        ...     filename="Q3_Report.pdf"
        ... )

    Example (Mode 3 - URL download - RECOMMENDED for Claude.ai):
        >>> # User uploaded file to Google Drive and got shareable link
        >>> metadata = await ingest_financial_document(
        ...     doc_url="https://drive.google.com/uc?export=download&id=FILE_ID"
        ... )
        >>> print(f"Ingested {metadata.chunk_count} chunks from {metadata.filename}")
    """
    # AC2: Input validation - mutual exclusivity (now supports 3 modes)
    has_path = doc_path is not None
    has_content = file_content is not None
    has_filename = filename is not None
    has_url = doc_url is not None

    # Count how many input modes are provided
    input_modes = sum([has_path, has_content, has_url])

    if input_modes == 0:
        raise DocumentProcessingError(
            "Must provide one of: doc_path, file_content + filename, or doc_url.\n\n"
            "📁 Mode 1 (doc_path): For Claude Code or configured Filesystem MCP directories\n"
            "📦 Mode 2 (file_content): For programmatic/API base64 uploads\n"
            "🌐 Mode 3 (doc_url): For Claude.ai/Desktop - upload to cloud, provide URL\n\n"
            "⚠️  If you dragged a file into Claude.ai or Claude Desktop, use Mode 3:\n"
            "    1. Upload file to Google Drive/Dropbox/S3\n"
            "    2. Get shareable download link\n"
            "    3. Call this tool with doc_url parameter"
        )

    if input_modes > 1:
        raise DocumentProcessingError(
            "Only one input mode allowed. Provide exactly one of:\n"
            "- doc_path (filesystem path)\n"
            "- file_content + filename (base64)\n"
            "- doc_url (URL download)"
        )

    if has_content and not has_filename:
        raise DocumentProcessingError(
            "filename is required when using file_content. "
            "Provide the original filename with extension (e.g., 'report.pdf')."
        )

    # Mode 3: URL download (Story 4.0.8 - Recommended for Claude.ai/Desktop)
    if has_url:
        assert doc_url is not None  # Type narrowing for mypy
        logger.info(
            "Ingesting document from URL",
            extra={"url_truncated": doc_url[:80] + "..." if len(doc_url) > 80 else doc_url},
        )

        try:
            # Download file and process with automatic cleanup
            with temp_file_from_url(doc_url) as (tmp_path, detected_filename):
                start_time = time.perf_counter()
                metadata = await ingest_document(tmp_path)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Use detected filename from URL/headers
                metadata.filename = detected_filename

                logger.info(
                    "Ingestion complete (URL)",
                    extra={
                        "doc_id": metadata.filename,
                        "doc_type": metadata.doc_type,
                        "chunks": metadata.chunk_count,
                        "pages": metadata.page_count,
                        "duration_ms": f"{duration_ms:.2f}",
                        "input_mode": "url",
                    },
                )

                # Story 4.3: Forecast refresh after ingestion
                return await _perform_forecast_refresh(metadata, auto_forecast)

        except ValueError as e:
            # URL validation errors (scheme, domain, size, extension)
            logger.error(
                "URL ingestion failed - validation error",
                extra={"url_truncated": doc_url[:80], "error": str(e)},
            )
            raise DocumentProcessingError(str(e)) from e

        except RuntimeError as e:
            # Download failures (network, HTTP errors, timeout)
            logger.error(
                "URL ingestion failed - download error",
                extra={"url_truncated": doc_url[:80], "error": str(e)},
            )
            raise DocumentProcessingError(str(e)) from e

        except Exception as e:
            logger.error(
                "Ingestion failed (URL)",
                extra={
                    "url_truncated": doc_url[:80],
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise DocumentProcessingError(f"Failed to ingest from URL: {e}") from e

    # Mode 2: Base64 content (Story 4.0.7)
    elif has_content:
        assert file_content is not None and filename is not None  # Type narrowing
        logger.info(
            "Ingesting document from base64 content",
            extra={"doc_filename": filename, "content_size": len(file_content)},
        )

        try:
            # Create temp file from base64 with automatic cleanup
            with temp_file_from_base64(file_content, filename) as tmp_path:
                start_time = time.perf_counter()
                metadata = await ingest_document(tmp_path)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Override metadata.filename with original filename (not temp path)
                metadata.filename = filename

                logger.info(
                    "Ingestion complete (base64)",
                    extra={
                        "doc_id": metadata.filename,
                        "doc_type": metadata.doc_type,
                        "chunks": metadata.chunk_count,
                        "pages": metadata.page_count,
                        "duration_ms": f"{duration_ms:.2f}",
                        "input_mode": "base64",
                    },
                )

                # Story 4.3: Forecast refresh after ingestion
                return await _perform_forecast_refresh(metadata, auto_forecast)

        except ValueError as e:
            # Base64 validation errors (size, extension, decode)
            logger.error(
                "Base64 ingestion failed - validation error",
                extra={"doc_filename": filename, "error": str(e)},
            )
            raise DocumentProcessingError(str(e)) from e

        except Exception as e:
            logger.error(
                "Ingestion failed (base64)",
                extra={"doc_filename": filename, "error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            raise DocumentProcessingError(f"Failed to ingest {filename}: {e}") from e

    # Mode 1: Filesystem path (default, backward compatible)
    # If we got here, has_path must be True (validated above)
    else:
        assert doc_path is not None  # Type narrowing for mypy
        effective_path = doc_path

        logger.info("Ingesting document", extra={"path": effective_path})

        try:
            # Call Story 1.2 ingestion pipeline
            start_time = time.perf_counter()
            metadata = await ingest_document(effective_path)
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Ingestion complete",
                extra={
                    "doc_id": metadata.filename,
                    "doc_type": metadata.doc_type,
                    "chunks": metadata.chunk_count,
                    "pages": metadata.page_count,
                    "duration_ms": f"{duration_ms:.2f}",
                    "input_mode": "path",
                },
            )

            # Story 4.3: Forecast refresh after ingestion
            return await _perform_forecast_refresh(metadata, auto_forecast)

        except FileNotFoundError as e:
            logger.error(
                "Document not found",
                extra={"path": effective_path, "error": str(e)},
                exc_info=True,
            )
            raise DocumentProcessingError(f"Document not found: {effective_path}") from e

        except Exception as e:
            logger.error(
                "Ingestion failed",
                extra={"path": effective_path, "error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            raise DocumentProcessingError(f"Failed to ingest {effective_path}: {e}") from e


@mcp.tool()
async def ingest_financial_document_async(
    doc_path: str | None = None,
    file_content: str | None = None,
    filename: str | None = None,
    doc_url: str | None = None,
) -> AsyncIngestionResponse:
    """Ingest large financial documents asynchronously to avoid MCP timeout.

    Story 4.0.3 AC5: Async ingestion for large documents (150-200 pages).
    Story 4.0.7/4.0.8: Extended with base64 and URL support (same modes as sync version).

    **When to Use:**
    - Documents >50 pages (estimated time >6 minutes)
    - Any document where sync ingestion previously timed out
    - Large quarterly/annual reports (150-200 pages)

    **How It Works:**
    1. Returns immediately with job ID (no blocking)
    2. Ingestion runs in background
    3. Poll status with `get_ingestion_status(job_id)`
    4. Query document normally after completion

    **Input Modes (same as sync version):**
    - Mode 1 - doc_path: For documents accessible via MCP server filesystem
    - Mode 2 - file_content + filename: For base64-encoded uploads
    - Mode 3 - doc_url: For URL downloads (recommended for Claude.ai/Desktop)

    **Performance Guidance:**
    - Small docs (<10 pages): ~30-60s → Use `ingest_financial_document` (sync)
    - Medium docs (10-50 pages): ~1-6 min → Use `ingest_financial_document` (sync, may timeout)
    - Large docs (>50 pages): 6-30+ min → Use THIS TOOL (async, no timeout)

    Args:
        doc_path: Absolute or relative path to document file (.pdf, .xlsx, .xls).
                  Use for Mode 1. Cannot be combined with file_content or doc_url.
        file_content: Base64-encoded file content. Use for Mode 2.
                      Max size: 25MB encoded (~18MB decoded file).
                      Requires filename parameter.
        filename: Original filename with extension (e.g., "Q3_Report.pdf").
                  Required when using file_content.
        doc_url: HTTP/HTTPS URL to download document from. Use for Mode 3.
                 Max file size: 50MB. Recommended for Claude.ai/Desktop.

    Returns:
        AsyncIngestionResponse with:
          - job_id: Unique identifier for status polling
          - status: Initial status ("started")
          - message: User-friendly instructions
          - estimated_time_s: Estimated completion time (based on page count if available)

    Raises:
        DocumentProcessingError: If file doesn't exist, path is invalid, or validation fails

    Example - Async Ingestion (filesystem path):
        >>> response = await ingest_financial_document_async(doc_path="/data/Annual_Report.pdf")
        >>> print(response.job_id)

    Example - Async Ingestion (URL - recommended for Claude.ai):
        >>> response = await ingest_financial_document_async(
        ...     doc_url="https://drive.google.com/uc?export=download&id=FILE_ID"
        ... )
        >>> # Poll status until complete
        >>> while True:
        ...     status = await get_ingestion_status(response.job_id)
        ...     if status.status in ["completed", "failed"]:
        ...         break
        ...     await asyncio.sleep(60)

    Note:
        Jobs are stored in-memory only (MVP). Jobs lost on server restart.
        Epic 5 (Production) will add persistent job storage with Redis.
    """
    import base64
    import tempfile
    import urllib.parse
    import urllib.request
    from urllib.error import HTTPError, URLError

    from raglite.ingestion.document_ingestion import (
        ALLOWED_URL_SCHEMES,
        MAX_URL_DOWNLOAD_SIZE_BYTES,
        URL_DOMAIN_ALLOWLIST,
        URL_DOWNLOAD_TIMEOUT_TOTAL,
    )

    # Input validation - mutual exclusivity (supports 3 modes)
    has_path = doc_path is not None
    has_content = file_content is not None
    has_filename = filename is not None
    has_url = doc_url is not None

    input_modes = sum([has_path, has_content, has_url])

    if input_modes == 0:
        raise DocumentProcessingError(
            "Must provide one of: doc_path, file_content + filename, or doc_url.\n"
            "For Claude.ai/Desktop: Use doc_url with a shareable download link."
        )

    if input_modes > 1:
        raise DocumentProcessingError(
            "Only one input mode allowed. Provide exactly one of:\n"
            "- doc_path (filesystem path)\n"
            "- file_content + filename (base64)\n"
            "- doc_url (URL download)"
        )

    if has_content and not has_filename:
        raise DocumentProcessingError(
            "filename is required when using file_content. "
            "Provide the original filename with extension (e.g., 'report.pdf')."
        )

    # Variables for job creation
    effective_path: str
    display_name: str
    temp_path_to_cleanup: str | None = None
    original_filename: str | None = None

    # Import constants
    from raglite.ingestion.document_ingestion import (
        MAX_BASE64_CONTENT_SIZE_BYTES,
        SUPPORTED_EXTENSIONS,
    )

    # Mode 3: URL download (Story 4.0.8)
    if has_url:
        assert doc_url is not None  # Type narrowing for mypy
        logger.info(
            "Async ingestion requested (URL)",
            extra={"url_truncated": doc_url[:80] + "..." if len(doc_url) > 80 else doc_url},
        )

        # Parse and validate URL
        parsed = urllib.parse.urlparse(doc_url)

        # Scheme validation
        if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
            raise DocumentProcessingError(
                f"URL scheme '{parsed.scheme}' not allowed. Use http or https."
            )

        # Domain allowlist check
        if URL_DOMAIN_ALLOWLIST and parsed.netloc.lower() not in URL_DOMAIN_ALLOWLIST:
            raise DocumentProcessingError(f"Domain '{parsed.netloc}' not in allowlist.")

        # Extract filename from URL
        url_path = urllib.parse.unquote(parsed.path)
        filename_from_url = Path(url_path).name if url_path else "downloaded_document"

        # Download file for background job
        try:
            request = urllib.request.Request(
                doc_url,
                headers={
                    "User-Agent": "RAGLite/1.0 (Financial Document Ingestion)",
                    "Accept": "application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*",
                },
            )

            with urllib.request.urlopen(request, timeout=URL_DOWNLOAD_TIMEOUT_TOTAL) as response:  # nosec B310 - URL scheme validated above
                # Check size
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_URL_DOWNLOAD_SIZE_BYTES:
                    raise DocumentProcessingError(
                        f"File too large. Maximum: {MAX_URL_DOWNLOAD_SIZE_BYTES / (1024 * 1024):.0f}MB"
                    )

                # Get filename from header if available
                content_disposition = response.headers.get("Content-Disposition", "")
                if "filename=" in content_disposition:
                    import re

                    match = re.search(r'filename[*]?=["\']?([^"\';\n]+)', content_disposition)
                    if match:
                        filename_from_url = match.group(1).strip()

                # Determine extension
                suffix = Path(filename_from_url).suffix.lower()
                if not suffix:
                    content_type = response.headers.get("Content-Type", "")
                    if "pdf" in content_type:
                        suffix = ".pdf"
                        filename_from_url = "downloaded_document.pdf"
                    elif "spreadsheet" in content_type or "excel" in content_type:
                        suffix = ".xlsx"
                        filename_from_url = "downloaded_document.xlsx"
                    else:
                        raise DocumentProcessingError(
                            "Cannot determine file type from URL. "
                            "Ensure URL ends with .pdf, .xlsx, or .xls"
                        )

                if suffix not in SUPPORTED_EXTENSIONS:
                    raise DocumentProcessingError(
                        f"Unsupported file type: {suffix}. Supported: .pdf, .xlsx, .xls"
                    )

                # Download to persistent temp file
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    downloaded_size = 0
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        downloaded_size += len(chunk)
                        if downloaded_size > MAX_URL_DOWNLOAD_SIZE_BYTES:
                            raise DocumentProcessingError("Download exceeded size limit")
                        tmp.write(chunk)
                    temp_path = tmp.name

                effective_path = temp_path
                display_name = filename_from_url
                temp_path_to_cleanup = temp_path
                original_filename = filename_from_url

                logger.info(
                    "Downloaded file for async ingestion",
                    extra={
                        "url_domain": parsed.netloc,
                        "filename": filename_from_url,
                        "size_bytes": downloaded_size,
                        "temp_path": temp_path,
                    },
                )

        except HTTPError as e:
            raise DocumentProcessingError(f"URL download failed: HTTP {e.code} {e.reason}") from e
        except URLError as e:
            raise DocumentProcessingError(f"URL download failed: {e.reason}") from e
        except TimeoutError:
            raise DocumentProcessingError(
                f"Download timed out after {URL_DOWNLOAD_TIMEOUT_TOTAL}s"
            ) from None

    # Mode 2: Base64 content (Story 4.0.7)
    elif has_content:
        assert file_content is not None and filename is not None  # Type narrowing
        logger.info(
            "Async ingestion requested (base64)",
            extra={"doc_filename": filename, "content_size": len(file_content)},
        )

        # Size validation
        if len(file_content) > MAX_BASE64_CONTENT_SIZE_BYTES:
            size_mb = len(file_content) / (1024 * 1024)
            raise DocumentProcessingError(
                f"File content ({size_mb:.1f}MB encoded) exceeds 25MB limit. "
                "For larger files, save to filesystem and use doc_path parameter."
            )

        # Decode base64
        try:
            file_bytes = base64.b64decode(file_content)
        except Exception as e:
            raise DocumentProcessingError(f"Invalid base64 content: {e}") from e

        # Extension validation
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise DocumentProcessingError(
                f"Unsupported file type: {suffix}. Supported extensions: {supported}"
            )

        # Create temp file that persists for background job (delete=False)
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_bytes)
                temp_path = tmp.name

            effective_path = temp_path
            display_name = filename
            temp_path_to_cleanup = temp_path
            original_filename = filename

            logger.info(
                "Created persistent temp file for async base64 ingestion",
                extra={
                    "doc_filename": filename,
                    "temp_path": temp_path,
                    "size_bytes": len(file_bytes),
                },
            )

        except Exception as e:
            raise DocumentProcessingError(f"Failed to create temp file: {e}") from e

    # Mode 1: Filesystem path (default)
    else:
        assert doc_path is not None  # Type narrowing for mypy
        logger.info("Async ingestion requested", extra={"path": doc_path})

        doc_file = Path(doc_path).resolve()
        if not doc_file.exists():
            error_msg = f"Document not found: {doc_path}"
            logger.error(
                "Async ingestion failed - file not found",
                extra={"path": str(doc_file), "error": error_msg},
            )
            raise DocumentProcessingError(error_msg)

        effective_path = str(doc_file)
        display_name = doc_file.name

    # Create job
    job_id = create_job(effective_path)

    # Start background ingestion (fire-and-forget)
    # Story 4.0.7: Pass temp file info for cleanup after job completes
    start_background_job(
        job_id,
        effective_path,
        temp_path_to_cleanup=temp_path_to_cleanup,
        original_filename=original_filename,
    )

    # Estimate completion time (7.29s/page from Task 1 investigation)
    estimated_time_s = None  # Will be updated after first progress check

    message = (
        f"Ingestion started for {display_name}. "
        f"Use get_ingestion_status('{job_id}') to check progress. "
        f"Large documents (150-200 pages) may take 15-30 minutes."
    )

    logger.info(
        "Async ingestion job started",
        extra={
            "job_id": job_id,
            "doc_path": effective_path,
            "input_mode": "base64" if has_content else "path",
        },
    )

    return AsyncIngestionResponse(
        job_id=job_id,
        status="started",
        message=message,
        estimated_time_s=estimated_time_s,
    )


@mcp.tool()
async def get_ingestion_status(job_id: str) -> IngestionJobStatus:
    """Check status of async document ingestion job.

    Story 4.0.3 AC5: Status polling for async ingestion jobs.

    Poll this endpoint periodically to check job progress. Recommended polling interval:
    - Every 30-60 seconds for large documents (150-200 pages)
    - Every 10-15 seconds for medium documents (50-100 pages)

    Args:
        job_id: Unique job identifier from `ingest_financial_document_async`

    Returns:
        IngestionJobStatus with:
          - job_id: Job identifier
          - status: "pending", "in_progress", "completed", or "failed"
          - progress: Progress percentage (0-100) if available
          - result: DocumentMetadata (only when status="completed")
          - error: Error message (only when status="failed")
          - started_at: Job start timestamp (ISO 8601)
          - completed_at: Completion timestamp (ISO 8601, only when done)

    Raises:
        ValueError: If job_id not found (invalid or expired)

    Example:
        >>> status = await get_ingestion_status("a3f8b2c1-4d5e-6f7g-8h9i...")
        >>> print(status.status)
        "in_progress"
        >>> print(status.progress)
        10

        >>> # Poll until complete
        >>> while status.status == "in_progress":
        ...     await asyncio.sleep(60)  # Wait 1 minute
        ...     status = await get_ingestion_status(job_id)
        >>> print(status.status)
        "completed"
        >>> print(status.result.chunk_count)
        1247

    Note:
        Jobs are stored in-memory only (MVP). Jobs lost on server restart.
    """
    logger.info("Checking job status", extra={"job_id": job_id})

    job_status = get_job_status(job_id)

    if job_status is None:
        error_msg = f"Job not found: {job_id}. Job may have expired or server restarted."
        logger.warning("Job status check failed - job not found", extra={"job_id": job_id})
        raise ValueError(error_msg)

    logger.info(
        "Job status retrieved",
        extra={
            "job_id": job_id,
            "status": job_status.status,
            "progress": job_status.progress,
        },
    )

    return job_status


@mcp.tool()
async def query_financial_documents(request: QueryRequest) -> QueryResponse:
    """Query financial documents using natural language with multi-index search.

    Story 2.7 AC4: Updated to use multi-index search (vector + SQL) with intelligent
    query routing. Maintains backward compatibility with Story 2.1 hybrid search.

    Query pipeline (Story 2.7):
      1. Classify query type (SQL_ONLY, VECTOR_ONLY, or HYBRID)
      2. Route to appropriate index(es):
         - SQL_ONLY → PostgreSQL table search
         - VECTOR_ONLY → Qdrant semantic search
         - HYBRID → Both indexes in parallel with fusion
      3. Generate source citations for each chunk
      4. Return raw chunks with metadata for LLM synthesis

    Args:
        request: Query parameters containing:
          - query: Natural language query string
          - top_k: Number of results to return (default: 5, range: 1-50)

    Returns:
        QueryResponse containing:
          - results: List of QueryResult objects with:
              * text: Chunk content with appended citation
              * score: Similarity score (0-1, higher is better)
              * source_document: Document filename
              * page_number: Page where chunk appears (or None)
              * chunk_index: Sequential chunk index
              * word_count: Chunk word count
          - query: Original query string
          - retrieval_time_ms: Retrieval time in milliseconds

    Raises:
        QueryError: If search fails (empty query, embedding error, index error)

    Example:
        >>> request = QueryRequest(query="What was Q3 revenue?", top_k=5)
        >>> response = await query_financial_documents(request)
        >>> for result in response.results:
        ...     print(f"[{result.score:.2f}] {result.text}")
    """
    logger.info(
        "Query received",
        extra={
            "query": request.query,
            "top_k": request.top_k,
        },
    )

    # Validate query
    if not request.query or not request.query.strip():
        error_msg = "Query cannot be empty"
        logger.warning("Empty query rejected", extra={"query": request.query})
        raise QueryError(error_msg)

    try:
        # Story 2.7: Call multi-index search (vector + SQL routing)
        start_time = time.perf_counter()
        search_results = await multi_index_search(request.query, top_k=request.top_k)
        search_duration_ms = (time.perf_counter() - start_time) * 1000

        # Convert SearchResult to QueryResult for backward compatibility
        from raglite.shared.models import QueryResult

        query_results = [
            QueryResult(
                score=r.score,
                text=r.text,
                source_document=r.document_id,
                page_number=r.page_number,
                chunk_index=r.metadata.get("chunk_index", 0),
                word_count=r.metadata.get("word_count", 0),
            )
            for r in search_results
        ]

        # Call Story 1.8 citation generation
        cited_results = await generate_citations(query_results)
        total_duration_ms = (time.perf_counter() - start_time) * 1000

        # AC4: Observability logging (classification, index usage, timing)
        retrieval_sources = {r.source for r in search_results}
        logger.info(
            "Query complete (multi-index)",
            extra={
                "query": request.query,
                "results_count": len(cited_results),
                "retrieval_sources": list(
                    retrieval_sources
                ),  # ["vector"], ["sql"], or ["vector", "sql", "hybrid"]
                "search_time_ms": f"{search_duration_ms:.2f}",
                "total_time_ms": f"{total_duration_ms:.2f}",
                "retrieval_method": "multi-index",
            },
        )

        return QueryResponse(
            results=cited_results,
            query=request.query,
            retrieval_time_ms=total_duration_ms,
        )

    except MultiIndexSearchError as e:
        # Story 2.7: Multi-index search error
        logger.error(
            "Multi-index search failed",
            extra={
                "query": request.query,
                "error": str(e),
            },
            exc_info=True,
        )
        raise QueryError(f"Multi-index search failed: {e}") from e

    except QueryError:
        # Re-raise QueryError (already logged in search.py)
        raise

    except Exception as e:
        logger.error(
            "Query failed",
            extra={
                "query": request.query,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise QueryError(f"Query failed: {e}") from e


@mcp.tool()
async def analytical_query_financial_documents(
    request: AnalyticalQueryRequest,
) -> AnalyticalQueryResponse:
    """Query financial documents using multi-step agentic workflow orchestration.

    Story 3.5 AC7: Advanced analytical queries using workflow decomposition and
    specialized agent coordination (Retrieval → Analysis → Synthesis).

    This tool handles complex analytical queries that require multi-step reasoning:
    - YoY/QoQ growth calculations
    - Variance analysis and driver identification
    - Trend analysis over multiple periods
    - Comparative financial analysis

    Workflow pipeline:
      1. Classify query complexity (simple vs analytical)
      2. Decompose analytical queries into sub-tasks with dependencies
      3. Execute workflow with specialized agents (retrieval, analysis, synthesis)
      4. Synthesize final answer with workflow metadata
      5. Graceful degradation to basic search if workflow fails (AC8)

    Args:
        request: Analytical query parameters containing:
          - query: Natural language analytical query
          - top_k: Number of results per retrieval step (default: 5)

    Returns:
        AnalyticalQueryResponse containing:
          - answer: Synthesized natural language answer
          - complexity: Query complexity classification ("simple" or "analytical")
          - workflow_metadata: Execution details:
              * task_count: Number of workflow tasks executed
              * execution_time_ms: Total workflow execution time
              * workflow_pattern: Pattern used (yoy_growth, variance_analysis, etc.)
              * fallback_tier: Quality tier ("full", "partial", "epic1_fallback")
          - confidence: Answer confidence level ("high", "medium", "low")
          - limitations: List of caveats or limitations (empty for full workflow)

    Raises:
        QueryError: If query is empty or invalid

    Example - YoY Growth Analysis:
        >>> request = AnalyticalQueryRequest(
        ...     query="Calculate YoY revenue growth from 2022 to 2023",
        ...     top_k=5
        ... )
        >>> response = await analytical_query_financial_documents(request)
        >>> print(response.answer)
        "Revenue grew 15.3% year-over-year from $245M in 2022 to $283M in 2023..."
        >>> print(response.workflow_metadata)
        {
            "task_count": 4,
            "execution_time_ms": 2847,
            "workflow_pattern": "yoy_growth",
            "fallback_tier": "full"
        }

    Example - Variance Analysis:
        >>> request = AnalyticalQueryRequest(
        ...     query="Explain the variance in Q3 operating expenses"
        ... )
        >>> response = await analytical_query_financial_documents(request)
        >>> print(response.answer)
        "Q3 operating expenses increased by $12M (8.5%)..."

    Example - Comparative Analysis:
        >>> request = AnalyticalQueryRequest(
        ...     query="Compare Q3 2023 revenue with Q3 2024 revenue"
        ... )
        >>> response = await analytical_query_financial_documents(request)
        >>> print(response.answer)
        "Q3 2024 revenue was $283M compared to $245M in Q3 2023..."
        >>> print(response.reasoning_steps)
        ["1. Classified query as analytical (comparative pattern)",
         "2. Retrieved Q3 2023 financial documents",
         "3. Retrieved Q3 2024 financial documents",
         "4. Performed comparative analysis",
         "5. Synthesized final answer from 4 workflow tasks"]

    Graceful Degradation (Story 3.7):
        RAGLite's workflow orchestration includes production-grade error handling
        that ensures users ALWAYS receive a response, even during system issues.

        **4-Tier Degradation System:**

        1. **Tier 1 - Full Orchestration (Best):**
           - All 3 agents succeed (Retrieval → Analysis → Synthesis)
           - Synthesized answer with citations
           - Confidence: "high"
           - Example: "Revenue grew 15.3% YoY from $245M in 2022 to $283M in 2023..."

        2. **Tier 2 - Partial Workflow (Good):**
           - Some agents succeed, others fail
           - Partial results with user-friendly error message
           - Confidence: "medium"
           - Example: "We found Q3 revenue data but experienced delays during analysis.
                      Based on retrieved documents: Q3 2024 revenue was $283M..."

        3. **Tier 3 - Retrieval Only (Acceptable):**
           - Only retrieval succeeds, no analysis
           - Raw document excerpts returned
           - Confidence: "low"
           - Example: "Found 5 relevant documents: [document excerpts...]"

        4. **Tier 4 - Epic 1/2 Fallback (Minimal):**
           - All agents fail, fallback to basic search
           - User-friendly error message with alternative query suggestion
           - Confidence: "none"
           - Example: "Our advanced analysis system is experiencing issues.
                      Here are the documents we found..."

        **Timeout Handling:**
        - Workflow-level timeout: 30 seconds (NFR5)
        - Per-agent timeout: 15 seconds (NFR26)
        - Timeouts trigger automatic tier degradation

        **Error Classification & User-Friendly Messages:**

        RAGLite automatically classifies errors and provides user-friendly messages
        (no technical jargon like "asyncio.TimeoutError"):

        | Technical Error | User-Friendly Message | Fallback Tier |
        |-----------------|----------------------|---------------|
        | Agent timeout (>15s) | "Our analysis system is experiencing delays, but we found some results." | Tier 2 |
        | Workflow timeout (>30s) | "Our advanced analysis system is taking longer than usual. Here are basic search results." | Tier 4 |
        | Claude/Mistral API 503 | "Our AI service is temporarily unavailable. We've provided partial results based on available data." | Tier 2 |
        | Qdrant connection error | "We're experiencing database connectivity issues, but retrieved some results." | Tier 4 |
        | Unexpected error | "We encountered an unexpected issue during analysis. Here are the partial results we gathered." | Tier 2/4 |

        **Alternative Query Suggestions:**

        When degradation occurs, RAGLite suggests alternative queries:
        - Timeout errors: "Try a simpler query like 'What was Q3 revenue?' or break into smaller questions"
        - API failures: "Please wait a moment and try again, or rephrase your question"
        - Connection errors: "Please wait a moment and try again"

        **Example - Timeout Degradation:**
        ```
        >>> request = AnalyticalQueryRequest(
        ...     query="Calculate YoY revenue growth with variance explanation and trend analysis"
        ... )
        >>> response = await analytical_query_financial_documents(request)
        >>> print(response.answer)
        "Our analysis system is experiencing delays, but we found 5 documents
         mentioning revenue data from 2022-2024."
        >>> print(response.confidence)
        "medium"
        >>> print(response.workflow_metadata["fallback_tier"])
        "partial"
        >>> print(response.limitations)
        ["Unable to complete full analysis due to processing delays"]
        >>> # Alternative query suggestion provided in response
        "Try a simpler query like 'What was 2024 revenue?' or break into smaller questions"
        ```

        **Example - API Failure Degradation:**
        ```
        >>> request = AnalyticalQueryRequest(
        ...     query="Compare Q3 and Q4 EBITDA with variance drivers"
        ... )
        >>> response = await analytical_query_financial_documents(request)
        >>> print(response.answer)
        "Our AI service is temporarily unavailable. Here are the documents we found:
         - Q3_2024_Report.pdf
         - Q4_2024_Report.pdf"
        >>> print(response.confidence)
        "low"
        >>> print(response.workflow_metadata["fallback_tier"])
        "epic1_fallback"
        ```

        **Observability & Metrics:**

        All degradation events are logged with structured metadata:
        - Degradation tier (full, partial, epic1_fallback)
        - Error type (timeout, connection, api_failure, unexpected)
        - Agents invoked and agents failed
        - Execution time and query details

        Target metrics (Epic 5 production monitoring):
        - Tier 1 success rate: ≥95%
        - Tier 2 fallback rate: <5%
        - Tier 4 Epic 1 rate: <0.1%

        See docs/user-guide-graceful-degradation.md for end-user documentation.
    """
    logger.info(
        "Analytical query received",
        extra={
            "query": request.query,
            "top_k": request.top_k,
        },
    )

    # Validate query
    if not request.query or not request.query.strip():
        error_msg = "Query cannot be empty"
        logger.warning("Empty analytical query rejected", extra={"query": request.query})
        raise QueryError(error_msg)

    workflow_start_time = time.perf_counter()

    try:
        # Step 1: Classify query complexity (AC1)
        complexity = await classify_query_complexity(request.query)

        logger.info(
            "Query classified",
            extra={"query": request.query, "complexity": complexity},
        )

        # Story 3.6 AC3: Conditional routing - simple queries to Epic 2, analytical to Epic 3
        if complexity == QueryComplexity.SIMPLE:
            logger.info(
                "Routing simple query to Epic 2 basic retrieval",
                extra={"query": request.query, "complexity": complexity},
            )

            # Route to Epic 2 basic retrieval tool
            basic_request = QueryRequest(query=request.query, top_k=request.top_k)
            basic_response = await query_financial_documents.fn(basic_request)

            workflow_duration_ms = (time.perf_counter() - workflow_start_time) * 1000

            # Story 3.6 AC4: Build reasoning steps for transparency
            reasoning_steps = [
                "1. Classified query as simple (direct retrieval)",
                f"2. Retrieved {len(basic_response.results)} relevant documents via vector search",
                "3. Ranked results by similarity score",
            ]

            # Story 3.6 AC6: Extract source citations from results
            sources = [
                f"{r.source_document} (page {r.page_number})"
                if r.page_number is not None
                else r.source_document
                for r in basic_response.results
            ]

            logger.info(
                "Simple query complete (Epic 2 routing)",
                extra={
                    "query": request.query,
                    "results_count": len(basic_response.results),
                    "duration_ms": f"{workflow_duration_ms:.2f}",
                    "routing": "epic2_basic_retrieval",
                },
            )

            # Convert QueryResponse to AnalyticalQueryResponse format
            # Synthesize answer from top results
            answer_parts = ["Based on the retrieved documents:\n"]
            for i, result in enumerate(basic_response.results[:3], 1):
                # Truncate long results for summary
                text_preview = result.text[:200] + "..." if len(result.text) > 200 else result.text
                answer_parts.append(f"{i}. {text_preview}")

            return AnalyticalQueryResponse(
                answer="\n".join(answer_parts),
                complexity=complexity.value,
                workflow_metadata={
                    "task_count": 1,
                    "execution_time_ms": int(workflow_duration_ms),
                    "workflow_pattern": "simple_retrieval",
                    "fallback_tier": "epic2_routing",
                },
                confidence="high",
                limitations=[],
                reasoning_steps=reasoning_steps,
                sources=sources,
            )

        # Analytical queries continue with Epic 3 workflow orchestration
        # Step 2: Decompose query into workflow plan (AC2)
        plan = await decompose_query(request.query, complexity)

        logger.info(
            "Query decomposed",
            extra={
                "query": request.query,
                "task_count": len(plan.tasks),
                "pattern": plan.metadata.get("pattern", "unknown"),
            },
        )

        # Step 3: Execute workflow with specialized agents (AC3, AC4, AC5)
        executor = WorkflowExecutor()
        results = await executor.execute_workflow(plan)

        workflow_duration_ms = (time.perf_counter() - workflow_start_time) * 1000

        # Step 4: Extract final synthesis result
        synthesis_result = next(
            (r for r in reversed(results) if r.success and r.agent_type == "synthesis"),
            None,
        )

        if synthesis_result:
            # Full workflow succeeded
            answer = str(synthesis_result.result)
            fallback_tier = "full"
            confidence = "high"
            limitations: list[str] = []

            # Story 3.6 AC4: Build reasoning steps from workflow execution
            reasoning_steps = []
            pattern = plan.metadata.get("pattern", "unknown")
            reasoning_steps.append(f"1. Classified query as analytical ({pattern} pattern)")

            # Add retrieval steps
            retrieval_results = [r for r in results if r.agent_type == "retrieval" and r.success]
            for i, r in enumerate(retrieval_results, start=2):
                task_desc = next(
                    (t.instruction for t in plan.tasks if t.task_id == r.task_id), "retrieval task"
                )
                # Extract document count if available in result
                doc_count = len(r.result) if isinstance(r.result, list) else "relevant"
                reasoning_steps.append(f"{i}. Retrieved {doc_count} documents: {task_desc}")

            # Add analysis steps
            analysis_results = [r for r in results if r.agent_type == "analysis" and r.success]
            step_num = len(reasoning_steps) + 1
            for r in analysis_results:
                task_desc = next(
                    (t.instruction for t in plan.tasks if t.task_id == r.task_id), "analysis task"
                )
                reasoning_steps.append(f"{step_num}. Performed analysis: {task_desc}")
                step_num += 1

            # Add synthesis step
            task_count = len(results)
            reasoning_steps.append(
                f"{step_num}. Synthesized final answer from {task_count} workflow tasks"
            )

            # Story 3.6 AC6: Extract source citations from retrieval results
            sources = []
            for r in retrieval_results:
                if isinstance(r.result, list):
                    # Extract sources from retrieval results (SearchResult or QueryResult objects)
                    for doc in r.result:
                        if hasattr(doc, "document_id"):
                            # SearchResult from multi_index_search
                            has_page = hasattr(doc, "page_number") and doc.page_number is not None
                            page_ref = f" (page {doc.page_number})" if has_page else ""
                            source = f"{doc.document_id}{page_ref}"
                        elif hasattr(doc, "source_document"):
                            # QueryResult from query_financial_documents
                            has_page_num = doc.page_number is not None
                            page_ref = f" (page {doc.page_number})" if has_page_num else ""
                            source = f"{doc.source_document}{page_ref}"
                        else:
                            continue

                        if source not in sources:  # Deduplicate
                            sources.append(source)

            logger.info(
                "Analytical query complete",
                extra={
                    "query": request.query,
                    "task_count": len(results),
                    "success_count": sum(1 for r in results if r.success),
                    "duration_ms": f"{workflow_duration_ms:.2f}",
                    "fallback_tier": fallback_tier,
                    "sources_count": len(sources),
                },
            )

            return AnalyticalQueryResponse(
                answer=answer,
                complexity=complexity.value,
                workflow_metadata={
                    "task_count": len(results),
                    "execution_time_ms": int(workflow_duration_ms),
                    "workflow_pattern": plan.metadata.get("pattern", "unknown"),
                    "fallback_tier": fallback_tier,
                },
                confidence=confidence,
                limitations=limitations,
                reasoning_steps=reasoning_steps,
                sources=sources,
            )

        else:
            # No synthesis result - partial failure
            # AC8: Graceful degradation
            raise RuntimeError("No synthesis result available from workflow")

    except Exception as e:
        # AC8: Graceful degradation - handle workflow failure
        workflow_duration_ms = (time.perf_counter() - workflow_start_time) * 1000

        logger.warning(
            "Analytical workflow failed - initiating graceful degradation",
            extra={
                "query": request.query,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": f"{workflow_duration_ms:.2f}",
            },
        )

        # Get partial results if available
        partial_results = []
        if "results" in locals():
            partial_results = results

        # Call fallback handler (AC8: Task 4.2, 4.3, 4.4)
        fallback_response: FallbackResponse = await handle_workflow_failure(
            query=request.query,
            complexity=complexity if "complexity" in locals() else QueryComplexity.ANALYTICAL,
            partial_results=partial_results,
            error=e,
            total_time_ms=int(workflow_duration_ms),
        )

        logger.info(
            "Graceful degradation complete",
            extra={
                "query": request.query,
                "fallback_tier": fallback_response.tier.value,
                "confidence": fallback_response.confidence,
                "duration_ms": f"{workflow_duration_ms:.2f}",
            },
        )

        # Story 3.6 AC4: Build reasoning steps for fallback
        fallback_reasoning = [
            "1. Classified query as analytical",
            f"2. Attempted multi-step workflow ({len(partial_results)} tasks started)",
            f"3. Workflow failed: {str(e)[:100]}...",
            f"4. Gracefully degraded to {fallback_response.tier.value} tier",
        ]

        # Story 3.6 AC6: Extract sources from fallback response if available
        fallback_sources = []
        if hasattr(fallback_response, "sources"):
            fallback_sources = fallback_response.sources
        elif hasattr(fallback_response, "results"):
            # Extract from Epic 1 fallback results
            for result in fallback_response.results[:5]:
                if hasattr(result, "source_document"):
                    has_page = result.page_number is not None
                    page_ref = f" (page {result.page_number})" if has_page else ""
                    fallback_sources.append(f"{result.source_document}{page_ref}")

        # Return fallback response
        return AnalyticalQueryResponse(
            answer=fallback_response.answer,
            complexity=complexity.value if "complexity" in locals() else "analytical",
            workflow_metadata={
                "task_count": len(partial_results),
                "execution_time_ms": fallback_response.execution_time_ms,
                "workflow_pattern": "fallback",
                "fallback_tier": fallback_response.tier.value,
            },
            confidence=fallback_response.confidence,
            limitations=fallback_response.limitations,
            reasoning_steps=fallback_reasoning,
            sources=fallback_sources,
        )


# Story 5.0.1: No hardcoded metric list needed - SQL extraction supports any metric in database
# Metrics are validated dynamically by checking if data exists in financial_tables


def parse_forecast_query(query: str) -> tuple[str | None, int | None]:
    """Parse natural language query to extract metric and period.

    Story 4.4 AC4: Natural language query parsing for forecast queries.
    Uses regex pattern matching first, with LLM fallback for complex queries.

    Args:
        query: Natural language query (e.g., "What's the revenue forecast for next quarter?")

    Returns:
        Tuple of (metric, periods) where either may be None if not found
    """
    import re

    query_lower = query.lower()

    # Metric patterns (primary extraction)
    metric_patterns = {
        r"\b(?:revenue|sales|income)\b": "revenue",
        r"\bcash\s*flow\b": "cash_flow",
        r"\b(?:expenses?|costs?|spending)\b": "expenses",
    }

    metric = None
    for pattern, metric_name in metric_patterns.items():
        if re.search(pattern, query_lower):
            metric = metric_name
            break

    # Period patterns (extract number of quarters)
    periods = None

    # "next quarter" = 1 quarter
    if re.search(r"next\s+quarter\b", query_lower):
        periods = 1

    # "next N quarters" = N quarters
    next_n_match = re.search(r"next\s+(\d+)\s+quarters?", query_lower)
    if next_n_match:
        periods = min(int(next_n_match.group(1)), 8)  # Cap at 8

    # "for N quarters" = N quarters
    for_n_match = re.search(r"for\s+(?:the\s+)?(?:next\s+)?(\d+)\s+quarters?", query_lower)
    if for_n_match:
        periods = min(int(for_n_match.group(1)), 8)

    # Specific quarter reference (Q1-Q4 YYYY) - calculate periods to that quarter
    q_match = re.search(r"q([1-4])\s*(\d{4})", query_lower)
    if q_match:
        from datetime import datetime

        target_quarter = int(q_match.group(1))
        target_year = int(q_match.group(2))

        now = datetime.now()
        current_quarter = (now.month - 1) // 3 + 1
        current_year = now.year

        # Calculate quarters ahead
        target_q_ordinal = target_year * 4 + target_quarter
        current_q_ordinal = current_year * 4 + current_quarter
        periods = max(1, target_q_ordinal - current_q_ordinal)
        periods = min(periods, 8)  # Cap at 8

    return metric, periods


@mcp.tool()
async def get_financial_forecast(
    request: ForecastQueryRequest,
) -> ForecastQueryResponse:
    """Query financial forecasts for key metrics.

    Story 4.4 AC1-AC5: MCP tool for conversational forecast queries using
    Prophet statistical forecasting combined with LLM reasoning.

    **Supported Metrics:** Any metric in the financial_tables database (e.g., revenue, turnover,
    cash_flow, ebitda, expenses, capex). The system automatically searches the database via SQL
    and falls back to hybrid search if needed.

    **Input Modes:**

    1. **Structured Query (Programmatic):**
       Provide explicit `metric` and `periods_ahead` parameters.

       Example:
           >>> request = ForecastQueryRequest(metric="revenue", periods_ahead=4)
           >>> response = await get_financial_forecast(request)

    2. **Natural Language Query (Conversational):**
       Provide a `query` parameter and let the system extract parameters.

       Example:
           >>> request = ForecastQueryRequest(query="What's the revenue forecast for next quarter?")
           >>> response = await get_financial_forecast(request)

    **How It Works:**

    1. Parse query to extract metric and time period (regex + LLM fallback)
    2. Extract historical time-series data (Story 5.0.1: SQL-first with fallback):
       a. Try SQL extraction from PostgreSQL financial_tables (primary)
       b. Fall back to hybrid search + LLM extraction if SQL fails
    3. Generate forecast using Prophet + LLM hybrid approach
    4. Return predictions with confidence intervals and explanation

    **Minimum Data Requirement:**
    - Requires 8+ historical data points (2 years quarterly) for reliable forecasts
    - Returns clear error message if insufficient data

    Args:
        request: Forecast query parameters containing:
          - metric: Financial metric to forecast (any metric in database: revenue, turnover, ebitda, cash_flow, expenses, capex, etc.)
          - periods_ahead: Number of quarters to forecast (1-8, default: 4)
          - query: Optional natural language query (parsed for metric/period)

    Returns:
        ForecastQueryResponse containing:
          - metric_name: Name of forecasted metric
          - forecast: List of ForecastPoint with value/lower/upper confidence intervals
          - basis: Description of historical data used (e.g., "Prophet model trained on 12 quarters")
          - confidence_reasoning: LLM explanation of forecast confidence
          - methodology: "Prophet + Mistral Large hybrid forecasting"
          - accuracy_estimate: "±15% (NFR10 target)"
          - source_documents: Documents used for time-series extraction
          - periods_ahead: Number of periods forecasted

    Raises:
        QueryError: If metric not supported, no metric specified, or insufficient data

    Example - Structured Query:
        >>> request = ForecastQueryRequest(metric="revenue", periods_ahead=4)
        >>> response = await get_financial_forecast(request)
        >>> print(response.forecast[0])
        ForecastPoint(date=2026-03-31, value=15.2M, lower=14.1M, upper=16.3M, label="Q1 2026")

    Example - Natural Language Query:
        >>> request = ForecastQueryRequest(query="What's the revenue forecast for next quarter?")
        >>> response = await get_financial_forecast(request)
        >>> print(response.basis)
        "Prophet model trained on 12 quarters of historical revenue data from 3 documents"

    Example - Cash Flow Forecast:
        >>> request = ForecastQueryRequest(query="Forecast cash flow for the next 4 quarters")
        >>> response = await get_financial_forecast(request)
        >>> print(f"{response.metric_name}: {len(response.forecast)} quarters forecasted")
        "cash_flow: 4 quarters forecasted"
    """
    logger.info(
        "Forecast query received",
        extra={
            "metric": request.metric,
            "periods_ahead": request.periods_ahead,
            "query": request.query,
        },
    )

    # Step 1: Determine metric and periods from request
    metric = request.metric
    periods_ahead = request.periods_ahead

    # If natural language query provided, parse it (AC4)
    if request.query and not metric:
        parsed_metric, parsed_periods = parse_forecast_query(request.query)
        if parsed_metric:
            metric = parsed_metric
        if parsed_periods:
            periods_ahead = parsed_periods

        logger.info(
            "Parsed natural language query",
            extra={
                "original_query": request.query,
                "parsed_metric": metric,
                "parsed_periods": periods_ahead,
            },
        )

    # Validate metric is provided
    if not metric:
        error_msg = (
            "Could not determine metric to forecast. Please specify a financial metric "
            "(e.g., revenue, turnover, ebitda, cash_flow, expenses, capex) or rephrase your query."
        )
        logger.warning("Forecast query failed - no metric", extra={"query": request.query})
        raise QueryError(error_msg)

    # Story 5.0.1: No validation needed - SQL extraction handles any metric in database
    # The extract_timeseries_from_sql function will raise ExtractionError if metric not found
    metric = metric.lower()

    try:
        # Step 2: Extract historical time-series data (AC3)
        # Story 5.0.1 AC3: SQL-first extraction with fallback to hybrid search
        logger.info(
            "Extracting time-series data",
            extra={"metric": metric},
        )

        # Try SQL extraction first (primary method)
        try:
            logger.info(
                "Attempting SQL-based extraction",
                extra={"metric": metric, "method": "sql"},
            )
            historical_data = await extract_timeseries_from_sql(metric=metric, min_points=8)

            logger.info(
                "SQL extraction successful",
                extra={
                    "metric": metric,
                    "data_points": len(historical_data.points),
                    "method": "sql",
                },
            )

        except ExtractionError as e:
            # Fallback to hybrid search + LLM extraction
            logger.warning(
                "SQL extraction failed, falling back to hybrid search",
                extra={
                    "metric": metric,
                    "reason": str(e),
                    "fallback_method": "hybrid_search",
                },
            )

            historical_data = await extract_timeseries(docs=[], metric=metric)

            logger.info(
                "Hybrid search extraction successful",
                extra={
                    "metric": metric,
                    "data_points": len(historical_data.points),
                    "source_docs": len(historical_data.source_documents),
                    "method": "hybrid_search_fallback",
                },
            )

        logger.info(
            "Time-series extraction complete",
            extra={
                "metric": metric,
                "data_points": len(historical_data.points),
                "source_docs": len(historical_data.source_documents),
            },
        )

        # Step 3: Generate forecast using Prophet + LLM (AC1, AC2)
        forecast_result = await generate_forecast(
            metric=metric,
            historical_data=historical_data,
            periods_ahead=periods_ahead,
        )

        logger.info(
            "Forecast generated successfully",
            extra={
                "metric": metric,
                "periods": periods_ahead,
                "forecast_points": len(forecast_result.forecast),
            },
        )

        # Step 4: Build MCP response (AC2, AC3)
        # Update basis to include document count
        enhanced_basis = (
            f"Prophet model trained on {len(historical_data.points)} quarters of historical "
            f"{metric} data from {len(historical_data.source_documents)} documents"
        )
        forecast_result.basis = enhanced_basis

        response = ForecastQueryResponse.from_forecast_result(
            result=forecast_result,
            source_documents=historical_data.source_documents,
        )

        logger.info(
            "Forecast query complete",
            extra={
                "metric": metric,
                "periods": periods_ahead,
                "confidence_reasoning_length": len(response.confidence_reasoning),
            },
        )

        return response

    except InsufficientDataError as e:
        # AC4: Handle insufficient data gracefully with user-friendly message
        error_msg = (
            f"Insufficient historical data for {metric} forecast. "
            f"At least 8 data points (2 years quarterly) are required for reliable predictions. "
            f"Please ingest more financial documents containing {metric} data."
        )
        logger.warning(
            "Forecast query failed - insufficient data",
            extra={"metric": metric, "error": str(e)},
        )
        raise QueryError(error_msg) from e

    except ExtractionError as e:
        # Handle time-series extraction failures
        error_msg = (
            f"Could not extract {metric} time-series data from documents. "
            f"Ensure financial documents containing {metric} data have been ingested. "
            f"Details: {str(e)}"
        )
        logger.warning(
            "Forecast query failed - extraction error",
            extra={"metric": metric, "error": str(e)},
        )
        raise QueryError(error_msg) from e

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            "Forecast query failed - unexpected error",
            extra={
                "metric": metric,
                "periods": periods_ahead,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise QueryError(f"Forecast generation failed: {e}") from e


# Story 4.9: Supported categories for insights queries
SUPPORTED_INSIGHT_CATEGORIES = {"RISK", "OPPORTUNITY", "ANOMALY", "TREND", "STRATEGIC_PRIORITY"}

# Story 4.9: Time period mappings
TIME_PERIOD_MAPPINGS = {
    "last_quarter": "Previous Quarter",
    "current_quarter": "Current Quarter",
    "last_year": "Last 12 Months",
    "ytd": "Year-to-Date",
}


def parse_insights_query(query: str) -> tuple[InsightCategory | None, str | None]:
    """Parse natural language query to extract category and time period.

    Story 4.9 AC1: Natural language query parsing for insight queries.
    Uses regex pattern matching for category and time period extraction.

    Args:
        query: Natural language query (e.g., "What risks should I know about?")

    Returns:
        Tuple of (category, time_period) where either may be None if not found

    Example:
        >>> parse_insights_query("What risks should I know about?")
        (InsightCategory.RISK, None)
        >>> parse_insights_query("Any opportunities this quarter?")
        (InsightCategory.OPPORTUNITY, "current_quarter")
    """
    import re

    query_lower = query.lower()

    # Category patterns
    category = None
    if re.search(r"\b(?:risk|risks|dangers?|threats?|warnings?)\b", query_lower):
        category = InsightCategory.RISK
    elif re.search(r"\b(?:opportunit(?:y|ies)|growth|potential|upside)\b", query_lower):
        category = InsightCategory.OPPORTUNITY
    elif re.search(r"\b(?:anomal(?:y|ies)|outliers?|unusual|unexpected)\b", query_lower):
        category = InsightCategory.ANOMALY
    elif re.search(r"\b(?:trends?|trending|patterns?|direction)\b", query_lower):
        category = InsightCategory.TREND
    elif re.search(r"\b(?:strategic|priorit(?:y|ies|ize)|focus|important)\b", query_lower):
        category = InsightCategory.STRATEGIC_PRIORITY

    # Time period patterns
    time_period = None
    if re.search(r"\b(?:last|previous)\s*quarter\b", query_lower):
        time_period = "last_quarter"
    elif re.search(r"\b(?:this|current)\s*quarter\b", query_lower):
        time_period = "current_quarter"
    elif re.search(r"\b(?:last|past)\s*(?:year|12\s*months)\b", query_lower):
        time_period = "last_year"
    elif re.search(r"\b(?:year\s*to\s*date|ytd)\b", query_lower):
        time_period = "ytd"

    return category, time_period


def format_insights_for_display(
    insights: list[Insight],
    recommendations: list[Recommendation],
) -> str:
    """Generate LLM-friendly formatted summary with priority indicators.

    Story 4.9 AC4: Format insights for conversational display.

    Args:
        insights: List of Insight objects sorted by priority
        recommendations: List of Recommendation objects sorted by impact

    Returns:
        Formatted string suitable for LLM response synthesis

    Example:
        >>> summary = format_insights_for_display(insights, recommendations)
        >>> print(summary)
        "🔴 Critical: Marketing spend increased 30%..."
    """
    lines = []

    # Executive summary
    if insights:
        critical_count = sum(1 for i in insights if i.priority == 1)
        risk_count = sum(1 for i in insights if i.category == InsightCategory.RISK)
        opp_count = sum(1 for i in insights if i.category == InsightCategory.OPPORTUNITY)

        summary_parts = []
        if critical_count > 0:
            summary_parts.append(f"{critical_count} critical finding(s)")
        if risk_count > 0:
            summary_parts.append(f"{risk_count} risk(s)")
        if opp_count > 0:
            summary_parts.append(f"{opp_count} opportunity(ies)")

        if summary_parts:
            lines.append(f"**Executive Summary:** {', '.join(summary_parts)} identified.\n")
    else:
        lines.append("**Executive Summary:** No significant insights detected.\n")

    # Top insights with priority indicators
    if insights:
        lines.append("**Key Insights:**\n")
        for i, insight in enumerate(insights[:5], 1):
            # Priority indicator
            if insight.priority == 1:
                indicator = "🔴 Critical"
            elif insight.priority == 2:
                indicator = "🟠 High"
            elif insight.priority == 3:
                indicator = "🟡 Medium"
            else:
                indicator = "🟢 Low"

            lines.append(f"{i}. [{indicator}] {insight.summary}")
            if insight.rationale:
                lines.append(f"   Rationale: {insight.rationale[:150]}...")
            lines.append("")

    # Recommended actions
    if recommendations:
        lines.append("**Recommended Actions:**\n")
        for i, rec in enumerate(recommendations[:3], 1):
            urgency_icon = "⚡" if rec.urgency == "high" else "📋"
            lines.append(f"{i}. {urgency_icon} {rec.title} (Impact: {rec.impact_score}/10)")
            if rec.action_steps:
                lines.append(f"   Next step: {rec.action_steps[0]}")
            lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def get_financial_insights(
    request: InsightsQueryRequest,
) -> InsightsQueryResponse:
    """Request proactive financial insights via MCP.

    Story 4.9 AC1-AC5: MCP tool for conversational insight queries combining
    anomaly detection, trend analysis, and strategic recommendations.

    **Supported Categories:** RISK, OPPORTUNITY, ANOMALY, TREND, STRATEGIC_PRIORITY

    **Input Modes:**

    1. **Structured Query (Programmatic):**
       Provide explicit `category` and `time_period` parameters.

       Example:
           >>> request = InsightsQueryRequest(category="RISK", limit=3)
           >>> response = await get_financial_insights(request)

    2. **Natural Language Query (Conversational):**
       Provide a `query` parameter and let the system extract filters.

       Example:
           >>> request = InsightsQueryRequest(query="What risks should I know about?")
           >>> response = await get_financial_insights(request)

    **How It Works:**

    1. Parse query to extract category and time period (if using natural language)
    2. Retrieve anomaly detection results (Story 4.5)
    3. Retrieve trend analysis results (Story 4.6)
    4. Generate insights from anomalies and trends (Story 4.7)
    5. Generate strategic recommendations (Story 4.8)
    6. Filter and rank results by priority/impact
    7. Format for conversational display

    Args:
        request: Insights query parameters containing:
          - category: Optional filter by insight category
          - time_period: Optional time period filter (last_quarter, ytd, etc.)
          - limit: Max insights to return (default 5, max 20)
          - include_recommendations: Include strategic recommendations (default True)
          - query: Optional natural language query

    Returns:
        InsightsQueryResponse containing:
          - insights: Ranked list of Insight objects
          - recommendations: List of Recommendation objects (if requested)
          - formatted_summary: LLM-friendly summary text
          - source_documents: Documents analyzed

    Raises:
        QueryError: If no documents available or insight generation fails

    Example - Structured Query:
        >>> request = InsightsQueryRequest(category="RISK", limit=5)
        >>> response = await get_financial_insights(request)
        >>> print(f"Found {len(response.insights)} risk insights")

    Example - Natural Language Query:
        >>> request = InsightsQueryRequest(query="What should I focus on?")
        >>> response = await get_financial_insights(request)
        >>> print(response.formatted_summary)
        "🔴 Critical: Marketing spend increased 30% with no revenue increase..."
    """
    start_time = time.perf_counter()

    logger.info(
        "Insights query received",
        extra={
            "category_filter": request.category,
            "time_period": request.time_period,
            "limit": request.limit,
            "include_recommendations": request.include_recommendations,
            "query": request.query,
        },
    )

    # Step 1: Parse natural language query if provided
    category_filter = request.category
    time_period = request.time_period

    if request.query and not category_filter:
        parsed_category, parsed_period = parse_insights_query(request.query)
        if parsed_category:
            category_filter = parsed_category.value.upper()
        if parsed_period and not time_period:
            time_period = parsed_period

        logger.info(
            "Parsed natural language query",
            extra={
                "original_query": request.query,
                "parsed_category": category_filter,
                "parsed_period": time_period,
            },
        )

    try:
        # Step 2: Import required modules
        from raglite.forecasting.timeseries_extract import extract_timeseries
        from raglite.insights.anomalies import detect_anomalies
        from raglite.insights.proactive import filter_insights, generate_insights
        from raglite.insights.recommendations import (
            generate_recommendations,
        )
        from raglite.insights.trends import analyze_trends

        # Step 3: Extract time-series data for analysis
        # Get available metrics from ingested documents
        source_documents: list[str] = []
        all_anomalies = []
        all_trends = []

        for metric in ["revenue", "expenses", "cash_flow"]:
            try:
                ts_data = await extract_timeseries(docs=[], metric=metric)
                if ts_data.points:
                    source_documents.extend(ts_data.source_documents)

                    # Detect anomalies
                    anomaly_result = await detect_anomalies(metric, ts_data)
                    all_anomalies.extend(anomaly_result.anomalies)

            except Exception as e:
                logger.debug(
                    f"Skipping metric {metric} for anomaly detection",
                    extra={"error": str(e)},
                )

        # Analyze trends across all metrics
        try:
            # Extract all available time series for trend analysis
            ts_list = []
            for metric in ["revenue", "expenses", "cash_flow"]:
                try:
                    ts_data = await extract_timeseries(docs=[], metric=metric)
                    if ts_data.points:
                        ts_list.append(ts_data)
                except Exception:  # nosec B112 - intentional skip of failed metrics
                    continue

            if ts_list:
                # Convert list to dict format expected by analyze_trends
                ts_dict = {ts.metric_name: ts for ts in ts_list}
                metrics_list = list(ts_dict.keys())
                trend_result = await analyze_trends(metrics_list, ts_dict)
                all_trends.extend(trend_result.trends)

        except Exception as e:
            logger.debug(
                "Trend analysis skipped",
                extra={"error": str(e)},
            )

        # Deduplicate source documents
        source_documents = list(set(source_documents))

        # Step 4: Generate insights from anomalies and trends
        if not all_anomalies and not all_trends:
            # No data to analyze - return empty response with helpful message
            logger.info(
                "No insights generated - insufficient data",
                extra={"anomalies_count": 0, "trends_count": 0},
            )

            generation_time_ms = (time.perf_counter() - start_time) * 1000

            return InsightsQueryResponse(
                insights=[],
                recommendations=[],
                total_insights=0,
                total_recommendations=0,
                formatted_summary=(
                    "**No insights available.** Please ingest financial documents "
                    "containing time-series data (revenue, expenses, cash flow) to "
                    "enable proactive insight generation."
                ),
                time_period_analyzed=TIME_PERIOD_MAPPINGS.get(
                    time_period or "all_time", "All available data"
                ),
                generation_time_ms=generation_time_ms,
                source_documents=source_documents,
            )

        # Generate insights using Story 4.7 infrastructure
        insight_result = await generate_insights(
            anomalies=all_anomalies,
            trends=all_trends,
            forecasts=[],  # Forecasts optional for insight generation
            auto_synthesize=True,
        )

        # Step 5: Apply category filter if specified
        filtered_insights = insight_result.insights
        if category_filter:
            try:
                category_enum = InsightCategory(category_filter.lower())
                filtered_insights = filter_insights(
                    filtered_insights,
                    category=category_enum,
                )
            except ValueError:
                logger.warning(
                    f"Invalid category filter: {category_filter}",
                    extra={"valid_categories": list(SUPPORTED_INSIGHT_CATEGORIES)},
                )

        # Apply limit (AC3: default 5)
        filtered_insights = filtered_insights[: request.limit]

        # Step 6: Generate recommendations if requested
        recommendations: list[Recommendation] = []
        total_recommendations = 0

        if request.include_recommendations and filtered_insights:
            try:
                rec_result = await generate_recommendations(
                    insights=filtered_insights,
                    auto_synthesize=True,
                )
                recommendations = rec_result.recommendations[:5]  # Top 5 recommendations
                total_recommendations = rec_result.total_generated
            except Exception as e:
                logger.warning(
                    "Recommendation generation failed",
                    extra={"error": str(e)},
                )

        # Step 7: Format for display (AC4)
        formatted_summary = format_insights_for_display(filtered_insights, recommendations)

        generation_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Insights query complete",
            extra={
                "category_filter": category_filter,
                "time_period": time_period,
                "insights_count": len(filtered_insights),
                "recommendations_count": len(recommendations),
                "total_insights": insight_result.total_generated,
                "total_recommendations": total_recommendations,
                "generation_time_ms": f"{generation_time_ms:.2f}",
                "source_documents_count": len(source_documents),
            },
        )

        return InsightsQueryResponse(
            insights=filtered_insights,
            recommendations=recommendations,
            total_insights=insight_result.total_generated,
            total_recommendations=total_recommendations,
            formatted_summary=formatted_summary,
            time_period_analyzed=TIME_PERIOD_MAPPINGS.get(
                time_period or "all_time", "All available data"
            ),
            generation_time_ms=generation_time_ms,
            source_documents=source_documents,
        )

    except Exception as e:
        generation_time_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Insights query failed",
            extra={
                "category_filter": category_filter,
                "time_period": time_period,
                "error": str(e),
                "error_type": type(e).__name__,
                "generation_time_ms": f"{generation_time_ms:.2f}",
            },
            exc_info=True,
        )
        raise QueryError(f"Insight generation failed: {e}") from e


# Module-level execution for direct startup
if __name__ == "__main__":
    logger.info(
        "Starting RAGLite MCP Server",
        extra={
            "qdrant_host": settings.qdrant_host,
            "qdrant_port": settings.qdrant_port,
            "collection": settings.qdrant_collection_name,
        },
    )
    mcp.run(show_banner=False)
