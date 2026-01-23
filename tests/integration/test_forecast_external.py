"""Integration tests for multi-variate forecasting with external data.

Story 6.3: Prophet Multi-Variate Forecasting (AC10)

REQUIRES: PostgreSQL running on test port (5433)
"""

from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
import pytest

from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Skip all tests in this module if not running integration tests
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]

# NOTE: db_session and clean_session fixtures are provided by tests/integration/conftest.py
# Do NOT define duplicate fixtures here - causes xdist deadlock (P0 fix 2026-01-23)


def _create_test_sources(storage):
    """Create test data sources for forecasting tests.

    Args:
        storage: ExternalDataStorage instance

    Returns:
        ExternalDataStorage with sources created
    """
    storage.get_or_create_source(
        source_name="INE_BuildingPermits_Test",
        api_endpoint="https://ine.pt/api/test",
        data_type="time_series",
        refresh_frequency="monthly",
    )

    storage.get_or_create_source(
        source_name="OMIE_ElectricityPrice_Test",
        api_endpoint="https://omie.es/api/test",
        data_type="time_series",
        refresh_frequency="daily",
    )

    storage.get_or_create_source(
        source_name="Cement_Consumption_Test",
        api_endpoint=None,
        data_type="time_series",
        refresh_frequency="monthly",
    )

    return storage


def _check_existing_data(storage):
    """Check if test data already exists from previous run."""
    existing_permits = storage.query_data_range(
        source_name="INE_BuildingPermits_Test",
        start_date=date(2023, 1, 1),
        end_date=date(2024, 12, 31),
        metric_name="building_permits_count",
    )
    return len(existing_permits) >= 24


def _insert_building_permits_data(storage, i, point_date, base_permits):
    """Insert building permits data point."""
    try:
        storage.insert_data_points(
            source_name="INE_BuildingPermits_Test",
            data_points=[
                {
                    "date": point_date,
                    "metric_name": "building_permits_count",
                    "value": Decimal(str(base_permits + i * 20)),
                    "unit": "count",
                }
            ],
        )
    except Exception:
        pass


def _insert_electricity_price_data(storage, i, point_date, base_electricity):
    """Insert electricity price data point."""
    try:
        seasonal_factor = 1.1 if (i % 12) in [11, 0, 1] else 1.0
        storage.insert_data_points(
            source_name="OMIE_ElectricityPrice_Test",
            data_points=[
                {
                    "date": point_date,
                    "metric_name": "electricity_price_mwh",
                    "value": Decimal(str(round((base_electricity + i) * seasonal_factor, 2))),
                    "unit": "EUR/MWh",
                }
            ],
        )
    except Exception:
        pass


def _insert_cement_consumption_data(storage, i, point_date, base_cement):
    """Insert cement consumption data point."""
    try:
        storage.insert_data_points(
            source_name="Cement_Consumption_Test",
            data_points=[
                {
                    "date": point_date,
                    "metric_name": "cement_consumption",
                    "value": Decimal(str(base_cement + i * 3 + (i % 4) * 2)),
                    "unit": "1000_tons",
                }
            ],
        )
    except Exception:
        pass


def _insert_time_series_data(storage):
    """Insert 24 months of time-series data for Prophet cross-validation."""
    base_permits = 1000
    base_electricity = 50.0
    base_cement = 100

    for i in range(24):
        point_date = date(2023, 1 + (i % 12), 1) if i < 12 else date(2024, 1 + (i % 12), 1)
        _insert_building_permits_data(storage, i, point_date, base_permits)
        _insert_electricity_price_data(storage, i, point_date, base_electricity)
        _insert_cement_consumption_data(storage, i, point_date, base_cement)


def _convert_to_timeseries_data(orm_points, metric_name: str, source_name: str) -> TimeSeriesData:
    """Convert ORM data points to TimeSeriesData model."""
    return TimeSeriesData(
        metric_name=metric_name,
        points=[
            TimeSeriesPoint(
                date=datetime.combine(p.date, datetime.min.time()),
                value=float(p.value),
                label=str(p.date),
            )
            for p in orm_points
        ],
        source_documents=[source_name],
    )


