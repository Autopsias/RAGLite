"""Unit tests for raglite/ingestion/adaptive_table/unit_inference.py.

Tests cover:
1. Unit pattern extraction from table cells
2. Statistical unit detection logic
3. Value/unit parsing from cell text
4. Column-level unit inference
5. Context-aware unit inference (mocked LLM)
6. Async batch unit inference
7. Edge cases: mixed units, invalid data, missing units

All tests use mocks to avoid external dependencies (Mistral API, Docling).
"""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from raglite.ingestion.adaptive_table.unit_inference import (
    _apply_context_aware_unit_inference,
    _apply_context_aware_unit_inference_async,
    _detect_unit_column_statistical,
    _extract_units_entity_column_junk,
    _extract_units_normal,
    _infer_unit_from_context,
    _infer_unit_from_context_async,
    _infer_units_batch_async,
    _parse_value_unit,
)


@pytest.mark.unit
class TestUnitPatternExtraction:
    """Test unit extraction from table structures."""

    def test_extract_units_normal_dedicated_row(self) -> None:
        """Test extraction from dedicated unit row (row 1)."""
        # Mock table cells with unit row at index 1
        cells = [
            Mock(start_row_offset_idx=0, start_col_offset_idx=0, text="Metric"),
            Mock(start_row_offset_idx=0, start_col_offset_idx=1, text="GROUP"),
            Mock(start_row_offset_idx=1, start_col_offset_idx=0, text="Unit"),
            Mock(start_row_offset_idx=1, start_col_offset_idx=1, text="EUR"),
            Mock(start_row_offset_idx=1, start_col_offset_idx=2, text="EUR"),
            Mock(start_row_offset_idx=2, start_col_offset_idx=0, text="Revenue"),
            Mock(start_row_offset_idx=2, start_col_offset_idx=1, text="100M"),
        ]
        unit_patterns = ["EUR", "USD", "ton"]

        result = _extract_units_normal(cells, unit_patterns)

        # Should extract units from column indices
        assert 1 in result
        assert result[1] == "EUR"

    def test_extract_units_normal_metric_names(self) -> None:
        """Test extraction from metric names with units in parentheses."""
        cells = [
            Mock(
                start_row_offset_idx=0,
                start_col_offset_idx=0,
                text="Revenue (EUR million)",
                column_header=False,
            ),
            Mock(
                start_row_offset_idx=1,
                start_col_offset_idx=0,
                text="EBITDA (Meur)",
                column_header=False,
            ),
            Mock(
                start_row_offset_idx=2,
                start_col_offset_idx=0,
                text="Cost (EUR/ton)",
                column_header=False,
            ),
        ]
        unit_patterns = ["EUR", "Meur", "EUR/ton"]

        result = _extract_units_normal(cells, unit_patterns)

        # Function extracts from row headers (column 0) that match patterns
        assert 0 in result
        assert "EUR million" in result[0]
        # Note: Row 1 "Meur" pattern IS matched and extracted
        # Note: Row 2 "EUR/ton" pattern IS matched and extracted
        assert len(result) >= 1  # At least Revenue extracted

    def test_extract_units_junk_column_headers(self) -> None:
        """Test extraction from Type B tables (junk column 0)."""
        cells = [
            Mock(
                start_col_offset_idx=2,
                column_header=True,
                text="CAPEX (EUR million)",
            ),
            Mock(
                start_col_offset_idx=3,
                column_header=True,
                text="Production (kton)",
            ),
        ]
        unit_patterns = ["EUR", "kton"]

        result = _extract_units_entity_column_junk(cells, unit_patterns)

        assert 2 in result
        assert result[2] == "EUR million"
        assert 3 in result
        assert result[3] == "kton"


