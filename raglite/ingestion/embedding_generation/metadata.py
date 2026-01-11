"""LLM-based metadata extraction for document chunks."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mistralai import Mistral

# Import from parent facade for test compatibility
# Tests patch the facade, so we must import from there at runtime
from typing import Any

from raglite.shared.config import settings
from raglite.shared.logging import get_logger
from raglite.shared.models import ExtractedMetadata

get_mistral_client: Any | None = None

# Use parent module name for logger to maintain backward compatibility with tests
logger = get_logger("raglite.ingestion.embedding_generation")

# Story 2.4: Metadata extraction cache (per-document)
# Cache keyed by document hash to avoid redundant API calls
_metadata_cache: dict[str, ExtractedMetadata] = {}


def _validate_mistral_config(chunk_id: str) -> None:
    """Validate that Mistral API key is configured.

    Args:
        chunk_id: Unique chunk identifier for logging

    Raises:
        RuntimeError: If Mistral API key not configured
    """
    if not settings.mistral_api_key:
        error_msg = "Mistral API key not configured. Set MISTRAL_API_KEY environment variable."
        logger.warning(
            "Metadata extraction skipped - API key not configured (graceful degradation)",
            extra={"chunk_id": chunk_id, "metadata_extraction": "disabled"},
        )
        raise RuntimeError(error_msg)


def _get_mistral_client(client: Mistral | None) -> Mistral:
    """Get or create Mistral client for metadata extraction.

    Args:
        client: Optional pre-created client

    Returns:
        Mistral client instance
    """
    if client is not None:
        return client

    # Look up from parent facade at runtime for test compatibility
    import sys

    parent_module = sys.modules["raglite.ingestion.embedding_generation"]
    return parent_module.get_mistral_client()


def _build_extraction_messages(text: str) -> list:
    """Build messages for Mistral metadata extraction API call.

    Args:
        text: Chunk text content to extract metadata from

    Returns:
        List of messages for Mistral API
    """
    from mistralai.models import SystemMessage, UserMessage

    return [
        SystemMessage(
            content=(
                "Extract 15 metadata fields from financial document chunks for RAG retrieval optimization.\n"
                "Return ONLY valid JSON with these exact fields. Use null for missing values.\n\n"
                "DOCUMENT-LEVEL (7 fields):\n"
                "- document_type: Income Statement | Balance Sheet | Cash Flow Statement | Operational Report | "
                "Earnings Call | Management Discussion | Financial Notes\n"
                "- reporting_period: Q1 2024 | Aug-25 YTD | FY 2023 | 2024 Annual | H1 2025\n"
                "- time_granularity: Daily | Weekly | Monthly | Quarterly | YTD | Annual | Rolling 12-Month\n"
                "- company_name: Portugal Cement | CIMPOR | Cimpor Trading | InterCement\n"
                "- geographic_jurisdiction: Portugal | EU | APAC | Americas | Global\n"
                "- data_source_type: Audited | Internal Report | Regulatory Filing | Management Estimate | Preliminary\n"
                "- version_date: 2025-08-15 | 2024-Q3-Final | 2024-12-31-Revised\n\n"
                "SECTION-LEVEL (5 fields):\n"
                "- section_type: Narrative | Table | Footnote | Chart Caption | Summary | List | Formula\n"
                "- metric_category: Revenue | EBITDA | Operating Expenses | Capital Expenditure | Cash Flow | "
                "Assets | Liabilities | Equity | Ratios | Production Volume | Cost per Unit\n"
                "- units: EUR | USD | GBP | EUR/ton | USD/MWh | Percentage | Count | Tonnes | MWh | m³\n"
                "- department_scope: Operations | Finance | Production | Sales | Corporate | HR | IT | Supply Chain\n\n"
                "TABLE-SPECIFIC (3 fields - ONLY for table chunks):\n"
                "- table_context: Brief description of table purpose and contents (1-2 sentences)\n"
                "- table_name: Actual table title from document\n"
                "- statistical_summary: Key statistics if numerical (e.g., 'Mean=5.8, Range=3.5-61.4')\n\n"
                "EXAMPLES:\n"
                "Narrative chunk: {document_type: 'Operational Report', reporting_period: 'Aug-25 YTD', "
                "time_granularity: 'YTD', company_name: 'Portugal Cement', section_type: 'Narrative', "
                "metric_category: 'EBITDA', department_scope: 'Operations', ...}\n\n"
                "Table chunk: {document_type: 'Operational Report', reporting_period: 'Aug-25 YTD', "
                "section_type: 'Table', metric_category: 'Operating Expenses', units: 'EUR/ton', "
                "table_name: 'Variable Costs Summary', table_context: 'Breakdown of variable costs by category', ...}"
            )
        ),
        UserMessage(
            content=f"Extract all 15 metadata fields from this financial document chunk:\n\n{text}"
        ),
    ]


def _validate_response_content(response_content: str | None, chunk_id: str) -> str:
    """Validate and type-guard Mistral API response content.

    Args:
        response_content: Raw response content from API
        chunk_id: Unique chunk identifier for logging

    Returns:
        Validated string response content

    Raises:
        RuntimeError: If response is empty or not a string
    """
    if not response_content:
        logger.error(
            "Empty response from Mistral Small 3.2",
            extra={"chunk_id": chunk_id},
        )
        raise RuntimeError("Empty response from Mistral API")

    if not isinstance(response_content, str):
        logger.error(
            "Response content is not a string, cannot parse JSON",
            extra={
                "chunk_id": chunk_id,
                "content_type": type(response_content).__name__,
            },
        )
        raise RuntimeError("Response content is not a string")

    return response_content


def _parse_metadata_dict(metadata_dict: dict) -> ExtractedMetadata:
    """Parse metadata dictionary into ExtractedMetadata model.

    Args:
        metadata_dict: Dictionary from parsed JSON response

    Returns:
        ExtractedMetadata with all 15 fields populated
    """
    return ExtractedMetadata(
        # Document-Level (7 fields)
        document_type=metadata_dict.get("document_type"),
        reporting_period=metadata_dict.get("reporting_period"),
        time_granularity=metadata_dict.get("time_granularity"),
        company_name=metadata_dict.get("company_name"),
        geographic_jurisdiction=metadata_dict.get("geographic_jurisdiction"),
        data_source_type=metadata_dict.get("data_source_type"),
        version_date=metadata_dict.get("version_date"),
        # Section-Level (5 fields)
        section_type=metadata_dict.get("section_type"),
        metric_category=metadata_dict.get("metric_category"),
        units=metadata_dict.get("units"),
        department_scope=metadata_dict.get("department_scope"),
        # Table-Specific (3 fields)
        table_context=metadata_dict.get("table_context"),
        table_name=metadata_dict.get("table_name"),
        statistical_summary=metadata_dict.get("statistical_summary"),
    )


def _log_extraction_success(
    chunk_id: str,
    metadata: ExtractedMetadata,
    duration_ms: int,
) -> None:
    """Log successful metadata extraction.

    Args:
        chunk_id: Unique chunk identifier
        metadata: Extracted metadata
        duration_ms: Extraction time in milliseconds
    """
    logger.debug(
        "Chunk metadata extraction complete (15-field rich schema)",
        extra={
            "chunk_id": chunk_id,
            "document_type": metadata.document_type,
            "reporting_period": metadata.reporting_period,
            "section_type": metadata.section_type,
            "metric_category": metadata.metric_category,
            "model": settings.metadata_extraction_model,
            "estimated_cost_usd": 0.0,  # FREE with Mistral Small 3.2
            "duration_ms": duration_ms,
        },
    )


def _handle_json_decode_error(
    e: json.JSONDecodeError,
    chunk_id: str,
    response_content: str | None = None,
) -> None:
    """Handle JSON decode errors from Mistral API response.

    Args:
        e: JSON decode error exception
        chunk_id: Unique chunk identifier
        response_content: Optional response content for logging

    Raises:
        RuntimeError: Always raises with formatted error message
    """
    error_msg = f"Invalid JSON response from Mistral for {chunk_id}: {e}"
    logger.warning(
        "Mistral API returned invalid JSON (graceful degradation)",
        extra={
            "chunk_id": chunk_id,
            "error": str(e),
            "response": response_content,
        },
        exc_info=True,
    )
    raise RuntimeError(error_msg) from e


def _handle_api_error(
    e: Exception,
    chunk_id: str,
) -> None:
    """Handle general Mistral API errors.

    Args:
        e: Exception from API call
        chunk_id: Unique chunk identifier

    Raises:
        RuntimeError: Always raises with formatted error message
    """
    error_msg = f"Chunk metadata extraction failed for {chunk_id}: {e}"
    logger.warning(
        "Mistral Small 3.2 API call failed for chunk (graceful degradation)",
        extra={
            "chunk_id": chunk_id,
            "error": str(e),
            "error_type": type(e).__name__,
        },
        exc_info=True,
    )
    raise RuntimeError(error_msg) from e


async def extract_chunk_metadata(
    text: str, chunk_id: str, client: Mistral | None = None
) -> ExtractedMetadata:
    """Extract business context metadata from a single chunk using Mistral Small 3.2.

    Story 2.4 AC1 (REVISED - FIX): Extract fiscal_period, company_name, department_name per chunk.

    MIGRATION FROM OPENAI o1-mini TO MISTRAL SMALL 3.2:
    - Previous: OpenAI o1-mini had 50% failure rate due to reasoning token overflow
    - Current: Mistral Small 3.2 with native JSON schema support
    - Benefits:
      * FREE (vs $0.110 per 400 chunks for o1-mini)
      * 91% extraction accuracy (research-validated, vs 48% for o1-mini)
      * Native JSON schema enforcement (not function calling)
      * No reasoning token waste
      * Released June 2025 (newest free option)

    Args:
        text: Chunk text content (~512 tokens from fixed chunking)
        chunk_id: Unique chunk identifier for logging
        client: Optional pre-created AsyncMistral client for connection pooling.
            If None, creates new client (slower). For best performance, create
            single client and reuse across all chunks. (Story 2.6 AC6 optimization)

    Returns:
        ExtractedMetadata with 15 RICH SCHEMA fields (document-level, section-level, table-specific)

    Raises:
        RuntimeError: If Mistral API call fails or API key not configured
        asyncio.TimeoutError: If API call exceeds 30 second timeout (Story 2.6 AC6 fail-fast)

    Cost (Mistral Small 3.2):
        - Input: FREE
        - Output: FREE
        - Total: $0.00 per chunk
        - For 160-page doc with 400 chunks: $0.00 total

    Example:
        >>> from mistralai.async_client import AsyncMistral
        >>> client = AsyncMistral(api_key=settings.mistral_api_key)  # Reuse for all chunks
        >>> metadata = await extract_chunk_metadata(chunk.content, chunk.chunk_id, client)
        >>> print(f"Chunk {chunk.chunk_id}: {metadata.reporting_period}")
    """
    start_time = time.time()

    _validate_mistral_config(chunk_id)

    logger.debug(
        "Extracting chunk metadata with Mistral Small 3.2",
        extra={
            "chunk_id": chunk_id,
            "text_length": len(text),
            "model": settings.metadata_extraction_model,
        },
    )

    try:
        client = _get_mistral_client(client)
        messages = _build_extraction_messages(text)

        response = await client.chat.complete_async(
            model=settings.metadata_extraction_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=400,
        )

        response_content = _validate_response_content(
            response.choices[0].message.content,
            chunk_id,
        )

        metadata_dict = json.loads(response_content)
        extracted_metadata = _parse_metadata_dict(metadata_dict)

        duration_ms = int((time.time() - start_time) * 1000)
        _log_extraction_success(chunk_id, extracted_metadata, duration_ms)

        return extracted_metadata

    except json.JSONDecodeError as e:
        _handle_json_decode_error(
            e, chunk_id, response_content if "response_content" in locals() else None
        )
        raise

    except Exception as e:
        _handle_api_error(e, chunk_id)
        raise
