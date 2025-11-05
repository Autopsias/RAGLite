"""Unit tests for Phase 2.7 transposed table detection and extraction.

Story 2.13 Phase 2.7: Tests for transposed table pattern detection and extraction.

Transposed tables have:
- Metrics as row labels (first column, col_idx=0)
- Entities as column headers (Row 0)
- Optional periods as sub-headers (Row 1)

Example pattern (pages 20-21):
                    Portugal        Tunisia         Lebanon         Brazil
                Aug-25  Budget  Aug-25  Budget  Aug-25  Budget  Aug-25  Budget
Variable Cost   -23.4   -20.4   -29.1   -27.3   -50.9   -44.4   -20.7   -22.0
Thermal Energy  -5.9    -5.9    -11.1   -10.5   -9.7    -12.3   -8.8    -9.1
"""

from typing import Any
from unittest.mock import Mock

import pytest
from docling_core.types.doc import DoclingDocument, TableCell, TableItem

from raglite.ingestion.adaptive_table_extraction import (
    TableLayout,
    _extract_transposed_entity_cols_metric_row_labels,
    detect_table_layout,
)


@pytest.fixture
def mock_result():
    """Mock ConversionResult for table extraction."""
    result = Mock()
    result.document = Mock(spec=DoclingDocument)
    return result


@pytest.fixture
def mock_table_item():
    """Mock TableItem for testing."""
    table_item = Mock(spec=TableItem)
    table_item.export_to_markdown.return_value = "| Test | Table |"
    return table_item


def create_table_cell(
    text: str,
    row_idx: int,
    col_idx: int,
    row_span: int = 1,
    col_span: int = 1,
    is_header: bool = False,
) -> Mock:
    """Helper to create mock TableCell."""
    cell = Mock(spec=TableCell)
    cell.text = text
    cell.start_row_offset_idx = row_idx
    cell.end_row_offset_idx = row_idx + row_span
    cell.start_col_offset_idx = col_idx
    cell.end_col_offset_idx = col_idx + col_span
    cell.column_header = is_header
    cell.row_header = False
    return cell


