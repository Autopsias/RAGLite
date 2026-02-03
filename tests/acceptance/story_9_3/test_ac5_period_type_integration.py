"""ATDD tests for Story 9.3 AC5 - Integration with Period Classification.

TDD RED Phase: All tests MUST fail initially because the value_type_classifier
does not exist yet.

Test IDs follow pattern: TEST-AC-9.3.5.{test}

BDD Acceptance Criteria:
Given period_type classification already identifies BUDGET and YTD_BUDGET
When value_type classification runs
Then BUDGET period types are automatically marked as value_type=BUDGET
And YTD_BUDGET period types are automatically marked as value_type=BUDGET
And MONTHLY_ACTUAL and YTD_ACTUAL default to value_type=ACTUAL
And this prevents classification inconsistencies
"""


class TestAC5PeriodTypeIntegration:
    """AC5: Integration with Period Classification.

    Given period_type classification already identifies BUDGET and YTD_BUDGET
    When value_type classification runs
    Then BUDGET period types are automatically marked as value_type=BUDGET
    And YTD_BUDGET period types are automatically marked as value_type=BUDGET
    And MONTHLY_ACTUAL and YTD_ACTUAL default to value_type=ACTUAL
    And this prevents classification inconsistencies
    """

    def test_ac_5_1_1_budget_period_type_maps_to_budget_value_type(self) -> None:
        """TEST-AC-9.3.5.1 [P0]: BUDGET period_type maps to BUDGET value_type.

        Given a period classified as BUDGET by period_type classifier
        When classify_value_type is called with period_type
        Then value_type is BUDGET
        """
        # Arrange: Import classifiers
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        # Act: Classify with BUDGET period_type provided
        result = classify_value_type("B Dec-21", period_type=PeriodType.BUDGET)

        # Assert: Value type is BUDGET
        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_type"

    def test_ac_5_1_2_ytd_budget_period_type_maps_to_budget_value_type(self) -> None:
        """TEST-AC-9.3.5.2 [P0]: YTD_BUDGET period_type maps to BUDGET value_type.

        Given a period classified as YTD_BUDGET by period_type classifier
        When classify_value_type is called with period_type
        Then value_type is BUDGET
        """
        # Arrange: Import classifiers
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        # Act: Classify with YTD_BUDGET period_type provided
        result = classify_value_type("YTD B Dec-21", period_type=PeriodType.YTD_BUDGET)

        # Assert: Value type is BUDGET (not separate YTD_BUDGET value type)
        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_type"

    def test_ac_5_2_1_monthly_actual_period_type_maps_to_actual_value_type(
        self,
    ) -> None:
        """TEST-AC-9.3.5.3 [P0]: MONTHLY_ACTUAL period_type maps to ACTUAL value_type.

        Given a period classified as MONTHLY_ACTUAL by period_type classifier
        When classify_value_type is called with period_type
        Then value_type is ACTUAL
        """
        # Arrange: Import classifiers
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        # Act: Classify with MONTHLY_ACTUAL period_type provided
        result = classify_value_type("Dec-21", period_type=PeriodType.MONTHLY_ACTUAL)

        # Assert: Value type is ACTUAL
        assert result.value_type == ValueType.ACTUAL

    def test_ac_5_2_2_ytd_actual_period_type_maps_to_actual_value_type(self) -> None:
        """TEST-AC-9.3.5.4 [P0]: YTD_ACTUAL period_type maps to ACTUAL value_type.

        Given a period classified as YTD_ACTUAL by period_type classifier
        When classify_value_type is called with period_type
        Then value_type is ACTUAL
        """
        # Arrange: Import classifiers
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        # Act: Classify with YTD_ACTUAL period_type provided
        result = classify_value_type("YTD Dec-21", period_type=PeriodType.YTD_ACTUAL)

        # Assert: Value type is ACTUAL
        assert result.value_type == ValueType.ACTUAL

    def test_ac_5_3_1_period_type_prevents_inconsistencies(self) -> None:
        """TEST-AC-9.3.5.5 [P0]: Period type integration prevents inconsistencies.

        Given period_type says BUDGET
        When the period string alone would be ambiguous
        Then period_type takes precedence, preventing inconsistency
        """
        # Arrange: Import classifiers
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        # A period that might be classified differently based on context
        # If period_type is explicitly BUDGET, value_type must be BUDGET
        ambiguous_period = "Jan B 25"

        # Act: Classify with explicit period_type
        result = classify_value_type(ambiguous_period, period_type=PeriodType.BUDGET)

        # Assert: Period type determines value type
        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_type"

    def test_ac_5_3_2_unknown_period_type_uses_other_signals(self) -> None:
        """TEST-AC-9.3.5.6 [P1]: UNKNOWN period_type falls back to other signals.

        Given period_type is UNKNOWN
        When classify_value_type is called
        Then it uses other signals (prefix, header) instead
        """
        # Arrange: Import classifiers
        from raglite.ingestion.classification import (
            PeriodType,
            ValueType,
            classify_value_type,
        )

        # Act: Classify with UNKNOWN period_type but budget prefix
        result = classify_value_type("B Dec-21", period_type=PeriodType.UNKNOWN)

        # Assert: Falls back to period prefix
        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_prefix"  # Not "period_type"

    def test_ac_5_4_1_integration_with_classify_period(self) -> None:
        """TEST-AC-9.3.5.7 [P0]: Integrates correctly with classify_period.

        Given classify_period returns a ClassifiedPeriod with period_type
        When classify_value_type uses that period_type
        Then classifications are consistent
        """
        # Arrange: Import both classifiers
        from raglite.ingestion.classification import (
            ValueType,
            classify_period,
            classify_value_type,
        )

        # Act: First classify the period type
        period_result = classify_period("B Dec-21")

        # Then use period_type in value_type classification
        value_result = classify_value_type("B Dec-21", period_type=period_result.period_type)

        # Assert: Classifications are consistent
        # If period_type is BUDGET, value_type should be BUDGET
        assert value_result.value_type == ValueType.BUDGET
