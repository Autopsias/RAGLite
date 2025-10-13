"""Source attribution and citation generation for retrieved chunks.

Adds formatted citations to query results for NFR7 (95%+ attribution accuracy).
"""

from raglite.shared.logging import get_logger
from raglite.shared.models import QueryResult

logger = get_logger(__name__)


class CitationError(Exception):
    """Exception raised when citation generation fails."""

    pass


async def generate_citations(results: list[QueryResult]) -> list[QueryResult]:
    """Add formatted citations to query results.

    Args:
        results: List of QueryResult objects from search

    Returns:
        Same list with citation strings appended to text

    Raises:
        CitationError: If critical metadata missing (source_document)

    Citation Format:
        "(Source: document.pdf, page 12, chunk 5)"

    Strategy:
        - Append citation to chunk text (preserves original content)
        - Validate required metadata (page_number, source_document)
        - Log warnings for missing page numbers (graceful degradation)
        - Raise error if source_document missing (critical field)

    Example:
        >>> results = await search_documents("What is revenue?", top_k=3)
        >>> cited_results = await generate_citations(results)
        >>> cited_results[0].text
        'Revenue increased by 15%...\n\n(Source: Q3_Report.pdf, page 12, chunk 5)'
    """
    if not results:
        logger.info("No results to cite")
        return results

    logger.info("Generating citations", extra={"chunk_count": len(results)})
    warnings_count = 0

    for result in results:
        # Validate critical metadata
        if not result.source_document or result.source_document.strip() == "":
            raise CitationError(f"Missing source_document for chunk {result.chunk_index}")

        if result.page_number is None:
            logger.warning(
                "Missing page_number for chunk",
                extra={
                    "source_document": result.source_document,
                    "chunk_index": result.chunk_index,
                },
            )
            warnings_count += 1

        # Format citation
        citation = (
            f"(Source: {result.source_document}, "
            f"page {result.page_number if result.page_number is not None else 'N/A'}, "
            f"chunk {result.chunk_index})"
        )

        # Append citation to chunk text
        result.text = f"{result.text}\n\n{citation}"

        logger.debug(
            "Citation added",
            extra={
                "doc": result.source_document,
                "page": result.page_number,
                "chunk": result.chunk_index,
            },
        )

    logger.info(
        "Citations complete",
        extra={"citations_generated": len(results), "warnings_count": warnings_count},
    )

    return results
