"""Unit tests for Story 4.3: Automated Forecast Updates.

Tests the auto_update module and related models.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.forecasting.auto_update import identify_affected_metrics, trigger_forecast_refresh
from raglite.shared.models import DocumentMetadata, ForecastRefreshResult, IngestionResult

# =============================================================================
# Test ForecastRefreshResult Model
# =============================================================================


class TestForecastRefreshResult:
    """Tests for the ForecastRefreshResult model."""

    def test_forecast_refresh_result_success(self):
        """Test creating a successful forecast refresh result."""
        result = ForecastRefreshResult(
            document_id="Q3_Report.pdf",
            metrics_refreshed=["revenue", "expenses"],
            metrics_skipped=[],
            refresh_duration_ms=1500,
            success=True,
            error_message=None,
        )

        assert result.document_id == "Q3_Report.pdf"
        assert result.metrics_refreshed == ["revenue", "expenses"]
        assert result.metrics_skipped == []
        assert result.refresh_duration_ms == 1500
        assert result.success is True
        assert result.error_message is None

    def test_forecast_refresh_result_partial_success(self):
        """Test creating a partial success result with some skipped metrics."""
        result = ForecastRefreshResult(
            document_id="Annual_Report.pdf",
            metrics_refreshed=["revenue"],
            metrics_skipped=["expenses: insufficient data"],
            refresh_duration_ms=2000,
            success=True,
        )

        assert result.metrics_refreshed == ["revenue"]
        assert len(result.metrics_skipped) == 1
        assert result.success is True

    def test_forecast_refresh_result_failure(self):
        """Test creating a failure result."""
        result = ForecastRefreshResult(
            document_id="Bad_Report.pdf",
            metrics_refreshed=[],
            metrics_skipped=[],
            refresh_duration_ms=5000,
            success=False,
            error_message="Forecast refresh timed out after 300 seconds",
        )

        assert result.metrics_refreshed == []
        assert result.success is False
        assert "timed out" in result.error_message


# =============================================================================
# Test IngestionResult Model
# =============================================================================


class TestIngestionResult:
    """Tests for the IngestionResult model with forecast fields."""

    def test_ingestion_result_with_forecasts(self):
        """Test creating IngestionResult with forecast updates."""
        result = IngestionResult(
            filename="Q3_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=40,
            source_path="/data/Q3_Report.pdf",
            chunk_count=120,
            forecasts_updated=["revenue", "expenses"],
            forecast_refresh_skipped_reason=None,
        )

        assert result.filename == "Q3_Report.pdf"
        assert result.forecasts_updated == ["revenue", "expenses"]
        assert result.forecast_refresh_skipped_reason is None

    def test_ingestion_result_forecasts_skipped(self):
        """Test creating IngestionResult when forecast refresh was skipped."""
        result = IngestionResult(
            filename="Q3_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=40,
            source_path="/data/Q3_Report.pdf",
            chunk_count=120,
            forecasts_updated=None,
            forecast_refresh_skipped_reason="auto_forecast=False",
        )

        assert result.forecasts_updated is None
        assert result.forecast_refresh_skipped_reason == "auto_forecast=False"

    def test_from_metadata_factory(self):
        """Test the from_metadata factory method."""
        metadata = DocumentMetadata(
            filename="Annual_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=160,
            source_path="/data/Annual_Report.pdf",
            chunk_count=480,
        )

        result = IngestionResult.from_metadata(
            metadata,
            forecasts_updated=["revenue"],
            forecast_refresh_skipped_reason=None,
        )

        assert result.filename == metadata.filename
        assert result.doc_type == metadata.doc_type
        assert result.page_count == metadata.page_count
        assert result.chunk_count == metadata.chunk_count
        assert result.forecasts_updated == ["revenue"]
        assert result.forecast_refresh_skipped_reason is None

    def test_from_metadata_no_forecasts(self):
        """Test from_metadata when forecast refresh is disabled."""
        metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
            page_count=10,
            source_path="/data/Report.pdf",
            chunk_count=30,
        )

        result = IngestionResult.from_metadata(
            metadata,
            forecasts_updated=None,
            forecast_refresh_skipped_reason="forecast_auto_update disabled in settings",
        )

        assert result.forecasts_updated is None
        assert "disabled" in result.forecast_refresh_skipped_reason


# =============================================================================
# Test identify_affected_metrics
# =============================================================================


class TestIdentifyAffectedMetrics:
    """Tests for the identify_affected_metrics function."""

    @pytest.mark.asyncio
    async def test_revenue_document(self):
        """Test that revenue documents return revenue metric."""
        metadata = DocumentMetadata(
            filename="Q3_Revenue_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )
        metrics = await identify_affected_metrics(metadata)
        assert "revenue" in metrics

    @pytest.mark.asyncio
    async def test_expense_document(self):
        """Test that expense documents return expenses metric."""
        metadata = DocumentMetadata(
            filename="Monthly_Expense_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )
        metrics = await identify_affected_metrics(metadata)
        assert "expenses" in metrics

    @pytest.mark.asyncio
    async def test_cost_document(self):
        """Test that cost documents return expenses metric."""
        metadata = DocumentMetadata(
            filename="Cost_Analysis_2024.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )
        metrics = await identify_affected_metrics(metadata)
        assert "expenses" in metrics

    @pytest.mark.asyncio
    async def test_cashflow_document(self):
        """Test that cashflow documents return cash_flow metric."""
        metadata = DocumentMetadata(
            filename="Cashflow_Statement_Q3.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )
        metrics = await identify_affected_metrics(metadata)
        assert "cash_flow" in metrics

    @pytest.mark.asyncio
    async def test_balance_sheet_document(self):
        """Test that balance sheet documents return assets and liabilities."""
        metadata = DocumentMetadata(
            filename="Balance_Sheet_2024.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )
        metrics = await identify_affected_metrics(metadata)
        assert "assets" in metrics
        assert "liabilities" in metrics

    @pytest.mark.asyncio
    async def test_quarterly_report(self):
        """Test that quarterly reports return revenue and expenses."""
        metadata = DocumentMetadata(
            filename="Quarterly_Financial_Report_Q3.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )
        metrics = await identify_affected_metrics(metadata)
        assert "revenue" in metrics
        assert "expenses" in metrics

    @pytest.mark.asyncio
    async def test_annual_report(self):
        """Test that annual reports return revenue and expenses."""
        metadata = DocumentMetadata(
            filename="Annual_Report_2024.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )
        metrics = await identify_affected_metrics(metadata)
        assert "revenue" in metrics
        assert "expenses" in metrics

    @pytest.mark.asyncio
    async def test_generic_document(self):
        """Test that generic documents default to revenue."""
        metadata = DocumentMetadata(
            filename="Report_XYZ.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )
        metrics = await identify_affected_metrics(metadata)
        assert "revenue" in metrics


# =============================================================================
# Test trigger_forecast_refresh
# =============================================================================


class TestTriggerForecastRefresh:
    """Tests for the trigger_forecast_refresh function."""

    @pytest.mark.asyncio
    async def test_successful_refresh(self):
        """Test successful forecast refresh for a document."""
        metadata = DocumentMetadata(
            filename="Q3_Revenue_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )

        # Mock the timeseries extraction and forecast generation
        mock_ts_data = MagicMock()
        mock_ts_data.points = [1, 2, 3, 4]

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
            result = await trigger_forecast_refresh(metadata)

        assert result.success is True
        assert result.document_id == "Q3_Revenue_Report.pdf"
        assert "revenue" in result.metrics_refreshed
        assert result.refresh_duration_ms >= 0  # Mocked operations may complete in <1ms

    @pytest.mark.asyncio
    async def test_refresh_with_insufficient_data(self):
        """Test refresh when timeseries has insufficient data."""
        from raglite.forecasting.hybrid import InsufficientDataError

        metadata = DocumentMetadata(
            filename="Q3_Revenue_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )

        with patch(
            "raglite.forecasting.auto_update.extract_timeseries",
            new_callable=AsyncMock,
            side_effect=InsufficientDataError("Need at least 8 data points"),
        ):
            result = await trigger_forecast_refresh(metadata)

        # Should still succeed (partial) but with skipped metrics
        assert result.success is True  # No metrics refreshed but no fatal error
        assert len(result.metrics_skipped) > 0
        assert "insufficient data" in result.metrics_skipped[0].lower()

    @pytest.mark.asyncio
    async def test_refresh_with_extraction_error(self):
        """Test refresh when timeseries extraction fails."""
        from raglite.forecasting.timeseries_extract import ExtractionError

        metadata = DocumentMetadata(
            filename="Bad_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )

        with patch(
            "raglite.forecasting.auto_update.extract_timeseries",
            new_callable=AsyncMock,
            side_effect=ExtractionError("No timeseries data found"),
        ):
            result = await trigger_forecast_refresh(metadata)

        assert result.success is True  # Graceful degradation
        assert len(result.metrics_skipped) > 0
        assert "extraction failed" in result.metrics_skipped[0].lower()

    @pytest.mark.asyncio
    async def test_refresh_timeout(self):
        """Test that refresh respects timeout (AC3)."""
        import asyncio

        metadata = DocumentMetadata(
            filename="Large_Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )

        async def slow_extraction(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow operation
            return MagicMock(points=[1, 2, 3])

        with patch(
            "raglite.forecasting.auto_update.extract_timeseries",
            new_callable=AsyncMock,
            side_effect=slow_extraction,
        ):
            # Use a 1-second timeout
            result = await trigger_forecast_refresh(metadata, timeout_seconds=1)

        assert result.success is False
        assert "timed out" in result.error_message

    @pytest.mark.asyncio
    async def test_refresh_unexpected_error(self):
        """Test handling of unexpected errors during refresh."""
        metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )

        with patch(
            "raglite.forecasting.auto_update.extract_timeseries",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected error"),
        ):
            result = await trigger_forecast_refresh(metadata)

        # Should handle gracefully
        assert len(result.metrics_skipped) > 0

    @pytest.mark.asyncio
    async def test_refresh_duration_recorded(self):
        """Test that refresh duration is accurately recorded."""
        import asyncio

        metadata = DocumentMetadata(
            filename="Report.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-27T10:00:00Z",
        )

        async def delayed_extraction(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return MagicMock(points=[1, 2, 3, 4])

        with (
            patch(
                "raglite.forecasting.auto_update.extract_timeseries",
                new_callable=AsyncMock,
                side_effect=delayed_extraction,
            ),
            patch(
                "raglite.forecasting.auto_update.generate_forecast",
                new_callable=AsyncMock,
            ),
        ):
            result = await trigger_forecast_refresh(metadata)

        # Duration should be at least 100ms
        assert result.refresh_duration_ms >= 100


# =============================================================================
# Test _perform_forecast_refresh helper (from main.py)
# =============================================================================


class TestPerformForecastRefresh:
    """Tests for the _perform_forecast_refresh helper in main.py."""

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

        with patch("raglite.main.settings") as mock_settings:
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
            patch("raglite.main.settings") as mock_settings,
            patch(
                "raglite.main.trigger_forecast_refresh",
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
            patch("raglite.main.settings") as mock_settings,
            patch(
                "raglite.main.trigger_forecast_refresh",
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
            patch("raglite.main.settings") as mock_settings,
            patch(
                "raglite.main.trigger_forecast_refresh",
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
