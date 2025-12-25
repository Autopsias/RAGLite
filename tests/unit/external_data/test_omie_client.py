"""Unit tests for OMIE (Spanish-Portuguese Electricity Market) client.

Story 7.1: Split test_external_data_clients.py
This module contains tests for: TestOMIEClient, TestOMIEStory692, TestOMIEClientAdditional
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from raglite.external_data.clients.omie import OMIEClient
from raglite.external_data.models import OMIEElectricityPrice


class TestOMIEClient:
    """Tests for OMIE electricity market client.

    Story 6.9.2: Updated tests for new OMIE CSV format and URL pattern.
    """

    @pytest.fixture
    def client(self) -> OMIEClient:
        """Create OMIE client instance."""
        return OMIEClient()

    @pytest.mark.asyncio
    async def test_fetch_spot_prices_success(self, client: OMIEClient) -> None:
        """Test successful spot prices fetch.

        Story 6.9.2 AC3/AC5: Updated for new CSV format.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Story 6.9.2 AC3: New format - MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT;ES;...
        mock_response.text = """MARGINALPDBC;2024;01;01;1;45,50;46,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;01;01;2;44,20;45,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;01;01;24;50,10;51,00;0;0;0;0;0;0;0;0"""
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_spot_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
                include_hourly=True,
            )

            assert len(result) == 3
            assert isinstance(result[0], OMIEElectricityPrice)
            assert result[0].price_eur_mwh == 45.50
            assert result[0].hour == 0  # OMIE uses 1-24, we convert to 0-23

    @pytest.mark.asyncio
    async def test_fetch_spot_prices_daily_average(self, client: OMIEClient) -> None:
        """Test daily average price calculation.

        Story 6.9.2 AC3/AC5: Updated for new CSV format.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Story 6.9.2 AC3: New format with European decimal comma
        mock_response.text = """MARGINALPDBC;2024;01;01;1;40,00;41,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;01;01;2;50,00;51,00;0;0;0;0;0;0;0;0"""
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_spot_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
                include_hourly=False,
            )

            assert len(result) == 1
            assert result[0].price_eur_mwh == 45.00  # Average of 40 and 50
            assert result[0].price_type == "spot_daily_avg"

    @pytest.mark.asyncio
    async def test_fetch_spot_prices_404_handled(self, client: OMIEClient) -> None:
        """Test 404 (no data) is handled gracefully."""
        error_response = MagicMock()
        error_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=MagicMock(), response=error_response
                )
            )

            result = await client.fetch_spot_prices(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
            )

            # 404 should return empty list, not raise
            assert result == []

    def test_parse_daily_file(self, client: OMIEClient) -> None:
        """Test parsing OMIE daily file.

        Story 6.9.2 AC3/AC5: Updated for new CSV format.
        Format: MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT_PRICE;ES_PRICE;...
        """
        # Story 6.9.2 AC3: New format with MARGINALPDBC prefix
        content = """MARGINALPDBC;2024;01;01;1;45,50;46,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;01;01;2;44,20;45,00;0;0;0;0;0;0;0;0
INVALID;2024;01;01;3;bad;data"""

        result = client._parse_daily_file(content, date(2024, 1, 1))

        # Should parse 2 valid MARGINALPDBC rows (comma decimal separator handled)
        assert len(result) == 2
        assert result[0].hour == 0
        assert result[0].price_eur_mwh == 45.50
        assert result[1].hour == 1
        assert result[1].price_eur_mwh == 44.20


# =============================================================================
# EU Oil Bulletin Client Tests
# =============================================================================


class TestOMIEStory692:
    """Tests for OMIE client fixes (Story 6.9.2 AC1-AC6).

    Story 6.9.2 Changes:
    - AC1: Updated URL pattern to use file-download endpoint
    - AC2: Enabled follow_redirects=True
    - AC3: Updated CSV parser for new format (MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT;ES)
    - AC5: Unit tests updated for new format
    - AC6: Retry logic per NFR1 (exponential backoff 2s/4s/8s)
    """

    def test_new_url_pattern(self) -> None:
        """AC1: Verify new file-download URL pattern."""
        from raglite.external_data.clients.omie import OMIE_BASE_URL

        # New URL should use file-download endpoint
        assert "file-download" in OMIE_BASE_URL
        # Old URL pattern should NOT be present
        assert "/sites/default/files/dados" not in OMIE_BASE_URL
        assert "/AGNO_" not in OMIE_BASE_URL

    def test_url_includes_query_params(self) -> None:
        """AC1: Verify URL construction uses query params."""
        from raglite.external_data.clients.omie import OMIE_BASE_URL

        # URL should be the base for query params
        expected_base = "https://www.omie.es/es/file-download"
        assert OMIE_BASE_URL == expected_base

    def test_new_csv_format_parsing(self) -> None:
        """AC3: Verify parsing of MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT;ES format."""
        from datetime import date

        from raglite.external_data.clients.omie import OMIEClient

        client = OMIEClient()

        # New format: MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT_PRICE;ES_PRICE;...
        content = """MARGINALPDBC;2024;12;08;1;111,60;112,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;12;08;2;105,50;106,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;12;08;3;98,75;99,00;0;0;0;0;0;0;0;0"""

        result = client._parse_daily_file(content, date(2024, 12, 8))

        assert len(result) == 3
        assert result[0].price_eur_mwh == 111.60  # European decimal comma handled
        assert result[1].price_eur_mwh == 105.50
        assert result[2].price_eur_mwh == 98.75

    def test_hour_conversion_1_based_to_0_based(self) -> None:
        """AC3: Verify hour 1 in file becomes hour 0 in output."""
        from datetime import date

        from raglite.external_data.clients.omie import OMIEClient

        client = OMIEClient()

        # Hours in OMIE files are 1-24, we convert to 0-23
        content = """MARGINALPDBC;2024;12;08;1;100,00;100,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;12;08;12;150,00;150,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;12;08;24;80,00;80,00;0;0;0;0;0;0;0;0"""

        result = client._parse_daily_file(content, date(2024, 12, 8))

        assert result[0].hour == 0  # Hour 1 -> 0
        assert result[1].hour == 11  # Hour 12 -> 11
        assert result[2].hour == 23  # Hour 24 -> 23

    def test_decimal_comma_handling(self) -> None:
        """AC3: Verify prices like '111,60' are parsed correctly."""
        from datetime import date

        from raglite.external_data.clients.omie import OMIEClient

        client = OMIEClient()

        # European format with comma as decimal separator
        content = """MARGINALPDBC;2024;12;08;1;111,60;112,50;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;12;08;2;99,99;100,01;0;0;0;0;0;0;0;0"""

        result = client._parse_daily_file(content, date(2024, 12, 8))

        assert result[0].price_eur_mwh == 111.60
        assert result[1].price_eur_mwh == 99.99

    def test_malformed_line_handling(self) -> None:
        """AC3: Verify malformed lines are skipped with warning."""
        from datetime import date

        from raglite.external_data.clients.omie import OMIEClient

        client = OMIEClient()

        # Mix of valid and invalid lines
        content = """MARGINALPDBC;2024;12;08;1;100,00;100,00;0;0;0;0;0;0;0;0
