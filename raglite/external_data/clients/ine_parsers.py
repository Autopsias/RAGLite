"""INE API response parsers.

Extracted from ine.py for better modularity (Story 8.3).
"""

from __future__ import annotations

import re
from datetime import date

from raglite.external_data.models import (
    INEBuildingPermits,
    INEConstructionConfidence,
    INEConstructionCostIndex,
    INEConstructionOutput,
    INEHousePriceIndex,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Portuguese month names for parsing API responses
MONTH_NAMES_PT = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}


def parse_period_to_date(period: str) -> date | None:
    """Parse INE period string to date.

    Handles multiple formats:
        - "Setembro de 2025" (Portuguese month name)
        - "202509" or "2025-09" (YYYYMM)
        - "2025" (year only)
        - "2024T1" or "2024T2" (quarterly format - Story 6.8)

    Args:
        period: Period string from INE API

    Returns:
        date object or None if parsing fails
    """
    # Try Portuguese month format: "Setembro de 2025"
    month_pattern = r"(\w+)\s+de\s+(\d{4})"
    match = re.match(month_pattern, period)
    if match:
        month_name, year_str = match.groups()
        month = MONTH_NAMES_PT.get(month_name)
        if month:
            return date(int(year_str), month, 1)

    # Story 6.8: Try quarterly format: "2024T1", "2024T2", etc.
    quarterly_pattern = r"(\d{4})T([1-4])"
    match = re.match(quarterly_pattern, period)
    if match:
        year_str, quarter_str = match.groups()
        quarter = int(quarter_str)
        # Q1 = Jan, Q2 = Apr, Q3 = Jul, Q4 = Oct
        month = (quarter - 1) * 3 + 1
        return date(int(year_str), month, 1)

    # Try YYYYMM format: "202509"
    if len(period) == 6 and period.isdigit():
        try:
            return date(int(period[:4]), int(period[4:6]), 1)
        except ValueError:
            pass

    # Try year only format: "2025"
    if len(period) == 4 and period.isdigit():
        try:
            return date(int(period), 1, 1)
        except ValueError:
            pass

    return None


def parse_building_permits(
    data: dict, start_date: date | None = None, end_date: date | None = None
) -> list[INEBuildingPermits]:
    """Parse INE building permits response.

    Args:
        data: Raw JSON response from INE API
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        List of building permit records within date range
    """
    results = []
    records = data.get("Dados", {})

    for period, values in records.items():
        try:
            # Parse period using flexible parser
            record_date = parse_period_to_date(period)
            if record_date is None:
                logger.debug(f"Skipping unparseable period: {period}")
                continue

            # Apply date range filter
            # Use first-of-month comparison for monthly data (Story 6.9.1 AC1)
            # Monthly periods like "Setembro de 2025" parse to 2025-09-01
            # Without this fix, start_date=2025-09-15 would exclude September data
            if start_date and record_date < start_date.replace(day=1):
                continue
            if end_date and record_date > end_date:
                continue

            for value_data in values if isinstance(values, list) else [values]:
                if isinstance(value_data, dict):
                    value = value_data.get("valor")
                    region = str(value_data.get("geodsg", value_data.get("geocod", "Portugal")))
                else:
                    value = value_data
                    region = "Portugal"

                if value is not None:
                    results.append(
                        INEBuildingPermits(
                            date=record_date,
                            permits_count=int(float(value)),
                            region=region,
                        )
                    )
        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse INE building permit record",
                extra={"period": period, "error": str(e)},
            )
            continue

    logger.info(
        "Parsed INE building permits",
        extra={"record_count": len(results)},
    )
    return results


def parse_construction_output(
    data: dict, start_date: date | None = None, end_date: date | None = None
) -> list[INEConstructionOutput]:
    """Parse INE construction output response.

    Args:
        data: Raw JSON response from INE API
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        List of construction output records within date range
    """
    results = []
    records = data.get("Dados", {})

    for period, values in records.items():
        try:
            # Parse period using flexible parser
            record_date = parse_period_to_date(period)
            if record_date is None:
                logger.debug(f"Skipping unparseable period: {period}")
                continue

            # Apply date range filter
            # Use first-of-month comparison for monthly data (Story 6.9.1 AC1)
            if start_date and record_date < start_date.replace(day=1):
                continue
            if end_date and record_date > end_date:
                continue

            for value_data in values if isinstance(values, list) else [values]:
                if isinstance(value_data, dict):
                    value = value_data.get("valor")
                    # Filter for Total only (dim_3_t == "Total")
                    dim3_type = value_data.get("dim_3_t", "")
                    if dim3_type and dim3_type != "Total":
                        continue
                else:
                    value = value_data

                if value is not None:
                    results.append(
                        INEConstructionOutput(
                            date=record_date,
                            index_value=float(value),
                            yoy_change_pct=None,  # YoY is the value itself for this indicator
                        )
                    )
        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse INE construction output record",
                extra={"period": period, "error": str(e)},
            )
            continue

    logger.info(
        "Parsed INE construction output",
        extra={"record_count": len(results)},
    )
    return results


