"""Tests for basegov parsers module.

Story 8.2 Task 4: Test structure for refactored basegov parsers.
"""


class TestParsers:
    """Test parser functionality."""

    def test_module_exists(self):
        """Verify parsers module can be imported."""
        from raglite.external_data.clients.basegov import parsers

        assert parsers is not None
