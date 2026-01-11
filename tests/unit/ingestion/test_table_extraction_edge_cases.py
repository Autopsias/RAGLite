"""[P2] Edge case testing for table extraction and parsing.

Story 8.4a-2 Phase 6: Test automation expansion.
Tests edge cases in table detection, parsing, and error scenarios.

DEPRECATED: Functions detect_tables, parse_table, infer_column_types, split_table_for_chunking
were removed in Story 8.3 refactoring. These were internal implementation details
replaced by the extract_table_data_adaptive API.
"""

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skip(
        reason="Internal functions removed in Story 8.3 - replaced by extract_table_data_adaptive API"
    ),
]


# =============================================================================
# Table Detection Edge Cases - DEPRECATED
# =============================================================================


class TestTableDetectionEdgeCases:
    """[P2] DEPRECATED: These functions were removed in Story 8.3 refactoring."""

    def test_empty_table_detection(self):
        """[P2] DEPRECATED: detect_tables was internal implementation, removed."""
        pytest.skip("Function removed in Story 8.3 - internal API")

    def test_table_with_only_headers(self):
        """[P2] DEPRECATED: detect_tables was internal implementation, removed."""
        pytest.skip("Function removed in Story 8.3 - internal API")

    def test_nested_tables_detection(self):
        """[P2] Test detection of nested tables (table within table)."""
        nested_html = """
        <table>
            <tr>
                <td>Outer Cell 1</td>
                <td>
                    <table>
                        <tr><td>Inner Cell 1</td><td>Inner Cell 2</td></tr>
                    </table>
                </td>
            </tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import detect_tables

        # Should handle nested tables gracefully
        result = detect_tables(nested_html)
        assert isinstance(result, list)

    def test_malformed_table_html(self):
        """[P2] Test handling of malformed table HTML."""
        malformed_html = """
        <table>
            <tr><td>Cell 1</td><td>Cell 2
            <tr><td>Cell 3</td>
        </table
        """

        from raglite.ingestion.adaptive_table.core import detect_tables

        # Should handle gracefully (HTML parser is lenient)
        try:
            result = detect_tables(malformed_html)
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"Should handle malformed HTML gracefully: {e}")


# =============================================================================
# Table Parsing Edge Cases
# =============================================================================


class TestTableParsingEdgeCases:
    """[P2] Test edge cases in table parsing logic."""

    def test_parse_table_with_merged_cells(self):
        """[P2] Test parsing tables with rowspan/colspan."""
        merged_html = """
        <table>
            <tr>
                <td rowspan="2">Merged Row</td>
                <td>Cell 1</td>
            </tr>
            <tr>
                <td>Cell 2</td>
            </tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import parse_table

        # Should handle merged cells
        result = parse_table(merged_html)
        assert result is not None

    def test_parse_table_with_unicode_content(self):
        """[P2] Test parsing tables with Unicode characters."""
        unicode_html = """
        <table>
            <tr><td>Ä€£¥</td><td>中文</td><td>🚀</td></tr>
            <tr><td>Émoji</td><td>Ñoño</td><td>Ω</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import parse_table

        # Should handle Unicode correctly
        result = parse_table(unicode_html)
        assert result is not None

    def test_parse_table_with_special_characters(self):
        """[P2] Test parsing tables with special characters."""
        special_html = """
        <table>
            <tr><td>&lt;script&gt;</td><td>&amp;</td><td>&quot;</td></tr>
            <tr><td>100% &nbsp; value</td><td>a &gt; b</td><td>x &lt; y</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import parse_table

        # Should decode HTML entities correctly
        result = parse_table(special_html)
        assert result is not None

    def test_parse_table_with_whitespace_only_cells(self):
        """[P2] Test parsing tables with whitespace-only cells."""
        whitespace_html = """
        <table>
            <tr><td>   </td><td>\t\t</td><td>\n\n</td></tr>
            <tr><td>Valid</td><td>   </td><td>Data</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import parse_table

        # Should trim whitespace correctly
        result = parse_table(whitespace_html)
        assert result is not None


# =============================================================================
# Table Structure Edge Cases
# =============================================================================


class TestTableStructureEdgeCases:
    """[P2] Test edge cases in table structure validation."""

    def test_single_column_table(self):
        """[P2] Test table with only one column."""
        single_column_html = """
        <table>
            <tr><th>Only Column</th></tr>
            <tr><td>Row 1</td></tr>
            <tr><td>Row 2</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import parse_table

        # Should handle single-column tables
        result = parse_table(single_column_html)
        assert result is not None

    def test_single_row_table(self):
        """[P2] Test table with only one row."""
        single_row_html = """
        <table>
            <tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import parse_table

        # Should handle single-row tables
        result = parse_table(single_row_html)
        assert result is not None

    def test_irregular_row_lengths(self):
        """[P2] Test table where rows have different number of cells."""
        irregular_html = """
        <table>
            <tr><td>A</td><td>B</td><td>C</td></tr>
            <tr><td>1</td><td>2</td></tr>
            <tr><td>X</td><td>Y</td><td>Z</td><td>W</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import parse_table

        # Should normalize irregular rows
        result = parse_table(irregular_html)
        assert result is not None


# =============================================================================
# Error Path Testing
# =============================================================================


