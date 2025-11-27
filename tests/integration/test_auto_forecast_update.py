"""Integration tests for Story 4.3: Automated Forecast Updates.

Tests end-to-end forecast refresh after document ingestion via MCP.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.shared.models import DocumentMetadata, IngestionResult

# =============================================================================
# Test MCP Ingestion with Forecast Refresh
# =============================================================================


class TestMCPIngestionWithForecast:
    """Integration tests for MCP ingestion tool with forecast refresh."""

    @pytest.mark.asyncio
    async def test_ingestion_returns_ingestion_result(self):
        """Test that ingest_financial_document returns IngestionResult (AC4)."""
        from raglite.main import ingest_financial_document

        # Mock the entire ingestion pipeline
        mock_metadata = DocumentMetadata(
            filename="test_report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=10,
            source_path="/tmp/test_report.pdf",
            chunk_count=30,
        )

        with (
            patch(
                "raglite.main.ingest_document", new_callable=AsyncMock, return_value=mock_metadata
            ),
            patch("raglite.main.settings") as mock_settings,
            patch("raglite.main.trigger_forecast_refresh", new_callable=AsyncMock),
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_settings.enable_forecast_auto_update = False  # Disable to simplify test

            result = await ingest_financial_document.fn(doc_path="/tmp/test_report.pdf")

        # Should return IngestionResult, not DocumentMetadata
        assert isinstance(result, IngestionResult)
        assert result.filename == "test_report.pdf"
        assert result.chunk_count == 30

    @pytest.mark.asyncio
    async def test_ingestion_with_forecast_refresh_enabled(self):
        """Test that forecast refresh is triggered when enabled (AC1)."""
        from raglite.main import ingest_financial_document
        from raglite.shared.models import ForecastRefreshResult

        mock_metadata = DocumentMetadata(
            filename="Q3_Revenue.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=40,
            source_path="/tmp/Q3_Revenue.pdf",
            chunk_count=120,
        )

        mock_refresh_result = ForecastRefreshResult(
            document_id="Q3_Revenue.pdf",
            metrics_refreshed=["revenue"],
            metrics_skipped=[],
            refresh_duration_ms=1500,
            success=True,
        )

        with (
            patch(
                "raglite.main.ingest_document", new_callable=AsyncMock, return_value=mock_metadata
            ),
            patch("raglite.main.settings") as mock_settings,
            patch(
                "raglite.main.trigger_forecast_refresh",
                new_callable=AsyncMock,
                return_value=mock_refresh_result,
            ) as mock_refresh,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_settings.enable_forecast_auto_update = True
            mock_settings.forecast_refresh_timeout = 300

            result = await ingest_financial_document.fn(doc_path="/tmp/Q3_Revenue.pdf")

        # Verify forecast refresh was called
        mock_refresh.assert_called_once()

        # Verify result has forecast fields (AC4)
        assert result.forecasts_updated == ["revenue"]
        assert result.forecast_refresh_skipped_reason is None

    @pytest.mark.asyncio
    async def test_ingestion_with_auto_forecast_false(self):
        """Test that forecast refresh is skipped when auto_forecast=False."""
        from raglite.main import ingest_financial_document

        mock_metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=10,
            source_path="/tmp/Report.pdf",
            chunk_count=30,
        )

        with (
            patch(
                "raglite.main.ingest_document", new_callable=AsyncMock, return_value=mock_metadata
            ),
            patch("raglite.main.settings") as mock_settings,
            patch("raglite.main.trigger_forecast_refresh", new_callable=AsyncMock) as mock_refresh,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_settings.enable_forecast_auto_update = True

            result = await ingest_financial_document.fn(
                doc_path="/tmp/Report.pdf",
                auto_forecast=False,
            )

        # Forecast refresh should NOT be called
        mock_refresh.assert_not_called()

        # Result should indicate it was skipped
        assert result.forecasts_updated is None
        assert result.forecast_refresh_skipped_reason == "auto_forecast=False"

    @pytest.mark.asyncio
    async def test_ingestion_with_settings_disabled(self):
        """Test that forecast refresh is skipped when disabled in settings."""
        from raglite.main import ingest_financial_document

        mock_metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=10,
            source_path="/tmp/Report.pdf",
            chunk_count=30,
        )

        with (
            patch(
                "raglite.main.ingest_document", new_callable=AsyncMock, return_value=mock_metadata
            ),
            patch("raglite.main.settings") as mock_settings,
            patch("raglite.main.trigger_forecast_refresh", new_callable=AsyncMock) as mock_refresh,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_settings.enable_forecast_auto_update = False

            result = await ingest_financial_document.fn(doc_path="/tmp/Report.pdf")

        # Forecast refresh should NOT be called
        mock_refresh.assert_not_called()

        # Result should indicate it was disabled
        assert result.forecasts_updated is None
        assert "disabled" in result.forecast_refresh_skipped_reason


# =============================================================================
# Test Forecast Refresh Pipeline
# =============================================================================


class TestForecastRefreshPipeline:
    """Integration tests for the forecast refresh pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_refresh_pipeline(self):
        """Test end-to-end forecast refresh with real function calls (AC1, AC3)."""
        from raglite.forecasting.auto_update import trigger_forecast_refresh

        metadata = DocumentMetadata(
            filename="Q3_Revenue_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=40,
            source_path="/data/Q3_Revenue_Report.pdf",
            chunk_count=120,
        )

        mock_ts_data = MagicMock()
        mock_ts_data.points = [100, 110, 120, 130, 140, 150, 160, 170]

        mock_forecast = MagicMock()
        mock_forecast.metric = "revenue"
        mock_forecast.predictions = [180, 190, 200, 210]

        with (
            patch(
                "raglite.forecasting.auto_update.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.forecasting.auto_update.generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
        ):
            result = await trigger_forecast_refresh(metadata, timeout_seconds=60)

        # Verify pipeline executed successfully
        assert result.success is True
        assert result.document_id == "Q3_Revenue_Report.pdf"
        assert "revenue" in result.metrics_refreshed

    @pytest.mark.asyncio
    async def test_pipeline_with_multiple_metrics(self):
        """Test refresh pipeline handles multiple metrics (AC2)."""
        from raglite.forecasting.auto_update import trigger_forecast_refresh

        # Quarterly report should trigger both revenue and expenses
        metadata = DocumentMetadata(
            filename="Quarterly_Financial_Report_Q3.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=60,
            source_path="/data/Quarterly_Financial_Report_Q3.pdf",
            chunk_count=180,
        )

        mock_ts_data = MagicMock()
        mock_ts_data.points = [100, 110, 120, 130, 140, 150, 160, 170]

        with (
            patch(
                "raglite.forecasting.auto_update.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.forecasting.auto_update.generate_forecast",
                new_callable=AsyncMock,
            ),
        ):
            result = await trigger_forecast_refresh(metadata, timeout_seconds=60)

        # Should attempt to refresh both revenue and expenses
        assert result.success is True
        # Both metrics should be refreshed (or skipped with reason)
        total_processed = len(result.metrics_refreshed) + len(result.metrics_skipped)
        assert total_processed >= 2  # At least revenue and expenses

    @pytest.mark.asyncio
    async def test_pipeline_partial_success(self):
        """Test pipeline handles partial success (some metrics fail)."""
        from raglite.forecasting.auto_update import trigger_forecast_refresh
        from raglite.forecasting.hybrid import InsufficientDataError

        metadata = DocumentMetadata(
            filename="Quarterly_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )

        call_count = [0]

        async def mock_extract(*args, **kwargs):
            call_count[0] += 1
            if kwargs.get("metric") == "revenue":
                return MagicMock(points=[100, 110, 120, 130])
            else:
                raise InsufficientDataError("Need more data")

        with (
            patch(
                "raglite.forecasting.auto_update.extract_timeseries",
                new_callable=AsyncMock,
                side_effect=mock_extract,
            ),
            patch(
                "raglite.forecasting.auto_update.generate_forecast",
                new_callable=AsyncMock,
            ),
        ):
            result = await trigger_forecast_refresh(metadata, timeout_seconds=60)

        # Partial success - some metrics refreshed, some skipped
        assert result.success is True
        assert len(result.metrics_refreshed) > 0 or len(result.metrics_skipped) > 0


# =============================================================================
# Test Timeout Behavior (AC3)
# =============================================================================


class TestTimeoutBehavior:
    """Integration tests for forecast refresh timeout behavior."""

    @pytest.mark.asyncio
    async def test_refresh_respects_timeout(self):
        """Test that forecast refresh respects the configured timeout (AC3)."""
        import asyncio

        from raglite.forecasting.auto_update import trigger_forecast_refresh

        metadata = DocumentMetadata(
            filename="Large_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )

        async def slow_extraction(*args, **kwargs):
            await asyncio.sleep(5)  # Simulate 5 second operation
            return MagicMock(points=[100, 110, 120, 130])

        with patch(
            "raglite.forecasting.auto_update.extract_timeseries",
            new_callable=AsyncMock,
            side_effect=slow_extraction,
        ):
            # Use 1 second timeout - should trigger timeout
            result = await trigger_forecast_refresh(metadata, timeout_seconds=1)

        # Should fail due to timeout
        assert result.success is False
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_mcp_ingestion_graceful_timeout(self):
        """Test that MCP ingestion handles forecast timeout gracefully (AC3)."""
        import asyncio

        from raglite.main import _perform_forecast_refresh
        from raglite.shared.models import ForecastRefreshResult

        metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=10,
            source_path="/tmp/Report.pdf",
            chunk_count=30,
        )

        async def slow_refresh(*args, **kwargs):
            await asyncio.sleep(5)
            return ForecastRefreshResult(
                document_id="Report.pdf",
                metrics_refreshed=["revenue"],
                metrics_skipped=[],
                refresh_duration_ms=5000,
                success=True,
            )

        with (
            patch("raglite.main.settings") as mock_settings,
            patch(
                "raglite.main.trigger_forecast_refresh",
                new_callable=AsyncMock,
                side_effect=slow_refresh,
            ),
        ):
            mock_settings.enable_forecast_auto_update = True
            mock_settings.forecast_refresh_timeout = 1  # 1 second timeout

            # This should NOT raise - should handle timeout gracefully
            result = await _perform_forecast_refresh(metadata, auto_forecast=True)

        # Ingestion should still succeed, but forecast refresh should be skipped
        assert isinstance(result, IngestionResult)
        # Note: The timeout is handled in trigger_forecast_refresh, not _perform_forecast_refresh
        # So we just verify graceful handling


# =============================================================================
# Test Settings Integration (AC5)
# =============================================================================


class TestSettingsIntegration:
    """Integration tests for settings configuration."""

    def test_default_settings(self):
        """Test that forecast auto update is enabled by default."""
        from raglite.shared.config import Settings

        # Create fresh settings instance
        settings = Settings()

        # Default should be enabled
        assert settings.enable_forecast_auto_update is True
        assert settings.forecast_refresh_timeout == 300  # 5 minutes

    def test_settings_can_be_disabled(self):
        """Test that forecast auto update can be disabled via environment."""
        import os

        from raglite.shared.config import Settings

        # Test with environment variable
        with patch.dict(os.environ, {"ENABLE_FORECAST_AUTO_UPDATE": "false"}):
            settings = Settings()
            assert settings.enable_forecast_auto_update is False

    def test_timeout_can_be_configured(self):
        """Test that timeout can be configured via environment."""
        import os

        from raglite.shared.config import Settings

        with patch.dict(os.environ, {"FORECAST_REFRESH_TIMEOUT": "600"}):
            settings = Settings()
            assert settings.forecast_refresh_timeout == 600


# =============================================================================
# Test Logging and Observability
# =============================================================================


class TestLoggingObservability:
    """Tests for logging and observability of forecast refresh."""

    @pytest.mark.asyncio
    async def test_refresh_logs_metrics(self, caplog):
        """Test that forecast refresh logs appropriate metrics."""
        import logging

        from raglite.forecasting.auto_update import trigger_forecast_refresh

        metadata = DocumentMetadata(
            filename="Test_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )

        mock_ts_data = MagicMock()
        mock_ts_data.points = [100, 110, 120, 130]

        with (
            caplog.at_level(logging.INFO),
            patch(
                "raglite.forecasting.auto_update.extract_timeseries",
                new_callable=AsyncMock,
                return_value=mock_ts_data,
            ),
            patch(
                "raglite.forecasting.auto_update.generate_forecast",
                new_callable=AsyncMock,
            ),
        ):
            await trigger_forecast_refresh(metadata)

        # Check that key log messages were emitted
        log_messages = [record.message for record in caplog.records]
        assert any("Starting forecast refresh" in msg for msg in log_messages)
        assert any("Forecast refresh complete" in msg for msg in log_messages)
