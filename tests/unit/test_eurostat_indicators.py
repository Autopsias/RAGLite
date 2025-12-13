"""Unit tests for Eurostat Construction & Industrial Indicators.

Story 6.16: Add Eurostat Construction & Industrial Indicators

ATDD RED PHASE - These tests MUST fail initially because:
1. EurostatConstructionOutput model does not exist
2. EurostatIndustrialProduction model does not exist
3. fetch_construction_output() method does not exist
4. fetch_industrial_production() method does not exist
5. _parse_construction_data() method does not exist
6. _parse_industrial_data() method does not exist

Run with: pytest tests/unit/test_eurostat_indicators.py -v
Expected: All tests should FAIL (RED phase)
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from raglite.external_data.clients.eurostat import EurostatClient
from raglite.external_data.exceptions import ExternalDataFetchError

# These imports will fail until models are implemented (RED phase)
# AC5: Unit tests verify parsing and data quality
try:
    from raglite.external_data.models import (
        EurostatConstructionOutput,
        EurostatIndustrialProduction,
    )
except ImportError:
    # Expected during RED phase - models don't exist yet
    EurostatConstructionOutput = None  # type: ignore[assignment, misc]
    EurostatIndustrialProduction = None  # type: ignore[assignment, misc]


class TestEurostatConstructionOutput:
    """Unit tests for Eurostat construction output index (AC1, AC5).

    Given: Mock Eurostat API responses for construction output
    When: Parsing and fetch methods are called
    Then: Correct data extraction and model creation occurs
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient(timeout=1.0)  # Short timeout for mocked tests

    @pytest.fixture
    def mock_construction_response(self) -> dict:
        """Mock Eurostat SDMX response for construction output.

        Represents sts_copr_m dataset response with 3 months of data.
        Matches real Eurostat SDMX-JSON structure with multi-dimensional indices.
        """
        return {
            "value": {"0": 105.2, "1": 106.8, "2": 104.5},
            "size": [1, 1, 1, 1, 1, 1, 3],  # [freq, indic_bt, nace_r2, s_adj, unit, geo, time]
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"F": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {"category": {"index": {"2024-01": 0, "2024-02": 1, "2024-03": 2}}},
            },
        }

    # =========================================================================
    # AC1: Construction Output Index API - Parsing Tests
    # =========================================================================

    def test_ac1_parse_construction_data_valid(
        self, client: EurostatClient, mock_construction_response: dict
    ) -> None:
        """
        AC1: Parse valid construction output response.

        Given: A valid Eurostat construction output API response
        When: _parse_construction_data() is called
        Then: Returns list of EurostatConstructionOutput with correct values
        """
        result = client._parse_construction_data(
            mock_construction_response, "PT", "F", "SCA", None, None
        )

        assert len(result) == 3
        assert result[0].index_value == 105.2
        assert result[0].country == "PT"
        assert result[0].nace_sector == "F"
        assert result[0].seasonal_adjustment == "SCA"

    def test_ac1_parse_construction_data_returns_model_type(
        self, client: EurostatClient, mock_construction_response: dict
    ) -> None:
        """
        AC1: Parsed data returns EurostatConstructionOutput model.

        Given: A valid Eurostat response
        When: _parse_construction_data() is called
        Then: All items are EurostatConstructionOutput instances
        """
        result = client._parse_construction_data(
            mock_construction_response, "PT", "F", "SCA", None, None
        )

        assert all(isinstance(r, EurostatConstructionOutput) for r in result)

    def test_ac1_parse_construction_data_date_parsing(
        self, client: EurostatClient, mock_construction_response: dict
    ) -> None:
        """
        AC1: Construction data dates are correctly parsed.

        Given: A response with monthly period strings (YYYY-MM)
        When: _parse_construction_data() is called
        Then: Dates are correctly converted to date objects
        """
        result = client._parse_construction_data(
            mock_construction_response, "PT", "F", "SCA", None, None
        )

        assert result[0].date == date(2024, 1, 1)
        assert result[1].date == date(2024, 2, 1)
        assert result[2].date == date(2024, 3, 1)

    def test_ac1_parse_construction_missing_values_skipped(self, client: EurostatClient) -> None:
        """
        AC1: Handle missing values in response gracefully.

        Given: A response with missing index values (gaps in data)
        When: _parse_construction_data() is called
        Then: Only valid records are returned, missing values skipped
        """
        mock_response = {
            "value": {"0": 105.2, "2": 104.5},  # Index 1 missing
            "size": [1, 1, 1, 1, 1, 1, 3],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"F": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {"category": {"index": {"2024-01": 0, "2024-02": 1, "2024-03": 2}}},
            },
        }

        result = client._parse_construction_data(mock_response, "PT", "F", "SCA", None, None)

        assert len(result) == 2  # Only 2 valid records

    def test_ac1_parse_construction_date_filter_start(
        self, client: EurostatClient, mock_construction_response: dict
    ) -> None:
        """
        AC1: Filter construction data by start_date.

        Given: A response with data from Jan-Mar 2024
        When: _parse_construction_data() is called with start_date=Feb
        Then: Only Feb and Mar data is returned
        """
        result = client._parse_construction_data(
            mock_construction_response,
            "PT",
            "F",
            "SCA",
            start_date=date(2024, 2, 1),
            end_date=None,
        )

        assert len(result) == 2
        assert result[0].date == date(2024, 2, 1)

    def test_ac1_parse_construction_date_filter_end(
        self, client: EurostatClient, mock_construction_response: dict
    ) -> None:
        """
        AC1: Filter construction data by end_date.

        Given: A response with data from Jan-Mar 2024
        When: _parse_construction_data() is called with end_date=Feb
        Then: Only Jan and Feb data is returned
        """
        result = client._parse_construction_data(
            mock_construction_response,
            "PT",
            "F",
            "SCA",
            start_date=None,
            end_date=date(2024, 2, 28),
        )

        assert len(result) == 2
        assert all(r.date <= date(2024, 2, 28) for r in result)

    def test_ac1_parse_construction_sorted_by_date(self, client: EurostatClient) -> None:
        """
        AC1: Parsed construction data is sorted by date ascending.

        Given: A response with unsorted time periods
        When: _parse_construction_data() is called
        Then: Results are sorted by date in ascending order
        """
        mock_response = {
            "value": {"0": 104.5, "1": 106.8, "2": 105.2},
            "size": [1, 1, 1, 1, 1, 1, 3],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"F": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {
                    "category": {
                        # Unsorted order in API response
                        "index": {"2024-03": 0, "2024-02": 1, "2024-01": 2}
                    }
                },
            },
        }

        result = client._parse_construction_data(mock_response, "PT", "F", "SCA", None, None)

        dates = [r.date for r in result]
        assert dates == sorted(dates), "Data should be sorted by date ascending"

    # =========================================================================
    # AC1: Construction Output Index API - Fetch Method Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ac1_fetch_construction_output_builds_correct_url(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: fetch_construction_output constructs correct API request.

        Given: Request for Portugal construction output
        When: fetch_construction_output() is called
        Then: Correct dataset and filters are passed to _fetch_eurostat_data
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "value": {},
                "dimension": {"time": {"category": {"index": {}}}},
            }

            await client.fetch_construction_output(country="PT")

            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args

            # Verify dataset code
            assert call_args[0][0] == "sts_copr_m", "Should use construction dataset"

            # Verify filters
            filters = call_args[0][1]
            assert filters["geo"] == "PT"
            assert filters["nace_r2"] == "F"  # Construction sector
            assert filters["s_adj"] == "SCA"  # Seasonally adjusted
            assert filters["unit"] == "I21"  # Index 2021=100

    @pytest.mark.asyncio
    async def test_ac1_fetch_construction_output_returns_data(
        self, client: EurostatClient, mock_construction_response: dict
    ) -> None:
        """
        AC1: fetch_construction_output returns parsed data.

        Given: A valid API response
        When: fetch_construction_output() is called
        Then: Returns list of EurostatConstructionOutput records
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_construction_response

            result = await client.fetch_construction_output(
                country="PT",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
            )

            assert len(result) == 3
            assert all(isinstance(r, EurostatConstructionOutput) for r in result)
            assert result[0].index_value > 0

    @pytest.mark.asyncio
    async def test_ac1_fetch_construction_output_handles_api_error(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: fetch_construction_output handles API errors.

        Given: API returns an error
        When: fetch_construction_output() is called
        Then: ExternalDataFetchError is raised
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ExternalDataFetchError(
                source="Eurostat", message="API unavailable"
            )

            with pytest.raises(ExternalDataFetchError):
                await client.fetch_construction_output(country="PT")


class TestEurostatIndustrialProduction:
    """Unit tests for Eurostat industrial production index (AC2, AC5).

    Given: Mock Eurostat API responses for industrial production
    When: Parsing and fetch methods are called
    Then: Correct data extraction and model creation occurs
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient(timeout=1.0)  # Short timeout for mocked tests

    @pytest.fixture
    def mock_industrial_response(self) -> dict:
        """Mock Eurostat SDMX response for industrial production.

        Represents sts_inpr_m dataset response with 3 months of data.
        Matches real Eurostat SDMX-JSON structure with multi-dimensional indices.
        """
        return {
            "value": {"0": 98.5, "1": 99.2, "2": 100.1},
            "size": [1, 1, 1, 1, 1, 1, 3],  # [freq, indic_bt, nace_r2, s_adj, unit, geo, time]
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"B-D": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {"category": {"index": {"2024-01": 0, "2024-02": 1, "2024-03": 2}}},
            },
        }

    # =========================================================================
    # AC2: Industrial Production Index API - Parsing Tests
    # =========================================================================

    def test_ac2_parse_industrial_data_valid(
        self, client: EurostatClient, mock_industrial_response: dict
    ) -> None:
        """
        AC2: Parse valid industrial production response.

        Given: A valid Eurostat industrial production API response
        When: _parse_industrial_data() is called
        Then: Returns list of EurostatIndustrialProduction with correct values
        """
        result = client._parse_industrial_data(
            mock_industrial_response, "PT", "B-D", "SCA", None, None
        )

        assert len(result) == 3
        assert result[0].index_value == 98.5
        assert result[0].country == "PT"
        assert result[0].nace_sector == "B-D"
        assert result[0].seasonal_adjustment == "SCA"

    def test_ac2_parse_industrial_data_returns_model_type(
        self, client: EurostatClient, mock_industrial_response: dict
    ) -> None:
        """
        AC2: Parsed data returns EurostatIndustrialProduction model.

        Given: A valid Eurostat response
        When: _parse_industrial_data() is called
        Then: All items are EurostatIndustrialProduction instances
        """
        result = client._parse_industrial_data(
            mock_industrial_response, "PT", "B-D", "SCA", None, None
        )

        assert all(isinstance(r, EurostatIndustrialProduction) for r in result)

    def test_ac2_parse_industrial_data_date_parsing(
        self, client: EurostatClient, mock_industrial_response: dict
    ) -> None:
        """
        AC2: Industrial production dates are correctly parsed.

        Given: A response with monthly period strings
        When: _parse_industrial_data() is called
        Then: Dates are correctly converted to date objects
        """
        result = client._parse_industrial_data(
            mock_industrial_response, "PT", "B-D", "SCA", None, None
        )

        assert result[0].date == date(2024, 1, 1)
        assert result[1].date == date(2024, 2, 1)
        assert result[2].date == date(2024, 3, 1)

    def test_ac2_parse_industrial_missing_values_skipped(self, client: EurostatClient) -> None:
        """
        AC2: Handle missing values in industrial response.

        Given: A response with gaps in data
        When: _parse_industrial_data() is called
        Then: Only valid records are returned
        """
        mock_response = {
            "value": {"0": 98.5, "2": 100.1},  # Index 1 missing
            "size": [1, 1, 1, 1, 1, 1, 3],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"B-D": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {"category": {"index": {"2024-01": 0, "2024-02": 1, "2024-03": 2}}},
            },
        }

        result = client._parse_industrial_data(mock_response, "PT", "B-D", "SCA", None, None)

        assert len(result) == 2

    def test_ac2_parse_industrial_date_filter_start(
        self, client: EurostatClient, mock_industrial_response: dict
    ) -> None:
        """
        AC2: Filter industrial data by start_date.

        Given: A response with data from Jan-Mar 2024
        When: _parse_industrial_data() is called with start_date=Feb
        Then: Only Feb and Mar data is returned
        """
        result = client._parse_industrial_data(
            mock_industrial_response,
            "PT",
            "B-D",
            "SCA",
            start_date=date(2024, 2, 1),
            end_date=None,
        )

        assert len(result) == 2
        assert result[0].date == date(2024, 2, 1)

    def test_ac2_parse_industrial_sorted_by_date(self, client: EurostatClient) -> None:
        """
        AC2: Parsed industrial data is sorted by date ascending.

        Given: A response with unsorted time periods
        When: _parse_industrial_data() is called
        Then: Results are sorted by date
        """
        mock_response = {
            "value": {"0": 100.1, "1": 99.2, "2": 98.5},
            "size": [1, 1, 1, 1, 1, 1, 3],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"B-D": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {"category": {"index": {"2024-03": 0, "2024-02": 1, "2024-01": 2}}},
            },
        }

        result = client._parse_industrial_data(mock_response, "PT", "B-D", "SCA", None, None)

        dates = [r.date for r in result]
        assert dates == sorted(dates)

    # =========================================================================
    # AC2: Industrial Production Index API - Fetch Method Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ac2_fetch_industrial_production_builds_correct_url(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: fetch_industrial_production constructs correct API request.

        Given: Request for Portugal industrial production
        When: fetch_industrial_production() is called
        Then: Correct dataset and filters are passed to _fetch_eurostat_data
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "value": {},
                "dimension": {"time": {"category": {"index": {}}}},
            }

            await client.fetch_industrial_production(country="PT")

            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args

            # Verify dataset code
            assert call_args[0][0] == "sts_inpr_m", "Should use industrial dataset"

            # Verify filters
            filters = call_args[0][1]
            assert filters["geo"] == "PT"
            assert filters["nace_r2"] == "B-D"  # Mining, manufacturing, energy
            assert filters["s_adj"] == "SCA"
            assert filters["unit"] == "I21"

    @pytest.mark.asyncio
    async def test_ac2_fetch_industrial_production_returns_data(
        self, client: EurostatClient, mock_industrial_response: dict
    ) -> None:
        """
        AC2: fetch_industrial_production returns parsed data.

        Given: A valid API response
        When: fetch_industrial_production() is called
        Then: Returns list of EurostatIndustrialProduction records
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_industrial_response

            result = await client.fetch_industrial_production(
                country="PT",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
            )

            assert len(result) == 3
            assert all(isinstance(r, EurostatIndustrialProduction) for r in result)

    @pytest.mark.asyncio
    async def test_ac2_fetch_industrial_production_handles_api_error(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: fetch_industrial_production handles API errors.

        Given: API returns an error
        When: fetch_industrial_production() is called
        Then: ExternalDataFetchError is raised
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ExternalDataFetchError(
                source="Eurostat", message="API unavailable"
            )

            with pytest.raises(ExternalDataFetchError):
                await client.fetch_industrial_production(country="PT")


class TestEurostatIndicatorDataModels:
    """Unit tests for Eurostat indicator data models (AC5).

    Given: Model class definitions
    When: Instances are created with valid/invalid data
    Then: Validation rules are enforced correctly
    """

    def test_ac5_construction_output_model_exists(self) -> None:
        """
        AC5: EurostatConstructionOutput model exists.

        Given: The models module is imported
        When: Checking for EurostatConstructionOutput
        Then: The model class is available
        """
        assert EurostatConstructionOutput is not None, (
            "EurostatConstructionOutput model must be implemented"
        )

    def test_ac5_industrial_production_model_exists(self) -> None:
        """
        AC5: EurostatIndustrialProduction model exists.

        Given: The models module is imported
        When: Checking for EurostatIndustrialProduction
        Then: The model class is available
        """
        assert EurostatIndustrialProduction is not None, (
            "EurostatIndustrialProduction model must be implemented"
        )

    def test_ac5_construction_output_model_fields(self) -> None:
        """
        AC5: EurostatConstructionOutput has required fields.

        Given: EurostatConstructionOutput model
        When: Creating an instance with valid data
        Then: All required fields are present and correctly typed
        """
        if EurostatConstructionOutput is None:
            pytest.skip("Model not yet implemented (RED phase)")

        # Create instance with required fields
        record = EurostatConstructionOutput(
            date=date(2024, 1, 1),
            index_value=105.2,
            country="PT",
            nace_sector="F",
            seasonal_adjustment="SCA",
        )

        assert record.date == date(2024, 1, 1)
        assert record.index_value == 105.2
        assert record.country == "PT"
        assert record.nace_sector == "F"
        assert record.seasonal_adjustment == "SCA"

    def test_ac5_industrial_production_model_fields(self) -> None:
        """
        AC5: EurostatIndustrialProduction has required fields.

        Given: EurostatIndustrialProduction model
        When: Creating an instance with valid data
        Then: All required fields are present and correctly typed
        """
        if EurostatIndustrialProduction is None:
            pytest.skip("Model not yet implemented (RED phase)")

        record = EurostatIndustrialProduction(
            date=date(2024, 1, 1),
            index_value=98.5,
            country="PT",
            nace_sector="B-D",
            seasonal_adjustment="SCA",
        )

        assert record.date == date(2024, 1, 1)
        assert record.index_value == 98.5
        assert record.country == "PT"
        assert record.nace_sector == "B-D"
        assert record.seasonal_adjustment == "SCA"

    def test_ac5_construction_output_index_value_positive(self) -> None:
        """
        AC5: Construction output index values must be positive.

        Given: EurostatConstructionOutput model
        When: Creating instance with index_value > 0
        Then: Validation passes
        """
        if EurostatConstructionOutput is None:
            pytest.skip("Model not yet implemented (RED phase)")

        record = EurostatConstructionOutput(
            date=date(2024, 1, 1),
            index_value=105.2,
            country="PT",
            nace_sector="F",
            seasonal_adjustment="SCA",
        )

        assert record.index_value > 0

    def test_ac5_industrial_production_index_value_positive(self) -> None:
        """
        AC5: Industrial production index values must be positive.

        Given: EurostatIndustrialProduction model
        When: Creating instance with index_value > 0
        Then: Validation passes
        """
        if EurostatIndustrialProduction is None:
            pytest.skip("Model not yet implemented (RED phase)")

        record = EurostatIndustrialProduction(
            date=date(2024, 1, 1),
            index_value=98.5,
            country="PT",
            nace_sector="B-D",
            seasonal_adjustment="SCA",
        )

        assert record.index_value > 0


class TestEurostatClientDatasetConstants:
    """Unit tests for Eurostat dataset constants (AC1, AC2).

    Given: EurostatClient class
    When: Accessing dataset constants
    Then: Correct Eurostat dataset codes are defined
    """

    def test_ac1_construction_dataset_constant(self) -> None:
        """
        AC1: CONSTRUCTION_DATASET constant defined.

        Given: EurostatClient class
        When: Accessing CONSTRUCTION_DATASET
        Then: Returns "sts_copr_m"
        """
        assert hasattr(EurostatClient, "CONSTRUCTION_DATASET"), (
            "CONSTRUCTION_DATASET constant must be defined"
        )
        assert EurostatClient.CONSTRUCTION_DATASET == "sts_copr_m"

    def test_ac2_industrial_production_dataset_constant(self) -> None:
        """
        AC2: INDUSTRIAL_PRODUCTION_DATASET constant defined.

        Given: EurostatClient class
        When: Accessing INDUSTRIAL_PRODUCTION_DATASET
        Then: Returns "sts_inpr_m"
        """
        assert hasattr(EurostatClient, "INDUSTRIAL_PRODUCTION_DATASET"), (
            "INDUSTRIAL_PRODUCTION_DATASET constant must be defined"
        )
        assert EurostatClient.INDUSTRIAL_PRODUCTION_DATASET == "sts_inpr_m"
