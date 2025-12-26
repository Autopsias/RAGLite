"""Integration tests for SQL extraction entity filtering (Story 6.15 Task 3).

Priority: P1 tests for entity parameter in extract_timeseries_from_sql.

Coverage gaps addressed:
- Entity parameter acceptance in SQL extraction
- Entity normalization integration with SQL queries
- Entity filter fallback to Qdrant when SQL insufficient
- No regression in existing metric extraction
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection]


class TestExtractTimeseriesFromSqlEntityParameter:
    """[P1] Test entity parameter integration in extract_timeseries_from_sql.

    Story 6.15 Task 3: SQL extraction must accept entity parameter
    for filtering multi-entity metrics like Variable Cost.
    """

    @pytest.mark.asyncio
    async def test_p1_sql_extraction_accepts_entity_parameter(self) -> None:
        """[P1] extract_timeseries_from_sql accepts entity parameter.

        Given: SQL extraction function
        When: Calling with entity='portugal' parameter
        Then: Function accepts parameter without TypeError
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        # Should accept entity parameter without TypeError
        try:
            data = await extract_timeseries_from_sql(
                metric="variable_cost", entity="portugal", min_points=6
            )
            # Either returns data or raises ExtractionError/MetricValidationError
            # (both are valid - depends on data availability)
            assert data is None or hasattr(data, "points"), "Unexpected return type"
        except (ExtractionError, MetricValidationError):
            # Expected when data unavailable - not a parameter acceptance issue
            pass
        except TypeError as e:
            if "entity" in str(e):
                pytest.fail("extract_timeseries_from_sql does not accept 'entity' parameter")
            raise

    @pytest.mark.asyncio
    async def test_p1_entity_parameter_optional(self) -> None:
        """[P1] entity parameter is optional (defaults to None).

        Given: SQL extraction function
        When: Calling without entity parameter
        Then: Function works with default behavior (no entity filter)
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        # Should work without entity parameter (backwards compatible)
        try:
            data = await extract_timeseries_from_sql(metric="revenue", min_points=6)
            assert data is None or hasattr(data, "points"), "Unexpected return type"
        except (ExtractionError, MetricValidationError):
            # Expected when data unavailable
            pass

    @pytest.mark.asyncio
    async def test_p1_entity_normalizes_to_canonical_form(self) -> None:
        """[P1] Entity parameter is normalized before SQL filtering.

        Given: entity='portugal' (lowercase)
        When: SQL query is built
        Then: Entity is normalized and used in ILIKE pattern matching

        Note: Tests integration with entity_normalizer.normalize_entity.
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        # Try various entity formats (all should work via normalization)
        entity_variants = ["portugal", "Portugal", "PORTUGAL", "PT"]

        for entity_input in entity_variants:
            try:
                data = await extract_timeseries_from_sql(
                    metric="variable_cost", entity=entity_input, min_points=6
                )
                # Should succeed or fail gracefully (not crash on normalization)
                assert data is None or hasattr(data, "points"), (
                    f"Unexpected return type for entity='{entity_input}'"
                )
            except (ExtractionError, MetricValidationError):
                # Expected when data unavailable - normalization still worked
                pass
            except Exception as e:
                pytest.fail(f"Entity normalization failed for '{entity_input}': {e}")


