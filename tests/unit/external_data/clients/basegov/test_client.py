"""Tests for basegov client module.

Story 8.2 Task 4: Test structure for refactored basegov client.
"""


class TestBaseGovClient:
    """Test BaseGovClient main functionality."""

    def test_client_exists(self):
        """Verify BaseGovClient can be imported."""
        from raglite.external_data.clients.basegov import BaseGovClient

        assert BaseGovClient is not None
