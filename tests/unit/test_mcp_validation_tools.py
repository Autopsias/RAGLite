"""Unit tests for MCP validation tools.

Story 6.22: MCP Validation Tool Integration

Tests for the three new MCP tools:
- validate_forecasting_accuracy
- list_available_regressors
- get_regressor_data
"""

from datetime import date
from unittest.mock import patch

import pytest

# Lazy import pattern: import raglite.shared.models only (fast)
# raglite.main is imported inside get_tool_function() to avoid slow module-level import
from raglite.shared.models import (
    RegressorDataResponse,
    RegressorListResponse,
    ValidationResponse,
)

# Module-level cache for lazy-loaded main_module
_main_module = None


def _get_main_module():
    """Lazy load raglite.main to avoid slow module-level import during test collection."""
    global _main_module
    if _main_module is None:
        import raglite.main as main_module

        _main_module = main_module
    return _main_module


# Get the actual tool functions from FastMCP-wrapped tools
def get_tool_function(tool_name: str):
    """Extract the underlying function from a FastMCP FunctionTool."""
    main_module = _get_main_module()

    # Map tool names to their FunctionTool objects
    func_map = {
        "validate_forecasting_accuracy": main_module.validate_forecasting_accuracy,
        "list_available_regressors": main_module.list_available_regressors,
        "get_regressor_data": main_module.get_regressor_data,
    }

    if tool_name not in func_map:
        raise ValueError(f"Tool {tool_name} not found")

    # Get the FunctionTool object and extract the actual function
    tool_obj = func_map[tool_name]
    if hasattr(tool_obj, "fn"):
        return tool_obj.fn

    raise ValueError(f"Could not extract function from {tool_name}")


# =============================================================================
# Tests for validate_forecasting_accuracy
# =============================================================================


@pytest.mark.asyncio
async def test_validate_accuracy_basic():
    """Test that validate_forecasting_accuracy returns valid response."""
    validate_func = get_tool_function("validate_forecasting_accuracy")

    with patch("scripts.validate_forecasting_unified.run_unified_validation") as mock_validation:
        # Create mock validation result
        from raglite.forecasting.validation_schema import (
            ModelPerformanceStats,
            QualityGateResult,
            UnifiedValidationResult,
            VariableValidationResult,
        )

        mock_result = UnifiedValidationResult(
            timestamp="2025-12-13T10:00:00Z",
            runtime_seconds=120.5,
            mape_method="holdout",
            variables_tested=12,
            variables_passed=10,
            pass_rate=0.833,
            average_mape=5.2,
            variable_results=[
                VariableValidationResult(
                    variable_name="revenue",
                    display_name="Revenue",
                    target_mape=5.0,
                    actual_mape=2.8,
                    passed=True,
                    ensemble_weights={"prophet": 0.4, "linear": 0.3, "xgboost": 0.3},
                    best_model="prophet",
                )
            ],
            model_performance={
                "prophet": ModelPerformanceStats(
                    model_name="prophet", avg_mape=3.5, variables_used=10, avg_runtime_seconds=15.0
                )
            },
            quality_gate=QualityGateResult(
                passed=True,
                minimum_required=10,
                actual_passed=10,
                variable_cost_mape=6.5,
                variable_cost_target=8.0,
            ),
        )

        mock_validation.return_value = mock_result

        # Call the tool
        response = await validate_func()

        # Assertions
        assert response.__class__.__name__ == "ValidationResponse"
        assert response.variables_tested == 12
        assert response.variables_passed == 10
        assert response.pass_rate == 0.833
        assert response.quality_gate_passed is True
        assert len(response.variable_results) == 1
        assert response.variable_results[0].variable_name == "revenue"


