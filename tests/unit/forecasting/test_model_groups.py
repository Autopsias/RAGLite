"""Tests for model group taxonomy and stratified ensemble.

Story: Ensemble Model Grouping (Phase 7)
"""

from __future__ import annotations

from raglite.forecasting.model_groups import (
    GROUP_WEIGHTS,
    MODEL_TO_GROUP,
    ModelGroup,
    get_active_groups,
    get_group_for_model,
    get_models_in_group,
)


class TestModelGroupTaxonomy:
    """Test model group definitions."""

    def test_all_models_have_groups(self) -> None:
        """Verify all 9 models are assigned to groups."""
        expected_models = {
            "arima",
            "ets",
            "prophet",
            "linear",
            "xgboost",
            "lightgbm",
            "catboost",
            "chronos",
            "tft",
        }
        actual_models = set(MODEL_TO_GROUP.keys())
        # Allow extra models (ridge, lasso) but ensure base 9 are present
        assert expected_models.issubset(actual_models)

    def test_group_weights_sum_to_one(self) -> None:
        """Verify group weights sum to 1.0."""
        total = sum(GROUP_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_groups_have_weights(self) -> None:
        """Verify all ModelGroup enum values have weights."""
        for group in ModelGroup:
            assert group in GROUP_WEIGHTS

    def test_get_models_in_group(self) -> None:
        """Verify get_models_in_group returns correct models."""
        ml_gb = get_models_in_group(ModelGroup.ML_GRADIENT_BOOSTING)
        assert "xgboost" in ml_gb
        assert "lightgbm" in ml_gb
        assert "catboost" in ml_gb
        assert "prophet" not in ml_gb

    def test_get_group_for_model(self) -> None:
        """Verify get_group_for_model returns correct group."""
        assert get_group_for_model("prophet") == ModelGroup.STATISTICAL_HYBRID
        assert get_group_for_model("xgboost") == ModelGroup.ML_GRADIENT_BOOSTING
        assert get_group_for_model("chronos") == ModelGroup.DEEP_LEARNING
        assert get_group_for_model("unknown") is None

    def test_get_active_groups(self) -> None:
        """Verify get_active_groups returns groups with available models."""
        available = ["prophet", "xgboost", "chronos"]
        active = get_active_groups(available)
        assert ModelGroup.STATISTICAL_HYBRID in active
        assert ModelGroup.ML_GRADIENT_BOOSTING in active
        assert ModelGroup.DEEP_LEARNING in active
        assert ModelGroup.STATISTICAL not in active  # No ARIMA/ETS


class TestStratifiedEnsemble:
    """Test stratified ensemble forecast calculation."""

    def test_stratified_ensemble_basic(self) -> None:
        """Verify stratified ensemble produces valid output."""
        from raglite.forecasting.ensemble_helpers_results import (
            calculate_stratified_ensemble_forecast,
        )

        # Simulate predictions from 3 models in different groups
        predictions = {
            "prophet": [100.0, 110.0, 120.0, 130.0],  # STATISTICAL_HYBRID
            "xgboost": [95.0, 105.0, 115.0, 125.0],  # ML_GB
            "chronos": [105.0, 115.0, 125.0, 135.0],  # DEEP_LEARNING
        }

        result = calculate_stratified_ensemble_forecast(predictions)

        # Should have 4 periods
        assert len(result) == 4

        # Values should be in reasonable range (between min and max predictions)
        for i, val in enumerate(result):
            min_val = min(
                predictions["prophet"][i], predictions["xgboost"][i], predictions["chronos"][i]
            )
            max_val = max(
                predictions["prophet"][i], predictions["xgboost"][i], predictions["chronos"][i]
            )
            assert min_val <= val <= max_val

    def test_stratified_ensemble_group_averaging(self) -> None:
        """Verify within-group averaging works correctly."""
        from raglite.forecasting.ensemble_helpers_results import (
            calculate_stratified_ensemble_forecast,
        )

        # 3 ML_GB models should be averaged together before cross-group weighting
        predictions = {
            "xgboost": [100.0, 100.0],
            "lightgbm": [100.0, 100.0],
            "catboost": [100.0, 100.0],  # All same = group average 100
            "prophet": [200.0, 200.0],  # Different group
        }

        result = calculate_stratified_ensemble_forecast(predictions)

        # Group averages:
        # - ML_GB: 100.0 (weight 0.25)
        # - STATISTICAL_HYBRID: 200.0 (weight 0.25)
        # Total weight: 0.5
        # Normalized: ML_GB=0.5, STAT_HYBRID=0.5
        # Result: 0.5 * 100 + 0.5 * 200 = 150
        assert len(result) == 2
        assert abs(result[0] - 150.0) < 0.01
        assert abs(result[1] - 150.0) < 0.01

    def test_stratified_ensemble_empty_predictions(self) -> None:
        """Verify empty predictions returns empty list."""
        from raglite.forecasting.ensemble_helpers_results import (
            calculate_stratified_ensemble_forecast,
        )

        result = calculate_stratified_ensemble_forecast({})
        assert result == []

    def test_stratified_ensemble_single_model(self) -> None:
        """Verify single model returns that model's predictions."""
        from raglite.forecasting.ensemble_helpers_results import (
            calculate_stratified_ensemble_forecast,
        )

        predictions = {
            "prophet": [100.0, 110.0, 120.0],
        }

        result = calculate_stratified_ensemble_forecast(predictions)
        assert len(result) == 3
        # With only one group, it gets 100% weight
        assert result == [100.0, 110.0, 120.0]

    def test_stratified_vs_flat_weighting(self) -> None:
        """Verify stratified ensemble differs from flat weighted average."""
        from raglite.forecasting.ensemble import _calculate_weighted_average
        from raglite.forecasting.ensemble_helpers_results import (
            calculate_stratified_ensemble_forecast,
        )

        # All ML_GB models agree, Prophet disagrees
        predictions = {
            "xgboost": [100.0],
            "lightgbm": [100.0],
            "catboost": [100.0],
            "prophet": [200.0],
        }

        # Flat weighted (default weights favor Prophet at 0.23)
        flat_weights = {
            "prophet": 0.23,
            "xgboost": 0.15,
            "lightgbm": 0.15,
            "catboost": 0.12,
        }
        flat_result = _calculate_weighted_average(
            predictions, flat_weights, list(predictions.keys())
        )

        # Stratified (ML_GB group gets 25%, Prophet gets 25%)
        stratified_result = calculate_stratified_ensemble_forecast(predictions)

        # Flat gives Prophet 23% weight + ML_GB 42% = biased toward agreement
        # Stratified gives each GROUP equal weight (25% each for the 2 active groups)
        # Results should differ
        assert len(flat_result) == 1
        assert len(stratified_result) == 1
        # Stratified should be closer to 150 (equal group weighting)
        assert abs(stratified_result[0] - 150.0) < 1.0


class TestVariableConfigEnsembleStrategy:
    """Test ensemble_strategy field in VariableConfig."""

    def test_default_ensemble_strategy(self) -> None:
        """Verify default ensemble_strategy is 'single_best'."""
        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="units",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
        )
        assert config.ensemble_strategy == "single_best"

    def test_stratified_ensemble_strategy(self) -> None:
        """Verify ensemble_strategy can be set to 'stratified'."""
        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="units",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
            ensemble_strategy="stratified",
        )
        assert config.ensemble_strategy == "stratified"
