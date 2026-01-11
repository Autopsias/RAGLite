"""Table extraction from financial documents.

Core extraction logic for processing Docling conversion results into structured data.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from docling.document_converter import ConversionResult, DocumentConverter
    from docling_core.types.doc import TableItem

from raglite.ingestion.adaptive_table_extraction import extract_table_data_adaptive
from raglite.shared.logging import get_logger

# Import parsing functions to expose as methods
from .parsing import (
    build_column_mapping,
    extract_caption,
    extract_year,
    get_row_period,
    parse_markdown_row,
    parse_table_structure,
    parse_value_unit,
)

logger = get_logger(__name__)


class TableExtractor:
    """Extract and parse financial tables into structured SQL format.

    Story 2.13 AC1: Table Extraction to SQL Database

    Parses Docling TableItem objects into structured rows with:
    - entity (company/division name from row headers)
    - metric (cost type/metric name from row labels)
    - period (time period from column headers)
    - fiscal_year (extracted from period)
    - value (numeric value from cells)
    - unit (measurement unit from cells)
    """

    def __init__(self, converter: DocumentConverter | None = None) -> None:
        """Initialize table extractor with optional Docling converter.

        Args:
            converter: Optional DocumentConverter instance. If None, creates a new one
                      with production settings (pypdfium backend, 8 threads, CPU device).
                      Passing a converter is useful for testing with mocked converters.

        IMPORTANT: Docling imports are lazy-loaded to prevent pytest collection hangs
        when Docling initializes PyTorch/CUDA. See commit 9bcc6b4.
        """
        if converter is not None:
            # Use provided converter (e.g., for testing with mocks)
            self.converter = converter
        else:
            # Create production converter with lazy imports
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
            from docling.datamodel.accelerator_options import AcceleratorOptions
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
            from docling.document_converter import DocumentConverter, PdfFormatOption

            # Configure Docling with pypdfium backend (Story 2.1)
            pipeline_options = PdfPipelineOptions()
            pipeline_options.accelerator_options = AcceleratorOptions(
                num_threads=8,  # Story 2.2: Page-level parallelism
                device="cpu",
            )
            pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options,
                        backend=PyPdfiumDocumentBackend,  # Story 2.1: pypdfium backend
                    )
                }
            )

    async def extract_tables(self, doc_path: str) -> list[dict[str, Any]]:
        """Extract and parse all tables from document.

        Args:
            doc_path: Path to financial document (PDF)

        Returns:
            List of table rows as dicts (ready for SQL insertion)

        Example:
            >>> extractor = TableExtractor()
            >>> rows = await extractor.extract_tables("2025-08-performance-review.pdf")
            >>> len(rows)
            428
            >>> rows[0]
            {
                'entity': 'Portugal Cement',
                'metric': 'Variable Costs',
                'period': 'Aug-25 YTD',
                'fiscal_year': 2025,
                'value': 23.2,
                'unit': 'EUR/ton',
                'page_number': 12,
                'table_index': 0,
                'table_caption': 'Financial Performance Summary',
                'row_index': 0,
                'column_name': 'Aug-25 YTD',
                'chunk_text': '| Entity | Metric | Aug-25 YTD | ... |'
            }
        """
        logger.info("Extracting tables from document", extra={"doc_path": doc_path})

        # Convert document with Docling
        result = self.converter.convert(doc_path)

        # Milestone 1: Use async table extraction with 10x speedup
        return await self.extract_tables_from_result(result, Path(doc_path).stem)

    async def extract_tables_from_result(
        self,
        result: ConversionResult,
        document_id: str,
        unit_cache: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract and parse tables from existing Docling ConversionResult with async unit inference.

        This method is optimized for use when the document has already been converted
        (e.g., in ingestion pipeline) to avoid double-conversion.

        Implements Milestone 1 async conversion for 10x speedup in table extraction
        (62 min → 6 min for 942 rows with unit inference).

        Story 5.0.6 AC3: Supports cross-document unit cache for 30% additional API reduction.

        Args:
            result: Docling ConversionResult from document conversion
            document_id: Document filename (without extension)
            unit_cache: Optional shared cache for cross-document unit inference (AC3).
                       If None, creates local cache per document. If provided, enables
                       reuse across documents in a batch.

        Returns:
            List of table rows as dicts (ready for SQL insertion)

        Performance:
            - Async unit inference with 10 concurrent API calls
            - Rate limiting via MISTRAL_SEMAPHORE
            - 5-second timeout per call
            - Connection pooling via shared Mistral client
            - Story 5.0.6 AC3: Cross-document cache reduces duplicate API calls by 30%
        """
        # Lazy import for isinstance check
        from docling_core.types.doc import TableItem

        all_rows: list[dict[str, Any]] = []
        table_index = 0

        # Iterate through all document items
        for item, _ in result.document.iterate_items():
            if isinstance(item, TableItem):
                # Get page number from table provenance
                page_number = item.prov[0].page_no if item.prov else 1

                # Extract using adaptive table extraction with async unit inference
                # Milestone 1: Concurrent processing for 10x speedup (62 min → 6 min)
                # Story 5.0.6 AC3: Pass unit_cache for cross-document reuse
                parsed_rows = await extract_table_data_adaptive(
                    table_item=item,
                    result=result,
                    table_index=table_index,
                    document_id=document_id,
                    page_number=page_number,
                    unit_cache=unit_cache,
                )
                all_rows.extend(parsed_rows)
                table_index += 1

        logger.info(
            "Table extraction complete",
            extra={
                "document_id": document_id,
                "table_count": table_index,
                "row_count": len(all_rows),
            },
        )

        return all_rows

    # Backward compatibility methods - delegate to parsing module functions
    # These methods maintain compatibility with existing tests that call extractor._method()

    def _parse_table_structure(
        self,
        table_item: TableItem,
        result: ConversionResult,
        table_index: int,
        document_id: str,
    ) -> list[dict[str, Any]]:
        """Parse table structure - delegates to parsing.parse_table_structure()."""
        return parse_table_structure(table_item, result, table_index, document_id)

    def _build_column_mapping(
        self, column_headers: list, is_multi_header: bool
    ) -> dict[int, tuple[str | None, str | None]]:
        """Build column mapping - delegates to parsing.build_column_mapping()."""
        return build_column_mapping(column_headers, is_multi_header)

    def _get_row_period(self, row_headers: list, row_idx: int) -> str | None:
        """Get row period - delegates to parsing.get_row_period()."""
        return get_row_period(row_headers, row_idx)

    def _extract_caption(self, table_markdown: str) -> str | None:
        """Extract caption - delegates to parsing.extract_caption()."""
        return extract_caption(table_markdown)

    def _parse_markdown_row(self, row_line: str) -> list[str]:
        """Parse markdown row - delegates to parsing.parse_markdown_row()."""
        return parse_markdown_row(row_line)

    def _parse_value_unit(self, cell_text: str) -> tuple[float | None, str | None]:
        """Parse value and unit - delegates to parsing.parse_value_unit()."""
        return parse_value_unit(cell_text)

    def _extract_year(self, period_text: str) -> int | None:
        """Extract year - delegates to parsing.extract_year()."""
        return extract_year(period_text)
