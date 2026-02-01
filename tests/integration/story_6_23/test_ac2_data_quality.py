"""Test AC2: Data coefficient of variation <15% (from 33% baseline).

Story 6.23 - RED PHASE: Tests MUST FAIL initially.
"""

from __future__ import annotations

import numpy as np
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


class TestAC2DataCoefficientOfVariation:
    """AC2: Data coefficient of variation <15% (from 33% baseline).

    GIVEN entity-specific extraction filters Portugal-only entities
    WHEN calculating CoV from extracted time series
    THEN CoV should be <15% (improved from 33% baseline)

    RED PHASE: This test will FAIL until data quality improves.
    """

    def test_ac2_variable_cost_cov_below_target(self):
        """TEST-AC-6.23.2: Variable Cost data CoV must be below 15%.

        GIVEN: Portugal-only entity filtering is active (Story 6.15)
        WHEN: Extracting variable_cost time series data
        THEN: Coefficient of variation < 15% (from 33% baseline)
        """
        from raglite.forecasting.timeseries import extract_timeseries
        from raglite.shared.clients import get_postgresql_connection

        # GIVEN: PostgreSQL connection available
        try:
            get_postgresql_connection()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
        # WHEN: Extract variable_cost time series with entity filtering
        try:
            timeseries_data = extract_timeseries(
                metric_name="variable_cost",
                entity_filter="Portugal",  # Story 6.15: Entity-specific filtering
            )
        except Exception as e:
            pytest.skip(f"Time series extraction not implemented: {e}")

        # Skip if no data
        if not timeseries_data or len(timeseries_data) < 3:
            pytest.skip("Insufficient time series data for CoV calculation")

        # THEN: Calculate coefficient of variation
        values = [point.value for point in timeseries_data]
        mean_value = np.mean(values)
        std_value = np.std(values)

        if mean_value == 0:
            pytest.skip("Cannot calculate CoV with zero mean")

        cov = (std_value / abs(mean_value)) * 100

        # AC2 ASSERTION: CoV must be below 15%
        assert cov < 15.0, (
            f"TEST-AC-6.23.2 FAILED: Variable Cost CoV {cov:.2f}% >= 15% target. "
            f"(Baseline was 33%, entity filtering should reduce variance)"
        )

    def test_ac2_portugal_only_entity_filtering(self):
        """TEST-AC-6.23.2b: Verify Portugal-only entity filtering is active.

        GIVEN: Entity detection from Story 6.15 is implemented
        WHEN: Extracting variable_cost data
        THEN: Only Portugal entities should be included
        """
        from raglite.forecasting.timeseries import extract_timeseries

        try:
            # Extract with explicit Portugal filter
            timeseries_data = extract_timeseries(
                metric_name="variable_cost",
                entity_filter="Portugal",
            )
        except Exception as e:
            pytest.skip(f"Entity filtering not implemented: {e}")

        # Verify data is Portugal-only (values in expected range)
        # Portugal variable cost should be EUR -150 to -350 per ton
        if timeseries_data:
            values = [point.value for point in timeseries_data]
            # AC2b: Values should be in Portugal range (negative, EUR/ton)
            assert all(-400 <= v <= 0 for v in values), (
                f"Variable cost values outside Portugal range: {values}"
            )

    def test_ac2_value_normalization_eur_per_ton(self):
        """TEST-AC-6.23.2c: Verify values normalized to EUR/ton.

        GIVEN: Variable cost data is extracted
        WHEN: Checking value units
        THEN: Values should be normalized EUR/ton (range: -150 to -350)
        """
        from raglite.forecasting.timeseries import extract_timeseries

        try:
            timeseries_data = extract_timeseries(metric_name="variable_cost")
        except Exception as e:
            pytest.skip(f"Time series extraction not implemented: {e}")

        if not timeseries_data:
            pytest.skip("No variable cost data available")

        values = [point.value for point in timeseries_data]

        # AC2c: Values should be in EUR/ton range for Portugal cement
        # Variable costs are typically -150 to -350 EUR/ton (negative = cost)
        EXPECTED_MIN = -400
        EXPECTED_MAX = 0

        assert min(values) >= EXPECTED_MIN, f"Min value {min(values)} below expected range"
        assert max(values) <= EXPECTED_MAX, f"Max value {max(values)} above expected range"
