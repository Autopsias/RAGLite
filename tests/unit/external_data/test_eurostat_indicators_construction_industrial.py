"""Unit tests for Eurostat Construction & Industrial Production Indicators.

Story 6.16: Add Eurostat Construction & Industrial Indicators

This file tests the parsing and fetching logic for construction output and
industrial production data from Eurostat's SDMX API.

Run with: pytest tests/unit/external_data/test_eurostat_indicators_construction_industrial.py -v
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
        """AC1: Parse valid construction output response."""
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
        """AC1: Parsed data returns EurostatConstructionOutput model."""
        result = client._parse_construction_data(
            mock_construction_response, "PT", "F", "SCA", None, None
        )

        assert all(isinstance(r, EurostatConstructionOutput) for r in result)

    def test_ac1_parse_construction_data_date_parsing(
        self, client: EurostatClient, mock_construction_response: dict
    ) -> None:
        """AC1: Construction data dates are correctly parsed."""
        result = client._parse_construction_data(
            mock_construction_response, "PT", "F", "SCA", None, None
        )

        assert result[0].date == date(2024, 1, 1)
        assert result[1].date == date(2024, 2, 1)
        assert result[2].date == date(2024, 3, 1)

    def test_ac1_parse_construction_missing_values_skipped(self, client: EurostatClient) -> None:
        """AC1: Handle missing values in response gracefully."""
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
        """AC1: Filter construction data by start_date."""
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
        """AC1: Filter construction data by end_date."""
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
        """AC1: Parsed construction data is sorted by date ascending."""
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
        """AC1: fetch_construction_output constructs correct API request."""
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
        """AC1: fetch_construction_output returns parsed data."""
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
        """AC1: fetch_construction_output handles API errors."""
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
        """AC2: Parse valid industrial production response."""
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
        """AC2: Parsed data returns EurostatIndustrialProduction model."""
        result = client._parse_industrial_data(
            mock_industrial_response, "PT", "B-D", "SCA", None, None
        )

        assert all(isinstance(r, EurostatIndustrialProduction) for r in result)

    def test_ac2_parse_industrial_data_date_parsing(
        self, client: EurostatClient, mock_industrial_response: dict
    ) -> None:
        """AC2: Industrial production dates are correctly parsed."""
        result = client._parse_industrial_data(
            mock_industrial_response, "PT", "B-D", "SCA", None, None
        )

        assert result[0].date == date(2024, 1, 1)
        assert result[1].date == date(2024, 2, 1)
        assert result[2].date == date(2024, 3, 1)

    def test_ac2_parse_industrial_missing_values_skipped(self, client: EurostatClient) -> None:
        """AC2: Handle missing values in industrial response."""
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
        """AC2: Filter industrial data by start_date."""
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
        """AC2: Parsed industrial data is sorted by date ascending."""
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
        """AC2: fetch_industrial_production constructs correct API request."""
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
        """AC2: fetch_industrial_production returns parsed data."""
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
        """AC2: fetch_industrial_production handles API errors."""
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ExternalDataFetchError(
                source="Eurostat", message="API unavailable"
            )

            with pytest.raises(ExternalDataFetchError):
                await client.fetch_industrial_production(country="PT")
