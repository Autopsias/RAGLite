"""Tier 2 data source storage operations.

Story 8.2: External Data Client Refactoring - Tier 2 Storage Module
Story 6.8: Tier 2 Data Sources & ML Enhancements (Conditional)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from raglite.external_data.storage.constants import TIER2_SOURCES
from raglite.external_data.storage.core import get_or_create_source, insert_data_points
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from datetime import date

    from sqlalchemy.orm import Session

logger = get_logger(__name__)


class PriceRecord(Protocol):
    """Protocol for price records (API2CoalPrice, TTFGasPrice, EurostatElectricityPrice)."""

    date: date
    settlement_price: float | None
    price_eur_kwh: float | None
    currency: str
    commodity: str | None
    market: str | None
    country: str | None
    consumption_band: str | None
    tax_component: str | None
    petcoke_proxy: bool | None
    source: str | None


def register_tier2_source(
    session: Session,
    source_key: str,
    tier2_sources: dict[str, Any],
) -> Any:
    """Register a Tier 2 data source from configuration.

    Args:
        session: SQLAlchemy session for database operations
        source_key: Key from TIER2_SOURCES (e.g., "ICE_API2_Coal")
        tier2_sources: Dictionary of Tier 2 source configurations

    Returns:
        Created or existing ExternalDataSourceORM

    Raises:
        ValueError: If source_key not found in TIER2_SOURCES
    """
    if source_key not in tier2_sources:
        raise ValueError(
            f"Unknown Tier 2 source: {source_key}. Valid keys: {list(tier2_sources.keys())}"
        )

    config = tier2_sources[source_key]
    source, created = get_or_create_source(
        session=session,
        source_name=source_key,
        api_endpoint=config["api_endpoint"]
        if isinstance(config["api_endpoint"], str)
        else ", ".join(config["api_endpoint"]),
        data_type=config["data_type"]
        if isinstance(config["data_type"], str)
        else ", ".join(config["data_type"]),
        refresh_frequency=config["refresh_frequency"]
        if isinstance(config["refresh_frequency"], str)
        else ", ".join(config["refresh_frequency"]),
        metadata={
            "tier": 2,
            "unit": config["unit"],
            "description": config["description"],
            "metrics": config["metrics"],
        },
    )

    if created:
        logger.info(
            "Registered Tier 2 source",
            extra={"source_key": source_key, "refresh_frequency": config["refresh_frequency"]},
        )

    return source


def store_api2_coal_prices(
    session: Session,
    prices: list[PriceRecord],  # list[API2CoalPrice]
    upsert: bool = True,
) -> int:
    """Store API2 Coal prices from ICEFuturesClient.

    Args:
        session: SQLAlchemy session for database operations
        prices: List of API2CoalPrice Pydantic models
        upsert: Update existing records on conflict (default: True)

    Returns:
        Number of records stored

    Raises:
        ValueError: If prices list is empty or contains invalid records
    """
    if not prices:
        raise ValueError("prices list cannot be empty")

    source_key = "ICE_API2_Coal"
    register_tier2_source(session, source_key, TIER2_SOURCES)

    data_points = []
    for idx, price in enumerate(prices):
        if not hasattr(price, "date") or not hasattr(price, "settlement_price"):
            raise ValueError(f"Invalid price record at index {idx}: missing required attributes")
        data_points.append(
            {
                "date": price.date,
                "metric_name": "settlement_price",
                "value": price.settlement_price,
                "unit": price.currency,
                "metadata": {
                    "commodity": price.commodity,
                    "petcoke_proxy": price.petcoke_proxy,
                    "source": price.source,
                },
            }
        )

    return insert_data_points(session, source_key, data_points, upsert=upsert)


def store_ttf_gas_prices(
    session: Session,
    prices: list[PriceRecord],  # list[TTFGasPrice]
    upsert: bool = True,
) -> int:
    """Store TTF Natural Gas prices from ICEFuturesClient.

    Args:
        session: SQLAlchemy session for database operations
        prices: List of TTFGasPrice Pydantic models
        upsert: Update existing records on conflict (default: True)

    Returns:
        Number of records stored

    Raises:
        ValueError: If prices list is empty or contains invalid records
    """
    if not prices:
        raise ValueError("prices list cannot be empty")

    source_key = "ICE_TTF_Gas"
    register_tier2_source(session, source_key, TIER2_SOURCES)

    data_points = []
    for idx, price in enumerate(prices):
        if not hasattr(price, "date") or not hasattr(price, "settlement_price"):
            raise ValueError(f"Invalid price record at index {idx}: missing required attributes")
        data_points.append(
            {
                "date": price.date,
                "metric_name": "settlement_price",
                "value": price.settlement_price,
                "unit": price.currency,
                "metadata": {
                    "commodity": price.commodity,
                    "market": price.market,
                    "source": price.source,
                },
            }
        )

    return insert_data_points(session, source_key, data_points, upsert=upsert)


def store_eurostat_electricity_prices(
    session: Session,
    prices: list[PriceRecord],  # list[EurostatElectricityPrice]
    upsert: bool = True,
) -> int:
    """Store Eurostat electricity prices.

    Args:
        session: SQLAlchemy session for database operations
        prices: List of EurostatElectricityPrice Pydantic models
        upsert: Update existing records on conflict (default: True)

    Returns:
        Number of records stored

    Raises:
        ValueError: If prices list is empty or contains invalid records
    """
    if not prices:
        raise ValueError("prices list cannot be empty")

    source_key = "Eurostat_Electricity"
    register_tier2_source(session, source_key, TIER2_SOURCES)

    data_points = []
    for idx, price in enumerate(prices):
        if not hasattr(price, "date") or not hasattr(price, "price_eur_kwh"):
            raise ValueError(f"Invalid price record at index {idx}: missing required attributes")
        data_points.append(
            {
                "date": price.date,
                "metric_name": "price_eur_kwh",
                "value": price.price_eur_kwh,
                "unit": "EUR/kWh",
                "metadata": {
                    "country": price.country,
                    "consumption_band": price.consumption_band,
                    "tax_component": price.tax_component,
                },
            }
        )

    return insert_data_points(session, source_key, data_points, upsert=upsert)


def store_house_price_index(
    session: Session,
    records: list,  # list[INEHousePriceIndex]
    upsert: bool = True,
) -> int:
    """Store INE House Price Index data.

    Args:
        session: SQLAlchemy session for database operations
        records: List of INEHousePriceIndex Pydantic models
        upsert: Update existing records on conflict (default: True)

    Returns:
        Number of records stored
    """
    source_key = "INE_HousePriceIndex"
    register_tier2_source(session, source_key, TIER2_SOURCES)

    data_points = []
    for record in records:
        # Store index value
        data_points.append(
            {
                "date": record.date,
                "metric_name": "index_value",
                "value": record.index_value,
                "unit": "index",
                "metadata": {
                    "region": record.region,
                    "property_type": record.property_type,
                },
            }
        )
        # Store YoY change if available
        if record.yoy_change_pct is not None:
            data_points.append(
                {
                    "date": record.date,
                    "metric_name": "yoy_change_pct",
                    "value": record.yoy_change_pct,
                    "unit": "percent",
                    "metadata": {
                        "region": record.region,
                        "property_type": record.property_type,
                    },
                }
            )

    return insert_data_points(session, source_key, data_points, upsert=upsert)


def store_construction_confidence(
    session: Session,
    records: list,  # list[INEConstructionConfidence]
    upsert: bool = True,
) -> int:
    """Store INE Construction Confidence data.

    Args:
        session: SQLAlchemy session for database operations
        records: List of INEConstructionConfidence Pydantic models
        upsert: Update existing records on conflict (default: True)

    Returns:
        Number of records stored
    """
    source_key = "INE_ConstructionConfidence"
    register_tier2_source(session, source_key, TIER2_SOURCES)

    data_points = []
    for record in records:
        data_points.append(
            {
                "date": record.date,
                "metric_name": "confidence_index",
                "value": record.confidence_index,
                "unit": "index",
                "metadata": {
                    "indicator_type": record.indicator_type,
                },
            }
        )

    return insert_data_points(session, source_key, data_points, upsert=upsert)


def store_bank_appraisals(
    session: Session,
    records: list,  # list[BPstatBankAppraisal]
    upsert: bool = True,
) -> int:
    """Store BPstat Bank Appraisal data.

    Args:
        session: SQLAlchemy session for database operations
        records: List of BPstatBankAppraisal Pydantic models
        upsert: Update existing records on conflict (default: True)

    Returns:
        Number of records stored
    """
    source_key = "BPstat_BankAppraisals"
    register_tier2_source(session, source_key, TIER2_SOURCES)

    data_points = []
    for record in records:
        data_points.append(
            {
                "date": record.date,
                "metric_name": "avg_appraisal_eur_m2",
                "value": record.avg_appraisal_eur_m2,
                "unit": "EUR/m²",
                "metadata": {
                    "region": record.region,
                },
            }
        )

    return insert_data_points(session, source_key, data_points, upsert=upsert)
