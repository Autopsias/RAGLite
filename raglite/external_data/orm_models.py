"""SQLAlchemy ORM models for external data storage.

Story 6.2: PostgreSQL External Data Schema & Storage

NOTE: Pydantic models are in models.py. This file contains SQLAlchemy ORM models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    Date,
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
from sqlalchemy.orm import Mapped, relationship

from raglite.shared.database import Base, utc_now

if TYPE_CHECKING:
    pass


class ExternalDataSourceORM(Base):
    """External data source metadata (SQLAlchemy ORM).

    Stores metadata about external data sources like INE, BPstat, OMIE, etc.
    """

    __tablename__ = "external_data_sources"

    id = Column(Integer, primary_key=True)
    source_name = Column(String(100), unique=True, nullable=False, index=True)
    api_endpoint = Column(Text)
    data_type = Column(String(50))
    refresh_frequency = Column(String(20))
    last_refresh_at = Column(DateTime)
    created_at = Column(DateTime, default=utc_now)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete (AC5)
    metadata_ = Column("metadata", JSONB, default={})

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

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("external_data_sources.id"), nullable=False)
    date = Column(Date, nullable=False)
    metric_name = Column(String(100), nullable=False)
    value = Column(Numeric, nullable=False)
    unit = Column(String(50))
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime, default=utc_now)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete (AC5)

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