@pytest.mark.unit
class TestStatisticalUnitDetection:
    """Test statistical unit detection logic."""

    def test_detect_unit_column_above_threshold(self) -> None:
        """Test detection when unit ratio exceeds threshold."""
        cells = [
            Mock(text="EUR"),
            Mock(text="EUR"),
            Mock(text="USD"),
            Mock(text="EUR"),
        ]
        unit_patterns = ["EUR", "USD", "ton"]

        has_units, confidence = _detect_unit_column_statistical(
            cells, unit_patterns, threshold=0.60
        )

        assert has_units is True
        assert confidence == 1.0  # 4/4 cells match

    def test_detect_unit_column_below_threshold(self) -> None:
        """Test detection when unit ratio below threshold."""
        cells = [
            Mock(text="100", start_row_offset_idx=1),
            Mock(text="EUR", start_row_offset_idx=2),
            Mock(text="200", start_row_offset_idx=3),
            Mock(text="300", start_row_offset_idx=4),
        ]
        unit_patterns = ["EUR", "USD"]

        has_units, confidence = _detect_unit_column_statistical(
            cells, unit_patterns, threshold=0.60
        )

        assert has_units is False
        assert confidence == 0.25  # 1/4 cells match

    def test_detect_unit_column_middle_section_concentration(self) -> None:
        """Test middle section concentration strategy (rows 3-10)."""
        # Cells in middle section (rows 3-10) with high unit density
        cells = [
            Mock(text="100", start_row_offset_idx=0),
            Mock(text="EUR", start_row_offset_idx=5),
            Mock(text="EUR", start_row_offset_idx=6),
            Mock(text="USD", start_row_offset_idx=7),
        ]
        unit_patterns = ["EUR", "USD"]

        has_units, confidence = _detect_unit_column_statistical(
            cells, unit_patterns, threshold=0.60
        )

        # Should detect based on middle section (75% in rows 3-10)
        assert has_units is True
        assert 0.50 <= confidence <= 0.80

    def test_detect_unit_column_extended_patterns(self) -> None:
        """Test detection with extended unit patterns."""
        cells = [
            Mock(text="million", start_row_offset_idx=1),
            Mock(text="people", start_row_offset_idx=2),
            Mock(text="ratio", start_row_offset_idx=3),
            Mock(text="value", start_row_offset_idx=4),
        ]
        unit_patterns = ["EUR"]

        has_units, confidence = _detect_unit_column_statistical(
            cells, unit_patterns, threshold=0.60
        )

        # Should detect via extended patterns
        assert has_units is True
        assert 0.30 <= confidence <= 0.60

    def test_detect_unit_column_insufficient_samples(self) -> None:
        """Test handling of insufficient sample size."""
        cells = [Mock(text="EUR"), Mock(text="")]
        unit_patterns = ["EUR"]

        has_units, confidence = _detect_unit_column_statistical(cells, unit_patterns, min_samples=3)

        assert has_units is False
        assert confidence == 0.0


@pytest.mark.unit
class TestValueUnitParsing:
    """Test parsing numeric values and units from cell text."""

    def test_parse_value_unit_with_unit(self) -> None:
        """Test parsing value with unit suffix."""
        value, unit = _parse_value_unit("123.45 EUR")

        assert value == 123.45
        assert unit == "EUR"

    def test_parse_value_unit_no_unit(self) -> None:
        """Test parsing value without unit."""
        value, unit = _parse_value_unit("987.65")

        assert value == 987.65
        assert unit is None

    def test_parse_value_unit_negative_value(self) -> None:
        """Test parsing negative value."""
        value, unit = _parse_value_unit("-250.00 kton")

        assert value == -250.00
        assert unit == "kton"

    def test_parse_value_unit_invalid_text(self) -> None:
        """Test parsing invalid text."""
        value, unit = _parse_value_unit("not a number")

        assert value is None
        assert unit is None

    def test_parse_value_unit_empty_text(self) -> None:
        """Test parsing empty text."""
        value, unit = _parse_value_unit("")

        assert value is None
        assert unit is None


