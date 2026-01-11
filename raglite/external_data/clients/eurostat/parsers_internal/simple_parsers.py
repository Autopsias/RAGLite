"""Simple value-based parsers for Eurostat data.

Story 8.2 Task 6: Eurostat client refactoring
"""

from datetime import date

from raglite.external_data.clients.eurostat.utils import parse_eurostat_period
from raglite.external_data.models import (
    ECConstructionConfidence,
    EurostatBuildingPermits,
    EurostatElectricityPrice,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def parse_electricity_data(
    data: dict,
    country: str,
    consumption_band: str,
    tax_component: str,
    start_date: date | None,
    end_date: date | None,
) -> list[EurostatElectricityPrice]:
    """Parse Eurostat electricity price response.

    Args:
        data: JSON response from Eurostat
        country: Country code
        consumption_band: Consumption band code
        tax_component: Tax component (I_TAX or X_TAX)
        start_date: Filter start date
        end_date: Filter end date

    Returns:
        List of electricity price records
    """
    results: list[EurostatElectricityPrice] = []

    # Get values and time dimension
    values = data.get("value", {})
    dimensions = data.get("dimension", {})
    time_dim = dimensions.get("time", {}).get("category", {}).get("index", {})

    # Build index to period mapping
    period_by_index = {v: k for k, v in time_dim.items()}

    for idx_str, price in values.items():
        try:
            idx = int(idx_str)
            period = period_by_index.get(idx)

            if not period or price is None:
                continue

            # Parse period (YYYY-MM or YYYY-S1/S2)
            record_date = parse_eurostat_period(period)
            if record_date is None:
                continue

            # Apply date filters
            if start_date and record_date < start_date.replace(day=1):
                continue
            if end_date and record_date > end_date:
                continue

            results.append(
                EurostatElectricityPrice(
                    date=record_date,
                    price_eur_kwh=float(price),
                    country=country,
                    consumption_band=consumption_band,
                    tax_component=tax_component,
                )
            )

        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse Eurostat electricity record",
                extra={"index": idx_str, "error": str(e)},
            )
            continue

    # Sort by date
    results.sort(key=lambda x: x.date)

    logger.info(
        "Parsed Eurostat electricity prices",
        extra={"count": len(results)},
    )
    return results


def parse_building_permits_data(
    data: dict,
    country: str,
    building_type: str,
    start_date: date | None,
    end_date: date | None,
) -> list[EurostatBuildingPermits]:
    """Parse Eurostat building permits response."""
    results: list[EurostatBuildingPermits] = []

    # Get values and time dimension
    values = data.get("value", {})
    dimensions = data.get("dimension", {})
    time_dim = dimensions.get("time", {}).get("category", {}).get("index", {})

    # Build index to period mapping
    period_by_index = {v: k for k, v in time_dim.items()}

    for idx_str, permits_value in values.items():
        try:
            idx = int(idx_str)
            period = period_by_index.get(idx)

            if not period or permits_value is None:
                continue

            # Parse period (YYYY-MM)
            record_date = parse_eurostat_period(period)
            if record_date is None:
                continue

            # Apply date filters
            if start_date and record_date < start_date.replace(day=1):
                continue
            if end_date and record_date > end_date:
                continue

            results.append(
                EurostatBuildingPermits(
                    date=record_date,
                    permits_count=int(permits_value),
                    country=country,
                    building_type=building_type,
                )
            )

        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse Eurostat building permits record",
                extra={"index": idx_str, "error": str(e)},
            )
            continue

    # Sort by date
    results.sort(key=lambda x: x.date)

    logger.info(
        "Parsed Eurostat building permits",
        extra={"count": len(results)},
    )
    return results


def _build_period_data_for_confidence(
    time_index: dict,
    indic_index: dict,
    values: dict,
) -> dict[str, dict[str, float | None]]:
    """Build period-wise indicator data for construction confidence.

    Args:
        time_index: Mapping of period codes to position indices
        indic_index: Mapping of indicator codes to position indices
        values: Flat value array keyed by position

    Returns:
        Dictionary mapping periods to their indicator values
    """
    # Map indicator codes to indices
    cci_idx = indic_index.get("BS-CCI-BAL")
    employment_idx = indic_index.get("BS-CEME-BAL")
    order_books_idx = indic_index.get("BS-COB-BAL")

    if cci_idx is None:
        logger.warning("Construction confidence indicator (BS-CCI-BAL) not found")
        return {}

    time_count = len(time_index)
    period_data: dict[str, dict[str, float | None]] = {}

    for period, t_idx in time_index.items():
        period_data[period] = {
            "confidence_index": None,
            "employment_expectations": None,
            "order_books": None,
        }

        # Get confidence index
        if cci_idx is not None:
            pos = cci_idx * time_count + t_idx
            if str(pos) in values:
                period_data[period]["confidence_index"] = values[str(pos)]

        # Get employment expectations
        if employment_idx is not None:
            pos = employment_idx * time_count + t_idx
            if str(pos) in values:
                period_data[period]["employment_expectations"] = values[str(pos)]

        # Get order books
        if order_books_idx is not None:
            pos = order_books_idx * time_count + t_idx
            if str(pos) in values:
                period_data[period]["order_books"] = values[str(pos)]

    return period_data


def parse_construction_confidence_data(
    data: dict,
    country: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ECConstructionConfidence]:
    """Parse EC construction confidence JSON-stat response.

    The data is organized with a flat value dictionary indexed by position.
    Position = indic_index * time_count + time_index
    """
    results: list[ECConstructionConfidence] = []

    # Get dimensions
    dimensions = data.get("dimension", {})
    time_dim = dimensions.get("time", {}).get("category", {})
    indic_dim = dimensions.get("indic", {}).get("category", {})

    time_index = time_dim.get("index", {})
    indic_index = indic_dim.get("index", {})
    values = data.get("value", {})

    if not time_index or not values:
        logger.warning("No time periods or values in EC construction confidence response")
        return results

    # Build data by time period
    period_data = _build_period_data_for_confidence(time_index, indic_index, values)

    if not period_data:
        return results

    # Convert to records
    for period, indicators in period_data.items():
        if indicators["confidence_index"] is None:
            continue

        # Parse period (YYYY-MM)
        record_date = parse_eurostat_period(period)
        if record_date is None:
            continue

        # Apply date filters
        if start_date and record_date < start_date.replace(day=1):
            continue
        if end_date and record_date > end_date:
            continue

        results.append(
            ECConstructionConfidence(
                date=record_date,
                confidence_index=indicators["confidence_index"],
                employment_expectations=indicators["employment_expectations"],
                order_books=indicators["order_books"],
                country=country,
            )
        )

    # Sort by date
    results.sort(key=lambda x: x.date)

    logger.info(
        "Parsed EC construction confidence",
        extra={"count": len(results), "country": country},
    )
    return results
