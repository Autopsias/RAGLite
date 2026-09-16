"""
Test: test_ac2_direct_sql_queries.py
Priority: P0 (critical)
AC Reference: AC2 - Direct SQL Queries by Classification Fields
"""

from pytest import mark

from raglite.forecasting.timeseries.sql_extraction_query import build_timeseries_query


@mark.acceptance
@mark.story_9_8
class TestAC2DirectSQLQueriesMonthlyActuals:
    """AC2: Monthly Actuals Query Using Classification Fields"""

    @mark.p0
    def test_ac_9_8_2_1_monthly_actuals_uses_period_type_filter(self):
        """
        TEST-AC-9.8.2.1 [P0]: Monthly actuals query uses period_type filter

        GIVEN: Building a timeseries query for monthly data
        WHEN: Query is constructed with prefer_ytd=False
        THEN: Query contains period_type = 'monthly_actual' filter
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=False, aggregation="sum"
        )
        assert "period_type = 'monthly_actual'" in query

    @mark.p0
    def test_ac_9_8_2_2_monthly_actuals_uses_value_type_filter(self):
        """
        TEST-AC-9.8.2.2 [P0]: Monthly actuals query uses value_type filter

        GIVEN: Building a timeseries query for actual values (not budget)
        WHEN: Query is constructed
        THEN: Query contains value_type = 'actual' filter
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=False, aggregation="sum"
        )
        assert "value_type = 'actual'" in query

    @mark.p0
    def test_ac_9_8_2_3_combined_filter_monthly_and_actual(self):
        """
        TEST-AC-9.8.2.3 [P0]: Combined filter for monthly actual data

        GIVEN: Building a query for monthly actual data
        WHEN: Query is constructed with both filters
        THEN: Query contains both period_type and value_type filters
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=False, aggregation="sum"
        )
        assert "period_type = 'monthly_actual'" in query
        assert "value_type = 'actual'" in query


@mark.acceptance
@mark.story_9_8
class TestAC2DirectSQLQueriesYTDActuals:
    """AC2: YTD Actuals Query Using Classification Fields"""

    @mark.p0
    def test_ac_9_8_2_4_ytd_actuals_uses_period_type_filter(self):
        """
        TEST-AC-9.8.2.4 [P0]: YTD actuals query uses period_type filter

        GIVEN: Building a timeseries query for YTD data
        WHEN: Query is constructed with prefer_ytd=True
        THEN: Query contains period_type filter with ytd_actual
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=True, aggregation="sum"
        )
        assert "period_type" in query
        assert "ytd_actual" in query

    @mark.p0
    def test_ac_9_8_2_5_ytd_actuals_uses_value_type_filter(self):
        """
        TEST-AC-9.8.2.5 [P0]: YTD actuals query uses value_type filter

        GIVEN: Building a YTD query for actual values
        WHEN: Query is constructed
        THEN: Query contains value_type = 'actual' filter
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=True, aggregation="sum"
        )
        assert "value_type = 'actual'" in query

    @mark.p0
    def test_ac_9_8_2_6_combined_filter_ytd_and_actual(self):
        """
        TEST-AC-9.8.2.6 [P0]: Combined filter for YTD actual data

        GIVEN: Building a query for YTD actual data
        WHEN: Query is constructed with both filters
        THEN: Query contains both period_type (ytd_actual) and value_type filters
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=True, aggregation="sum"
        )
        assert "period_type" in query and "ytd_actual" in query
        assert "value_type = 'actual'" in query


@mark.acceptance
@mark.story_9_8
class TestAC2BudgetExclusionSimplified:
    """AC2: Budget Exclusion Simplified to Column Filter"""

    @mark.p0
    def test_ac_9_8_2_7_budget_exclusion_no_regex(self):
        """
        TEST-AC-9.8.2.7 [P0]: Budget exclusion uses column filter, not regex

        GIVEN: Query needs to exclude budget data
        WHEN: Query is built for actual values only
        THEN: Uses value_type = 'actual' instead of regex patterns
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=False, aggregation="sum"
        )
        assert "value_type = 'actual'" in query
        assert "period !~ '^B\\\\s'" not in query

    @mark.p1
    def test_ac_9_8_2_8_no_pattern_b_space_regex(self):
        """
        TEST-AC-9.8.2.8 [P1]: Budget exclusion pattern removed

        GIVEN: Query should not contain old regex patterns
        WHEN: Query is built
        THEN: Pattern '^B\\s' is not present
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=False, aggregation="sum"
        )
        assert "^B\\\\s" not in query

    @mark.p1
    def test_ac_9_8_2_9_no_ytd_budget_regex(self):
        """
        TEST-AC-9.8.2.9 [P1]: YTD budget regex pattern removed

        GIVEN: Old YTD budget exclusion regex should be gone
        WHEN: Query is built for YTD data
        THEN: Pattern '^YTD\\s+B\\s' is not present
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=True, aggregation="sum"
        )
        assert "^YTD\\\\s+B\\\\s" not in query


@mark.acceptance
@mark.story_9_8
class TestAC2ClassificationColumnsPresence:
    """AC2: Verify Database Classification Columns Are Used"""

    @mark.p0
    def test_ac_9_8_2_10_query_references_period_type_column(self):
        """
        TEST-AC-9.8.2.10 [P0]: Query uses period_type classification column

        GIVEN: Query needs to filter by period type
        WHEN: Query is built
        THEN: period_type column is referenced in query
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=False, aggregation="sum"
        )
        assert "period_type" in query

    @mark.p0
    def test_ac_9_8_2_11_query_references_value_type_column(self):
        """
        TEST-AC-9.8.2.11 [P0]: Query uses value_type classification column

        GIVEN: Query needs to filter by value type (actual vs budget)
        WHEN: Query is built
        THEN: value_type column is referenced in query
        """
        query = build_timeseries_query(
            metric_condition="metric = %s", entity_filter="", prefer_ytd=False, aggregation="sum"
        )
        assert "value_type" in query
