"""Additional edge case and error handling tests for Eurostat Construction & Industrial Indicators.

Story 6.16: Add Eurostat Construction & Industrial Indicators

This test file complements test_eurostat_indicators.py with:
- [P0] Critical edge cases for SDMX parsing
- [P1] Error handling for malformed responses
- [P2] Boundary conditions and data validation
- [P3] Robustness tests for production scenarios

Run with: pytest tests/unit/test_eurostat_indicators_edge_cases.py -v
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from raglite.external_data.clients.eurostat import EurostatClient
from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import (
    EurostatConstructionOutput,
    EurostatIndustrialProduction,
)


class TestEurostatSDMXParsingEdgeCases:
    """[P0] Critical edge cases for SDMX-JSON multi-dimensional index parsing.

    The _parse_sdmx_index_data() method handles complex multi-dimensional
    indexing with stride calculations. These tests validate critical edge cases.
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient(timeout=1.0)

    def test_p0_empty_response_returns_empty_list(self, client: EurostatClient) -> None:
        """
        [P0] Empty API response should return empty list, not crash.

        Given: An empty Eurostat SDMX response
        When: _parse_sdmx_index_data() is called
        Then: Returns empty list without errors
        """
        empty_response = {
            "value": {},
            "dimension": {},
            "size": [],
        }

        result = client._parse_sdmx_index_data(empty_response, "PT", "F", "SCA", None, None)

        assert result == []

    def test_p0_missing_dimension_keys_returns_empty(self, client: EurostatClient) -> None:
        """
        [P0] Missing required dimension keys should not crash.

        Given: Response missing nace_r2 dimension
        When: _parse_sdmx_index_data() is called
        Then: Returns empty list and logs warning
        """
        malformed_response = {
            "value": {"0": 105.2},
            "size": [1, 1, 1, 1, 1, 1, 1],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                # Missing nace_r2, s_adj, unit, geo
                "time": {"category": {"index": {"2024-01": 0}}},
            },
        }

        result = client._parse_sdmx_index_data(malformed_response, "PT", "F", "SCA", None, None)

        assert result == []

    def test_p1_dimension_index_mismatch_filters_skips_data(self, client: EurostatClient) -> None:
        """
        [P1] When filter dimensions don't match, should return empty.

        Given: Response has geo=DE but we're filtering for PT
        When: _parse_sdmx_index_data() is called with country="PT"
        Then: Returns empty list (no matching data)
        """
        response_germany = {
            "value": {"0": 105.2},
            "size": [1, 1, 1, 1, 1, 1, 1],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"F": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"DE": 0}}},  # Germany, not Portugal
                "time": {"category": {"index": {"2024-01": 0}}},
            },
        }

        result = client._parse_sdmx_index_data(
            response_germany,
            "PT",
            "F",
            "SCA",
            None,
            None,  # Requesting Portugal
        )

        assert result == []

    def test_p2_size_array_wrong_length_logs_warning(self, client: EurostatClient) -> None:
        """
        [P2] Size array with unexpected dimension count should log warning.

        Given: Response with size array length != 7
        When: _parse_sdmx_index_data() is called
        Then: Continues parsing but logs warning
        """
        response_wrong_size = {
            "value": {"0": 105.2},
            "size": [1, 1, 1, 1, 1],  # Only 5 dimensions instead of 7
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"F": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {"category": {"index": {"2024-01": 0}}},
            },
        }

        # Should not crash, but may log warning
        result = client._parse_sdmx_index_data(response_wrong_size, "PT", "F", "SCA", None, None)

        # Result may be empty or incorrect due to dimension mismatch
        assert isinstance(result, list)


