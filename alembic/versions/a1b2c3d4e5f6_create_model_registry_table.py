"""create_model_registry_table

Story 6.14: Model Registry for TFT Checkpoints

Creates the model_registry table for storing trained model checkpoints
and metadata for models that require offline training (e.g., TFT).

Revision ID: a1b2c3d4e5f6
Revises: 69a46cf8f4db
Create Date: 2025-12-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "69a46cf8f4db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create model_registry table.

    Creates:
    - model_registry: Trained model checkpoints and metadata
    """
    op.create_table(
        "model_registry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_type", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=20), nullable=False),
        sa.Column("checkpoint_path", sa.Text(), nullable=False),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("trained_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_type", "model_version", name="uq_model_type_version"),
    )
    # Index on model_type for fast lookups
    op.create_index(
        "idx_model_registry_type",
        "model_registry",
        ["model_type"],
    )


def downgrade() -> None:
    """Drop model_registry table."""
    op.drop_index("idx_model_registry_type", table_name="model_registry")
    op.drop_table("model_registry")
