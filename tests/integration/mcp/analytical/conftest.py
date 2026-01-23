"""Shared fixtures for analytical query tool tests."""

import pytest

from raglite.main import analytical_query_financial_documents

# Access underlying function from FastMCP FunctionTool wrapper
# FunctionTool objects are NOT directly callable - must use .fn attribute
analytical_query_fn = analytical_query_financial_documents.fn


@pytest.fixture
def analytical_query_tool():
    """Return the analytical query function (extracted from FunctionTool wrapper)."""
    return analytical_query_fn