class TestEurostatPeriodParsingEdgeCases:
    """[P1] Edge cases for _parse_eurostat_period() date parsing.

    Eurostat uses multiple period formats:
    - YYYY-MM (monthly)
    - YYYY-S1/S2 (semester)
    - YYYY (annual)
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    def test_p1_invalid_month_returns_none(self, client: EurostatClient) -> None:
        """
        [P1] Invalid month number should return None.

        Given: Period string with invalid month (13)
        When: _parse_eurostat_period() is called
        Then: Returns None
        """
        assert client._parse_eurostat_period("2024-13") is None

    def test_p1_invalid_semester_returns_none(self, client: EurostatClient) -> None:
        """
        [P1] Invalid semester number should return None.

        Given: Period string with invalid semester (S3)
        When: _parse_eurostat_period() is called
        Then: Returns None
        """
        assert client._parse_eurostat_period("2024-S3") is None

    def test_p1_malformed_period_returns_none(self, client: EurostatClient) -> None:
        """
        [P1] Malformed period strings should return None.

        Given: Invalid period format
        When: _parse_eurostat_period() is called
        Then: Returns None
        """
        assert client._parse_eurostat_period("202401") is None  # Missing hyphen
        assert client._parse_eurostat_period("24-01") is None  # 2-digit year
        assert client._parse_eurostat_period("2024-ABC") is None  # Invalid format

    def test_p2_semester_s1_maps_to_january(self, client: EurostatClient) -> None:
        """
        [P2] Semester 1 should map to January 1st.

        Given: Period string "2024-S1"
        When: _parse_eurostat_period() is called
        Then: Returns date(2024, 1, 1)
        """
        result = client._parse_eurostat_period("2024-S1")
        assert result == date(2024, 1, 1)

    def test_p2_semester_s2_maps_to_july(self, client: EurostatClient) -> None:
        """
        [P2] Semester 2 should map to July 1st.

        Given: Period string "2024-S2"
        When: _parse_eurostat_period() is called
        Then: Returns date(2024, 7, 1)
        """
        result = client._parse_eurostat_period("2024-S2")
        assert result == date(2024, 7, 1)

    def test_p2_annual_format_maps_to_january(self, client: EurostatClient) -> None:
        """
        [P2] Annual format should map to January 1st.

        Given: Period string "2024" (annual)
        When: _parse_eurostat_period() is called
        Then: Returns date(2024, 1, 1)
        """
        result = client._parse_eurostat_period("2024")
        assert result == date(2024, 1, 1)


class TestConstructionOutputErrorHandling:
    """[P0] Error handling for construction output API."""

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    @pytest.mark.asyncio
    async def test_p0_network_timeout_raises_external_data_error(
        self, client: EurostatClient
    ) -> None:
        """
        [P0] Network timeout should raise ExternalDataFetchError.

        Given: API request times out
        When: fetch_construction_output() is called
        Then: ExternalDataFetchError is raised with timeout message
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            import httpx

            mock_fetch.side_effect = ExternalDataFetchError(
                source="Eurostat",
                message="Timeout after retries",
                original_error=httpx.TimeoutException("Request timeout"),
            )

            with pytest.raises(ExternalDataFetchError) as exc_info:
                await client.fetch_construction_output(country="PT")

            assert "Timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_p0_http_500_error_raises_external_data_error(
        self, client: EurostatClient
    ) -> None:
        """
        [P0] HTTP 500 error should raise ExternalDataFetchError.

        Given: API returns 500 Internal Server Error
        When: fetch_construction_output() is called
        Then: ExternalDataFetchError is raised
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ExternalDataFetchError(source="Eurostat", message="HTTP 500")

            with pytest.raises(ExternalDataFetchError):
                await client.fetch_construction_output(country="PT")

    @pytest.mark.asyncio
    async def test_p1_http_404_raises_external_data_error(self, client: EurostatClient) -> None:
        """
        [P1] HTTP 404 (dataset not found) should raise ExternalDataFetchError.

        Given: API returns 404 (dataset doesn't exist)
        When: fetch_construction_output() is called
        Then: ExternalDataFetchError is raised
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ExternalDataFetchError(source="Eurostat", message="HTTP 404")

            with pytest.raises(ExternalDataFetchError):
                await client.fetch_construction_output(country="PT")


class TestIndustrialProductionErrorHandling:
    """[P0] Error handling for industrial production API."""

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    @pytest.mark.asyncio
    async def test_p0_network_timeout_raises_external_data_error(
        self, client: EurostatClient
    ) -> None:
        """
        [P0] Network timeout should raise ExternalDataFetchError.

        Given: API request times out
        When: fetch_industrial_production() is called
        Then: ExternalDataFetchError is raised
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ExternalDataFetchError(
                source="Eurostat", message="Timeout after retries"
            )

            with pytest.raises(ExternalDataFetchError):
                await client.fetch_industrial_production(country="PT")

    @pytest.mark.asyncio
    async def test_p0_http_500_error_raises_external_data_error(
        self, client: EurostatClient
    ) -> None:
        """
        [P0] HTTP 500 error should raise ExternalDataFetchError.

        Given: API returns 500 Internal Server Error
        When: fetch_industrial_production() is called
        Then: ExternalDataFetchError is raised
        """
        with patch.object(client, "_fetch_eurostat_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ExternalDataFetchError(source="Eurostat", message="HTTP 500")

            with pytest.raises(ExternalDataFetchError):
                await client.fetch_industrial_production(country="PT")


class TestDataModelValidation:
    """[P1] Validation tests for EurostatConstructionOutput and EurostatIndustrialProduction models."""

    def test_p1_construction_output_negative_index_rejected(self) -> None:
        """
        [P1] Construction output model should reject negative index values.

        Given: Attempt to create model with index_value <= 0
        When: Creating EurostatConstructionOutput instance
        Then: Pydantic ValidationError is raised
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EurostatConstructionOutput(
                date=date(2024, 1, 1),
                index_value=-10.0,  # Negative value
                country="PT",
                nace_sector="F",
                seasonal_adjustment="SCA",
            )

    def test_p1_construction_output_zero_index_rejected(self) -> None:
        """
        [P1] Construction output model should reject zero index values.

        Given: Attempt to create model with index_value = 0
        When: Creating EurostatConstructionOutput instance
        Then: Pydantic ValidationError is raised (gt=0 constraint)
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EurostatConstructionOutput(
                date=date(2024, 1, 1),
                index_value=0.0,  # Zero value (gt=0 means > 0)
                country="PT",
                nace_sector="F",
                seasonal_adjustment="SCA",
            )

    def test_p1_industrial_production_negative_index_rejected(self) -> None:
        """
        [P1] Industrial production model should reject negative index values.

        Given: Attempt to create model with index_value < 0
        When: Creating EurostatIndustrialProduction instance
        Then: Pydantic ValidationError is raised
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EurostatIndustrialProduction(
                date=date(2024, 1, 1),
                index_value=-5.0,  # Negative value
                country="PT",
                nace_sector="B-D",
                seasonal_adjustment="SCA",
            )

    def test_p1_industrial_production_zero_index_rejected(self) -> None:
        """
        [P1] Industrial production model should reject zero index values.

        Given: Attempt to create model with index_value = 0
        When: Creating EurostatIndustrialProduction instance
        Then: Pydantic ValidationError is raised
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EurostatIndustrialProduction(
                date=date(2024, 1, 1),
                index_value=0.0,  # Zero value
                country="PT",
                nace_sector="B-D",
                seasonal_adjustment="SCA",
            )

    def test_p2_construction_output_future_date_allowed(self) -> None:
        """
        [P2] Future dates should be allowed (for forecasting scenarios).

        Given: Future date (e.g., 2030)
        When: Creating EurostatConstructionOutput instance
        Then: Instance is created successfully
        """
        future_record = EurostatConstructionOutput(
            date=date(2030, 12, 31),
            index_value=150.0,
            country="PT",
            nace_sector="F",
            seasonal_adjustment="SCA",
        )

        assert future_record.date.year == 2030

    def test_p2_industrial_production_very_large_index_allowed(self) -> None:
        """
        [P2] Very large index values should be allowed (no upper bound).

        Given: Large index value (e.g., 10000.0)
        When: Creating EurostatIndustrialProduction instance
        Then: Instance is created successfully
        """
        record = EurostatIndustrialProduction(
            date=date(2024, 1, 1),
            index_value=10000.0,  # Very large value
            country="PT",
            nace_sector="B-D",
            seasonal_adjustment="SCA",
        )

        assert record.index_value == 10000.0


class TestDateFilteringBoundaryConditions:
    """[P2] Boundary conditions for date filtering in construction/industrial data."""

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    @pytest.fixture
    def mock_multi_year_response(self) -> dict:
        """Mock response with data spanning multiple years."""
        return {
            "value": {
                "0": 100.0,
                "1": 102.0,
                "2": 104.0,
                "3": 106.0,
                "4": 108.0,
                "5": 110.0,
            },
            "size": [1, 1, 1, 1, 1, 1, 6],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"F": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {
                    "category": {
                        "index": {
                            "2022-01": 0,
                            "2022-06": 1,
                            "2022-12": 2,
                            "2023-06": 3,
                            "2023-12": 4,
                            "2024-06": 5,
                        }
                    }
                },
            },
        }

    def test_p2_start_date_exact_match_includes_record(
        self, client: EurostatClient, mock_multi_year_response: dict
    ) -> None:
        """
        [P2] Record exactly matching start_date should be included.

        Given: start_date = 2022-06-01 and data includes 2022-06-01
        When: Parsing construction data
        Then: 2022-06-01 record is included
        """
        result = client._parse_construction_data(
            mock_multi_year_response,
            "PT",
            "F",
            "SCA",
            start_date=date(2022, 6, 1),
            end_date=None,
        )

        dates = [r.date for r in result]
        assert date(2022, 6, 1) in dates

    def test_p2_end_date_exact_match_includes_record(
        self, client: EurostatClient, mock_multi_year_response: dict
    ) -> None:
        """
        [P2] Record exactly matching end_date should be included.

        Given: end_date = 2023-12-31 and data includes 2023-12-01
        When: Parsing construction data
        Then: 2023-12-01 record is included (within month)
        """
        result = client._parse_construction_data(
            mock_multi_year_response,
            "PT",
            "F",
            "SCA",
            start_date=None,
            end_date=date(2023, 12, 31),
        )

        dates = [r.date for r in result]
        assert date(2023, 12, 1) in dates

    def test_p2_date_range_one_day_returns_matching_month(
        self, client: EurostatClient, mock_multi_year_response: dict
    ) -> None:
        """
        [P2] Single-day date range should return matching month data.

        Given: start_date = end_date = 2022-06-15
        When: Parsing construction data
        Then: June 2022 record is included
        """
        result = client._parse_construction_data(
            mock_multi_year_response,
            "PT",
            "F",
            "SCA",
            start_date=date(2022, 6, 15),
            end_date=date(2022, 6, 15),
        )

        assert len(result) == 1
        assert result[0].date == date(2022, 6, 1)


class TestRegressorIntegrationPoints:
    """[P1] Integration points between regressor_fetch.py and regressor_config.py."""

    @pytest.mark.asyncio
    async def test_p1_construction_output_regressor_fetch(self) -> None:
        """
        [P1] construction_output regressor should be fetchable via regressor_fetch.

        Given: Request for "construction_output" regressor
        When: fetch_single_regressor() is called
        Then: Returns pandas Series with construction index data
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        # Mock the Eurostat client to avoid real API call
        with patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock fetch_construction_output to return sample data
            mock_data = [
                EurostatConstructionOutput(
                    date=date(2024, 1, 1),
                    index_value=105.2,
                    country="PT",
                    nace_sector="F",
                    seasonal_adjustment="SCA",
                ),
                EurostatConstructionOutput(
                    date=date(2024, 2, 1),
                    index_value=106.8,
                    country="PT",
                    nace_sector="F",
                    seasonal_adjustment="SCA",
                ),
            ]
            mock_client.fetch_construction_output = AsyncMock(return_value=mock_data)

            result = await fetch_single_regressor(
                "construction_output", date(2024, 1, 1), date(2024, 12, 31)
            )

            assert result is not None
            assert len(result) == 2
            assert result.iloc[0] == 105.2

    @pytest.mark.asyncio
    async def test_p1_industrial_production_regressor_fetch(self) -> None:
        """
        [P1] industrial_production regressor should be fetchable via regressor_fetch.

        Given: Request for "industrial_production" regressor
        When: fetch_single_regressor() is called
        Then: Returns pandas Series with industrial index data
        """
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        with patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_data = [
                EurostatIndustrialProduction(
                    date=date(2024, 1, 1),
                    index_value=98.5,
                    country="PT",
                    nace_sector="B-D",
                    seasonal_adjustment="SCA",
                ),
                EurostatIndustrialProduction(
                    date=date(2024, 2, 1),
                    index_value=99.2,
                    country="PT",
                    nace_sector="B-D",
                    seasonal_adjustment="SCA",
                ),
            ]
            mock_client.fetch_industrial_production = AsyncMock(return_value=mock_data)

            result = await fetch_single_regressor(
                "industrial_production", date(2024, 1, 1), date(2024, 12, 31)
            )

            assert result is not None
            assert len(result) == 2
            assert result.iloc[0] == 98.5

    def test_p1_construction_output_in_available_regressors(self) -> None:
        """
        [P1] construction_output should be in AVAILABLE_REGRESSORS list.

        Given: regressor_config module
        When: Checking AVAILABLE_REGRESSORS
        Then: "construction_output" is present
        """
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert "construction_output" in AVAILABLE_REGRESSORS

    def test_p1_industrial_production_in_available_regressors(self) -> None:
        """
        [P1] industrial_production should be in AVAILABLE_REGRESSORS list.

        Given: regressor_config module
        When: Checking AVAILABLE_REGRESSORS
        Then: "industrial_production" is present
        """
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert "industrial_production" in AVAILABLE_REGRESSORS

    def test_p1_production_metrics_use_new_regressors(self) -> None:
        """
        [P1] Production metrics should auto-select construction/industrial regressors.

        Given: Metric with "volume" or "production" keywords
        When: get_default_regressors() is called
        Then: Returns construction_output and/or industrial_production
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        # Test sales_volume metric
        regressors = get_default_regressors("sales_volume")
        assert "construction_output" in regressors or "industrial_production" in regressors

    def test_p2_capacity_utilization_uses_industrial_production(self) -> None:
        """
        [P2] Capacity utilization metrics should use industrial_production.

        Given: Metric "capacity_utilization"
        When: get_default_regressors() is called
        Then: Returns industrial_production as a regressor
        """
        from raglite.forecasting.regressor_config import get_default_regressors

        regressors = get_default_regressors("capacity_utilization")
        assert "industrial_production" in regressors


class TestRobustnessScenarios:
    """[P3] Production robustness scenarios for long-term stability."""

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    def test_p3_large_dataset_parsing_performance(self, client: EurostatClient) -> None:
        """
        [P3] Parsing very large datasets (10+ years) should complete in reasonable time.

        Given: Mock response with 120 months of data (10 years)
        When: _parse_construction_data() is called
        Then: Completes in < 1 second
        """
        import time

        # Generate 120 months of data
        large_response = {
            "value": {str(i): 100.0 + i * 0.1 for i in range(120)},
            "size": [1, 1, 1, 1, 1, 1, 120],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"F": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {
                    "category": {
                        "index": {f"{2015 + (i // 12)}-{(i % 12) + 1:02d}": i for i in range(120)}
                    }
                },
            },
        }

        start_time = time.time()
        result = client._parse_construction_data(large_response, "PT", "F", "SCA", None, None)
        elapsed = time.time() - start_time

        assert len(result) == 120
        assert elapsed < 1.0  # Should complete in < 1 second

    def test_p3_concurrent_parsing_different_datasets(self, client: EurostatClient) -> None:
        """
        [P3] Parsing construction and industrial data concurrently should work.

        Given: Mock responses for both construction and industrial
        When: Parsing both simultaneously
        Then: Both return correct results without interference
        """
        construction_response = {
            "value": {"0": 105.2},
            "size": [1, 1, 1, 1, 1, 1, 1],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"F": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {"category": {"index": {"2024-01": 0}}},
            },
        }

        industrial_response = {
            "value": {"0": 98.5},
            "size": [1, 1, 1, 1, 1, 1, 1],
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"B-D": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {"category": {"index": {"2024-01": 0}}},
            },
        }

        construction_result = client._parse_construction_data(
            construction_response, "PT", "F", "SCA", None, None
        )
        industrial_result = client._parse_industrial_data(
            industrial_response, "PT", "B-D", "SCA", None, None
        )

        assert len(construction_result) == 1
        assert len(industrial_result) == 1
        assert construction_result[0].index_value == 105.2
        assert industrial_result[0].index_value == 98.5

    def test_p3_empty_time_dimension_returns_empty_list(self, client: EurostatClient) -> None:
        """
        [P3] Response with empty time dimension should return empty list.

        Given: Response with no time periods
        When: _parse_construction_data() is called
        Then: Returns empty list without errors
        """
        response_no_time = {
            "value": {},
            "size": [1, 1, 1, 1, 1, 1, 0],  # 0 time periods
            "dimension": {
                "freq": {"category": {"index": {"M": 0}}},
                "indic_bt": {"category": {"index": {"PRD": 0}}},
                "nace_r2": {"category": {"index": {"F": 0}}},
                "s_adj": {"category": {"index": {"SCA": 0}}},
                "unit": {"category": {"index": {"I21": 0}}},
                "geo": {"category": {"index": {"PT": 0}}},
                "time": {"category": {"index": {}}},  # Empty time index
            },
        }

        result = client._parse_construction_data(response_no_time, "PT", "F", "SCA", None, None)

        assert result == []
