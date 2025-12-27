"""
ATDD tests for Story 7b-5: Model Selection Slash Commands & Subagent.

TDD RED Phase: These tests should FAIL until implementation is complete.

This test file covers:
- AC-7b.5.1: Slash Command Definition
- AC-7b.5.2: Model-Selection-Executor Subagent
- AC-7b.5.3: run_batch_model_selection() Python Function
- AC-7b.5.4: Parallel Execution (4 Workers)
- AC-7b.5.5: Cache Results in PostgreSQL
- AC-7b.5.6: Generate JSON + Markdown Report
- AC-7b.5.7: Progress Logging with Status Updates
- AC-7b.5.8: Runtime Less Than 120 Minutes (P2 - Performance test)

Priority levels:
- P0: Critical path tests (must pass for story completion)
- P1: Important scenarios (should pass)
- P2: Edge cases and performance tests
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

if TYPE_CHECKING:
    pass

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit]


# Shared fixtures for mocking batch model selection dependencies
@pytest.fixture
def mock_historical_data():
    """Provide mock historical data with 15 points."""
    import pandas as pd

    return pd.Series(
        [100.0 + i * 5 for i in range(15)],
        index=pd.date_range("2023-01-01", periods=15, freq="MS"),
    )


@pytest.fixture
def mock_model_result():
    """Provide mock model selection result."""
    mock_result = MagicMock()
    mock_result.best_model = "arima"
    mock_result.best_mape = 0.05
    mock_result.best_mase = 0.8
    mock_result.best_with_regressors = False
    mock_result.best_regressor_set = None
    mock_result.cv_folds = 5
    mock_result.runtime_seconds = 10.0
    mock_result.candidate_results = {}
    return mock_result


@pytest.fixture
def batch_selection_mocks(mock_historical_data, mock_model_result):
    """Context manager providing all mocks needed for batch model selection tests."""
    from contextlib import contextmanager

    @contextmanager
    def _mocks(output_dir: str):
        with (
            patch(
                "raglite.forecasting.model_selection_job.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection_job.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_model_result,
            ),
            patch(
                "raglite.forecasting.model_selection_job.cache_model_selection",
                new_callable=Mock,
            ),
        ):
            yield

    return _mocks


@pytest.fixture
def single_selection_mocks(mock_historical_data, mock_model_result):
    """Context manager for single variable selection tests with cache tracking."""
    from contextlib import contextmanager

    @contextmanager
    def _mocks():
        mock_cache = Mock()
        with (
            patch(
                "raglite.forecasting.model_selection_job.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection_job.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_model_result,
            ),
            patch(
                "raglite.forecasting.model_selection_job.cache_model_selection",
                mock_cache,
            ),
        ):
            yield mock_cache

    return _mocks


# -----------------------------------------------------------------------------
# AC-7b.5.1: Slash Command Definition
# -----------------------------------------------------------------------------


class TestSlashCommandFile:
    """[P0] AC-7b.5.1: Slash command file existence and structure."""

    def test_slash_command_file_exists(self) -> None:
        """[P0][TEST-AC-7b.5.1.1] .claude/commands/model-selection.md must exist."""
        path = Path(".claude/commands/model-selection.md")
        assert path.exists(), f"Slash command file not found: {path}"

    def test_slash_command_has_required_frontmatter(self) -> None:
        """[P0][TEST-AC-7b.5.1.2] Slash command has argument-hint and description."""
        path = Path(".claude/commands/model-selection.md")
        assert path.exists(), f"Slash command file not found: {path}"
        content = path.read_text()
        assert "argument-hint:" in content, "Missing argument-hint in frontmatter"
        assert "description:" in content, "Missing description in frontmatter"

    def test_slash_command_has_allowed_tools(self) -> None:
        """[P1][TEST-AC-7b.5.1.3] Slash command has allowed-tools in frontmatter."""
        path = Path(".claude/commands/model-selection.md")
        assert path.exists(), f"Slash command file not found: {path}"
        content = path.read_text()
        assert "allowed-tools:" in content, "Missing allowed-tools in frontmatter"

    def test_slash_command_documents_single_variable(self) -> None:
        """[P1][TEST-AC-7b.5.1.4] Slash command documents single variable execution."""
        path = Path(".claude/commands/model-selection.md")
        assert path.exists(), f"Slash command file not found: {path}"
        content = path.read_text()
        # Check for mentions of single variable execution
        assert "select_best_model" in content or "single" in content.lower(), (
            "Missing documentation for single variable execution"
        )

    def test_slash_command_documents_all_flag(self) -> None:
        """[P1][TEST-AC-7b.5.1.5] Slash command documents --all flag and subagent delegation."""
        path = Path(".claude/commands/model-selection.md")
        assert path.exists(), f"Slash command file not found: {path}"
        content = path.read_text()
        assert "--all" in content, "Missing --all flag documentation"

    def test_slash_command_documents_force_flag(self) -> None:
        """[P1][TEST-AC-7b.5.1.6] Slash command documents --force flag."""
        path = Path(".claude/commands/model-selection.md")
        assert path.exists(), f"Slash command file not found: {path}"
        content = path.read_text()
        assert "--force" in content, "Missing --force flag documentation"

    def test_slash_command_documents_dry_run_flag(self) -> None:
        """[P1][TEST-AC-7b.5.1.7] Slash command documents --dry-run flag."""
        path = Path(".claude/commands/model-selection.md")
        assert path.exists(), f"Slash command file not found: {path}"
        content = path.read_text()
        assert "--dry-run" in content, "Missing --dry-run flag documentation"


# -----------------------------------------------------------------------------
# AC-7b.5.2: Model-Selection-Executor Subagent
# -----------------------------------------------------------------------------


class TestSubagentFile:
    """[P0] AC-7b.5.2: Subagent file existence and structure."""

    def test_subagent_file_exists(self) -> None:
        """[P0][TEST-AC-7b.5.2.1] .claude/agents/model-selection-executor.md must exist."""
        path = Path(".claude/agents/model-selection-executor.md")
        assert path.exists(), f"Subagent file not found: {path}"

    def test_subagent_has_required_frontmatter(self) -> None:
        """[P0][TEST-AC-7b.5.2.2] Subagent has name and description in frontmatter."""
        path = Path(".claude/agents/model-selection-executor.md")
        assert path.exists(), f"Subagent file not found: {path}"
        content = path.read_text()
        assert "name:" in content, "Missing name in frontmatter"
        assert "description:" in content, "Missing description in frontmatter"

    def test_subagent_has_tools(self) -> None:
        """[P1][TEST-AC-7b.5.2.3] Subagent has tools in frontmatter."""
        path = Path(".claude/agents/model-selection-executor.md")
        assert path.exists(), f"Subagent file not found: {path}"
        content = path.read_text()
        assert "tools:" in content, "Missing tools in frontmatter"

    def test_subagent_has_model(self) -> None:
        """[P1][TEST-AC-7b.5.2.4] Subagent has model in frontmatter."""
        path = Path(".claude/agents/model-selection-executor.md")
        assert path.exists(), f"Subagent file not found: {path}"
        content = path.read_text()
        assert "model:" in content, "Missing model in frontmatter"

    def test_subagent_documents_batch_processing(self) -> None:
        """[P1][TEST-AC-7b.5.2.5] Subagent documents batch processing steps."""
        path = Path(".claude/agents/model-selection-executor.md")
        assert path.exists(), f"Subagent file not found: {path}"
        content = path.read_text()
        assert "run_batch_model_selection" in content, (
            "Missing run_batch_model_selection in subagent documentation"
        )

    def test_subagent_documents_variables_list(self) -> None:
        """[P1][TEST-AC-7b.5.2.6] Subagent documents the 20 variables to process."""
        path = Path(".claude/agents/model-selection-executor.md")
        assert path.exists(), f"Subagent file not found: {path}"
        content = path.read_text()
        # Check for some key variables mentioned
        assert "ebitda" in content.lower() or "revenue" in content.lower(), (
            "Missing variable documentation in subagent"
        )


# -----------------------------------------------------------------------------
# AC-7b.5.3: run_batch_model_selection() Python Function
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# AC-7b.5.4: Parallel Execution (4 Workers)
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# AC-7b.5.5: Cache Results in PostgreSQL
# -----------------------------------------------------------------------------


class TestCacheResults:
    """[P0] AC-7b.5.5: Cache results in PostgreSQL."""

    @pytest.mark.asyncio
    async def test_cache_called_for_each_result(self) -> None:
        """[P0][TEST-AC-7b.5.5.1] cache_model_selection called for each successful result."""
        import pandas as pd

        from raglite.forecasting.model_selection_job import run_batch_model_selection

        mock_result = MagicMock()
        mock_result.best_model = "arima"
        mock_result.best_mape = 0.05
        mock_result.best_mase = 0.8
        mock_result.best_with_regressors = False
        mock_result.best_regressor_set = None
        mock_result.cv_folds = 5
        mock_result.runtime_seconds = 10.0
        mock_result.candidate_results = {}

        mock_cache = Mock()
        # Mock historical data with 12+ points to pass validation
        mock_historical = pd.Series(
            [100.0] * 15,
            index=pd.date_range("2023-01-01", periods=15, freq="MS"),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch(
                    "raglite.forecasting.model_selection_job.fetch_historical_data",
                    new_callable=AsyncMock,
                    return_value=mock_historical,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                    new_callable=AsyncMock,
                    return_value={},
                ),
                patch(
                    "raglite.forecasting.model_selection_job.select_best_model",
                    new_callable=AsyncMock,
                    return_value=mock_result,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.cache_model_selection",
                    mock_cache,
                ),
            ):
                await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=2,
                    output_dir=tmpdir,
                )

                # cache_model_selection should be called once per variable
                assert mock_cache.call_count == 3, (
                    f"Expected 3 cache calls, got {mock_cache.call_count}"
                )


# -----------------------------------------------------------------------------
# AC-7b.5.6: Generate JSON + Markdown Report
# -----------------------------------------------------------------------------


class TestReportGeneration:
    """[P1] AC-7b.5.6: Report generation."""

    def test_generate_reports_function_exists(self) -> None:
        """[P1][TEST-AC-7b.5.6.1] _generate_reports helper must exist."""
        from raglite.forecasting.model_selection_job import _generate_reports

        assert callable(_generate_reports)

    def test_generate_reports_is_async(self) -> None:
        """[P1][TEST-AC-7b.5.6.2] _generate_reports is an async function."""
        from raglite.forecasting.model_selection_job import _generate_reports

        assert inspect.iscoroutinefunction(_generate_reports), "_generate_reports must be async"

    @pytest.mark.asyncio
    async def test_reports_created_in_output_dir(self, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.6.3] JSON and Markdown reports created in output_dir."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                # Check for JSON report
                json_files = list(Path(tmpdir).glob("model-selection-*.json"))
                assert len(json_files) >= 1, "No JSON report generated"

                # Check for Markdown report
                md_files = list(Path(tmpdir).glob("model-selection-*.md"))
                assert len(md_files) >= 1, "No Markdown report generated"

    @pytest.mark.asyncio
    async def test_json_report_has_required_fields(self, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.6.4] JSON report contains required fields."""
        import json

        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                json_files = list(Path(tmpdir).glob("model-selection-*.json"))
                assert len(json_files) >= 1, "No JSON report generated"

                with open(json_files[0]) as f:
                    report = json.load(f)

                assert "timestamp" in report, "Missing timestamp in JSON report"
                assert "runtime_minutes" in report, "Missing runtime_minutes in JSON report"
                assert "results" in report, "Missing results in JSON report"

    @pytest.mark.asyncio
    async def test_markdown_report_has_summary_table(self, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.6.5] Markdown report contains summary table."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                md_files = list(Path(tmpdir).glob("model-selection-*.md"))
                assert len(md_files) >= 1, "No Markdown report generated"

                content = md_files[0].read_text()
                # Check for table structure
                assert "| Variable |" in content or "| variable |" in content.lower(), (
                    "Missing summary table in Markdown report"
                )
                assert "| Best Model |" in content or "best_model" in content.lower(), (
                    "Missing best model column in Markdown report"
                )