@pytest.mark.unit
class TestContextAwareInference:
    """Test LLM-based context-aware unit inference (with mocks)."""

    def test_infer_unit_no_api_key(self) -> None:
        """Test inference skips when Mistral API key not configured."""
        with patch("raglite.shared.config.settings") as mock_settings:
            mock_settings.mistral_api_key = None

            result = _infer_unit_from_context(
                metric="EBITDA",
                entity="GROUP",
                table_caption="Financial Results",
                section_heading="Consolidated Results (EUR Million)",
                page_title=None,
                nearby_text=None,
            )

        assert result is None

    def test_infer_unit_from_context_success(self) -> None:
        """Test successful unit inference from context."""
        with patch("raglite.shared.config.settings") as mock_settings:
            mock_settings.mistral_api_key = "test-key"
            mock_settings.metadata_extraction_model = "mistral-small-latest"

            with patch("raglite.shared.clients.get_mistral_client") as mock_get_client:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message = Mock()
                mock_response.choices[0].message.content = "Meur"
                mock_client.chat.complete.return_value = mock_response
                mock_get_client.return_value = mock_client

                result = _infer_unit_from_context(
                    metric="EBITDA IFRS",
                    entity="GROUP",
                    table_caption="Consolidated Results",
                    section_heading="Financial Results (EUR Million)",
                    page_title="Q3 2025 Report",
                    nearby_text=["All values in EUR million"],
                )

        assert result == "Meur"

    def test_infer_unit_from_context_unknown(self) -> None:
        """Test inference returns None when LLM cannot determine unit."""
        with patch("raglite.shared.config.settings") as mock_settings:
            mock_settings.mistral_api_key = "test-key"
            mock_settings.metadata_extraction_model = "mistral-small-latest"

            with patch("raglite.shared.clients.get_mistral_client") as mock_get_client:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message = Mock()
                mock_response.choices[0].message.content = "UNKNOWN"
                mock_client.chat.complete.return_value = mock_response
                mock_get_client.return_value = mock_client

                result = _infer_unit_from_context(
                    metric="Unknown Metric",
                    entity=None,
                    table_caption=None,
                    section_heading=None,
                    page_title=None,
                    nearby_text=None,
                )

        assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
class TestAsyncUnitInference:
    """Test async unit inference with rate limiting."""

    async def test_infer_unit_async_success(self) -> None:
        """Test async unit inference with successful response."""
        with patch("raglite.shared.config.settings") as mock_settings:
            mock_settings.mistral_api_key = "test-key"
            mock_settings.metadata_extraction_model = "mistral-small-latest"

            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Eur/ton"

            mock_client.chat.complete_async = AsyncMock(return_value=mock_response)

            result = await _infer_unit_from_context_async(
                metric="Cost per ton",
                entity="PORTUGAL",
                table_caption="Production Costs",
                section_heading="Cost Analysis (EUR/ton)",
                page_title=None,
                nearby_text=None,
                client=mock_client,
            )

        assert result == "Eur/ton"

    async def test_infer_unit_async_timeout(self) -> None:
        """Test async inference handles timeout gracefully."""
        with patch("raglite.shared.config.settings") as mock_settings:
            mock_settings.mistral_api_key = "test-key"

            mock_client = Mock()
            mock_client.chat.complete_async = AsyncMock(side_effect=TimeoutError())

            result = await _infer_unit_from_context_async(
                metric="EBITDA",
                entity="GROUP",
                table_caption=None,
                section_heading=None,
                page_title=None,
                nearby_text=None,
                client=mock_client,
            )

        assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
class TestBatchAsyncInference:
    """Test batch async unit inference for performance."""

    async def test_batch_inference_success(self) -> None:
        """Test batch inference processes multiple rows."""
        with patch("raglite.shared.config.settings") as mock_settings:
            mock_settings.mistral_api_key = "test-key"
            mock_settings.metadata_extraction_model = "mistral-small-latest"

            rows_batch = [
                (0, {"metric": "EBITDA", "entity": "GROUP"}),
                (1, {"metric": "Revenue", "entity": "PORTUGAL"}),
            ]

            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[
                0
            ].message.content = '[{"index": 0, "unit": "Meur"}, {"index": 1, "unit": "Meur"}]'
            mock_client.chat.complete_async = AsyncMock(return_value=mock_response)

            results = await _infer_units_batch_async(
                rows_batch,
                table_caption="Financial Results",
                section_heading="Consolidated (EUR Million)",
                page_title=None,
                nearby_text=None,
                client=mock_client,
            )

        assert len(results) == 2
        assert results[0] == (0, {"metric": "EBITDA", "entity": "GROUP"}, "Meur")
        assert results[1] == (1, {"metric": "Revenue", "entity": "PORTUGAL"}, "Meur")

    async def test_batch_inference_json_decode_error(self) -> None:
        """Test batch inference handles malformed JSON."""
        with patch("raglite.shared.config.settings") as mock_settings:
            mock_settings.mistral_api_key = "test-key"
            mock_settings.metadata_extraction_model = "mistral-small-latest"

            rows_batch = [(0, {"metric": "EBITDA"})]

            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Invalid JSON"
            mock_client.chat.complete_async = AsyncMock(return_value=mock_response)

            results = await _infer_units_batch_async(
                rows_batch,
                table_caption=None,
                section_heading=None,
                page_title=None,
                nearby_text=None,
                client=mock_client,
            )

        assert len(results) == 1
        assert results[0][2] is None