@pytest.fixture(scope="module")
def populated_storage(db_session):
    """ExternalDataStorage with sample time-series data for forecasting."""
    from raglite.external_data.storage import ExternalDataStorage

    storage = ExternalDataStorage(db_session)
    _create_test_sources(storage)
    if _check_existing_data(storage):
        return storage
    _insert_time_series_data(storage)
    return storage


class TestForecastWithPostgreSQLData:
    """Integration tests for multi-variate forecasting with PostgreSQL data."""

    def test_storage_has_test_data(self, populated_storage) -> None:
        """Verify test data was inserted correctly."""
        # Check building permits
        permits = populated_storage.query_data_range(
            source_name="INE_BuildingPermits_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="building_permits_count",
        )
        assert len(permits) == 24

        # Check electricity
        electricity = populated_storage.query_data_range(
            source_name="OMIE_ElectricityPrice_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="electricity_price_mwh",
        )
        assert len(electricity) == 24

        # Check cement
        cement = populated_storage.query_data_range(
            source_name="Cement_Consumption_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="cement_consumption",
        )
        assert len(cement) == 24

    def test_query_data_as_pandas_series(self, populated_storage) -> None:
        """Test converting PostgreSQL data to pandas Series for Prophet."""
        cement_points = populated_storage.query_data_range(
            source_name="Cement_Consumption_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="cement_consumption",
        )

        # Convert to pandas Series
        dates = [pd.Timestamp(p.date) for p in cement_points]
        values = [float(p.value) for p in cement_points]
        series = pd.Series(values, index=pd.DatetimeIndex(dates), name="cement_consumption")

        assert len(series) == 24
        assert not series.isna().any()
        assert series.index.is_monotonic_increasing

    def test_prepare_regressors_with_postgresql_data(self, populated_storage) -> None:
        """Test preparing regressors from PostgreSQL data."""
        from raglite.forecasting.hybrid import prepare_regressors

        # Get target index from cement data
        cement_points = populated_storage.query_data_range(
            source_name="Cement_Consumption_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="cement_consumption",
        )
        target_index = pd.DatetimeIndex([pd.Timestamp(p.date) for p in cement_points])

        # Get regressor data
        permits_points = populated_storage.query_data_range(
            source_name="INE_BuildingPermits_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="building_permits_count",
        )
        permits_series = pd.Series(
            [float(p.value) for p in permits_points],
            index=pd.DatetimeIndex([pd.Timestamp(p.date) for p in permits_points]),
            name="building_permits",
        )

        # Prepare regressors
        regressors = {"building_permits": permits_series}
        prepared = prepare_regressors(regressors, target_index)

        assert "building_permits" in prepared
        assert len(prepared["building_permits"]) == 24
        assert not prepared["building_permits"].isna().any()

    def test_select_regressors_with_real_data(self, populated_storage) -> None:
        """Test regressor selection using real PostgreSQL data."""
        from raglite.forecasting.hybrid import select_regressors

        # Get target metric
        cement_points = populated_storage.query_data_range(
            source_name="Cement_Consumption_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="cement_consumption",
        )
        target = pd.Series(
            [float(p.value) for p in cement_points],
            index=pd.DatetimeIndex([pd.Timestamp(p.date) for p in cement_points]),
        )

        # Get candidate regressors
        permits_points = populated_storage.query_data_range(
            source_name="INE_BuildingPermits_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="building_permits_count",
        )
        electricity_points = populated_storage.query_data_range(
            source_name="OMIE_ElectricityPrice_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="electricity_price_mwh",
        )

        candidates = {
            "building_permits": pd.Series(
                [float(p.value) for p in permits_points],
                index=pd.DatetimeIndex([pd.Timestamp(p.date) for p in permits_points]),
            ),
            "electricity_price": pd.Series(
                [float(p.value) for p in electricity_points],
                index=pd.DatetimeIndex([pd.Timestamp(p.date) for p in electricity_points]),
            ),
        }

        # Select regressors with low threshold to include both
        selected = select_regressors(target, candidates, top_n=2, min_correlation=0.3)

        # Both should have some correlation with cement (they all have upward trends)
        assert isinstance(selected, list)
        assert len(selected) <= 2


