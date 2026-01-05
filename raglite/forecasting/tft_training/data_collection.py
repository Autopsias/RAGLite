"""Training data collection functions for TFT models.

Story 6.14 AC4: Gather time-series data for TFT training.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def collect_training_data(
    metrics: list[str] | None = None,
    min_data_points: int = 24,
) -> pd.DataFrame | None:
    """Collect training data for TFT from external data sources.

    Story 6.14 AC4: Gather time-series data for TFT training.

    Args:
        metrics: List of metrics to collect (default: EBITDA, revenue, etc.)
        min_data_points: Minimum required data points per metric

    Returns:
        DataFrame with columns: time_idx, metric_name, value, plus regressors
        Returns None if insufficient data
    """

    from raglite.external_data.clients.ecb import ECBClient
    from raglite.external_data.clients.eu_oil_bulletin import EUOilBulletinClient
    from raglite.forecasting.timeseries import extract_timeseries_from_sql

    if metrics is None:
        metrics = ["ebitda", "revenue", "sales_volume"]

    all_data = []

    for metric in metrics:
        try:
            # Extract time-series using SQL extraction (primary method)
            ts_data = await extract_timeseries_from_sql(metric=metric, min_points=6)

            if ts_data and len(ts_data.points) >= min_data_points:
                # Convert to DataFrame rows
                for i, point in enumerate(ts_data.points):
                    all_data.append(
                        {
                            "time_idx": i,
                            "metric_name": metric,
                            "value": point.value,
                            "date": point.date,
                        }
                    )
                logger.info(
                    f"Collected {len(ts_data.points)} points for {metric}",
                    extra={"metric": metric, "points": len(ts_data.points)},
                )
            else:
                logger.warning(
                    f"Insufficient data for {metric}: "
                    f"{len(ts_data.points) if ts_data else 0} points (need {min_data_points})"
                )
        except Exception as e:
            logger.warning(f"Failed to collect data for {metric}: {e}")
            continue

    if not all_data:
        logger.warning("No training data collected - need at least one metric with 24+ points")
        return None

    df = pd.DataFrame(all_data)

    # Add external regressors if available
    try:
        ecb = ECBClient()

        euribor_data = await ecb.fetch_euribor(
            start_date=date(2020, 1, 1), end_date=date(2025, 12, 31), tenor="3M"
        )
        if euribor_data:
            euribor_series = pd.Series({d.date: float(d.rate_pct) for d in euribor_data})
            df["euribor_3m"] = df["date"].map(
                lambda x: euribor_series.get(x, euribor_series.iloc[-1])
            )
    except Exception as e:
        logger.warning(f"Failed to add EURIBOR regressor: {e}")
        df["euribor_3m"] = 0.0

    try:
        oil = EUOilBulletinClient()
        diesel_data = await oil.fetch_diesel_prices(
            start_date=date(2020, 1, 1), end_date=date(2025, 12, 31), country="Portugal"
        )
        if diesel_data:
            diesel_series = pd.Series({d.date: float(d.price_eur_litre) for d in diesel_data})
            df["diesel"] = df["date"].map(lambda x: diesel_series.get(x, diesel_series.iloc[-1]))
    except Exception as e:
        logger.warning(f"Failed to add diesel regressor: {e}")
        df["diesel"] = 0.0

    logger.info(
        "Training data collection complete",
        extra={"total_rows": len(df), "metrics": df["metric_name"].nunique()},
    )

    return df


__all__ = ["collect_training_data"]
