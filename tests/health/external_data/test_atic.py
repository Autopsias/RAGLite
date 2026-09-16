"""ATIC (cement industry) health checks - CSV-based, currently working."""

import pytest

# All health check tests are excluded from regular CI runs
# Run manually with: pytest tests/health/ -m "" -v
pytestmark = [
    pytest.mark.health_check,
]


class TestATICHealth:
    """ATIC (cement industry) health checks - CSV-based, currently working."""

    @pytest.mark.asyncio
    async def test_atic_client_importable(self):
        """Verify ATIC client can be imported (CSV-based, no API)."""
        try:
            from raglite.external_data.clients.atic import ATICClient

            client = ATICClient()
            assert client is not None
        except ImportError as e:
            pytest.fail(f"ATIC client import failed: {e}")

    @pytest.mark.asyncio
    async def test_atic_has_fetch_method(self):
        """Verify ATIC client has expected fetch and parse methods."""
        from raglite.external_data.clients.atic import ATICClient

        client = ATICClient()

        # Check for expected method names (ATIC is CSV-based, not API-based)
        has_fetch = hasattr(client, "fetch_historical_data")
        has_parse_file = hasattr(client, "parse_csv_file")
        has_parse_content = hasattr(client, "parse_csv_content")

        assert has_fetch, "ATIC client missing fetch_historical_data method"
        assert has_parse_file, "ATIC client missing parse_csv_file method"
        assert has_parse_content, "ATIC client missing parse_csv_content method"
