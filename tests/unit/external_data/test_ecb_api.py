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
    ECBInflation,
)


class TestECBGDPGrowthModel:
    """Tests for ECBGDPGrowth dataclass."""

    def test_ac1_gdp_growth_dataclass_exists(self) -> None:
        """
        Given: The ECBGDPGrowth dataclass is defined
        When: Creating a GDP growth record
        Then: All required fields are present and correctly typed

        AC1: GDP growth dataclass for storing quarterly YoY growth rates
        """
        gdp = ECBGDPGrowth(
            date=date(2024, 1, 1),
            growth_pct=2.5,
            country="PT",
            frequency="Q",
        )
        assert gdp.date == date(2024, 1, 1)
        assert gdp.growth_pct == 2.5
        assert gdp.country == "PT"
        assert gdp.frequency == "Q"

    def test_ac1_gdp_growth_default_frequency(self) -> None:
        """
        Given: ECBGDPGrowth with only required fields
        When: frequency is not specified
        Then: frequency defaults to "Q" (Quarterly)

        AC1: GDP growth defaults to quarterly frequency
        """
        gdp = ECBGDPGrowth(
            date=date(2024, 1, 1),
            growth_pct=1.8,
            country="PT",
        )
        assert gdp.frequency == "Q"


class TestECBInflationModel:
    """Tests for ECBInflation dataclass."""

    def test_ac2_inflation_dataclass_exists(self) -> None:
        """
        Given: The ECBInflation dataclass is defined
        When: Creating an inflation record
        Then: All required fields are present and correctly typed

        AC2: HICP inflation dataclass for storing monthly index values
        """
        inflation = ECBInflation(
            date=date(2024, 1, 1),
            index_value=120.5,
            country="PT",
            yoy_change_pct=3.2,
        )
        assert inflation.date == date(2024, 1, 1)
        assert inflation.index_value == 120.5
        assert inflation.country == "PT"
        assert inflation.yoy_change_pct == 3.2

    def test_ac2_inflation_yoy_optional(self) -> None:
        """
        Given: ECBInflation with only required fields
        When: yoy_change_pct is not specified
        Then: yoy_change_pct defaults to None

        AC2: YoY change is optional (calculated when 12 months of data available)
        """
        inflation = ECBInflation(
            date=date(2024, 1, 1),
            index_value=118.0,
            country="PT",
        )
        assert inflation.yoy_change_pct is None


class TestECBPeriodParsing:
    """Tests for ECB period string parsing."""

    def test_ac4_parse_quarterly_period_q1(self) -> None:
        """
        Given: ECB quarterly period string "2024-Q1"
        When: Parsed by _parse_ecb_period
        Then: Returns date(2024, 1, 1) - first day of Q1

        AC4: Unit tests verify ECB SDW parsing - quarterly format
        """
        client = ECBClient()
        result = client._parse_ecb_period("2024-Q1")
        assert result == date(2024, 1, 1)

    def test_ac4_parse_quarterly_period_q2(self) -> None:
        """
        Given: ECB quarterly period string "2024-Q2"
        When: Parsed by _parse_ecb_period
        Then: Returns date(2024, 4, 1) - first day of Q2

        AC4: Q2 maps to April
        """
        client = ECBClient()
        result = client._parse_ecb_period("2024-Q2")
        assert result == date(2024, 4, 1)

    def test_ac4_parse_quarterly_period_q3(self) -> None:
        """
        Given: ECB quarterly period string "2024-Q3"
        When: Parsed by _parse_ecb_period
        Then: Returns date(2024, 7, 1) - first day of Q3

        AC4: Q3 maps to July
        """
        client = ECBClient()
        result = client._parse_ecb_period("2024-Q3")
        assert result == date(2024, 7, 1)

    def test_ac4_parse_quarterly_period_q4(self) -> None:
        """
        Given: ECB quarterly period string "2024-Q4"
        When: Parsed by _parse_ecb_period
        Then: Returns date(2024, 10, 1) - first day of Q4

        AC4: Q4 maps to October
        """
        client = ECBClient()
        result = client._parse_ecb_period("2024-Q4")
        assert result == date(2024, 10, 1)

    def test_ac4_parse_monthly_period(self) -> None:
        """
        Given: ECB monthly period string "2024-03"
        When: Parsed by _parse_ecb_period
        Then: Returns date(2024, 3, 1) - first day of month

        AC4: Monthly format parsing (also used by existing EURIBOR)
        """
        client = ECBClient()
        result = client._parse_ecb_period("2024-03")
        assert result == date(2024, 3, 1)


class TestGDPCSVParsing:
    """Tests for GDP growth CSV parsing."""

    def test_ac4_parse_gdp_csv_valid(self) -> None:
        """
        Given: Valid GDP growth CSV response from ECB API
        When: Parsed by _parse_gdp_csv
        Then: Returns list of ECBGDPGrowth records with correct values

        AC4: Unit tests verify ECB SDW parsing for GDP
        """
        mock_csv = """KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2024-Q1,2.5
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2024-Q2,2.8
MNA.Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N,Q,PT,N,2024-Q3,2.1"""

        client = ECBClient()
        result = client._parse_gdp_csv(mock_csv, country="PT")

        assert len(result) == 3
        assert result[0].growth_pct == 2.5
        assert result[0].country == "PT"
        assert result[0].date == date(2024, 1, 1)
        assert result[1].growth_pct == 2.8
        assert result[1].date == date(2024, 4, 1)
        assert result[2].growth_pct == 2.1
        assert result[2].date == date(2024, 7, 1)

    def test_ac4_parse_gdp_csv_empty_response(self) -> None:
        """
        Given: Empty CSV response (header only)
        When: Parsed by _parse_gdp_csv
        Then: Returns empty list (no data available)

        AC4: Handle empty API responses gracefully
        """
        mock_csv = "KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE\n"

        client = ECBClient()
        result = client._parse_gdp_csv(mock_csv, country="PT")

        assert len(result) == 0

    def test_ac4_parse_gdp_csv_skip_invalid_rows(self) -> None:
        """
        Given: CSV with some invalid rows (missing values)
        When: Parsed by _parse_gdp_csv
        Then: Valid rows are parsed, invalid rows are skipped

        AC4: Robust parsing - skip invalid records
        """
        mock_csv = """KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE
MNA.Q.Y.PT...,Q,PT,N,2024-Q1,2.5
MNA.Q.Y.PT...,Q,PT,N,2024-Q2,
MNA.Q.Y.PT...,Q,PT,N,2024-Q3,2.1"""

        client = ECBClient()
        result = client._parse_gdp_csv(mock_csv, country="PT")

        # Should have 2 valid rows (Q1 and Q3), Q2 is missing OBS_VALUE
        assert len(result) == 2
        assert result[0].growth_pct == 2.5
        assert result[1].growth_pct == 2.1

    def test_ac4_parse_gdp_csv_negative_growth(self) -> None:
        """
        Given: CSV with negative GDP growth (recession)
        When: Parsed by _parse_gdp_csv
        Then: Negative values are correctly parsed

        AC4: Handle negative growth rates (e.g., COVID recession)
        """
        mock_csv = """KEY,FREQ,REF_AREA,ADJUSTMENT,TIME_PERIOD,OBS_VALUE
MNA.Q.Y.PT...,Q,PT,N,2020-Q2,-16.3"""

        client = ECBClient()
        result = client._parse_gdp_csv(mock_csv, country="PT")

        assert len(result) == 1
        assert result[0].growth_pct == -16.3
