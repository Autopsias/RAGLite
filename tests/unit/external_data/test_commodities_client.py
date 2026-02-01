"""Unit tests for Commodities (CO2, Oil, Gas, Coal) client.

Story 7.1: Split test_external_data_clients.py
This module contains tests for: TestCommoditiesURLFix, TestCommoditiesClient, TestCommoditiesClientAdditional, TestCommoditiesClientCoverage
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.clients.commodities import CommoditiesClient
from raglite.external_data.exceptions import (
    ExternalDataFetchError,
)


class TestCommoditiesURLFix:
    """Tests for Commodities Ember API URL fix (Story 6.9.1 AC4-AC6).

    Problem: Ember Climate rebranded to Ember Energy and deprecated the old
    domain api.ember-climate.org on 2025-01-01.
    Fix: Update URL to api.ember-energy.org.
    """

    def test_co2_url_uses_new_domain(self) -> None:
        """AC4: Verify URL uses api.ember-energy.org."""
        # Read the commodities module source to verify URL
        import inspect

        from raglite.external_data import clients

        source = inspect.getsource(clients.commodities)

        # New domain should be present
        assert "api.ember-energy.org" in source
        # Comment about deprecated domain should be present
        assert "ember-climate.org" in source or "deprecated" in source.lower()

    def test_old_domain_not_used_in_fetch(self) -> None:
        """AC4: Verify api.ember-climate.org is not used in fetch_co2_prices."""
        import inspect

        from raglite.external_data.clients.commodities import CommoditiesClient

        # Get the source of fetch_co2_prices method
        source = inspect.getsource(CommoditiesClient.fetch_co2_prices)

        # Old domain should NOT be in the actual fetch URL
        assert "api.ember-climate.org/v1/carbon-price-tracker" not in source
        # New domain should be present
        assert "api.ember-energy.org" in source

    def test_co2_data_sources_updated(self) -> None:
        """AC4: Verify CO2_DATA_SOURCES constant updated."""
        from raglite.external_data.clients.commodities import CO2_DATA_SOURCES

        # Ember URL should use new domain
        assert "ember-energy.org" in CO2_DATA_SOURCES.get("ember", "")


class TestCommoditiesClient:
    """Tests for commodities price client."""

    @pytest.fixture
    def client(self, tmp_path) -> CommoditiesClient:
        """Create commodities client with temp cache directory."""
        return CommoditiesClient(cache_dir=tmp_path / "cache")

    @pytest.mark.asyncio
    async def test_fetch_co2_prices_success(self, client: CommoditiesClient) -> None:
        """Test successful CO2 EUA prices fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"date": "2024-01-15", "price": 85.50},
                {"date": "2024-01-16", "price": 86.00},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_co2_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

            assert len(result) == 2
            assert result[0].price == 85.50
            assert result[0].currency == "EUR"

    def test_save_and_load_cache(self, client: CommoditiesClient) -> None:
        """Test cache save and load operations."""
        from raglite.external_data.models import CoalPrice

        prices = [
            CoalPrice(date=date(2024, 1, 1), price=120.0, currency="EUR"),
            CoalPrice(date=date(2024, 1, 8), price=122.0, currency="EUR"),
        ]

        client.save_to_cache("coal", prices)
        loaded = client.load_from_cache("coal")

        assert len(loaded) == 2
        assert loaded[0].price == 120.0

    def test_load_cache_with_date_filter(self, client: CommoditiesClient) -> None:
        """Test cache loading with date filtering."""
        from raglite.external_data.models import CoalPrice

        prices = [
            CoalPrice(date=date(2024, 1, 1), price=120.0, currency="EUR"),
            CoalPrice(date=date(2024, 2, 1), price=122.0, currency="EUR"),
            CoalPrice(date=date(2024, 3, 1), price=124.0, currency="EUR"),
        ]

        client.save_to_cache("coal", prices)
        loaded = client.load_from_cache(
            "coal",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 2, 15),
        )

        assert len(loaded) == 1
        assert loaded[0].date == date(2024, 2, 1)

    def test_import_from_csv(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import."""
        csv_file = tmp_path / "coal_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit,grade
2024-01-01,120.0,EUR,EUR/tonne,thermal
2024-01-08,122.0,EUR,EUR/tonne,thermal"""
        )

        result = client.import_from_csv("coal", csv_file)

        assert len(result) == 2
        assert result[0].price == 120.0
        assert result[0].grade == "thermal"

    def test_load_cache_empty(self, client: CommoditiesClient) -> None:
        """Test loading from non-existent cache returns empty list."""
        result = client.load_from_cache("nonexistent")
        assert result == []


# =============================================================================
# Exception Tests
# =============================================================================


# =============================================================================
# Additional Coverage Tests
# =============================================================================


