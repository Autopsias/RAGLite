"""Unit tests for ECB macroeconomic indicators.

Story 6.17: Add ECB Macroeconomic Indicators
- AC1: GDP Growth Rate API
- AC2: HICP Inflation API
- AC3: Quarterly GDP interpolation to monthly
- AC4: Unit tests for ECB SDW parsing

This is the RED phase of TDD - tests MUST fail because implementation doesn't exist yet.
"""

from __future__ import annotations

from datetime import date

# Story 6.17: Add ECB Macroeconomic Indicators
# These imports will fail until implementation is complete (RED phase)
# Import paths match the story specification
from raglite.external_data.clients.ecb import (
    ECBClient,
    ECBGDPGrowth,
    interpolate_quarterly_to_monthly,
)


class TestHICPCSVParsing:
    """Tests for HICP inflation CSV parsing."""

    def test_ac4_parse_hicp_csv_valid(self) -> None:
        """
        Given: Valid HICP CSV response from ECB API
        When: Parsed by _parse_hicp_csv
        Then: Returns list of ECBInflation records with correct values

        AC4: Unit tests verify ECB SDW parsing for HICP
        """
        mock_csv = """KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-01,120.5
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-02,121.2
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-03,121.8"""

        client = ECBClient()
        result = client._parse_hicp_csv(mock_csv, country="PT")

        assert len(result) == 3
        assert result[0].index_value == 120.5
        assert result[0].country == "PT"
        assert result[0].date == date(2024, 1, 1)
        assert result[1].index_value == 121.2
        assert result[1].date == date(2024, 2, 1)
        assert result[2].index_value == 121.8
        assert result[2].date == date(2024, 3, 1)

    def test_ac4_parse_hicp_csv_with_yoy_calculation(self) -> None:
        """
        Given: HICP data spanning more than 12 months
        When: Parsed by _parse_hicp_csv
        Then: YoY change is calculated for records with prior year data

        AC4: YoY calculation when sufficient historical data available
        """
        # Create 13 months of data so YoY can be calculated for the last month
        mock_csv = """KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-01,100.0
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-02,100.5
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-03,101.0
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-04,101.5
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-05,102.0
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-06,102.5
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-07,103.0
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-08,103.5
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-09,104.0
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-10,104.5
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-11,105.0
ICP.M.PT.N.000000.4.INX,M,PT,N,2023-12,105.5
ICP.M.PT.N.000000.4.INX,M,PT,N,2024-01,106.0"""

        client = ECBClient()
        result = client._parse_hicp_csv(mock_csv, country="PT")

        assert len(result) == 13
        # Jan 2024 should have YoY: (106.0 - 100.0) / 100.0 * 100 = 6.0%
        jan_2024 = [r for r in result if r.date == date(2024, 1, 1)][0]
        assert jan_2024.yoy_change_pct is not None
        assert abs(jan_2024.yoy_change_pct - 6.0) < 0.01

    def test_ac4_parse_hicp_csv_empty(self) -> None:
        """
        Given: Empty HICP CSV response
        When: Parsed by _parse_hicp_csv
        Then: Returns empty list

        AC4: Handle empty API responses gracefully
        """
        mock_csv = "KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE\n"

        client = ECBClient()
        result = client._parse_hicp_csv(mock_csv, country="PT")

        assert len(result) == 0


