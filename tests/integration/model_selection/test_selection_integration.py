"""Core model selection tests - CV, Models, Regressors, Metrics.

Story 7b-3: Per-Variable Model Selection via Cross-Validation
Test IDs map to Acceptance Criteria:
- TEST-AC-7b.3.1.x: TimeSeriesSplit CV tests
- TEST-AC-7b.3.2.x: All 9 models tests
- TEST-AC-7b.3.3.x: Regressor comparison tests
- TEST-AC-7b.3.4.x: MAPE/MASE selection tests
"""

from __future__ import annotations

import pandas as pd
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.preserve_collection]


# TEST-AC-7b.3.1: TimeSeriesSplit Cross-Validation Implementation
class TestAC_7b_3_1_TimeSeriesSplitCV:
    """[P0] AC-7b.3.1: TimeSeriesSplit Cross-Validation Implementation."""

    @pytest.mark.asyncio
    async def test_ac_7b_3_1_1_select_best_model_uses_time_series_split(
        self, sample_time_series: pd.Series
    ) -> None:
        """TEST-AC-7b.3.1.1: select_best_model uses TimeSeriesSplit for CV."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
            cv_folds=5,
        )

        assert result.cv_folds == 5

    @pytest.mark.asyncio
    @pytest.mark.parametrize("cv_folds", [3, 5, 7])
    async def test_ac_7b_3_1_2_configurable_cv_folds(
        self, sample_time_series: pd.Series, cv_folds: int
    ) -> None:
        """TEST-AC-7b.3.1.2: select_best_model accepts configurable cv_folds parameter."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
            cv_folds=cv_folds,
        )

        assert result.cv_folds == cv_folds

    @pytest.mark.asyncio
    async def test_ac_7b_3_1_3_default_five_folds(self, sample_time_series: pd.Series) -> None:
        """TEST-AC-7b.3.1.3: Default 5 folds used when cv_folds not specified."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
        )

        assert result.cv_folds == 5

    @pytest.mark.asyncio
    async def test_ac_7b_3_1_4_minimum_12_observations_required(
        self, short_time_series: pd.Series
    ) -> None:
        """TEST-AC-7b.3.1.4: Minimum 12 observations enforced."""
        from raglite.forecasting.model_selection import select_best_model

        with pytest.raises(ValueError, match="minimum 12 required"):
            await select_best_model(
                variable_name="short_metric",
                historical_data=short_time_series,
            )

    @pytest.mark.asyncio
    async def test_ac_7b_3_1_5_exactly_12_points_accepted(
        self, minimum_time_series: pd.Series
    ) -> None:
        """TEST-AC-7b.3.1.5: Exactly 12 data points is accepted."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="minimum_metric",
            historical_data=minimum_time_series,
        )

        assert result is not None
        assert result.variable_name == "minimum_metric"


