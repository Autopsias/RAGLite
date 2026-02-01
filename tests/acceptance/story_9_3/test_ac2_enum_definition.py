"""ATDD tests for Story 9.3 AC2 - ValueType Enum Definition.

TDD RED Phase: All tests MUST fail initially because the ValueType enum
does not exist yet in raglite/ingestion/classification/.

Test IDs follow pattern: TEST-AC-9.3.2.{test}

BDD Acceptance Criteria:
Given the value_type column in financial_tables is VARCHAR(50)
When the ValueType enum is defined
Then it includes: ACTUAL, BUDGET, FORECAST, VARIANCE, UNKNOWN
And enum values map to database strings: "actual", "budget", "forecast", "variance", "unknown"
And the enum is exported from raglite/ingestion/classification/__init__.py
"""



class TestAC2ValueTypeEnumDefinition:
    """AC2: ValueType Enum Definition.

    Given the value_type column in financial_tables is VARCHAR(50)
    When the ValueType enum is defined
    Then it includes: ACTUAL, BUDGET, FORECAST, VARIANCE, UNKNOWN
    And enum values map to database strings
    And the enum is exported from raglite/ingestion/classification/__init__.py
    """

    def test_ac_2_1_1_enum_includes_actual(self) -> None:
        """TEST-AC-9.3.2.1 [P0]: ValueType enum includes ACTUAL.

        Given the ValueType enum is defined
        When we access ACTUAL member
        Then it exists and maps to "actual" database string
        """
        # Arrange/Act: Import and access ACTUAL
        from raglite.ingestion.classification import ValueType

        # Assert: ACTUAL exists with correct value
        assert hasattr(ValueType, "ACTUAL")
        assert ValueType.ACTUAL.value == "actual"

    def test_ac_2_1_2_enum_includes_budget(self) -> None:
        """TEST-AC-9.3.2.2 [P0]: ValueType enum includes BUDGET.

        Given the ValueType enum is defined
        When we access BUDGET member
        Then it exists and maps to "budget" database string
        """
        # Arrange/Act: Import and access BUDGET
        from raglite.ingestion.classification import ValueType

        # Assert: BUDGET exists with correct value
        assert hasattr(ValueType, "BUDGET")
        assert ValueType.BUDGET.value == "budget"

    def test_ac_2_1_3_enum_includes_forecast(self) -> None:
        """TEST-AC-9.3.2.3 [P0]: ValueType enum includes FORECAST.

        Given the ValueType enum is defined
        When we access FORECAST member
        Then it exists and maps to "forecast" database string
        """
        # Arrange/Act: Import and access FORECAST
        from raglite.ingestion.classification import ValueType

        # Assert: FORECAST exists with correct value
        assert hasattr(ValueType, "FORECAST")
        assert ValueType.FORECAST.value == "forecast"

    def test_ac_2_1_4_enum_includes_variance(self) -> None:
        """TEST-AC-9.3.2.4 [P0]: ValueType enum includes VARIANCE.

        Given the ValueType enum is defined
        When we access VARIANCE member
        Then it exists and maps to "variance" database string
        """
        # Arrange/Act: Import and access VARIANCE
        from raglite.ingestion.classification import ValueType

        # Assert: VARIANCE exists with correct value
        assert hasattr(ValueType, "VARIANCE")
        assert ValueType.VARIANCE.value == "variance"

    def test_ac_2_1_5_enum_includes_unknown(self) -> None:
        """TEST-AC-9.3.2.5 [P0]: ValueType enum includes UNKNOWN.

        Given the ValueType enum is defined
        When we access UNKNOWN member
        Then it exists and maps to "unknown" database string
        """
        # Arrange/Act: Import and access UNKNOWN
        from raglite.ingestion.classification import ValueType

        # Assert: UNKNOWN exists with correct value
        assert hasattr(ValueType, "UNKNOWN")
        assert ValueType.UNKNOWN.value == "unknown"

    def test_ac_2_2_1_all_values_fit_varchar50(self) -> None:
        """TEST-AC-9.3.2.6 [P0]: All enum values fit VARCHAR(50) constraint.

        Given the database column is VARCHAR(50)
        When we check all ValueType enum values
        Then all values are <= 50 characters
        """
        # Arrange/Act: Import ValueType and check all values
        from raglite.ingestion.classification import ValueType

        # Assert: All values fit VARCHAR(50)
        for member in ValueType:
            assert isinstance(member.value, str)
            assert len(member.value) <= 50, (
                f"{member.name} value '{member.value}' exceeds VARCHAR(50)"
            )

    def test_ac_2_2_2_enum_has_exactly_five_members(self) -> None:
        """TEST-AC-9.3.2.7 [P0]: ValueType has exactly 5 members.

        Given the specification defines 5 value types
        When we enumerate all ValueType members
        Then there are exactly 5 members
        """
        # Arrange/Act: Import and count members
        from raglite.ingestion.classification import ValueType

        # Assert: Exactly 5 members
        members = list(ValueType)
        assert len(members) == 5

    def test_ac_2_3_1_enum_exported_from_init(self) -> None:
        """TEST-AC-9.3.2.8 [P0]: ValueType is exported from __init__.py.

        Given the classification package __init__.py
        When we import from the package root
        Then ValueType is accessible
        """
        # Arrange/Act: Import from package root
        from raglite.ingestion.classification import ValueType

        # Assert: Successfully imported (no ImportError)
        assert ValueType is not None
        # Verify it is the actual enum, not just any object
        from enum import Enum

        assert issubclass(ValueType, Enum)
