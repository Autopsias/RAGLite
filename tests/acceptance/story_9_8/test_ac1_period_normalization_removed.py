"""
Test: test_ac1_period_normalization_removed.py
Priority: P0 (critical)
AC Reference: AC1 - Period Normalization Logic Removed

Validates that runtime period classification is replaced with SQL filters
and complex regex-based period parsing is simplified.
"""

from pytest import mark

from raglite.forecasting.timeseries.sql_extraction_query import (
    _get_period_match_clause,
    build_timeseries_query,
)


@mark.acceptance
@mark.story_9_8
class TestAC1PeriodNormalizationRemoved:
    """AC1: Period Normalization Logic Removed from Query Time"""

    @mark.p0
    def test_ac_9_8_1_1_sql_queries_use_period_type_filter(self):
        """
        TEST-AC-9.8.1.1 [P0]: SQL queries use period_type column filter

        GIVEN: The forecasting module needs to filter monthly data
        WHEN: Building a SQL query for time-series extraction
        THEN: The query uses WHERE period_type = 'monthly_actual'
              instead of complex regex patterns
        """
        # Act: Build a timeseries query for monthly data
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=False,
            aggregation="sum",
        )

        # Assert: Query contains period_type filter
        assert "period_type = 'monthly_actual'" in query
        assert "period_type" in query

    @mark.p0
    def test_ac_9_8_1_2_sql_queries_use_value_type_filter(self):
        """
        TEST-AC-9.8.1.2 [P0]: SQL queries use value_type column filter

        GIVEN: The forecasting module needs to filter actual values (exclude budget)
        WHEN: Building a SQL query for time-series extraction
        THEN: The query uses WHERE value_type = 'actual'
              instead of regex budget exclusion patterns
        """
        # Act: Build a timeseries query excluding budget data
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=False,
            aggregation="sum",
        )

        # Assert: Query contains value_type filter
        assert "value_type = 'actual'" in query
        assert "value_type" in query

    @mark.p0
    def test_ac_9_8_1_3_ytd_queries_use_period_type_filter(self):
        """
        TEST-AC-9.8.1.3 [P0]: YTD queries use period_type column filter

        GIVEN: The forecasting module needs to filter YTD data
        WHEN: Building a SQL query for YTD time-series extraction
        THEN: The query uses WHERE period_type = 'ytd_actual'
        """
        # Act: Build a timeseries query for YTD data
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=True,
            aggregation="sum",
        )

        # Assert: Query contains period_type = 'ytd_actual'
        assert "period_type" in query
        assert "ytd_actual" in query

    @mark.p1
    def test_ac_9_8_1_4_classification_imports_removed_from_sql_extraction(self):
        """
        TEST-AC-9.8.1.4 [P1]: Classification imports removed from sql_extraction modules

        GIVEN: The sql_extraction_query.py module
        WHEN: Inspecting module imports via inspect module
        THEN: No direct imports of classification modules are present
              (classification is now done at ingestion time, not query time)
        """
        # Arrange: Read the sql_extraction_query module source using inspect
        import inspect

        import raglite.forecasting.timeseries.sql_extraction_query as query_module

        source_code = inspect.getsource(query_module)

        # Assert: No classification module imports
        assert "from raglite.forecasting.timeseries.period_classification import" not in source_code
        assert "import period_classification" not in source_code

    @mark.p1
    def test_ac_9_8_1_5_regex_period_matching_replaced(self):
        """
        TEST-AC-9.8.1.5 [P1]: Complex regex period matching is replaced

        GIVEN: The old query used regex patterns like '^[A-Za-z]{3}-[0-9]{2,4}$'
        WHEN: Building a new query for period matching
        THEN: Regex patterns are NOT used for period matching
              (replaced by indexed column lookups)
        """
        # Act: Build a timeseries query
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=False,
            aggregation="sum",
        )

        # Assert: Query does not contain period matching regex patterns
        assert "period ~ '^[A-Za-z]{3}-[0-9]{2,4}$'" not in query
        assert (
            "period ~" not in query or "period_type" in query
        )  # Allow REGEXP_MATCH for extraction


@mark.acceptance
@mark.story_9_8
class TestAC1SimplifiedQueryStructure:
    """AC1: Query Structure Simplification Validation"""

    @mark.p0
    def test_ac_9_8_1_6_query_does_not_use_budget_exclusion_regex(self):
        """
        TEST-AC-9.8.1.6 [P0]: Query does not use budget exclusion regex

        GIVEN: The old query used regex like period !~ '^B\\s'
        WHEN: Building a new query
        THEN: Budget exclusion regex patterns are NOT present
              (replaced by value_type != 'budget')
        """
        # Act: Build a timeseries query
        query = build_timeseries_query(
            metric_condition="metric = %s",
            entity_filter="",
            prefer_ytd=False,
            aggregation="sum",
        )

        # Assert: No budget exclusion regex patterns in query
        assert "period !~ '^B\\\\s'" not in query
        assert "period !~ '\\\\sB\\\\s'" not in query
        assert "period !~ '^YTD\\\\s+B\\\\s'" not in query

    @mark.p1
    def test_ac_9_8_1_7_get_period_match_clause_simplified(self):
        """
        TEST-AC-9.8.1.7 [P1]: _get_period_match_clause() is simplified

        GIVEN: The function _get_period_match_clause() exists in sql_extraction_query
        WHEN: Calling it with monthly_actual preference
        THEN: Returns a simple column filter, not a regex pattern
        """
        # Act: Call with monthly preference
        period_match, period_extract, is_ytd_flag = _get_period_match_clause(prefer_ytd=False)

        # Assert: Returns column-based WHERE clause
        assert "period_type = 'monthly_actual'" in period_match
        assert "value_type = 'actual'" in period_match
        # Should NOT contain complex regex
        assert "period ~ '^[A-Za-z]" not in period_match

    @mark.p1
    def test_ac_9_8_1_8_get_budget_exclusion_clause_removed_or_simplified(self):
        """
        TEST-AC-9.8.1.8 [P1]: _get_budget_exclusion_clause() removed or simplified

        GIVEN: The function _get_budget_exclusion_clause() was used for budget exclusion
        WHEN: Building a query that needs budget exclusion
        THEN: The function is removed entirely (budget exclusion now handled by value_type column)
        """
        # Act: Verify the function no longer exists
        import raglite.forecasting.timeseries.sql_extraction_query as query_module

        # Assert: Function is removed (dead code elimination)
        assert not hasattr(query_module, "_get_budget_exclusion_clause"), (
            "_get_budget_exclusion_clause should be removed (budget exclusion now handled by value_type filter)"
        )
