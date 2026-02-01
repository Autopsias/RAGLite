"""ATDD Integration tests for Story 9.2 - Period Classification.

TDD RED Phase: All tests MUST fail initially because the implementation
at raglite/ingestion/classification/ does not exist yet.

Test IDs follow pattern: TEST-AC-9.2.{ac}.{test}

Coverage:
- AC2: Classification Accuracy Target (95%+ on 50+ ground truth examples)
- AC5: Integration with Database Schema (values match VARCHAR(50) constraint)
"""

import json
from pathlib import Path

import pytest

# Integration tests - require database infrastructure
pytestmark = [
    pytest.mark.integration,
]


class TestAC2ClassificationAccuracy:
    """AC2: Classification Accuracy Target.

    Given a ground truth dataset of 50+ period strings from production PDFs
    When the period classifier processes all strings
    Then it achieves 95%+ classification accuracy
    And monthly actual periods (e.g., "Dec-21") are correctly classified
    And YTD actual periods (e.g., "YTD Dec-21") are correctly classified
    And budget periods (e.g., "B Dec-21") are correctly excluded
    And unknown formats are properly flagged
    """

    @pytest.fixture
    def ground_truth_data(self) -> list[dict]:
        """Load ground truth dataset for accuracy validation."""
        ground_truth_path = Path(
            "tests/fixtures/period_classification_ground_truth.json"
        )

        # Ground truth file should exist for AC2 validation
        assert ground_truth_path.exists(), (
            f"Ground truth file not found: {ground_truth_path}"
        )

        with open(ground_truth_path) as f:
            data = json.load(f)

        # AC2 requires 50+ examples
        assert len(data) >= 50, f"Need 50+ examples, found {len(data)}"

        return data

    def test_ac2_1_achieves_95_percent_accuracy(
        self, ground_truth_data: list[dict]
    ) -> None:
        """TEST-AC-9.2.2.1 [P0]: Achieves 95%+ classification accuracy."""
        from raglite.ingestion.classification import classify_period

        # Given the ground truth dataset
        # When all periods are classified
        correct = 0
        total = len(ground_truth_data)

        for entry in ground_truth_data:
            period = entry["period"]
            expected_type = entry["expected_type"]
            expected_normalized = entry.get("expected_normalized")

            result = classify_period(period)

            # Check type classification
            if result.period_type.value == expected_type:
                # If normalized is specified, check that too
                if expected_normalized is None or result.normalized == expected_normalized:
                    correct += 1

        accuracy = (correct / total) * 100

        # Then accuracy is 95%+
        assert accuracy >= 95.0, (
            f"Accuracy {accuracy:.1f}% below 95% target. "
            f"Correct: {correct}/{total}"
        )

    def test_ac2_2_monthly_actual_classified_correctly(self) -> None:
        """TEST-AC-9.2.2.2 [P0]: Monthly actual periods classified correctly."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given standard monthly actual periods
        monthly_periods = [
            "Dec-21",
            "Jan-25",
            "Feb-24",
            "Mar-23",
            "Nov-22",
        ]

        # When classified
        for period in monthly_periods:
            result = classify_period(period)

            # Then all are MONTHLY_ACTUAL and usable
            assert result.period_type == PeriodType.MONTHLY_ACTUAL, (
                f"{period} should be MONTHLY_ACTUAL, got {result.period_type}"
            )
            assert result.is_usable is True

    def test_ac2_3_ytd_actual_classified_correctly(self) -> None:
        """TEST-AC-9.2.2.3 [P0]: YTD actual periods classified correctly."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given YTD actual periods
        ytd_periods = [
            "YTD Dec-21",
            "YTD Jan-25",
            "YTD Sep-24",
        ]

        # When classified
        for period in ytd_periods:
            result = classify_period(period)

            # Then all are YTD_ACTUAL and usable
            assert result.period_type == PeriodType.YTD_ACTUAL, (
                f"{period} should be YTD_ACTUAL, got {result.period_type}"
            )
            assert result.is_usable is True

    def test_ac2_4_budget_periods_excluded(self) -> None:
        """TEST-AC-9.2.2.4 [P0]: Budget periods correctly excluded."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given budget periods
        budget_periods = [
            "B Dec-21",
            "B Jan-25",
            "Dec-21 B",
        ]

        # When classified
        for period in budget_periods:
            result = classify_period(period)

            # Then all are BUDGET and not usable
            assert result.period_type == PeriodType.BUDGET, (
                f"{period} should be BUDGET, got {result.period_type}"
            )
            assert result.is_usable is False

    def test_ac2_5_unknown_formats_flagged(self) -> None:
        """TEST-AC-9.2.2.5 [P0]: Unknown formats properly flagged."""
        from raglite.ingestion.classification import PeriodType, classify_period

        # Given unknown format periods
        unknown_periods = [
            "N/A",
            "",
            "   ",
            "invalid",
            "2017",
        ]

        # When classified
        for period in unknown_periods:
            result = classify_period(period)

            # Then all are UNKNOWN and not usable
            assert result.period_type == PeriodType.UNKNOWN, (
                f"'{period}' should be UNKNOWN, got {result.period_type}"
            )
            assert result.is_usable is False


class TestAC5DatabaseSchemaIntegration:
    """AC5: Integration with Database Schema.

    Given the period_type column exists in financial_tables (Story 9.1)
    When a period is classified
    Then the period_type value matches the VARCHAR(50) column constraint
    And valid values are: "monthly_actual", "ytd_actual", "budget", "ytd_budget", "unknown"
    And the normalized period string is available for storage
    """

    def test_ac5_1_period_type_values_within_varchar50(self) -> None:
        """TEST-AC-9.2.5.1 [P0]: All period_type values fit VARCHAR(50)."""
        from raglite.ingestion.classification import PeriodType

        # Given all PeriodType enum values
        # When we check their string representation
        for period_type in PeriodType:
            value = period_type.value

            # Then all values are strings <= 50 characters
            assert isinstance(value, str), f"{period_type.name} value is not a string"
            assert len(value) <= 50, (
                f"{period_type.name} value '{value}' exceeds VARCHAR(50)"
            )

    def test_ac5_2_valid_values_match_schema(self) -> None:
        """TEST-AC-9.2.5.2 [P0]: Valid values match database schema."""
        from raglite.ingestion.classification import PeriodType

        # Given the expected valid values from Story 9.1 schema
        expected_values = {
            "monthly_actual",
            "ytd_actual",
            "budget",
            "ytd_budget",
            "unknown",
        }

        # When we extract all PeriodType values
        actual_values = {pt.value for pt in PeriodType}

        # Then they match exactly
        assert actual_values == expected_values, (
            f"PeriodType values {actual_values} do not match schema {expected_values}"
        )

    def test_ac5_3_classified_period_type_value_for_storage(self) -> None:
        """TEST-AC-9.2.5.3 [P0]: ClassifiedPeriod provides value for storage."""
        from raglite.ingestion.classification import classify_period

        # Given various period strings
        test_cases = [
            ("Dec-21", "monthly_actual"),
            ("YTD Jan-22", "ytd_actual"),
            ("B Feb-22", "budget"),
            ("YTD B Mar-22", "ytd_budget"),
            ("N/A", "unknown"),
        ]

        for period, expected_db_value in test_cases:
            # When classified
            result = classify_period(period)

            # Then period_type.value provides the database value
            assert result.period_type.value == expected_db_value, (
                f"{period}: expected {expected_db_value}, "
                f"got {result.period_type.value}"
            )

    def test_ac5_4_normalized_period_available_for_storage(self) -> None:
        """TEST-AC-9.2.5.4 [P1]: Normalized period available for storage."""
        from raglite.ingestion.classification import classify_period

        # Given usable periods
        usable_periods = [
            ("Dec-21", "Dec-21"),
            ("Dez-21", "Dec-21"),  # Portuguese -> English
            ("YTD Jan-22", "Jan-22"),
        ]

        for period, expected_normalized in usable_periods:
            # When classified
            result = classify_period(period)

            # Then normalized is available for storage
            assert result.normalized is not None
            assert result.normalized == expected_normalized

    def test_ac5_5_excluded_periods_have_no_normalized(self) -> None:
        """TEST-AC-9.2.5.5 [P1]: Excluded periods have normalized=None."""
        from raglite.ingestion.classification import classify_period

        # Given excluded periods (budget, unknown)
        excluded_periods = ["B Dec-21", "YTD B Jan-22", "N/A", "invalid"]

        for period in excluded_periods:
            # When classified
            result = classify_period(period)

            # Then normalized is None (not usable for forecasting)
            assert result.normalized is None, (
                f"Excluded period '{period}' should have normalized=None"
            )
            assert result.is_usable is False

    @pytest.mark.slow
    def test_ac5_6_actual_database_insert_compatibility(self) -> None:
        """TEST-AC-9.2.5.6 [P2]: Values can be inserted into actual database.

        This test requires the database infrastructure from Story 9.1.
        """
        import os

        from sqlalchemy import create_engine, text

        from raglite.ingestion.classification import classify_period

        # Get test database URL
        db_url = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql://raglite:raglite@localhost:5433/raglite",
        )

        engine = create_engine(db_url)

        # Given period classifications
        result = classify_period("Dec-21")

        # When attempting to match the database constraint
        with engine.connect() as conn:
            # Check that the period_type column exists and accepts our value
            # This validates Story 9.1 schema is in place
            check_query = text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'financial_tables'
                AND column_name = 'period_type'
            """)
            column_info = conn.execute(check_query).fetchone()

            # Then the column exists with correct type
            assert column_info is not None, "period_type column not found in financial_tables"
            assert column_info[1] == "character varying"
            assert column_info[2] >= 50

            # And our value fits the constraint
            assert len(result.period_type.value) <= column_info[2]
