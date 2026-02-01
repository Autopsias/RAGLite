"""ATDD tests for Story 9.3 AC4 - Context-Based Classification.

TDD RED Phase: All tests MUST fail initially because the value_type_classifier
does not exist yet.

Test IDs follow pattern: TEST-AC-9.3.4.{test}

BDD Acceptance Criteria:
Given a period string and optional column header context
When classify_value_type() is called
Then it uses period prefixes (e.g., "B Dec-21" -> BUDGET) as primary signal
And column headers (e.g., "Budget", "Actual", "Forecast") as secondary signal
And returns ACTUAL as default when no modifiers are present
And handles Portuguese equivalents (Orcamento, Previsao, Real)
"""



class TestAC4ContextBasedClassification:
    """AC4: Context-Based Classification.

    Given a period string and optional column header context
    When classify_value_type() is called
    Then it uses period prefixes as primary signal
    And column headers as secondary signal
    And returns ACTUAL as default when no modifiers are present
    And handles Portuguese equivalents
    """

    def test_ac_4_1_1_period_prefix_is_primary_signal(self) -> None:
        """TEST-AC-9.3.4.1 [P0]: Period prefix is primary classification signal.

        Given a period with "B " prefix
        When classify_value_type is called
        Then it classifies as BUDGET regardless of header
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with budget prefix
        result = classify_value_type("B Dec-21")

        # Assert: Primary signal (prefix) determines classification
        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_prefix"

    def test_ac_4_1_2_forecast_prefix_as_primary_signal(self) -> None:
        """TEST-AC-9.3.4.2 [P0]: Forecast prefix as primary signal.

        Given a period with "F " prefix
        When classify_value_type is called
        Then it classifies as FORECAST
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with forecast prefix
        result = classify_value_type("F Dec-21")

        # Assert: Primary signal determines classification
        assert result.value_type == ValueType.FORECAST
        assert result.source == "period_prefix"

    def test_ac_4_2_1_column_header_as_secondary_signal(self) -> None:
        """TEST-AC-9.3.4.3 [P0]: Column header as secondary signal.

        Given a period without prefix but with "Budget" header
        When classify_value_type is called with header
        Then it classifies as BUDGET based on header
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with header but no prefix
        result = classify_value_type("Dec-21", header="Budget")

        # Assert: Secondary signal (header) used when no prefix
        assert result.value_type == ValueType.BUDGET
        assert result.source == "column_header"

    def test_ac_4_2_2_forecast_header_as_secondary_signal(self) -> None:
        """TEST-AC-9.3.4.4 [P0]: Forecast header as secondary signal.

        Given a period without prefix but with "Forecast" header
        When classify_value_type is called with header
        Then it classifies as FORECAST based on header
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with header
        result = classify_value_type("Dec-21", header="Forecast")

        # Assert: Header used as secondary signal
        assert result.value_type == ValueType.FORECAST
        assert result.source == "column_header"

    def test_ac_4_2_3_actual_header_as_secondary_signal(self) -> None:
        """TEST-AC-9.3.4.5 [P0]: Actual header as secondary signal.

        Given a period without prefix but with "Actual" header
        When classify_value_type is called with header
        Then it classifies as ACTUAL based on header
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with header
        result = classify_value_type("Dec-21", header="Actual")

        # Assert: Header confirms ACTUAL
        assert result.value_type == ValueType.ACTUAL

    def test_ac_4_3_1_default_to_actual_without_modifiers(self) -> None:
        """TEST-AC-9.3.4.6 [P0]: Default to ACTUAL when no modifiers present.

        Given a period without any modifiers or headers
        When classify_value_type is called
        Then it defaults to ACTUAL
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify without any context
        result = classify_value_type("Dec-21")

        # Assert: Default is ACTUAL
        assert result.value_type == ValueType.ACTUAL
        assert result.source == "default"

    def test_ac_4_4_1_portuguese_orcamento_classified_as_budget(self) -> None:
        """TEST-AC-9.3.4.7 [P0]: Portuguese "Orcamento" classified as BUDGET.

        Given a period with Portuguese budget indicator
        When classify_value_type is called
        Then it classifies as BUDGET
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with Portuguese indicator
        result = classify_value_type("Orcamento Dez-21")

        # Assert: Portuguese handled correctly
        assert result.value_type == ValueType.BUDGET

    def test_ac_4_4_2_portuguese_previsao_classified_as_forecast(self) -> None:
        """TEST-AC-9.3.4.8 [P0]: Portuguese "Previsao" classified as FORECAST.

        Given a period with Portuguese forecast indicator
        When classify_value_type is called
        Then it classifies as FORECAST
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with Portuguese indicator
        result = classify_value_type("Previsao Dez-21")

        # Assert: Portuguese handled correctly
        assert result.value_type == ValueType.FORECAST

    def test_ac_4_4_3_portuguese_real_classified_as_actual(self) -> None:
        """TEST-AC-9.3.4.9 [P0]: Portuguese "Real" classified as ACTUAL.

        Given a period with Portuguese actual indicator
        When classify_value_type is called
        Then it classifies as ACTUAL
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with Portuguese indicator
        result = classify_value_type("Real Dez-21")

        # Assert: Portuguese handled correctly
        assert result.value_type == ValueType.ACTUAL

    def test_ac_4_4_4_portuguese_variacao_classified_as_variance(self) -> None:
        """TEST-AC-9.3.4.10 [P0]: Portuguese "Variacao" classified as VARIANCE.

        Given a period with Portuguese variance indicator
        When classify_value_type is called
        Then it classifies as VARIANCE
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with Portuguese indicator
        result = classify_value_type("Variacao Dez-21")

        # Assert: Portuguese handled correctly
        assert result.value_type == ValueType.VARIANCE

    def test_ac_4_5_1_period_prefix_overrides_header(self) -> None:
        """TEST-AC-9.3.4.11 [P1]: Period prefix overrides conflicting header.

        Given a period with budget prefix but forecast header
        When classify_value_type is called
        Then period prefix wins (BUDGET)
        """
        # Arrange: Import classifier
        from raglite.ingestion.classification import ValueType, classify_value_type

        # Act: Classify with conflicting signals
        result = classify_value_type("B Dec-21", header="Forecast")

        # Assert: Primary signal (prefix) wins
        assert result.value_type == ValueType.BUDGET
        assert result.source == "period_prefix"