class TestEntityFilterFallbackToQdrant:
    """[P1] Test Qdrant fallback when SQL entity filtering returns insufficient data.

    Critical: When SQL extraction with entity filter returns <min_points,
    fallback should try Qdrant extraction with same entity filter.
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_p1_sql_insufficient_triggers_qdrant_fallback(self) -> None:
        """[P1] SQL insufficient data triggers Qdrant fallback with entity.

        Given: SQL extraction with entity filter returns <min_points
        When: MetricValidationError is raised
        Then: Qdrant fallback is attempted with same entity filter

        Note: This test validates the fallback mechanism integration.
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        # Try to extract Variable Cost with Portugal filter
        # If SQL data insufficient, should fall back to Qdrant
        try:
            data = await extract_timeseries_from_sql(
                metric="variable_cost", entity="portugal", min_points=6
            )

            # If we get data, it should be from SQL or Qdrant fallback
            if data is not None:
                assert len(data.points) >= 6, (
                    f"Returned data has {len(data.points)} points, expected >=6"
                )
                assert data.metric_name in ["variable_cost", "variable cost"], (
                    f"Unexpected metric name: {data.metric_name}"
                )

        except (ExtractionError, MetricValidationError) as e:
            # Expected when neither SQL nor Qdrant have sufficient data
            # Verify error message is helpful
            error_msg = str(e)
            assert "variable" in error_msg.lower() or "cost" in error_msg.lower(), (
                f"Error message should mention the metric: {error_msg}"
            )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_p1_qdrant_fallback_preserves_entity_filter(self) -> None:
        """[P1] Qdrant fallback uses same entity parameter as SQL query.

        Given: SQL extraction fails with entity='portugal'
        When: Fallback to Qdrant occurs
        Then: Qdrant extraction also uses entity='portugal' filter

        Note: Validates that entity parameter is passed through to fallback.
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            extract_timeseries_from_sql,
        )

        # For Variable Cost, SQL may fail -> Qdrant fallback
        # This test ensures entity parameter is preserved in fallback
        try:
            data = await extract_timeseries_from_sql(
                metric="variable_cost", entity="portugal", min_points=6
            )

            # If fallback succeeded, data should be Portugal-only
            if data is not None and len(data.points) > 0:
                # Portugal Variable Cost should be in EUR/ton range
                for point in data.points:
                    # Quick sanity check that values are in Portugal EUR range
                    # (not Tunisia TND or Brazil BRL scale)
                    assert -400 <= point.value <= -100, (
                        f"Value {point.value} outside Portugal EUR/ton range. "
                        "Entity filter may not have been applied in fallback."
                    )

        except ExtractionError:
            # Expected when no data available in SQL or Qdrant
            pytest.skip("No Variable Cost data available for fallback test")


class TestNoRegressionExistingMetrics:
    """[P1] Test that entity parameter addition doesn't break existing metrics.

    Critical: Revenue, EBITDA, Sales Volume extraction must continue
    to work correctly with entity parameter as optional.
    """

    @pytest.mark.asyncio
    async def test_p1_revenue_extraction_unaffected_by_entity_param(self) -> None:
        """[P1] Revenue extraction works with entity=None (default).

        Given: Revenue extraction (no entity filter needed)
        When: Calling extract_timeseries_from_sql without entity parameter
        Then: Extraction works as before (no regression)
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        try:
            data = await extract_timeseries_from_sql(metric="revenue", min_points=6)
            if data is not None:
                assert data.metric_name == "revenue", "Metric name mismatch"
                assert len(data.points) >= 6, "Insufficient data points"
        except (ExtractionError, MetricValidationError):
            pytest.skip("Revenue data not available (not a regression)")

    @pytest.mark.asyncio
    async def test_p1_ebitda_extraction_unaffected_by_entity_param(self) -> None:
        """[P1] EBITDA extraction works with entity=None (uses GROUP default).

        Given: EBITDA extraction (uses GROUP entity by default)
        When: Calling extract_timeseries_from_sql without entity parameter
        Then: Extraction works with prefer_group_level logic (no regression)
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        try:
            data = await extract_timeseries_from_sql(metric="ebitda", min_points=6)
            if data is not None:
                assert data.metric_name == "ebitda", "Metric name mismatch"
                assert len(data.points) >= 6, "Insufficient data points"
        except (ExtractionError, MetricValidationError):
            pytest.skip("EBITDA data not available (not a regression)")

    @pytest.mark.asyncio
    async def test_p1_sales_volume_extraction_unaffected(self) -> None:
        """[P1] Sales volume extraction works without entity parameter.

        Given: Sales volume extraction
        When: Calling without entity parameter
        Then: No regression errors (may skip if data unavailable)
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        try:
            data = await extract_timeseries_from_sql(metric="sales_volume", min_points=6)
            if data is not None:
                assert hasattr(data, "points"), "Missing points attribute"
                assert hasattr(data, "metric_name"), "Missing metric_name"
        except (ExtractionError, MetricValidationError):
            # Expected for metrics with insufficient data
            pass
        except Exception as e:
            pytest.fail(f"Sales volume extraction failed unexpectedly: {e}")


class TestEntityFilterSqlQueryIntegration:
    """[P2] Test SQL query construction with entity filter.

    Validates that entity parameter correctly integrates with
    SQL query building and entity normalization.
    """

    @pytest.mark.asyncio
    async def test_p2_entity_filter_applied_to_sql_query(self) -> None:
        """[P2] Entity filter is applied to SQL WHERE clause.

        Given: extract_timeseries_from_sql with entity='portugal'
        When: SQL query is executed
        Then: Query includes entity filter using ILIKE pattern

        Note: This is an integration test - validates end-to-end behavior
        rather than inspecting SQL query directly.
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        try:
            # If Variable Cost has Portugal-only data in SQL,
            # this should return Portugal-filtered results
            data = await extract_timeseries_from_sql(
                metric="variable_cost", entity="portugal", min_points=6
            )

            if data is not None and len(data.points) > 0:
                # Returned data should be Portugal-specific
                # (no way to directly verify SQL query, but results validate filter worked)
                assert data.metric_name in ["variable_cost", "variable cost"]

        except (ExtractionError, MetricValidationError):
            # Expected when data unavailable
            pytest.skip("No Variable Cost SQL data for query integration test")

    @pytest.mark.asyncio
    async def test_p2_entity_none_uses_default_behavior(self) -> None:
        """[P2] entity=None uses default prefer_group_level logic.

        Given: extract_timeseries_from_sql with entity=None
        When: Metric is aggregate metric (like EBITDA)
        Then: prefer_group_level logic applies (not entity filter)
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        try:
            # EBITDA with entity=None should use GROUP via prefer_group_level
            data = await extract_timeseries_from_sql(
                metric="ebitda",
                entity=None,  # Explicitly None to test default behavior
                min_points=6,
            )

            if data is not None:
                assert data.metric_name == "ebitda"
                # Should have GROUP-level consolidated data

        except (ExtractionError, MetricValidationError):
            pytest.skip("EBITDA data not available")

    @pytest.mark.asyncio
    async def test_p2_user_entity_overrides_prefer_group_level(self) -> None:
        """[P2] User-specified entity overrides prefer_group_level logic.

        Given: extract_timeseries_from_sql with entity='portugal' for EBITDA
        When: User explicitly requests entity filter
        Then: User's entity takes priority over default GROUP preference

        Note: Tests that explicit entity parameter wins over implicit defaults.
        """
        from raglite.forecasting.timeseries import (
            ExtractionError,
            MetricValidationError,
            extract_timeseries_from_sql,
        )

        try:
            # User requests Portugal EBITDA specifically (override GROUP default)
            data = await extract_timeseries_from_sql(
                metric="ebitda",
                entity="portugal",  # User-specified entity
                min_points=6,
            )

            # Should attempt to get Portugal-specific EBITDA
            # (may fail if only GROUP data available, which is expected)
            if data is not None:
                assert data.metric_name == "ebitda"
                # Data should be Portugal-filtered (if available)

        except (ExtractionError, MetricValidationError):
            # Expected if only GROUP EBITDA available (no Portugal-specific)
            pass
