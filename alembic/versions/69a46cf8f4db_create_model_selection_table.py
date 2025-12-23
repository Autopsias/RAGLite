"""create_model_selection_table

Story 7b-4: Model Selection Cache PostgreSQL

Creates the model_selection table for caching per-variable
optimal model selections from cross-validation.

Revision ID: 69a46cf8f4db
Revises: d934654201bb
Create Date: 2025-12-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "69a46cf8f4db"
down_revision: str | Sequence[str] | None = "d934654201bb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create model_selection table.

    Creates:
    - model_selection: Cached model selection results per variable
    """
    op.create_table(
        "model_selection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variable_name", sa.String(length=100), nullable=False),
        sa.Column("best_model", sa.String(length=50), nullable=False),
        sa.Column("best_mape", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("best_mase", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("use_regressors", sa.Boolean(), default=False),
        sa.Column("regressor_list", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("candidate_results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("data_characteristics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("selected_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Unique index on variable_name for fast lookups
    op.create_index(
        "ix_model_selection_variable_name",
        "model_selection",
        ["variable_name"],
        unique=True,
    )
    # Index on expires_at for TTL queries
    op.create_index(
        "idx_model_selection_expires",
        "model_selection",
        ["expires_at"],
    )


def downgrade() -> None:
    """Drop model_selection table."""
    op.drop_index("idx_model_selection_expires", table_name="model_selection")
    op.drop_index("ix_model_selection_variable_name", table_name="model_selection")
    op.drop_table("model_selection")
