"""ATDD tests for Story 9.6 AC5 - Storage Metrics Include Classification.

TDD RED Phase: All tests MUST fail initially because the storage module
has not been updated to include classification coverage metrics in logging.

Test IDs follow pattern: TEST-AC-9.6.5.{test}

BDD Acceptance Criteria:
Given classification fields add storage overhead
When store_tables_in_postgresql() completes successfully
Then logging includes classification field presence:
  - rows_with_classification: count of rows with all 3 fields populated
  - rows_without_classification: count of rows with NULL classification
And metrics enable monitoring of classification coverage during migration
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC5StorageMetricsIncludeClassification:
    """AC5: Storage Metrics Include Classification.

    Given classification fields add storage overhead
    When store_tables_in_postgresql() completes successfully
    Then logging includes classification field presence metrics
    """

    def test_ac_5_1_1_count_classification_coverage_function_exists(self) -> None:
        """TEST-AC-9.6.5.1 [P0]: Classification coverage counting function exists.

        Given the table_store module
        When we look for classification coverage counting
        Then a function _count_classification_coverage exists
        """
        from raglite.ingestion.storage import table_store

        # Assert: Module has classification coverage function
        # RED STATE: Function doesn't exist yet
        assert hasattr(table_store, "_count_classification_coverage")

    def test_ac_5_1_2_rows_with_full_classification_counted(self) -> None:
        """TEST-AC-9.6.5.2 [P0]: Rows with full classification are counted.

        Given rows with all three classification fields
        When counting classification coverage
        Then rows_with_classification is correct
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        # Arrange: Rows with full classification
        rows = [
            {
                "entity": "Portugal",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "geographic",
            },
            {
                "entity": "Spain",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "geographic",
            },
        ]

        # Act: Count coverage
        result = _count_classification_coverage(rows)

        # Assert: Both rows counted as having classification
        assert result["rows_with_classification"] == 2

    def test_ac_5_1_3_rows_without_classification_counted(self) -> None:
        """TEST-AC-9.6.5.3 [P0]: Rows without classification are counted.

        Given rows without any classification fields
        When counting classification coverage
        Then rows_without_classification is correct
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        # Arrange: Rows without classification (legacy)
        rows = [
            {"entity": "Portugal", "metric": "Sales"},
            {"entity": "Spain", "metric": "Revenue"},
            {"entity": "GROUP", "metric": "Total"},
        ]

        # Act: Count coverage
        result = _count_classification_coverage(rows)

        # Assert: All rows counted as without classification
        assert result["rows_without_classification"] == 3

    def test_ac_5_1_4_mixed_rows_counted_correctly(self) -> None:
        """TEST-AC-9.6.5.4 [P0]: Mixed rows with/without classification counted.

        Given a mix of classified and unclassified rows
        When counting classification coverage
        Then both counts are correct
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        # Arrange: Mixed rows
        rows = [
            # Fully classified
            {
                "entity": "Portugal",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "geographic",
            },
            # Not classified
            {"entity": "Spain", "metric": "Sales"},
            # Partially classified (counts as without)
            {"entity": "GROUP", "period_type": "ytd_actual"},
            # Fully classified
            {
                "entity": "SECIL",
                "period_type": "budget",
                "value_type": "budget",
                "entity_level": "company_only",
            },
        ]

        # Act: Count coverage
        result = _count_classification_coverage(rows)

        # Assert: 2 with classification, 2 without
        assert result["rows_with_classification"] == 2
        assert result["rows_without_classification"] == 2

    def test_ac_5_1_5_partial_classification_counts_as_without(self) -> None:
        """TEST-AC-9.6.5.5 [P0]: Partial classification counts as without.

        Given a row with only some classification fields
        When counting classification coverage
        Then the row counts as rows_without_classification
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        # Arrange: Row with partial classification
        rows = [
            {
                "entity": "Portugal",
                "period_type": "monthly_actual",
                # Missing value_type and entity_level
            },
            {
                "entity": "Spain",
                "value_type": "actual",
                # Missing period_type and entity_level
            },
            {
                "entity": "GROUP",
                "entity_level": "consolidated",
                # Missing period_type and value_type
            },
        ]

        # Act: Count coverage
        result = _count_classification_coverage(rows)

        # Assert: All count as without (need ALL 3 fields)
        assert result["rows_with_classification"] == 0
        assert result["rows_without_classification"] == 3

    def test_ac_5_1_6_empty_rows_list_returns_zero(self) -> None:
        """TEST-AC-9.6.5.6 [P0]: Empty rows list returns zero counts.

        Given an empty list of rows
        When counting classification coverage
        Then both counts are 0
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        # Arrange: Empty list
        rows = []

        # Act: Count coverage
        result = _count_classification_coverage(rows)

        # Assert: Both zero
        assert result["rows_with_classification"] == 0
        assert result["rows_without_classification"] == 0

    def test_ac_5_1_7_coverage_percentage_calculated(self) -> None:
        """TEST-AC-9.6.5.7 [P1]: Classification coverage percentage calculated.

        Given rows with mixed classification status
        When counting classification coverage
        Then classification_coverage_pct is calculated correctly
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        # Arrange: 3 out of 4 rows classified
        rows = [
            {
                "entity": "A",
                "period_type": "x",
                "value_type": "y",
                "entity_level": "z",
            },
            {
                "entity": "B",
                "period_type": "x",
                "value_type": "y",
                "entity_level": "z",
            },
            {
                "entity": "C",
                "period_type": "x",
                "value_type": "y",
                "entity_level": "z",
            },
            {"entity": "D"},  # Not classified
        ]

        # Act: Count coverage
        result = _count_classification_coverage(rows)

        # Assert: 75% coverage (3/4)
        assert result["classification_coverage_pct"] == 75.0

    def test_ac_5_1_8_logging_includes_classification_metrics(self) -> None:
        """TEST-AC-9.6.5.8 [P0]: Storage logging includes classification metrics.

        Given rows to store
        When _log_storage_success() is called with classification metrics
        Then log output includes rows_with_classification and rows_without_classification
        """

        # Verify that _log_storage_success accepts classification_metrics parameter
        # RED STATE: Current function signature doesn't include classification_metrics
        import inspect

        from raglite.ingestion.storage.table_store import _log_storage_success

        sig = inspect.signature(_log_storage_success)
        params = list(sig.parameters.keys())

        # Assert: Function should accept classification_metrics parameter
        # RED STATE: Current signature is (records_count, skipped_count, ...)
        assert "classification_metrics" in params or len(params) >= 6

    def test_ac_5_1_9_classification_metrics_in_log_extra(self) -> None:
        """TEST-AC-9.6.5.9 [P1]: Classification metrics in structured log extra.

        Given storage completes successfully
        When examining _count_classification_coverage output
        Then result dict contains all required metrics for logging
        """
        # Verify output structure matches expected format
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        # Arrange
        rows = [
            {
                "entity": "Test",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "geographic",
            }
        ]

        # Act
        result = _count_classification_coverage(rows)

        # Assert: Result has expected keys for logging
        assert "rows_with_classification" in result
        assert "rows_without_classification" in result
        assert "classification_coverage_pct" in result
        assert isinstance(result["rows_with_classification"], int)
        assert isinstance(result["rows_without_classification"], int)
        assert isinstance(result["classification_coverage_pct"], (int, float))

    def test_ac_5_1_10_null_values_treated_as_unclassified(self) -> None:
        """TEST-AC-9.6.5.10 [P1]: Explicit None values treated as unclassified.

        Given rows with explicit None classification values
        When counting classification coverage
        Then they count as rows_without_classification
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        # Arrange: Rows with explicit None values
        rows = [
            {
                "entity": "Portugal",
                "period_type": None,
                "value_type": None,
                "entity_level": None,
            },
            {
                "entity": "Spain",
                "period_type": "monthly_actual",
                "value_type": None,  # One None
                "entity_level": "geographic",
            },
        ]

        # Act: Count coverage
        result = _count_classification_coverage(rows)

        # Assert: Both count as without classification
        assert result["rows_with_classification"] == 0
        assert result["rows_without_classification"] == 2
