"""Unit tests for external regressor time-series extraction (Story 6.24.4).

This function enables validation of external-only metrics by reusing
regressor fetch logic, bridging the gap between regressor system and
validation system.

Testing Strategy:
- Unit tests with mocked fetch_single_regressor
- Tests cover AC1-AC5 from Story 6.24.4
- Edge cases: NaN/Inf values, empty series, insufficient data
- Boundary: No actual API calls (integration testing separate)
"""

from datetime import datetime

import pandas as pd
import pytest

from raglite.forecasting.timeseries import extract_external_regressor_timeseries


class TestExtractExternalRegressorTimeseries:
    """Tests for extract_external_regressor_timeseries (Story 6.24.4)."""

    @pytest.mark.asyncio
    async def test_extract_euribor_3m_success(self, mocker) -> None:
        """Test successful extraction of euribor_3m regressor data."""
        # Mock fetch_single_regressor to return sample data
        mock_series = pd.Series(
            data=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            index=pd.date_range("2024-01-01", periods=6, freq="ME"),
        )
        # Fix Issue #1: Mock at import location, not definition location
        mocker.patch(
            "raglite.forecasting.timeseries.external.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("euribor_3m", min_points=6)

        assert result is not None
        assert result.metric_name == "euribor_3m"
        assert len(result.points) == 6
        assert result.points[0].value == 0.5
        assert result.points[-1].value == 1.0
        assert result.interval == "monthly"

    @pytest.mark.asyncio
    async def test_extract_insufficient_data_returns_none(self, mocker) -> None:
        """Test that insufficient data returns None."""
        # Mock fetch_single_regressor to return insufficient data
        mock_series = pd.Series(
            data=[1.0, 2.0, 3.0],
            index=pd.date_range("2024-01-01", periods=3, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries.external.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("gdp_growth", min_points=6)

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_none_series_returns_none(self, mocker) -> None:
        """Test that None series from fetch returns None."""
        # Mock fetch_single_regressor to return None
        mocker.patch(
            "raglite.forecasting.timeseries.external.fetch_single_regressor",
            return_value=None,
        )

        result = await extract_external_regressor_timeseries("invalid_metric", min_points=6)

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_empty_series_returns_none(self, mocker) -> None:
        """Test that empty series returns None (Issue #7 fix)."""
        # Mock fetch_single_regressor to return empty series
        mock_series = pd.Series([], dtype=float)
        mocker.patch(
            "raglite.forecasting.timeseries.external.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("empty_metric", min_points=6)

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_diesel_price_conversion(self, mocker) -> None:
        """Test data type conversion for diesel price regressor."""
        # Mock fetch_single_regressor to return diesel price data
        mock_series = pd.Series(
            data=[1.45, 1.50, 1.55, 1.60, 1.65, 1.70, 1.75],
            index=pd.date_range("2024-01-01", periods=7, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries.external.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("diesel", min_points=6)

        assert result is not None
        assert result.metric_name == "diesel"
        assert len(result.points) == 7
        # Verify all values are floats
        assert all(isinstance(p.value, float) for p in result.points)
        # Verify date conversion
        assert all(isinstance(p.date, datetime) for p in result.points)

    @pytest.mark.asyncio
    async def test_extract_filters_nan_values(self, mocker, caplog) -> None:
        """Test that NaN values are filtered out (Issue #4 fix)."""
        # Mock fetch_single_regressor to return data with NaN
        mock_series = pd.Series(
            data=[1.0, float("nan"), 3.0, 4.0, float("nan"), 6.0, 7.0, 8.0],
            index=pd.date_range("2024-01-01", periods=8, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries.external.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("test_metric", min_points=6)

        assert result is not None
        assert len(result.points) == 6  # 8 total - 2 NaN = 6 valid
        # Verify no NaN values in result
        assert all(not (val != val) for val in [p.value for p in result.points])
        # Check warning log
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("Filtered NaN/Inf values" in r.message for r in warning_records)

    @pytest.mark.asyncio
    async def test_extract_filters_inf_values(self, mocker, caplog) -> None:
        """Test that infinite values are filtered out (Issue #4 fix)."""
        # Mock fetch_single_regressor to return data with Inf
        mock_series = pd.Series(
            data=[1.0, float("inf"), 3.0, 4.0, float("-inf"), 6.0, 7.0, 8.0],
            index=pd.date_range("2024-01-01", periods=8, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries.external.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("test_metric", min_points=6)

        assert result is not None
        assert len(result.points) == 6  # 8 total - 2 Inf = 6 valid
        # Verify no infinite values in result
        import math

        assert all(not math.isinf(p.value) for p in result.points)
        # Check warning log
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("Filtered NaN/Inf values" in r.message for r in warning_records)

    @pytest.mark.asyncio
    async def test_extract_nan_filtering_insufficient_after_filter(self, mocker, caplog) -> None:
        """Test that insufficient data after NaN filtering returns None."""
        # Mock fetch_single_regressor to return data with too many NaN
        mock_series = pd.Series(
            data=[1.0, float("nan"), float("nan"), 4.0, float("nan"), float("nan")],
            index=pd.date_range("2024-01-01", periods=6, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries.external.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("test_metric", min_points=6)

        assert result is None  # Only 2 valid points after filtering
        # Check warning logs
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("Insufficient valid data after filtering" in r.message for r in warning_records)

    @pytest.mark.asyncio
    async def test_extract_handles_fetch_exception(self, mocker, caplog) -> None:
        """Test error handling when fetch_single_regressor raises exception."""
        # Mock fetch_single_regressor to raise exception
        mocker.patch(
            "raglite.forecasting.timeseries.external.fetch_single_regressor",
            side_effect=Exception("API connection failed"),
        )

        result = await extract_external_regressor_timeseries("construction_output", min_points=6)

        assert result is None
        # Check error log
        error_records = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_records) > 0
        assert any("Failed to extract external regressor" in r.message for r in error_records)
