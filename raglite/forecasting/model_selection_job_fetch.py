"""
Data fetching functions for model selection job.

This module provides functions to fetch historical time series data
for different variable types (internal, external_db, external_api).
"""

import logging

import pandas as pd

from raglite.forecasting.model_selection_job_config import VARIABLE_CONFIG
from raglite.forecasting.timeseries import (
    extract_external_regressor_timeseries,
    extract_external_timeseries,
    extract_timeseries_from_sql,
)

logger = logging.getLogger(__name__)


async def fetch_historical_data(var_name: str, min_points: int = 12) -> pd.Series | None:
    """Fetch historical time series data for a variable.

    Args:
        var_name: Variable name from VARIABLE_CONFIG
        min_points: Minimum data points required

    Returns:
        pandas Series with DatetimeIndex, or None if insufficient data
    """
    config = VARIABLE_CONFIG.get(var_name)
    if not config:
        logger.warning(f"Unknown variable: {var_name}")
        return None

    try:
        var_type = config["type"]

        if var_type == "internal":
            # Extract from SECIL financial_tables
            for alias in config["aliases"]:
                try:
                    ts_data = await extract_timeseries_from_sql(
                        metric=alias,
                        min_points=min_points,
                        aggregation=config.get("aggregation", "sum"),
                    )
                    if ts_data and len(ts_data.points) >= min_points:
                        # Convert to pandas Series
                        dates = [p.date for p in ts_data.points]
                        values = [p.value for p in ts_data.points]
                        series = pd.Series(values, index=pd.DatetimeIndex(dates))
                        series.name = var_name
                        return series.sort_index()
                except Exception as e:
                    logger.debug(f"Alias {alias} failed: {e}")
                    continue
            logger.warning(f"No data found for internal variable {var_name}")
            return None

        elif var_type == "external_db":
            # Extract from external_data_points table
            ext_ts_data = await extract_external_timeseries(
                metric=config["metric_name"],
                min_points=min_points,
            )
            if ext_ts_data and len(ext_ts_data.points) >= min_points:
                dates = [p.date for p in ext_ts_data.points]
                values = [p.value for p in ext_ts_data.points]
                series = pd.Series(values, index=pd.DatetimeIndex(dates))
                series.name = var_name
                return series.sort_index()
            return None

        elif var_type == "external_api":
            # Extract via regressor fetch (API-backed)
            api_ts_data = await extract_external_regressor_timeseries(
                metric=config["metric_name"],
                min_points=min_points,
            )
            if api_ts_data and len(api_ts_data.points) >= min_points:
                dates = [p.date for p in api_ts_data.points]
                values = [p.value for p in api_ts_data.points]
                series = pd.Series(values, index=pd.DatetimeIndex(dates))
                series.name = var_name
                return series.sort_index()
            return None

        else:
            logger.warning(f"Unknown variable type: {var_type}")
            return None

    except Exception as e:
        logger.error(f"Error fetching data for {var_name}: {e}")
        return None
