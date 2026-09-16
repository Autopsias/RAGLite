"""Unit tests for Story 6.10: Forecasting Data Quality & External Data Reliability.

Tests cover:
- Sub-Story 6.10.1: Query-Time Entity Normalization
- Sub-Story 6.10.2: External API Reliability Fixes
- Sub-Story 6.10.3: Local File Caching
"""

import json
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from raglite.forecasting.timeseries import prefer_group_level
from raglite.ingestion.entity_normalizer import (
    get_entity_ilike_pattern,
    normalize_entity,
)
from raglite.shared.caching import ExternalDataCache


class TestQueryTimeEntityNormalization:
    """Tests for Sub-Story 6.10.1: Query-Time Entity Normalization."""

    def test_normalize_entity_exact_match(self) -> None:
        """AC1: Exact match entity normalization."""
        assert normalize_entity("GROUP") == "Group"
        assert normalize_entity("PT") == "Portugal"
        assert normalize_entity("BR") == "Brazil"

    def test_normalize_entity_case_insensitive(self) -> None:
        """AC2: Case-insensitive entity normalization."""
        assert normalize_entity("group") == "Group"
        assert normalize_entity("GROUP") == "Group"
        assert normalize_entity("Group") == "Group"

    def test_normalize_entity_returns_none_for_empty(self) -> None:
        """AC1: None/empty input returns None."""
        assert normalize_entity(None) is None
        assert normalize_entity("") is None
        assert normalize_entity("   ") is None

    def test_normalize_entity_fuzzy_patterns(self) -> None:
        """AC3: Fuzzy pattern matching for entity variations."""
        assert normalize_entity("Portugal Cement Ltd") == "Portugal"
        assert normalize_entity("Brazil Operations") == "Brazil"
        assert normalize_entity("Consolidated Total") == "Group"

    def test_get_entity_ilike_pattern_group(self) -> None:
        """AC4: ILIKE pattern generation for Group entity."""
        pattern = get_entity_ilike_pattern("Group")
        assert "ILIKE ANY" in pattern
        assert "Group" in pattern
        # Should include aliases
        assert "Conso" in pattern or "GROUP" in pattern or "Total" in pattern

    def test_get_entity_ilike_pattern_portugal(self) -> None:
        """AC4: ILIKE pattern generation for Portugal entity."""
        pattern = get_entity_ilike_pattern("Portugal")
        assert "ILIKE ANY" in pattern
        assert "Portugal" in pattern
        # Should include aliases
        assert "PT" in pattern

    def test_prefer_group_level_aggregate_metrics(self) -> None:
        """AC5: GROUP-level preference for aggregate metrics.

        Story 6.10.4 Update: Only EBITDA has actual GROUP-level data in database.
        Revenue/turnover, sales volume, capacity utilization don't have GROUP entity
        (they use "Currency (1000 EUR)" instead), so GROUP filter was removed.

        Fix 2026-01-29: EBITDA removed from GROUP_PREFERRED_METRICS because
        database has NO entity="GROUP" data for EBITDA - only entity="Portugal".
        All metrics now return None when entity is None (no entity filter).
        """
        # Fix 2026-01-29: EBITDA no longer uses GROUP filter (GROUP_PREFERRED_METRICS is empty)
        assert prefer_group_level(None, "ebitda") is None  # No GROUP data in DB
        # Story 6.10.4: These metrics DON'T have GROUP-level data - return None
        assert prefer_group_level(None, "revenue") is None  # No GROUP rows
        assert prefer_group_level(None, "sales volume") is None  # No GROUP rows
        assert prefer_group_level(None, "capacity utilization") is None  # No GROUP rows

    def test_prefer_group_level_specific_entity(self) -> None:
        """AC5: Specific entity is preserved when explicitly requested."""
        assert prefer_group_level("Portugal", "ebitda") == "Portugal"
        assert prefer_group_level("Brazil", "revenue") == "Brazil"
        assert prefer_group_level("Group", "ebitda") == "Group"

    def test_prefer_group_level_unknown_metric(self) -> None:
        """Story 6.10.4 Update: Non-aggregate metrics return None (no filter).

        Previously defaulted to Group, but this caused 0 results for metrics
        that don't have GROUP-level data in the database.
        """
        # For unknown metrics with no entity, return None (no entity filter)
        assert prefer_group_level(None, "unknown_metric") is None


