"""create_model_weights_table

Story 6.12 AC2: Adaptive weights PostgreSQL schema for backtest-driven
ensemble weight optimization.

Creates the model_weights table for storing model performance metrics
from rolling backtest and calculated weights for each model-metric combination.

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create model_weights table.

    Creates:
    - model_weights: Model performance metrics and ensemble weights
    """
    op.create_table(
        "model_weights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=50), nullable=False),
        sa.Column("weight", sa.Numeric(precision=5, scale=4), nullable=False),
        # RMSE: Can be large for raw values (e.g., cement tons), precision 12,4
        sa.Column("backtest_rmse", sa.Numeric(precision=12, scale=4), nullable=True),
        # MAPE: Percentage, typically 0-100%, precision 8,4
        sa.Column("backtest_mape", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("has_regressors", sa.Boolean(), default=True),
        sa.Column("data_points", sa.Integer(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_name", "model_name", name="uq_metric_model"),
    )
    # Index on metric_name for fast lookups by metric
    op.create_index(
        "idx_model_weights_metric",
        "model_weights",
        ["metric_name"],
    )
    # Index on model_name for fast lookups by model
    op.create_index(
        "idx_model_weights_model",
        "model_weights",
        ["model_name"],
    )


def downgrade() -> None:
    """Drop model_weights table."""
    op.drop_index("idx_model_weights_model", table_name="model_weights")
    op.drop_index("idx_model_weights_metric", table_name="model_weights")
    op.drop_table("model_weights")
