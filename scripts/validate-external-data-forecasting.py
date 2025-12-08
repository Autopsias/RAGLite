#!/usr/bin/env python3
"""External Data & Forecasting Validation Script.

Story 6.7 Pre-Validation: Tests Tier 1 external data sources and their
integration with the forecasting engine to determine if Story 6.8 is needed.

This script validates:
1. API connectivity for all 8 Tier 1 data source clients
2. Data quality (completeness, freshness, validity)
3. Correlation analysis between external data and cement demand
4. Multi-variate forecasting accuracy vs univariate baseline
5. Story 6.8 decision gate recommendation

Decision Gate (Story 6.8):
- IF multi-variate accuracy >= 90% (MAPE <= 10%) -> SKIP Story 6.8
- IF multi-variate accuracy >= 88% (MAPE <= 12%) -> SKIP Story 6.8 (threshold)
- IF multi-variate accuracy < 88% -> EXECUTE Story 6.8 (add Tier 2 sources)

Usage:
    python scripts/validate-external-data-forecasting.py [--live-api] [--verbose]

Options:
    --live-api      Actually call external APIs (requires network/API keys)
    --verbose       Show detailed output for each test
    --export-json   Export results to JSON file
    --skip-forecast Skip forecasting tests (API tests only)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class ClientTestResult:
    """Result of testing a single external data client."""

    client_name: str
    success: bool = False
    records_fetched: int = 0
    error_message: str | None = None
    response_time_ms: float = 0.0
    data_freshness_days: int | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None
    sample_data: list[dict] = field(default_factory=list)


@dataclass
class DataQualityResult:
    """Result of data quality validation."""

    source_name: str
    completeness_pct: float  # % of expected data points present
    freshness_ok: bool  # Is latest data within freshness threshold?
    has_outliers: bool  # Statistical outlier detection
    missing_periods: list[str] = field(default_factory=list)
    quality_score: float = 0.0  # 0-100 composite score


@dataclass
class CorrelationResult:
    """Correlation analysis between external data and target metric."""

    regressor_name: str
    correlation: float
    p_value: float | None = None
    lag_months: int = 0  # Optimal lag for correlation
    recommendation: str = ""  # "include", "exclude", "transform"


@dataclass
class ForecastAccuracyResult:
    """Forecasting accuracy results."""

    model_type: str  # "univariate", "multivariate", "ensemble"
    rmse: float
    mae: float
    mape: float  # Mean Absolute Percentage Error
    regressors_used: list[str] = field(default_factory=list)
    periods_tested: int = 0


@dataclass
class ValidationReport:
    """Complete validation report."""

    timestamp: str
    client_tests: list[ClientTestResult] = field(default_factory=list)
    data_quality: list[DataQualityResult] = field(default_factory=list)
    correlations: list[CorrelationResult] = field(default_factory=list)
    univariate_accuracy: ForecastAccuracyResult | None = None
    multivariate_accuracy: ForecastAccuracyResult | None = None
    ensemble_accuracy: ForecastAccuracyResult | None = None
    story_6_8_decision: str = ""  # "SKIP" or "EXECUTE"
    decision_rationale: str = ""
    overall_status: str = ""  # "PASS", "PARTIAL", "FAIL"


# =============================================================================
# Client Testing
# =============================================================================


async def test_ine_client(live_api: bool = False) -> ClientTestResult:
    """Test INE client connectivity and data fetching."""
    import time

    from raglite.external_data.clients import INEClient

    client = INEClient()
    result = ClientTestResult(client_name="INE (Instituto Nacional de Estatística)")

    # Test date range (last 6 months)
    end_date = date.today()
    start_date = end_date - timedelta(days=180)

    start_time = time.time()

    if live_api:
        try:
            permits = await client.fetch_building_permits(start_date, end_date)
            result.success = True
            result.records_fetched = len(permits)
            result.date_range_start = start_date
            result.date_range_end = end_date

            if permits:
                result.data_freshness_days = (end_date - permits[-1].date).days
                result.sample_data = [
                    {"date": str(p.date), "permits": p.permits_count, "region": p.region}
                    for p in permits[:3]
                ]
        except Exception as e:
            result.success = False
            result.error_message = str(e)
    else:
        # Mock test - verify client can be instantiated and has methods
        result.success = hasattr(client, "fetch_building_permits")
        result.records_fetched = 0
        result.error_message = "Skipped (--live-api not specified)"

    result.response_time_ms = (time.time() - start_time) * 1000
    return result


async def test_bpstat_client(live_api: bool = False) -> ClientTestResult:
    """Test BPstat client connectivity."""
    import time

    from raglite.external_data.clients import BPstatClient

    client = BPstatClient()
    result = ClientTestResult(client_name="BPstat (Banco de Portugal)")

    end_date = date.today()
    start_date = end_date - timedelta(days=180)

    start_time = time.time()

    if live_api:
        try:
            loans = await client.fetch_mortgage_loans(start_date, end_date)
            result.success = True
            result.records_fetched = len(loans)
            result.date_range_start = start_date
            result.date_range_end = end_date

            if loans:
                result.data_freshness_days = (end_date - loans[-1].date).days
                result.sample_data = [
                    {"date": str(loan.date), "total_loans_eur": loan.total_loans_eur}
                    for loan in loans[:3]
                ]
        except Exception as e:
            result.success = False
            result.error_message = str(e)
    else:
        result.success = hasattr(client, "fetch_mortgage_loans")
        result.records_fetched = 0
        result.error_message = "Skipped (--live-api not specified)"

    result.response_time_ms = (time.time() - start_time) * 1000
    return result


async def test_omie_client(live_api: bool = False) -> ClientTestResult:
    """Test OMIE client connectivity."""
    import time

    from raglite.external_data.clients import OMIEClient

    client = OMIEClient()
    result = ClientTestResult(client_name="OMIE (Electricity Market)")

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    start_time = time.time()

    if live_api:
        try:
            prices = await client.fetch_spot_prices(start_date, end_date)
            result.success = True
            result.records_fetched = len(prices)
            result.date_range_start = start_date
            result.date_range_end = end_date

            if prices:
                result.data_freshness_days = (end_date - prices[-1].date).days
                result.sample_data = [
                    {"date": str(p.date), "price_eur_mwh": p.price_eur_mwh} for p in prices[:3]
                ]
        except Exception as e:
            result.success = False
            result.error_message = str(e)
    else:
        result.success = hasattr(client, "fetch_spot_prices")
        result.records_fetched = 0
        result.error_message = "Skipped (--live-api not specified)"

    result.response_time_ms = (time.time() - start_time) * 1000
    return result


async def test_ipma_client(live_api: bool = False) -> ClientTestResult:
    """Test IPMA client connectivity."""
    import time

    from raglite.external_data.clients import IPMAClient

    client = IPMAClient()
    result = ClientTestResult(client_name="IPMA (Weather)")

    start_time = time.time()

    if live_api:
        try:
            # IPMA fetch_all_stations returns list of stations with weather data for a date
            target_date = date.today() - timedelta(days=1)  # Yesterday (more likely to have data)
            stations = await client.fetch_all_stations(target_date)
            result.success = True
            result.records_fetched = len(stations) if stations else 0
            result.date_range_start = target_date
            result.date_range_end = target_date

            if stations:
                result.data_freshness_days = 1
                result.sample_data = [
                    {
                        "station": s.station_name or s.station_id,
                        "temp_c": s.temperature_c,
                    }
                    for s in stations[:3]
                ]
        except Exception as e:
            result.success = False
            result.error_message = str(e)
    else:
        result.success = hasattr(client, "fetch_observations")
        result.records_fetched = 0
        result.error_message = "Skipped (--live-api not specified)"

    result.response_time_ms = (time.time() - start_time) * 1000
    return result


async def test_eu_oil_bulletin_client(live_api: bool = False) -> ClientTestResult:
    """Test EU Oil Bulletin client connectivity."""
    import time

    from raglite.external_data.clients import EUOilBulletinClient

    client = EUOilBulletinClient()
    result = ClientTestResult(client_name="EU Oil Bulletin (Diesel Prices)")

    end_date = date.today()
    start_date = end_date - timedelta(days=90)

    start_time = time.time()

    if live_api:
        try:
            prices = await client.fetch_diesel_prices(start_date, end_date)
            result.success = True
            result.records_fetched = len(prices)
            result.date_range_start = start_date
            result.date_range_end = end_date

            if prices:
                result.data_freshness_days = (end_date - prices[-1].date).days
                result.sample_data = [
                    {"date": str(p.date), "price_eur_litre": p.price_eur_litre} for p in prices[:3]
                ]
        except Exception as e:
            result.success = False
            result.error_message = str(e)
    else:
        result.success = hasattr(client, "fetch_diesel_prices")
        result.records_fetched = 0
        result.error_message = "Skipped (--live-api not specified)"

    result.response_time_ms = (time.time() - start_time) * 1000
    return result


async def test_basegov_client(live_api: bool = False) -> ClientTestResult:
    """Test Base.gov.pt client connectivity."""
    import time

    from raglite.external_data.clients import BaseGovClient

    client = BaseGovClient()
    result = ClientTestResult(client_name="Base.gov.pt (Public Contracts)")

    end_date = date.today()
    start_date = end_date - timedelta(days=365)  # Last year (IMPIC data is yearly)

    start_time = time.time()

    if live_api:
        try:
            contracts = await client.fetch_contracts(start_date, end_date)
            result.success = True
            result.records_fetched = len(contracts)
            result.date_range_start = start_date
            result.date_range_end = end_date

            if contracts:
                result.data_freshness_days = (end_date - contracts[-1].publication_date).days
                result.sample_data = [
                    {
                        "date": str(c.publication_date),
                        "value_eur": c.contract_value_eur,
                        "entity": c.contracting_entity,
                    }
                    for c in contracts[:3]
                ]
        except Exception as e:
            result.success = False
            result.error_message = str(e)
    else:
        result.success = hasattr(client, "fetch_contracts")
        result.records_fetched = 0
        result.error_message = "Skipped (--live-api not specified)"

    result.response_time_ms = (time.time() - start_time) * 1000
    return result


async def test_atic_client(live_api: bool = False) -> ClientTestResult:
    """Test ATIC client (cement consumption - CSV-based)."""
    import time

    from raglite.external_data.clients import ATICClient

    client = ATICClient()
    result = ClientTestResult(client_name="ATIC (Cement Consumption)")

    start_time = time.time()

    # ATIC has fetch_historical_data method
    result.success = hasattr(client, "fetch_historical_data")
    result.records_fetched = 0
    result.error_message = "CSV-based source (manual data load)" if not live_api else None

    if live_api:
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=365)
            data = await client.fetch_historical_data(start_date, end_date)
            result.success = True
            result.records_fetched = len(data) if data else 0
        except Exception as e:
            result.success = False
            result.error_message = str(e)

    result.response_time_ms = (time.time() - start_time) * 1000
    return result


async def test_commodities_client(live_api: bool = False) -> ClientTestResult:
    """Test Commodities client (coal, petcoke, CO2)."""
    import time

    from raglite.external_data.clients import CommoditiesClient

    client = CommoditiesClient()
    result = ClientTestResult(client_name="Commodities (Coal/Petcoke/CO2)")

    start_time = time.time()

    if live_api:
        try:
            # Test CO2 prices
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            prices = await client.fetch_co2_prices(start_date, end_date)
            result.success = True
            result.records_fetched = len(prices)
            result.date_range_start = start_date
            result.date_range_end = end_date

            if prices:
                result.data_freshness_days = (end_date - prices[-1].date).days
                result.sample_data = [
                    {"date": str(p.date), "price": p.price, "unit": p.unit} for p in prices[:3]
                ]
        except Exception as e:
            result.success = False
            result.error_message = str(e)
    else:
        result.success = hasattr(client, "fetch_co2_prices")
        result.records_fetched = 0
        result.error_message = "Skipped (--live-api not specified)"

    result.response_time_ms = (time.time() - start_time) * 1000
    return result


async def test_ecb_client(live_api: bool = False) -> ClientTestResult:
    """Test ECB client (EURIBOR rates)."""
    import time

    from raglite.external_data.clients import ECBClient

    client = ECBClient()
    result = ClientTestResult(client_name="ECB (EURIBOR Rates)")

    end_date = date.today()
    start_date = end_date - timedelta(days=365)  # Last year

    start_time = time.time()

    if live_api:
        try:
            rates = await client.fetch_euribor(start_date, end_date, tenor="3M")
            result.success = True
            result.records_fetched = len(rates)
            result.date_range_start = start_date
            result.date_range_end = end_date

            if rates:
                result.data_freshness_days = (end_date - rates[-1].date).days
                result.sample_data = [
                    {"date": str(r.date), "rate_pct": r.rate_pct, "tenor": r.tenor}
                    for r in rates[:3]
                ]
        except Exception as e:
            result.success = False
            result.error_message = str(e)
    else:
        result.success = hasattr(client, "fetch_euribor")
        result.records_fetched = 0
        result.error_message = "Skipped (--live-api not specified)"

    result.response_time_ms = (time.time() - start_time) * 1000
    return result


async def run_all_client_tests(live_api: bool = False) -> list[ClientTestResult]:
    """Run connectivity tests for all 8 Tier 1 clients."""
    print("\n" + "=" * 60)
    print("PHASE 1: API CLIENT CONNECTIVITY TESTS")
    print("=" * 60 + "\n")

    # Run each test individually with better error handling
    test_funcs = [
        ("INE", test_ine_client),
        ("BPstat", test_bpstat_client),
        ("OMIE", test_omie_client),
        ("IPMA", test_ipma_client),
        ("EU Oil Bulletin", test_eu_oil_bulletin_client),
        ("Base.gov.pt", test_basegov_client),
        ("ATIC", test_atic_client),
        ("Commodities", test_commodities_client),
        ("ECB", test_ecb_client),  # EURIBOR rates
    ]

    client_results = []
    for name, test_func in test_funcs:
        try:
            result = await test_func(live_api)
            client_results.append(result)
        except Exception as e:
            client_results.append(
                ClientTestResult(
                    client_name=name,
                    success=False,
                    error_message=str(e),
                )
            )

    # Print results
    for result in client_results:
        status = "\u2705" if result.success else "\u274c"
        print(f"{status} {result.client_name}")
        if result.success and result.records_fetched > 0:
            print(f"   Records: {result.records_fetched}")
            print(f"   Response time: {result.response_time_ms:.0f}ms")
            if result.data_freshness_days is not None:
                print(f"   Data freshness: {result.data_freshness_days} days old")
        elif result.error_message:
            print(f"   {result.error_message}")
        print()

    return client_results


# =============================================================================
# Data Quality Analysis
# =============================================================================


def analyze_data_quality(
    source_name: str,
    data: pd.DataFrame,
    expected_frequency: str = "monthly",
    freshness_threshold_days: int = 45,
) -> DataQualityResult:
    """Analyze data quality for a source.

    Args:
        source_name: Name of the data source
        data: DataFrame with 'date' column and value columns
        expected_frequency: Expected data frequency (daily, weekly, monthly)
        freshness_threshold_days: Max days since last data point

    Returns:
        DataQualityResult with quality metrics
    """
    result = DataQualityResult(
        source_name=source_name, completeness_pct=0.0, freshness_ok=False, has_outliers=False
    )

    if data.empty:
        result.quality_score = 0.0
        return result

    # Ensure date column
    if "date" not in data.columns:
        result.quality_score = 0.0
        return result

    data = data.sort_values("date")

    # Completeness analysis
    if expected_frequency == "monthly":
        # Calculate expected months in range
        date_range = pd.date_range(
            start=data["date"].min(),
            end=data["date"].max(),
            freq="MS",
        )
        expected_count = len(date_range)
        actual_count = len(data)
        result.completeness_pct = (
            (actual_count / expected_count * 100) if expected_count > 0 else 0.0
        )

        # Find missing periods
        actual_months = set(pd.to_datetime(data["date"]).dt.to_period("M"))
        expected_months = set(pd.to_datetime(date_range).to_period("M"))
        missing = expected_months - actual_months
        result.missing_periods = [str(m) for m in sorted(missing)]

    elif expected_frequency == "daily":
        date_range = pd.date_range(
            start=data["date"].min(),
            end=data["date"].max(),
            freq="D",
        )
        expected_count = len(date_range)
        actual_count = len(data)
        result.completeness_pct = (
            (actual_count / expected_count * 100) if expected_count > 0 else 0.0
        )

    # Freshness check
    latest_date = pd.to_datetime(data["date"].max())
    days_since_latest = (pd.Timestamp.now() - latest_date).days
    result.freshness_ok = days_since_latest <= freshness_threshold_days

    # Outlier detection (IQR method)
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if col != "date":
            q1 = data[col].quantile(0.25)
            q3 = data[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = data[(data[col] < lower_bound) | (data[col] > upper_bound)]
            if len(outliers) > 0:
                result.has_outliers = True
                break

    # Composite quality score (0-100)
    completeness_score = min(result.completeness_pct, 100)
    freshness_score = 100 if result.freshness_ok else 50
    outlier_score = 90 if result.has_outliers else 100

    result.quality_score = completeness_score * 0.5 + freshness_score * 0.3 + outlier_score * 0.2

    return result


# =============================================================================
# Correlation Analysis
# =============================================================================


def calculate_correlations(
    target_series: pd.Series,
    regressors: dict[str, pd.Series],
    max_lag: int = 3,
) -> list[CorrelationResult]:
    """Calculate correlations between target and regressors.

    Args:
        target_series: Target metric (e.g., cement demand)
        regressors: Dict of regressor name -> series
        max_lag: Maximum lag (months) to test

    Returns:
        List of CorrelationResult sorted by correlation strength
    """
    from scipy import stats

    results = []

    for name, regressor in regressors.items():
        best_corr = 0.0
        best_lag = 0
        best_p_value = 1.0

        for lag in range(max_lag + 1):
            if lag > 0:
                shifted = regressor.shift(lag)
            else:
                shifted = regressor

            # Align series
            aligned = pd.DataFrame({"target": target_series, "regressor": shifted}).dropna()

            if len(aligned) < 10:
                continue

            corr, p_value = stats.pearsonr(aligned["target"], aligned["regressor"])

            if abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag
                best_p_value = p_value

        # Recommendation based on correlation
        if abs(best_corr) >= 0.5:
            recommendation = "include"
        elif abs(best_corr) >= 0.3:
            recommendation = "include (moderate)"
        elif abs(best_corr) >= 0.2:
            recommendation = "transform"
        else:
            recommendation = "exclude"

        results.append(
            CorrelationResult(
                regressor_name=name,
                correlation=best_corr,
                p_value=best_p_value,
                lag_months=best_lag,
                recommendation=recommendation,
            )
        )

    # Sort by absolute correlation descending
    results.sort(key=lambda x: abs(x.correlation), reverse=True)
    return results


# =============================================================================
# Forecasting Accuracy Tests
# =============================================================================


async def test_univariate_forecast(
    historical_data: pd.DataFrame,
    metric_name: str = "cement_demand",
    test_periods: int = 6,
) -> ForecastAccuracyResult:
    """Test univariate Prophet forecast accuracy.

    Uses hold-out validation: train on all but last N periods, test on last N.
    """
    from raglite.forecasting.hybrid import InsufficientDataError, generate_forecast
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    if len(historical_data) < test_periods + 12:
        return ForecastAccuracyResult(
            model_type="univariate",
            rmse=0.0,
            mae=0.0,
            mape=100.0,  # Failure indicator
            periods_tested=0,
        )

    # Split data: train on all but last N periods
    train_data = historical_data.iloc[:-test_periods]
    test_data = historical_data.iloc[-test_periods:]

    # Convert to TimeSeriesData
    ts_points = [
        TimeSeriesPoint(date=row["date"], value=row["value"]) for _, row in train_data.iterrows()
    ]
    ts_data = TimeSeriesData(
        metric_name=metric_name,
        points=ts_points,
        frequency="monthly",
        source_documents=["validation_test"],
    )

    try:
        forecast_result = await generate_forecast(
            metric=metric_name,
            historical_data=ts_data,
            periods_ahead=test_periods,
            frequency="M",
        )

        # Calculate accuracy metrics
        actual = test_data["value"].values
        predicted = [p.value for p in forecast_result.forecast]

        # Ensure same length
        min_len = min(len(actual), len(predicted))
        actual = actual[:min_len]
        predicted = predicted[:min_len]

        # RMSE
        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

        # MAE
        mae = float(np.mean(np.abs(actual - predicted)))

        # MAPE (avoid division by zero)
        non_zero_mask = actual != 0
        if non_zero_mask.any():
            mape = float(
                np.mean(
                    np.abs(
                        (actual[non_zero_mask] - predicted[: sum(non_zero_mask)])
                        / actual[non_zero_mask]
                    )
                )
                * 100
            )
        else:
            mape = 0.0

        return ForecastAccuracyResult(
            model_type="univariate",
            rmse=rmse,
            mae=mae,
            mape=mape,
            periods_tested=min_len,
        )

    except InsufficientDataError:
        return ForecastAccuracyResult(
            model_type="univariate",
            rmse=0.0,
            mae=0.0,
            mape=100.0,
            periods_tested=0,
        )


async def test_multivariate_forecast(
    historical_data: pd.DataFrame,
    external_regressors: dict[str, pd.Series],
    metric_name: str = "cement_demand",
    test_periods: int = 6,
) -> ForecastAccuracyResult:
    """Test multi-variate Prophet forecast accuracy with external regressors."""
    from raglite.forecasting.hybrid import InsufficientDataError, generate_forecast
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    if len(historical_data) < test_periods + 12:
        return ForecastAccuracyResult(
            model_type="multivariate",
            rmse=0.0,
            mae=0.0,
            mape=100.0,
            periods_tested=0,
        )

    # Split data
    train_data = historical_data.iloc[:-test_periods]
    test_data = historical_data.iloc[-test_periods:]

    # Split regressors too
    train_regressors = {}
    for name, series in external_regressors.items():
        train_regressors[name] = series.iloc[:-test_periods]

    # Convert to TimeSeriesData
    ts_points = [
        TimeSeriesPoint(date=row["date"], value=row["value"]) for _, row in train_data.iterrows()
    ]
    ts_data = TimeSeriesData(
        metric_name=metric_name,
        points=ts_points,
        frequency="monthly",
        source_documents=["validation_test"],
    )

    try:
        forecast_result = await generate_forecast(
            metric=metric_name,
            historical_data=ts_data,
            external_regressors=train_regressors,
            periods_ahead=test_periods,
            frequency="M",
        )

        # Calculate accuracy metrics
        actual = test_data["value"].values
        predicted = [p.value for p in forecast_result.forecast]

        min_len = min(len(actual), len(predicted))
        actual = actual[:min_len]
        predicted = predicted[:min_len]

        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
        mae = float(np.mean(np.abs(actual - predicted)))

        non_zero_mask = actual != 0
        if non_zero_mask.any():
            mape = float(
                np.mean(
                    np.abs(
                        (actual[non_zero_mask] - predicted[: sum(non_zero_mask)])
                        / actual[non_zero_mask]
                    )
                )
                * 100
            )
        else:
            mape = 0.0

        return ForecastAccuracyResult(
            model_type="multivariate",
            rmse=rmse,
            mae=mae,
            mape=mape,
            regressors_used=forecast_result.regressors_used or [],
            periods_tested=min_len,
        )

    except (InsufficientDataError, Exception) as e:
        logger.warning(f"Multivariate forecast failed: {e}")
        return ForecastAccuracyResult(
            model_type="multivariate",
            rmse=0.0,
            mae=0.0,
            mape=100.0,
            periods_tested=0,
        )


async def test_secil_kpi_forecasts(
    kpis: dict[str, pd.DataFrame],
    test_periods: int = 6,
) -> dict[str, ForecastAccuracyResult]:
    """Test forecasting accuracy on SECIL business KPIs.

    Tests whether the forecasting tool can predict key cement business metrics
    that SECIL employees would care about (EBITDA, Revenue, Sales Volume, etc.).

    These are the actual variables from Performance Reviews that users want to forecast.
    """
    from raglite.forecasting.hybrid import InsufficientDataError, generate_forecast
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    results = {}

    for kpi_name, kpi_df in kpis.items():
        if kpi_df.empty or len(kpi_df) < test_periods + 12:
            results[kpi_name] = ForecastAccuracyResult(
                model_type=f"univariate_{kpi_name}",
                rmse=0.0,
                mae=0.0,
                mape=100.0,
                periods_tested=0,
            )
            continue

        # Split data
        train_data = kpi_df.iloc[:-test_periods]
        test_data = kpi_df.iloc[-test_periods:]

        # Convert to TimeSeriesData
        ts_points = [
            TimeSeriesPoint(date=row["date"], value=row["value"])
            for _, row in train_data.iterrows()
        ]
        ts_data = TimeSeriesData(
            metric_name=kpi_name.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("(", "")
            .replace(")", ""),
            points=ts_points,
            frequency="monthly",
            source_documents=["secil_performance_review"],
        )

        try:
            forecast_result = await generate_forecast(
                metric=kpi_name,
                historical_data=ts_data,
                periods_ahead=test_periods,
                frequency="M",
            )

            actual = test_data["value"].values
            predicted = [p.value for p in forecast_result.forecast]

            min_len = min(len(actual), len(predicted))
            actual = actual[:min_len]
            predicted = np.array(predicted[:min_len])

            # Metrics
            rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
            mae = float(np.mean(np.abs(actual - predicted)))
            mape = float(np.mean(np.abs((actual - predicted) / actual)) * 100)

            results[kpi_name] = ForecastAccuracyResult(
                model_type=f"univariate_{kpi_name}",
                rmse=rmse,
                mae=mae,
                mape=mape,
                periods_tested=min_len,
            )

        except (InsufficientDataError, Exception) as e:
            logger.warning(f"KPI forecast failed for {kpi_name}: {e}")
            results[kpi_name] = ForecastAccuracyResult(
                model_type=f"univariate_{kpi_name}",
                rmse=0.0,
                mae=0.0,
                mape=100.0,
                periods_tested=0,
            )

    return results


async def test_alternative_targets(
    regressors: dict[str, pd.Series],
    test_periods: int = 6,
) -> dict[str, ForecastAccuracyResult]:
    """Test forecasting accuracy on alternative target variables.

    Tests whether the forecasting tool can predict non-seasonal variables
    that cement companies might want to forecast (e.g., EURIBOR, diesel prices).

    This validates the tool's versatility beyond seasonal cement demand.
    """
    from raglite.forecasting.hybrid import InsufficientDataError, generate_forecast
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    results = {}

    for target_name, target_series in regressors.items():
        if target_series.empty or len(target_series) < test_periods + 12:
            results[target_name] = ForecastAccuracyResult(
                model_type=f"univariate_{target_name}",
                rmse=0.0,
                mae=0.0,
                mape=100.0,
                periods_tested=0,
            )
            continue

        # Convert series to DataFrame format
        target_df = pd.DataFrame(
            {
                "date": target_series.index,
                "value": target_series.values,
            }
        ).reset_index(drop=True)

        # Split data
        train_data = target_df.iloc[:-test_periods]
        test_data = target_df.iloc[-test_periods:]

        # Convert to TimeSeriesData
        ts_points = [
            TimeSeriesPoint(date=row["date"], value=row["value"])
            for _, row in train_data.iterrows()
        ]
        ts_data = TimeSeriesData(
            metric_name=target_name,
            points=ts_points,
            frequency="monthly",
            source_documents=["validation_test"],
        )

        try:
            forecast_result = await generate_forecast(
                metric=target_name,
                historical_data=ts_data,
                periods_ahead=test_periods,
                frequency="M",
            )

            actual = test_data["value"].values
            predicted = [p.value for p in forecast_result.forecast]

            min_len = min(len(actual), len(predicted))
            actual = actual[:min_len]
            predicted = np.array(predicted[:min_len])

            # Handle metrics appropriately
            rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
            mae = float(np.mean(np.abs(actual - predicted)))

            # For MAPE, handle negative values (like EURIBOR) carefully
            if np.any(actual == 0):
                # Use SMAPE for series with zeros
                mape = float(
                    np.mean(
                        2 * np.abs(actual - predicted) / (np.abs(actual) + np.abs(predicted) + 1e-8)
                    )
                    * 100
                )
            else:
                mape = float(np.mean(np.abs((actual - predicted) / actual)) * 100)

            results[target_name] = ForecastAccuracyResult(
                model_type=f"univariate_{target_name}",
                rmse=rmse,
                mae=mae,
                mape=mape,
                periods_tested=min_len,
            )

        except (InsufficientDataError, Exception):
            results[target_name] = ForecastAccuracyResult(
                model_type=f"univariate_{target_name}",
                rmse=0.0,
                mae=0.0,
                mape=100.0,
                periods_tested=0,
            )

    return results


async def test_ensemble_forecast(
    historical_data: pd.DataFrame,
    external_regressors: dict[str, pd.Series],
    metric_name: str = "cement_demand",
    test_periods: int = 6,
) -> ForecastAccuracyResult:
    """Test ensemble forecast accuracy (Prophet + Linear + XGBoost)."""
    from raglite.forecasting.hybrid import InsufficientDataError, generate_ensemble_forecast
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    if len(historical_data) < test_periods + 12:
        return ForecastAccuracyResult(
            model_type="ensemble",
            rmse=0.0,
            mae=0.0,
            mape=100.0,
            periods_tested=0,
        )

    # Split data
    train_data = historical_data.iloc[:-test_periods]
    test_data = historical_data.iloc[-test_periods:]

    train_regressors = {}
    for name, series in external_regressors.items():
        train_regressors[name] = series.iloc[:-test_periods]

    ts_points = [
        TimeSeriesPoint(date=row["date"], value=row["value"]) for _, row in train_data.iterrows()
    ]
    ts_data = TimeSeriesData(
        metric_name=metric_name,
        points=ts_points,
        frequency="monthly",
        source_documents=["validation_test"],
    )

    try:
        forecast_result = await generate_ensemble_forecast(
            metric=metric_name,
            historical_data=ts_data,
            external_regressors=train_regressors,
            periods_ahead=test_periods,
            fast_mode=True,  # Use fast mode for validation
        )

        actual = test_data["value"].values
        predicted = [p.value for p in forecast_result.forecast]

        min_len = min(len(actual), len(predicted))
        actual = actual[:min_len]
        predicted = predicted[:min_len]

        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
        mae = float(np.mean(np.abs(actual - predicted)))

        non_zero_mask = actual != 0
        if non_zero_mask.any():
            mape = float(
                np.mean(
                    np.abs(
                        (actual[non_zero_mask] - predicted[: sum(non_zero_mask)])
                        / actual[non_zero_mask]
                    )
                )
                * 100
            )
        else:
            mape = 0.0

        return ForecastAccuracyResult(
            model_type="ensemble",
            rmse=rmse,
            mae=mae,
            mape=mape,
            regressors_used=forecast_result.regressors_used or [],
            periods_tested=min_len,
        )

    except (InsufficientDataError, Exception) as e:
        logger.warning(f"Ensemble forecast failed: {e}")
        return ForecastAccuracyResult(
            model_type="ensemble",
            rmse=0.0,
            mae=0.0,
            mape=100.0,
            periods_tested=0,
        )


# =============================================================================
# Sample Data Generation (for testing without live API)
# =============================================================================


def generate_sample_data() -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Generate synthetic sample data for testing.

    Returns:
        Tuple of (target_df, regressors_dict)
    """
    # Generate 36 months of synthetic data (3 years)
    dates = pd.date_range(start="2022-01-01", periods=36, freq="MS")

    # Target: cement demand with trend and seasonality
    np.random.seed(42)
    trend = np.linspace(100, 120, 36)
    seasonality = 10 * np.sin(2 * np.pi * np.arange(36) / 12)
    noise = np.random.normal(0, 5, 36)
    cement_demand = trend + seasonality + noise

    target_df = pd.DataFrame(
        {
            "date": dates,
            "value": cement_demand,
        }
    )

    # Generate correlated regressors
    regressors = {}

    # Building permits (strongly correlated with 1-month lag)
    regressors["building_permits"] = pd.Series(
        trend * 10 + seasonality * 5 + np.random.normal(0, 20, 36),
        index=dates,
    )

    # Electricity prices (moderately correlated)
    regressors["electricity_price"] = pd.Series(
        50 + 0.2 * cement_demand + np.random.normal(0, 5, 36),
        index=dates,
    )

    # Temperature (seasonal, inversely correlated)
    regressors["temperature"] = pd.Series(
        15 + 10 * np.sin(2 * np.pi * np.arange(36) / 12) + np.random.normal(0, 2, 36),
        index=dates,
    )

    # Mortgage loans (strongly correlated)
    regressors["mortgage_loans"] = pd.Series(
        1000 + trend * 50 + np.random.normal(0, 100, 36),
        index=dates,
    )

    # Diesel prices (weakly correlated)
    regressors["diesel_price"] = pd.Series(
        1.5 + 0.01 * cement_demand + np.random.normal(0, 0.1, 36),
        index=dates,
    )

    return target_df, regressors