class TestTransposedTableDetection:
    """Test transposed table pattern detection."""

    def test_detect_transposed_single_header(self):
        """Test detection of transposed table with single header row."""
        # Create transposed pattern:
        # Row 0: [Entity headers] Portugal, Tunisia, Lebanon
        # Row 1+: [Metrics in first column] Variable Cost, Thermal Energy, Fixed Costs
        table_cells = [
            # Column headers (Row 0)
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_header=True),
            create_table_cell("Tunisia", row_idx=0, col_idx=1, is_header=True),
            create_table_cell("Lebanon", row_idx=0, col_idx=2, is_header=True),
            # First column - metrics (NOT marked as headers)
            create_table_cell("Variable Cost Eur/ton", row_idx=1, col_idx=0, is_header=False),
            create_table_cell("Thermal Energy Eur/ton", row_idx=2, col_idx=0, is_header=False),
            create_table_cell("Fixed Costs Eur/ton", row_idx=3, col_idx=0, is_header=False),
            create_table_cell("Sales Volumes kton", row_idx=4, col_idx=0, is_header=False),
            # Data cells
            create_table_cell("-23.4", row_idx=1, col_idx=1, is_header=False),
            create_table_cell("-29.1", row_idx=1, col_idx=2, is_header=False),
            create_table_cell("-5.9", row_idx=2, col_idx=1, is_header=False),
            create_table_cell("-11.1", row_idx=2, col_idx=2, is_header=False),
        ]

        layout, metadata = detect_table_layout(table_cells, num_rows=5, num_cols=3)

        # Should detect as transposed
        assert layout == TableLayout.TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS
        assert metadata["transposed_pattern"] is True
        assert metadata["entity_location"] == "cols"
        assert metadata["metric_location"] == "first_column"
        assert metadata["first_col_metric_ratio"] >= 0.5

    def test_detect_transposed_multi_header(self):
        """Test detection of transposed table with multi-level headers (entity + period)."""
        # Create transposed pattern with 2 header rows:
        # Row 0: [Entities] Portugal (spans 2 cols), Tunisia (spans 2 cols)
        # Row 1: [Periods] Aug-25, Budget, Aug-25, Budget
        # Row 2+: [Metrics] Variable Cost, Thermal Energy
        table_cells = [
            # Row 0 - Entity headers
            create_table_cell("Portugal", row_idx=0, col_idx=0, col_span=2, is_header=True),
            create_table_cell("Tunisia", row_idx=0, col_idx=2, col_span=2, is_header=True),
            # Row 1 - Period sub-headers
            create_table_cell("Aug-25", row_idx=1, col_idx=0, is_header=True),
            create_table_cell("Budget", row_idx=1, col_idx=1, is_header=True),
            create_table_cell("Aug-25", row_idx=1, col_idx=2, is_header=True),
            create_table_cell("Budget", row_idx=1, col_idx=3, is_header=True),
            # First column - metrics
            create_table_cell("Variable Cost", row_idx=2, col_idx=0, is_header=False),
            create_table_cell("Thermal Energy", row_idx=3, col_idx=0, is_header=False),
            create_table_cell("Fixed Costs", row_idx=4, col_idx=0, is_header=False),
            # Data cells
            create_table_cell("-23.4", row_idx=2, col_idx=1, is_header=False),
            create_table_cell("-20.4", row_idx=2, col_idx=2, is_header=False),
        ]

        layout, metadata = detect_table_layout(table_cells, num_rows=5, num_cols=4)

        # Should detect as transposed
        assert layout == TableLayout.TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS
        assert metadata["transposed_pattern"] is True
        assert metadata["period_location"] == "multi_header"

    def test_not_transposed_traditional_table(self):
        """Test that traditional tables (metrics in headers) are NOT detected as transposed."""
        # Traditional pattern:
        # Row 0: [Metric headers] EBITDA, Turnover, Margin
        # Row 1+: [Entity in first column] Portugal, Spain, France
        table_cells = [
            # Column headers - metrics
            create_table_cell("EBITDA", row_idx=0, col_idx=0, is_header=True),
            create_table_cell("Turnover", row_idx=0, col_idx=1, is_header=True),
            create_table_cell("Margin", row_idx=0, col_idx=2, is_header=True),
            # First column - entities (NOT metrics)
            create_table_cell("Portugal", row_idx=1, col_idx=0, is_header=False),
            create_table_cell("Spain", row_idx=2, col_idx=0, is_header=False),
            create_table_cell("France", row_idx=3, col_idx=0, is_header=False),
            # Data cells
            create_table_cell("1234", row_idx=1, col_idx=1, is_header=False),
            create_table_cell("5678", row_idx=1, col_idx=2, is_header=False),
        ]

        layout, metadata = detect_table_layout(table_cells, num_rows=4, num_cols=3)

        # Should NOT detect as transposed (first column has entities, not metrics)
        assert layout != TableLayout.TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS
        assert metadata.get("transposed_pattern", False) is False

    def test_not_transposed_insufficient_metrics_threshold(self):
        """Test that tables with <50% metrics in first column are NOT detected as transposed."""
        # Borderline case: Only 40% of first column is metrics
        table_cells = [
            # Column headers
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_header=True),
            create_table_cell("Tunisia", row_idx=0, col_idx=1, is_header=True),
            # First column - mixed content (only 2 of 5 rows are metrics = 40%)
            create_table_cell("Variable Cost", row_idx=1, col_idx=0, is_header=False),
            create_table_cell("Thermal Energy", row_idx=2, col_idx=0, is_header=False),
            create_table_cell("Some Text", row_idx=3, col_idx=0, is_header=False),
            create_table_cell("Random Data", row_idx=4, col_idx=0, is_header=False),
            create_table_cell("More Text", row_idx=5, col_idx=0, is_header=False),
        ]

        layout, metadata = detect_table_layout(table_cells, num_rows=6, num_cols=2)

        # Should NOT detect as transposed (metric ratio <50%)
        assert layout != TableLayout.TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS

    def test_not_transposed_insufficient_rows(self):
        """Test that tables with <3 data rows are NOT detected as transposed."""
        # Only 2 data rows (below minimum threshold)
        table_cells = [
            # Headers
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_header=True),
            create_table_cell("Tunisia", row_idx=0, col_idx=1, is_header=True),
            # First column - metrics (but only 2 rows)
            create_table_cell("Variable Cost", row_idx=1, col_idx=0, is_header=False),
            create_table_cell("Thermal Energy", row_idx=2, col_idx=0, is_header=False),
        ]

        layout, metadata = detect_table_layout(table_cells, num_rows=3, num_cols=2)

        # Should NOT detect as transposed (insufficient data rows)
        assert layout != TableLayout.TRANSPOSED_ENTITY_COLS_METRIC_ROW_LABELS


