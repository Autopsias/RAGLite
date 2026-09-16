"""Response and utility test data factories.

Provides factory functions for generating MCP tool responses and test cleanup helpers.
"""

import os
from typing import Any

from faker import Faker

_FAKER_SEED = int(os.getenv("FAKER_SEED", "42"))
fake = Faker()
Faker.seed(_FAKER_SEED)


def create_mcp_tool_response(success: bool = True, **overrides: Any) -> dict[str, Any]:
    """Create MCP tool response structure for testing.

    Args:
        success: Whether response indicates success (default: True)
        **overrides: Override specific fields

    Returns:
        Dictionary representing MCP tool response

    Example:
        # Success response
        response = create_mcp_tool_response()

        # Error response
        response = create_mcp_tool_response(
            success=False,
            error="Query failed"
        )
    """
    if success:
        defaults = {
            "content": [
                {
                    "type": "text",
                    "text": f"Found {fake.random_int(1, 10)} results for your query.",
                }
            ],
            "isError": False,
        }
    else:
        defaults = {
            "content": [{"type": "text", "text": overrides.get("error", "An error occurred")}],
            "isError": True,
        }

    defaults.update(overrides)
    return defaults


# Cleanup helper for integration tests
def cleanup_test_data():
    """Clean up test data after integration tests.

    This is a placeholder for future cleanup logic if needed.
    Currently, tests use fixtures with auto-cleanup.
    """
    pass
