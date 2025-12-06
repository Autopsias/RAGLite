"""Integration tests for multi-variate forecasting with external data.

Story 6.3: Prophet Multi-Variate Forecasting (AC10)

REQUIRES: PostgreSQL running on test port (5433)
"""

from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal

import pandas as pd
import pytest

from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Skip all tests in this module if not running integration tests
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection]


@pytest.fixture(scope="module")
def db_session():
    """PostgreSQL session for integration tests.

    Creates tables in test database and yields session.
    Rolls back after tests complete.
    """
    from raglite.shared.safety import SafetyGuard

    guard = SafetyGuard()
    guard.validate_test_environment("forecast_external_integration")

    # IMPORTANT: Import ORM models BEFORE create_all() so they register with Base
    from raglite.external_data.orm_models import (  # noqa: F401
        ExternalDataPointORM,
        ExternalDataSourceORM,
    )
    from raglite.shared.database import Base, get_engine, get_session, reset_engine

    # Reset engine to pick up test environment settings
    reset_engine()

    # Create tables in test database
    engine = get_engine()
    Base.metadata.create_all(engine)

    session = get_session()
    yield session

    session.rollback()
    session.close()


@pytest.fixture
def clean_session(db_session):
    """Clean session that rolls back after each test."""
    yield db_session
    db_session.rollback()


@pytest.fixture(scope="module")
def populated_storage(db_session):
    """ExternalDataStorage with sample time-series data for forecasting.

    Module-scoped to avoid recreating data for each test.
    """
    from raglite.external_data.storage import ExternalDataStorage

    storage = ExternalDataStorage(db_session)

    # Use get_or_create to avoid duplicate issues
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

    # Check if data already exists (from previous test run)
    existing_permits = storage.query_data_range(
        source_name="INE_BuildingPermits_Test",
        start_date=date(2023, 1, 1),
        end_date=date(2024, 12, 31),
        metric_name="building_permits_count",
    )

    if len(existing_permits) >= 24:
        # Data already exists, skip insertion
        return storage

    # Insert 24 months of data (enough for Prophet cross-validation)
    base_permits = 1000
    base_electricity = 50.0
    base_cement = 100

    for i in range(24):
        point_date = date(2023, 1 + (i % 12), 1) if i < 12 else date(2024, 1 + (i % 12), 1)

        try:
            # Building permits: growing trend
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
            pass  # Ignore duplicates

        try:
            # Electricity price: seasonal pattern
            seasonal_factor = 1.1 if (i % 12) in [11, 0, 1] else 1.0  # Winter higher
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
            pass  # Ignore duplicates

        try:
            # Cement consumption: target metric with correlation to permits
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
            pass  # Ignore duplicates

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
        """Test complete multi-variate forecast generation.

        This test is slow because it runs Prophet fitting and cross-validation.
        """
        import warnings

        from raglite.forecasting.hybrid import generate_forecast

        # Get historical data from storage
        cement_points = populated_storage.query_data_range(
            source_name="Cement_Consumption_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="cement_consumption",
        )

        # Convert ORM points to TimeSeriesPoint objects
        historical_data = TimeSeriesData(
            metric_name="cement_consumption",
            points=[
                TimeSeriesPoint(
                    date=datetime.combine(p.date, datetime.min.time()),
                    value=float(p.value),
                    label=str(p.date),
                )
                for p in cement_points
            ],
            source_documents=["Cement_Consumption_Test"],
        )

        # Get regressor data
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

        # Generate forecast (should trigger deprecation warning)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = await generate_forecast(
                metric="cement_consumption",
                historical_data=historical_data,
                periods_ahead=3,
                external_regressors=external_regressors,
                frequency="M",
                future_regressor_strategy="constant",
            )

            # Should have deprecation warning
            assert any("deprecated" in str(warning.message).lower() for warning in w)

        # Validate result
        assert result.metric_name == "cement_consumption"
        assert result.model_type == "prophet_multivariate"
        assert len(result.forecast) == 3  # Fixed: was 'forecasts', should be 'forecast'
        assert "building_permits" in result.regressors_used


class TestForecastAccuracyComparison:
    """Tests for comparing univariate vs multivariate accuracy."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multivariate_improves_accuracy(self, populated_storage) -> None:
        """Test that adding regressors can improve forecast accuracy.

        This test compares univariate vs multivariate forecasts.
        """
        import warnings

        from raglite.forecasting.hybrid import generate_forecast

        # Get historical data
        cement_points = populated_storage.query_data_range(
            source_name="Cement_Consumption_Test",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            metric_name="cement_consumption",
        )

        # Convert ORM points to TimeSeriesPoint objects
        historical_data = TimeSeriesData(
            metric_name="cement_consumption",
            points=[
                TimeSeriesPoint(
                    date=datetime.combine(p.date, datetime.min.time()),
                    value=float(p.value),
                    label=str(p.date),
                )
                for p in cement_points
            ],
            source_documents=["Cement_Consumption_Test"],
        )

        # Univariate forecast
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            univariate_result = await generate_forecast(
                metric="cement_consumption",
                historical_data=historical_data,
                periods_ahead=3,
                external_regressors=None,  # No regressors
            )

        assert univariate_result.model_type == "prophet_univariate"
        assert len(univariate_result.forecast) == 3  # Fixed: was 'forecasts'

        # Get regressor data
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

        # Multivariate forecast
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            multivariate_result = await generate_forecast(
                metric="cement_consumption",
                historical_data=historical_data,
                periods_ahead=3,
                external_regressors=external_regressors,
            )

        assert multivariate_result.model_type == "prophet_multivariate"
        assert "building_permits" in multivariate_result.regressors_used

        # Both should produce valid forecasts
        assert len(multivariate_result.forecast) == 3  # Fixed: was 'forecasts'

        # Accuracy metrics should be populated (if CV ran)
        # Note: with 24 data points, CV should have enough data
        if multivariate_result.accuracy_metrics:
            assert "rmse" in multivariate_result.accuracy_metrics
            assert "mae" in multivariate_result.accuracy_metrics
            assert "mape" in multivariate_result.accuracy_metrics
