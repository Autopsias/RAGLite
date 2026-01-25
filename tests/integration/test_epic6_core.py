"""Integration tests for Story 6.7: Epic 6 Accuracy Regression Gate - Core Tests.

Tests multi-variate forecasting accuracy to prevent regression.
CI/CD gate: Fail if MAPE exceeds 12% (AC6).

Requires running PostgreSQL and Qdrant containers.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest

from raglite.forecasting.ensemble import generate_ensemble_forecast
from raglite.forecasting.hybrid import generate_forecast

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData

# Set DYLD_LIBRARY_PATH for XGBoost on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/opt/libomp/lib")

# Mark all tests as integration tests that preserve collection state
# requires_ml_stack: Loads full ML stack for multi-variate forecasting (~3-4GB)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
    pytest.mark.requires_ml_stack,
]

# Ground truth file path
GROUND_TRUTH_PATH = Path("tests/ground_truth/cement_demand_2020_2024.csv")

# Decision gate thresholds (AC5/AC6)
MAPE_CI_GATE = 0.12  # CI fails if MAPE > 12%
MAPE_WARNING = 0.10  # Warning threshold


@pytest.fixture(scope="module")
def ground_truth_df() -> pd.DataFrame:
    """Load ground truth data from CSV.

    This fixture is module-scoped for efficiency (loaded once per test file).
    """
    if not GROUND_TRUTH_PATH.exists():
        pytest.skip(f"Ground truth file not found: {GROUND_TRUTH_PATH}")

    # Read CSV, skipping comment lines
    df = pd.read_csv(GROUND_TRUTH_PATH, comment="#", parse_dates=["date"])
    return df


@pytest.fixture
def train_test_split(ground_truth_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split ground truth into train (48 months) and test (12 months)."""
    train_size = 48
    train_df = ground_truth_df.iloc[:train_size]
    test_df = ground_truth_df.iloc[train_size:]
    return train_df, test_df


@pytest.fixture
def train_time_series(train_test_split: tuple[pd.DataFrame, pd.DataFrame]) -> TimeSeriesData:
    """Create TimeSeriesData from training data."""
    from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

    train_df, _ = train_test_split
    points = [
        TimeSeriesPoint(
            date=row["date"].to_pydatetime(),
            value=row["actual_value"],
            label=row["date"].strftime("%b %Y"),
        )
        for _, row in train_df.iterrows()
    ]
    return TimeSeriesData(
        metric_name="cement_demand",
        points=points,
        interval="monthly",
        source_documents=["cement_demand_2020_2024.csv"],
    )


@pytest.fixture
def synthetic_regressors(
    train_test_split: tuple[pd.DataFrame, pd.DataFrame],
) -> dict[str, pd.Series]:
    """Create synthetic external regressors for validation.

    These simulate external data sources (Story 6.1) for testing.
    For real accuracy validation, use the real_external_regressors fixture.
    """
    train_df, _ = train_test_split
    dates = pd.DatetimeIndex(train_df["date"])
    values = train_df["actual_value"].values

    regressors: dict[str, pd.Series] = {}

    # Construction index (correlated proxy with noise)
    np.random.seed(42)  # Reproducible
    noise = np.random.normal(0, 10, len(values))
    construction_index = values * 0.95 + noise
    regressors["construction_index"] = pd.Series(construction_index, index=dates)

    # Seasonal indicator
    months = train_df["date"].dt.month.values
    seasonal = np.where((months >= 5) & (months <= 9), 1.0, 0.0)
    regressors["seasonal_high"] = pd.Series(seasonal, index=dates)

    # Temperature proxy
    temp_by_month = {
        1: 10,
        2: 11,
        3: 13,
        4: 15,
        5: 18,
        6: 21,
        7: 24,
        8: 24,
        9: 21,
        10: 17,
        11: 13,
        12: 10,
    }
    temps = [temp_by_month[m] for m in months]
    regressors["temperature"] = pd.Series(temps, index=dates)

    return regressors


