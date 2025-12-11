"""SQLAlchemy ORM models for external data storage.

Story 6.2: PostgreSQL External Data Schema & Storage
Story 6.12: Model weights for adaptive ensemble forecasting
Story 6.14: Model registry for TFT training workflow

NOTE: Pydantic models are in models.py. This file contains SQLAlchemy ORM models.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from raglite.shared.database import Base, utc_now

if TYPE_CHECKING:
    pass


class ExternalDataSourceORM(Base):
    """External data source metadata (SQLAlchemy ORM).

    Stores metadata about external data sources like INE, BPstat, OMIE, etc.
    """

    __tablename__ = "external_data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    api_endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    refresh_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_refresh_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utc_now, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )  # Soft delete (AC5)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, default={}, nullable=True
    )

    # Relationship to data points
    data_points: Mapped[list[ExternalDataPointORM]] = relationship(
        "ExternalDataPointORM",
        back_populates="source",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ExternalDataSourceORM(id={self.id}, source_name='{self.source_name}')>"


class ExternalDataPointORM(Base):
    """Time-series data point from external source (SQLAlchemy ORM).

    Stores individual data points with date, metric name, value, and unit.
    Supports efficient querying by source, date range, and metric name.
    """

    __tablename__ = "external_data_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("external_data_sources.id"), nullable=False)
    date: Mapped[date_type] = mapped_column(nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, default={}, nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utc_now, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )  # Soft delete (AC5)

    # Relationship to source
    source: Mapped[ExternalDataSourceORM] = relationship(
        "ExternalDataSourceORM", back_populates="data_points"
    )

    __table_args__ = (
        Index("idx_data_points_source_date", "source_id", "date"),
        Index("idx_data_points_metric", "metric_name"),
        UniqueConstraint("source_id", "date", "metric_name", name="uq_source_date_metric"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ExternalDataPointORM(id={self.id}, source_id={self.source_id}, "
            f"date={self.date}, metric_name='{self.metric_name}')>"
        )


class ModelWeightORM(Base):
    """Model weight for adaptive ensemble forecasting (SQLAlchemy ORM).

    Story 6.12 AC2: Adaptive weights PostgreSQL schema for backtest-driven
    ensemble weight optimization.

    Stores model performance metrics from rolling backtest and calculated
    weights for each model-metric combination.
    """

    __tablename__ = "model_weights"

    id: Mapped[int] = mapped_column(primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    # Story 6.12 Issue #6 fix: Define precision for RMSE/MAPE columns
    # RMSE: Can be large for raw values (e.g., cement tons), precision 12,4 allows up to 99999999.9999
    # MAPE: Percentage, typically 0-100%, precision 8,4 allows up to 9999.9999%
    backtest_rmse: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    backtest_mape: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    has_regressors: Mapped[bool] = mapped_column(Boolean, default=True)
    data_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint("metric_name", "model_name", name="uq_metric_model"),
        Index("idx_model_weights_metric", "metric_name"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ModelWeightORM(metric_name='{self.metric_name}', "
            f"model_name='{self.model_name}', weight={self.weight})>"
        )


class ModelRegistryORM(Base):
    """Model registry for trained model checkpoints (SQLAlchemy ORM).

    Story 6.14 AC2: Store trained model checkpoints and metadata.

    Stores checkpoint paths, training metrics, and versioning information
    for models that require offline training (e.g., TFT).
    """

    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    checkpoint_path: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("model_type", "model_version", name="uq_model_type_version"),
        Index("idx_model_registry_type", "model_type"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ModelRegistryORM(model_type='{self.model_type}', "
            f"model_version='{self.model_version}', is_active={self.is_active})>"
        )
