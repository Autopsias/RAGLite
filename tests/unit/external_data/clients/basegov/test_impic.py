"""Tests for basegov impic module.

Story 8.2 Task 4: Test structure for refactored basegov IMPIC client.
"""


class TestImpic:
    """Test IMPIC XLSX functionality."""

    def test_module_exists(self):
        """Verify impic module can be imported."""
        from raglite.external_data.clients.basegov import impic

        assert impic is not None
