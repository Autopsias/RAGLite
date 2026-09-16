"""Unit tests for JSON serialization of cache data.

Story 7b-4: Model Selection Cache in PostgreSQL

Test Categories:
- JSON serialization tests for cache fields
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


class TestJSONSerialization:
    """[P1] Tests for JSON serialization of cache data."""

    def test_candidate_results_serialization(self) -> None:
        """Candidate results dict can be serialized to JSON."""
        import json

        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="test",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=False,
            regressor_list=[],
            candidate_results={
                "prophet_False": {"mape": 5.0, "mase": 0.8},
                "xgboost_False": {"mape": 6.0, "mase": 0.9},
            },
            data_characteristics={"trend": "linear"},
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        # Should not raise
        json_str = json.dumps(cached.candidate_results)
        assert isinstance(json_str, str)

    def test_data_characteristics_serialization(self) -> None:
        """Data characteristics dict can be serialized to JSON."""
        import json

        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="test",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=False,
            regressor_list=[],
            candidate_results={},
            data_characteristics={
                "trend": "linear",
                "seasonality_type": "yearly",
                "volatility_level": "medium",
                "sample_size": 48,
            },
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        # Should not raise
        json_str = json.dumps(cached.data_characteristics)
        assert isinstance(json_str, str)

    def test_regressor_list_serialization(self) -> None:
        """Regressor list can be serialized to JSON."""
        import json

        from raglite.external_data.storage import CachedModelSelection

        now = datetime.utcnow()
        cached = CachedModelSelection(
            variable_name="test",
            best_model="prophet",
            best_mape=5.0,
            best_mase=0.8,
            use_regressors=True,
            regressor_list=["gas_price", "euribor", "electricity_price"],
            candidate_results={},
            data_characteristics=None,
            selected_at=now,
            expires_at=now + timedelta(days=7),
        )

        # Should not raise
        json_str = json.dumps(cached.regressor_list)
        assert isinstance(json_str, str)
        assert "gas_price" in json_str
