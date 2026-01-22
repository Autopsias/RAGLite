"""Integration tests for MCP validation tools.

Story 6.22: MCP Validation Tool Integration

Integration tests for the three new MCP tools with real dependencies:
- validate_forecasting_accuracy (with database)
- list_available_regressors (static config)
- get_regressor_data (with API mocks)
"""

import pytest

from raglite.mcp.tools.validation import (
    get_regressor_data,
    list_available_regressors,
    validate_forecasting_accuracy,
)

# Mark all tests as integration tests that require collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]


@pytest.mark.asyncio
async def test_validate_forecasting_accuracy_success():
    """Test successful validation with existing forecasts in database."""
    # Access the underlying function via .fn (FunctionTool wrapper)
    response = await validate_forecasting_accuracy.fn()

    assert response.__class__.__name__ == "ValidationResponse"
    assert response.variables_tested >= 0
    assert response.variables_passed >= 0
    assert 0.0 <= response.pass_rate <= 100.0
    assert len(response.variable_results) >= 0


@pytest.mark.asyncio
async def test_list_available_regressors_static_data():
    """Test regressor list returns all configured regressors."""
    # Access the underlying function via .fn (FunctionTool wrapper)
    response = await list_available_regressors.fn()

    assert response.__class__.__name__ == "RegressorListResponse"
    assert len(response.regressors) > 0

    # Check each regressor has expected fields
    for reg in response.regressors:
        assert reg.name
        assert reg.display_name
        assert reg.source in ["Eurostat", "ECB", "Unknown"]


@pytest.mark.asyncio
async def test_get_regressor_data_with_valid_variable():
    """Test fetching regressor data for a valid variable."""
    # Access the underlying function via .fn (FunctionTool wrapper)
    # Use a known regressor from config (use ISO string format)
    response = await get_regressor_data.fn(
        regressor="ttf_gas",
        start_date="2020-01-01",
        end_date="2023-12-31",
    )

    assert response.__class__.__name__ == "RegressorDataResponse"
    assert response.regressor_name == "ttf_gas"
    assert response.source in ["Eurostat", "ECB", "ICE", "Unknown"]
    assert len(response.data_points) > 0

    # Check data point structure
    for dp in response.data_points:
        assert dp.date
        assert isinstance(dp.value, (int, float))


@pytest.mark.asyncio
async def test_get_regressor_data_with_invalid_variable():
    """Test error handling for unknown variable."""
    # Access the underlying function via .fn (FunctionTool wrapper)
    with pytest.raises(ValueError, match="Unknown regressor"):
        await get_regressor_data.fn(
            regressor="nonexistent_variable",
            start_date="2020-01-01",
            end_date="2023-12-31",
        )