class TestCommoditiesClientAdditional:
    """Additional tests for commodities client coverage."""

    @pytest.fixture
    def client(self, tmp_path) -> CommoditiesClient:
        return CommoditiesClient(cache_dir=tmp_path / "cache")

    @pytest.mark.asyncio
    async def test_fetch_coal_falls_back_to_cache(self, client: CommoditiesClient) -> None:
        """Test coal prices fallback to cache (no API)."""
        result = await client.fetch_coal_prices(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )
        # No cache exists, returns empty
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_petcoke_falls_back_to_cache(self, client: CommoditiesClient) -> None:
        """Test petcoke prices fallback to cache (no API)."""
        result = await client.fetch_petcoke_prices(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_co2_api_failure_fallback(self, client: CommoditiesClient) -> None:
        """Test CO2 prices fallback on API failure."""
        import pandas as pd

        # Mock yfinance module at sys.modules level for dynamic imports
        mock_yfinance = MagicMock()
        mock_yfinance.download = MagicMock(return_value=pd.DataFrame())

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("timeout")
            )

            # Story 6.10: Mock yfinance at module level to handle dynamic import
            with patch.dict("sys.modules", {"yfinance": mock_yfinance}):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await client.fetch_co2_prices(
                        start_date=date(2024, 1, 1),
                        end_date=date(2024, 3, 31),
                    )

        # Falls back to empty cache (tmp_path cache is empty)
        assert result == []

    def test_import_csv_file_not_found(self, client: CommoditiesClient) -> None:
        """Test CSV import with non-existent file."""
        with pytest.raises(ExternalDataFetchError):
            client.import_from_csv("coal", "/nonexistent/path.csv")


class TestCommoditiesClientCoverage:
    """Additional tests for commodities client coverage."""

    @pytest.fixture
    def client(self, tmp_path) -> CommoditiesClient:
        return CommoditiesClient(cache_dir=tmp_path / "cache")

    @pytest.mark.asyncio
    async def test_fetch_co2_prices_timeout_exhausted(self, client: CommoditiesClient) -> None:
        """Test CO2 fetch with all retries exhausted falls back to empty cache."""
        import pandas as pd

        # Mock yfinance module at sys.modules level for dynamic imports
        mock_yfinance = MagicMock()
        mock_yfinance.download = MagicMock(return_value=pd.DataFrame())

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("timeout")
            )

            # Story 6.10: Mock yfinance at module level to handle dynamic import
            with patch.dict("sys.modules", {"yfinance": mock_yfinance}):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    # Should fall back to empty cache (tmp_path cache is empty)
                    result = await client.fetch_co2_prices(
                        start_date=date(2024, 1, 1),
                        end_date=date(2024, 1, 31),
                    )

        assert result == []

    def test_save_to_cache_merge_existing(self, client: CommoditiesClient) -> None:
        """Test merging new prices with existing cache."""
        from raglite.external_data.models import CoalPrice

        # Save initial prices
        initial_prices = [
            CoalPrice(date=date(2024, 1, 1), price=120.0),
            CoalPrice(date=date(2024, 1, 8), price=122.0),
        ]
        client.save_to_cache("coal", initial_prices)

        # Save new prices (including one that overwrites)
        new_prices = [
            CoalPrice(date=date(2024, 1, 8), price=125.0),  # Overwrite
            CoalPrice(date=date(2024, 1, 15), price=128.0),  # New
        ]
        client.save_to_cache("coal", new_prices)

        # Load and verify
        loaded = client.load_from_cache("coal")
        assert len(loaded) == 3
        # Find the Jan 8 price - should be updated
        jan8_price = next(p for p in loaded if p.date == date(2024, 1, 8))
        assert jan8_price.price == 125.0

    def test_load_cache_corrupted_file(self, client: CommoditiesClient) -> None:
        """Test loading from corrupted cache file."""
        cache_file = client.cache_dir / "corrupted_prices.json"
        cache_file.write_text("not valid json {{{")

        result = client.load_from_cache("corrupted")
        assert result == []

    def test_load_cache_invalid_record(self, client: CommoditiesClient) -> None:
        """Test loading cache with invalid records."""
        import json

        cache_file = client.cache_dir / "coal_prices.json"
        cache_file.write_text(
            json.dumps(
                [
                    {"date": "2024-01-01", "price": 120.0},  # Valid
                    {"date": "invalid", "price": 130.0},  # Invalid date
                    {"date": "2024-01-15"},  # Missing price
                ]
            )
        )

        result = client.load_from_cache("coal")
        # Only the valid record should be loaded
        assert len(result) == 1

    def test_import_csv_petcoke(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import for petcoke commodity."""
        csv_file = tmp_path / "petcoke_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit,sulfur_content_pct
2024-01-01,180.0,EUR,EUR/tonne,3.5
2024-01-08,185.0,EUR,EUR/tonne,3.2"""
        )

        result = client.import_from_csv("petcoke", csv_file)

        assert len(result) == 2
        assert result[0].price == 180.0
        assert result[0].sulfur_content_pct == 3.5

    def test_import_csv_co2(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import for CO2 EUA commodity."""
        csv_file = tmp_path / "co2_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit
2024-01-01,85.0,EUR,EUR/tonne
2024-01-08,88.0,EUR,EUR/tonne"""
        )

        result = client.import_from_csv("co2_eua", csv_file)

        assert len(result) == 2
        assert result[0].price == 85.0

    def test_import_csv_generic_commodity(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import for generic commodity type."""
        csv_file = tmp_path / "other_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit
2024-01-01,50.0,EUR,EUR/unit"""
        )

        result = client.import_from_csv("other", csv_file)

        assert len(result) == 1
        assert result[0].price == 50.0

    def test_import_csv_invalid_row(self, client: CommoditiesClient, tmp_path) -> None:
        """Test CSV import with invalid rows."""
        csv_file = tmp_path / "coal_prices.csv"
        csv_file.write_text(
            """date,price,currency,unit
2024-01-01,120.0,EUR,EUR/tonne
invalid-date,130.0,EUR,EUR/tonne
2024-01-15,not-a-number,EUR,EUR/tonne"""
        )

        result = client.import_from_csv("coal", csv_file)

        # Only the valid row should be imported
        assert len(result) == 1
        assert result[0].price == 120.0


# =============================================================================
# Story 6.8: Tier 2 Data Sources Tests
# =============================================================================
