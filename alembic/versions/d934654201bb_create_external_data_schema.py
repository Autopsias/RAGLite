"""create_external_data_schema

Story 6.2: PostgreSQL External Data Schema & Storage

Creates tables for external data sources (INE, BPstat, OMIE, etc.)
and their time-series data points.

Revision ID: d934654201bb
Revises:
Create Date: 2025-12-05 15:20:46.232055
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d934654201bb"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create external data schema tables.

    Creates:
    - external_data_sources: Metadata about external data sources
    - external_data_points: Time-series data points from sources
    """
    # Create external_data_sources table
    op.create_table(
        "external_data_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("api_endpoint", sa.Text(), nullable=True),
        sa.Column("data_type", sa.String(length=50), nullable=True),
        sa.Column("refresh_frequency", sa.String(length=20), nullable=True),
        sa.Column("last_refresh_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_data_sources_source_name",
        "external_data_sources",
        ["source_name"],
        unique=True,
    )

    # Create external_data_points table
    op.create_table(
        "external_data_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["external_data_sources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "date", "metric_name", name="uq_source_date_metric"),
    )
    op.create_index("idx_data_points_metric", "external_data_points", ["metric_name"], unique=False)
    op.create_index(
        "idx_data_points_source_date",
        "external_data_points",
        ["source_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    """Drop external data schema tables."""
    op.drop_index("idx_data_points_source_date", table_name="external_data_points")
    op.drop_index("idx_data_points_metric", table_name="external_data_points")
    op.drop_table("external_data_points")
    op.drop_index("ix_external_data_sources_source_name", table_name="external_data_sources")
    op.drop_table("external_data_sources")
