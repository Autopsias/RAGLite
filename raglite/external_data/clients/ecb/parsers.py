"""ECB response parsers.

Story 8.2 Task 5: ECB client refactoring
"""

import csv
from datetime import date
from io import StringIO

from raglite.external_data.clients.ecb.models import ECBGDPGrowth, ECBInflation, EuriborRate
from raglite.external_data.clients.ecb.utils import parse_ecb_period
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def parse_euribor_csv(csv_data: str, tenor: str) -> list[EuriborRate]:
    """Parse ECB SDMX CSV response for EURIBOR data.

    Args:
        csv_data: CSV string from ECB API
        tenor: EURIBOR tenor

    Returns:
        List of EURIBOR rate records
    """
    results: list[EuriborRate] = []

    reader = csv.DictReader(StringIO(csv_data))

    for row in reader:
        try:
            # TIME_PERIOD format: "2020-01"
            period = row.get("TIME_PERIOD", "")
            if not period or len(period) < 7:
                continue

            year, month = int(period[:4]), int(period[5:7])
            record_date = date(year, month, 1)

            # OBS_VALUE is the interest rate (can be negative)
            rate_str = row.get("OBS_VALUE", "")
            if not rate_str:
                continue

            rate = float(rate_str)

            results.append(
                EuriborRate(
                    date=record_date,
                    rate_pct=rate,
                    tenor=tenor,
                )
            )

        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse ECB row",
                extra={"row": str(row)[:100], "error": str(e)},
            )
            continue

    logger.info(
        "Parsed ECB EURIBOR rates",
        extra={"record_count": len(results), "tenor": tenor},
    )

    return results


def parse_gdp_csv(csv_data: str, country: str) -> list[ECBGDPGrowth]:
    """Parse ECB SDMX CSV response for GDP growth data.

    Story 6.17 AC4: Unit tests for GDP parsing.

    Args:
        csv_data: CSV string from ECB API
        country: Country code for the results

    Returns:
        List of GDP growth records
    """
    results: list[ECBGDPGrowth] = []

    reader = csv.DictReader(StringIO(csv_data))

    for row in reader:
        try:
            # TIME_PERIOD format: "2024-Q1"
            period = row.get("TIME_PERIOD", "")
            if not period:
                continue

            record_date = parse_ecb_period(period)

            # OBS_VALUE is the YoY growth rate
            growth_str = row.get("OBS_VALUE", "")
            if not growth_str:
                continue

            growth_pct = float(growth_str)

            results.append(
                ECBGDPGrowth(
                    date=record_date,
                    growth_pct=growth_pct,
                    country=country,
                    frequency="Q",
                )
            )

        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse ECB GDP row",
                extra={"row": str(row)[:100], "error": str(e)},
            )
            continue

    logger.info(
        "Parsed ECB GDP growth rates",
        extra={"record_count": len(results), "country": country},
    )

    return results


def parse_hicp_csv(csv_data: str, country: str) -> list[ECBInflation]:
    """Parse ECB SDMX CSV response for HICP inflation data.

    Story 6.17 AC4: Unit tests for HICP parsing.

    Calculates YoY change when 12 months of historical data is available.

    Args:
        csv_data: CSV string from ECB API
        country: Country code for the results

    Returns:
        List of HICP inflation records
    """
    results: list[ECBInflation] = []
    index_by_month: dict[tuple[int, int], float] = {}

    reader = csv.DictReader(StringIO(csv_data))

    for row in reader:
        try:
            # TIME_PERIOD format: "2024-01"
            period = row.get("TIME_PERIOD", "")
            if not period:
                continue

            record_date = parse_ecb_period(period)

            # OBS_VALUE is the HICP index value
            index_str = row.get("OBS_VALUE", "")
            if not index_str:
                continue

            index_value = float(index_str)

            # Store for YoY calculation
            index_by_month[(record_date.year, record_date.month)] = index_value

            results.append(
                ECBInflation(
                    date=record_date,
                    index_value=index_value,
                    country=country,
                    yoy_change_pct=None,  # Will calculate after collecting all data
                )
            )

        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse ECB HICP row",
                extra={"row": str(row)[:100], "error": str(e)},
            )
            continue

    # Calculate YoY change for each record
    for record in results:
        prior_year = record.date.year - 1
        prior_month = record.date.month
        prior_key = (prior_year, prior_month)

        if prior_key in index_by_month:
            prior_value = index_by_month[prior_key]
            if prior_value > 0:
                yoy_change = ((record.index_value - prior_value) / prior_value) * 100
                record.yoy_change_pct = round(yoy_change, 2)

    logger.info(
        "Parsed ECB HICP inflation",
        extra={"record_count": len(results), "country": country},
    )

    return results


def convert_eurostat_json_to_ecb_format(eurostat_json: dict) -> str:
    """Convert Eurostat JSON GDP index to YoY growth rates in ECB CSV format.

    Story 6.24: Transform Eurostat JSON response to ECB growth rate format.

    Eurostat provides chain-linked volume index (2010=100), which we convert
    to year-on-year percentage change to match ECB's growth_pct format.

    Args:
        eurostat_json: JSON dict from Eurostat API (index values)

    Returns:
        CSV string in ECB-compatible format (YoY % growth)
    """
    # Extract time period mapping and values from JSON
    try:
        time_index = (
            eurostat_json.get("dimension", {}).get("time", {}).get("category", {}).get("index", {})
        )
        values = eurostat_json.get("value", {})
    except (AttributeError, KeyError):
        logger.warning("Invalid Eurostat JSON structure")
        return "TIME_PERIOD,OBS_VALUE\n"

    if not time_index or not values:
        logger.warning("Empty Eurostat GDP response")
        return "TIME_PERIOD,OBS_VALUE\n"

    # Build index lookup: {quarter: index_value}
    # time_index: {"2020-Q1": 0, "2020-Q2": 1, ...}
    # values: {"0": 103.054, "1": 87.549, ...}
    index_by_quarter: dict[str, float] = {}
    for quarter, idx in time_index.items():
        value = values.get(str(idx))
        if value is not None:
            try:
                index_by_quarter[quarter] = float(value)
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid Eurostat index value",
                    extra={"time_period": quarter, "value": value},
                )
                continue

    # Calculate YoY percentage change
    ecb_rows = []
    sorted_quarters = sorted(index_by_quarter.keys())

    for quarter in sorted_quarters:
        # Parse year and quarter: "2024-Q1" -> year=2024, q=1
        try:
            year = int(quarter[:4])
            q = int(quarter[-1])
        except (ValueError, IndexError):
            continue

        # Calculate previous year same quarter: "2024-Q1" -> "2023-Q1"
        prev_year_quarter = f"{year - 1}-Q{q}"

        if prev_year_quarter in index_by_quarter:
            current_index = index_by_quarter[quarter]
            prev_index = index_by_quarter[prev_year_quarter]

            if prev_index > 0:
                # YoY % change = ((current - previous) / previous) * 100
                yoy_growth = ((current_index - prev_index) / prev_index) * 100
                ecb_rows.append({"TIME_PERIOD": quarter, "OBS_VALUE": f"{yoy_growth:.2f}"})

    # Write ECB-compatible CSV
    output = StringIO()
    if ecb_rows:
        writer = csv.DictWriter(output, fieldnames=["TIME_PERIOD", "OBS_VALUE"])
        writer.writeheader()
        writer.writerows(ecb_rows)

    result = output.getvalue()

    logger.info(
        "Converted Eurostat GDP index to YoY growth",
        extra={
            "eurostat_index_points": len(index_by_quarter),
            "calculated_growth_points": len(ecb_rows),
        },
    )

    return result
