"""Validation Script Edge Cases for Story 9.7 - Coverage and Accuracy Validation.

This file tests validation script edge cases:
- Empty dataset handling
- Invalid ground truth files
- Database connection failures
- Large dataset performance
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import psycopg2
import pytest

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.story_9_7,
]


class TestValidationScriptsEdgeCases:
    """Edge cases for validation scripts (coverage, accuracy)."""

    def test_coverage_validation_zero_rows(self) -> None:
        """[P1] Coverage validation handles empty database.

        EDGE CASE: financial_tables has 0 rows
        EXPECTED: Reports 0% coverage, not division by zero
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "validate_coverage", "scripts/validate-classification-coverage.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Mock: database returns 0 rows
            mock_cursor = MagicMock()
            # fetchone returns tuple
            mock_cursor.fetchone = MagicMock(return_value=(0, 0, 0, 0, 0, 0, 0))

            mock_context_mgr = MagicMock()
            mock_context_mgr.__enter__ = MagicMock(return_value=mock_cursor)
            mock_context_mgr.__exit__ = MagicMock(return_value=False)

            mock_conn = MagicMock()
            mock_conn.cursor = MagicMock(return_value=mock_context_mgr)
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)

            with patch("psycopg2.connect", return_value=mock_conn):
                # Act: Query coverage
                coverage = module.query_coverage("conn_str")

                # Assert: No division by zero error
                assert coverage["total_rows"] == 0
                assert coverage["with_period_type"] == 0
        finally:
            sys.path.pop(0)

    def test_coverage_validation_sql_injection_prevention(self) -> None:
        """[P0] Coverage breakdown prevents SQL injection.

        SECURITY: Malicious field parameter
        EXPECTED: ValueError for invalid field name
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "validate_coverage", "scripts/validate-classification-coverage.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Act & Assert: Should reject invalid field
            with pytest.raises(ValueError, match="Invalid field"):
                module.query_breakdown("conn_str", "DROP TABLE financial_tables;--")
        finally:
            sys.path.pop(0)

    @pytest.mark.slow
    def test_accuracy_validation_ground_truth_missing(self) -> None:
        """[P0] Accuracy validation fails when ground truth missing.

        ERROR PATH: classification_ground_truth.json does not exist
        EXPECTED: Script exits with error code 1
        """
        result = subprocess.run(
            [
                "python",
                "scripts/validate-classification-accuracy.py",
                "--ground-truth",
                "/tmp/nonexistent_ground_truth_9_7.json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should fail with error
        assert result.returncode == 1
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()

    @pytest.mark.slow
    def test_accuracy_validation_empty_ground_truth(self) -> None:
        """[P1] Accuracy validation handles empty ground truth entries.

        EDGE CASE: Ground truth JSON has empty entries list
        EXPECTED: Reports 0 samples validated, no division errors
        """
        # Create empty ground truth file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": "1.0", "entries": []}, f)
            temp_path = f.name

        try:
            result = subprocess.run(
                [
                    "python",
                    "scripts/validate-classification-accuracy.py",
                    "--ground-truth",
                    temp_path,
                    "--output",
                    "/tmp/test_accuracy_report_9_7.md",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Should handle gracefully (may fail or warn about empty data)
            assert "Loaded 0 ground truth entries" in result.stdout
        finally:
            Path(temp_path).unlink(missing_ok=True)
            Path("/tmp/test_accuracy_report_9_7.md").unlink(missing_ok=True)

    @pytest.mark.slow
    def test_accuracy_validation_database_connection_failure(self) -> None:
        """[P0] Accuracy validation handles database connection errors.

        ERROR PATH: Cannot connect to PostgreSQL
        EXPECTED: Script fails with connection error
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "validate_accuracy", "scripts/validate-classification-accuracy.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Create mock ground truth entry
            mock_entry = module.GroundTruthEntry(
                document="test.pdf",
                page=1,
                table_index=0,
                row_index=0,
                period="Jan-24",
                entity="Test",
                expected_period_type="monthly_actual",
                expected_value_type="actual",
                expected_entity_level="company_only",
            )

            # Mock: database connection fails
            with patch(
                "psycopg2.connect", side_effect=psycopg2.OperationalError("connection refused")
            ):
                # Act & Assert
                with pytest.raises(psycopg2.OperationalError, match="connection refused"):
                    module.query_actual_classification("bad_conn_str", mock_entry)
        finally:
            sys.path.pop(0)

    @pytest.mark.slow
    def test_coverage_validation_large_dataset(self) -> None:
        """[P2] Coverage validation handles large dataset efficiently.

        EDGE CASE: financial_tables has 1M+ rows
        EXPECTED: Script completes without memory issues
        """
        sys.path.insert(0, str(Path("scripts")))
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "validate_coverage", "scripts/validate-classification-coverage.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Mock: large dataset response
            mock_cursor = MagicMock()
            # Return large numbers
            mock_cursor.fetchone = MagicMock(
                return_value=(1000000, 850000, 800000, 75000, 70000, 50000, 30000)
            )

            mock_context_mgr = MagicMock()
            mock_context_mgr.__enter__ = MagicMock(return_value=mock_cursor)
            mock_context_mgr.__exit__ = MagicMock(return_value=False)

            mock_conn = MagicMock()
            mock_conn.cursor = MagicMock(return_value=mock_context_mgr)
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)

            with patch("psycopg2.connect", return_value=mock_conn):
                # Act: Query coverage with large dataset
                coverage = module.query_coverage("conn_str")

                # Assert: Handles large numbers without overflow
                assert coverage["total_rows"] == 1000000
                assert coverage["with_period_type"] == 850000
                # Verify percentage calculation works
                percentage = (coverage["with_period_type"] / coverage["total_rows"]) * 100
                assert 80 < percentage < 90
        finally:
            sys.path.pop(0)