def calculate_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Calculate Mean Absolute Percentage Error.

    Args:
        actual: Actual values
        predicted: Predicted values

    Returns:
        MAPE as a decimal (e.g., 0.10 = 10%)
    """
    epsilon = 1e-8
    return float(np.mean(np.abs((actual - predicted) / np.maximum(actual, epsilon))))


class TestGroundTruthData:
    """Tests for ground truth data integrity."""

    def test_ground_truth_file_exists(self) -> None:
        """AC1: Ground truth CSV must exist."""
        assert GROUND_TRUTH_PATH.exists(), f"Ground truth file not found: {GROUND_TRUTH_PATH}"

    def test_ground_truth_has_minimum_scenarios(self, ground_truth_df: pd.DataFrame) -> None:
        """AC1: Ground truth must have 20+ scenarios."""
        assert len(ground_truth_df) >= 20, (
            f"Ground truth has only {len(ground_truth_df)} scenarios, need 20+"
        )

    def test_ground_truth_covers_2020_2024(self, ground_truth_df: pd.DataFrame) -> None:
        """AC1: Ground truth must cover 2020-2024."""
        min_date = ground_truth_df["date"].min()
        max_date = ground_truth_df["date"].max()

        assert min_date.year <= 2020, f"Data starts in {min_date.year}, should include 2020"
        assert max_date.year >= 2024, f"Data ends in {max_date.year}, should include 2024"

    def test_ground_truth_has_source_attribution(self, ground_truth_df: pd.DataFrame) -> None:
        """AC1: Ground truth must have source attribution."""
        assert "source" in ground_truth_df.columns, "Missing 'source' column"
        assert ground_truth_df["source"].notna().all(), "Some rows missing source attribution"

    def test_ground_truth_covers_seasonal_patterns(self, ground_truth_df: pd.DataFrame) -> None:
        """AC1: Data covers seasonal patterns (Q1 low, Q2-Q3 high)."""
        # Group by month and check for seasonal variation
        ground_truth_df["month"] = ground_truth_df["date"].dt.month
        monthly_avg = ground_truth_df.groupby("month")["actual_value"].mean()

        # Q1 months (Jan, Feb) should be lower than Q2-Q3 (May-Sept)
        q1_avg = monthly_avg[[1, 2]].mean()
        q2q3_avg = monthly_avg[[5, 6, 7, 8, 9]].mean()

        assert q2q3_avg > q1_avg, (
            f"Seasonal pattern not evident: Q1 avg={q1_avg:.1f}, Q2-Q3 avg={q2q3_avg:.1f}"
        )

    def test_ground_truth_covers_economic_shocks(self, ground_truth_df: pd.DataFrame) -> None:
        """AC1: Data covers economic shocks (COVID-2020, energy crisis 2022)."""
        # Check COVID period (Mar-May 2020)
        covid_data = ground_truth_df[
            (ground_truth_df["date"].dt.year == 2020)
            & (ground_truth_df["date"].dt.month.isin([3, 4, 5]))
        ]
        assert len(covid_data) == 3, "Missing COVID period data (Mar-May 2020)"

        # Check energy crisis period (Q4 2022)
        energy_crisis_data = ground_truth_df[
            (ground_truth_df["date"].dt.year == 2022)
            & (ground_truth_df["date"].dt.month.isin([10, 11, 12]))
        ]
        assert len(energy_crisis_data) == 3, "Missing energy crisis data (Q4 2022)"


class TestBaselineForecast:
    """Tests for Epic 4 baseline (Prophet univariate)."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_baseline_forecast_runs(
        self,
        train_time_series: TimeSeriesData,
        train_test_split: tuple[pd.DataFrame, pd.DataFrame],
    ) -> None:
        """AC2: Baseline forecast runs without errors."""
        _, test_df = train_test_split

        # Patch where the function is imported (ensemble.py), not the alias in __init__.py
        with patch(
            "raglite.forecasting.hybrid.ensemble.ensure_historical_data",
            new_callable=AsyncMock,
            return_value=train_time_series,
        ):
            result = await generate_forecast(
                metric="cement_demand",
                periods_ahead=len(test_df),
                external_regressors=None,
                frequency="M",
            )

        assert result is not None
        assert len(result.forecast) >= len(test_df)


class TestMultivariateForecast:
    """Tests for Story 6.3 multivariate forecasting."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multivariate_forecast_runs(
        self,
        train_time_series: TimeSeriesData,
        train_test_split: tuple[pd.DataFrame, pd.DataFrame],
        synthetic_regressors: dict[str, pd.Series],
    ) -> None:
        """AC2: Multivariate forecast runs without errors."""
        _, test_df = train_test_split

        # Patch where the function is imported (ensemble.py), not the alias in __init__.py
        with patch(
            "raglite.forecasting.hybrid.ensemble.ensure_historical_data",
            new_callable=AsyncMock,
            return_value=train_time_series,
        ):
            result = await generate_forecast(
                metric="cement_demand",
                periods_ahead=len(test_df),
                external_regressors=synthetic_regressors,
                frequency="M",
            )

        assert result is not None
        assert len(result.forecast) >= len(test_df)


class TestEnsembleForecast:
    """Tests for Story 6.4 ensemble forecasting."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_ensemble_forecast_runs(
        self,
        train_time_series: TimeSeriesData,
        train_test_split: tuple[pd.DataFrame, pd.DataFrame],
        synthetic_regressors: dict[str, pd.Series],
    ) -> None:
        """AC2: Ensemble forecast runs without errors."""
        _, test_df = train_test_split

        # Epic 8 API change: historical_data is now a required positional parameter
        result = await generate_ensemble_forecast(
            metric="cement_demand",
            historical_data=train_time_series,  # Required param (Epic 8)
            external_regressors=synthetic_regressors,
            periods_ahead=len(test_df),
            fast_mode=True,
        )

        assert result is not None
        assert len(result.forecast) >= len(test_df)
