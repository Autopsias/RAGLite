"""Shared fixtures for Epic 6 accuracy regression tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest

if TYPE_CHECKING:
    from raglite.shared.models import TimeSeriesData

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


@pytest.fixture
async def real_external_regressors(
    train_test_split: tuple[pd.DataFrame, pd.DataFrame],
) -> dict[str, pd.Series] | None:
    """Fetch real external regressors from Story 6.1 API clients.

    This fixture fetches HISTORICAL data directly from the INE API (not via
    refresh_source, which only fetches the last 120 days). The INE API supports
    querying historical data going back many years.

    For accuracy validation, we need the full training period (2020-2023) to have
    real external regressors that align with our ground truth data.

    Returns None if external data is unavailable (network issues, API limits, etc.)
    Tests using this fixture should handle the None case gracefully.
    """
    try:
        from raglite.external_data.clients.ine import INEClient

        train_df, _ = train_test_split
        start_date = train_df["date"].min().date()
        end_date = train_df["date"].max().date()

        regressors: dict[str, pd.Series] = {}

        # Fetch historical INE Construction Output (directly, not via refresh_source)
        try:
            client = INEClient()
            # Override test timeout since we need real network access
            client.timeout = 30.0  # 30 seconds for historical data

            output_data = await client.fetch_construction_output(
                start_date=start_date,
                end_date=end_date,
            )

            if output_data:
                dates = pd.to_datetime([d.date for d in output_data])
                values = [float(d.index_value) for d in output_data]
                regressors["ine_construction_output"] = pd.Series(values, index=dates)

        except Exception as e:
            # Network issues, API limits, etc.
            print(f"Failed to fetch INE data: {e}")
            return None

        # Optionally fetch IPMA temperature data (secondary regressor)
        try:
            from raglite.external_data.clients.ipma import IPMAClient

            ipma_client = IPMAClient()
            ipma_client.timeout = 30.0

            observations = await ipma_client.fetch_observations(
                start_date=start_date,
                end_date=end_date,
            )

            if observations:
                dates = pd.to_datetime([o.date for o in observations])
                temps = [float(o.temperature_c) for o in observations if o.temperature_c]
                if temps and len(temps) == len(dates):
                    regressors["temperature"] = pd.Series(temps, index=dates)

        except Exception:
            # Temperature is optional - continue without it
            pass

        return regressors if regressors else None

    except Exception as e:
        print(f"real_external_regressors failed: {e}")
        return None


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
