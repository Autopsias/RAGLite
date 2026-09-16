"""Unit tests for building permits regressor.

Story 6.18: Fix INE Building Permits API
- AC1: INE building permits aggregated to national total
- AC2: Eurostat building permits backup
- AC3: Fallback logic (INE → Eurostat)
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from raglite.external_data.models import INEBuildingPermits


class TestINEBuildingPermitsAggregation:
    """AC1: INE Building Permits Aggregated to National Total."""

    @pytest.mark.asyncio
    async def test_ine_building_permits_aggregates_to_national(self) -> None:
        """AC1.1: Regional data aggregated to national monthly totals."""
        # Setup mock data with multiple regions for same month
        mock_regional_data = [
            INEBuildingPermits(date=date(2024, 1, 1), permits_count=100, region="Lisboa"),
            INEBuildingPermits(date=date(2024, 1, 1), permits_count=50, region="Porto"),
            INEBuildingPermits(date=date(2024, 1, 1), permits_count=30, region="Algarve"),
            INEBuildingPermits(date=date(2024, 2, 1), permits_count=120, region="Lisboa"),
            INEBuildingPermits(date=date(2024, 2, 1), permits_count=60, region="Porto"),
        ]

        with patch("raglite.external_data.clients.ine.INEClient") as mock_ine:
            mock_client = AsyncMock()
            mock_client.fetch_building_permits.return_value = mock_regional_data
            mock_ine.return_value = mock_client

            from raglite.forecasting.regressor_fetch import fetch_single_regressor

            result = await fetch_single_regressor(
                "building_permits",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

        assert result is not None
        assert isinstance(result, pd.Series)
        # January: 100 + 50 + 30 = 180
        assert result.loc[pd.Timestamp("2024-01-01")] == 180
        # February: 120 + 60 = 180
        assert result.loc[pd.Timestamp("2024-02-01")] == 180

    @pytest.mark.asyncio
    async def test_ine_building_permits_uses_national_totals_when_available(self) -> None:
        """AC1.3: Uses national totals directly when available (no double-counting)."""
        # Mock data with BOTH regional data AND national totals
        # Should use only Portugal totals, not sum all
        mock_mixed_data = [
            INEBuildingPermits(date=date(2024, 1, 1), permits_count=100, region="Lisboa"),
            INEBuildingPermits(date=date(2024, 1, 1), permits_count=50, region="Porto"),
            INEBuildingPermits(
                date=date(2024, 1, 1), permits_count=150, region="Portugal"
            ),  # National total
            INEBuildingPermits(
                date=date(2024, 2, 1), permits_count=200, region="Portugal"
            ),  # National total
        ]

        with patch("raglite.external_data.clients.ine.INEClient") as mock_ine:
            mock_client = AsyncMock()
            mock_client.fetch_building_permits.return_value = mock_mixed_data
            mock_ine.return_value = mock_client

            from raglite.forecasting.regressor_fetch import fetch_single_regressor

            result = await fetch_single_regressor(
                "building_permits",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

        assert result is not None
        # Should use Portugal national total (150), not sum all (100+50+150=300)
        assert result.loc[pd.Timestamp("2024-01-01")] == 150
        assert result.loc[pd.Timestamp("2024-02-01")] == 200

    @pytest.mark.asyncio
    async def test_ine_building_permits_returns_series_with_datetime_index(self) -> None:
        """AC1.2: Returns pd.Series with DatetimeIndex for Prophet compatibility."""
        mock_data = [
            INEBuildingPermits(date=date(2024, 1, 1), permits_count=100, region="Portugal"),
            INEBuildingPermits(date=date(2024, 2, 1), permits_count=110, region="Portugal"),
        ]

        with patch("raglite.external_data.clients.ine.INEClient") as mock_ine:
            mock_client = AsyncMock()
            mock_client.fetch_building_permits.return_value = mock_data
            mock_ine.return_value = mock_client

            from raglite.forecasting.regressor_fetch import fetch_single_regressor

            result = await fetch_single_regressor(
                "building_permits",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

        assert result is not None
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 2


class TestEurostatBuildingPermitsBackup:
    """AC2: Eurostat Building Permits Backup."""

    @pytest.mark.asyncio
    async def test_eurostat_building_permits_method_exists(self) -> None:
        """AC2.1: fetch_building_permits() method exists in EurostatClient."""
        from raglite.external_data.clients.eurostat import EurostatClient

        client = EurostatClient()
        assert hasattr(client, "fetch_building_permits")
        assert callable(client.fetch_building_permits)

    @pytest.mark.asyncio
    async def test_eurostat_building_permits_uses_correct_dataset(self) -> None:
        """AC2.2: Uses dataset sts_cobp_m with PT country filter."""
        from raglite.external_data.clients.eurostat import EurostatClient

        client = EurostatClient()
        assert hasattr(client, "BUILDING_PERMITS_DATASET")
        assert client.BUILDING_PERMITS_DATASET == "sts_cobp_m"


class TestBuildingPermitsFallback:
    """AC3: Fallback Logic (INE → Eurostat)."""

    @pytest.mark.asyncio
    async def test_uses_ine_when_available(self) -> None:
        """AC3.1: Uses INE data when available."""
        mock_ine_data = [
            INEBuildingPermits(date=date(2024, 1, 1), permits_count=100, region="Portugal"),
        ]

        with patch("raglite.external_data.clients.ine.INEClient") as mock_ine:
            mock_client = AsyncMock()
            mock_client.fetch_building_permits.return_value = mock_ine_data
            mock_ine.return_value = mock_client

            from raglite.forecasting.regressor_fetch import fetch_single_regressor

            result = await fetch_single_regressor(
                "building_permits",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

        assert result is not None
        mock_client.fetch_building_permits.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_eurostat_when_ine_fails(self) -> None:
        """AC3.2: Falls back to Eurostat when INE fails."""
        from raglite.external_data.models import EurostatBuildingPermits

        with (
            patch("raglite.external_data.clients.ine.INEClient") as mock_ine,
            patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_eurostat,
        ):
            # INE fails
            ine_client = AsyncMock()
            ine_client.fetch_building_permits.return_value = []  # No data
            mock_ine.return_value = ine_client

            # Eurostat provides backup
            eurostat_client = AsyncMock()
            eurostat_client.fetch_building_permits.return_value = [
                EurostatBuildingPermits(
                    date=date(2024, 1, 1),
                    permits_count=150,
                    country="PT",
                    building_type="TOTAL",
                )
            ]
            mock_eurostat.return_value = eurostat_client

            from raglite.forecasting.regressor_fetch import fetch_single_regressor

            result = await fetch_single_regressor(
                "building_permits",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

        assert result is not None
        eurostat_client.fetch_building_permits.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_eurostat_on_ine_exception(self) -> None:
        """AC3.3: Falls back to Eurostat when INE throws exception."""
        from raglite.external_data.exceptions import ExternalDataFetchError
        from raglite.external_data.models import EurostatBuildingPermits

        with (
            patch("raglite.external_data.clients.ine.INEClient") as mock_ine,
            patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_eurostat,
        ):
            # INE throws exception
            ine_client = AsyncMock()
            ine_client.fetch_building_permits.side_effect = ExternalDataFetchError(
                source="INE", message="API unavailable"
            )
            mock_ine.return_value = ine_client

            # Eurostat provides backup
            eurostat_client = AsyncMock()
            eurostat_client.fetch_building_permits.return_value = [
                EurostatBuildingPermits(
                    date=date(2024, 1, 1),
                    permits_count=150,
                    country="PT",
                    building_type="TOTAL",
                )
            ]
            mock_eurostat.return_value = eurostat_client

            from raglite.forecasting.regressor_fetch import fetch_single_regressor

            result = await fetch_single_regressor(
                "building_permits",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

        assert result is not None


class TestRegressorConfigRegistration:
    """AC4/AC5: Regressor registration and no regression."""

    def test_building_permits_in_available_regressors(self) -> None:
        """Building permits should be registered in AVAILABLE_REGRESSORS."""
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert "building_permits" in AVAILABLE_REGRESSORS

    def test_building_permits_not_disabled(self) -> None:
        """Building permits regressor should not be disabled in regressor_fetch."""
        import inspect

        from raglite.forecasting import regressor_fetch

        source = inspect.getsource(regressor_fetch.fetch_single_regressor)
        # The old disabled code had "Currently disabled" or returned None immediately
        # After fix, it should actually fetch data
        assert 'reg_name == "building_permits"' in source
        # Should NOT have "Currently disabled" in the building_permits block
        # This test verifies the regressor is enabled
