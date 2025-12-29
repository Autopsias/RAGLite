"""Integration tests for complete ECB macroeconomic pipeline (Story 6.17 AC3)."""

from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.external_data.clients.ecb import (
    ECBClient,
    ECBGDPGrowth,
    ECBInflation,
    interpolate_quarterly_to_monthly,
)

from .conftest import SAMPLE_GDP_CSV, SAMPLE_HICP_CSV

pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


@pytest.mark.asyncio
class TestGDPInterpolationIntegration:
    """Integration tests for GDP quarterly-to-monthly interpolation."""

    async def test_ac3_interpolation_produces_correct_monthly_count(self) -> None:
        """
        Given: 2 years of quarterly GDP data (8 quarters)
        When: Interpolated to monthly
        Then: Produces 24 months of data

        AC3: Quarterly GDP interpolated to monthly for regressor alignment
        """
        client = ECBClient()

        mock_response = MagicMock()
        # Use subset of GDP data for 2 years
        gdp_2_years = """KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE
MNA.Q.Y.PT...,Q,PT,N,2022-Q1,12.5
MNA.Q.Y.PT...,Q,PT,N,2022-Q2,6.9
MNA.Q.Y.PT...,Q,PT,N,2022-Q3,4.3
MNA.Q.Y.PT...,Q,PT,N,2022-Q4,3.0
MNA.Q.Y.PT...,Q,PT,N,2023-Q1,2.5
MNA.Q.Y.PT...,Q,PT,N,2023-Q2,2.6
MNA.Q.Y.PT...,Q,PT,N,2023-Q3,1.9
MNA.Q.Y.PT...,Q,PT,N,2023-Q4,2.2"""
        mock_response.text = gdp_2_years
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            quarterly = await client.fetch_gdp_growth(
                country="PT",
                start_date=date(2022, 1, 1),
                end_date=date(2023, 12, 31),
            )

        monthly = interpolate_quarterly_to_monthly(quarterly)

        assert len(monthly) == 24, f"Expected 24 months, got {len(monthly)}"

    async def test_ac3_interpolation_all_months_present(self) -> None:
        """
        Given: Quarterly GDP data
        When: Interpolated to monthly
        Then: All months within quarters are represented

        AC3: Each quarter expands to 3 months
        """
        quarterly_data = [
            ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=2.0, country="PT"),  # Q1
            ECBGDPGrowth(date=date(2024, 4, 1), growth_pct=2.5, country="PT"),  # Q2
        ]

        monthly = interpolate_quarterly_to_monthly(quarterly_data)

        # Should have Jan, Feb, Mar (Q1) and Apr, May, Jun (Q2)
        expected_months = [
            date(2024, 1, 1),
            date(2024, 2, 1),
            date(2024, 3, 1),
            date(2024, 4, 1),
            date(2024, 5, 1),
            date(2024, 6, 1),
        ]
        actual_dates = [m.date for m in monthly]

        assert actual_dates == expected_months

    async def test_ac3_interpolation_ready_for_prophet(self) -> None:
        """
        Given: Interpolated monthly GDP data
        When: Prepared for Prophet regressor
        Then: Data can be aligned with other monthly regressors

        AC3: Monthly interpolation enables use as Prophet regressor
        """
        quarterly_data = [
            ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=2.0, country="PT"),
            ECBGDPGrowth(date=date(2024, 4, 1), growth_pct=2.5, country="PT"),
            ECBGDPGrowth(date=date(2024, 7, 1), growth_pct=2.2, country="PT"),
        ]

        monthly = interpolate_quarterly_to_monthly(quarterly_data)

        # Verify data structure is compatible with Prophet add_regressor
        assert all(hasattr(m, "date") for m in monthly)
        assert all(hasattr(m, "growth_pct") for m in monthly)

        # Convert to dict for Prophet DataFrame
        prophet_data = [{"ds": m.date, "gdp_growth": m.growth_pct} for m in monthly]
        assert len(prophet_data) == 9  # 3 quarters * 3 months


@pytest.mark.asyncio
class TestECBMacroeconomicPipeline:
    """Integration tests for complete ECB macroeconomic data pipeline."""

    async def test_gdp_and_inflation_fetch_in_parallel(self) -> None:
        """
        Given: Need for both GDP and HICP data
        When: Fetched in parallel
        Then: Both datasets are returned successfully

        AC1+AC2: Both indicators can be fetched concurrently
        """
        client = ECBClient()

        # Mock responses for both GDP and HICP
        gdp_response = MagicMock()
        gdp_response.text = SAMPLE_GDP_CSV
        gdp_response.raise_for_status = MagicMock()

        hicp_response = MagicMock()
        hicp_response.text = SAMPLE_HICP_CSV
        hicp_response.raise_for_status = MagicMock()

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Alternate between GDP and HICP responses based on URL
            url = args[0] if args else kwargs.get("url", "")
            if "MNA" in url:
                return gdp_response
            elif "ICP" in url:
                return hicp_response
            # Default based on call order
            if call_count % 2 == 1:
                return gdp_response
            return hicp_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)

            gdp_data, hicp_data = await asyncio.gather(
                client.fetch_gdp_growth(
                    country="PT",
                    start_date=date(2020, 1, 1),
                    end_date=date(2024, 12, 31),
                ),
                client.fetch_inflation(
                    country="PT",
                    start_date=date(2020, 1, 1),
                    end_date=date(2024, 12, 31),
                ),
            )

        assert len(gdp_data) > 0, "GDP data should be returned"
        assert len(hicp_data) > 0, "HICP data should be returned"

    async def test_gdp_interpolated_aligns_with_monthly_hicp(self) -> None:
        """
        Given: Quarterly GDP and monthly HICP data
        When: GDP is interpolated to monthly
        Then: GDP and HICP dates can be aligned for multivariate forecasting

        AC3: Interpolation enables alignment with monthly regressors
        """
        # Quarterly GDP
        quarterly_gdp = [
            ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=2.0, country="PT"),
            ECBGDPGrowth(date=date(2024, 4, 1), growth_pct=2.5, country="PT"),
        ]

        # Monthly HICP
        monthly_hicp = [
            ECBInflation(date=date(2024, 1, 1), index_value=113.0, country="PT"),
            ECBInflation(date=date(2024, 2, 1), index_value=113.5, country="PT"),
            ECBInflation(date=date(2024, 3, 1), index_value=114.0, country="PT"),
            ECBInflation(date=date(2024, 4, 1), index_value=114.2, country="PT"),
            ECBInflation(date=date(2024, 5, 1), index_value=114.7, country="PT"),
            ECBInflation(date=date(2024, 6, 1), index_value=114.4, country="PT"),
        ]

        # Interpolate GDP to monthly
        monthly_gdp = interpolate_quarterly_to_monthly(quarterly_gdp)

        # Dates should align
        gdp_dates = {m.date for m in monthly_gdp}
        hicp_dates = {m.date for m in monthly_hicp}

        assert gdp_dates == hicp_dates, "Interpolated GDP dates should match HICP dates"