class TestExternalAPIReliabilityFixes:
    """Tests for Sub-Story 6.10.2: External API Reliability Fixes."""

    def test_ine_client_timeout_increased_for_tests(self) -> None:
        """AC1: INE client timeout increased from 1s to 60s for tests."""
        # Set test environment
        os.environ["PYTEST_CURRENT_TEST"] = "test_something"

        try:
            from raglite.external_data.clients.ine import INEClient

            client = INEClient()
            assert client.timeout == 60.0
        finally:
            os.environ.pop("PYTEST_CURRENT_TEST", None)

    def test_omie_client_timeout_increased_for_tests(self) -> None:
        """AC2: OMIE client timeout increased from 1s to 10s for tests."""
        # Set test environment
        os.environ["PYTEST_CURRENT_TEST"] = "test_something"

        try:
            from raglite.external_data.clients.omie import OMIEClient

            client = OMIEClient()
            assert client.timeout == 10.0
        finally:
            os.environ.pop("PYTEST_CURRENT_TEST", None)

    def test_ecb_client_timeout_increased_for_tests(self) -> None:
        """AC3: ECB client timeout increased from 1s to 10s for tests."""
        # Set test environment
        os.environ["PYTEST_CURRENT_TEST"] = "test_something"

        try:
            from raglite.external_data.clients.ecb import ECBClient

            client = ECBClient()
            assert client.timeout == 10.0
        finally:
            os.environ.pop("PYTEST_CURRENT_TEST", None)

    def test_commodities_client_timeout_increased_for_tests(self) -> None:
        """AC6 (Code Review Fix): CommoditiesClient timeout increased to 10s."""
        # Set test environment
        os.environ["PYTEST_CURRENT_TEST"] = "test_something"

        try:
            from raglite.external_data.clients.commodities import CommoditiesClient

            client = CommoditiesClient()
            assert client.timeout == 10.0
        finally:
            os.environ.pop("PYTEST_CURRENT_TEST", None)

    def test_ice_futures_client_timeout_increased_for_tests(self) -> None:
        """AC7 (Code Review Fix): ICEFuturesClient timeout increased to 10s."""
        # Set test environment
        os.environ["PYTEST_CURRENT_TEST"] = "test_something"

        try:
            from raglite.external_data.clients.ice_futures import ICEFuturesClient

            client = ICEFuturesClient()
            assert client.timeout == 10.0
        finally:
            os.environ.pop("PYTEST_CURRENT_TEST", None)


class TestExternalDataCache:
    """Tests for Sub-Story 6.10.3: Local File Caching."""

    def test_cache_init_creates_directory(self) -> None:
        """AC1: Cache initialization creates cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                cache = ExternalDataCache()
                assert cache.CACHE_DIR.exists()

    def test_cache_set_and_get(self) -> None:
        """AC2: Cache set and get operations work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                cache = ExternalDataCache(ttl_hours=24)

                # Set data
                test_data = {"value": 123, "name": "test"}
                cache.set("test_key", test_data)

                # Get data
                result = cache.get("test_key")
                assert result == test_data

    def test_cache_get_returns_none_for_missing(self) -> None:
        """AC2: Cache returns None for missing keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                cache = ExternalDataCache()
                result = cache.get("nonexistent_key")
                assert result is None

    def test_cache_ttl_expiration(self) -> None:
        """AC3: Cache returns None for expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                cache = ExternalDataCache(ttl_hours=1)

                # Manually write expired cache entry
                cache_path = cache._get_cache_path("expired_key")
                expired_time = datetime.now() - timedelta(hours=2)
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(
                    json.dumps({"cached_at": expired_time.isoformat(), "payload": "old_data"})
                )

                # Should return None for expired entry
                result = cache.get("expired_key")
                assert result is None

    def test_cache_clear_single_key(self) -> None:
        """AC4: Cache clear removes specific key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                cache = ExternalDataCache()

                cache.set("key1", "value1")
                cache.set("key2", "value2")

                # Clear key1
                cleared = cache.clear("key1")
                assert cleared == 1

                # key1 should be gone, key2 should remain
                assert cache.get("key1") is None
                assert cache.get("key2") == "value2"

    def test_cache_clear_all(self) -> None:
        """AC4: Cache clear all removes all entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                cache = ExternalDataCache()

                cache.set("key1", "value1")
                cache.set("key2", "value2")

                # Clear all
                cleared = cache.clear()
                assert cleared == 2

                # Both should be gone
                assert cache.get("key1") is None
                assert cache.get("key2") is None

    def test_cache_handles_serialization_errors(self) -> None:
        """AC2: Cache handles non-serializable data gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                cache = ExternalDataCache()

                # Try to cache non-serializable object
                class NotSerializable:
                    pass

                # Should not raise, but not cache
                cache.set("bad_key", NotSerializable())

                # Should return None (or cached as string via default=str)
                _result = cache.get("bad_key")
                # Cache.set uses default=str, so it should still cache something
                # The test verifies it doesn't crash

    def test_cache_date_serialization(self) -> None:
        """AC5: Cache handles date objects via default=str."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                cache = ExternalDataCache()

                # Data with date objects
                test_data = {"date": date(2024, 1, 15), "value": 100}
                cache.set("date_key", test_data)

                # Get should work (date serialized as string)
                result = cache.get("date_key")
                assert result is not None
                assert result["value"] == 100
                # Date will be serialized as string
                assert "2024-01-15" in str(result["date"])


