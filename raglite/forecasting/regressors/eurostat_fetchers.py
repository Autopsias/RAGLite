"""Eurostat regressor fetchers.

Eurostat (European Union statistics office) data providers.
"""

from datetime import date

import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def fetch_eurostat_electricity(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch industrial electricity price from Eurostat.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.eurostat import EurostatClient

    client_eurostat: EurostatClient = EurostatClient()
    electricity_data = await client_eurostat.fetch_electricity_prices(
        start_date=start_date, end_date=end_date
    )
    if electricity_data:
        series = pd.Series(
            [d.price_eur_kwh for d in electricity_data],
            index=pd.DatetimeIndex([d.date for d in electricity_data]),
        )
        series = series.groupby(level=0).mean()
        return series

    return None


async def fetch_construction_output(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch construction output index from Eurostat.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.eurostat import EurostatClient

    client_eurostat_constr: EurostatClient = EurostatClient()
    construction_data = await client_eurostat_constr.fetch_construction_output(
        start_date=start_date, end_date=end_date
    )
    if construction_data:
        series = pd.Series(
            [d.index_value for d in construction_data],
            index=pd.DatetimeIndex([d.date for d in construction_data]),
        )
        series = series.groupby(level=0).mean()
        return series

    return None


async def fetch_industrial_production(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch industrial production index from Eurostat.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.eurostat import EurostatClient

    client_eurostat_ind: EurostatClient = EurostatClient()
    industrial_data = await client_eurostat_ind.fetch_industrial_production(
        start_date=start_date, end_date=end_date
    )
    if industrial_data:
        series = pd.Series(
            [d.index_value for d in industrial_data],
            index=pd.DatetimeIndex([d.date for d in industrial_data]),
        )
        series = series.groupby(level=0).mean()
        return series

    return None


async def fetch_eurostat_building_permits(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch building permits from Eurostat (fallback from INE).

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.eurostat import EurostatClient

    try:
        client_eurostat = EurostatClient()
        eurostat_data = await client_eurostat.fetch_building_permits(
            country="PT", start_date=start_date, end_date=end_date
        )

        if eurostat_data:
            series = pd.Series(
                [d.permits_count for d in eurostat_data],
                index=pd.DatetimeIndex([d.date for d in eurostat_data]),
            )
            series = series.groupby(level=0).sum()
            logger.info(
                "Fetched building permits regressor",
                extra={"source": "Eurostat (fallback)", "data_points": len(series)},
            )
            return series
    except Exception as e:
        logger.warning(f"Eurostat building permits fallback failed: {e}")

    return None


async def fetch_construction_confidence(
    start_date: date,
    end_date: date,
) -> pd.Series | None:
    """Fetch construction confidence indicator from Eurostat.

    Story 6.19: EC Construction Confidence via Eurostat.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        pandas Series with datetime index, or None if fetch fails
    """
    from raglite.external_data.clients.eurostat import EurostatClient

    client_eurostat = EurostatClient()
    confidence_data = await client_eurostat.fetch_construction_confidence(
        country="PT", start_date=start_date, end_date=end_date
    )

    if confidence_data:
        series = pd.Series(
            [d.confidence_index for d in confidence_data],
            index=pd.DatetimeIndex([d.date for d in confidence_data]),
        )
        series = series.groupby(level=0).mean()
        logger.info(
            "Fetched construction confidence regressor",
            extra={"source": "Eurostat (EC)", "data_points": len(series)},
        )
        return series

    return None
