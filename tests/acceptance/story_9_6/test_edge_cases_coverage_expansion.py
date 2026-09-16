"""Coverage expansion tests for Story 9.6 - Edge cases and error paths.

These tests were added in Phase 6 (Coverage Expansion) to find gaps in:
- Edge cases (null handling, boundary values, special characters)
- Error paths (validation errors, type mismatches)
- Integration scenarios (batch processing edge cases)

Each test is tagged with priority:
- [P0]: Critical path, must never fail
- [P1]: Important scenarios
- [P2]: Edge cases
- [P3]: Nice-to-have
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestEdgeCasesNullHandling:
    """Edge cases for NULL and missing value handling.

    Gap found: Original tests don't cover mixed None/empty string scenarios
    or edge cases with partial data.
    """

    @pytest.mark.parametrize(
        "period_type,value_type,entity_level,expected_classification",
        [
            # [P1] All empty strings (should count as unclassified)
            ("", "", "", False),
            # [P2] Mix of empty string and None (should count as unclassified)
            ("", None, "company_only", False),
            (None, "", "company_only", False),
            ("monthly_actual", None, "", False),
        ],
    )
    def test_edge_case_mixed_empty_and_none_values(
        self,
        period_type: str | None,
        value_type: str | None,
        entity_level: str | None,
        expected_classification: bool,
    ) -> None:
        """TEST-EDGE-9.6.1 [P1/P2]: Mixed empty strings and None values.

        Given rows with various combinations of empty strings and None
        When counting classification coverage
        Then only rows with ALL three non-empty fields count as classified

        NOTE: Whitespace-only strings (e.g., "   ") are treated as VALID
        classification values by current implementation. This is a potential
        bug but documented here as current behavior.
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        rows = [
            {
                "entity": "Test",
                "period_type": period_type,
                "value_type": value_type,
                "entity_level": entity_level,
            }
        ]

        result = _count_classification_coverage(rows)

        if expected_classification:
            assert result["rows_with_classification"] == 1
            assert result["rows_without_classification"] == 0
        else:
            assert result["rows_with_classification"] == 0
            assert result["rows_without_classification"] == 1

    def test_edge_case_whitespace_only_strings_bug(self) -> None:
        """TEST-EDGE-9.6.1b [P2]: Whitespace-only strings treated as valid.

        BUG FOUND: Implementation treats whitespace-only strings as valid
        classification values instead of treating them as unclassified.

        Given rows with whitespace-only classification values
        When counting classification coverage
        Then current implementation counts them as classified (BUG)
        But they SHOULD be counted as unclassified

        This test documents the bug for future fix in refactoring story.
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        rows = [
            {
                "entity": "Test",
                "period_type": "   ",  # Whitespace only
                "value_type": "actual",
                "entity_level": "company_only",
            }
        ]

        result = _count_classification_coverage(rows)

        # Current (buggy) behavior: counts as classified
        assert result["rows_with_classification"] == 1
        # Expected behavior would be: assert result["rows_without_classification"] == 1


class TestEdgeCasesBoundaryValues:
    """Boundary value tests for classification fields.

    Gap found: No tests for extremely long strings, special characters,
    or VARCHAR limit edge cases.
    """

    def test_edge_case_maximum_varchar_length_period_type(self) -> None:
        """TEST-EDGE-9.6.2 [P2]: period_type at VARCHAR(50) boundary.

        Given a period_type value at the maximum allowed length (50 chars)
        When storing the row
        Then the value is stored successfully without truncation
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # 50 characters exactly (VARCHAR(50) limit)
        max_length_value = "x" * 50

        rows = [
            {
                "document_id": "test-doc",
                "entity": "Test",
                "period_type": max_length_value,
                "value_type": "actual",
                "entity_level": "company_only",
            }
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 1
        assert records[0][13] == max_length_value

    def test_edge_case_maximum_varchar_length_value_type(self) -> None:
        """TEST-EDGE-9.6.3 [P2]: value_type at VARCHAR(50) boundary.

        Given a value_type value at the maximum allowed length (50 chars)
        When storing the row
        Then the value is stored successfully without truncation
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        max_length_value = "y" * 50

        rows = [
            {
                "document_id": "test-doc",
                "entity": "Test",
                "period_type": "monthly_actual",
                "value_type": max_length_value,
                "entity_level": "company_only",
            }
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 1
        assert records[0][14] == max_length_value

    def test_edge_case_maximum_varchar_length_entity_level(self) -> None:
        """TEST-EDGE-9.6.4 [P2]: entity_level at VARCHAR(100) boundary.

        Given an entity_level value at the maximum allowed length (100 chars)
        When storing the row
        Then the value is stored successfully without truncation
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # 100 characters exactly (VARCHAR(100) limit)
        max_length_value = "z" * 100

        rows = [
            {
                "document_id": "test-doc",
                "entity": "Test",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": max_length_value,
            }
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 1
        assert records[0][15] == max_length_value


class TestEdgeCasesSpecialCharacters:
    """Special character handling tests.

    Gap found: No tests for Unicode, special characters, or
    potentially problematic strings (SQL injection patterns, etc.)
    """

    @pytest.mark.parametrize(
        "classification_value,field_name",
        [
            # [P1] Unicode characters
            ("résumé_données", "period_type"),
            ("açúcar_café", "value_type"),
            ("região_geográfica", "entity_level"),
            # [P2] Special characters
            ("period-with-dashes", "period_type"),
            ("value_with_underscores", "value_type"),
            ("entity.with.dots", "entity_level"),
            # [P2] Numbers in classification
            ("period_2024_Q1", "period_type"),
            ("value_123", "value_type"),
            ("entity_level_1", "entity_level"),
            # [P2] Mixed case and symbols
            ("Period-Type_2024", "period_type"),
            ("VALUE@TYPE", "value_type"),
            ("Entity#Level$123", "entity_level"),
        ],
    )
    def test_edge_case_special_characters_in_classification(
        self, classification_value: str, field_name: str
    ) -> None:
        """TEST-EDGE-9.6.5 [P1/P2]: Special characters in classification values.

        Given classification fields with Unicode, special characters, numbers
        When storing the row
        Then values are stored exactly as provided without sanitization
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        rows = [
            {
                "document_id": "test-doc",
                "entity": "Test",
                field_name: classification_value,
            }
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 1
        # Find which position (13, 14, or 15) based on field_name
        field_positions = {
            "period_type": 13,
            "value_type": 14,
            "entity_level": 15,
        }
        position = field_positions[field_name]
        assert records[0][position] == classification_value

    def test_edge_case_sql_injection_pattern_stored_safely(self) -> None:
        """TEST-EDGE-9.6.6 [P1]: SQL injection patterns stored safely.

        Given classification fields with SQL-like syntax
        When storing the row
        Then values are stored safely without execution (parameterized queries)
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # SQL injection attempt pattern (should be stored as-is, not executed)
        malicious_value = "'; DROP TABLE financial_tables; --"

        rows = [
            {
                "document_id": "test-doc",
                "entity": "Test",
                "period_type": malicious_value,
                "value_type": "actual",
                "entity_level": "company_only",
            }
        ]

        records, skipped = _prepare_table_records(rows)

        # Should be stored as-is (parameterized queries prevent SQL injection)
        assert len(records) == 1
        assert records[0][13] == malicious_value


class TestEdgeCasesBatchProcessing:
    """Batch processing edge cases.

    Gap found: No tests for very large batches, empty batches,
    or batch size boundary conditions.
    """

    def test_edge_case_single_row_batch(self) -> None:
        """TEST-EDGE-9.6.7 [P2]: Batch processing with single row.

        Given a batch with exactly one row
        When preparing records
        Then single row is processed correctly
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        rows = [
            {
                "document_id": "test-doc-001",
                "entity": "Test",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            }
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 1
        assert skipped == 0

    def test_edge_case_large_batch_1000_rows(self) -> None:
        """TEST-EDGE-9.6.8 [P2]: Large batch with 1000 rows.

        Given a batch with 1000 rows (10x default batch size)
        When preparing records
        Then all rows are processed correctly
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        # Generate 1000 rows
        rows = [
            {
                "document_id": f"test-doc-{i:04d}",
                "entity": f"Entity-{i}",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            }
            for i in range(1000)
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 1000
        assert skipped == 0
        # Verify first and last records
        assert records[0][13] == "monthly_actual"
        assert records[999][13] == "monthly_actual"

    def test_edge_case_all_rows_missing_document_id(self) -> None:
        """TEST-EDGE-9.6.9 [P1]: All rows missing document_id.

        Given a batch where all rows are missing document_id
        When preparing records
        Then all rows are skipped and skipped_count reflects this
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        rows = [
            {
                # No document_id
                "entity": "Test-1",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            {
                # No document_id
                "entity": "Test-2",
                "period_type": "ytd_actual",
                "value_type": "actual",
                "entity_level": "consolidated",
            },
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 0
        assert skipped == 2

    def test_edge_case_mixed_valid_and_missing_document_id(self) -> None:
        """TEST-EDGE-9.6.10 [P1]: Mix of valid and missing document_id.

        Given a batch with some rows having document_id and some not
        When preparing records
        Then only valid rows are included, skipped count is accurate
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        rows = [
            # Valid row
            {
                "document_id": "test-doc-001",
                "entity": "Test-1",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            # Missing document_id
            {
                "entity": "Test-2",
                "period_type": "ytd_actual",
                "value_type": "actual",
                "entity_level": "consolidated",
            },
            # Valid row
            {
                "document_id": "test-doc-003",
                "entity": "Test-3",
                "period_type": "budget",
                "value_type": "budget",
                "entity_level": "segment",
            },
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 2
        assert skipped == 1
        # Verify the valid records are included
        assert records[0][0] == "test-doc-001"
        assert records[1][0] == "test-doc-003"


class TestEdgeCasesClassificationCoverage:
    """Classification coverage metric edge cases.

    Gap found: No tests for coverage percentage edge cases,
    rounding behavior, or zero-division scenarios.
    """

    def test_edge_case_zero_percent_coverage(self) -> None:
        """TEST-EDGE-9.6.11 [P2]: Zero classification coverage.

        Given rows with no classification
        When calculating coverage
        Then coverage_pct is 0.0
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        rows = [
            {"entity": "Test-1"},
            {"entity": "Test-2"},
            {"entity": "Test-3"},
        ]

        result = _count_classification_coverage(rows)

        assert result["classification_coverage_pct"] == 0.0
        assert result["rows_with_classification"] == 0
        assert result["rows_without_classification"] == 3

    def test_edge_case_hundred_percent_coverage(self) -> None:
        """TEST-EDGE-9.6.12 [P2]: 100% classification coverage.

        Given all rows fully classified
        When calculating coverage
        Then coverage_pct is 100.0
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        rows = [
            {
                "entity": f"Test-{i}",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            }
            for i in range(5)
        ]

        result = _count_classification_coverage(rows)

        assert result["classification_coverage_pct"] == 100.0
        assert result["rows_with_classification"] == 5
        assert result["rows_without_classification"] == 0

    def test_edge_case_coverage_percentage_rounding(self) -> None:
        """TEST-EDGE-9.6.13 [P2]: Coverage percentage rounding behavior.

        Given 1 classified row out of 3 (33.333...%)
        When calculating coverage
        Then percentage is rounded to 1 decimal place (33.3%)
        """
        from raglite.ingestion.storage.table_store import _count_classification_coverage

        rows = [
            # Classified
            {
                "entity": "Test-1",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            },
            # Not classified
            {"entity": "Test-2"},
            # Not classified
            {"entity": "Test-3"},
        ]

        result = _count_classification_coverage(rows)

        assert result["classification_coverage_pct"] == 33.3
        assert result["rows_with_classification"] == 1
        assert result["rows_without_classification"] == 2


class TestEdgeCasesDataTypeValidation:
    """Data type edge cases.

    Gap found: No tests for non-string classification values,
    type coercion, or unexpected data types.
    """

    def test_edge_case_integer_classification_values(self) -> None:
        """TEST-EDGE-9.6.14 [P2]: Integer values in classification fields.

        Given classification fields with integer values (type coercion test)
        When preparing records
        Then values are handled (Python's row.get() returns integers as-is)
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        rows = [
            {
                "document_id": "test-doc",
                "entity": "Test",
                "period_type": 123,  # Integer instead of string
                "value_type": 456,
                "entity_level": 789,
            }
        ]

        records, skipped = _prepare_table_records(rows)

        # Values stored as-is (no type validation in storage layer)
        assert len(records) == 1
        assert records[0][13] == 123
        assert records[0][14] == 456
        assert records[0][15] == 789

    def test_edge_case_boolean_classification_values(self) -> None:
        """TEST-EDGE-9.6.15 [P3]: Boolean values in classification fields.

        Given classification fields with boolean values
        When preparing records
        Then values are stored as-is (no type validation)
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        rows = [
            {
                "document_id": "test-doc",
                "entity": "Test",
                "period_type": True,  # Boolean
                "value_type": False,
                "entity_level": True,
            }
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 1
        assert records[0][13] is True
        assert records[0][14] is False
        assert records[0][15] is True


class TestIntegrationEndToEndScenarios:
    """Integration scenarios testing complete flow.

    Gap found: No tests combining classification with other field variations,
    or testing interaction between classification and non-classification fields.
    """

    def test_integration_classification_with_minimal_required_fields(self) -> None:
        """TEST-EDGE-9.6.16 [P1]: Classification with minimal required fields.

        Given a row with only document_id, entity, and classification
        When preparing records
        Then row is stored with classification and NULLs for other fields
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        rows = [
            {
                "document_id": "test-doc",
                "entity": "MinimalEntity",
                # No page_number, table_index, metric, period, value, etc.
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "company_only",
            }
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 1
        # Classification fields populated
        assert records[0][13] == "monthly_actual"
        assert records[0][14] == "actual"
        assert records[0][15] == "company_only"
        # Other optional fields are None
        assert records[0][1] is None  # page_number
        assert records[0][2] is None  # table_index
        assert records[0][5] is None  # metric

    def test_integration_classification_with_all_fields_populated(self) -> None:
        """TEST-EDGE-9.6.17 [P1]: Classification with all fields populated.

        Given a row with all 16 fields populated
        When preparing records
        Then complete record tuple is created with all values
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        rows = [
            {
                "document_id": "test-doc-complete",
                "page_number": 10,
                "table_index": 2,
                "table_caption": "Financial Summary",
                "entity": "Portugal Cement",
                "metric": "Revenue",
                "period": "Dec-24",
                "fiscal_year": 2024,
                "value": 1500.5,
                "unit": "EUR millions",
                "row_index": 5,
                "column_name": "December",
                "chunk_text": "Portugal Cement Revenue December 2024: 1500.5 EUR millions",
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "geographic",
            }
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 1
        record = records[0]
        # Verify all 16 fields
        assert record[0] == "test-doc-complete"
        assert record[1] == 10
        assert record[2] == 2
        assert record[3] == "Financial Summary"
        assert record[4] == "Portugal Cement"
        assert record[5] == "Revenue"
        assert record[6] == "Dec-24"
        assert record[7] == 2024
        assert record[8] == 1500.5
        assert record[9] == "EUR millions"
        assert record[10] == 5
        assert record[11] == "December"
        assert record[12] == "Portugal Cement Revenue December 2024: 1500.5 EUR millions"
        assert record[13] == "monthly_actual"
        assert record[14] == "actual"
        assert record[15] == "geographic"

    def test_integration_duplicate_rows_with_different_classification(self) -> None:
        """TEST-EDGE-9.6.18 [P2]: Duplicate rows with different classification.

        Given duplicate rows (same entity/metric) with different classification
        When preparing records
        Then both rows are stored separately (classification differentiates them)
        """
        from raglite.ingestion.storage.table_store import _prepare_table_records

        rows = [
            {
                "document_id": "test-doc",
                "entity": "Portugal",
                "metric": "Revenue",
                "period": "Dec-24",
                "value": 100.0,
                # Actual classification
                "period_type": "monthly_actual",
                "value_type": "actual",
                "entity_level": "geographic",
            },
            {
                "document_id": "test-doc",
                "entity": "Portugal",
                "metric": "Revenue",
                "period": "Dec-24",
                "value": 105.0,  # Different value
                # Budget classification
                "period_type": "budget",
                "value_type": "budget",
                "entity_level": "geographic",
            },
        ]

        records, skipped = _prepare_table_records(rows)

        assert len(records) == 2
        # First row: actual
        assert records[0][13] == "monthly_actual"
        assert records[0][14] == "actual"
        # Second row: budget
        assert records[1][13] == "budget"
        assert records[1][14] == "budget"