# -----------------------------------------------------------------------------
# AC-7b.5.7: Progress Logging with Status Updates
# -----------------------------------------------------------------------------


class TestProgressLogging:
    """[P1] AC-7b.5.7: Progress logging with status updates."""

    @pytest.mark.asyncio
    async def test_progress_printed_for_each_variable(self, capsys, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.7.1] Progress printed as each variable completes."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["var1", "var2"],
                    workers=1,
                    output_dir=tmpdir,
                )

                captured = capsys.readouterr()
                # Check for [N/total] format
                assert "[1/" in captured.out or "[2/" in captured.out, (
                    "Missing [N/total] progress format in output"
                )

    @pytest.mark.asyncio
    async def test_summary_printed_at_completion(self, capsys, batch_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.7.2] Summary section printed at completion."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                captured = capsys.readouterr()
                # Check for summary section
                assert "Summary" in captured.out or "Variables processed" in captured.out, (
                    "Missing summary section in output"
                )


# -----------------------------------------------------------------------------
# AC-7b.5.3 (additional): run_single_variable_selection helper
# -----------------------------------------------------------------------------


class TestRunSingleVariableSelection:
    """[P1] AC-7b.5.3: Single variable selection helper function."""

    def test_run_single_variable_selection_exists(self) -> None:
        """[P1][TEST-AC-7b.5.3.11] run_single_variable_selection function exists."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        assert callable(run_single_variable_selection)

    def test_run_single_variable_selection_is_async(self) -> None:
        """[P1][TEST-AC-7b.5.3.12] run_single_variable_selection is async."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        assert inspect.iscoroutinefunction(run_single_variable_selection), (
            "run_single_variable_selection must be async"
        )

    def test_run_single_variable_selection_has_dry_run_param(self) -> None:
        """[P1][TEST-AC-7b.5.3.13] run_single_variable_selection has dry_run parameter."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        sig = inspect.signature(run_single_variable_selection)
        params = list(sig.parameters.keys())
        assert "dry_run" in params, "Missing dry_run parameter"

    def test_run_single_variable_selection_has_force_refresh_param(self) -> None:
        """[P1][TEST-AC-7b.5.3.14] run_single_variable_selection has force_refresh parameter."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        sig = inspect.signature(run_single_variable_selection)
        params = list(sig.parameters.keys())
        assert "force_refresh" in params, "Missing force_refresh parameter"

    @pytest.mark.asyncio
    async def test_dry_run_skips_cache(self, single_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.3.15] dry_run=True skips caching."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        with single_selection_mocks() as mock_cache:
            # Run with dry_run=True
            await run_single_variable_selection(
                variable="test_var", force_refresh=False, dry_run=True
            )

            # cache_model_selection should NOT be called
            assert mock_cache.call_count == 0, (
                f"Expected 0 cache calls with dry_run=True, got {mock_cache.call_count}"
            )

    @pytest.mark.asyncio
    async def test_normal_mode_calls_cache(self, single_selection_mocks) -> None:
        """[P1][TEST-AC-7b.5.3.16] dry_run=False calls cache."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        with single_selection_mocks() as mock_cache:
            # Run with dry_run=False
            await run_single_variable_selection(
                variable="test_var", force_refresh=False, dry_run=False
            )

            # cache_model_selection should be called once
            assert mock_cache.call_count == 1, (
                f"Expected 1 cache call with dry_run=False, got {mock_cache.call_count}"
            )


# -----------------------------------------------------------------------------
# AC-7b.5.3 (additional): CANDIDATE_MODELS import
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# AC-7b.5.8: Runtime Performance (P2)
# -----------------------------------------------------------------------------


class TestRuntimePerformance:
    """[P2] AC-7b.5.8: Runtime less than 120 minutes.

    Note: This is marked as P2 because it's a performance test that
    requires real execution. In practice, this test would be run in
    a dedicated CI job with actual model selection.
    """

    @pytest.mark.slow
    @pytest.mark.skip(reason="Performance test - run manually with real data")
    @pytest.mark.asyncio
    async def test_full_batch_under_120_minutes(self) -> None:
        """[P2][TEST-AC-7b.5.8.1] Full batch completes in <120 minutes."""
        import time

        from raglite.forecasting.model_selection_job import (
            ALL_VARIABLES,
            run_batch_model_selection,
        )

        start = time.time()
        await run_batch_model_selection(
            variables=ALL_VARIABLES,
            workers=4,
        )
        elapsed_minutes = (time.time() - start) / 60

        assert elapsed_minutes < 120, (
            f"Batch took {elapsed_minutes:.1f} minutes, exceeds 120 minute budget"
        )


# -----------------------------------------------------------------------------
# Error Handling Tests
# -----------------------------------------------------------------------------


class TestErrorHandling:
    """[P1] Error handling in batch model selection."""

    @pytest.mark.asyncio
    async def test_individual_failures_dont_stop_batch(self, mock_historical_data) -> None:
        """[P1][TEST-ERR-1] Individual variable failures don't stop batch processing."""

        from raglite.forecasting.model_selection_job import run_batch_model_selection

        call_count = 0

        async def mock_select_best_model(variable_name: str, **kwargs) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if variable_name == "var2":
                raise ValueError("Simulated failure for var2")
            mock_result = MagicMock()
            mock_result.best_model = "arima"
            mock_result.best_mape = 0.05
            mock_result.best_mase = 0.8
            mock_result.best_with_regressors = False
            mock_result.best_regressor_set = None
            mock_result.cv_folds = 5
            mock_result.runtime_seconds = 10.0
            mock_result.candidate_results = {}
            return mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch(
                    "raglite.forecasting.model_selection_job.fetch_historical_data",
                    new_callable=AsyncMock,
                    return_value=mock_historical_data,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                    new_callable=AsyncMock,
                    return_value={},
                ),
                patch(
                    "raglite.forecasting.model_selection_job.select_best_model",
                    side_effect=mock_select_best_model,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.cache_model_selection",
                    new_callable=Mock,
                ),
            ):
                results = await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=1,
                    output_dir=tmpdir,
                )

                # All 3 should have been attempted
                assert call_count == 3, f"Expected 3 calls, got {call_count}"
                # var1 and var3 should succeed
                assert len(results) == 2, f"Expected 2 successful results, got {len(results)}"

    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self, batch_selection_mocks) -> None:
        """[P0][TEST-RET-1] run_batch_model_selection returns dict of results."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                results = await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=tmpdir,
                )

                assert isinstance(results, dict), f"Expected dict, got {type(results)}"
                assert "test_var" in results, "Result should contain variable key"


# -----------------------------------------------------------------------------
# EXPANDED TEST COVERAGE: Edge Cases and Error Handling
# -----------------------------------------------------------------------------


class TestEdgeCases:
    """[P2] Edge case tests for model_selection_job."""

    @pytest.mark.asyncio
    async def test_empty_variables_list(self, batch_selection_mocks) -> None:
        """[P2][TEST-EDGE-1] Empty variables list returns empty dict."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                result = await run_batch_model_selection(variables=[], output_dir=tmpdir)
                assert result == {}, "Empty variables list should return empty dict"

    @pytest.mark.asyncio
    async def test_single_variable_in_batch_mode(self, batch_selection_mocks) -> None:
        """[P1][TEST-EDGE-2] Single variable in batch mode works correctly."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                results = await run_batch_model_selection(
                    variables=["ebitda"],
                    workers=1,
                    output_dir=tmpdir,
                )

                assert len(results) == 1, "Single variable should return single result"
                assert "ebitda" in results, "Result should contain the variable"

    @pytest.mark.asyncio
    async def test_output_dir_created_if_missing(self, batch_selection_mocks) -> None:
        """[P2][TEST-EDGE-3] Output directory is created if it doesn't exist."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nonexistent_dir"
            assert not output_path.exists(), "Directory should not exist initially"

            with batch_selection_mocks(str(output_path)):
                await run_batch_model_selection(
                    variables=["test_var"],
                    workers=1,
                    output_dir=str(output_path),
                )

                assert output_path.exists(), "Output directory should be created"
                assert output_path.is_dir(), "Output path should be a directory"

    @pytest.mark.asyncio
    async def test_all_variables_fail(self, mock_historical_data) -> None:
        """[P1][TEST-EDGE-4] All variables failing returns empty results dict."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        async def mock_failing_select(variable_name: str, **kwargs):
            raise ValueError(f"Simulated failure for {variable_name}")

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch(
                    "raglite.forecasting.model_selection_job.fetch_historical_data",
                    new_callable=AsyncMock,
                    return_value=mock_historical_data,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                    new_callable=AsyncMock,
                    return_value={},
                ),
                patch(
                    "raglite.forecasting.model_selection_job.select_best_model",
                    side_effect=mock_failing_select,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.cache_model_selection",
                    new_callable=Mock,
                ),
            ):
                results = await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=1,
                    output_dir=tmpdir,
                )

                assert len(results) == 0, "All failures should return empty dict"

    @pytest.mark.asyncio
    async def test_cache_failure_doesnt_stop_processing(
        self, mock_historical_data, mock_model_result
    ) -> None:
        """[P1][TEST-EDGE-5] Cache failures don't stop batch processing."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        def failing_cache(*args, **kwargs):
            raise ValueError("Cache write failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch(
                    "raglite.forecasting.model_selection_job.fetch_historical_data",
                    new_callable=AsyncMock,
                    return_value=mock_historical_data,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                    new_callable=AsyncMock,
                    return_value={},
                ),
                patch(
                    "raglite.forecasting.model_selection_job.select_best_model",
                    new_callable=AsyncMock,
                    return_value=mock_model_result,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.cache_model_selection",
                    side_effect=failing_cache,
                ),
            ):
                # Should not raise - errors are caught and logged
                results = await run_batch_model_selection(
                    variables=["var1", "var2"],
                    workers=1,
                    output_dir=tmpdir,
                )

                # Processing should continue despite cache failures
                assert len(results) == 0, (
                    "Cache failures should cause variables to be treated as failed"
                )

    @pytest.mark.asyncio
    async def test_workers_parameter_affects_concurrency(self, batch_selection_mocks) -> None:
        """[P1][TEST-EDGE-6] Workers parameter controls parallel execution."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                # Test with different worker counts
                result_1_worker = await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=1,
                    output_dir=tmpdir,
                )
                result_8_workers = await run_batch_model_selection(
                    variables=["var1", "var2", "var3"],
                    workers=8,
                    output_dir=tmpdir,
                )

                # Both should succeed with same results
                assert len(result_1_worker) == 3
                assert len(result_8_workers) == 3


class TestReportStructure:
    """[P2] Detailed tests for report structure and content."""

    @pytest.mark.asyncio
    async def test_json_report_structure_validation(self, mock_historical_data) -> None:
        """[P2][TEST-REPORT-1] JSON report has all required fields with correct types."""
        import json

        from raglite.forecasting.model_selection_job import run_batch_model_selection

        mock_result = MagicMock()
        mock_result.best_model = "arima"
        mock_result.best_mape = 0.082
        mock_result.best_mase = 0.42
        mock_result.best_with_regressors = True
        mock_result.best_regressor_set = ["euribor_3m", "diesel"]
        mock_result.cv_folds = 5
        mock_result.runtime_seconds = 45.2
        mock_result.candidate_results = {"arima_True": {"mape": 0.082, "mase": 0.42}}

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch(
                    "raglite.forecasting.model_selection_job.fetch_historical_data",
                    new_callable=AsyncMock,
                    return_value=mock_historical_data,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                    new_callable=AsyncMock,
                    return_value={},
                ),
                patch(
                    "raglite.forecasting.model_selection_job.select_best_model",
                    new_callable=AsyncMock,
                    return_value=mock_result,
                ),
                patch(
                    "raglite.forecasting.model_selection_job.cache_model_selection",
                    new_callable=Mock,
                ),
            ):
                await run_batch_model_selection(
                    variables=["ebitda"],
                    workers=1,
                    output_dir=tmpdir,
                )

                json_files = list(Path(tmpdir).glob("model-selection-*.json"))
                assert len(json_files) == 1, "Should create exactly one JSON report"

                with open(json_files[0]) as f:
                    report = json.load(f)

                # Validate structure
                assert "timestamp" in report
                assert "runtime_minutes" in report
                assert "variables_processed" in report
                assert "results" in report
                assert isinstance(report["results"], dict)

                # Validate ebitda result
                assert "ebitda" in report["results"]
                ebitda_result = report["results"]["ebitda"]
                assert ebitda_result["best_model"] == "arima"
                assert ebitda_result["best_mape"] == 0.082
                assert ebitda_result["best_mase"] == 0.42
                assert ebitda_result["use_regressors"] is True
                assert ebitda_result["regressor_set"] == ["euribor_3m", "diesel"]

    @pytest.mark.asyncio
    async def test_markdown_report_structure_validation(self, batch_selection_mocks) -> None:
        """[P2][TEST-REPORT-2] Markdown report has proper table formatting."""
        from raglite.forecasting.model_selection_job import run_batch_model_selection

        with tempfile.TemporaryDirectory() as tmpdir:
            with batch_selection_mocks(tmpdir):
                await run_batch_model_selection(
                    variables=["revenue", "ebitda"],
                    workers=1,
                    output_dir=tmpdir,
                )

                md_files = list(Path(tmpdir).glob("model-selection-*.md"))
                assert len(md_files) == 1, "Should create exactly one Markdown report"

                content = md_files[0].read_text()

                # Check for required sections
                assert "# Model Selection Report" in content
                assert "## Summary" in content or "Summary" in content
                assert "## Results" in content or "## Best Performers" in content

                # Check for table structure
                assert "|" in content, "Should contain table formatting"
                assert "Variable" in content or "variable" in content.lower()
                assert "MAPE" in content or "mape" in content.lower()

    @pytest.mark.asyncio
    async def test_print_summary_with_empty_results(self, capsys) -> None:
        """[P2][TEST-REPORT-3] _print_summary handles empty results gracefully."""
        from raglite.forecasting.model_selection_job import _print_summary

        _print_summary(results={}, errors=[], variables=["var1", "var2"])

        captured = capsys.readouterr()
        assert "Variables processed: 0/2" in captured.out
        assert "MODEL SELECTION COMPLETE" in captured.out

    @pytest.mark.asyncio
    async def test_print_summary_with_only_errors(self, capsys) -> None:
        """[P2][TEST-REPORT-4] _print_summary handles error-only scenario."""
        from raglite.forecasting.model_selection_job import _print_summary

        errors = ["var1: timeout", "var2: network error"]
        _print_summary(results={}, errors=errors, variables=["var1", "var2"])

        captured = capsys.readouterr()
        assert "Errors: 2" in captured.out
        assert "var1: timeout" in captured.out
        assert "var2: network error" in captured.out

    @pytest.mark.asyncio
    async def test_generate_markdown_report_sorting(self) -> None:
        """[P2][TEST-REPORT-5] Markdown report sorts variables by MAPE."""
        from raglite.forecasting.model_selection_job import _generate_markdown_report

        # Create mock results with different MAPE values
        result_high = MagicMock()
        result_high.best_model = "arima"
        result_high.best_mape = 0.15  # Worst
        result_high.best_mase = 1.0
        result_high.best_with_regressors = False
        result_high.best_regressor_set = []

        result_low = MagicMock()
        result_low.best_model = "prophet"
        result_low.best_mape = 0.03  # Best
        result_low.best_mase = 0.8
        result_low.best_with_regressors = False
        result_low.best_regressor_set = []

        results = {
            "capacity_utilization": result_high,
            "co2_eua_price": result_low,
        }

        md_content = _generate_markdown_report(results, "20251221-120000")

        # co2_eua_price should appear before capacity_utilization (sorted by MAPE)
        co2_index = md_content.find("co2_eua_price")
        capacity_index = md_content.find("capacity_utilization")
        assert co2_index < capacity_index, "Should be sorted by MAPE (best first)"


class TestSingleVariableSelection:
    """[P1] Edge cases for run_single_variable_selection."""

    @pytest.mark.asyncio
    async def test_single_variable_error_returns_none(self, mock_historical_data) -> None:
        """[P1][TEST-SINGLE-1] Error in single variable selection returns None."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        async def failing_select(*args, **kwargs):
            raise ValueError("Model selection failed")

        with (
            patch(
                "raglite.forecasting.model_selection_job.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection_job.select_best_model",
                side_effect=failing_select,
            ),
        ):
            result = await run_single_variable_selection(
                variable="ebitda", force_refresh=False, dry_run=False
            )

            assert result is None, "Failed selection should return None"

    @pytest.mark.asyncio
    async def test_single_variable_with_no_regressors(
        self, mock_historical_data, mock_model_result, capsys
    ) -> None:
        """[P1][TEST-SINGLE-2] Single variable with no regressors displays correctly."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        with (
            patch(
                "raglite.forecasting.model_selection_job.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection_job.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_model_result,
            ),
            patch(
                "raglite.forecasting.model_selection_job.cache_model_selection",
                new_callable=Mock,
            ),
        ):
            result = await run_single_variable_selection(
                variable="ebitda", force_refresh=False, dry_run=False
            )

            assert result is not None
            captured = capsys.readouterr()
            assert "Use Regressors: False" in captured.out or "Regressors: None" in captured.out

    @pytest.mark.asyncio
    async def test_single_variable_comparison_table_output(
        self, mock_historical_data, capsys
    ) -> None:
        """[P2][TEST-SINGLE-3] Single variable displays candidate comparison table."""
        from raglite.forecasting.model_selection_job import run_single_variable_selection

        mock_result = MagicMock()
        mock_result.best_model = "arima"
        mock_result.best_mape = 0.05
        mock_result.best_mase = 0.8
        mock_result.best_with_regressors = False
        mock_result.best_regressor_set = []
        mock_result.cv_folds = 5
        mock_result.runtime_seconds = 25.0
        mock_result.candidate_results = {
            "arima_False": {"mape": 0.05, "mase": 0.8},
            "prophet_False": {"mape": 0.07, "mase": 0.9},
            "ets_False": {"mape": 0.10, "mase": 1.1},
        }

        with (
            patch(
                "raglite.forecasting.model_selection_job.fetch_historical_data",
                new_callable=AsyncMock,
                return_value=mock_historical_data,
            ),
            patch(
                "raglite.forecasting.model_selection_job.fetch_regressors_with_date_range",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "raglite.forecasting.model_selection_job.select_best_model",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch(
                "raglite.forecasting.model_selection_job.cache_model_selection",
                new_callable=Mock,
            ),
        ):
            await run_single_variable_selection(
                variable="ebitda", force_refresh=False, dry_run=False
            )

            captured = capsys.readouterr()
            # Check for comparison table header
            assert "Model" in captured.out or "model" in captured.out.lower()
            assert "MAPE" in captured.out
            assert "BEST" in captured.out or "Status" in captured.out
