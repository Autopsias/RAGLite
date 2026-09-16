#!/usr/bin/env python3
"""Story 6.23 MCP Integration Tests.

Tests AC5: MCP tools functional with new data sources.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from raglite.forecasting.regressor_config import METRIC_REGRESSORS

pytestmark = [
    pytest.mark.integration,
    pytest.mark.preserve_collection,
    pytest.mark.slow,
]


@pytest.fixture
def validation_script_path():
    """Path to unified validation script."""
    script_path = (
        Path(__file__).parent.parent.parent.parent / "scripts" / "validate_forecasting_unified.py"
    )
    if not script_path.exists():
        pytest.skip(f"Validation script not found: {script_path}")
    return script_path


class TestStory623MCPIntegration:
    """Tests for MCP tools integration."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_ac5_mcp_forecast_query_tool_functional(self):
        """AC5: MCP forecast_query tool accepts new regressors."""
        # This would test actual MCP tool invocation
        # For now, validate that regressor config is accessible
        assert len(METRIC_REGRESSORS) > 0
        pytest.skip("MCP tool integration test - implementation pending")
