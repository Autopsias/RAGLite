"""Unit tests for standard table layout extraction functions.

Continuation of tests.
"""

from raglite.ingestion.adaptive_table.standard_layouts import (
    _extract_entity_cols_metric_rows,
    _extract_temporal_cols_metric_rows,
    _extract_transposed_entity_cols_metric_row_labels,
)
from tests.unit.ingestion.conftest import create_table_cell


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
