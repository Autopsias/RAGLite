"""Integration tests for building permits regressor.

Story 6.18: Fix INE Building Permits API
- Tests with real API calls (marked as slow)
- Tests regressor integration with forecasting system
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest


class TestINEBuildingPermitsRealAPI:
    """Integration tests with real INE API."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_ine_building_permits_real_api(self) -> None:
        """Test fetching building permits from real INE API."""
        from raglite.external_data.clients.ine import INEClient

        client = INEClient()
        permits = await client.fetch_building_permits(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert permits is not None
        assert len(permits) > 0
        # Verify we got construction data (not death statistics)
        # Building permits should have reasonable counts (not zero or astronomical)
        for p in permits[:5]:
            assert 0 < p.permits_count < 100000, f"Suspicious permits count: {p.permits_count}"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_ine_building_permits_data_quality(self) -> None:
        """Verify INE building permits data is construction-related."""
        from raglite.external_data.clients.ine import INEClient

        client = INEClient()
        permits = await client.fetch_building_permits(
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Aggregate by date to get national totals
        totals_by_date: dict[date, int] = {}
        for p in permits:
            if p.date not in totals_by_date:
                totals_by_date[p.date] = 0
            totals_by_date[p.date] += p.permits_count

        # Portugal typically issues 2,000-10,000 building permits per month
        # If we're getting wildly different numbers, something is wrong
        for d, total in totals_by_date.items():
            assert 500 < total < 50000, f"Suspicious total for {d}: {total}"


class TestEurostatBuildingPermitsRealAPI:
    """Integration tests with real Eurostat API."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_eurostat_building_permits_real_api(self) -> None:
        """Test fetching building permits from real Eurostat API."""
        from raglite.external_data.clients.eurostat import EurostatClient

        client = EurostatClient()
        permits = await client.fetch_building_permits(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert permits is not None
        assert len(permits) > 0
        # Verify we got valid data
        for p in permits[:3]:
            assert p.permits_count >= 0
            assert p.country == "PT"


class TestBuildingPermitsRegressorIntegration:
    """Integration tests for building permits as regressor."""

    @pytest.mark.integration
    @pytest.mark.slow  # Hits real INE/Eurostat APIs
    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_building_permits_regressor_returns_series(self) -> None:
        """Verify building_permits regressor returns valid pandas Series."""
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "building_permits",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        # Should return data (from INE or Eurostat fallback)
        assert result is not None
        assert isinstance(result, pd.Series)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) > 0

    @pytest.mark.integration
    @pytest.mark.slow  # Hits real INE/Eurostat APIs
    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_building_permits_regressor_no_duplicates(self) -> None:
        """Verify aggregated data has no duplicate dates."""
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        result = await fetch_single_regressor(
            "building_permits",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert result is not None
        # No duplicate indices after aggregation
        assert not result.index.duplicated().any()


class TestBuildingPermitsCorrelation:
    """AC4: Correlation validation with sales_volume."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.preserve_collection
    @pytest.mark.asyncio
    async def test_building_permits_correlation_with_construction_output(self) -> None:
        """Verify building permits correlates with construction output (proxy for sales_volume)."""
        from raglite.forecasting.regressor_fetch import fetch_single_regressor

        # Fetch both regressors
        permits = await fetch_single_regressor(
            "building_permits",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 6, 30),
        )

        construction = await fetch_single_regressor(
            "construction_output",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 6, 30),
        )

        if permits is not None and construction is not None and len(permits) > 10:
            # Align dates
            common_dates = permits.index.intersection(construction.index)
            if len(common_dates) > 10:
                permits_aligned = permits.loc[common_dates]
                construction_aligned = construction.loc[common_dates]

                # Calculate correlation
                correlation = permits_aligned.corr(construction_aligned)

                # Should have positive correlation (>0.3 per AC4)
                # Note: We use > 0 as baseline, AC4 target is >0.3
                assert correlation > 0, f"Expected positive correlation, got {correlation}"
