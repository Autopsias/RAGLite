"""SQLAlchemy ORM models for external data storage.

Story 6.2: PostgreSQL External Data Schema & Storage

NOTE: Pydantic models are in models.py. This file contains SQLAlchemy ORM models.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
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
