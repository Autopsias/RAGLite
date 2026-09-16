"""Unit tests for ModelSelectionORM.

Story 7b-4: Model Selection Cache in PostgreSQL

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.4.1.x: ModelSelectionORM tests
"""

from __future__ import annotations

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestModelSelectionORM:
    """[P0] AC-7b.4.1: Tests for ModelSelectionORM model."""

    def test_ac_7b_4_1_1_model_selection_orm_exists(self) -> None:
        """TEST-AC-7b.4.1.1: ModelSelectionORM class exists."""
        from raglite.external_data.orm_models import ModelSelectionORM

        assert ModelSelectionORM is not None

    def test_ac_7b_4_1_2_model_selection_orm_has_table_name(self) -> None:
        """TEST-AC-7b.4.1.2: ModelSelectionORM has correct table name."""
        from raglite.external_data.orm_models import ModelSelectionORM

        assert ModelSelectionORM.__tablename__ == "model_selection"

    def test_ac_7b_4_1_3_model_selection_orm_has_required_columns(self) -> None:
        """TEST-AC-7b.4.1.3: ModelSelectionORM has all required columns."""
        from raglite.external_data.orm_models import ModelSelectionORM

        required_columns = [
            "id",
            "variable_name",
            "best_model",
            "best_mape",
            "best_mase",
            "use_regressors",
            "regressor_list",
            "candidate_results",
            "data_characteristics",
            "selected_at",
            "expires_at",
        ]

        mapper = ModelSelectionORM.__mapper__
        column_names = [c.key for c in mapper.columns]

        for col in required_columns:
            assert col in column_names, f"Missing required column: {col}"

    def test_ac_7b_4_1_4_variable_name_is_unique(self) -> None:
        """TEST-AC-7b.4.1.4: variable_name column is unique."""
        from raglite.external_data.orm_models import ModelSelectionORM

        mapper = ModelSelectionORM.__mapper__
        variable_name_col = mapper.columns["variable_name"]

        assert variable_name_col.unique is True

    def test_ac_7b_4_1_5_expires_at_is_not_nullable(self) -> None:
        """TEST-AC-7b.4.1.5: expires_at column is not nullable."""
        from raglite.external_data.orm_models import ModelSelectionORM

        mapper = ModelSelectionORM.__mapper__
        expires_at_col = mapper.columns["expires_at"]

        assert expires_at_col.nullable is False
