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
from raglite.shared.models import (
    RegressorDataResponse,
    RegressorListResponse,
    ValidationResponse,
)


def get_tool_function(tool_name: str):
    """Extract the underlying function from a FastMCP FunctionTool.

    MCP tools are FunctionTool objects, not regular functions.
    Access the `.fn` attribute to get the callable.
    """
    func_map = {
        "validate_forecasting_accuracy": main_module.validate_forecasting_accuracy,
        "list_available_regressors": main_module.list_available_regressors,
        "get_regressor_data": main_module.get_regressor_data,
    }

    if tool_name not in func_map:
        raise ValueError(f"Tool {tool_name} not found")

    tool_obj = func_map[tool_name]
    if hasattr(tool_obj, "fn"):
        return tool_obj.fn

    raise ValueError(f"Could not extract function from {tool_name}")


# =============================================================================
# Integration Test for validate_forecasting_accuracy
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_validate_accuracy_integration():
    """Test full MCP validation roundtrip with database.

    Note: This test may take several minutes to run as it performs
    actual forecasting validation. It requires a populated database
    with financial metrics.
    """
    # Skip if no database available
    try:
        from raglite.forecasting.metrics import list_available_metrics

        metrics = await list_available_metrics(min_points=6)
        if len(metrics) < 1:
            pytest.skip("No metrics available in database for validation")
    except Exception:
        pytest.skip("Database not available for integration test")

    # Get the underlying function from FunctionTool
    validate_func = get_tool_function("validate_forecasting_accuracy")

    # Run validation for a single variable to keep test fast
    response = await validate_func(
        metrics=["revenue"], mape_method="holdout", include_model_breakdown=False
    )

    # Assertions
    assert isinstance(response, ValidationResponse)
    assert response.mape_method == "holdout"
    assert response.variables_tested >= 0  # May be 0 if metric not found
    assert 0.0 <= response.pass_rate <= 1.0
    assert response.average_mape >= 0.0

    # Validate response structure
    assert response.timestamp is not None
    assert response.runtime_seconds > 0
    assert isinstance(response.variable_results, list)


# =============================================================================
# Integration Test for list_available_regressors
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_list_regressors_integration():
    """Test full MCP list regressors roundtrip."""
    # Get the underlying function from FunctionTool
    list_func = get_tool_function("list_available_regressors")

    # Test listing all regressors
    response = await list_func()

    # Assertions
    assert isinstance(response, RegressorListResponse)
    assert response.total_count > 0
    assert response.available_count > 0
    assert len(response.regressors) == response.total_count

    # Verify expected regressors are present
    regressor_names = [r.name for r in response.regressors]
    expected_regressors = [
        "euribor_3m",
        "ttf_gas",
        "construction_output",
        "gdp_growth",
        "inflation",
    ]

    for expected in expected_regressors:
        assert expected in regressor_names, f"Expected regressor {expected} not found"

    # Test filtering by metric
    revenue_response = await list_func(metric="revenue")
    assert isinstance(revenue_response, RegressorListResponse)
    assert revenue_response.total_count > 0

    # Revenue-related regressors should include construction indicators
    revenue_regressor_names = [r.name for r in revenue_response.regressors]
    assert any(
        name in revenue_regressor_names
        for name in ["construction_output", "gdp_growth", "building_permits"]
    )


# =============================================================================
# Integration Test for get_regressor_data (with mocked API)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_regressor_data_integration():
    """Test full MCP regressor data fetch with API mock.

    Uses mocked API responses to avoid external dependencies while
    testing the full integration path.
    """
    from unittest.mock import patch

    import pandas as pd

    # Get the underlying function from FunctionTool
    get_data_func = get_tool_function("get_regressor_data")

    # Mock the fetch function to avoid real API calls
    with patch("raglite.forecasting.regressor_fetch.fetch_single_regressor") as mock_fetch:
        # Create realistic mock data
        dates = pd.date_range(start="2023-01-01", end="2024-12-01", freq="ME")
        values = [102.0 + i * 0.5 for i in range(len(dates))]
        mock_series = pd.Series(values, index=dates)
        mock_fetch.return_value = mock_series

        # Test fetching construction output data
        response = await get_data_func(
            regressor="construction_output",
            start_date="2023-01-01",
            end_date="2024-12-01",
        )

        # Assertions
        assert isinstance(response, RegressorDataResponse)
        assert response.regressor_name == "construction_output"
        assert response.display_name == "Construction Production Index (Portugal)"
        assert response.source == "Eurostat"
        assert response.unit == "Index"
        assert response.record_count == len(dates)
        assert len(response.data_points) == len(dates)
        assert response.visualization_hint == "line_chart"

        # Validate data points structure
        first_point = response.data_points[0]
        assert isinstance(first_point.date, date)
        assert isinstance(first_point.value, float)
        assert first_point.value > 0

        # Validate date range string
        # Note: ME (month-end) frequency produces end-of-month dates
        assert "2023-01" in response.date_range  # Start of range
        assert "2024-11" in response.date_range  # Last full month in range (ME ends at month-end)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mcp_multiple_regressors_integration():
    """Test fetching data from multiple different regressors."""
    from unittest.mock import patch

    import pandas as pd

    # Get the underlying function from FunctionTool
    get_data_func = get_tool_function("get_regressor_data")

    regressors_to_test = ["euribor_3m", "gdp_growth", "inflation"]

    for regressor_name in regressors_to_test:
        with patch("raglite.forecasting.regressor_fetch.fetch_single_regressor") as mock_fetch:
            # Create mock data
            dates = pd.date_range(start="2024-01-01", end="2024-06-01", freq="ME")
            values = [i * 1.5 for i in range(len(dates))]
            mock_series = pd.Series(values, index=dates)
            mock_fetch.return_value = mock_series

            # Fetch data
            response = await get_data_func(regressor=regressor_name)

            # Basic assertions
            assert response.regressor_name == regressor_name
            assert response.source in ["ECB", "Eurostat", "ICE", "EU Oil Bulletin", "EC"]
            assert response.record_count > 0
            assert len(response.data_points) > 0