@pytest.mark.unit
class TestApplyUnitInference:
    """Test applying unit inference to row data."""

    def test_apply_inference_with_cache(self) -> None:
        """Test unit inference uses cache for same metric."""
        rows = [
            {"metric": "EBITDA", "entity": "GROUP", "value": 100, "unit": None},
            {"metric": "EBITDA", "entity": "PORTUGAL", "value": 50, "unit": None},
        ]

        mock_table_item = Mock()
        mock_result = Mock()

        with patch("raglite.ingestion.adaptive_table.core._extract_page_context") as mock_context:
            mock_context.return_value = {
                "section_heading": "Results (EUR Million)",
                "page_title": None,
                "nearby_text": [],
            }

            with patch("raglite.ingestion.adaptive_table.core._get_table_caption") as mock_caption:
                mock_caption.return_value = "Financial Results"

                with patch(
                    "raglite.ingestion.adaptive_table.unit_inference._infer_unit_from_context"
                ) as mock_infer:
                    mock_infer.return_value = "Meur"

                    result = _apply_context_aware_unit_inference(rows, mock_table_item, mock_result)

        assert result[0]["unit"] == "Meur"
        assert result[1]["unit"] == "Meur"
        assert result[1]["unit_source"] == "cached_inference"
        assert mock_infer.call_count == 1

    def test_apply_inference_skips_explicit_units(self) -> None:
        """Test inference skips rows with existing units."""
        rows = [
            {"metric": "Revenue", "entity": "GROUP", "value": 100, "unit": "EUR"},
            {"metric": "EBITDA", "entity": "GROUP", "value": 50, "unit": None},
        ]

        mock_table_item = Mock()
        mock_result = Mock()

        with patch("raglite.ingestion.adaptive_table.core._extract_page_context") as mock_context:
            mock_context.return_value = {}

            with patch("raglite.ingestion.adaptive_table.core._get_table_caption"):
                with patch(
                    "raglite.ingestion.adaptive_table.unit_inference._infer_unit_from_context"
                ) as mock_infer:
                    mock_infer.return_value = "Meur"

                    result = _apply_context_aware_unit_inference(rows, mock_table_item, mock_result)

        assert result[0]["unit"] == "EUR"
        assert result[1]["unit"] == "Meur"


@pytest.mark.asyncio
@pytest.mark.unit
class TestApplyAsyncBatchInference:
    """Test async batch inference application."""

    async def test_async_inference_batch_processing(self) -> None:
        """Test async inference groups rows into batches."""
        rows = [
            {"metric": f"Metric_{i}", "entity": "GROUP", "value": i, "unit": None}
            for i in range(25)
        ]

        mock_table_item = Mock()
        mock_result = Mock()

        with patch("raglite.shared.config.settings") as mock_settings:
            mock_settings.mistral_api_key = "test-key"

            with patch(
                "raglite.ingestion.adaptive_table.core._extract_page_context"
            ) as mock_context:
                mock_context.return_value = {}

                with patch("raglite.ingestion.adaptive_table.core._get_table_caption"):
                    with patch("raglite.shared.clients.get_mistral_client") as mock_get_client:
                        mock_client = Mock()
                        mock_get_client.return_value = mock_client

                        def batch_response(*args: Any, **kwargs: Any) -> Any:
                            rows_batch = args[0]
                            return [(idx, row, "Meur") for idx, row in rows_batch]

                        with patch(
                            "raglite.ingestion.adaptive_table.unit_inference._infer_units_batch_async"
                        ) as mock_batch:
                            mock_batch.side_effect = batch_response

                            result = await _apply_context_aware_unit_inference_async(
                                rows, mock_table_item, mock_result
                            )

        assert all(row["unit"] == "Meur" for row in result)
        assert mock_batch.call_count == 2

    async def test_async_inference_no_api_key(self) -> None:
        """Test async inference skips when API key not configured."""
        rows = [{"metric": "EBITDA", "value": 100, "unit": None}]

        mock_table_item = Mock()
        mock_result = Mock()

        with patch("raglite.shared.config.settings") as mock_settings:
            mock_settings.mistral_api_key = None

            result = await _apply_context_aware_unit_inference_async(
                rows, mock_table_item, mock_result
            )

        assert result[0]["unit"] is None