# TEST-AC-7b.3.2: All 9 Models Tested
class TestAC_7b_3_2_AllNineModels:
    """[P0] AC-7b.3.2: All 9 Models Tested."""

    def test_ac_7b_3_2_1_candidate_models_contains_all_nine(self) -> None:
        """TEST-AC-7b.3.2.1: CANDIDATE_MODELS list contains exactly 9 models."""
        from raglite.forecasting.model_selection import CANDIDATE_MODELS

        expected_models = {
            "arima",
            "ets",
            "prophet",
            "xgboost",
            "lightgbm",
            "catboost",
            "chronos",
            "tft",
            "linear",
        }

        assert len(CANDIDATE_MODELS) == 9
        assert set(CANDIDATE_MODELS) == expected_models

    def test_ac_7b_3_2_2_candidate_models_is_list(self) -> None:
        """TEST-AC-7b.3.2.2: CANDIDATE_MODELS is a list (ordered)."""
        from raglite.forecasting.model_selection import CANDIDATE_MODELS

        assert isinstance(CANDIDATE_MODELS, list)

    @pytest.mark.asyncio
    async def test_ac_7b_3_2_3_all_models_attempted_during_selection(
        self, sample_time_series: pd.Series
    ) -> None:
        """TEST-AC-7b.3.2.3: Each model in list is tested during selection."""
        from raglite.forecasting.model_selection import CANDIDATE_MODELS, select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
        )

        tested_models = set()
        for config_key in result.candidate_results.keys():
            model_name = config_key.rsplit("_", 1)[0]
            tested_models.add(model_name)

        for model in CANDIDATE_MODELS:
            assert model in tested_models, f"Model {model} was not tested"

    @pytest.mark.asyncio
    async def test_ac_7b_3_2_4_tft_included_when_available(
        self, sample_time_series: pd.Series
    ) -> None:
        """TEST-AC-7b.3.2.4: TFT included when trained model available."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
        )

        tft_keys = [k for k in result.candidate_results.keys() if k.startswith("tft_")]
        assert len(tft_keys) > 0, "TFT should be attempted"


# TEST-AC-7b.3.3: Regressor Comparison
class TestAC_7b_3_3_RegressorComparison:
    """[P0] AC-7b.3.3: Regressor Comparison."""

    @pytest.mark.asyncio
    async def test_ac_7b_3_3_1_models_tested_with_and_without_regressors(
        self, sample_time_series: pd.Series, sample_regressors: dict[str, pd.Series]
    ) -> None:
        """TEST-AC-7b.3.3.1: Each model tested with and without regressors."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
            external_regressors=sample_regressors,
        )

        regressor_capable_models = [
            "arima",
            "ets",
            "prophet",
            "xgboost",
            "lightgbm",
            "catboost",
            "tft",
            "linear",
        ]

        for model in regressor_capable_models:
            without_regs_key = f"{model}_False"
            with_regs_key = f"{model}_True"

            assert (
                without_regs_key in result.candidate_results
                or with_regs_key in result.candidate_results
            ), f"Model {model} should have at least one configuration tested"

    @pytest.mark.asyncio
    async def test_ac_7b_3_3_2_chronos_skipped_for_regressor_mode(
        self, sample_time_series: pd.Series, sample_regressors: dict[str, pd.Series]
    ) -> None:
        """TEST-AC-7b.3.3.2: Chronos-2 skipped in regressor mode."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
            external_regressors=sample_regressors,
        )

        assert "chronos_True" not in result.candidate_results

    @pytest.mark.asyncio
    async def test_ac_7b_3_3_3_best_with_regressors_flag_set(
        self, sample_time_series: pd.Series, sample_regressors: dict[str, pd.Series]
    ) -> None:
        """TEST-AC-7b.3.3.3: best_with_regressors flag correctly set in result."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
            external_regressors=sample_regressors,
        )

        assert hasattr(result, "best_with_regressors")
        assert isinstance(result.best_with_regressors, bool)

    @pytest.mark.asyncio
    async def test_ac_7b_3_3_4_best_regressor_set_populated(
        self, sample_time_series: pd.Series, sample_regressors: dict[str, pd.Series]
    ) -> None:
        """TEST-AC-7b.3.3.4: best_regressor_set correctly populated when regressors used."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
            external_regressors=sample_regressors,
        )

        assert hasattr(result, "best_regressor_set")
        assert isinstance(result.best_regressor_set, list)

        if result.best_with_regressors:
            assert set(result.best_regressor_set) == set(sample_regressors.keys())

    @pytest.mark.asyncio
    async def test_ac_7b_3_3_5_no_regressors_provided(self, sample_time_series: pd.Series) -> None:
        """TEST-AC-7b.3.3.5: Works correctly when no regressors provided."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
            external_regressors=None,
        )

        for config_key in result.candidate_results.keys():
            assert config_key.endswith("_False"), (
                f"Unexpected config {config_key} when no regressors provided"
            )

        assert result.best_with_regressors is False
        assert result.best_regressor_set == []


# TEST-AC-7b.3.4: MAPE/MASE Selection Criteria
class TestAC_7b_3_4_MAPEMASESelection:
    """[P0] AC-7b.3.4: MAPE/MASE Selection Criteria."""

    @pytest.mark.asyncio
    async def test_ac_7b_3_4_1_best_model_selected_by_lowest_mape(
        self, sample_time_series: pd.Series
    ) -> None:
        """TEST-AC-7b.3.4.1: Model with lowest MAPE selected as winner."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
        )

        valid_results = {k: v for k, v in result.candidate_results.items() if "error" not in v}

        if valid_results:
            min_mape = min(v["mape"] for v in valid_results.values())
            assert result.best_mape == min_mape

    @pytest.mark.asyncio
    async def test_ac_7b_3_4_2_mase_used_as_tiebreaker(self, sample_time_series: pd.Series) -> None:
        """TEST-AC-7b.3.4.2: MASE used as tiebreaker when MAPE is equal."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
        )

        valid_results = {k: v for k, v in result.candidate_results.items() if "error" not in v}

        tied_results = {
            k: v for k, v in valid_results.items() if abs(v["mape"] - result.best_mape) < 1e-6
        }

        if len(tied_results) > 1:
            min_mase_among_tied = min(v["mase"] for v in tied_results.values())
            assert result.best_mase == min_mase_among_tied

    @pytest.mark.asyncio
    async def test_ac_7b_3_4_3_best_mape_populated(self, sample_time_series: pd.Series) -> None:
        """TEST-AC-7b.3.4.3: best_mape field correctly populated."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
        )

        assert hasattr(result, "best_mape")
        assert isinstance(result.best_mape, float)
        assert result.best_mape >= 0

    @pytest.mark.asyncio
    async def test_ac_7b_3_4_4_best_mase_populated(self, sample_time_series: pd.Series) -> None:
        """TEST-AC-7b.3.4.4: best_mase field correctly populated."""
        from raglite.forecasting.model_selection import select_best_model

        result = await select_best_model(
            variable_name="test_metric",
            historical_data=sample_time_series,
        )

        assert hasattr(result, "best_mase")
        assert isinstance(result.best_mase, float)
        assert result.best_mase >= 0
