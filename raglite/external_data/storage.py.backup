"""External data storage utilities.

Story 6.2: PostgreSQL External Data Schema & Storage (AC4)
Story 6.8: Tier 2 Data Sources & ML Enhancements (Conditional)
Story 6.9: External Data Source Client Fixes - Freshness Tracking

Provides ExternalDataStorage class for CRUD operations on external data.

Tier 2 Source Configuration (Story 6.8 AC3):
- ICE_API2_Coal: API2 Coal settlement prices (pet coke proxy)
- ICE_TTF_Gas: TTF Natural Gas settlement prices
- Eurostat_Electricity: EU electricity prices for industrial consumers
- INE_HousePriceIndex: Portuguese house price index (quarterly)
- INE_ConstructionConfidence: Construction sector confidence indicator
- BPstat_BankAppraisals: Average bank appraisal values (EUR/m²)
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from raglite.external_data.orm_models import (
    ExternalDataPointORM,
    ExternalDataSourceORM,
    ModelSelectionORM,
    ModelWeightORM,
)
from raglite.shared.database import get_session, utc_now
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from raglite.external_data.models import ModelRegistry
    from raglite.forecasting.model_selection import ModelSelectionResult

logger = get_logger(__name__)

# Freshness thresholds by refresh frequency
FRESHNESS_THRESHOLDS: dict[str, timedelta] = {
    "hourly": timedelta(hours=2),
    "daily": timedelta(days=2),
    "weekly": timedelta(days=10),
    "monthly": timedelta(days=45),
    "quarterly": timedelta(days=120),
    "annual": timedelta(days=400),
}

# Model selection cache TTL (Story 7b-4 AC-7b.4.5)
MODEL_SELECTION_TTL_DAYS = 7

# ===========================================================================
# Tier 2 Source Configuration (Story 6.8 AC3)
# ===========================================================================

# Source name constants for Tier 2 data sources
TIER2_SOURCES = {
    # Energy commodities (AC1.1, AC1.2)
    "ICE_API2_Coal": {
        "api_endpoint": "https://data.nasdaq.com/api/v3/datasets/CHRIS/ICE_ATW1",
        "data_type": "time_series",
        "refresh_frequency": "daily",
        "metrics": ["settlement_price"],
        "unit": "USD/tonne",
        "description": "API2 Coal (CIF ARA) - pet coke proxy (correlation 0.7-0.85)",
    },
    "ICE_TTF_Gas": {
        "api_endpoint": "https://data.nasdaq.com/api/v3/datasets/CHRIS/ICE_TFM1",
        "data_type": "time_series",
        "refresh_frequency": "daily",
        "metrics": ["settlement_price"],
        "unit": "EUR/MWh",
        "description": "TTF Natural Gas - critical for thermal energy forecasting",
    },
    # EU statistics (AC1.3)
    "Eurostat_Electricity": {
        "api_endpoint": "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1",
        "data_type": "time_series",
        "refresh_frequency": "monthly",
        "metrics": ["price_eur_kwh"],
        "unit": "EUR/kWh",
        "description": "EU electricity prices for industrial consumers (nrg_pc_204)",
    },
    # Portuguese indicators (AC2.1, AC2.2)
    "INE_HousePriceIndex": {
        "api_endpoint": "https://www.ine.pt/ine/json_indicador/",
        "data_type": "index",
        "refresh_frequency": "quarterly",
        "metrics": ["index_value", "yoy_change_pct"],
        "unit": "index (base 2015)",
        "description": "Portuguese House Price Index - leading indicator for construction",
    },
    "INE_ConstructionConfidence": {
        "api_endpoint": "https://www.ine.pt/ine/json_indicador/",
        "data_type": "index",
        "refresh_frequency": "monthly",
        "metrics": ["confidence_index"],
        "unit": "index",
        "description": "Construction sector confidence indicator",
    },
    "BPstat_BankAppraisals": {
        "api_endpoint": "https://bpstat.bportugal.pt/api/observations/",
        "data_type": "time_series",
        "refresh_frequency": "monthly",
        "metrics": ["avg_appraisal_eur_m2"],
        "unit": "EUR/m²",
        "description": "Average bank appraisal values for housing",
    },
}


class ExternalDataStorage:
    """Utility for storing and querying external data in PostgreSQL.

    Provides methods for:
    - Creating and managing external data sources
    - Bulk inserting data points
    - Querying data by source, date range, and metric
    - Soft delete operations

    Example:
        >>> from raglite.shared.database import get_session
        >>> from raglite.external_data.storage import ExternalDataStorage
        >>>
        >>> session = get_session()
        >>> storage = ExternalDataStorage(session)
        >>>
        >>> # Create a data source
        >>> source = storage.create_source(
        ...     source_name="INE_BuildingPermits",
        ...     api_endpoint="https://ine.pt/api",
        ...     data_type="time_series",
        ...     refresh_frequency="monthly"
        ... )
        >>>
        >>> # Insert data points
        >>> data = [
        ...     {"date": date(2024, 1, 1), "metric_name": "permits", "value": 1234, "unit": "count"},
        ...     {"date": date(2024, 2, 1), "metric_name": "permits", "value": 1456, "unit": "count"},
        ... ]
        >>> count = storage.insert_data_points("INE_BuildingPermits", data)
    """

    def __init__(self, session: Session) -> None:
        """Initialize storage with database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def create_source(
        self,
        source_name: str,
        api_endpoint: str | None = None,
        data_type: str | None = None,
        refresh_frequency: str | None = None,
        metadata: dict | None = None,
    ) -> ExternalDataSourceORM:
        """Create a new external data source.

        Args:
            source_name: Unique identifier for the source (e.g., "INE_BuildingPermits")
            api_endpoint: API endpoint URL (optional)
            data_type: Type of data (e.g., "time_series", "index")
            refresh_frequency: How often data is updated (e.g., "daily", "monthly")
            metadata: Additional source-specific metadata (optional)

        Returns:
            Created ExternalDataSourceORM instance

        Raises:
            IntegrityError: If source_name already exists
        """
        source = ExternalDataSourceORM(
            source_name=source_name,
            api_endpoint=api_endpoint,
            data_type=data_type,
            refresh_frequency=refresh_frequency,
            metadata_=metadata or {},
        )
        self.session.add(source)
        self.session.commit()
        self.session.refresh(source)
        return source

    def get_source(self, source_name: str) -> ExternalDataSourceORM | None:
        """Get an external data source by name.

        Args:
            source_name: Source identifier to look up

        Returns:
            ExternalDataSourceORM if found and not deleted, None otherwise
        """
        result: ExternalDataSourceORM | None = (
            self.session.query(ExternalDataSourceORM)
            .filter(
                ExternalDataSourceORM.source_name == source_name,
                ExternalDataSourceORM.deleted_at.is_(None),
            )
            .first()
        )
        return result

    def get_or_create_source(
        self,
        source_name: str,
        api_endpoint: str | None = None,
        data_type: str | None = None,
        refresh_frequency: str | None = None,
        metadata: dict | None = None,
    ) -> tuple[ExternalDataSourceORM, bool]:
        """Get existing source or create new one.

        Args:
            source_name: Unique identifier for the source
            api_endpoint: API endpoint URL (used only if creating)
            data_type: Type of data (used only if creating)
            refresh_frequency: Update frequency (used only if creating)
            metadata: Additional metadata (used only if creating)

        Returns:
            Tuple of (source, created) where created is True if new source was created
        """
        source = self.get_source(source_name)
        if source:
            return source, False

        try:
            source = self.create_source(
                source_name=source_name,
                api_endpoint=api_endpoint,
                data_type=data_type,
                refresh_frequency=refresh_frequency,
                metadata=metadata,
            )
            return source, True
        except IntegrityError:
            # Race condition - source was created by another process
            self.session.rollback()
            source = self.get_source(source_name)
            if source:
                return source, False
            raise

    def insert_data_points(
        self,
        source_name: str,
        data_points: list[dict],
        upsert: bool = False,
    ) -> int:
        """Bulk insert data points for a source.

        Args:
            source_name: Source identifier to insert data for
            data_points: List of dicts with keys: date, metric_name, value, unit (optional), metadata (optional)
            upsert: If True, update existing records on conflict (default: False)

        Returns:
            Number of data points inserted/updated

        Raises:
            ValueError: If source_name does not exist
            IntegrityError: If duplicate (source_id, date, metric_name) and upsert=False

        Example:
            >>> data = [
            ...     {"date": date(2024, 1, 1), "metric_name": "permits", "value": 1234},
            ...     {"date": date(2024, 2, 1), "metric_name": "permits", "value": 1456},
            ... ]
            >>> storage.insert_data_points("INE_BuildingPermits", data)
            2
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        if not data_points:
            return 0

        count = 0
        for dp in data_points:
            point = ExternalDataPointORM(
                source_id=source.id,
                date=dp["date"],
                metric_name=dp["metric_name"],
                value=dp["value"],
                unit=dp.get("unit"),
                metadata_=dp.get("metadata", {}),
            )

            if upsert:
                # Check if exists and update
                existing = (
                    self.session.query(ExternalDataPointORM)
                    .filter(
                        ExternalDataPointORM.source_id == source.id,
                        ExternalDataPointORM.date == dp["date"],
                        ExternalDataPointORM.metric_name == dp["metric_name"],
                    )
                    .first()
                )
                if existing:
                    existing.value = dp["value"]
                    unit_value = dp.get("unit")
                    existing.unit = unit_value if unit_value is not None else existing.unit
                    existing.metadata_ = dp.get("metadata", {})
                    existing.deleted_at = None  # type: ignore[assignment]
                    count += 1
                    continue

            self.session.add(point)
            count += 1

        self.session.commit()

        # Update last_refresh timestamp
        stmt = (
            update(ExternalDataSourceORM)
            .where(ExternalDataSourceORM.id == source.id)
            .values(last_refresh_at=utc_now())
        )
        self.session.execute(stmt)
        self.session.commit()

        return count

    def query_data_range(
        self,
        source_name: str,
        start_date: date,
        end_date: date,
        metric_name: str | None = None,
    ) -> list[ExternalDataPointORM]:
        """Query data points for a date range.

        Args:
            source_name: Source identifier to query
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            metric_name: Optional filter by specific metric

        Returns:
            List of ExternalDataPointORM matching the criteria, ordered by date

        Raises:
            ValueError: If source_name does not exist
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        query = self.session.query(ExternalDataPointORM).filter(
            ExternalDataPointORM.source_id == source.id,
            ExternalDataPointORM.date >= start_date,
            ExternalDataPointORM.date <= end_date,
            ExternalDataPointORM.deleted_at.is_(None),
        )

        if metric_name:
            query = query.filter(ExternalDataPointORM.metric_name == metric_name)

        results: list[ExternalDataPointORM] = query.order_by(ExternalDataPointORM.date).all()
        return results

    def query_latest(
        self,
        source_name: str,
        metric_name: str | None = None,
        limit: int = 1,
    ) -> list[ExternalDataPointORM]:
        """Query the most recent data points.

        Args:
            source_name: Source identifier to query
            metric_name: Optional filter by specific metric
            limit: Maximum number of results (default: 1)

        Returns:
            List of most recent ExternalDataPointORM, ordered by date descending
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        query = self.session.query(ExternalDataPointORM).filter(
            ExternalDataPointORM.source_id == source.id,
            ExternalDataPointORM.deleted_at.is_(None),
        )

        if metric_name:
            query = query.filter(ExternalDataPointORM.metric_name == metric_name)

        results: list[ExternalDataPointORM] = (
            query.order_by(ExternalDataPointORM.date.desc()).limit(limit).all()
        )
        return results

    def soft_delete_source(self, source_name: str) -> bool:
        """Soft delete a data source and all its data points.

        Args:
            source_name: Source identifier to delete

        Returns:
            True if source was deleted, False if not found
        """
        source = self.get_source(source_name)
        if not source:
            return False

        now = utc_now()

        # Soft delete all data points
        stmt = (
            update(ExternalDataPointORM)
            .where(
                ExternalDataPointORM.source_id == source.id,
                ExternalDataPointORM.deleted_at.is_(None),
            )
            .values(deleted_at=now)
        )
        self.session.execute(stmt)

        # Soft delete the source
        source.deleted_at = now  # type: ignore[assignment]
        self.session.commit()

        return True

    def list_sources(self, include_deleted: bool = False) -> list[ExternalDataSourceORM]:
        """List all data sources.

        Args:
            include_deleted: If True, include soft-deleted sources

        Returns:
            List of ExternalDataSourceORM
        """
        query = self.session.query(ExternalDataSourceORM)

        if not include_deleted:
            query = query.filter(ExternalDataSourceORM.deleted_at.is_(None))

        results: list[ExternalDataSourceORM] = query.order_by(
            ExternalDataSourceORM.source_name
        ).all()
        return results

    def get_metrics_for_source(self, source_name: str) -> list[str]:
        """Get all unique metric names for a source.

        Args:
            source_name: Source identifier

        Returns:
            List of unique metric names

        Raises:
            ValueError: If source_name does not exist
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        results = (
            self.session.query(ExternalDataPointORM.metric_name)
            .filter(
                ExternalDataPointORM.source_id == source.id,
                ExternalDataPointORM.deleted_at.is_(None),
            )
            .distinct()
            .all()
        )

        return [r[0] for r in results]

    # =========================================================================
    # Data Freshness Tracking (Story 6.9)
    # =========================================================================

    def is_source_fresh(
        self,
        source_name: str,
        custom_threshold: timedelta | None = None,
    ) -> bool:
        """Check if a data source is fresh (recently updated).

        Args:
            source_name: Source identifier to check
            custom_threshold: Optional custom staleness threshold (overrides frequency-based)

        Returns:
            True if data is fresh, False if stale or never refreshed

        Raises:
            ValueError: If source_name does not exist
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        if source.last_refresh_at is None:
            return False  # Never refreshed

        now = utc_now()
        last_refresh = source.last_refresh_at

        # Make last_refresh timezone-aware if needed
        if last_refresh.tzinfo is None:
            last_refresh = last_refresh.replace(tzinfo=UTC)

        # Determine threshold
        if custom_threshold:
            threshold = custom_threshold
        else:
            freq = source.refresh_frequency or "daily"
            threshold = FRESHNESS_THRESHOLDS.get(freq, timedelta(days=2))

        age = now - last_refresh
        return age <= threshold

    def get_source_freshness(self, source_name: str) -> dict:
        """Get detailed freshness information for a source.

        Args:
            source_name: Source identifier

        Returns:
            Dict with freshness details:
            - source_name: Source identifier
            - is_fresh: Boolean indicating freshness
            - last_refresh_at: Last refresh timestamp (ISO format or None)
            - age_seconds: Seconds since last refresh (or None)
            - age_human: Human-readable age string
            - refresh_frequency: Expected refresh frequency
            - threshold_seconds: Staleness threshold in seconds
            - next_refresh_due: When next refresh is expected (ISO format)

        Raises:
            ValueError: If source_name does not exist
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        freq = source.refresh_frequency or "daily"
        threshold = FRESHNESS_THRESHOLDS.get(freq, timedelta(days=2))
        now = utc_now()

        if source.last_refresh_at is None:
            return {
                "source_name": source_name,
                "is_fresh": False,
                "last_refresh_at": None,
                "age_seconds": None,
                "age_human": "never refreshed",
                "refresh_frequency": freq,
                "threshold_seconds": int(threshold.total_seconds()),
                "next_refresh_due": "immediately",
            }

        last_refresh = source.last_refresh_at
        if last_refresh.tzinfo is None:
            last_refresh = last_refresh.replace(tzinfo=UTC)

        age = now - last_refresh
        is_fresh = age <= threshold

        # Human-readable age
        age_seconds = int(age.total_seconds())
        if age_seconds < 60:
            age_human = f"{age_seconds} seconds ago"
        elif age_seconds < 3600:
            age_human = f"{age_seconds // 60} minutes ago"
        elif age_seconds < 86400:
            age_human = f"{age_seconds // 3600} hours ago"
        else:
            age_human = f"{age_seconds // 86400} days ago"

        # Next refresh due
        next_due = last_refresh + threshold
        next_due_str = next_due.isoformat() if next_due > now else "overdue"

        return {
            "source_name": source_name,
            "is_fresh": is_fresh,
            "last_refresh_at": last_refresh.isoformat(),
            "age_seconds": age_seconds,
            "age_human": age_human,
            "refresh_frequency": freq,
            "threshold_seconds": int(threshold.total_seconds()),
            "next_refresh_due": next_due_str,
        }

    def get_freshness_report(
        self,
        include_deleted: bool = False,
    ) -> dict:
        """Generate a freshness report for all data sources.

        Args:
            include_deleted: If True, include soft-deleted sources

        Returns:
            Dict with:
            - generated_at: Report generation timestamp
            - total_sources: Total number of sources
            - fresh_count: Number of fresh sources
            - stale_count: Number of stale sources
            - never_refreshed_count: Sources never refreshed
            - sources: List of per-source freshness details
        """
        sources = self.list_sources(include_deleted=include_deleted)
        now = utc_now()

        fresh_count = 0
        stale_count = 0
        never_refreshed = 0
        source_details = []

        for source in sources:
            try:
                details = self.get_source_freshness(source.source_name)
                source_details.append(details)

                if details["last_refresh_at"] is None:
                    never_refreshed += 1
                elif details["is_fresh"]:
                    fresh_count += 1
                else:
                    stale_count += 1

            except ValueError:
                continue

        return {
            "generated_at": now.isoformat(),
            "total_sources": len(sources),
            "fresh_count": fresh_count,
            "stale_count": stale_count,
            "never_refreshed_count": never_refreshed,
            "sources": source_details,
        }

    def get_stale_sources(self) -> list[dict]:
        """Get list of stale data sources requiring refresh.

        Returns:
            List of freshness details for stale sources only,
            sorted by staleness (most stale first)
        """
        report = self.get_freshness_report()
        stale = [s for s in report["sources"] if not s["is_fresh"]]

        # Sort by age (most stale first), handling None age
        stale.sort(
            key=lambda x: x["age_seconds"] if x["age_seconds"] is not None else float("inf"),
            reverse=True,
        )

        return stale

    def update_last_refresh(
        self,
        source_name: str,
        refresh_time: datetime | None = None,
    ) -> bool:
        """Update the last_refresh_at timestamp for a source.

        Args:
            source_name: Source identifier
            refresh_time: Timestamp to set (default: now)

        Returns:
            True if updated, False if source not found
        """
        source = self.get_source(source_name)
        if not source:
            return False

        refresh_time = refresh_time or utc_now()

        stmt = (
            update(ExternalDataSourceORM)
            .where(ExternalDataSourceORM.id == source.id)
            .values(last_refresh_at=refresh_time)
        )
        self.session.execute(stmt)
        self.session.commit()

        logger.info(
            "Updated last_refresh_at for source",
            extra={"source_name": source_name, "refresh_time": refresh_time.isoformat()},
        )
        return True

    # =========================================================================
    # Tier 2 Data Storage (Story 6.8 AC3)
    # =========================================================================

    def register_tier2_source(self, source_key: str) -> ExternalDataSourceORM:
        """Register a Tier 2 data source from configuration.

        Args:
            source_key: Key from TIER2_SOURCES (e.g., "ICE_API2_Coal")

        Returns:
            Created or existing ExternalDataSourceORM

        Raises:
            ValueError: If source_key not found in TIER2_SOURCES
        """
        if source_key not in TIER2_SOURCES:
            raise ValueError(
                f"Unknown Tier 2 source: {source_key}. Valid keys: {list(TIER2_SOURCES.keys())}"
            )

        config = TIER2_SOURCES[source_key]
        source, created = self.get_or_create_source(
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
        self,
        prices: list,  # list[API2CoalPrice]
        upsert: bool = True,
    ) -> int:
        """Store API2 Coal prices from ICEFuturesClient.

        Args:
            prices: List of API2CoalPrice Pydantic models
            upsert: Update existing records on conflict (default: True)

        Returns:
            Number of records stored
        """
        source_key = "ICE_API2_Coal"
        self.register_tier2_source(source_key)

        data_points = []
        for price in prices:
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

        return self.insert_data_points(source_key, data_points, upsert=upsert)

    def store_ttf_gas_prices(
        self,
        prices: list,  # list[TTFGasPrice]
        upsert: bool = True,
    ) -> int:
        """Store TTF Natural Gas prices from ICEFuturesClient.

        Args:
            prices: List of TTFGasPrice Pydantic models
            upsert: Update existing records on conflict (default: True)

        Returns:
            Number of records stored
        """
        source_key = "ICE_TTF_Gas"
        self.register_tier2_source(source_key)

        data_points = []
        for price in prices:
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

        return self.insert_data_points(source_key, data_points, upsert=upsert)

    def store_eurostat_electricity_prices(
        self,
        prices: list,  # list[EurostatElectricityPrice]
        upsert: bool = True,
    ) -> int:
        """Store Eurostat electricity prices.

        Args:
            prices: List of EurostatElectricityPrice Pydantic models
            upsert: Update existing records on conflict (default: True)

        Returns:
            Number of records stored
        """
        source_key = "Eurostat_Electricity"
        self.register_tier2_source(source_key)

        data_points = []
        for price in prices:
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

        return self.insert_data_points(source_key, data_points, upsert=upsert)

    def store_house_price_index(
        self,
        records: list,  # list[INEHousePriceIndex]
        upsert: bool = True,
    ) -> int:
        """Store INE House Price Index data.

        Args:
            records: List of INEHousePriceIndex Pydantic models
            upsert: Update existing records on conflict (default: True)

        Returns:
            Number of records stored
        """
        source_key = "INE_HousePriceIndex"
        self.register_tier2_source(source_key)

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

        return self.insert_data_points(source_key, data_points, upsert=upsert)

    def store_construction_confidence(
        self,
        records: list,  # list[INEConstructionConfidence]
        upsert: bool = True,
    ) -> int:
        """Store INE Construction Confidence data.

        Args:
            records: List of INEConstructionConfidence Pydantic models
            upsert: Update existing records on conflict (default: True)

        Returns:
            Number of records stored
        """
        source_key = "INE_ConstructionConfidence"
        self.register_tier2_source(source_key)

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

        return self.insert_data_points(source_key, data_points, upsert=upsert)

    def store_bank_appraisals(
        self,
        records: list,  # list[BPstatBankAppraisal]
        upsert: bool = True,
    ) -> int:
        """Store BPstat Bank Appraisal data.

        Args:
            records: List of BPstatBankAppraisal Pydantic models
            upsert: Update existing records on conflict (default: True)

        Returns:
            Number of records stored
        """
        source_key = "BPstat_BankAppraisals"
        self.register_tier2_source(source_key)

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

        return self.insert_data_points(source_key, data_points, upsert=upsert)

    # =========================================================================
    # Story 6.12: Model Weight Storage Methods
    # =========================================================================

    def save_model_weight(
        self,
        metric_name: str,
        model_name: str,
        weight: float,
        backtest_rmse: float | None = None,
        backtest_mape: float | None = None,
        has_regressors: bool = True,
        data_points: int | None = None,
    ) -> ModelWeightORM:
        """Save or update a model weight entry.

        Story 6.12 AC2: Store model weights from backtest results.
        Story 6.12 AC4: Weight caps enforced (5% min, 50% max).

        Uses upsert semantics: updates existing entry or creates new one.

        Args:
            metric_name: Target metric (e.g., "cement_demand")
            model_name: Model identifier (e.g., "prophet", "xgboost", "catboost")
            weight: Normalized weight (0.0-1.0)
            backtest_rmse: RMSE from backtest validation (optional)
            backtest_mape: MAPE from backtest validation (optional)
            has_regressors: Whether external regressors were available
            data_points: Number of data points used in backtest

        Returns:
            Created or updated ModelWeightORM instance

        Raises:
            ValueError: If weight is outside valid range after capping
        """
        from decimal import Decimal

        # Story 6.12 AC4: Enforce weight caps (5% min, 50% max)
        MIN_WEIGHT = 0.05
        MAX_WEIGHT = 0.50

        # Apply caps and warn if adjustment was needed
        original_weight = weight
        weight = max(MIN_WEIGHT, min(MAX_WEIGHT, weight))

        if original_weight != weight:
            logger.warning(
                "Weight capped to valid range",
                extra={
                    "metric": metric_name,
                    "model": model_name,
                    "original_weight": original_weight,
                    "capped_weight": weight,
                },
            )

        # Check for existing entry
        existing: ModelWeightORM | None = (
            self.session.query(ModelWeightORM)
            .filter(
                ModelWeightORM.metric_name == metric_name,
                ModelWeightORM.model_name == model_name,
            )
            .first()
        )

        if existing:
            # Update existing entry
            existing.weight = Decimal(str(weight))
            existing.backtest_rmse = (
                Decimal(str(backtest_rmse)) if backtest_rmse is not None else None
            )
            existing.backtest_mape = (
                Decimal(str(backtest_mape)) if backtest_mape is not None else None
            )
            existing.has_regressors = has_regressors
            existing.data_points = data_points
            existing.calculated_at = utc_now()
            self.session.commit()
            self.session.refresh(existing)
            logger.info(
                "Updated model weight",
                extra={"metric": metric_name, "model": model_name, "weight": weight},
            )
            return existing
        else:
            # Create new entry
            new_weight = ModelWeightORM(
                metric_name=metric_name,
                model_name=model_name,
                weight=Decimal(str(weight)),
                backtest_rmse=Decimal(str(backtest_rmse)) if backtest_rmse is not None else None,
                backtest_mape=Decimal(str(backtest_mape)) if backtest_mape is not None else None,
                has_regressors=has_regressors,
                data_points=data_points,
                calculated_at=utc_now(),
            )
            self.session.add(new_weight)
            self.session.commit()
            self.session.refresh(new_weight)
            logger.info(
                "Created model weight",
                extra={"metric": metric_name, "model": model_name, "weight": weight},
            )
            return new_weight

    def get_model_weights(
        self,
        metric_name: str | None = None,
    ) -> list[ModelWeightORM]:
        """Get model weights, optionally filtered by metric.

        Story 6.12 AC2: Query model weights for ensemble configuration.

        Args:
            metric_name: Filter by metric (None = all metrics)

        Returns:
            List of ModelWeightORM entries
        """
        query = self.session.query(ModelWeightORM)

        if metric_name:
            query = query.filter(ModelWeightORM.metric_name == metric_name)

        query = query.order_by(ModelWeightORM.metric_name, ModelWeightORM.model_name)
        result: list[ModelWeightORM] = list(query.all())
        return result

    def get_weights_for_metric(
        self,
        metric_name: str,
    ) -> dict[str, float]:
        """Get model weights as a dict for a specific metric.

        Story 6.12 AC4: Retrieve weights for ensemble forecast.

        Args:
            metric_name: Target metric name

        Returns:
            Dict mapping model_name -> weight (float)
        """
        weights = self.get_model_weights(metric_name)
        return {w.model_name: float(w.weight) for w in weights}

    def delete_model_weights(
        self,
        metric_name: str | None = None,
    ) -> int:
        """Delete model weights, optionally filtered by metric.

        Args:
            metric_name: Metric to delete weights for (None = all weights)

        Returns:
            Number of deleted records
        """
        query = self.session.query(ModelWeightORM)

        if metric_name:
            query = query.filter(ModelWeightORM.metric_name == metric_name)

        count: int = query.delete()
        self.session.commit()

        logger.info(
            "Deleted model weights",
            extra={"metric": metric_name or "all", "count": count},
        )
        return count

    # =========================================================================
    # Story 6.14: Model Registry Operations
    # =========================================================================

    def save_model_checkpoint(
        self,
        model_type: str,
        model_version: str,
        checkpoint_path: str,
        metrics_json: dict[str, float | str | int] | None = None,
        set_active: bool = True,
    ) -> ModelRegistry:
        """Save trained model checkpoint to registry.

        Story 6.14 AC2: Save checkpoint and update registry.

        Args:
            model_type: Model type (e.g., "tft")
            model_version: Version string (e.g., "2024-12-10")
            checkpoint_path: Path to checkpoint file
            metrics_json: Training/validation metrics
            set_active: Mark as active checkpoint for this model type

        Returns:
            ModelRegistry entry
        """
        from raglite.external_data.models import ModelRegistry
        from raglite.external_data.orm_models import ModelRegistryORM

        # Deactivate other checkpoints for this model_type if setting active
        if set_active:
            self.session.query(ModelRegistryORM).filter(
                ModelRegistryORM.model_type == model_type
            ).update({"is_active": False})

        # Create new checkpoint entry
        checkpoint_orm = ModelRegistryORM(
            model_type=model_type,
            model_version=model_version,
            checkpoint_path=checkpoint_path,
            metrics_json=metrics_json,
            is_active=set_active,
        )

        self.session.add(checkpoint_orm)
        self.session.commit()
        self.session.refresh(checkpoint_orm)

        logger.info(
            "Saved model checkpoint to registry",
            extra={
                "model_type": model_type,
                "version": model_version,
                "active": set_active,
            },
        )

        return ModelRegistry(
            id=checkpoint_orm.id,
            model_type=checkpoint_orm.model_type,
            model_version=checkpoint_orm.model_version,
            checkpoint_path=checkpoint_orm.checkpoint_path,
            metrics_json=checkpoint_orm.metrics_json,
            trained_at=checkpoint_orm.trained_at,
            is_active=checkpoint_orm.is_active,
        )

    def get_active_model(self, model_type: str) -> ModelRegistry | None:
        """Get active checkpoint for model type.

        Story 6.14 AC2: Retrieve active checkpoint for inference.

        Args:
            model_type: Model type (e.g., "tft")

        Returns:
            Active ModelRegistry entry or None
        """
        from raglite.external_data.models import ModelRegistry
        from raglite.external_data.orm_models import ModelRegistryORM

        checkpoint_orm = (
            self.session.query(ModelRegistryORM)
            .filter(
                ModelRegistryORM.model_type == model_type,
                ModelRegistryORM.is_active == True,  # noqa: E712
            )
            .first()
        )

        if not checkpoint_orm:
            return None

        return ModelRegistry(
            id=checkpoint_orm.id,
            model_type=checkpoint_orm.model_type,
            model_version=checkpoint_orm.model_version,
            checkpoint_path=checkpoint_orm.checkpoint_path,
            metrics_json=checkpoint_orm.metrics_json,
            trained_at=checkpoint_orm.trained_at,
            is_active=checkpoint_orm.is_active,
        )

    def get_model_history(
        self,
        model_type: str,
        limit: int = 10,
    ) -> list[ModelRegistry]:
        """Get checkpoint history for model type.

        Story 6.14 AC2: Retrieve checkpoint history for fallback.

        Args:
            model_type: Model type (e.g., "tft")
            limit: Maximum number of checkpoints to return

        Returns:
            List of ModelRegistry entries (newest first)
        """
        from raglite.external_data.models import ModelRegistry
        from raglite.external_data.orm_models import ModelRegistryORM

        checkpoints_orm = (
            self.session.query(ModelRegistryORM)
            .filter(ModelRegistryORM.model_type == model_type)
            .order_by(ModelRegistryORM.trained_at.desc())
            .limit(limit)
            .all()
        )

        return [
            ModelRegistry(
                id=c.id,
                model_type=c.model_type,
                model_version=c.model_version,
                checkpoint_path=c.checkpoint_path,
                metrics_json=c.metrics_json,
                trained_at=c.trained_at,
                is_active=c.is_active,
            )
            for c in checkpoints_orm
        ]


