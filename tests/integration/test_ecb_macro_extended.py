"""Integration tests for ECB macroeconomic indicators - Extended tests.

Story 6.17: Add ECB Macroeconomic Indicators
- AC3: Quarterly GDP interpolation to monthly frequency
- Full pipeline tests
- Real API integration tests

This is the RED phase of TDD - tests MUST fail because implementation doesn't exist yet.

Integration tests verify actual ECB SDW API communication and end-to-end flows.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These imports will fail until implementation is complete (RED phase)
from raglite.external_data.clients.ecb import (
    ECBClient,
    ECBGDPGrowth,
    ECBInflation,
    interpolate_quarterly_to_monthly,
)

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


# =============================================================================
# Sample ECB API Response Data
# =============================================================================

# Sample GDP growth CSV response from ECB SDW
# Format: MNA (National accounts) dataset
SAMPLE_GDP_CSV = """KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2020-Q1,0.6
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2020-Q2,-16.3
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2020-Q3,-5.5
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2020-Q4,-6.1
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2021-Q1,-5.3
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2021-Q2,16.3
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2021-Q3,4.6
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2021-Q4,6.5
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2022-Q1,12.5
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2022-Q2,6.9
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2022-Q3,4.3
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2022-Q4,3.0
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2023-Q1,2.5
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2023-Q2,2.6
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2023-Q3,1.9
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2023-Q4,2.2
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2024-Q1,1.5
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2024-Q2,1.6
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2024-Q3,1.8"""

# Sample HICP inflation CSV response from ECB SDW
# Format: ICP (HICP) dataset
SAMPLE_HICP_CSV = """KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-01,101.74
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-02,101.50
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-03,101.34
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-04,100.80
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-05,100.42
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-06,101.27
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-07,101.12
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-08,100.51
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-09,101.15
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-10,101.18
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-11,100.76
ICP.M.PT.N.000000.4.INX,M,PT,N,2020-12,100.87
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-01,101.35
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-02,101.04
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-03,102.00
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-04,101.94
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-05,102.18
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-06,101.96
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-07,102.47
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-08,102.13
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-09,102.51
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-10,103.20
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-11,103.60
ICP.M.PT.N.000000.4.INX,M,PT,N,2021-12,103.33
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-01,104.22
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-02,105.02
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-03,106.77
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-04,107.52
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-05,109.04
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-06,110.30
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-07,110.55
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-08,110.51
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-09,111.09
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-10,111.81
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-11,111.47
ICP.M.PT.N.000000.4.INX,M,PT,N,2022-12,111.26
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-01,112.25
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-02,112.49
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-03,112.53
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-04,112.92
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-05,112.67
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-06,112.38
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-07,112.19
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-08,112.54
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-09,113.06
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-10,113.18
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-11,112.79
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-12,112.67
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-01,113.22
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-02,113.61
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-03,114.08
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-04,114.20
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-05,114.71
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-06,114.40
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-07,114.65
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-08,114.35
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-09,115.02
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-10,115.44
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-11,115.83"""


# =============================================================================
# Integration Tests - Quarterly to Monthly Interpolation (AC3)
# =============================================================================


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


# =============================================================================
# Integration Tests - Full Pipeline (AC1 + AC2 + AC3)
# =============================================================================


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
        import asyncio

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


# =============================================================================
# Integration Tests with Real API (marked as slow for CI)
# =============================================================================


@pytest.mark.slow
@pytest.mark.external_api
@pytest.mark.asyncio
class TestECBMacroeconomicRealAPI:
    """Integration tests that hit the real ECB SDW API.

    These tests are marked as slow and external_api for:
    - CI exclusion by default
    - Manual verification when needed
    """

    async def test_real_gdp_growth_portugal(self) -> None:
        """
        Given: Real ECB SDW API connection
        When: fetch_gdp_growth() is called
        Then: Real GDP data for Portugal is returned

        AC1: Real API integration verification
        """
        client = ECBClient()

        data = await client.fetch_gdp_growth(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert len(data) >= 16, f"Expected at least 16 quarters, got {len(data)}"
        assert all(d.country == "PT" for d in data)

    async def test_real_inflation_portugal(self) -> None:
        """
        Given: Real ECB SDW API connection
        When: fetch_inflation() is called
        Then: Real HICP data for Portugal is returned

        AC2: Real API integration verification
        """
        client = ECBClient()

        data = await client.fetch_inflation(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert len(data) >= 48, f"Expected at least 48 months, got {len(data)}"
        assert all(d.country == "PT" for d in data)