class TestINEClientCaching:
    """Tests for INE client caching integration (Story 6.10.3 AC2)."""

    @pytest.mark.asyncio
    async def test_ine_building_permits_uses_cache(self) -> None:
        """AC2: INE building permits method uses cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                from raglite.external_data.clients.ine import INEClient

                # Set test environment for timeout
                os.environ["PYTEST_CURRENT_TEST"] = "test_something"
                try:
                    client = INEClient()

                    # Pre-populate cache
                    start_date = date(2024, 1, 1)
                    end_date = date(2024, 3, 31)
                    cache_key = f"ine_building_permits_{start_date}_{end_date}"

                    # Cache fake data
                    cached_data = [
                        {"date": "2024-01-01", "permits_count": 100, "region": "Portugal"}
                    ]
                    client._cache.set(cache_key, cached_data)

                    # Mock the actual API call (should NOT be called)
                    with patch.object(
                        client, "_fetch_with_retry", new_callable=AsyncMock
                    ) as mock_fetch:
                        mock_fetch.side_effect = Exception("Should not be called")

                        # This should use cache
                        result = await client.fetch_building_permits(start_date, end_date)

                        # Should have gotten data from cache
                        assert len(result) == 1
                        assert result[0].permits_count == 100
                        # API should NOT have been called
                        mock_fetch.assert_not_called()

                finally:
                    os.environ.pop("PYTEST_CURRENT_TEST", None)


class TestECBClientCaching:
    """Tests for ECB client caching integration (Story 6.10.3 AC3)."""

    @pytest.mark.asyncio
    async def test_ecb_euribor_uses_cache(self) -> None:
        """AC3: ECB euribor method uses cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ExternalDataCache, "CACHE_DIR", Path(tmpdir) / "test_cache"):
                from raglite.external_data.clients.ecb import ECBClient

                # Set test environment for timeout
                os.environ["PYTEST_CURRENT_TEST"] = "test_something"
                try:
                    client = ECBClient()

                    # Pre-populate cache
                    start_date = date(2024, 1, 1)
                    end_date = date(2024, 3, 31)
                    cache_key = f"ecb_euribor_3M_{start_date}_{end_date}"

                    # Cache fake data
                    cached_data = [{"date": "2024-01-01", "rate_pct": 3.5, "tenor": "3M"}]
                    client._cache.set(cache_key, cached_data)

                    # Mock the actual API call (should NOT be called)
                    with patch.object(
                        client, "_fetch_series", new_callable=AsyncMock
                    ) as mock_fetch:
                        mock_fetch.side_effect = Exception("Should not be called")

                        # This should use cache
                        result = await client.fetch_euribor(start_date, end_date, tenor="3M")

                        # Should have gotten data from cache
                        assert len(result) == 1
                        assert result[0].rate_pct == 3.5
                        # API should NOT have been called
                        mock_fetch.assert_not_called()

                finally:
                    os.environ.pop("PYTEST_CURRENT_TEST", None)