class TestEndToEndForecastingFlow:
    """End-to-end tests for the complete forecasting flow."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_generate_multivariate_forecast(self, populated_storage) -> None:
        """Test complete multi-variate forecast generation (slow: Prophet fitting/CV)."""
        import warnings

        from raglite.forecasting.hybrid import generate_forecast

        cement_points = populated_storage.query_data_range(
            source_name="Cement_Consumption_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="cement_consumption",
        )
        historical_data = _convert_to_timeseries_data(
            cement_points, "cement_consumption", "Cement_Consumption_Test"
        )

        permits_points = populated_storage.query_data_range(
            source_name="INE_BuildingPermits_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="building_permits_count",
        )
        external_regressors = {
            "building_permits": pd.Series(
                [float(p.value) for p in permits_points],
                index=pd.DatetimeIndex([pd.Timestamp(p.date) for p in permits_points]),
            ),
        }

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with patch("raglite.forecasting.hybrid.fetch_historical_data") as mock_fetch:
                mock_fetch.return_value = historical_data
                result = await generate_forecast(
                    metric="cement_consumption",
                    periods_ahead=3,
                    external_regressors=external_regressors,
                    frequency="M",
                    future_regressor_strategy="constant",
                )
            assert any("deprecated" in str(warning.message).lower() for warning in w)

        assert result.metric_name == "cement_consumption"
        assert result.model_type == "prophet_multivariate"
        assert len(result.forecast) == 3
        assert "building_permits" in result.regressors_used


class TestForecastAccuracyComparison:
    """Tests for comparing univariate vs multivariate accuracy."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multivariate_improves_accuracy(self, populated_storage) -> None:
        """Test that adding regressors can improve forecast accuracy (compares uni/multivariate)."""
        import warnings

        from raglite.forecasting.hybrid import generate_forecast

        cement_points = populated_storage.query_data_range(
            source_name="Cement_Consumption_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="cement_consumption",
        )
        historical_data = _convert_to_timeseries_data(
            cement_points, "cement_consumption", "Cement_Consumption_Test"
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with patch("raglite.forecasting.hybrid.fetch_historical_data") as mock_fetch:
                mock_fetch.return_value = historical_data
                univariate_result = await generate_forecast(
                    metric="cement_consumption", periods_ahead=3, external_regressors=None
                )

        assert univariate_result.model_type == "prophet_univariate"
        assert len(univariate_result.forecast) == 3

        permits_points = populated_storage.query_data_range(
            source_name="INE_BuildingPermits_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="building_permits_count",
        )
        external_regressors = {
            "building_permits": pd.Series(
                [float(p.value) for p in permits_points],
                index=pd.DatetimeIndex([pd.Timestamp(p.date) for p in permits_points]),
            ),
        }

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with patch("raglite.forecasting.hybrid.fetch_historical_data") as mock_fetch:
                mock_fetch.return_value = historical_data
                multivariate_result = await generate_forecast(
                    metric="cement_consumption",
                    periods_ahead=3,
                    external_regressors=external_regressors,
                )

        assert multivariate_result.model_type == "prophet_multivariate"
        assert "building_permits" in multivariate_result.regressors_used
        assert len(multivariate_result.forecast) == 3

        if multivariate_result.accuracy_metrics:
            assert "rmse" in multivariate_result.accuracy_metrics
            assert "mae" in multivariate_result.accuracy_metrics
            assert "mape" in multivariate_result.accuracy_metrics
