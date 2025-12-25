"""Unit tests for ATIC (Cement Consumption) client.

Story 7.1: Split test_external_data_clients.py
This module contains tests for: TestATICClient, TestATICClientAdditional
"""

from __future__ import annotations

from datetime import date

import pytest

from raglite.external_data.clients.atic import ATICClient
from raglite.external_data.exceptions import (
    ExternalDataFetchError,
    ExternalDataValidationError,
)
from raglite.external_data.models import ATICCementConsumption


class TestATICClient:
    """Tests for ATIC cement consumption client."""

    @pytest.fixture
    def client(self) -> ATICClient:
        """Create ATIC client instance."""
        return ATICClient()

    def test_parse_csv_content_success(self, client: ATICClient) -> None:
        """Test successful CSV parsing."""
        csv_content = """date,consumption,region,type
2024-01-01,150000,Portugal,gray
2024-02-01,160000,Portugal,gray
2024-03-01,170000,Lisboa,white"""

        result = client.parse_csv_content(csv_content)

        assert len(result) == 3
        assert isinstance(result[0], ATICCementConsumption)
        assert result[0].consumption_tonnes == 150000
        assert result[0].region == "Portugal"
        assert result[2].region == "Lisboa"
        assert result[2].cement_type == "white"

    def test_parse_csv_content_alternate_columns(self, client: ATICClient) -> None:
        """Test CSV with alternate column names."""
        csv_content = """Data,Consumo,Regiao
2024-01-01,150000,Norte
2024-02-01,160000,Sul"""

        result = client.parse_csv_content(csv_content)

        assert len(result) == 2
        assert result[0].consumption_tonnes == 150000
        assert result[0].region == "Norte"

    def test_parse_csv_content_no_headers(self, client: ATICClient) -> None:
        """Test CSV validation error on missing headers."""
        csv_content = ""

        with pytest.raises(ExternalDataValidationError) as exc_info:
            client.parse_csv_content(csv_content)

        assert exc_info.value.source == "ATIC"
        assert "headers" in exc_info.value.message.lower()

    def test_parse_csv_content_missing_date_column(self, client: ATICClient) -> None:
        """Test validation error on missing date column."""
        csv_content = """value,region
150000,Portugal"""

        with pytest.raises(ExternalDataValidationError) as exc_info:
            client.parse_csv_content(csv_content)

        assert "date column" in exc_info.value.message.lower()

    def test_parse_csv_content_missing_value_column(self, client: ATICClient) -> None:
        """Test validation error on missing value column."""
        csv_content = """date,region
2024-01-01,Portugal"""

        with pytest.raises(ExternalDataValidationError) as exc_info:
            client.parse_csv_content(csv_content)

        assert "value" in exc_info.value.message.lower()

    def test_parse_csv_file_not_found(self, client: ATICClient) -> None:
        """Test error on missing file."""
        with pytest.raises(ExternalDataFetchError) as exc_info:
            client.parse_csv_file("/nonexistent/path.csv")

        assert exc_info.value.source == "ATIC"
        assert "not found" in exc_info.value.message.lower()

    def test_parse_date_formats(self, client: ATICClient) -> None:
        """Test parsing various date formats."""
        # Test different date formats
        assert client._parse_date("2024-01-15") == date(2024, 1, 15)
        assert client._parse_date("15/01/2024") == date(2024, 1, 15)
        assert client._parse_date("2024-01") == date(2024, 1, 1)
        assert client._parse_date("01/2024") == date(2024, 1, 1)
        assert client._parse_date("202401") == date(2024, 1, 1)
        assert client._parse_date("invalid") is None


# =============================================================================
# ATIC Client Additional Tests
# =============================================================================


class TestATICClientAdditional:
    """Additional tests for ATIC client coverage."""

    @pytest.fixture
    def client(self) -> ATICClient:
        return ATICClient()

    @pytest.mark.asyncio
    async def test_fetch_historical_no_csv(self, client: ATICClient) -> None:
        """Test historical fetch without CSV returns empty with warning."""
        result = await client.fetch_historical_data(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            csv_path=None,
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_historical_with_csv(self, client: ATICClient, tmp_path) -> None:
        """Test historical fetch with CSV and date filtering."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            """date,consumption,region
2024-01-01,100000,Portugal
2024-02-01,110000,Portugal
2024-06-01,120000,Portugal"""
        )

        result = await client.fetch_historical_data(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            csv_path=csv_file,
        )

        # Only 2 records in date range
        assert len(result) == 2
