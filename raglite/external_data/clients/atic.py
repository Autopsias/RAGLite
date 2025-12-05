"""ATIC (Associação Técnica da Indústria de Cimento) client.

Story 6.1: Tier 1 External Data Source Integration

Handles cement consumption data from ATIC.
Note: ATIC does not provide a public API - data is obtained via CSV upload.

This client provides:
- CSV file parsing for cement consumption data
- Data validation using Pydantic models
- Caching support for imported data
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

from raglite.external_data.exceptions import (
    ExternalDataFetchError,
    ExternalDataValidationError,
)
from raglite.external_data.models import ATICCementConsumption
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class ATICClient:
    """Client for ATIC cement consumption data.

    ATIC (Associação Técnica da Indústria de Cimento) provides cement
    consumption statistics for Portugal. Data is obtained via CSV upload
    rather than API calls.

    Example:
        >>> client = ATICClient()
        >>> records = client.parse_csv_file("/path/to/atic_data.csv")
        >>> # Or from string content:
        >>> records = client.parse_csv_content(csv_string)
    """

    # Expected CSV column mappings
    DATE_COLUMNS = ["data", "date", "periodo", "period", "mes", "month"]
    VALUE_COLUMNS = ["consumo", "consumption", "valor", "value", "tonnes", "toneladas"]
    REGION_COLUMNS = ["regiao", "region", "zona", "area"]
    TYPE_COLUMNS = ["tipo", "type", "cement_type", "tipo_cimento"]

    def __init__(self) -> None:
        """Initialize ATIC client."""
        pass

    def parse_csv_file(self, file_path: str | Path) -> list[ATICCementConsumption]:
        """Parse cement consumption data from CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            List of cement consumption records

        Raises:
            ExternalDataFetchError: If file cannot be read
            ExternalDataValidationError: If CSV format is invalid
        """
        path = Path(file_path)

        if not path.exists():
            raise ExternalDataFetchError(
                source="ATIC",
                message=f"CSV file not found: {file_path}",
            )

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            raise ExternalDataFetchError(
                source="ATIC",
                message=f"Failed to read CSV file: {e}",
                original_error=e,
            ) from e

        return self.parse_csv_content(content)

    def parse_csv_content(self, content: str) -> list[ATICCementConsumption]:
        """Parse cement consumption data from CSV string.

        Args:
            content: CSV content as string

        Returns:
            List of cement consumption records

        Raises:
            ExternalDataValidationError: If CSV format is invalid
        """
        logger.info("Parsing ATIC CSV content")

        results = []
        reader = csv.DictReader(io.StringIO(content))

        if not reader.fieldnames:
            raise ExternalDataValidationError(
                source="ATIC",
                message="CSV file has no headers",
            )

        # Map columns to expected names (case-insensitive)
        field_map = self._map_columns(reader.fieldnames)

        if "date" not in field_map:
            raise ExternalDataValidationError(
                source="ATIC",
                message=f"Missing date column. Found: {reader.fieldnames}",
            )

        if "value" not in field_map:
            raise ExternalDataValidationError(
                source="ATIC",
                message=f"Missing consumption value column. Found: {reader.fieldnames}",
            )

        for row_num, row in enumerate(reader, start=2):
            try:
                record = self._parse_row(row, field_map)
                if record:
                    results.append(record)
            except Exception as e:
                logger.warning(
                    "Failed to parse ATIC CSV row",
                    extra={"row": row_num, "error": str(e)},
                )
                continue

        logger.info(
            "Parsed ATIC CSV content",
            extra={"record_count": len(results)},
        )
        return results

    def _map_columns(self, fieldnames: list[str]) -> dict[str, str]:
        """Map CSV column names to standard names.

        Args:
            fieldnames: CSV column headers

        Returns:
            Mapping of standard names to actual column names
        """
        field_map = {}
        lower_fields = {f.lower().strip(): f for f in fieldnames}

        for col in self.DATE_COLUMNS:
            if col.lower() in lower_fields:
                field_map["date"] = lower_fields[col.lower()]
                break

        for col in self.VALUE_COLUMNS:
            if col.lower() in lower_fields:
                field_map["value"] = lower_fields[col.lower()]
                break

        for col in self.REGION_COLUMNS:
            if col.lower() in lower_fields:
                field_map["region"] = lower_fields[col.lower()]
                break

        for col in self.TYPE_COLUMNS:
            if col.lower() in lower_fields:
                field_map["type"] = lower_fields[col.lower()]
                break

        return field_map

    def _parse_row(
        self,
        row: dict[str, str],
        field_map: dict[str, str],
    ) -> ATICCementConsumption | None:
        """Parse a single CSV row.

        Args:
            row: CSV row as dict
            field_map: Column name mapping

        Returns:
            Cement consumption record or None if parsing fails
        """
        date_str = row.get(field_map["date"], "").strip()
        value_str = row.get(field_map["value"], "").strip()

        if not date_str or not value_str:
            return None

        # Parse date (support multiple formats)
        record_date = self._parse_date(date_str)
        if not record_date:
            return None

        # Parse consumption value
        try:
            # Remove thousands separators and convert
            value_clean = value_str.replace(",", "").replace(" ", "")
            consumption = float(value_clean)
        except ValueError:
            return None

        # Optional fields
        region = row.get(field_map.get("region", ""), "Portugal") or "Portugal"
        cement_type = row.get(field_map.get("type", ""), None) or None

        return ATICCementConsumption(
            date=record_date,
            consumption_tonnes=consumption,
            region=region,
            cement_type=cement_type,
        )

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date from various formats.

        Supports:
        - YYYY-MM-DD
        - DD/MM/YYYY
        - MM/YYYY
        - YYYY-MM
        - YYYYMM

        Args:
            date_str: Date string

        Returns:
            Parsed date or None
        """
        from datetime import datetime

        # List of formats to try
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%Y",
            "%Y-%m",
            "%Y%m",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.date()
            except ValueError:
                continue

        return None

    async def fetch_historical_data(
        self,
        start_date: date,
        end_date: date,
        csv_path: str | Path | None = None,
    ) -> list[ATICCementConsumption]:
        """Fetch historical cement consumption data.

        Since ATIC doesn't have an API, this method reads from a local CSV file.
        If csv_path is not provided, returns empty list with a warning.

        Args:
            start_date: Start of date range (for filtering)
            end_date: End of date range (for filtering)
            csv_path: Path to CSV file with ATIC data

        Returns:
            List of cement consumption records within date range
        """
        if csv_path is None:
            logger.warning(
                "ATIC data requires CSV upload - no API available",
                extra={"start": str(start_date), "end": str(end_date)},
            )
            return []

        all_records = self.parse_csv_file(csv_path)

        # Filter by date range
        filtered = [r for r in all_records if start_date <= r.date <= end_date]

        logger.info(
            "Filtered ATIC historical data",
            extra={
                "total_records": len(all_records),
                "filtered_records": len(filtered),
                "start": str(start_date),
                "end": str(end_date),
            },
        )

        return filtered
