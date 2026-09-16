"""Unit tests for CachedModelSelection dataclass.

Story 7b-4: Model Selection Cache in PostgreSQL

Test IDs map to Acceptance Criteria:
- TEST-AC-7b.4.3.x: CachedModelSelection dataclass tests
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestCachedModelSelectionDataclass:
    """[P0] AC-7b.4.3: CachedModelSelection dataclass tests."""

    def test_ac_7b_4_3_1_cached_model_selection_exists(self) -> None:
        """TEST-AC-7b.4.3.1: CachedModelSelection dataclass exists."""
        from raglite.external_data.storage import CachedModelSelection

        assert CachedModelSelection is not None

    def test_ac_7b_4_3_2_cached_model_selection_has_required_fields(self) -> None:
        """TEST-AC-7b.4.3.2: CachedModelSelection has all required fields."""
        from dataclasses import fields

        from raglite.external_data.storage import CachedModelSelection

        field_names = {f.name for f in fields(CachedModelSelection)}
        required_fields = {
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
        }

        for field in required_fields:
            assert field in field_names, f"Missing required field: {field}"

    def test_ac_7b_4_3_3_cached_model_selection_instantiation(self) -> None:
        """TEST-AC-7b.4.3.3: CachedModelSelection can be instantiated."""
        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        expires = now + timedelta(days=7)

        cached = CachedModelSelection(
            variable_name="ebitda",
            best_model="prophet",
            best_mape=5.5,
            best_mase=0.8,
            use_regressors=True,
            regressor_list=["gas_price", "euribor"],
            candidate_results={"prophet_True": {"mape": 5.5, "mase": 0.8}},
            data_characteristics={"trend": "linear", "seasonality": "yearly"},
            selected_at=now,
            expires_at=expires,
        )

        assert cached.variable_name == "ebitda"
        assert cached.best_model == "prophet"
        assert cached.best_mape == 5.5
        assert cached.best_mase == 0.8
        assert cached.use_regressors is True
        assert cached.regressor_list == ["gas_price", "euribor"]
