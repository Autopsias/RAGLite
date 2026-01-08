"""SDMX-JSON parsers for Eurostat data.

Story 8.2 Task 6: Eurostat client refactoring
"""

from datetime import date

from raglite.external_data.clients.eurostat.utils import parse_eurostat_period
from raglite.external_data.models import (
    EurostatConstructionOutput,
    EurostatIndustrialProduction,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def _extract_dimension_indices(
    data: dict,
    country: str,
    nace_sector: str,
    seasonal_adjustment: str,
) -> tuple[int, int, int, int] | None:
    """Extract dimension indices from SDMX-JSON data.

    Args:
        data: JSON response from Eurostat
        country: Country code
        nace_sector: NACE sector code
        seasonal_adjustment: Seasonal adjustment type

    Returns:
        Tuple of (nace_idx, s_adj_idx, unit_idx, geo_idx) or None if any missing
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

    if nace_idx is None or s_adj_idx is None or unit_idx is None or geo_idx is None:
        logger.warning(
            "Could not find dimension indices",
            extra={
                "nace": nace_sector,
                "s_adj": seasonal_adjustment,
                "country": country,
            },
        )
        return None

    return nace_idx, s_adj_idx, unit_idx, geo_idx


def _calculate_sdmx_strides(size: list[int]) -> tuple[int, int, int, int, int]:
    """Calculate stride values for SDMX multi-dimensional indexing.

    SDMX-JSON uses row-major order: index = sum(dim_index * product_of_following_dims)
    Size array typically: [freq, indic_bt, nace_r2, s_adj, unit, geo, time]

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


def _process_time_periods(
    values: dict,
    period_by_index: dict,
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
    """Process time periods and extract filtered data points.

    Args:
        values: SDMX value dictionary
        period_by_index: Mapping from time index to period string
        nace_idx: NACE dimension index
        s_adj_idx: Seasonal adjustment dimension index
        unit_idx: Unit dimension index
        geo_idx: Geographic dimension index
        time_stride: Time dimension stride
        geo_stride: Geographic dimension stride
        unit_stride: Unit dimension stride
        s_adj_stride: Seasonal adjustment stride
        nace_stride: NACE dimension stride
        start_date: Filter start date
        end_date: Filter end date

    Returns:
        List of (date, index_value) tuples
    """
    results: list[tuple[date, float]] = []

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
    dimensions = data.get("dimension", {})
    size = data.get("size", [])

    # Get time dimension
    time_dim = dimensions.get("time", {}).get("category", {}).get("index", {})
    period_by_index = {v: k for k, v in time_dim.items()}

    # Extract dimension indices
    dimension_indices = _extract_dimension_indices(data, country, nace_sector, seasonal_adjustment)
    if dimension_indices is None:
        return results

    nace_idx, s_adj_idx, unit_idx, geo_idx = dimension_indices

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
        time_stride, geo_stride, unit_stride, s_adj_stride, nace_stride = _calculate_sdmx_strides(
            size
        )

        # Process time periods
        results = _process_time_periods(
            values=values,
            period_by_index=period_by_index,
            nace_idx=nace_idx,
            s_adj_idx=s_adj_idx,
            unit_idx=unit_idx,
            geo_idx=geo_idx,
            time_stride=time_stride,
            geo_stride=geo_stride,
            unit_stride=unit_stride,
            s_adj_stride=s_adj_stride,
            nace_stride=nace_stride,
            start_date=start_date,
            end_date=end_date,
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
