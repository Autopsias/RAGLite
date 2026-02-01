"""Error handling, data validation, and robustness tests for Eurostat indicators.

Story 6.16: Add Eurostat Construction & Industrial Indicators

This test file covers error scenarios and robustness:
- [P0] Network error handling (timeouts, HTTP errors)
- [P1] Data model validation (negative values, constraints)
- [P3] Production robustness scenarios (large datasets, concurrency)

Run with: pytest tests/unit/external_data/test_eurostat_error_handling.py -v
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
    async def test_p0_industrial_network_timeout_raises_external_data_error(
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
    async def test_p0_industrial_http_500_error_raises_external_data_error(
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