class TestTableExtractionErrors:
    """[P1] Test error handling in table extraction."""

    def test_none_input_to_detect_tables(self):
        """[P1] Test detect_tables with None input."""
        from raglite.ingestion.adaptive_table.core import detect_tables

        # Should handle None gracefully
        with pytest.raises((ValueError, TypeError, AttributeError)):
            detect_tables(None)

    def test_empty_string_input_to_detect_tables(self):
        """[P1] Test detect_tables with empty string."""
        from raglite.ingestion.adaptive_table.core import detect_tables

        # Should return empty list for empty input
        result = detect_tables("")
        assert result == [] or result is None

    def test_non_html_input_to_parse_table(self):
        """[P1] Test parse_table with non-HTML text."""
        from raglite.ingestion.adaptive_table.core import parse_table

        non_html = "This is plain text, not HTML"

        # Should handle gracefully (return None or empty result)
        result = parse_table(non_html)
        # Either None or empty structure is acceptable
        assert result is None or (isinstance(result, (list, dict)) and len(result) == 0)

    def test_very_large_table_parsing(self):
        """[P2] Test parsing of very large table (performance edge case)."""
        # Generate table with 1000 rows and 50 columns
        large_table_html = "<table>"
        large_table_html += "<tr>" + "".join(f"<th>Col{i}</th>" for i in range(50)) + "</tr>"
        for row in range(1000):
            large_table_html += (
                "<tr>" + "".join(f"<td>R{row}C{i}</td>" for i in range(50)) + "</tr>"
            )
        large_table_html += "</table>"

        from raglite.ingestion.adaptive_table.core import parse_table

        # Should complete within reasonable time (no timeout in test)
        result = parse_table(large_table_html)
        assert result is not None


# =============================================================================
# Data Type Inference Edge Cases
# =============================================================================


class TestDataTypeInference:
    """[P2] Test edge cases in data type inference for table cells."""

    def test_mixed_numeric_and_text_column(self):
        """[P2] Test column with mixed numeric and text values."""
        mixed_html = """
        <table>
            <tr><th>Mixed Column</th></tr>
            <tr><td>100</td></tr>
            <tr><td>Not a number</td></tr>
            <tr><td>200.5</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import infer_column_types

        # Should infer as text (mixed types)
        result = infer_column_types(mixed_html)
        assert isinstance(result, (list, dict))

    def test_date_like_strings(self):
        """[P2] Test detection of date-like strings."""
        date_html = """
        <table>
            <tr><th>Date Column</th></tr>
            <tr><td>2024-01-01</td></tr>
            <tr><td>2024-12-31</td></tr>
            <tr><td>2025-06-15</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import infer_column_types

        # Should detect as date type
        result = infer_column_types(date_html)
        assert isinstance(result, (list, dict))

    def test_percentage_values(self):
        """[P2] Test detection of percentage values (e.g., '25%')."""
        percentage_html = """
        <table>
            <tr><th>Percentage</th></tr>
            <tr><td>25%</td></tr>
            <tr><td>50.5%</td></tr>
            <tr><td>100%</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import infer_column_types

        # Should detect as numeric (strip % symbol)
        result = infer_column_types(percentage_html)
        assert isinstance(result, (list, dict))

    def test_currency_values(self):
        """[P2] Test detection of currency values (e.g., '$1,000.00')."""
        currency_html = """
        <table>
            <tr><th>Amount</th></tr>
            <tr><td>$1,000.00</td></tr>
            <tr><td>$250.50</td></tr>
            <tr><td>$10,500</td></tr>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import infer_column_types

        # Should detect as numeric (strip $ and commas)
        result = infer_column_types(currency_html)
        assert isinstance(result, (list, dict))


# =============================================================================
# Integration with Chunking
# =============================================================================


class TestTableChunkingIntegration:
    """[P2] Test integration between table extraction and chunking."""

    def test_large_table_splitting(self):
        """[P2] Test that large tables are split into chunks correctly."""
        # Generate large table (100 rows)
        large_table = "<table>"
        large_table += "<tr><th>ID</th><th>Name</th><th>Value</th></tr>"
        for i in range(100):
            large_table += f"<tr><td>{i}</td><td>Name{i}</td><td>{i * 100}</td></tr>"
        large_table += "</table>"

        from raglite.ingestion.adaptive_table.core import split_table_for_chunking

        # Should split into multiple chunks
        chunks = split_table_for_chunking(large_table, max_rows_per_chunk=20)
        assert len(chunks) > 1
        assert len(chunks) <= 5  # 100 rows / 20 rows per chunk = 5 chunks

    def test_table_header_preservation_in_chunks(self):
        """[P2] Test that table headers are preserved in all chunks."""
        table_html = """
        <table>
            <thead><tr><th>Column A</th><th>Column B</th></tr></thead>
            <tbody>
                <tr><td>1</td><td>A</td></tr>
                <tr><td>2</td><td>B</td></tr>
                <tr><td>3</td><td>C</td></tr>
            </tbody>
        </table>
        """

        from raglite.ingestion.adaptive_table.core import split_table_for_chunking

        chunks = split_table_for_chunking(table_html, max_rows_per_chunk=2)

        # Each chunk should contain the header
        for chunk in chunks:
            assert "Column A" in chunk
            assert "Column B" in chunk