# =============================================================================
# Real Data Loading
# =============================================================================


def load_real_cement_data() -> pd.DataFrame:
    """Load real Portuguese cement demand data from ground truth CSV.

    Returns:
        DataFrame with columns: date, value
    """
    csv_path = (
        Path(__file__).parent.parent / "tests" / "ground_truth" / "cement_demand_2020_2024.csv"
    )

    if not csv_path.exists():
        raise FileNotFoundError(f"Cement demand CSV not found: {csv_path}")

    # Read CSV, skip comment lines
    df = pd.read_csv(csv_path, comment="#")
    df["date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={"actual_value": "value"})

    return df[["date", "value"]].sort_values("date").reset_index(drop=True)


def load_secil_business_kpis() -> dict[str, pd.DataFrame]:
    """Load SECIL business KPIs from ground truth CSV.

    Returns:
        Dict of KPI name -> DataFrame with date and value columns
    """
    csv_path = (
        Path(__file__).parent.parent
        / "tests"
        / "ground_truth"
        / "secil_business_kpis_2020_2024.csv"
    )

    if not csv_path.exists():
        raise FileNotFoundError(f"SECIL KPIs CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, comment="#")
    df["date"] = pd.to_datetime(df["date"])

    # Extract each KPI as separate DataFrame
    kpis = {}
    kpi_columns = [
        ("ebitda_eur_ton", "EBITDA (EUR/ton)"),
        ("revenue_eur_m", "Revenue (EUR M)"),
        ("sales_volume_kt", "Sales Volume (kt)"),
        ("variable_margin_eur_ton", "Variable Margin (EUR/ton)"),
        ("electricity_cost_eur_ton", "Electricity Cost (EUR/ton)"),
        ("thermal_cost_eur_ton", "Thermal Cost (EUR/ton)"),
    ]

    for col, display_name in kpi_columns:
        if col in df.columns:
            kpis[display_name] = df[["date", col]].rename(columns={col: "value"}).copy()

    return kpis


async def fetch_real_external_data(
    start_date: date,
    end_date: date,
) -> dict[str, pd.Series]:
    """Fetch real external data from APIs.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Dict of regressor name -> pandas Series with datetime index
    """
    from raglite.external_data.clients import (
        BPstatClient,
        ECBClient,
        EUOilBulletinClient,
        INEClient,
        OMIEClient,
    )

    regressors = {}

    # 1. INE Building Permits
    print("  Fetching INE building permits...")
    try:
        ine = INEClient()
        permits = await ine.fetch_building_permits(start_date, end_date)
        if permits:
            permit_df = pd.DataFrame([{"date": p.date, "value": p.permits_count} for p in permits])
            permit_df = permit_df.groupby("date")["value"].sum()
            permit_df.index = pd.to_datetime(permit_df.index)
            regressors["building_permits"] = permit_df
            print(f"    ✓ {len(permit_df)} months of building permit data")
    except Exception as e:
        print(f"    ✗ INE failed: {e}")

    # 2. BPstat Mortgage Rates
    print("  Fetching BPstat mortgage rates...")
    try:
        bpstat = BPstatClient()
        loans = await bpstat.fetch_mortgage_loans(start_date, end_date)
        print(f"    DEBUG: BPstat returned {len(loans) if loans else 0} records")
        if loans:
            # Model has avg_interest_rate_pct (not interest_rate)
            loan_df = pd.DataFrame(
                [
                    {"date": loan.date, "value": loan.avg_interest_rate_pct}
                    for loan in loans
                    if loan.avg_interest_rate_pct is not None
                ]
            )
            if not loan_df.empty:
                loan_df = loan_df.groupby("date")["value"].mean()
                loan_df.index = pd.to_datetime(loan_df.index)
                regressors["mortgage_rate"] = loan_df
                print(
                    f"    ✓ {len(loan_df)} months of mortgage rate data (range: {loan_df.min():.2f}% - {loan_df.max():.2f}%)"
                )
            else:
                print("    ⚠ BPstat returned records but no interest rate values")
    except Exception as e:
        print(f"    ✗ BPstat failed: {e}")

    # 3. OMIE Electricity Prices (limit to recent 90 days - historical data not available via API)
    print("  Fetching OMIE electricity prices (recent 90 days only)...")
    try:
        omie = OMIEClient()
        # OMIE API returns 404 for historical data - only recent days available
        # Limit to last 90 days to avoid hundreds of 404 errors
        today = date.today()
        omie_start = today - timedelta(days=90)
        omie_end = today - timedelta(days=1)  # Yesterday (today's data may not be ready)

        # Only fetch if end_date is recent enough
        if end_date >= omie_start:
            prices = await omie.fetch_spot_prices(omie_start, omie_end)
            print(f"    DEBUG: OMIE returned {len(prices) if prices else 0} daily records")
            if prices:
                price_df = pd.DataFrame(
                    [{"date": p.date, "value": p.price_eur_mwh} for p in prices]
                )
                # Aggregate to monthly
                price_df["date"] = pd.to_datetime(price_df["date"])
                price_df["month"] = price_df["date"].dt.to_period("M").dt.to_timestamp()
                monthly = price_df.groupby("month")["value"].mean()
                regressors["electricity_price"] = monthly
                print(
                    f"    ✓ {len(monthly)} months of electricity price data (avg: €{monthly.mean():.2f}/MWh)"
                )
            else:
                print("    ⚠ OMIE returned no data (API may only provide very recent days)")
        else:
            print("    ⚠ Skipping OMIE - date range too old (OMIE only has recent ~90 days)")
    except Exception as e:
        print(f"    ✗ OMIE failed: {e}")

    # 4. EU Oil Bulletin Diesel Prices
    print("  Fetching EU Oil Bulletin diesel prices...")
    try:
        eu_oil = EUOilBulletinClient()
        diesel = await eu_oil.fetch_diesel_prices(start_date, end_date)
        print(f"    DEBUG: EU Oil returned {len(diesel) if diesel else 0} records")
        if diesel:
            diesel_df = pd.DataFrame([{"date": d.date, "value": d.price_eur_litre} for d in diesel])
            # Aggregate to monthly
            diesel_df["date"] = pd.to_datetime(diesel_df["date"])
            diesel_df["month"] = diesel_df["date"].dt.to_period("M").dt.to_timestamp()
            monthly = diesel_df.groupby("month")["value"].mean()
            regressors["diesel_price"] = monthly
            print(
                f"    ✓ {len(monthly)} months of diesel price data (range: €{monthly.min():.2f} - €{monthly.max():.2f}/L)"
            )
    except Exception as e:
        print(f"    ✗ EU Oil failed: {e}")

    # 5. ECB EURIBOR Rates (non-seasonal financial indicator)
    # Key for cement industry: EURIBOR affects construction financing costs
    print("  Fetching ECB EURIBOR rates (3M tenor)...")
    try:
        ecb = ECBClient()
        rates = await ecb.fetch_euribor(start_date, end_date, tenor="3M")
        print(f"    DEBUG: ECB returned {len(rates) if rates else 0} records")
        if rates:
            rate_df = pd.DataFrame([{"date": r.date, "value": r.rate_pct} for r in rates])
            rate_df["date"] = pd.to_datetime(rate_df["date"])
            rate_df = rate_df.set_index("date")["value"]
            regressors["euribor_3m"] = rate_df
            print(
                f"    ✓ {len(rate_df)} months of EURIBOR data (range: {rate_df.min():.2f}% - {rate_df.max():.2f}%)"
            )
    except Exception as e:
        print(f"    ✗ ECB EURIBOR failed: {e}")

    return regressors


def align_time_series(
    target_df: pd.DataFrame,
    regressors: dict[str, pd.Series],
) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Align target and regressor time series to common date range.

    Args:
        target_df: Target metric DataFrame with date and value columns
        regressors: Dict of regressor series

    Returns:
        Tuple of aligned (target_df, regressors)
    """
    if not regressors:
        return target_df, regressors

    # Find common date range
    target_dates = set(target_df["date"].dt.to_period("M"))

    # Filter regressors to common dates
    aligned_regressors = {}
    for name, series in regressors.items():
        if series.empty:
            continue

        # Convert index to period for comparison
        series_periods = series.index.to_period("M")
        common_periods = target_dates.intersection(set(series_periods))

        if len(common_periods) > 0:
            mask = series_periods.isin(common_periods)
            aligned_regressors[name] = series[mask]
            print(f"  {name}: {len(aligned_regressors[name])} aligned points")

    # Filter target to periods where we have at least one regressor
    if aligned_regressors:
        regressor_periods = set()
        for series in aligned_regressors.values():
            regressor_periods.update(series.index.to_period("M"))

        target_df = target_df[target_df["date"].dt.to_period("M").isin(regressor_periods)].copy()

    return target_df, aligned_regressors


# =============================================================================
# Story 6.8 Decision Logic
# =============================================================================


def make_story_6_8_decision(
    univariate_mape: float,
    multivariate_mape: float,
    ensemble_mape: float | None = None,
) -> tuple[str, str]:
    """Determine if Story 6.8 (Tier 2 sources) is needed.

    Decision Gate:
    - MAPE <= 10% -> SKIP (target accuracy achieved)
    - MAPE <= 12% -> SKIP (threshold met)
    - MAPE > 12% -> EXECUTE (need Tier 2 sources)

    Args:
        univariate_mape: Baseline MAPE without external regressors
        multivariate_mape: MAPE with Tier 1 external regressors
        ensemble_mape: Optional ensemble model MAPE

    Returns:
        Tuple of (decision, rationale)
    """
    # Use best available accuracy
    best_mape = multivariate_mape
    best_model = "multivariate"

    if ensemble_mape is not None and ensemble_mape < best_mape:
        best_mape = ensemble_mape
        best_model = "ensemble"

    improvement_pct = (
        ((univariate_mape - best_mape) / univariate_mape * 100) if univariate_mape > 0 else 0
    )

    if best_mape <= 10.0:
        decision = "SKIP"
        rationale = (
            f"Target accuracy achieved! {best_model.capitalize()} model achieved "
            f"MAPE={best_mape:.1f}% (<=10% target). "
            f"Improvement vs univariate baseline: {improvement_pct:.1f}%. "
            f"Story 6.8 (Tier 2 sources) is NOT needed."
        )
    elif best_mape <= 12.0:
        decision = "SKIP"
        rationale = (
            f"Threshold accuracy met. {best_model.capitalize()} model achieved "
            f"MAPE={best_mape:.1f}% (<=12% threshold). "
            f"Improvement vs univariate baseline: {improvement_pct:.1f}%. "
            f"Story 6.8 (Tier 2 sources) can be SKIPPED - consider for future optimization."
        )
    else:
        decision = "EXECUTE"
        rationale = (
            f"Below threshold accuracy. {best_model.capitalize()} model achieved "
            f"MAPE={best_mape:.1f}% (>12% threshold). "
            f"Improvement vs univariate baseline: {improvement_pct:.1f}%. "
            f"Story 6.8 (Tier 2 sources) is RECOMMENDED to improve accuracy."
        )

    return decision, rationale


# =============================================================================
# Main Validation Flow
# =============================================================================


async def run_validation(
    live_api: bool = False,
    verbose: bool = False,
    skip_forecast: bool = False,
    use_real_data: bool = False,
) -> ValidationReport:
    """Run complete validation suite.

    Args:
        live_api: Whether to call actual external APIs
        verbose: Show detailed output
        skip_forecast: Skip forecasting tests (API tests only)
        use_real_data: Use real cement demand data and fetch real external data

    Returns:
        Complete ValidationReport
    """
    from datetime import datetime

    report = ValidationReport(timestamp=datetime.now().isoformat())

    # Phase 1: Client connectivity tests
    report.client_tests = await run_all_client_tests(live_api)

    # Summary
    passed = sum(1 for t in report.client_tests if t.success)
    total = len(report.client_tests)
    print(f"\nClient Tests: {passed}/{total} passed")

    if skip_forecast:
        report.overall_status = "PARTIAL" if passed == total else "FAIL"
        report.story_6_8_decision = "UNKNOWN"
        report.decision_rationale = "Forecasting tests skipped - cannot determine accuracy"
        return report

    # Phase 2: Generate/load sample data for forecasting tests
    print("\n" + "=" * 60)
    print("PHASE 2: FORECASTING ACCURACY TESTS")
    print("=" * 60 + "\n")

    if use_real_data:
        print("Loading REAL cement demand data from ground truth CSV...")
        try:
            target_df = load_real_cement_data()
            print(f"Loaded {len(target_df)} months of real cement demand data (2020-2024)")
            print(f"  Date range: {target_df['date'].min()} to {target_df['date'].max()}")
            print(
                f"  Value range: {target_df['value'].min():.0f} - {target_df['value'].max():.0f} kt/month"
            )

            # Fetch real external data
            print("\nFetching REAL external data from APIs...")
            start_date = target_df["date"].min().date()
            end_date = target_df["date"].max().date()
            regressors = await fetch_real_external_data(start_date, end_date)

            if regressors:
                print(f"\nFetched {len(regressors)} external regressors")

                # Align time series
                print("\nAligning time series...")
                target_df, regressors = align_time_series(target_df, regressors)
                print(f"Aligned to {len(target_df)} common months")
            else:
                print("\n⚠️  No external data fetched - falling back to synthetic regressors")
                _, regressors = generate_sample_data()
                # Align synthetic regressors to real target dates
                dates = target_df["date"]
                for name in regressors:
                    regressors[name] = regressors[name].reindex(dates)

        except Exception as e:
            print(f"⚠️  Failed to load real data: {e}")
            print("Falling back to synthetic data...")
            target_df, regressors = generate_sample_data()
    else:
        print("Generating SYNTHETIC sample data for forecasting validation...")
        target_df, regressors = generate_sample_data()
        print(f"Generated {len(target_df)} months of synthetic cement demand data")
        print(f"Generated {len(regressors)} external regressors")

    # Phase 3: Correlation analysis
    print("\n--- Correlation Analysis ---\n")
    target_series = pd.Series(target_df["value"].values, index=pd.to_datetime(target_df["date"]))
    report.correlations = calculate_correlations(target_series, regressors)

    for corr in report.correlations:
        print(
            f"  {corr.regressor_name}: r={corr.correlation:.3f} (lag={corr.lag_months}m) -> {corr.recommendation}"
        )

    # Phase 4: Forecast accuracy tests
    print("\n--- Forecast Accuracy Tests ---\n")

    print("Testing univariate forecast (baseline)...")
    report.univariate_accuracy = await test_univariate_forecast(target_df)
    print(f"  Univariate MAPE: {report.univariate_accuracy.mape:.1f}%")

    print("Testing multivariate forecast (with Tier 1 regressors)...")
    report.multivariate_accuracy = await test_multivariate_forecast(target_df, regressors)
    print(f"  Multivariate MAPE: {report.multivariate_accuracy.mape:.1f}%")
    if report.multivariate_accuracy.regressors_used:
        print(f"  Regressors used: {', '.join(report.multivariate_accuracy.regressors_used)}")

    print("Testing ensemble forecast (Prophet + Linear + XGBoost)...")
    report.ensemble_accuracy = await test_ensemble_forecast(target_df, regressors)
    print(f"  Ensemble MAPE: {report.ensemble_accuracy.mape:.1f}%")

    # Phase 4b: SECIL Business KPI Forecasts (key Performance Review variables)
    print("\n" + "=" * 60)
    print("SECIL BUSINESS KPI FORECASTING")
    print("=" * 60)
    print("\nTesting forecasting accuracy on key SECIL Performance Review metrics:")
    print("(These are the variables cement company employees want to predict)\n")

    try:
        secil_kpis = load_secil_business_kpis()
        kpi_results = await test_secil_kpi_forecasts(secil_kpis)

        # Categorize results
        seasonal_kpis = ["Revenue (EUR M)", "Sales Volume (kt)"]
        non_seasonal_kpis = ["EBITDA (EUR/ton)", "Variable Margin (EUR/ton)"]
        volatile_kpis = ["Electricity Cost (EUR/ton)", "Thermal Cost (EUR/ton)"]

        print("📈 SEASONAL KPIs (follow cement demand patterns):")
        for kpi in seasonal_kpis:
            if kpi in kpi_results and kpi_results[kpi].periods_tested > 0:
                r = kpi_results[kpi]
                status = "✅" if r.mape <= 10 else "⚠️" if r.mape <= 20 else "❌"
                print(f"  {status} {kpi}: MAPE {r.mape:.1f}%  |  MAE {r.mae:.2f}")

        print("\n📊 NON-SEASONAL KPIs (business cycle driven):")
        for kpi in non_seasonal_kpis:
            if kpi in kpi_results and kpi_results[kpi].periods_tested > 0:
                r = kpi_results[kpi]
                status = "✅" if r.mape <= 10 else "⚠️" if r.mape <= 20 else "❌"
                print(f"  {status} {kpi}: MAPE {r.mape:.1f}%  |  MAE {r.mae:.2f}")

        print("\n⚡ VOLATILE KPIs (energy market driven - hardest to predict):")
        for kpi in volatile_kpis:
            if kpi in kpi_results and kpi_results[kpi].periods_tested > 0:
                r = kpi_results[kpi]
                status = "✅" if r.mape <= 15 else "⚠️" if r.mape <= 25 else "❌"
                print(f"  {status} {kpi}: MAPE {r.mape:.1f}%  |  MAE {r.mae:.2f}")

        # Summary statistics
        valid_results = [r for r in kpi_results.values() if r.periods_tested > 0]
        if valid_results:
            avg_mape = np.mean([r.mape for r in valid_results])
            best_kpi = min(
                kpi_results.items(), key=lambda x: x[1].mape if x[1].periods_tested > 0 else 999
            )
            worst_kpi = max(
                kpi_results.items(), key=lambda x: x[1].mape if x[1].periods_tested > 0 else 0
            )

            print("\n📋 SUMMARY:")
            print(f"  Average MAPE across all KPIs: {avg_mape:.1f}%")
            print(f"  Best forecast: {best_kpi[0]} ({best_kpi[1].mape:.1f}%)")
            print(f"  Hardest to forecast: {worst_kpi[0]} ({worst_kpi[1].mape:.1f}%)")

            # Assessment
            if avg_mape <= 10:
                print("\n  ✅ EXCELLENT: Forecasting tool performs well on SECIL business KPIs")
            elif avg_mape <= 15:
                print("\n  ✅ GOOD: Forecasting tool is useful for business planning")
            elif avg_mape <= 20:
                print("\n  ⚠️  MODERATE: Tool useful for directional forecasts, consider ensemble")
            else:
                print("\n  ❌ POOR: May need additional regressors or model improvements")

    except FileNotFoundError as e:
        print(f"  ⚠️  SECIL KPIs data not found: {e}")
        print("  Skipping SECIL KPI forecasting test")

    # Phase 5: Story 6.8 Decision Gate
    print("\n" + "=" * 60)
    print("PHASE 3: STORY 6.8 DECISION GATE")
    print("=" * 60 + "\n")

    decision, rationale = make_story_6_8_decision(
        univariate_mape=report.univariate_accuracy.mape,
        multivariate_mape=report.multivariate_accuracy.mape,
        ensemble_mape=report.ensemble_accuracy.mape if report.ensemble_accuracy else None,
    )

    report.story_6_8_decision = decision
    report.decision_rationale = rationale

    # Print decision with visual emphasis
    if decision == "SKIP":
        print("\u2705 DECISION: SKIP Story 6.8")
    else:
        print("\u26a0\ufe0f  DECISION: EXECUTE Story 6.8")

    print(f"\n{rationale}")

    # Overall status
    if passed == total and decision == "SKIP":
        report.overall_status = "PASS"
    elif passed >= total * 0.75:
        report.overall_status = "PARTIAL"
    else:
        report.overall_status = "FAIL"

    return report


def print_summary(report: ValidationReport) -> None:
    """Print final validation summary."""
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    print(f"\nTimestamp: {report.timestamp}")
    print(f"Overall Status: {report.overall_status}")

    # Client tests summary
    passed = sum(1 for t in report.client_tests if t.success)
    total = len(report.client_tests)
    print(f"\nClient Tests: {passed}/{total} passed")

    # Accuracy summary
    if report.univariate_accuracy:
        print(f"\nUnivariate Baseline MAPE: {report.univariate_accuracy.mape:.1f}%")
    if report.multivariate_accuracy:
        print(f"Multivariate MAPE: {report.multivariate_accuracy.mape:.1f}%")
    if report.ensemble_accuracy:
        print(f"Ensemble MAPE: {report.ensemble_accuracy.mape:.1f}%")

    # Decision
    print(f"\n{'=' * 60}")
    print(f"STORY 6.8 DECISION: {report.story_6_8_decision}")
    print(f"{'=' * 60}")
    print(f"\n{report.decision_rationale}")


def export_to_json(report: ValidationReport, output_path: Path) -> None:
    """Export validation report to JSON."""
    import dataclasses

    def serialize(obj: Any) -> Any:
        if dataclasses.is_dataclass(obj):
            return {k: serialize(v) for k, v in dataclasses.asdict(obj).items()}
        elif isinstance(obj, (date, pd.Timestamp)):
            return str(obj)
        elif isinstance(obj, list):
            return [serialize(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        return obj

    with open(output_path, "w") as f:
        json.dump(serialize(report), f, indent=2)

    print(f"\nReport exported to: {output_path}")


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate external data sources and forecasting integration"
    )
    parser.add_argument(
        "--live-api",
        action="store_true",
        help="Call actual external APIs (requires network/API keys)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--export-json",
        type=Path,
        help="Export results to JSON file",
    )
    parser.add_argument(
        "--skip-forecast",
        action="store_true",
        help="Skip forecasting tests (API tests only)",
    )
    parser.add_argument(
        "--real-data",
        action="store_true",
        help="Use real cement demand data and fetch real external data from APIs",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("EXTERNAL DATA & FORECASTING VALIDATION")
    print("Story 6.7 Pre-Validation for Story 6.8 Decision Gate")
    print("=" * 60)

    if args.real_data:
        print("\n📊 REAL DATA MODE - Using ground truth cement demand + live API data")
    elif args.live_api:
        print("\n⚠️  LIVE API MODE - Will call external services (synthetic target data)")
    else:
        print("\nℹ️  MOCK MODE - Use --live-api to call real APIs, --real-data for full validation")

    # Run validation
    report = asyncio.run(
        run_validation(
            live_api=args.live_api or args.real_data,  # real-data implies live-api
            verbose=args.verbose,
            skip_forecast=args.skip_forecast,
            use_real_data=args.real_data,
        )
    )

    # Print summary
    print_summary(report)

    # Export if requested
    if args.export_json:
        export_to_json(report, args.export_json)

    # Return code based on status
    if report.overall_status == "PASS":
        return 0
    elif report.overall_status == "PARTIAL":
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
