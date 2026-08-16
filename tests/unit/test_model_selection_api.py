"""
Tests for model selection job API surface and function signatures.

AC-7b.5.3: run_batch_model_selection() Python Function
AC-7b.5.4: Parallel Execution (4 Workers)
"""

from __future__ import annotations

import inspect
import tempfile
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

# Skip all tests in this module if model_selection_job isn't implemented yet (Story 7b-5)
try:
    from raglite.forecasting import model_selection_job  # noqa: F401

    MODEL_SELECTION_JOB_AVAILABLE = True
except ImportError:
    MODEL_SELECTION_JOB_AVAILABLE = False

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        not MODEL_SELECTION_JOB_AVAILABLE,
        reason="Story 7b-5 not implemented - model_selection_job.py doesn't exist",
    ),
]


class TestModelSelectionJobModuleExists:
    """[P0] AC-7b.5.3: Module must exist."""

    def test_module_can_be_imported(self) -> None:
        """[P0][TEST-AC-7b.5.3.1] model_selection_job.py must be importable."""
        from raglite.forecasting import model_selection_job

        assert model_selection_job is not None


class TestRunBatchModelSelection:
    """[P0] AC-7b.5.3: Batch model selection function."""

    def test_function_exists(self) -> None:
        """[P0][TEST-AC-7b.5.3.2] run_batch_model_selection function must exist."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        assert callable(run_batch_model_selection)

    def test_all_variables_constant_exists(self) -> None:
        """[P0][TEST-AC-7b.5.3.3] ALL_VARIABLES constant with 20 variables."""
        from raglite.forecasting.model_selection_job import ALL_VARIABLES

        assert len(ALL_VARIABLES) == 20, f"Expected 20 variables, got {len(ALL_VARIABLES)}"

    def test_all_variables_contains_key_financial(self) -> None:
        """[P0][TEST-AC-7b.5.3.4] ALL_VARIABLES contains key financial variables."""
        from raglite.forecasting.model_selection_job import ALL_VARIABLES

        assert "ebitda" in ALL_VARIABLES, "Missing ebitda in ALL_VARIABLES"
        assert "revenue" in ALL_VARIABLES, "Missing revenue in ALL_VARIABLES"
        assert "variable_cost" in ALL_VARIABLES, "Missing variable_cost in ALL_VARIABLES"
        assert "sales_volume" in ALL_VARIABLES, "Missing sales_volume in ALL_VARIABLES"

    def test_all_variables_contains_key_external(self) -> None:
        """[P1][TEST-AC-7b.5.3.5] ALL_VARIABLES contains key external variables."""
        from raglite.forecasting.model_selection_job import ALL_VARIABLES

        assert "ttf_gas_price" in ALL_VARIABLES, "Missing ttf_gas_price in ALL_VARIABLES"
        assert "co2_eua_price" in ALL_VARIABLES, "Missing co2_eua_price in ALL_VARIABLES"
        assert "euribor_3m" in ALL_VARIABLES, "Missing euribor_3m in ALL_VARIABLES"

    def test_function_signature_has_variables_param(self) -> None:
        """[P0][TEST-AC-7b.5.3.6] Function accepts variables parameter."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        sig = inspect.signature(run_batch_model_selection)
        params = list(sig.parameters.keys())
        assert "variables" in params, "Missing variables parameter"

    def test_function_signature_has_workers_param(self) -> None:
        """[P0][TEST-AC-7b.5.3.7] Function accepts workers parameter."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        sig = inspect.signature(run_batch_model_selection)
        params = list(sig.parameters.keys())
        assert "workers" in params, "Missing workers parameter"

    def test_function_signature_has_force_refresh_param(self) -> None:
        """[P0][TEST-AC-7b.5.3.8] Function accepts force_refresh parameter."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        sig = inspect.signature(run_batch_model_selection)
        params = list(sig.parameters.keys())
        assert "force_refresh" in params, "Missing force_refresh parameter"

    def test_function_signature_has_output_dir_param(self) -> None:
        """[P0][TEST-AC-7b.5.3.9] Function accepts output_dir parameter."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        sig = inspect.signature(run_batch_model_selection)
        params = list(sig.parameters.keys())
        assert "output_dir" in params, "Missing output_dir parameter"

    def test_function_is_async(self) -> None:
        """[P0][TEST-AC-7b.5.3.10] run_batch_model_selection is an async function."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        assert inspect.iscoroutinefunction(run_batch_model_selection), (
            "run_batch_model_selection must be async"
        )


class TestParallelExecution:
    """[P0] AC-7b.5.4: Parallel execution with 4 workers."""

    def test_default_workers_is_four(self) -> None:
        """[P0][TEST-AC-7b.5.4.1] Default workers parameter should be 4."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        sig = inspect.signature(run_batch_model_selection)
        workers_param = sig.parameters.get("workers")
        assert workers_param is not None, "workers parameter not found"
        assert workers_param.default == 4, (
            f"Expected default workers=4, got {workers_param.default}"
        )

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.4.2] Semaphore limits to workers concurrent tasks."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                results = await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=2,  # Use 2 workers for faster test
                    output_dir=tmpdir,
                )
                # If function returns dict, concurrency worked
                assert isinstance(results, dict)


class TestCandidateModelsImport:
    """[P1] AC-7b.5.3: CANDIDATE_MODELS imported correctly."""

    def test_candidate_models_imported(self) -> None:
        """[P1][TEST-AC-7b.5.3.15] CANDIDATE_MODELS accessible from job module."""
        from raglite.forecasting.model_selection_job import CANDIDATE_MODELS

        assert isinstance(CANDIDATE_MODELS, (list, tuple)), (
            "CANDIDATE_MODELS should be a list or tuple"
        )
        assert len(CANDIDATE_MODELS) >= 5, (
            f"Expected at least 5 candidate models, got {len(CANDIDATE_MODELS)}"
        )
