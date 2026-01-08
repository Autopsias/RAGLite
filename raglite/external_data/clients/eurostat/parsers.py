"""Eurostat response parsers.

Story 8.2 Task 6: Eurostat client refactoring
"""

from datetime import date

from raglite.external_data.clients.eurostat.utils import parse_eurostat_period
from raglite.external_data.models import (
    ECConstructionConfidence,
    EurostatBuildingPermits,
    EurostatConstructionOutput,
    EurostatElectricityPrice,
    EurostatIndustrialProduction,
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


def _get_sdmx_dimension_indices(
    data: dict,
    country: str,
    nace_sector: str,
    seasonal_adjustment: str,
) -> tuple[int | None, int | None, int | None, int | None]:
    """Extract dimension indices from SDMX-JSON data.

    Args:
        data: JSON response from Eurostat
        country: Country code
        nace_sector: NACE sector code
        seasonal_adjustment: Seasonal adjustment type

    Returns:
        Tuple of (nace_idx, s_adj_idx, unit_idx, geo_idx) or None values if not found
    """
    dimensions = data.get("dimension", {})

    # Get dimension indices for our filters
    nace_indices = dimensions.get("nace_r2", {}).get("category", {}).get("index", {})
    s_adj_indices = dimensions.get("s_adj", {}).get("category", {}).get("index", {})
    unit_indices = dimensions.get("unit", {}).get("category", {}).get("index", {})
    geo_indices = dimensions.get("geo", {}).get("category", {}).get("index", {})

    # Get the dimension indices for our query
    nace_idx = nace_indices.get(nace_sector)
    s_adj_idx = s_adj_indices.get(seasonal_adjustment)
    unit_idx = unit_indices.get("I21")
    geo_idx = geo_indices.get(country)

    return nace_idx, s_adj_idx, unit_idx, geo_idx


def _calculate_sdmx_strides(size: list[int]) -> tuple[int, int, int, int, int]:
    """Calculate stride values for SDMX multi-dimensional indexing.

    Args:
        size: Array of dimension sizes

    Returns:
        Tuple of (time_stride, geo_stride, unit_stride, s_adj_stride, nace_stride)
    """
    time_stride = 1
    geo_stride = size[6]  # time
    unit_stride = size[6] * size[5]  # time * geo
    s_adj_stride = size[6] * size[5] * size[4]  # time * geo * unit
    nace_stride = size[6] * size[5] * size[4] * size[3]  # time * geo * unit * s_adj

    return time_stride, geo_stride, unit_stride, s_adj_stride, nace_stride


def _extract_sdmx_time_values(
    data: dict,
    values: dict,
    nace_idx: int,
    s_adj_idx: int,
    unit_idx: int,
    geo_idx: int,
    time_stride: int,
    geo_stride: int,
    unit_stride: int,
    s_adj_stride: int,
    nace_stride: int,
    start_date: date | None,
    end_date: date | None,
) -> list[tuple[date, float]]:
    """Extract time-series values from SDMX-JSON data using calculated indices.

    Args:
        data: JSON response from Eurostat
        values: Value dictionary from SDMX response
        nace_idx: NACE sector dimension index
        s_adj_idx: Seasonal adjustment dimension index
        unit_idx: Unit dimension index
        geo_idx: Geographic dimension index
        time_stride: Time dimension stride
        geo_stride: Geographic dimension stride
        unit_stride: Unit dimension stride
        s_adj_stride: Seasonal adjustment stride
        nace_stride: NACE sector stride
        start_date: Filter start date
        end_date: Filter end date

    Returns:
        List of (date, index_value) tuples
    """
    results: list[tuple[date, float]] = []

    # Get time dimension
    dimensions = data.get("dimension", {})
    time_dim = dimensions.get("time", {}).get("category", {}).get("index", {})
    period_by_index = {v: k for k, v in time_dim.items()}

    # For each time period, calculate the flat index
    for time_idx, period in period_by_index.items():
        # Calculate flat index assuming freq_idx=0, indic_bt_idx=0
        flat_idx = (
            nace_idx * nace_stride
            + s_adj_idx * s_adj_stride
            + unit_idx * unit_stride
            + geo_idx * geo_stride
            + time_idx * time_stride
        )

        idx_str = str(flat_idx)
        index_value = values.get(idx_str)

        if index_value is None:
            continue

        # Parse period
        record_date = parse_eurostat_period(period)
        if record_date is None:
            continue

        # Apply date filters
        if start_date and record_date < start_date.replace(day=1):
            continue
        if end_date and record_date > end_date:
            continue

        results.append((record_date, float(index_value)))

    return results


def parse_sdmx_index_data(
    data: dict,
    country: str,
    nace_sector: str,
    seasonal_adjustment: str,
    start_date: date | None,
    end_date: date | None,
) -> list[tuple[date, float]]:
    """Parse SDMX-JSON index data (common to construction and industrial production).

    Args:
        data: JSON response from Eurostat
        country: Country code
        nace_sector: NACE sector code
        seasonal_adjustment: Seasonal adjustment type
        start_date: Filter start date
        end_date: Filter end date

    Returns:
        List of (date, index_value) tuples
    """
    results: list[tuple[date, float]] = []

    # Get values and dimensions
    values = data.get("value", {})
    size = data.get("size", [])

    # Get dimension indices
    nace_idx, s_adj_idx, unit_idx, geo_idx = _get_sdmx_dimension_indices(
        data, country, nace_sector, seasonal_adjustment
    )

    if nace_idx is None or s_adj_idx is None or unit_idx is None or geo_idx is None:
        logger.warning(
            "Could not find dimension indices",
            extra={
                "nace": nace_sector,
                "s_adj": seasonal_adjustment,
                "country": country,
            },
        )
        return results

    # Calculate offset for multi-dimensional indexing
    # SDMX-JSON uses row-major order: index = sum(dim_index * product_of_following_dims)
    # Size array typically: [freq, indic_bt, nace_r2, s_adj, unit, geo, time]
    if len(size) >= 7:
        # Warn if dimension count differs from expected
        if len(size) != 7:
            logger.warning(
                "Unexpected dimension count in SDMX response",
                extra={"expected": 7, "actual": len(size)},
            )

        # Calculate stride for each dimension (product of all following dimensions)
        time_stride, geo_stride, unit_stride, s_adj_stride, nace_stride = (
            _calculate_sdmx_strides(size)
        )

        # Extract time-series values
        results = _extract_sdmx_time_values(
            data,
            values,
            nace_idx,
            s_adj_idx,
            unit_idx,
            geo_idx,
            time_stride,
            geo_stride,
            unit_stride,
            s_adj_stride,
            nace_stride,
            start_date,
            end_date,
        )

    return results


def parse_construction_data(
    data: dict,
    country: str,
    nace_sector: str,
    seasonal_adjustment: str,
    start_date: date | None,
    end_date: date | None,
) -> list[EurostatConstructionOutput]:
    """Parse Eurostat construction output response."""
    parsed_data = parse_sdmx_index_data(
        data, country, nace_sector, seasonal_adjustment, start_date, end_date
    )

    results = [
        EurostatConstructionOutput(
            date=record_date,
            index_value=index_value,
            country=country,
            nace_sector=nace_sector,
            seasonal_adjustment=seasonal_adjustment,
        )
        for record_date, index_value in parsed_data
    ]

    # Sort by date
    results.sort(key=lambda x: x.date)

    logger.info(
        "Parsed Eurostat construction output",
        extra={"count": len(results)},
    )
    return results


def parse_industrial_data(
    data: dict,
    country: str,
    nace_sector: str,
    seasonal_adjustment: str,
    start_date: date | None,
    end_date: date | None,
) -> list[EurostatIndustrialProduction]:
    """Parse Eurostat industrial production response."""
    parsed_data = parse_sdmx_index_data(
        data, country, nace_sector, seasonal_adjustment, start_date, end_date
    )

    results = [
        EurostatIndustrialProduction(
            date=record_date,
            index_value=index_value,
            country=country,
            nace_sector=nace_sector,
            seasonal_adjustment=seasonal_adjustment,
        )
        for record_date, index_value in parsed_data
    ]

    # Sort by date
    results.sort(key=lambda x: x.date)

    logger.info(
        "Parsed Eurostat industrial production",
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


def _build_confidence_period_data(
    time_index: dict,
    indic_index: dict,
    values: dict,
) -> dict[str, dict[str, float | None]]:
    """Build period-level data dictionary for construction confidence indicators.

    Args:
        time_index: Time period index mapping
        indic_index: Indicator index mapping
        values: Flat value dictionary from JSON-stat response

    Returns:
        Dictionary mapping period to indicator values
    """
    # Map indicator codes
    cci_idx = indic_index.get("BS-CCI-BAL")
    employment_idx = indic_index.get("BS-CEME-BAL")
    order_books_idx = indic_index.get("BS-COB-BAL")

    time_count = len(time_index)

    # Build data by time period
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

    # Get values
    values = data.get("value", {})

    if not time_index or not values:
        logger.warning("No time periods or values in EC construction confidence response")
        return results

    # Check for required confidence index
    cci_idx = indic_index.get("BS-CCI-BAL")
    if cci_idx is None:
        logger.warning("Construction confidence indicator (BS-CCI-BAL) not found")
        return results

    # Build period-level data
    period_data = _build_confidence_period_data(time_index, indic_index, values)

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
