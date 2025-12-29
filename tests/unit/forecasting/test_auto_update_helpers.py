"""Unit tests for Story 4.3: Automated Forecast Updates - MCP Helper.

Tests the _perform_forecast_refresh helper function from mcp.tools.ingestion.
"""

from unittest.mock import AsyncMock, patch

import pytest

from raglite.mcp.tools import ingestion as ingestion_module
from raglite.shared.models import DocumentMetadata, ForecastRefreshResult, IngestionResult


class TestPerformForecastRefresh:
    """Tests for the _perform_forecast_refresh helper in mcp.tools.ingestion."""

    @pytest.mark.asyncio
    async def test_auto_forecast_disabled(self):
        """Test when auto_forecast parameter is False."""
        from raglite.main import _perform_forecast_refresh

        metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=10,
            source_path="/data/Report.pdf",
            chunk_count=30,
        )

        result = await _perform_forecast_refresh(metadata, auto_forecast=False)

        assert isinstance(result, IngestionResult)
        assert result.forecasts_updated is None
        assert result.forecast_refresh_skipped_reason == "auto_forecast=False"

    @pytest.mark.asyncio
    async def test_settings_disabled(self):
        """Test when forecast auto update is disabled in settings."""
        from raglite.main import _perform_forecast_refresh

        metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=10,
            source_path="/data/Report.pdf",
            chunk_count=30,
        )

        with patch.object(ingestion_module, "settings") as mock_settings:
            mock_settings.enable_forecast_auto_update = False
            result = await _perform_forecast_refresh(metadata, auto_forecast=True)

        assert result.forecasts_updated is None
        assert "disabled" in result.forecast_refresh_skipped_reason

    @pytest.mark.asyncio
    async def test_successful_forecast_refresh(self):
        """Test successful forecast refresh through helper."""
        from raglite.main import _perform_forecast_refresh

        metadata = DocumentMetadata(
            filename="Q3_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=40,
            source_path="/data/Q3_Report.pdf",
            chunk_count=120,
        )

        mock_refresh_result = ForecastRefreshResult(
            document_id="Q3_Report.pdf",
            metrics_refreshed=["revenue"],
            metrics_skipped=[],
            refresh_duration_ms=1500,
            success=True,
        )

        with (
            patch.object(ingestion_module, "settings") as mock_settings,
            patch.object(
                ingestion_module,
                "trigger_forecast_refresh",
                new_callable=AsyncMock,
                return_value=mock_refresh_result,
            ),
        ):
            mock_settings.enable_forecast_auto_update = True
            mock_settings.forecast_refresh_timeout = 300
            result = await _perform_forecast_refresh(metadata, auto_forecast=True)

        assert result.forecasts_updated == ["revenue"]
        assert result.forecast_refresh_skipped_reason is None

    @pytest.mark.asyncio
    async def test_forecast_refresh_failure(self):
        """Test when forecast refresh fails."""
        from raglite.main import _perform_forecast_refresh

        metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=10,
            source_path="/data/Report.pdf",
            chunk_count=30,
        )

        mock_refresh_result = ForecastRefreshResult(
            document_id="Report.pdf",
            metrics_refreshed=[],
            metrics_skipped=[],
            refresh_duration_ms=5000,
            success=False,
            error_message="Forecast refresh timed out",
        )

        with (
            patch.object(ingestion_module, "settings") as mock_settings,
            patch.object(
                ingestion_module,
                "trigger_forecast_refresh",
                new_callable=AsyncMock,
                return_value=mock_refresh_result,
            ),
        ):
            mock_settings.enable_forecast_auto_update = True
            mock_settings.forecast_refresh_timeout = 300
            result = await _perform_forecast_refresh(metadata, auto_forecast=True)

        assert result.forecasts_updated is None
        assert "timed out" in result.forecast_refresh_skipped_reason

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self):
        """Test that unexpected exceptions are handled gracefully."""
        from raglite.main import _perform_forecast_refresh

        metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=10,
            source_path="/data/Report.pdf",
            chunk_count=30,
        )

        with (
            patch.object(ingestion_module, "settings") as mock_settings,
            patch.object(
                ingestion_module,
                "trigger_forecast_refresh",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Unexpected crash"),
            ),
        ):
            mock_settings.enable_forecast_auto_update = True
            mock_settings.forecast_refresh_timeout = 300
            result = await _perform_forecast_refresh(metadata, auto_forecast=True)

        # Should not raise, should gracefully handle
        assert result.forecasts_updated is None
        assert "RuntimeError" in result.forecast_refresh_skipped_reason
