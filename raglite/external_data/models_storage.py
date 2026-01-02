"""Storage models for external data.

Story 6.2: PostgreSQL Storage for External Data

Generic data point model for unified storage in PostgreSQL.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

from .models_base import DataSource

# =============================================================================
# Generic Data Point Model (for storage)
# =============================================================================


class ExternalDataPoint(BaseModel):
    """Generic external data point for unified storage.

    Used for PostgreSQL storage in Story 6.2.
    """

    source: DataSource
    indicator: str = Field(description="Data indicator/metric name")
    date: date
    value: float
    unit: str | None = Field(default=None, description="Unit of measurement")
    region: str | None = Field(default=None, description="Geographic region")
    metadata: dict[str, str | float | int | bool | None] = Field(
        default_factory=dict, description="Additional metadata"
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When data was fetched (UTC)",
    )