@pytest.mark.asyncio
async def test_validate_accuracy_single_metric():
    """Test validation of a single metric."""
    validate_func = get_tool_function("validate_forecasting_accuracy")

    with patch("scripts.validate_forecasting_unified.run_unified_validation") as mock_validation:
        from raglite.forecasting.validation_schema import (
            QualityGateResult,
            UnifiedValidationResult,
            VariableValidationResult,
        )

        mock_result = UnifiedValidationResult(
            timestamp="2025-12-13T10:00:00Z",
            runtime_seconds=15.0,
            mape_method="holdout",
            variables_tested=1,
            variables_passed=1,
            pass_rate=1.0,
            average_mape=2.8,
            variable_results=[
                VariableValidationResult(
                    variable_name="revenue",
                    display_name="Revenue",
                    target_mape=5.0,
                    actual_mape=2.8,
                    passed=True,
                )
            ],
            model_performance={},
            quality_gate=QualityGateResult(
                passed=True,
                minimum_required=10,
                actual_passed=1,
                variable_cost_mape=None,
                variable_cost_target=8.0,
            ),
        )

        mock_validation.return_value = mock_result

        # Call with specific metric
        response = await validate_func(metrics=["revenue"])

        # Assertions
        assert response.variables_tested == 1
        assert response.variables_passed == 1
        assert response.pass_rate == 1.0
        mock_validation.assert_called_once()


@pytest.mark.asyncio
async def test_validate_accuracy_timeout():
    """Test graceful timeout handling with custom timeout."""

    validate_func = get_tool_function("validate_forecasting_accuracy")

    with patch("asyncio.wait_for") as mock_wait_for:
        # Simulate timeout
        mock_wait_for.side_effect = TimeoutError()

        # Call the tool with custom timeout
        custom_timeout = 120.0
        response = await validate_func(timeout_seconds=custom_timeout)

        # Should return error response, not raise
        assert response.__class__.__name__ == "ValidationResponse"
        assert response.variables_tested == 0
        assert response.variables_passed == 0
        assert response.quality_gate_passed is False
        assert response.runtime_seconds == custom_timeout  # Uses custom timeout


# =============================================================================
# Tests for list_available_regressors
# =============================================================================


@pytest.mark.asyncio
async def test_list_regressors_all():
    """Test listing all regressors."""
    list_func = get_tool_function("list_available_regressors")
    response = await list_func()

    # Assertions
    assert response.__class__.__name__ == "RegressorListResponse"
    assert response.total_count > 0
    assert response.available_count > 0
    assert len(response.regressors) == response.total_count

    # Check regressor details
    for regressor in response.regressors:
        assert regressor.name is not None
        assert regressor.display_name is not None
        assert regressor.source is not None
        assert regressor.available is True


@pytest.mark.asyncio
async def test_list_regressors_filtered():
    """Test filtering regressors by metric."""
    list_func = get_tool_function("list_available_regressors")
    response = await list_func(metric="revenue")

    # Assertions
    assert response.__class__.__name__ == "RegressorListResponse"
    assert response.total_count > 0

    # Check that we get relevant regressors for revenue
    regressor_names = [r.name for r in response.regressors]
    assert any(
        name in regressor_names
        for name in ["construction_output", "gdp_growth", "euribor_3m", "building_permits"]
    )


# =============================================================================
# Tests for get_regressor_data
# =============================================================================


@pytest.mark.asyncio
async def test_get_regressor_data():
    """Test fetching regressor data successfully."""
    get_data_func = get_tool_function("get_regressor_data")

    with patch("raglite.forecasting.regressor_fetch.fetch_single_regressor") as mock_fetch:
        import pandas as pd

        # Create mock series
        dates = pd.date_range(start="2023-01-01", end="2023-12-01", freq="ME")
        values = [100.0 + i for i in range(len(dates))]
        mock_series = pd.Series(values, index=dates)
        mock_fetch.return_value = mock_series

        # Call the tool
        response = await get_data_func(regressor="construction_output")

        # Assertions
        assert response.__class__.__name__ == "RegressorDataResponse"
        assert response.regressor_name == "construction_output"
        assert response.display_name == "Construction Production Index (Portugal)"
        assert response.source == "Eurostat"
        assert response.record_count == len(dates)
        assert len(response.data_points) == len(dates)
        assert response.visualization_hint == "line_chart"


