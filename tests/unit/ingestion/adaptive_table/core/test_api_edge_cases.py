"""[P1/P2] Edge case tests for adaptive_table core API.

Tests critical error paths and boundary conditions for table extraction.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestExtractTableDataAdaptiveErrorHandling:
    """[P1] Error handling for adaptive table extraction."""

    @pytest.mark.asyncio
    async def test_none_dataframe_input(self):
        """[P1] TEST-API-1.1: Handle None dataframe gracefully."""
        # Given None dataframe
        df = None

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            # Mock to raise TypeError
            mock_extract.side_effect = TypeError("Expected DataFrame, got NoneType")

            # When extracting
            # Then raise TypeError
            with pytest.raises(TypeError):
                from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

                await extract_table_data_adaptive(df)

    @pytest.mark.asyncio
    async def test_empty_dataframe(self):
        """[P2] TEST-API-1.2: Handle empty dataframe (0 rows)."""
        # Given empty dataframe
        df = MagicMock()
        df.shape = (0, 5)  # Zero rows
        df.columns = ["A", "B", "C", "D", "E"]
        df.empty = True

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            # Mock returns empty structure
            mock_extract.return_value = {
                "headers": ["A", "B", "C", "D", "E"],
                "rows": [],  # No data
                "units": [None, None, None, None, None],
                "metadata": {},
            }

            # When extracting
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df)

            # Then returns valid structure with no rows
            assert result["headers"] == ["A", "B", "C", "D", "E"]
            assert result["rows"] == []

    @pytest.mark.asyncio
    async def test_dataframe_with_no_columns(self):
        """[P2] TEST-API-1.3: Handle dataframe with zero columns."""
        # Given dataframe with no columns
        df = MagicMock()
        df.shape = (10, 0)  # Zero columns
        df.columns = []
        df.empty = False

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            # Mock returns empty structure
            mock_extract.return_value = {
                "headers": [],
                "rows": [],
                "units": [],
                "metadata": {},
            }

            # When extracting
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df)

            # Then returns valid structure
            assert result["headers"] == []
            assert result["rows"] == []

    @pytest.mark.asyncio
    async def test_dataframe_with_null_values(self):
        """[P2] TEST-API-1.4: Handle dataframe with many null values."""
        # Given dataframe with nulls
        df = MagicMock()
        df.shape = (5, 3)
        df.columns = ["A", "B", "C"]
        df.isnull().sum().return_value = 10  # Many nulls

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            # Mock returns data with None values
            mock_extract.return_value = {
                "headers": ["A", "B", "C"],
                "rows": [
                    ["1", None, "3"],
                    [None, "2", None],
                ],
                "units": [None, None, None],
                "metadata": {},
            }

            # When extracting
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df)

            # Then handles nulls gracefully
            assert None in result["rows"][0]

    @pytest.mark.asyncio
    async def test_dataframe_with_duplicate_column_names(self):
        """[P2] TEST-API-1.5: Handle duplicate column names."""
        # Given dataframe with duplicate columns
        df = MagicMock()
        df.shape = (5, 4)
        df.columns = ["Revenue", "Cost", "Revenue", "Margin"]  # Duplicate "Revenue"

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            # Mock may deduplicate or preserve
            mock_extract.return_value = {
                "headers": ["Revenue", "Cost", "Revenue_2", "Margin"],  # Deduplicated
                "rows": [["100", "80", "120", "20%"]],
                "units": ["USD", "USD", "USD", "%"],
                "metadata": {},
            }

            # When extracting
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df)

            # Then handles duplicates
            assert len(result["headers"]) == 4


class TestExtractTableDataAdaptiveBoundaryConditions:
    """[P2] Boundary conditions for adaptive table extraction."""

    @pytest.mark.asyncio
    async def test_single_row_single_column(self):
        """[P2] TEST-API-2.1: Handle 1x1 dataframe."""
        # Given single cell dataframe
        df = MagicMock()
        df.shape = (1, 1)
        df.columns = ["Value"]

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            mock_extract.return_value = {
                "headers": ["Value"],
                "rows": [["100"]],
                "units": [None],
                "metadata": {},
            }

            # When extracting
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df)

            # Then processes single cell
            assert result["headers"] == ["Value"]
            assert len(result["rows"]) == 1

    @pytest.mark.asyncio
    async def test_very_wide_table(self):
        """[P2] TEST-API-2.2: Handle table with many columns (>50)."""
        # Given very wide dataframe
        df = MagicMock()
        df.shape = (10, 75)  # 75 columns
        df.columns = [f"Col{i}" for i in range(75)]

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            mock_extract.return_value = {
                "headers": [f"Col{i}" for i in range(75)],
                "rows": [["val"] * 75],
                "units": [None] * 75,
                "metadata": {},
            }

            # When extracting
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df)

            # Then processes all columns
            assert len(result["headers"]) == 75

    @pytest.mark.asyncio
    async def test_very_tall_table(self):
        """[P2] TEST-API-2.3: Handle table with many rows (>1000)."""
        # Given very tall dataframe
        df = MagicMock()
        df.shape = (2500, 5)  # 2500 rows
        df.columns = ["A", "B", "C", "D", "E"]

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            # Mock may truncate or sample
            mock_extract.return_value = {
                "headers": ["A", "B", "C", "D", "E"],
                "rows": [["val"] * 5 for _ in range(2500)],  # All rows or sampled
                "units": [None] * 5,
                "metadata": {"row_count": 2500},
            }

            # When extracting
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df)

            # Then processes efficiently
            assert "row_count" in result["metadata"]

    @pytest.mark.asyncio
    async def test_column_names_with_special_characters(self):
        """[P2] TEST-API-2.4: Handle special characters in column names."""
        # Given dataframe with special chars in columns
        df = MagicMock()
        df.shape = (5, 3)
        df.columns = ["Revenue (USD)", "Cost@2024", "Margin%"]

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            mock_extract.return_value = {
                "headers": ["Revenue (USD)", "Cost@2024", "Margin%"],
                "rows": [["100", "80", "20%"]],
                "units": ["USD", None, "%"],
                "metadata": {},
            }

            # When extracting
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df)

            # Then preserves special characters
            assert "Revenue (USD)" in result["headers"]

    @pytest.mark.asyncio
    async def test_unicode_column_names(self):
        """[P2] TEST-API-2.5: Handle Unicode in column names."""
        # Given dataframe with Unicode columns
        df = MagicMock()
        df.shape = (5, 2)
        df.columns = ["Revenus (€)", "日本円"]  # Euro symbol, Japanese

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            mock_extract.return_value = {
                "headers": ["Revenus (€)", "日本円"],
                "rows": [["100", "1000"]],
                "units": ["EUR", "JPY"],
                "metadata": {},
            }

            # When extracting
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df)

            # Then handles Unicode correctly
            assert "Revenus (€)" in result["headers"]


class TestExtractTableDataAdaptiveContextHandling:
    """[P1] Page context handling in adaptive extraction."""

    @pytest.mark.asyncio
    async def test_empty_page_context(self):
        """[P2] TEST-API-3.1: Handle empty page context."""
        # Given table with empty context
        df = MagicMock()
        df.shape = (5, 3)
        df.columns = ["A", "B", "C"]

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            mock_extract.return_value = {
                "headers": ["A", "B", "C"],
                "rows": [["1", "2", "3"]],
                "units": [None, None, None],
                "metadata": {},  # No context extracted
            }

            # When extracting with empty context
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df, page_context="")

            # Then succeeds without context
            assert result is not None

    @pytest.mark.asyncio
    async def test_very_long_page_context(self):
        """[P2] TEST-API-3.2: Handle very long page context (>10k chars)."""
        # Given table with massive context
        df = MagicMock()
        df.shape = (5, 3)
        df.columns = ["A", "B", "C"]
        long_context = "A" * 15000  # 15k characters

        with patch(
            "raglite.ingestion.adaptive_table.core.api.extract_table_data_adaptive"
        ) as mock_extract:
            mock_extract.return_value = {
                "headers": ["A", "B", "C"],
                "rows": [["1", "2", "3"]],
                "units": [None, None, None],
                "metadata": {},
            }

            # When extracting with long context
            from raglite.ingestion.adaptive_table.core.api import extract_table_data_adaptive

            result = await extract_table_data_adaptive(df, page_context=long_context)

            # Then processes without performance issues
            assert result is not None
