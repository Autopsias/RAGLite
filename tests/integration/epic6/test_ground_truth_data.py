"""Tests for ground truth data integrity and validation."""

from __future__ import annotations

import pandas as pd
import pytest

from tests.integration.epic6.conftest import GROUND_TRUTH_PATH

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


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