class TestTransposedTableExtraction:
    """Test transposed table data extraction."""

    def test_extract_single_header_transposed(self, mock_table_item, mock_result):
        """Test extraction from transposed table with single header row."""
        # Pattern (transposed):
        #              Portugal  Tunisia  Lebanon
        # Var Cost     -23.4     -29.1    -50.9
        # Thermal      -5.9      -11.1    -9.7
        #
        # NOTE: In transposed tables, col_idx=0 contains METRICS (first column),
        # and entity headers start at col_idx=1, 2, 3...
        table_cells = [
            # Column headers (Row 0) - Entities start at col_idx=1
            create_table_cell("", row_idx=0, col_idx=0, is_header=True),  # Top-left corner (empty)
            create_table_cell("Portugal", row_idx=0, col_idx=1, is_header=True),
            create_table_cell("Tunisia", row_idx=0, col_idx=2, is_header=True),
            create_table_cell("Lebanon", row_idx=0, col_idx=3, is_header=True),
            # First column (col_idx=0) - Metrics
            create_table_cell("Variable Cost Eur/ton", row_idx=1, col_idx=0, is_header=False),
            create_table_cell("Thermal Energy Eur/ton", row_idx=2, col_idx=0, is_header=False),
            # Data cells (col_idx=1, 2, 3)
            create_table_cell("-23.4", row_idx=1, col_idx=1, is_header=False),
            create_table_cell("-29.1", row_idx=1, col_idx=2, is_header=False),
            create_table_cell("-50.9", row_idx=1, col_idx=3, is_header=False),
            create_table_cell("-5.9", row_idx=2, col_idx=1, is_header=False),
            create_table_cell("-11.1", row_idx=2, col_idx=2, is_header=False),
            create_table_cell("-9.7", row_idx=2, col_idx=3, is_header=False),
        ]

        metadata: dict[str, Any] = {}
        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=3,
            num_cols=4,
            metadata=metadata,
            document_id="test_doc",
            page_number=20,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Should extract 6 rows (2 metrics × 3 entities)
        assert len(rows) == 6

        # Verify extraction structure
        portugal_var_cost = [
            r for r in rows if r["entity"] == "Portugal" and "Variable Cost" in r["metric"]
        ][0]
        assert portugal_var_cost["value"] == -23.4
        assert portugal_var_cost["page_number"] == 20
        assert portugal_var_cost["extraction_method"] == "transposed_entity_cols_metric_row_labels"

        tunisia_thermal = [
            r for r in rows if r["entity"] == "Tunisia" and "Thermal Energy" in r["metric"]
        ][0]
        assert tunisia_thermal["value"] == -11.1

        lebanon_var_cost = [
            r for r in rows if r["entity"] == "Lebanon" and "Variable Cost" in r["metric"]
        ][0]
        assert lebanon_var_cost["value"] == -50.9

    def test_extract_multi_header_transposed(self, mock_table_item, mock_result):
        """Test extraction from transposed table with entity + period headers."""
        # Pattern:
        #                Portugal        Tunisia
        #           Aug-25  Budget  Aug-25  Budget
        # Var Cost  -23.4   -20.4   -29.1   -27.3
        # Thermal   -5.9    -5.9    -11.1   -10.5
        table_cells = [
            # Row 0 - Entity headers (spanning columns)
            create_table_cell("Portugal", row_idx=0, col_idx=0, col_span=2, is_header=True),
            create_table_cell("Tunisia", row_idx=0, col_idx=2, col_span=2, is_header=True),
            # Row 1 - Period sub-headers
            create_table_cell("Aug-25", row_idx=1, col_idx=0, is_header=True),
            create_table_cell("Budget", row_idx=1, col_idx=1, is_header=True),
            create_table_cell("Aug-25", row_idx=1, col_idx=2, is_header=True),
            create_table_cell("Budget", row_idx=1, col_idx=3, is_header=True),
            # First column - Metrics
            create_table_cell("Variable Cost", row_idx=2, col_idx=0, is_header=False),
            create_table_cell("Thermal Energy", row_idx=3, col_idx=0, is_header=False),
            # Data cells
            create_table_cell("-23.4", row_idx=2, col_idx=1, is_header=False),
            create_table_cell("-20.4", row_idx=2, col_idx=2, is_header=False),
            create_table_cell("-29.1", row_idx=2, col_idx=3, is_header=False),
            create_table_cell("-5.9", row_idx=3, col_idx=1, is_header=False),
            create_table_cell("-5.9", row_idx=3, col_idx=2, is_header=False),
            create_table_cell("-11.1", row_idx=3, col_idx=3, is_header=False),
        ]

        metadata: dict[str, Any] = {}
        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=4,
            num_cols=4,
            metadata=metadata,
            document_id="test_doc",
            page_number=21,
            table_index=2,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Should extract 6 rows (2 metrics × 2 entities × 2 periods - 2 cells = 6 data cells)
        assert len(rows) == 6

        # Verify entity mapping works across column spans
        portugal_rows = [r for r in rows if r["entity"] == "Portugal"]
        tunisia_rows = [r for r in rows if r["entity"] == "Tunisia"]
        assert len(portugal_rows) >= 2, "Portugal should appear in multiple rows"
        assert len(tunisia_rows) >= 2, "Tunisia should appear in multiple rows"

        # Verify period extraction
        aug_rows = [r for r in rows if r["period"] == "Aug-25"]
        budget_rows = [r for r in rows if r["period"] == "Budget"]
        assert len(aug_rows) >= 2
        assert len(budget_rows) >= 2

    def test_extract_handles_empty_cells(self, mock_table_item, mock_result):
        """Test that extraction handles empty/None cell values gracefully."""
        table_cells = [
            # Headers
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_header=True),
            create_table_cell("Tunisia", row_idx=0, col_idx=1, is_header=True),
            # First column
            create_table_cell("Variable Cost", row_idx=1, col_idx=0, is_header=False),
            # Data cells - one empty
            create_table_cell("-23.4", row_idx=1, col_idx=1, is_header=False),
            create_table_cell("", row_idx=1, col_idx=2, is_header=False),  # Empty cell
        ]

        metadata: dict[str, Any] = {}
        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=2,
            num_cols=2,
            metadata=metadata,
            document_id="test_doc",
            page_number=20,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Should only extract non-empty cells
        assert len(rows) == 1
        assert rows[0]["value"] == -23.4

    def test_extract_metric_parsing(self, mock_table_item, mock_result):
        """Test that metrics are correctly parsed from row labels."""
        table_cells = [
            # Headers
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_header=True),
            # Metrics with various formats
            create_table_cell("Variable Cost Eur/ton", row_idx=1, col_idx=0, is_header=False),
            create_table_cell("Thermal Energy GJ/ton", row_idx=2, col_idx=0, is_header=False),
            create_table_cell("Sales Volumes kton", row_idx=3, col_idx=0, is_header=False),
            create_table_cell("EBITDA %", row_idx=4, col_idx=0, is_header=False),
            # Data cells
            create_table_cell("-23.4", row_idx=1, col_idx=1, is_header=False),
            create_table_cell("-5.9", row_idx=2, col_idx=1, is_header=False),
            create_table_cell("1234", row_idx=3, col_idx=1, is_header=False),
            create_table_cell("45.6", row_idx=4, col_idx=1, is_header=False),
        ]

        metadata: dict[str, Any] = {}
        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=5,
            num_cols=2,
            metadata=metadata,
            document_id="test_doc",
            page_number=20,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Check metrics are extracted
        assert len(rows) == 4
        metrics = {r["metric"] for r in rows}
        assert "Variable Cost Eur/ton" in metrics or "Variable Cost" in str(metrics)
        assert "Thermal Energy GJ/ton" in metrics or "Thermal Energy" in str(metrics)

    def test_extract_column_name_generation(self, mock_table_item, mock_result):
        """Test that column names are generated correctly."""
        # Pattern with entity + period headers:
        #                Portugal
        #               Aug-25
        # Variable Cost -23.4
        table_cells = [
            # Row 0 - Entity header (col_idx=1, not col_idx=0 which is for metrics)
            create_table_cell("", row_idx=0, col_idx=0, is_header=True),  # Top-left corner
            create_table_cell("Portugal", row_idx=0, col_idx=1, is_header=True),
            # Row 1 - Period sub-header
            create_table_cell("", row_idx=1, col_idx=0, is_header=True),  # Left column header
            create_table_cell("Aug-25", row_idx=1, col_idx=1, is_header=True),
            # Row 2 - Metric (col_idx=0) and data (col_idx=1)
            create_table_cell("Variable Cost", row_idx=2, col_idx=0, is_header=False),
            create_table_cell("-23.4", row_idx=2, col_idx=1, is_header=False),
        ]

        metadata: dict[str, Any] = {}
        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=3,
            num_cols=2,
            metadata=metadata,
            document_id="test_doc",
            page_number=20,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        assert len(rows) == 1
        # Column name should be in format: {metric}_{entity}_{period}
        col_name = rows[0]["column_name"]
        assert col_name is not None
        assert "Variable Cost" in col_name or "Variable_Cost" in col_name
        assert "Portugal" in col_name
        assert "Aug-25" in col_name or "Aug_25" in col_name

    def test_extract_metadata_fields(self, mock_table_item, mock_result):
        """Test that all required metadata fields are present."""
        table_cells = [
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_header=True),
            create_table_cell("Variable Cost", row_idx=1, col_idx=0, is_header=False),
            create_table_cell("-23.4", row_idx=1, col_idx=1, is_header=False),
        ]

        metadata: dict[str, Any] = {}
        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=2,
            num_cols=2,
            metadata=metadata,
            document_id="test_doc_123",
            page_number=20,
            table_index=5,
            table_item=mock_table_item,
            result=mock_result,
        )

        assert len(rows) == 1
        row = rows[0]

        # Verify all required fields
        assert row["document_id"] == "test_doc_123"
        assert row["page_number"] == 20
        assert row["table_index"] == 5
        assert row["row_index"] is not None
        assert row["extraction_method"] == "transposed_entity_cols_metric_row_labels"
        assert "entity" in row
        assert "metric" in row
        assert "value" in row
        assert "chunk_text" in row  # Markdown content
