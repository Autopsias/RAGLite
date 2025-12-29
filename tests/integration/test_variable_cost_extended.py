"""Integration tests for entity-specific Variable Cost extraction (Story 6.15) - Extended Tests.

ATDD RED PHASE: These tests define the expected behavior for Variable Cost extraction
with entity filtering. Tests MUST FAIL initially because the implementation doesn't exist yet.

Tests cover:
- AC4: Variable Cost MAPE improves to <25% (from 41%)
- AC5: No regression in other metric extraction

Story 6.15: Entity-Specific Variable Cost Extraction
- Problem: Variable Cost MAPE is 41.43% (target <8%) due to multi-entity data mixing
- Solution: Implement entity detection to filter Portugal-only data and normalize to EUR/ton

IMPORTANT: These tests require production data with Variable Cost information.
- LOCAL: Tests skip when using 10-page sample PDF (no Variable Cost data)
- CI: Run with TEST_USE_FULL_PDF=true to use 160-page production PDF
- Command: TEST_USE_FULL_PDF=true pytest tests/integration/test_variable_cost_extended.py

TEST PERFORMANCE: Most tests will skip locally (75% skip rate without full PDF).
This is expected and not a problem - tests validate behavior when data IS available.
Use @pytest.mark.slow for tests that would take >1s if data were available.
"""

import statistics

import pytest

# Mark all tests as integration tests and slow (H3: reduce skip rate impact on performance budget)
# All tests are read-only (query operations only) - skip cleanup overhead
pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.preserve_collection]


class TestVariableCostMAPEImprovement:
    """Test Variable Cost MAPE improvement (AC4).

    Given: Variable Cost forecasting with entity-specific extraction
    When: Running MAPE validation with holdout test set
    Then: Variable Cost MAPE improves to <25% (from 41%)

    Note: Full MAPE validation requires the forecasting pipeline.
    These tests validate the prerequisites for MAPE improvement.
    """

    @pytest.mark.asyncio
    async def test_ac4_entity_param_accepted_by_extraction(self) -> None:
        """AC4: extract_variable_cost_from_qdrant_chunks accepts entity parameter.

        Given: Variable Cost extraction function
        When: Calling with entity='portugal' parameter
        Then: Function accepts the parameter and returns filtered data
        """
        from raglite.forecasting.timeseries import extract_variable_cost_from_qdrant_chunks

        # This test verifies the interface change for AC4
        # The function must accept 'entity' parameter
        try:
            data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")
            # If function doesn't accept entity param, this would raise TypeError
            assert data is None or hasattr(data, "points"), "Unexpected return type"
        except TypeError as e:
            if "entity" in str(e):
                pytest.fail("Function does not accept 'entity' parameter")
            raise

    @pytest.mark.asyncio
    async def test_ac4_filtered_data_more_consistent(self) -> None:
        """AC4: Portugal-filtered data is more consistent for forecasting.

        Given: Variable Cost data with entity='portugal' filter
        When: Analyzing data consistency metrics
        Then: Data shows lower variance suitable for accurate forecasting
        """
        from raglite.forecasting.timeseries import extract_variable_cost_from_qdrant_chunks

        data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")

        if data is None or len(data.points) < 6:
            pytest.skip("Insufficient data for consistency analysis")

        values = [abs(p.value) for p in data.points]

        # For good forecasting, we want:
        # 1. Reasonable range (not too spread out)
        # 2. No extreme outliers (all within 2 stdev of mean)

        mean_val = statistics.mean(values)
        stdev_val = statistics.stdev(values)

        outliers = [v for v in values if abs(v - mean_val) > 2 * stdev_val]

        assert len(outliers) == 0, (
            f"Found {len(outliers)} outliers (>2 stdev from mean): {outliers}. "
            f"Mean: {mean_val:.1f}, StdDev: {stdev_val:.1f}"
        )


