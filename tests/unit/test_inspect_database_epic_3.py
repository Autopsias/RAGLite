"""Unit tests for scripts/inspect-database-for-epic-3.py.

Tests database inspection logic, JSON catalog generation, and validation
for Epic 3 data dictionary creation.

Test Coverage (AC1):
- SQL query construction for metrics, periods, entities, units
- JSON catalog structure generation
- Data aggregation and counting
- File writing operations
- Error handling for database connection failures

All tests use mocked database client to avoid external dependencies.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Add parent directory to path to import scripts
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.inspect_database_for_epic_3 import inspect_database


@pytest.mark.priority("P0")
@pytest.mark.unit
class TestFetchDistinctMetrics:
    """Test fetching distinct metrics from financial_tables."""

    def test_fetch_distinct_metrics_success(self):
        """GIVEN database with financial_tables
        WHEN querying distinct metrics via inspect_database
        THEN should return complete sorted metric list"""
        # GIVEN: Mock psycopg2 connection and cursor with sample metrics
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (170142,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",), ("Fixed Cost",), ("Revenue",), ("Variable Cost",)],  # metrics
            [("Aug-25",)],  # periods
            [("Portugal Cement",)],  # entities
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should return sorted list of metrics
                assert catalog["metrics"] == ["EBITDA", "Fixed Cost", "Revenue", "Variable Cost"]
                assert "metrics" in catalog

    def test_fetch_distinct_metrics_empty_table(self):
        """GIVEN empty financial_tables
        WHEN querying distinct metrics
        THEN should return empty list"""
        # GIVEN: Mock database with no data
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)  # row count = 0
        mock_cursor.fetchall.side_effect = [
            [],  # metrics
            [],  # periods
            [],  # entities
            [],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting empty database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should return empty list
                assert catalog["metrics"] == []

    def test_fetch_distinct_metrics_database_error(self):
        """GIVEN database connection failure
        WHEN querying distinct metrics
        THEN should raise connection error"""
        # GIVEN: Mock connection that raises error
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection",
            side_effect=ConnectionError("Database unavailable"),
        ):
            # WHEN/THEN: Should raise connection error
            with pytest.raises(ConnectionError, match="Failed to connect to PostgreSQL"):
                inspect_database()


@pytest.mark.priority("P0")
@pytest.mark.unit
class TestFetchDistinctPeriods:
    """Test fetching distinct periods from financial_tables."""

    def test_fetch_distinct_periods_success(self):
        """GIVEN database with financial_tables
        WHEN querying distinct periods
        THEN should return complete sorted period list"""
        # GIVEN: Mock database with sample periods
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",)],  # metrics
            [("Aug-25",), ("Aug-25 YTD",), ("Jul-25",), ("Sep-25",)],  # periods (sorted)
            [("Portugal Cement",)],  # entities
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should return sorted list (SQL ORDER BY handles sorting)
                assert catalog["periods"] == ["Aug-25", "Aug-25 YTD", "Jul-25", "Sep-25"]
                assert "periods" in catalog


@pytest.mark.priority("P0")
@pytest.mark.unit
class TestFetchDistinctEntities:
    """Test fetching distinct entities from financial_tables."""

    def test_fetch_distinct_entities_success(self):
        """GIVEN database with financial_tables
        WHEN querying distinct entities
        THEN should return complete sorted entity list"""
        # GIVEN: Mock database with sample entities
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",)],  # metrics
            [("Aug-25",)],  # periods
            [
                ("Currency (1000 EUR)",),
                ("Portugal Cement",),
                ("Secil Angola",),
                ("Tunisia Cement",),
            ],  # entities (sorted)
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should return sorted list
                expected = [
                    "Currency (1000 EUR)",
                    "Portugal Cement",
                    "Secil Angola",
                    "Tunisia Cement",
                ]
                assert catalog["entities"] == expected
                assert "entities" in catalog


@pytest.mark.priority("P0")
@pytest.mark.unit
class TestFetchDistinctUnits:
    """Test fetching distinct units from financial_tables."""

    def test_fetch_distinct_units_success(self):
        """GIVEN database with financial_tables
        WHEN querying distinct units
        THEN should return unit list (EUR, USD, EUR/ton, etc.)"""
        # GIVEN: Mock database with unit data (actual column is 'unit', not 'currency')
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",)],  # metrics
            [("Aug-25",)],  # periods
            [("Portugal Cement",)],  # entities
            [("EUR",), ("EUR/ton",), ("USD",)],  # units (sorted)
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should return unit list
                assert catalog["units"] == ["EUR", "EUR/ton", "USD"]
                assert "units" in catalog


@pytest.mark.priority("P0")
@pytest.mark.unit
class TestFetchRowCount:
    """Test fetching total row count from financial_tables."""

    def test_fetch_row_count_success(self):
        """GIVEN database with 170,142 rows
        WHEN querying row count
        THEN should return correct count"""
        # GIVEN: Mock database with known row count
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (170142,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",)],  # metrics
            [("Aug-25",)],  # periods
            [("Portugal Cement",)],  # entities
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should return 170,142
                assert catalog["total_rows"] == 170142
                assert "total_rows" in catalog
                # Verify SQL query was executed for row count
                calls = [str(call) for call in mock_cursor.execute.call_args_list]
                assert any("COUNT(*)" in str(call) for call in calls)


@pytest.mark.priority("P0")
@pytest.mark.unit
class TestGenerateJsonCatalog:
    """Test JSON catalog generation from inspection results."""

    def test_generate_json_catalog_structure(self):
        """GIVEN inspection results with all data
        WHEN generating JSON catalog via inspect_database
        THEN should produce correct structure with all fields"""
        # GIVEN: Mock database with complete data
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (170142,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",), ("Revenue",), ("Variable Cost",)],  # metrics
            [("Aug-25",), ("Aug-25 YTD",), ("Sep-25",)],  # periods
            [("Portugal Cement",), ("Tunisia Cement",)],  # entities
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting database (generates catalog)
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should have all required fields with correct data
                assert "metrics" in catalog
                assert "periods" in catalog
                assert "entities" in catalog
                assert "units" in catalog
                assert "total_rows" in catalog
                assert catalog["metrics"] == ["EBITDA", "Revenue", "Variable Cost"]
                assert catalog["total_rows"] == 170142

    def test_generate_json_catalog_empty_data(self):
        """GIVEN empty inspection results
        WHEN generating JSON catalog
        THEN should produce catalog with empty lists"""
        # GIVEN: Mock database with no data
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)  # row count = 0
        mock_cursor.fetchall.side_effect = [
            [],  # metrics
            [],  # periods
            [],  # entities
            [],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting empty database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should have structure with empty arrays
                assert catalog["metrics"] == []
                assert catalog["total_rows"] == 0


@pytest.mark.priority("P0")
@pytest.mark.unit
class TestSaveCatalogToFile:
    """Test saving JSON catalog to file."""

    def test_save_catalog_to_file_success(self):
        """GIVEN valid JSON catalog
        WHEN saving to file via inspect_database
        THEN should write correctly formatted JSON"""
        # GIVEN: Mock database returning valid data
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (170142,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",), ("Revenue",)],  # metrics
            [("Aug-25",)],  # periods
            [("Portugal Cement",)],  # entities
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting database (saves to file)
        mock_file_handle = mock_open()
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("pathlib.Path.open", mock_file_handle):
                _catalog = inspect_database(output_path="docs/data-dictionary-epic-3.json")

                # THEN: Should write JSON with proper formatting
                mock_file_handle.assert_called_once_with("w")
                handle = mock_file_handle()
                written_content = "".join(str(call.args[0]) for call in handle.write.call_args_list)
                parsed = json.loads(written_content)
                assert parsed["total_rows"] == 170142
                assert parsed["metrics"] == ["EBITDA", "Revenue"]
                assert _catalog is not None  # Verify catalog was returned

    def test_save_catalog_to_file_creates_directory(self):
        """GIVEN catalog and non-existent directory
        WHEN saving to file
        THEN should create directory structure"""
        # GIVEN: Mock database with data
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)  # row count
        mock_cursor.fetchall.side_effect = [[], [], [], []]  # empty lists

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock Path.stat() to return file size
        mock_stat = MagicMock()
        mock_stat.st_size = 100

        # WHEN: Saving to file in new directory
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                with patch("pathlib.Path.open", mock_open()):
                    with patch("pathlib.Path.stat", return_value=mock_stat):
                        inspect_database(output_path="docs/new-folder/catalog.json")

                        # THEN: Should create parent directories
                        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


@pytest.mark.priority("P0")
@pytest.mark.unit
class TestInspectDatabase:
    """Test main inspect_database orchestration function."""

    def test_inspect_database_full_flow(self):
        """GIVEN database connection
        WHEN running full inspection
        THEN should query all data and return complete catalog"""
        # GIVEN: Mock psycopg2 connection with complete data
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (170142,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",)],  # metrics
            [("Aug-25",)],  # periods
            [("Portugal Cement",)],  # entities
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Running inspect_database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                result = inspect_database()

                # THEN: Should return complete catalog
                assert result["metrics"] == ["EBITDA"]
                assert result["periods"] == ["Aug-25"]
                assert result["entities"] == ["Portugal Cement"]
                assert result["units"] == ["EUR"]
                assert result["total_rows"] == 170142

    def test_inspect_database_saves_json(self):
        """GIVEN successful inspection
        WHEN running inspect_database
        THEN should save catalog to JSON file"""
        # GIVEN: Mock database with sample data
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",)],  # metrics
            [("Aug-25",)],  # periods
            [("Portugal",)],  # entities
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Running inspection with file save
        mock_file_handle = mock_open()
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("pathlib.Path.open", mock_file_handle):
                inspect_database(output_path="docs/data-dictionary-epic-3.json")

                # THEN: Should save to correct path
                mock_file_handle.assert_called_once_with("w")


@pytest.mark.priority("P1")
@pytest.mark.unit
class TestCatalogStructureValidation:
    """Test catalog structure validation (dict-based, no Pydantic model)."""

    def test_catalog_structure_validation(self):
        """GIVEN inspection data
        WHEN generating catalog
        THEN should validate structure with correct keys"""
        # GIVEN: Mock database with valid data
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (170142,)  # row count
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",)],  # metrics
            [("Aug-25",)],  # periods
            [("Portugal",)],  # entities
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should have valid structure
                assert isinstance(catalog, dict)
                assert catalog["total_rows"] == 170142
                assert len(catalog["metrics"]) == 1
                assert all(
                    key in catalog
                    for key in ["metrics", "periods", "entities", "units", "total_rows"]
                )

    def test_catalog_list_types(self):
        """GIVEN inspection results
        WHEN generating catalog
        THEN should ensure all list fields are actual lists"""
        # GIVEN: Mock database with data
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)
        mock_cursor.fetchall.side_effect = [
            [("EBITDA",)],  # metrics
            [("Aug-25",)],  # periods
            [("Portugal",)],  # entities
            [("EUR",)],  # units
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # WHEN: Inspecting database
        with patch(
            "scripts.inspect_database_for_epic_3.get_postgresql_connection", return_value=mock_conn
        ):
            with patch("builtins.open", mock_open()):
                catalog = inspect_database()

                # THEN: Should have proper types
                assert isinstance(catalog["metrics"], list)
                assert isinstance(catalog["periods"], list)
                assert isinstance(catalog["entities"], list)
                assert isinstance(catalog["units"], list)
                assert isinstance(catalog["total_rows"], int)
