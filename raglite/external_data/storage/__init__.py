"""External data storage utilities.

Story 6.2: PostgreSQL External Data Schema & Storage (AC4)
Story 6.8: Tier 2 Data Sources & ML Enhancements (Conditional)
Story 6.9: External Data Source Client Fixes - Freshness Tracking
Story 8.2: External Data Client Refactoring - Storage Package

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

from typing import TYPE_CHECKING

from raglite.external_data.storage.constants import (
    FRESHNESS_THRESHOLDS,
    MODEL_SELECTION_TTL_DAYS,
    TIER2_SOURCES,
)
from raglite.external_data.storage.core import (
    create_source,
    get_metrics_for_source,
    get_or_create_source,
    get_source,
    insert_data_points,
    list_sources,
    query_data_range,
    query_latest,
    soft_delete_source,
    update_last_refresh,
)
from raglite.external_data.storage.freshness import (
    get_freshness_report,
    get_source_freshness,
    get_stale_sources,
    is_source_fresh,
)

# Re-export all public functions for backward compatibility
from raglite.external_data.storage.model_selection import (
    CachedModelSelection,
    cache_model_selection,
    cleanup_expired_model_selections,
    get_cached_model_selection,
    invalidate_all_model_selections,
    invalidate_model_selection,
)
from raglite.external_data.storage.model_weights import (
    delete_model_weights,
    get_active_model,
    get_model_history,
    get_model_weights,
    get_weights_for_metric,
    save_model_checkpoint,
    save_model_weight,
)
from raglite.external_data.storage.tier2 import (
    register_tier2_source,
    store_api2_coal_prices,
    store_bank_appraisals,
    store_construction_confidence,
    store_eurostat_electricity_prices,
    store_house_price_index,
    store_ttf_gas_prices,
)
from raglite.shared.database import get_session

if TYPE_CHECKING:
    from datetime import date, datetime, timedelta

    from sqlalchemy.orm import Session

    from raglite.external_data.models import ModelRegistry
    from raglite.external_data.orm_models import (
        ExternalDataPointORM,
        ExternalDataSourceORM,
        ModelWeightORM,
    )

__all__ = [
    # Main storage class
    "ExternalDataStorage",
    # Constants (alphabetized)
    "FRESHNESS_THRESHOLDS",
    "MODEL_SELECTION_TTL_DAYS",
    "TIER2_SOURCES",
    # Database utilities
    "get_session",
    # Operations (alphabetized)
    "create_source",
    "get_metrics_for_source",
    "get_or_create_source",
    "get_source",
    "insert_data_points",
    "list_sources",
    "soft_delete_source",
    "update_last_refresh",
    # Queries (alphabetized)
    "query_data_range",
    "query_latest",
    # Freshness (alphabetized)
    "get_freshness_report",
    "get_source_freshness",
    "get_stale_sources",
    "is_source_fresh",
    # Tier2 (alphabetized)
    "register_tier2_source",
    "store_api2_coal_prices",
    "store_bank_appraisals",
    "store_construction_confidence",
    "store_eurostat_electricity_prices",
    "store_house_price_index",
    "store_ttf_gas_prices",
    # Model weights (alphabetized)
    "delete_model_weights",
    "get_model_weights",
    "get_weights_for_metric",
    "save_model_weight",
    # Model registry (alphabetized)
    "get_active_model",
    "get_model_history",
    "save_model_checkpoint",
    # Model selection cache (alphabetized)
    "CachedModelSelection",
    "cache_model_selection",
    "cleanup_expired_model_selections",
    "get_cached_model_selection",
    "invalidate_all_model_selections",
    "invalidate_model_selection",
]


class ExternalDataStorage:
    """Utility for storing and querying external data in PostgreSQL.

    Provides methods for:
    - Creating and managing external data sources
    - Bulk inserting data points
    - Querying data by source, date range, and metric
    - Soft delete operations

    This is a backward-compatibility wrapper that delegates to functional modules.

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

    # =========================================================================
    # Operations
    # =========================================================================

    def create_source(
        self,
        source_name: str,
        api_endpoint: str | None = None,
        data_type: str | None = None,
        refresh_frequency: str | None = None,
        metadata: dict | None = None,
    ) -> ExternalDataSourceORM:
        """Create a new external data source."""
        return create_source(
            self.session, source_name, api_endpoint, data_type, refresh_frequency, metadata
        )

    def get_source(self, source_name: str) -> ExternalDataSourceORM | None:
        """Get an external data source by name."""
        return get_source(self.session, source_name)

    def get_or_create_source(
        self,
        source_name: str,
        api_endpoint: str | None = None,
        data_type: str | None = None,
        refresh_frequency: str | None = None,
        metadata: dict | None = None,
    ) -> tuple[ExternalDataSourceORM, bool]:
        """Get existing source or create new one."""
        return get_or_create_source(
            self.session, source_name, api_endpoint, data_type, refresh_frequency, metadata
        )

    def insert_data_points(
        self,
        source_name: str,
        data_points: list[dict],
        upsert: bool = False,
    ) -> int:
        """Bulk insert data points for a source."""
        return insert_data_points(self.session, source_name, data_points, upsert)

    def soft_delete_source(self, source_name: str) -> bool:
        """Soft delete a data source and all its data points."""
        return soft_delete_source(self.session, source_name)

    def list_sources(self, include_deleted: bool = False) -> list[ExternalDataSourceORM]:
        """List all data sources."""
        return list_sources(self.session, include_deleted)

    def update_last_refresh(
        self,
        source_name: str,
        refresh_time: datetime | None = None,
    ) -> bool:
        """Update the last_refresh_at timestamp for a source."""
        return update_last_refresh(self.session, source_name, refresh_time)

    # =========================================================================
    # Queries
    # =========================================================================

    def query_data_range(
        self,
        source_name: str,
        start_date: date,
        end_date: date,
        metric_name: str | None = None,
    ) -> list[ExternalDataPointORM]:
        """Query data points for a date range."""
        return query_data_range(self.session, source_name, start_date, end_date, metric_name)

    def query_latest(
        self,
        source_name: str,
        metric_name: str | None = None,
        limit: int = 1,
    ) -> list[ExternalDataPointORM]:
        """Query the most recent data points."""
        return query_latest(self.session, source_name, metric_name, limit)

    def get_metrics_for_source(self, source_name: str) -> list[str]:
        """Get all unique metric names for a source."""
        return get_metrics_for_source(self.session, source_name)

    # =========================================================================
    # Metadata (Freshness Tracking)
    # =========================================================================

    def is_source_fresh(
        self,
        source_name: str,
        custom_threshold: timedelta | None = None,
    ) -> bool:
        """Check if a data source is fresh (recently updated)."""
        return is_source_fresh(self.session, source_name, custom_threshold)

    def get_source_freshness(self, source_name: str) -> dict:
        """Get detailed freshness information for a source."""
        return get_source_freshness(self.session, source_name)

    def get_freshness_report(
        self,
        include_deleted: bool = False,
    ) -> dict:
        """Generate a freshness report for all data sources."""
        return get_freshness_report(self.session, include_deleted)

    def get_stale_sources(self) -> list[dict]:
        """Get list of stale data sources requiring refresh."""
        return get_stale_sources(self.session)

    # =========================================================================
    # Tier 2 Data Storage (Story 6.8 AC3)
    # =========================================================================

    def register_tier2_source(self, source_key: str) -> ExternalDataSourceORM:
        """Register a Tier 2 data source from configuration."""
        return register_tier2_source(  # type: ignore[no-any-return]self.session, source_key, TIER2_SOURCES)

    def store_api2_coal_prices(
        self,
        prices: list,  # list[API2CoalPrice]
        upsert: bool = True,
    ) -> int:
        """Store API2 Coal prices from ICEFuturesClient."""
        return store_api2_coal_prices(self.session, prices, upsert)

    def store_ttf_gas_prices(
        self,
        prices: list,  # list[TTFGasPrice]
        upsert: bool = True,
    ) -> int:
        """Store TTF Natural Gas prices from ICEFuturesClient."""
        return store_ttf_gas_prices(self.session, prices, upsert)

    def store_eurostat_electricity_prices(
        self,
        prices: list,  # list[EurostatElectricityPrice]
        upsert: bool = True,
    ) -> int:
        """Store Eurostat electricity prices."""
        return store_eurostat_electricity_prices(self.session, prices, upsert)

    def store_house_price_index(
        self,
        records: list,  # list[INEHousePriceIndex]
        upsert: bool = True,
    ) -> int:
        """Store INE House Price Index data."""
        return store_house_price_index(self.session, records, upsert)

    def store_construction_confidence(
        self,
        records: list,  # list[INEConstructionConfidence]
        upsert: bool = True,
    ) -> int:
        """Store INE Construction Confidence data."""
        return store_construction_confidence(self.session, records, upsert)

    def store_bank_appraisals(
        self,
        records: list,  # list[BPstatBankAppraisal]
        upsert: bool = True,
    ) -> int:
        """Store BPstat Bank Appraisal data."""
        return store_bank_appraisals(self.session, records, upsert)

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
        """Save or update a model weight entry."""
        return save_model_weight(
            self.session,
            metric_name,
            model_name,
            weight,
            backtest_rmse,
            backtest_mape,
            has_regressors,
            data_points,
        )

    def get_model_weights(
        self,
        metric_name: str | None = None,
    ) -> list[ModelWeightORM]:
        """Get model weights, optionally filtered by metric."""
        return get_model_weights(self.session, metric_name)

    def get_weights_for_metric(
        self,
        metric_name: str,
    ) -> dict[str, float]:
        """Get model weights as a dict for a specific metric."""
        return get_weights_for_metric(self.session, metric_name)

    def delete_model_weights(
        self,
        metric_name: str | None = None,
    ) -> int:
        """Delete model weights, optionally filtered by metric."""
        return delete_model_weights(self.session, metric_name)

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
        """Save trained model checkpoint to registry."""
        return save_model_checkpoint(
            self.session,
            model_type,
            model_version,
            checkpoint_path,
            metrics_json,
            set_active,
        )

    def get_active_model(self, model_type: str) -> ModelRegistry | None:
        """Get active checkpoint for model type."""
        return get_active_model(self.session, model_type)

    def get_model_history(
        self,
        model_type: str,
        limit: int = 10,
    ) -> list[ModelRegistry]:
        """Get checkpoint history for model type."""
        return get_model_history(self.session, model_type, limit)