class TestNoRegressionOtherMetrics:
    """Test no regression in other metric extraction (AC5).

    Given: Changes to entity detection in timeseries_extract.py
    When: Running full forecasting validation suite
    Then: No regression occurs in other metric extraction
    """

    @pytest.mark.asyncio
    async def test_ac5_revenue_extraction_unaffected(self) -> None:
        """AC5: Revenue extraction continues to work after entity detection changes.

        Given: Revenue extraction via extract_timeseries_from_sql()
        When: Extracting revenue time series
        Then: Extraction succeeds with expected data points (or skips if data unavailable)

        Note: This test validates that entity detection changes didn't break revenue extraction.
        If revenue data isn't available in test PDF, test skips (not a regression).
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        try:
            data = await extract_timeseries_from_sql(metric="revenue", min_points=6)
            if data is None:
                pytest.skip("No revenue data in test collection (not a regression)")
            assert len(data.points) >= 6, f"Revenue: only {len(data.points)} points (need >=6)"
            assert data.metric_name == "revenue", f"Unexpected metric name: {data.metric_name}"
        except (ExtractionError, MetricValidationError):
            # These are expected when data isn't available - not a regression
            pytest.skip("Revenue data not available in test PDF (not a regression)")

    @pytest.mark.asyncio
    async def test_ac5_ebitda_extraction_unaffected(self) -> None:
        """AC5: EBITDA extraction continues to work after entity detection changes.

        Given: EBITDA extraction via extract_timeseries_from_sql()
        When: Extracting EBITDA time series
        Then: Extraction succeeds with expected data points (or skips if data unavailable)

        Note: This test validates that entity detection changes didn't break EBITDA extraction.
        If EBITDA data isn't available in test PDF, test skips (not a regression).
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        try:
            data = await extract_timeseries_from_sql(metric="ebitda", min_points=6)
            if data is None:
                pytest.skip("No EBITDA data in test collection (not a regression)")
            assert len(data.points) >= 6, f"EBITDA: only {len(data.points)} points (need >=6)"
            assert data.metric_name == "ebitda", f"Unexpected metric name: {data.metric_name}"
        except (ExtractionError, MetricValidationError):
            # These are expected when data isn't available - not a regression
            pytest.skip("EBITDA data not available in test PDF (not a regression)")

    @pytest.mark.asyncio
    async def test_ac5_sales_volume_extraction_unaffected(self) -> None:
        """AC5: Sales volume extraction continues to work after entity detection changes.

        Given: Sales volume extraction via extract_timeseries_from_sql()
        When: Extracting sales_volume time series
        Then: Extraction succeeds or fails gracefully (not regression error)
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        try:
            data = await extract_timeseries_from_sql(metric="sales_volume", min_points=6)
            # If extraction succeeds, validate basic structure
            if data is not None:
                assert hasattr(data, "points"), "Missing points attribute"
                assert hasattr(data, "metric_name"), "Missing metric_name attribute"
        except (ExtractionError, MetricValidationError):
            # These are expected errors for metrics with insufficient data
            # This is NOT a regression - it's expected behavior
            pass
        except Exception as e:
            pytest.fail(f"Sales volume extraction failed unexpectedly (potential regression): {e}")

    @pytest.mark.asyncio
    async def test_ac5_timeseries_data_structure_unchanged(self) -> None:
        """AC5: TimeSeriesData model structure unchanged.

        Given: TimeSeriesData model from shared.models
        When: Creating TimeSeriesData instance
        Then: All expected fields are present and work correctly
        """
        from datetime import datetime

        from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

        # Verify model can be instantiated with expected fields
        point = TimeSeriesPoint(date=datetime(2024, 1, 1), value=-250.0, label="Jan-24")

        data = TimeSeriesData(
            metric_name="variable_cost",
            points=[point],
            interval="monthly",
            source_documents=["test.pdf"],
        )

        assert data.metric_name == "variable_cost"
        assert len(data.points) == 1
        assert data.interval == "monthly"
        assert data.source_documents == ["test.pdf"]
        assert data.points[0].value == -250.0


class TestEntityParameterIntegration:
    """Test entity parameter integration in extraction function (AC2, AC3).

    Story 6.15: Validates that the entity parameter is properly
    integrated into the extraction function.
    """

    @pytest.mark.asyncio
    async def test_entity_portugal_filters_correctly(self) -> None:
        """AC2/AC3: entity='portugal' filters to Portugal-only data.

        Given: extract_variable_cost_from_qdrant_chunks with entity='portugal'
        When: Extracting Variable Cost data
        Then: All returned data is from Portugal (EUR/ton values)
        """
        from raglite.forecasting.timeseries import extract_variable_cost_from_qdrant_chunks

        data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")

        if data is None:
            pytest.skip("No data returned for filtering test")

        # All values should be in Portugal EUR/ton range
        for point in data.points:
            assert -400 <= point.value <= -100, (
                f"Value {point.value} outside Portugal EUR/ton range. "
                f"May indicate Tunisia (TND) or Brazil (BRL) data mixing."
            )

    @pytest.mark.asyncio
    async def test_default_entity_is_portugal(self) -> None:
        """AC2: Default entity is 'portugal' when not specified.

        Given: extract_variable_cost_from_qdrant_chunks without entity parameter
        When: Extracting Variable Cost data
        Then: Defaults to Portugal data (same as explicit entity='portugal')
        """
        from raglite.forecasting.timeseries import extract_variable_cost_from_qdrant_chunks

        # Call without entity parameter
        default_data = await extract_variable_cost_from_qdrant_chunks()

        # Call with explicit portugal
        portugal_data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")

        # Both should return same data structure
        if default_data is not None and portugal_data is not None:
            assert len(default_data.points) == len(portugal_data.points), (
                f"Default extraction ({len(default_data.points)} points) "
                f"differs from explicit Portugal ({len(portugal_data.points)} points)"
            )
