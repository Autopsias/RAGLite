"""Tests for basegov ted_api module.

Story 8.2 Task 4: Test structure for refactored basegov TED API client.
"""


class TestTedApi:
    """Test TED API functionality."""

    def test_module_exists(self):
        """Verify ted_api module can be imported."""
        from raglite.external_data.clients.basegov import ted_api

        assert ted_api is not None
