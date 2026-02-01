"""ATDD tests for Story 9.3 AC1 - Value Type Classifier Module Creation.

TDD RED Phase: All tests MUST fail initially because the value_type_classifier
module does not exist yet at raglite/ingestion/classification/.

Test IDs follow pattern: TEST-AC-9.3.1.{test}

BDD Acceptance Criteria:
Given the period classification module exists at raglite/ingestion/classification/
When Story 9.3 is implemented
Then a new module exists at raglite/ingestion/classification/value_type_classifier.py
And it exports ValueType enum and classify_value_type function
And the module follows the same patterns as period_classifier.py
"""



class TestAC1ValueTypeClassifierModuleCreation:
    """AC1: Value Type Classifier Module Creation.

    Given the period classification module exists at raglite/ingestion/classification/
    When Story 9.3 is implemented
    Then a new module exists at raglite/ingestion/classification/value_type_classifier.py
    And it exports ValueType enum and classify_value_type function
    And the module follows the same patterns as period_classifier.py
    """

    def test_ac_1_1_1_module_can_be_imported(self) -> None:
        """TEST-AC-9.3.1.1 [P0]: Value type classifier module can be imported.

        Given the classification package exists
        When we import value_type_classifier
        Then the import succeeds without errors
        """
        # Arrange: Classification package exists
        # Act: Import the value type classifier module
        from raglite.ingestion.classification import value_type_classifier

        # Assert: Module is importable
        assert value_type_classifier is not None

    def test_ac_1_1_2_value_type_enum_exported(self) -> None:
        """TEST-AC-9.3.1.2 [P0]: ValueType enum is exported from module.

        Given the value_type_classifier module exists
        When we import ValueType
        Then it is a valid enum class
        """
        # Arrange/Act: Import ValueType from module
        # Assert: ValueType is an enum
        from enum import Enum

        from raglite.ingestion.classification import ValueType

        assert issubclass(ValueType, Enum)

    def test_ac_1_1_3_classify_value_type_function_exported(self) -> None:
        """TEST-AC-9.3.1.3 [P0]: classify_value_type function is exported.

        Given the value_type_classifier module exists
        When we import classify_value_type
        Then it is a callable function
        """
        # Arrange/Act: Import the function
        from raglite.ingestion.classification import classify_value_type

        # Assert: Function is callable
        assert callable(classify_value_type)

    def test_ac_1_1_4_classified_value_type_dataclass_exported(self) -> None:
        """TEST-AC-9.3.1.4 [P0]: ClassifiedValueType dataclass is exported.

        Given the value_type_classifier module exists
        When we import ClassifiedValueType
        Then it is a dataclass with required fields
        """
        # Arrange/Act: Import the dataclass
        # Assert: It has required fields (original, value_type, source)
        from dataclasses import fields

        from raglite.ingestion.classification import ClassifiedValueType

        field_names = {f.name for f in fields(ClassifiedValueType)}
        assert "original" in field_names
        assert "value_type" in field_names
        assert "source" in field_names

    def test_ac_1_1_5_module_follows_period_classifier_patterns(self) -> None:
        """TEST-AC-9.3.1.5 [P1]: Module follows period_classifier.py patterns.

        Given the period_classifier module exists
        When value_type_classifier is implemented
        Then it follows the same structural patterns
        """
        # Arrange: Import both modules
        from raglite.ingestion.classification import period_classifier, value_type_classifier

        # Assert: Both modules have similar function signatures
        # Period classifier has classify_period, value type should have classify_value_type
        assert hasattr(period_classifier, "classify_period")
        assert hasattr(value_type_classifier, "classify_value_type")

        # Both should have batch functions
        assert hasattr(period_classifier, "classify_periods_batch")
        assert hasattr(value_type_classifier, "classify_value_types_batch")