class TestQuarterlyToMonthlyInterpolation:
    """Tests for quarterly to monthly interpolation."""

    def test_ac3_interpolate_constant_method(self) -> None:
        """
        Given: Quarterly GDP data for 2 quarters
        When: Interpolated with constant method
        Then: Each month in a quarter gets the same value as the quarter

        AC3: Quarterly GDP interpolated to monthly for regressor alignment
        """
        quarterly_data = [
            ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=2.5, country="PT"),
            ECBGDPGrowth(date=date(2024, 4, 1), growth_pct=2.8, country="PT"),
        ]

        monthly_data = interpolate_quarterly_to_monthly(quarterly_data, method="constant")

        assert len(monthly_data) == 6  # 3 months * 2 quarters
        # Q1 months all get 2.5%
        assert monthly_data[0].growth_pct == 2.5  # Jan
        assert monthly_data[0].date == date(2024, 1, 1)
        assert monthly_data[1].growth_pct == 2.5  # Feb
        assert monthly_data[1].date == date(2024, 2, 1)
        assert monthly_data[2].growth_pct == 2.5  # Mar
        assert monthly_data[2].date == date(2024, 3, 1)
        # Q2 months all get 2.8%
        assert monthly_data[3].growth_pct == 2.8  # Apr
        assert monthly_data[3].date == date(2024, 4, 1)
        assert monthly_data[4].growth_pct == 2.8  # May
        assert monthly_data[4].date == date(2024, 5, 1)
        assert monthly_data[5].growth_pct == 2.8  # Jun
        assert monthly_data[5].date == date(2024, 6, 1)

    def test_ac3_interpolate_preserves_country(self) -> None:
        """
        Given: Quarterly GDP data with country code
        When: Interpolated to monthly
        Then: Country code is preserved in all monthly records

        AC3: Metadata preserved during interpolation
        """
        quarterly_data = [
            ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=2.5, country="PT"),
        ]

        monthly_data = interpolate_quarterly_to_monthly(quarterly_data, method="constant")

        assert all(m.country == "PT" for m in monthly_data)

    def test_ac3_interpolate_changes_frequency(self) -> None:
        """
        Given: Quarterly GDP data (frequency="Q")
        When: Interpolated to monthly
        Then: Monthly records have frequency="M"

        AC3: Frequency indicator updated after interpolation
        """
        quarterly_data = [
            ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=2.5, country="PT", frequency="Q"),
        ]

        monthly_data = interpolate_quarterly_to_monthly(quarterly_data, method="constant")

        assert all(m.frequency == "M" for m in monthly_data)

    def test_ac3_interpolate_empty_list(self) -> None:
        """
        Given: Empty quarterly data list
        When: Interpolated
        Then: Returns empty list

        AC3: Handle edge case of no input data
        """
        quarterly_data: list[ECBGDPGrowth] = []

        monthly_data = interpolate_quarterly_to_monthly(quarterly_data, method="constant")

        assert len(monthly_data) == 0

    def test_ac3_interpolate_single_quarter(self) -> None:
        """
        Given: Single quarter of GDP data
        When: Interpolated to monthly
        Then: Returns 3 monthly records

        AC3: Single quarter produces 3 months
        """
        quarterly_data = [
            ECBGDPGrowth(date=date(2024, 7, 1), growth_pct=1.9, country="PT"),  # Q3
        ]

        monthly_data = interpolate_quarterly_to_monthly(quarterly_data, method="constant")

        assert len(monthly_data) == 3
        assert monthly_data[0].date == date(2024, 7, 1)  # Jul
        assert monthly_data[1].date == date(2024, 8, 1)  # Aug
        assert monthly_data[2].date == date(2024, 9, 1)  # Sep

    def test_ac3_interpolate_full_year(self) -> None:
        """
        Given: Full year of quarterly GDP data (4 quarters)
        When: Interpolated to monthly
        Then: Returns 12 monthly records

        AC3: Full year interpolation
        """
        quarterly_data = [
            ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=2.0, country="PT"),  # Q1
            ECBGDPGrowth(date=date(2024, 4, 1), growth_pct=2.5, country="PT"),  # Q2
            ECBGDPGrowth(date=date(2024, 7, 1), growth_pct=2.2, country="PT"),  # Q3
            ECBGDPGrowth(date=date(2024, 10, 1), growth_pct=1.8, country="PT"),  # Q4
        ]

        monthly_data = interpolate_quarterly_to_monthly(quarterly_data, method="constant")

        assert len(monthly_data) == 12
        # Verify all 12 months are present
        months = [m.date.month for m in monthly_data]
        assert sorted(months) == list(range(1, 13))

    def test_ac3_interpolate_default_method_is_constant(self) -> None:
        """
        Given: Quarterly GDP data
        When: Interpolated without specifying method
        Then: Uses constant interpolation (default)

        AC3: Default interpolation method
        """
        quarterly_data = [
            ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=3.0, country="PT"),
        ]

        monthly_data = interpolate_quarterly_to_monthly(quarterly_data)

        # Should use constant method by default
        assert len(monthly_data) == 3
        assert all(m.growth_pct == 3.0 for m in monthly_data)


class TestECBClientGDPSeriesKey:
    """Tests for GDP series key configuration."""

    def test_ac1_gdp_series_key_exists(self) -> None:
        """
        Given: ECBClient instance
        When: Accessing GDP_SERIES constant
        Then: Series key for Portugal GDP growth is defined

        AC1: GDP series key configured for ECB SDW API
        """
        client = ECBClient()

        # The GDP_SERIES should be a dict or string constant
        assert hasattr(client, "GDP_SERIES") or hasattr(ECBClient, "GDP_SERIES")


class TestECBClientHICPSeriesKey:
    """Tests for HICP series key configuration."""

    def test_ac2_hicp_series_key_exists(self) -> None:
        """
        Given: ECBClient instance
        When: Accessing HICP_SERIES constant
        Then: Series key for Portugal HICP inflation is defined

        AC2: HICP series key configured for ECB SDW API
        """
        client = ECBClient()

        # The HICP_SERIES should be a dict or string constant
        assert hasattr(client, "HICP_SERIES") or hasattr(ECBClient, "HICP_SERIES")


class TestECBClientMethodSignatures:
    """Tests for ECBClient method signatures (interface validation)."""

    def test_ac1_fetch_gdp_growth_method_exists(self) -> None:
        """
        Given: ECBClient instance
        When: Checking for fetch_gdp_growth method
        Then: Method exists with correct signature

        AC1: fetch_gdp_growth method defined on ECBClient
        """
        client = ECBClient()
        assert hasattr(client, "fetch_gdp_growth")
        assert callable(client.fetch_gdp_growth)

    def test_ac2_fetch_inflation_method_exists(self) -> None:
        """
        Given: ECBClient instance
        When: Checking for fetch_inflation method
        Then: Method exists with correct signature

        AC2: fetch_inflation method defined on ECBClient
        """
        client = ECBClient()
        assert hasattr(client, "fetch_inflation")
        assert callable(client.fetch_inflation)

    def test_ac3_interpolate_method_exists(self) -> None:
        """
        Given: ECBClient instance
        When: Checking for interpolate_quarterly_to_monthly method
        Then: Method exists as either instance method or module function

        AC3: interpolate_quarterly_to_monthly available for use
        """
        # Can be either a method on ECBClient or a standalone function
        client = ECBClient()
        has_method = hasattr(client, "interpolate_quarterly_to_monthly")
        has_function = callable(interpolate_quarterly_to_monthly)
        assert has_method or has_function