def parse_construction_cost_index(
    data: dict, start_date: date | None = None, end_date: date | None = None
) -> list[INEConstructionCostIndex]:
    """Parse INE construction cost index response.

    Args:
        data: Raw JSON response from INE API
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        List of construction cost index records within date range
    """
    results = []
    records = data.get("Dados", {})

    # Collect values by period to group Total, Materials, Labor
    period_data: dict[date, dict[str, float]] = {}

    for period, values in records.items():
        try:
            # Parse period using flexible parser
            record_date = parse_period_to_date(period)
            if record_date is None:
                logger.debug(f"Skipping unparseable period: {period}")
                continue

            # Apply date range filter
            # Use first-of-month comparison for monthly data (Story 6.9.1 AC1)
            if start_date and record_date < start_date.replace(day=1):
                continue
            if end_date and record_date > end_date:
                continue

            if record_date not in period_data:
                period_data[record_date] = {}

            for value_data in values if isinstance(values, list) else [values]:
                if isinstance(value_data, dict):
                    value = value_data.get("valor")
                    factor_type = value_data.get("dim_3_t", "Total")

                    if value is not None:
                        if factor_type == "Total":
                            period_data[record_date]["total"] = float(value)
                        elif factor_type == "Materiais":
                            period_data[record_date]["materials"] = float(value)
                        elif "Mão" in factor_type or "obra" in factor_type.lower():
                            period_data[record_date]["labor"] = float(value)
                else:
                    if value_data is not None:
                        period_data[record_date]["total"] = float(value_data)

        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse INE construction cost record",
                extra={"period": period, "error": str(e)},
            )
            continue

    # Convert grouped data to results
    for record_date, values in sorted(period_data.items()):
        if "total" in values:
            results.append(
                INEConstructionCostIndex(
                    date=record_date,
                    total_index=values["total"],
                    materials_index=values.get("materials"),
                    labor_index=values.get("labor"),
                )
            )

    logger.info(
        "Parsed INE construction cost index",
        extra={"record_count": len(results)},
    )
    return results


def parse_house_price_index(
    data: dict, start_date: date | None = None, end_date: date | None = None
) -> list[INEHousePriceIndex]:
    """Parse INE house price index response.

    Args:
        data: Raw JSON response from INE API
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        List of house price index records within date range
    """
    results = []
    records = data.get("Dados", {})

    for period, values in records.items():
        try:
            # Parse period using flexible parser
            record_date = parse_period_to_date(period)
            if record_date is None:
                logger.debug(f"Skipping unparseable period: {period}")
                continue

            # Apply date range filter
            if start_date and record_date < start_date.replace(day=1):
                continue
            if end_date and record_date > end_date:
                continue

            for value_data in values if isinstance(values, list) else [values]:
                if isinstance(value_data, dict):
                    value = value_data.get("valor")
                    region = str(value_data.get("geodsg", value_data.get("geocod", "Portugal")))
                else:
                    value = value_data
                    region = "Portugal"

                if value is not None:
                    results.append(
                        INEHousePriceIndex(
                            date=record_date,
                            index_value=float(value),
                            yoy_change_pct=None,  # Calculated separately if needed
                            region=region,
                        )
                    )
        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse INE house price index record",
                extra={"period": period, "error": str(e)},
            )
            continue

    logger.info(
        "Parsed INE house price index",
        extra={"record_count": len(results)},
    )
    return results


def parse_construction_confidence(
    data: dict, start_date: date | None = None, end_date: date | None = None
) -> list[INEConstructionConfidence]:
    """Parse INE construction confidence response.

    Args:
        data: Raw JSON response from INE API
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        List of construction confidence records within date range
    """
    results = []
    records = data.get("Dados", {})

    for period, values in records.items():
        try:
            # Parse period using flexible parser
            record_date = parse_period_to_date(period)
            if record_date is None:
                logger.debug(f"Skipping unparseable period: {period}")
                continue

            # Apply date range filter
            if start_date and record_date < start_date.replace(day=1):
                continue
            if end_date and record_date > end_date:
                continue

            for value_data in values if isinstance(values, list) else [values]:
                if isinstance(value_data, dict):
                    value = value_data.get("valor")
                    region = str(value_data.get("geodsg", value_data.get("geocod", "Portugal")))
                else:
                    value = value_data
                    region = "Portugal"

                if value is not None:
                    results.append(
                        INEConstructionConfidence(
                            date=record_date,
                            confidence_index=float(value),
                            region=region,
                        )
                    )
        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse INE construction confidence record",
                extra={"period": period, "error": str(e)},
            )
            continue

    logger.info(
        "Parsed INE construction confidence",
        extra={"record_count": len(results)},
    )
    return results