# =============================================================================
# Story 7b-4: Model Selection Cache
# =============================================================================


@dataclass
class CachedModelSelection:
    """Cached model selection result for a variable.

    Story 7b-4 AC-7b.4.3: Dataclass for cached model selection results.
    """

    variable_name: str
    best_model: str
    best_mape: float
    best_mase: float | None  # M3: Can be None if not calculated
    use_regressors: bool
    regressor_list: list[str]
    candidate_results: dict
    data_characteristics: dict | None
    selected_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if cached entry has expired (AC-7b.4.5).

        Returns:
            True if current time is past expires_at, False otherwise
        """
        now = datetime.utcnow()
        return now >= self.expires_at


def _sanitize_for_json(obj: Any) -> Any:
    """Sanitize a value for JSON serialization, handling Infinity, NaN, Enums, and numpy types.

    Args:
        obj: Any value that may not be JSON-serializable

    Returns:
        JSON-serializable version of the value
    """
    import math

    import numpy as np

    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        val = float(obj)
        if math.isinf(val) or math.isnan(val):
            return None
        return val
    elif isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    elif isinstance(obj, np.ndarray):
        return [_sanitize_for_json(v) for v in obj.tolist()]
    else:
        return obj


def _serialize_dataclass_with_enums(obj: Any) -> dict[str, Any]:
    """Serialize a dataclass to dict, converting Enums and numpy types to JSON-serializable values.

    Args:
        obj: A dataclass instance that may contain Enum fields or numpy types

    Returns:
        Dictionary with all values converted to JSON-serializable types
    """
    result = dataclasses.asdict(obj)
    sanitized = _sanitize_for_json(result)
    # _sanitize_for_json preserves dict structure when input is dict
    return dict(sanitized) if isinstance(sanitized, dict) else {"data": sanitized}


async def cache_model_selection(result: ModelSelectionResult) -> None:
    """Cache model selection result in PostgreSQL.

    Story 7b-4 AC-7b.4.2: Store model selection results with upsert semantics.

    Uses INSERT ... ON CONFLICT to update existing entries for the same variable.
    Sets expires_at to selected_at + 7 days (AC-7b.4.5).

    Args:
        result: ModelSelectionResult from select_best_model()
    """
    # NOTE: This is sync-over-async - function is declared async for API consistency
    # but uses synchronous get_session() and SQLAlchemy operations. This matches
    # existing codebase patterns. Full async DB migration would be a separate epic.

    from decimal import Decimal

    session = get_session()

    try:
        # Calculate expiry time (AC-7b.4.5: 7-day TTL)
        selected_at = datetime.utcnow()  # Use naive datetime for PostgreSQL TIMESTAMP column
        expires_at = selected_at + timedelta(days=MODEL_SELECTION_TTL_DAYS)

        # Serialize DataCharacteristics if present (with Enum->string conversion)
        data_chars_dict = None
        if result.data_characteristics:
            data_chars_dict = _serialize_dataclass_with_enums(result.data_characteristics)

        # Sanitize candidate_results (may contain Infinity/NaN from failed models)
        sanitized_candidate_results = _sanitize_for_json(result.candidate_results)

        # Create new entry
        new_entry = ModelSelectionORM(
            variable_name=result.variable_name,
            best_model=result.best_model,
            best_mape=Decimal(str(result.best_mape)),
            best_mase=Decimal(str(result.best_mase)),
            use_regressors=result.best_with_regressors,
            regressor_list=result.best_regressor_set,
            candidate_results=sanitized_candidate_results,
            data_characteristics=data_chars_dict,
            selected_at=selected_at,
            expires_at=expires_at,
        )

        # Try insert first (optimistic approach for new entries)
        session.add(new_entry)

        try:
            session.commit()
            logger.info(
                "Cached model selection",
                extra={
                    "variable_name": result.variable_name,
                    "best_model": result.best_model,
                    "best_mape": result.best_mape,
                },
            )
        except IntegrityError:
            # Entry exists, update instead
            session.rollback()
            existing = (
                session.query(ModelSelectionORM)
                .filter(ModelSelectionORM.variable_name == result.variable_name)
                .first()
            )
            if existing:
                existing.best_model = result.best_model
                existing.best_mape = Decimal(str(result.best_mape))
                existing.best_mase = Decimal(str(result.best_mase))
                existing.use_regressors = result.best_with_regressors
                existing.regressor_list = result.best_regressor_set
                existing.candidate_results = sanitized_candidate_results
                existing.data_characteristics = data_chars_dict
                existing.selected_at = selected_at
                existing.expires_at = expires_at
                session.commit()
                logger.info(
                    "Updated cached model selection",
                    extra={
                        "variable_name": result.variable_name,
                        "best_model": result.best_model,
                        "best_mape": result.best_mape,
                    },
                )

    except Exception as e:
        session.rollback()
        logger.error(
            "Failed to cache model selection",
            extra={"variable_name": result.variable_name, "error": str(e)},
        )
        raise
    finally:
        session.close()


async def get_cached_model_selection(variable_name: str) -> CachedModelSelection | None:
    """Retrieve cached model selection for a variable.

    Story 7b-4 AC-7b.4.3: Lookup cached model selection by variable name.
    Performance target: <100ms (indexed query on variable_name).

    Note: Returns expired entries with is_expired=True. Caller should check
    the is_expired property to determine if re-selection is needed.

    Args:
        variable_name: Name of the variable to look up (non-empty, max 100 chars)

    Returns:
        CachedModelSelection if found (may be expired), None if not found

    Raises:
        ValueError: If variable_name is empty or exceeds 100 characters
    """
    # NOTE: This is sync-over-async - function is declared async for API consistency
    # but uses synchronous get_session() and SQLAlchemy operations. This matches
    # existing codebase patterns. Full async DB migration would be a separate epic.

    # M4: Input validation
    if not variable_name or not variable_name.strip():
        raise ValueError("variable_name cannot be empty")
    if len(variable_name) > 100:
        raise ValueError("variable_name cannot exceed 100 characters")
    session = get_session()

    try:
        record = (
            session.query(ModelSelectionORM)
            .filter(ModelSelectionORM.variable_name == variable_name)
            .first()
        )

        if not record:
            return None

        # Convert ORM to dataclass
        cached = CachedModelSelection(
            variable_name=record.variable_name,
            best_model=record.best_model,
            best_mape=float(record.best_mape),
            best_mase=float(record.best_mase)
            if record.best_mase is not None
            else None,  # M2: Preserve None
            use_regressors=record.use_regressors,
            regressor_list=record.regressor_list or [],
            candidate_results=record.candidate_results or {},
            data_characteristics=record.data_characteristics,
            selected_at=record.selected_at,
            expires_at=record.expires_at,
        )

        return cached

    finally:
        session.close()


async def invalidate_model_selection(variable_name: str | None = None) -> int:
    """Invalidate (delete) cached model selection entries.

    Story 7b-4 AC-7b.4.4: Manual cache invalidation.

    Args:
        variable_name: Specific variable to invalidate, or None to invalidate all
                       (non-empty, max 100 chars if provided)

    Returns:
        Number of deleted records

    Raises:
        ValueError: If variable_name is empty or exceeds 100 characters
    """
    # NOTE: This is sync-over-async - function is declared async for API consistency
    # but uses synchronous get_session() and SQLAlchemy operations. This matches
    # existing codebase patterns. Full async DB migration would be a separate epic.

    # M4: Input validation
    if variable_name is not None:
        if not variable_name.strip():
            raise ValueError("variable_name cannot be empty")
        if len(variable_name) > 100:
            raise ValueError("variable_name cannot exceed 100 characters")

    session = get_session()

    try:
        query = session.query(ModelSelectionORM)

        if variable_name:
            query = query.filter(ModelSelectionORM.variable_name == variable_name)

        count = query.delete()
        session.commit()

        logger.info(
            "Invalidated model selection cache",
            extra={"variable_name": variable_name or "all", "count": count},
        )

        return count

    except Exception as e:
        session.rollback()
        logger.error(
            "Failed to invalidate model selection cache",
            extra={"variable_name": variable_name, "error": str(e)},
        )
        raise
    finally:
        session.close()


async def cleanup_expired_model_selections() -> int:
    """Delete expired model selection entries.

    Story 7b-4 AC-7b.4.5: Automatic cleanup of expired entries.
    Should be run periodically (e.g., daily cron job).

    Returns:
        Number of deleted records
    """
    session = get_session()

    try:
        now = datetime.utcnow()  # Use naive datetime for PostgreSQL TIMESTAMP column

        count = session.query(ModelSelectionORM).filter(ModelSelectionORM.expires_at < now).delete()
        session.commit()

        logger.info("Cleaned up expired model selections", extra={"count": count})

        return count

    except Exception as e:
        session.rollback()
        logger.error(
            "Failed to cleanup expired model selections",
            extra={"error": str(e)},
        )
        raise
    finally:
        session.close()


async def invalidate_all_model_selections() -> int:
    """Invalidate all cached model selection entries.

    Story 7b-4 AC-7b.4.4: Convenience alias for invalidating all entries.

    This is a convenience wrapper around invalidate_model_selection(None).

    Returns:
        Number of deleted records
    """
    return await invalidate_model_selection(variable_name=None)