INVALID_PREFIX;2024;12;08;2;50,00;50,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;12;08;3;short
MARGINALPDBC;2024;12;08;bad;100,00;100,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;12;08;4;150,00;150,00;0;0;0;0;0;0;0;0"""

        result = client._parse_daily_file(content, date(2024, 12, 8))

        # Only first and last lines should be parsed
        assert len(result) == 2
        assert result[0].hour == 0  # Hour 1
        assert result[1].hour == 3  # Hour 4

    def test_non_marginalpdbc_lines_skipped(self) -> None:
        """AC3: Verify non-MARGINALPDBC lines (headers, etc.) are skipped."""
        from datetime import date

        from raglite.external_data.clients.omie import OMIEClient

        client = OMIEClient()

        # Content with headers and comments
        content = """Header;Line;That;Should;Be;Skipped
MARGINALPDBC;2024;12;08;1;100,00;100,00;0;0;0;0;0;0;0;0
Some;Other;Data;Format
MARGINALPDBC;2024;12;08;2;110,00;110,00;0;0;0;0;0;0;0;0"""

        result = client._parse_daily_file(content, date(2024, 12, 8))

        # Only MARGINALPDBC lines should be parsed
        assert len(result) == 2

    def test_omie_retry_delays_exponential_backoff(self) -> None:
        """AC6: Verify retry logic uses exponential backoff (2s/4s/8s)."""
        import inspect

        from raglite.external_data.clients.omie import OMIEClient

        # Get the source of _fetch_daily_file method
        source = inspect.getsource(OMIEClient._fetch_daily_file)

        # Should have 2, 4, 8 second delays (NFR1 requirement)
        assert "retry_delays = [2, 4, 8]" in source


class TestOMIEClientAdditional:
    """Additional tests for OMIE client coverage.

    Story 6.9.2: Updated for new OMIE CSV format.
    """

    @pytest.fixture
    def client(self) -> OMIEClient:
        return OMIEClient()

    @pytest.mark.asyncio
    async def test_server_error_retry_then_fail(self, client: OMIEClient) -> None:
        """Test retry exhaustion on server errors."""
        error_response = MagicMock()
        error_response.status_code = 503

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Service Unavailable", request=MagicMock(), response=error_response
                )
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                # Should fail after retries but not raise (404 handling)
                result = await client.fetch_spot_prices(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 1),
                )
                # Non-404 errors are caught and logged, returns empty
                assert result == []

    @pytest.mark.asyncio
    async def test_monthly_average(self, client: OMIEClient) -> None:
        """Test monthly average calculation.

        Story 6.9.2 AC3/AC5: Updated for new CSV format.
        """
        mock_response = MagicMock()
        # Story 6.9.2 AC3: New format - MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT;ES;...
        mock_response.text = """MARGINALPDBC;2024;01;01;1;50,00;51,00;0;0;0;0;0;0;0;0
MARGINALPDBC;2024;01;01;2;60,00;61,00;0;0;0;0;0;0;0;0"""
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await client.fetch_monthly_average(2024, 1)

        assert result is not None
        assert result.price_type == "monthly_avg"