@pytest.mark.asyncio
async def test_get_regressor_data_invalid():
    """Test error handling for unknown regressor."""
    get_data_func = get_tool_function("get_regressor_data")

    with pytest.raises(ValueError, match="Unknown regressor"):
        await get_data_func(regressor="invalid_regressor")


@pytest.mark.asyncio
async def test_get_regressor_data_with_dates():
    """Test fetching regressor data with custom date range."""
    get_data_func = get_tool_function("get_regressor_data")

    with patch("raglite.forecasting.regressor_fetch.fetch_single_regressor") as mock_fetch:
        import pandas as pd

        # Create mock series
        dates = pd.date_range(start="2024-01-01", end="2024-06-01", freq="ME")
        values = [100.0 + i for i in range(len(dates))]
        mock_series = pd.Series(values, index=dates)
        mock_fetch.return_value = mock_series

        # Call with custom dates
        response = await get_data_func(
            regressor="euribor_3m", start_date="2024-01-01", end_date="2024-06-01"
        )

        # Assertions
        assert response.regressor_name == "euribor_3m"
        assert response.display_name == "3-Month EURIBOR Rate"
        assert response.unit == "%"
        assert response.record_count == len(dates)

        # Check that fetch was called with correct dates
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert call_args[0] == "euribor_3m"
        assert call_args[1] == date(2024, 1, 1)
        assert call_args[2] == date(2024, 6, 1)


# =============================================================================
# Test Response Models
# =============================================================================


def test_validation_response_schema():
    """Test ValidationResponse model schema."""
    from raglite.shared.models import VariableValidationDetail

    response = ValidationResponse(
        timestamp="2025-12-13T10:00:00Z",
        runtime_seconds=120.5,
        mape_method="holdout",
        variables_tested=12,
        variables_passed=10,
        pass_rate=0.833,
        average_mape=5.2,
        quality_gate_passed=True,
        variable_cost_mape=6.5,
        variable_results=[
            VariableValidationDetail(
                variable_name="revenue",
                display_name="Revenue",
                target_mape=5.0,
                actual_mape=2.8,
                passed=True,
            )
        ],
    )

    # Test serialization
    data = response.model_dump()
    assert data["variables_tested"] == 12
    assert data["quality_gate_passed"] is True
    assert len(data["variable_results"]) == 1


def test_regressor_list_response_schema():
    """Test RegressorListResponse model schema."""
    from raglite.shared.models import RegressorInfo

    response = RegressorListResponse(
        regressors=[
            RegressorInfo(
                name="euribor_3m",
                display_name="3-Month EURIBOR Rate",
                source="ECB",
                available=True,
                unit="%",
            )
        ],
        total_count=1,
        available_count=1,
    )

    # Test serialization
    data = response.model_dump()
    assert data["total_count"] == 1
    assert data["available_count"] == 1
    assert len(data["regressors"]) == 1
    assert data["regressors"][0]["name"] == "euribor_3m"


def test_regressor_data_response_schema():
    """Test RegressorDataResponse model schema."""
    from raglite.shared.models import RegressorDataPoint

    response = RegressorDataResponse(
        regressor_name="construction_output",
        display_name="Construction Production Index",
        source="Eurostat",
        unit="Index",
        data_points=[
            RegressorDataPoint(date=date(2024, 1, 1), value=100.5),
            RegressorDataPoint(date=date(2024, 2, 1), value=101.2),
        ],
        record_count=2,
        date_range="2024-01-01 to 2024-02-01",
        visualization_hint="line_chart",
    )

    # Test serialization
    data = response.model_dump()
    assert data["regressor_name"] == "construction_output"
    assert data["record_count"] == 2
    assert len(data["data_points"]) == 2
    assert data["visualization_hint"] == "line_chart"
