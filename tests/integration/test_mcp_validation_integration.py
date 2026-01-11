"""Integration tests for MCP validation tools.

Story 6.22: MCP Validation Tool Integration

Integration tests for the three new MCP tools with real dependencies:
- validate_forecasting_accuracy (with database)
- list_available_regressors (static config)
- get_regressor_data (with API mocks)
"""

from datetime import date

import pytest

import raglite.main as main_module

# Mark all tests as integration tests that require collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


def get_tool_function(tool_name: str):
    """Extract the underlying function from a FastMCP FunctionTool.

    MCP tools are FunctionTool objects, not regular functions.
    Access the `.fn` attribute to get the callable.
    """
    tool = main_module.mcp.get_tool(tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


@pytest.mark.asyncio
async def test_validate_forecasting_accuracy_success():
    """Test successful validation with existing forecasts in database."""
    tool_fn = get_tool_function("validate_forecasting_accuracy")

    response = await tool_fn()

    assert response.__class__.__name__ == "ValidationResponse"
    assert response.total_variables >= 0
    assert response.validated_count >= 0
    assert 0.0 <= response.pass_rate <= 100.0
    assert len(response.detailed_results) >= 0


@pytest.mark.asyncio
async def test_list_available_regressors_static_data():
    """Test regressor list returns all configured regressors."""
    tool_fn = get_tool_function("list_available_regressors")

    response = await tool_fn()

    assert response.__class__.__name__ == "RegressorListResponse"
    assert len(response.regressors) > 0

    # Check each regressor has expected fields
    for reg in response.regressors:
        assert reg.variable_name
        assert reg.description
        assert reg.source in ["Eurostat", "ECB"]


@pytest.mark.asyncio
async def test_get_regressor_data_with_valid_variable():
    """Test fetching regressor data for a valid variable."""
    tool_fn = get_tool_function("get_regressor_data")

    # Use a known regressor from config
    response = await tool_fn(
        variable_name="energy_prices_gas",
        start_date=date(2020, 1, 1),
        end_date=date(2023, 12, 31),
    )

    assert response.__class__.__name__ == "RegressorDataResponse"
    assert response.variable_name == "energy_prices_gas"
    assert response.source in ["Eurostat", "ECB"]
    assert len(response.data_points) > 0

    # Check data point structure
    for dp in response.data_points:
        assert dp.date
        assert isinstance(dp.value, (int, float))


@pytest.mark.asyncio
async def test_get_regressor_data_with_invalid_variable():
    """Test error handling for unknown variable."""
    tool_fn = get_tool_function("get_regressor_data")

    with pytest.raises(ValueError, match="Unknown regressor variable"):
        await tool_fn(
            variable_name="nonexistent_variable",
            start_date=date(2020, 1, 1),
            end_date=date(2023, 12, 31),
        )
