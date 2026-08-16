"""Integration tests for Variable Cost coefficient of variation (Story 6.15).

Tests AC2: Portugal-only extraction produces <15% coefficient of variation.
"""

import statistics

import pytest

# Mark all tests as integration tests and slow
# All tests are read-only (query operations only) - skip cleanup overhead
pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.preserve_collection]


class TestVariableCostCoefficientOfVariation:
    """Test Portugal-only Variable Cost CV reduction (AC2).

    Given: Variable Cost time series extracted from financial documents
    When: Filtering to Portugal-only data with entity detection enabled
    Then: The coefficient of variation is <15% (vs 33% current mixed-entity)
    """

    @pytest.mark.asyncio
    async def test_ac2_portugal_only_cv_under_15_percent(self) -> None:
        """AC2: Portugal-only CV < 15%.

        Given: Variable Cost data extracted with entity='portugal' filter
        When: Calculating coefficient of variation (CV = stdev/mean * 100)
        Then: CV is <15% (improved from 33% when mixing entities)

        Note: Requires production data with Variable Cost information.
        Use TEST_USE_FULL_PDF=true to run with 160-page production PDF.
        """
        from raglite.forecasting.timeseries import extract_variable_cost_from_qdrant_chunks

        # Extract Variable Cost with Portugal entity filter
        data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")

        if data is None:
            pytest.skip(
                "No Variable Cost data available in test collection. "
                "Run with TEST_USE_FULL_PDF=true to use production PDF with Variable Cost data."
            )

        if len(data.points) < 6:
            pytest.skip(
                f"Insufficient data points: {len(data.points)} (need >=6). "
                "Run with TEST_USE_FULL_PDF=true for comprehensive data."
            )

        # Extract absolute values (costs are negative)
        values = [abs(p.value) for p in data.points]

        # Calculate coefficient of variation
        mean_val = statistics.mean(values)
        stdev_val = statistics.stdev(values)
        cv = (stdev_val / mean_val) * 100

        assert cv < 15, (
            f"CV {cv:.1f}% exceeds 15% target. "
            f"Mean: {mean_val:.1f}, StdDev: {stdev_val:.1f}. "
            f"Values: {values}"
        )

    @pytest.mark.asyncio
    async def test_ac2_entity_filter_reduces_variability(self) -> None:
        """AC2: Entity filtering reduces CV compared to mixed-entity extraction.

        Given: Variable Cost extraction with and without entity filter
        When: Comparing CV values
        Then: Filtered CV < Unfiltered CV (proves entity mixing causes variance)
        """
        from raglite.forecasting.timeseries import extract_variable_cost_from_qdrant_chunks

        # Extract with Portugal filter
        portugal_data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")

        # Extract without filter (all entities mixed)
        mixed_data = await extract_variable_cost_from_qdrant_chunks(entity=None)

        # Skip if either extraction failed
        if portugal_data is None or mixed_data is None:
            pytest.skip("Insufficient data for comparison test")

        if len(portugal_data.points) < 3 or len(mixed_data.points) < 3:
            pytest.skip("Insufficient data points for CV calculation")

        # Calculate CVs
        portugal_values = [abs(p.value) for p in portugal_data.points]
        portugal_cv = (statistics.stdev(portugal_values) / statistics.mean(portugal_values)) * 100

        mixed_values = [abs(p.value) for p in mixed_data.points]
        mixed_cv = (statistics.stdev(mixed_values) / statistics.mean(mixed_values)) * 100

        # Portugal-only CV should be lower than mixed
        assert portugal_cv < mixed_cv, (
            f"Entity filtering did not reduce CV. "
            f"Portugal CV: {portugal_cv:.1f}%, Mixed CV: {mixed_cv:.1f}%"
        )


class TestEurTonRangeValidation:
    """Test EUR/ton range validation for Portugal Variable Cost (AC3).

    Given: A Variable Cost value extracted from a financial document
    When: The value is from Portugal-only data
    Then: The value falls within the valid EUR/ton range (-150 to -350)
    """

    @pytest.mark.asyncio
    async def test_ac3_all_values_in_eur_ton_range(self) -> None:
        """AC3: All Portugal Variable Cost values in EUR/ton range (-150 to -350).

        Given: Variable Cost data extracted with entity='portugal' filter
        When: Validating each value
        Then: All values fall within -350 <= value <= -150
        """
        from raglite.forecasting.timeseries import extract_variable_cost_from_qdrant_chunks

        data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")

        if data is None or len(data.points) == 0:
            pytest.skip("No Variable Cost data available. Run with TEST_USE_FULL_PDF=true.")

        # Validate each point is in EUR/ton range
        out_of_range = []
        for point in data.points:
            # Variable costs are negative (outflows)
            if not (-350 <= point.value <= -150):
                out_of_range.append(f"{point.label}: {point.value}")

        assert len(out_of_range) == 0, (
            f"{len(out_of_range)} values outside EUR/ton range [-350, -150]: "
            f"{out_of_range[:5]}{'...' if len(out_of_range) > 5 else ''}"
        )

    @pytest.mark.asyncio
    async def test_ac3_values_are_negative_costs(self) -> None:
        """AC3: Variable Cost values are negative (cost outflows).

        Given: Variable Cost data extracted with entity='portugal' filter
        When: Checking value signs
        Then: All values are negative (representing cost outflows)
        """
        from raglite.forecasting.timeseries import extract_variable_cost_from_qdrant_chunks

        data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")

        if data is None:
            pytest.skip("No Variable Cost data available. Run with TEST_USE_FULL_PDF=true.")

        positive_values = [(p.label, p.value) for p in data.points if p.value >= 0]

        assert len(positive_values) == 0, (
            f"Found {len(positive_values)} non-negative values "
            f"(costs should be negative): {positive_values[:5]}"
        )

    @pytest.mark.asyncio
    async def test_ac3_typical_value_around_280_eur_ton(self) -> None:
        """AC3: Typical Portugal Variable Cost is around -280 EUR/ton.

        Given: Variable Cost data extracted with entity='portugal' filter
        When: Calculating the mean value
        Then: Mean is approximately -280 EUR/ton (+/- 50 tolerance)

        Note: Based on actual data showing Portugal cement variable costs
        typically range from -250 to -300 EUR/ton.
        """
        from raglite.forecasting.timeseries import extract_variable_cost_from_qdrant_chunks

        data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")

        if data is None or len(data.points) < 3:
            pytest.skip(
                "Insufficient Variable Cost data for mean calculation. Run with TEST_USE_FULL_PDF=true."
            )

        mean_value = statistics.mean([p.value for p in data.points])

        # Typical value around -280 EUR/ton with +/- 50 tolerance
        assert -330 <= mean_value <= -230, (
            f"Mean Variable Cost {mean_value:.1f} EUR/ton outside "
            f"expected range [-330, -230]. Portugal cement typically -250 to -300."
        )
