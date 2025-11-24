"""Unit tests for standard table layout extraction functions.

Tests coverage for raglite/ingestion/adaptive_table/standard_layouts.py:
- _extract_temporal_cols_metric_rows (temporal columns + metric rows)
- _extract_entity_cols_metric_rows (entity columns + metric rows)
- _extract_transposed_entity_cols_metric_row_labels (transposed layout)

Target: Increase coverage from 54.0% to 70%+
"""

from unittest.mock import Mock

import pytest
from docling_core.types.doc import DoclingDocument, TableCell, TableItem

from raglite.ingestion.adaptive_table.standard_layouts import (
    _extract_entity_cols_metric_rows,
    _extract_temporal_cols_metric_rows,
    _extract_transposed_entity_cols_metric_row_labels,
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
    table_item.export_to_markdown.return_value = "| Test | Table | Data |"
    table_item.caption = None
    return table_item


def create_table_cell(
    text: str,
    row_idx: int,
    col_idx: int,
    row_span: int = 1,
    col_span: int = 1,
    is_col_header: bool = False,
    is_row_header: bool = False,
) -> Mock:
    """Helper to create mock TableCell with proper attributes."""
    cell = Mock(spec=TableCell)
    cell.text = text
    cell.start_row_offset_idx = row_idx
    cell.end_row_offset_idx = row_idx + row_span
    cell.start_col_offset_idx = col_idx
    cell.end_col_offset_idx = col_idx + col_span
    cell.column_header = is_col_header
    cell.row_header = is_row_header
    return cell


class TestTemporalColsMetricRows:
    """Test temporal columns + metric rows layout extraction."""

    def test_extract_basic_temporal_layout(self, mock_table_item, mock_result):
        """Test basic extraction with temporal column headers and metric rows."""
        # Pattern:
        #        | YTD    | Q1     | Q2     |
        # EBITDA | 1.2M   | 0.5M   | 0.7M   |
        # Sales  | 5.4M   | 2.1M   | 3.3M   |
        table_cells = [
            # Column headers (temporal periods) - row_idx=0
            create_table_cell("YTD", row_idx=0, col_idx=1, is_col_header=True),
            create_table_cell("Q1", row_idx=0, col_idx=2, is_col_header=True),
            create_table_cell("Q2", row_idx=0, col_idx=3, is_col_header=True),
            # Row headers (metrics) - col_idx=0
            create_table_cell("EBITDA", row_idx=1, col_idx=0, is_row_header=True),
            create_table_cell("Sales", row_idx=2, col_idx=0, is_row_header=True),
            # Data cells - match row_idx with metrics, col_idx with periods
            create_table_cell("1.2M", row_idx=1, col_idx=1, is_col_header=False),
            create_table_cell("0.5M", row_idx=1, col_idx=2, is_col_header=False),
            create_table_cell("0.7M", row_idx=1, col_idx=3, is_col_header=False),
            create_table_cell("5.4M", row_idx=2, col_idx=1, is_col_header=False),
            create_table_cell("2.1M", row_idx=2, col_idx=2, is_col_header=False),
        ]

        rows = _extract_temporal_cols_metric_rows(
            table_cells=table_cells,
            num_rows=3,
            num_cols=4,
            metadata={},
            document_id="test_doc",
            page_number=10,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Should extract 5 data cells
        assert len(rows) == 5
        assert all(r["document_id"] == "test_doc" for r in rows)
        assert all(r["page_number"] == 10 for r in rows)

        # Check metric mapping
        ebitda_rows = [r for r in rows if r["metric"] == "EBITDA"]
        assert len(ebitda_rows) == 3

        # Check period mapping
        ytd_rows = [r for r in rows if r["period"] == "YTD"]
        q1_rows = [r for r in rows if r["period"] == "Q1"]
        assert len(ytd_rows) >= 1
        assert len(q1_rows) >= 1

    def test_extract_temporal_with_year_extraction(self, mock_table_item, mock_result):
        """Test fiscal year extraction from period headers."""
        table_cells = [
            # Column headers with years - row_idx=0
            # Use "FY 2023" with space so regex \b works correctly
            create_table_cell("FY 2023", row_idx=0, col_idx=1, is_col_header=True),
            create_table_cell("2024", row_idx=0, col_idx=2, is_col_header=True),
            create_table_cell("Q1 2025", row_idx=0, col_idx=3, is_col_header=True),
            # Row header - col_idx=0
            create_table_cell("Revenue", row_idx=1, col_idx=0, is_row_header=True),
            # Data cells - row_idx matches metric, col_idx matches period
            create_table_cell("100M", row_idx=1, col_idx=1, is_col_header=False),
            create_table_cell("110M", row_idx=1, col_idx=2, is_col_header=False),
            create_table_cell("120M", row_idx=1, col_idx=3, is_col_header=False),
        ]

        rows = _extract_temporal_cols_metric_rows(
            table_cells=table_cells,
            num_rows=2,
            num_cols=4,
            metadata={},
            document_id="test_doc",
            page_number=5,
            table_index=2,
            table_item=mock_table_item,
            result=mock_result,
        )

        assert len(rows) == 3

        # Verify fiscal year extraction
        fy2023_row = [r for r in rows if "2023" in r["period"]][0]
        assert fy2023_row["fiscal_year"] == 2023

        fy2024_row = [r for r in rows if r["period"] == "2024"][0]
        assert fy2024_row["fiscal_year"] == 2024

        fy2025_row = [r for r in rows if "2025" in r["period"]][0]
        assert fy2025_row["fiscal_year"] == 2025

    def test_extract_temporal_handles_empty_cells(self, mock_table_item, mock_result):
        """Test graceful handling of empty data cells."""
        table_cells = [
            create_table_cell("Q1", row_idx=0, col_idx=0, is_col_header=True),
            create_table_cell("Revenue", row_idx=1, col_idx=0, is_row_header=True),
            create_table_cell("", row_idx=1, col_idx=1, is_col_header=False),  # Empty
            create_table_cell("100M", row_idx=1, col_idx=2, is_col_header=False),
        ]

        rows = _extract_temporal_cols_metric_rows(
            table_cells=table_cells,
            num_rows=2,
            num_cols=3,
            metadata={},
            document_id="test_doc",
            page_number=1,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Should skip empty cells
        assert len(rows) == 1
        assert rows[0]["value"] == 100.0


class TestEntityColsMetricRows:
    """Test entity columns + metric rows layout extraction."""

    def test_extract_basic_entity_layout(self, mock_table_item, mock_result):
        """Test basic extraction with entity columns and metric rows."""
        # Pattern:
        #        | Portugal | Angola | Brazil |
        # EBITDA | 1.2M     | 0.8M   | 2.1M   |
        # Sales  | 5.4M     | 3.2M   | 7.8M   |
        table_cells = [
            # Column headers (entities) - row_idx=0
            create_table_cell("Portugal", row_idx=0, col_idx=1, is_col_header=True),
            create_table_cell("Angola", row_idx=0, col_idx=2, is_col_header=True),
            create_table_cell("Brazil", row_idx=0, col_idx=3, is_col_header=True),
            # Row headers (metrics) - col_idx=0
            create_table_cell("EBITDA", row_idx=1, col_idx=0, is_row_header=True),
            create_table_cell("Sales", row_idx=2, col_idx=0, is_row_header=True),
            # Data cells - row_idx matches metric, col_idx matches entity
            create_table_cell("1.2M", row_idx=1, col_idx=1, is_col_header=False),
            create_table_cell("0.8M", row_idx=1, col_idx=2, is_col_header=False),
            create_table_cell("2.1M", row_idx=1, col_idx=3, is_col_header=False),
            create_table_cell("5.4M", row_idx=2, col_idx=1, is_col_header=False),
        ]

        rows = _extract_entity_cols_metric_rows(
            table_cells=table_cells,
            num_rows=3,
            num_cols=4,
            metadata={},
            document_id="test_doc",
            page_number=15,
            table_index=3,
            table_item=mock_table_item,
            result=mock_result,
        )

        assert len(rows) == 4

        # Check entity mapping
        portugal_rows = [r for r in rows if r["entity"] == "Portugal"]
        angola_rows = [r for r in rows if r["entity"] == "Angola"]
        assert len(portugal_rows) >= 1
        assert len(angola_rows) >= 1

        # Check metric mapping
        ebitda_rows = [r for r in rows if r["metric"] == "EBITDA"]
        sales_rows = [r for r in rows if r["metric"] == "Sales"]
        assert len(ebitda_rows) >= 2
        assert len(sales_rows) >= 1

    def test_extract_entity_with_caption_period(self, mock_table_item, mock_result):
        """Test period extraction from table caption."""
        mock_table_item.caption = "Financial Data Q3 2024"

        table_cells = [
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_col_header=True),
            create_table_cell("EBITDA", row_idx=1, col_idx=0, is_row_header=True),
            create_table_cell("1.2M", row_idx=1, col_idx=1, is_col_header=False),
        ]

        rows = _extract_entity_cols_metric_rows(
            table_cells=table_cells,
            num_rows=2,
            num_cols=2,
            metadata={},
            document_id="test_doc",
            page_number=8,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        assert len(rows) == 1
        # Period should be extracted from caption
        assert rows[0]["period"] == "Financial Data Q3 2024"
        assert rows[0]["fiscal_year"] == 2024

    def test_extract_entity_null_period_acceptable(self, mock_table_item, mock_result):
        """Test that NULL periods are acceptable for entity-metric tables."""
        table_cells = [
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_col_header=True),
            create_table_cell("Revenue", row_idx=1, col_idx=0, is_row_header=True),
            create_table_cell("100M", row_idx=1, col_idx=1, is_col_header=False),
        ]

        rows = _extract_entity_cols_metric_rows(
            table_cells=table_cells,
            num_rows=2,
            num_cols=2,
            metadata={},
            document_id="test_doc",
            page_number=1,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        assert len(rows) == 1
        # Period can be NULL
        assert rows[0]["period"] is None
        assert rows[0]["fiscal_year"] is None

    def test_extract_entity_column_name_format(self, mock_table_item, mock_result):
        """Test column name generation format: metric_entity."""
        table_cells = [
            # Column header (entity) - row_idx=0, col_idx=1
            create_table_cell("Tunisia", row_idx=0, col_idx=1, is_col_header=True),
            # Row header (metric) - row_idx=1, col_idx=0
            create_table_cell("Margin", row_idx=1, col_idx=0, is_row_header=True),
            # Data cell - row_idx matches metric, col_idx matches entity
            create_table_cell("25.5", row_idx=1, col_idx=1, is_col_header=False),
        ]

        rows = _extract_entity_cols_metric_rows(
            table_cells=table_cells,
            num_rows=2,
            num_cols=2,
            metadata={},
            document_id="test_doc",
            page_number=12,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        assert len(rows) == 1
        col_name = rows[0]["column_name"]
        assert col_name is not None
        assert "Margin" in col_name
        assert "Tunisia" in col_name


class TestTransposedTableExtraction:
    """Test transposed table extraction (metrics in first column)."""

    def test_extract_transposed_single_header_row(self, mock_table_item, mock_result):
        """Test transposed table with single entity header row."""
        # Pattern:
        #               Portugal  Tunisia
        # Variable Cost -23.4     -29.1
        # EBITDA        1.2       0.8
        table_cells = [
            # Column headers (entities) - start from col_idx=1
            create_table_cell("", row_idx=0, col_idx=0, is_col_header=True),
            create_table_cell("Portugal", row_idx=0, col_idx=1, is_col_header=True),
            create_table_cell("Tunisia", row_idx=0, col_idx=2, is_col_header=True),
            # First column - metrics
            create_table_cell("Variable Cost", row_idx=1, col_idx=0, is_col_header=False),
            create_table_cell("EBITDA", row_idx=2, col_idx=0, is_col_header=False),
            # Data cells
            create_table_cell("-23.4", row_idx=1, col_idx=1, is_col_header=False),
            create_table_cell("-29.1", row_idx=1, col_idx=2, is_col_header=False),
            create_table_cell("1.2", row_idx=2, col_idx=1, is_col_header=False),
            create_table_cell("0.8", row_idx=2, col_idx=2, is_col_header=False),
        ]

        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=3,
            num_cols=3,
            metadata={},
            document_id="test_doc",
            page_number=20,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Should extract 4 data cells (2 metrics × 2 entities)
        assert len(rows) == 4

        # Verify entity mapping
        portugal_rows = [r for r in rows if r["entity"] == "Portugal"]
        tunisia_rows = [r for r in rows if r["entity"] == "Tunisia"]
        assert len(portugal_rows) == 2
        assert len(tunisia_rows) == 2

        # Verify metric extraction
        var_cost_rows = [r for r in rows if "Variable Cost" in str(r["metric"])]
        ebitda_rows = [r for r in rows if "EBITDA" in str(r["metric"])]
        assert len(var_cost_rows) == 2
        assert len(ebitda_rows) == 2

    def test_extract_transposed_multi_header_entity_period(self, mock_table_item, mock_result):
        """Test transposed table with entity and period headers."""
        # Pattern:
        #               Portugal        Tunisia
        #               Aug-25  Budget  Aug-25
        # Variable Cost -23.4   -20.4   -29.1
        table_cells = [
            # Row 0 - Entity headers (spanning columns) - starts from col_idx=1
            create_table_cell("Portugal", row_idx=0, col_idx=1, col_span=2, is_col_header=True),
            create_table_cell("Tunisia", row_idx=0, col_idx=3, col_span=1, is_col_header=True),
            # Row 1 - Period sub-headers - starts from col_idx=1
            create_table_cell("Aug-25", row_idx=1, col_idx=1, is_col_header=True),
            create_table_cell("Budget", row_idx=1, col_idx=2, is_col_header=True),
            create_table_cell("Aug-25", row_idx=1, col_idx=3, is_col_header=True),
            # First column (col_idx=0) - metrics
            create_table_cell("Variable Cost", row_idx=2, col_idx=0, is_col_header=False),
            # Data cells - start from col_idx=1
            create_table_cell("-23.4", row_idx=2, col_idx=1, is_col_header=False),
            create_table_cell("-20.4", row_idx=2, col_idx=2, is_col_header=False),
            create_table_cell("-29.1", row_idx=2, col_idx=3, is_col_header=False),
        ]

        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=3,
            num_cols=4,
            metadata={},
            document_id="test_doc",
            page_number=21,
            table_index=2,
            table_item=mock_table_item,
            result=mock_result,
        )

        assert len(rows) == 3

        # Verify entity and period mapping - Portugal appears twice, Tunisia once
        portugal_rows = [r for r in rows if r["entity"] == "Portugal"]
        tunisia_rows = [r for r in rows if r["entity"] == "Tunisia"]
        assert len(portugal_rows) == 2
        assert len(tunisia_rows) == 1

        # Check period mapping
        aug_rows = [r for r in rows if r["period"] == "Aug-25"]
        budget_rows = [r for r in rows if r["period"] == "Budget"]
        assert len(aug_rows) == 2  # Portugal Aug-25 + Tunisia Aug-25
        assert len(budget_rows) == 1  # Portugal Budget

    def test_extract_transposed_handles_missing_metric(self, mock_table_item, mock_result):
        """Test handling of rows with missing metric names."""
        table_cells = [
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_col_header=True),
            # Row with no metric name in first column
            create_table_cell("", row_idx=1, col_idx=0, is_col_header=False),
            create_table_cell("123", row_idx=1, col_idx=1, is_col_header=False),
            # Row with metric name
            create_table_cell("EBITDA", row_idx=2, col_idx=0, is_col_header=False),
            create_table_cell("456", row_idx=2, col_idx=1, is_col_header=False),
        ]

        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=3,
            num_cols=2,
            metadata={},
            document_id="test_doc",
            page_number=1,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Should still extract both rows (metric can be None)
        assert len(rows) == 2

    def test_extract_transposed_extraction_method_marker(self, mock_table_item, mock_result):
        """Test that extraction method is correctly marked."""
        table_cells = [
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_col_header=True),
            create_table_cell("EBITDA", row_idx=1, col_idx=0, is_col_header=False),
            create_table_cell("100", row_idx=1, col_idx=1, is_col_header=False),
        ]

        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells=table_cells,
            num_rows=2,
            num_cols=2,
            metadata={},
            document_id="test_doc",
            page_number=5,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        assert len(rows) == 1
        assert rows[0]["extraction_method"] == "transposed_entity_cols_metric_row_labels"


class TestStandardLayoutsEdgeCases:
    """Test edge cases and error handling across all standard layouts."""

    def test_temporal_with_none_period_headers(self, mock_table_item, mock_result):
        """Test temporal extraction when period headers are None."""
        table_cells = [
            create_table_cell(None, row_idx=0, col_idx=0, is_col_header=True),
            create_table_cell("Revenue", row_idx=1, col_idx=0, is_row_header=True),
            create_table_cell("100", row_idx=1, col_idx=1, is_col_header=False),
        ]

        rows = _extract_temporal_cols_metric_rows(
            table_cells=table_cells,
            num_rows=2,
            num_cols=2,
            metadata={},
            document_id="test_doc",
            page_number=1,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Should still extract with None period
        assert len(rows) == 1
        assert rows[0]["period"] is None

    def test_entity_with_whitespace_only_cells(self, mock_table_item, mock_result):
        """Test entity extraction with whitespace-only cells."""
        table_cells = [
            create_table_cell("Portugal", row_idx=0, col_idx=0, is_col_header=True),
            create_table_cell("Revenue", row_idx=1, col_idx=0, is_row_header=True),
            create_table_cell("   ", row_idx=1, col_idx=1, is_col_header=False),  # Whitespace
            create_table_cell("100", row_idx=1, col_idx=2, is_col_header=False),
        ]

        rows = _extract_entity_cols_metric_rows(
            table_cells=table_cells,
            num_rows=2,
            num_cols=3,
            metadata={},
            document_id="test_doc",
            page_number=1,
            table_index=1,
            table_item=mock_table_item,
            result=mock_result,
        )

        # Should skip whitespace-only cells
        assert len(rows) == 1
        assert rows[0]["value"] == 100.0

    def test_all_layouts_preserve_table_caption(self, mock_table_item, mock_result):
        """Test that all layouts preserve table_caption field."""
        mock_table_item.caption = "Test Caption FY2024"

        table_cells = [
            create_table_cell("Q1", row_idx=0, col_idx=0, is_col_header=True),
            create_table_cell("Revenue", row_idx=1, col_idx=0, is_row_header=True),
            create_table_cell("100", row_idx=1, col_idx=1, is_col_header=False),
        ]

        # Test temporal layout
        rows = _extract_temporal_cols_metric_rows(
            table_cells, 2, 2, {}, "doc", 1, 1, mock_table_item, mock_result
        )
        assert rows[0]["table_caption"] == "Test Caption FY2024"

        # Test entity layout
        rows = _extract_entity_cols_metric_rows(
            table_cells, 2, 2, {}, "doc", 1, 1, mock_table_item, mock_result
        )
        assert rows[0]["table_caption"] == "Test Caption FY2024"

    def test_all_layouts_include_chunk_text(self, mock_table_item, mock_result):
        """Test that all layouts include chunk_text from markdown."""
        table_cells = [
            create_table_cell("Q1", row_idx=0, col_idx=0, is_col_header=True),
            create_table_cell("Revenue", row_idx=1, col_idx=0, is_row_header=True),
            create_table_cell("100", row_idx=1, col_idx=1, is_col_header=False),
        ]

        # Test temporal layout
        rows = _extract_temporal_cols_metric_rows(
            table_cells, 2, 2, {}, "doc", 1, 1, mock_table_item, mock_result
        )
        assert "chunk_text" in rows[0]
        assert len(rows[0]["chunk_text"]) <= 500  # Truncated to 500 chars

        # Test entity layout
        rows = _extract_entity_cols_metric_rows(
            table_cells, 2, 2, {}, "doc", 1, 1, mock_table_item, mock_result
        )
        assert "chunk_text" in rows[0]

        # Test transposed layout
        rows = _extract_transposed_entity_cols_metric_row_labels(
            table_cells, 2, 2, {}, "doc", 1, 1, mock_table_item, mock_result
        )
        assert "chunk_text" in rows[0]
