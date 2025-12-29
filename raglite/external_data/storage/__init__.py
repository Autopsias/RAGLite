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
from raglite.external_data.storage.wrapper import ExternalDataStorage
from raglite.shared.database import get_session

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
