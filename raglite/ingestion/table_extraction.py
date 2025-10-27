"""Table extraction and SQL structuring for financial documents.

Story 2.13 AC1: Extract tables from Docling output and parse into structured SQL format.
"""

import re
from pathlib import Path
from typing import Any

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import ConversionResult, DocumentConverter, PdfFormatOption
from docling_core.types.doc import TableItem

from raglite.ingestion.adaptive_table_extraction import extract_table_data_adaptive
from raglite.shared.logging import get_logger

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

    def __init__(self):
        """Initialize table extractor with Docling converter."""
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

        return self.extract_tables_from_result(result, Path(doc_path).stem)

    def extract_tables_from_result(
        self, result: ConversionResult, document_id: str
    ) -> list[dict[str, Any]]:
        """Extract and parse tables from existing Docling ConversionResult.

        This method is optimized for use when the document has already been converted
        (e.g., in ingestion pipeline) to avoid double-conversion.

        Args:
            result: Docling ConversionResult from document conversion
            document_id: Document filename (without extension)

        Returns:
            List of table rows as dicts (ready for SQL insertion)
        """
        all_rows: list[dict[str, Any]] = []
        table_index = 0

        # Iterate through all document items
        for item, _ in result.document.iterate_items():
            if isinstance(item, TableItem):
                # Get page number from table provenance
                page_number = item.prov[0].page_no if item.prov else 1

                # Extract using adaptive table extraction (Story 2.13 AC4 fix)
                parsed_rows = extract_table_data_adaptive(
                    table_item=item,
                    result=result,
                    table_index=table_index,
                    document_id=document_id,
                    page_number=page_number,
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

    def _parse_table_structure(
        self, table_item: TableItem, result: ConversionResult, table_index: int, document_id: str
    ) -> list[dict[str, Any]]:
        """Parse table into structured rows for SQL insertion using table_cells API.

        Strategy (AC1 - REVISED for multi-header tables):
        1. Access table.data.table_cells directly (production-proven 80%+ accuracy)
        2. Detect multi-header structure via column_header flags
        3. Build hierarchical column mapping (metric -> entity)
        4. Extract data cells using column mapping
        5. Parse each cell: extract value + unit

        Research validation: Salesforce, fintechs use this approach (≥80% accuracy)

        Args:
            table_item: Docling TableItem object
            result: ConversionResult (for markdown context)
            table_index: Index of table in document
            document_id: Document filename (without extension)

        Returns:
            List of structured row dicts
        """
        rows: list[dict[str, Any]] = []

        # Get table caption (from markdown export for context)
        table_markdown = table_item.export_to_markdown(doc=result.document)
        caption = self._extract_caption(table_markdown)

        # Get page number
        page_number = table_item.prov[0].page_no if table_item.prov else 1

        # Access table_cells API directly
        table_cells = table_item.data.table_cells
        num_rows = table_item.data.num_rows
        num_cols = table_item.data.num_cols

        if not table_cells:
            logger.warning(
                f"Skipping empty table {table_index}", extra={"table_index": table_index}
            )
            return rows

        # Detect multi-header structure
        column_headers = [cell for cell in table_cells if cell.column_header]
        header_rows = set(cell.start_row_offset_idx for cell in column_headers)
        is_multi_header = len(header_rows) > 1

        logger.debug(
            f"Table {table_index} structure",
            extra={
                "table_index": table_index,
                "dimensions": f"{num_rows}x{num_cols}",
                "header_rows": sorted(header_rows),
                "multi_header": is_multi_header,
            },
        )

        # Build column mapping (col_idx -> (metric, entity))
        column_mapping = self._build_column_mapping(column_headers, is_multi_header)

        # Get row headers (for period extraction)
        row_headers = [cell for cell in table_cells if cell.row_header]

        # Extract data cells
        data_cells = [
            cell for cell in table_cells if not cell.column_header and not cell.row_header
        ]

        # Parse each data cell
        for cell in data_cells:
            if not cell.text or not cell.text.strip():
                continue

            row_idx = cell.start_row_offset_idx
            col_idx = cell.start_col_offset_idx

            # Get metric + entity from column mapping
            metric, entity = column_mapping.get(col_idx, (None, None))

            # Get period from row headers
            period = self._get_row_period(row_headers, row_idx)

            # Parse value + unit
            value, unit = self._parse_value_unit(cell.text)

            # Extract fiscal year
            fiscal_year = self._extract_year(period) if period else None

            # Create structured row
            row_dict = {
                "entity": entity,
                "metric": metric,
                "period": period,
                "fiscal_year": fiscal_year,
                "value": value,
                "unit": unit,
                "page_number": page_number,
                "table_index": table_index,
                "table_caption": caption,
                "row_index": row_idx,
                "column_name": f"{metric}_{entity}" if metric and entity else None,
                "chunk_text": table_markdown[:500],
                "document_id": document_id,
            }

            rows.append(row_dict)

        logger.debug(
            f"Parsed table {table_index} via table_cells API",
            extra={
                "table_index": table_index,
                "page": page_number,
                "rows": len(rows),
                "caption": caption,
                "multi_header": is_multi_header,
            },
        )

        return rows

    def _build_column_mapping(
        self, column_headers: list, is_multi_header: bool
    ) -> dict[int, tuple[str | None, str | None]]:
        """Build column index to (metric, entity) mapping.

        For multi-header tables:
        - Row 0: Metric categories ("Frequency Ratio", "Currency Exchange")
        - Row 1: Entity names ("Portugal", "Angola", "Group")

        For single-header tables:
        - Row 0: Period names ("Aug-25 YTD", "Q2 2025")
        - Entity/metric from row headers or defaults

        Args:
            column_headers: List of cells with column_header=True
            is_multi_header: Whether table has 2+ header rows

        Returns:
            Dict mapping col_idx to (metric, entity) tuple
        """
        mapping: dict[int, tuple[str | None, str | None]] = {}

        if not column_headers:
            return mapping

        if is_multi_header:
            # Separate headers by row level
            headers_by_row: dict[int, list] = {}
            for cell in column_headers:
                row_idx = cell.start_row_offset_idx
                if row_idx not in headers_by_row:
                    headers_by_row[row_idx] = []
                headers_by_row[row_idx].append(cell)

            # Sort row indices to get header levels
            row_levels = sorted(headers_by_row.keys())

            if len(row_levels) >= 2:
                # Multi-header: Row 0 = metrics, Row 1 = entities
                metric_row = row_levels[0]
                entity_row = row_levels[1]

                # Build metric mapping (may span multiple columns)
                metric_map: dict[int, str] = {}
                for cell in headers_by_row[metric_row]:
                    start_col = cell.start_col_offset_idx
                    end_col = cell.end_col_offset_idx
                    metric_text = cell.text.strip() if cell.text else "Unknown"
                    # Apply metric to all spanned columns
                    for col_idx in range(start_col, end_col):
                        metric_map[col_idx] = metric_text

                # Build final mapping with entities
                for cell in headers_by_row[entity_row]:
                    col_idx = cell.start_col_offset_idx
                    entity = cell.text.strip() if cell.text else "Unknown"
                    metric = metric_map.get(col_idx, "Unknown")
                    mapping[col_idx] = (metric, entity)

        else:
            # Single-header: Periods as column names
            # Entity/metric will come from row context
            for cell in column_headers:
                col_idx = cell.start_col_offset_idx
                period_name = cell.text.strip() if cell.text else "Unknown"
                # For single-header, use period as both metric and entity placeholder
                mapping[col_idx] = (period_name, None)

        return mapping

    def _get_row_period(self, row_headers: list, row_idx: int) -> str | None:
        """Extract period from row headers for given row index.

        Args:
            row_headers: List of cells with row_header=True
            row_idx: Row index to find period for

        Returns:
            Period text (e.g., "Jan-25", "Q2 2025") or None
        """
        for cell in row_headers:
            if cell.start_row_offset_idx == row_idx:
                return cell.text.strip() if cell.text else None
        return None

    def _extract_caption(self, table_markdown: str) -> str | None:
        """Extract table caption from markdown (first non-table line)."""
        for line in table_markdown.split("\n"):
            line = line.strip()
            if line and "|" not in line and not line.startswith("#"):
                return line
        return None

    def _parse_markdown_row(self, row_line: str) -> list[str]:
        """Parse markdown table row into list of cell values.

        Example:
            >>> _parse_markdown_row("| Entity | Metric | Aug-25 YTD |")
            ['Entity', 'Metric', 'Aug-25 YTD']
        """
        # Remove leading/trailing pipes
        row_line = row_line.strip().strip("|")
        # Split by pipe and strip whitespace
        cells = [cell.strip() for cell in row_line.split("|")]
        return cells

    def _parse_value_unit(self, cell_text: str) -> tuple[float | None, str | None]:
        """Parse cell text into (value, unit) tuple.

        Examples:
            >>> _parse_value_unit("23.2 EUR/ton")
            (23.2, "EUR/ton")

            >>> _parse_value_unit("1,234.56 GJ")
            (1234.56, "GJ")

            >>> _parse_value_unit("42.5")
            (42.5, None)

            >>> _parse_value_unit("N/A")
            (None, None)
        """
        cell_text = cell_text.strip()

        if not cell_text or cell_text.upper() in ("N/A", "-", ""):
            return None, None

        # Regex to match number (with optional commas) and optional unit
        # Pattern: optional sign, digits with commas, optional decimal, optional unit
        match = re.match(r"^([+-]?[\d,]+\.?\d*)\s*([A-Za-z/%€£$]+)?", cell_text)

        if match:
            # Extract numeric value (remove commas)
            value_str = match.group(1).replace(",", "")
            try:
                value = float(value_str)
            except ValueError:
                logger.debug(f"Failed to parse value: {cell_text}")
                return None, None

            # Extract unit (if present)
            unit = match.group(2) if match.group(2) else None

            return value, unit

        # No numeric value found
        return None, None

    def _extract_year(self, period_text: str) -> int | None:
        """Extract fiscal year from period text.

        Examples:
            >>> _extract_year("Aug-25 YTD")
            2025

            >>> _extract_year("Q2 2025")
            2025

            >>> _extract_year("2024")
            2024

            >>> _extract_year("Aug-24")
            2024
        """
        if not period_text:
            return None

        # Look for 4-digit year (2024, 2025, etc.)
        match_4digit = re.search(r"\b(20\d{2})\b", period_text)
        if match_4digit:
            return int(match_4digit.group(1))

        # Look for 2-digit year (24, 25, etc.) and convert to 20XX
        match_2digit = re.search(r"-(\d{2})\b", period_text)
        if match_2digit:
            year_2digit = int(match_2digit.group(1))
            # Assume 20XX for years 00-99
            return 2000 + year_2digit

        # Look for standalone 2-digit year at end
        match_standalone = re.search(r"\b(\d{2})$", period_text)
        if match_standalone:
            year_2digit = int(match_standalone.group(1))
            return 2000 + year_2digit

        return None
