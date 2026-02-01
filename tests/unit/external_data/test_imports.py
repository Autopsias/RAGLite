"""Import and circular dependency validation tests.

Story 8.2: External Data Client Refactoring
Validates no circular dependencies in refactored modules.
"""

import importlib
import sys


class TestImportValidation:
    """Tests for import validation and circular dependency detection."""

    def test_no_circular_dependencies_storage(self) -> None:
        """Storage package modules should not have circular dependencies."""
        # Clear any cached imports
        modules_to_clear = [
            k for k in sys.modules.keys() if k.startswith("raglite.external_data.storage")
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

        # Import each module individually to catch circular imports
        storage_modules = [
            "raglite.external_data.storage.constants",
            "raglite.external_data.storage.core",
            "raglite.external_data.storage.freshness",
            "raglite.external_data.storage.tier2",
            "raglite.external_data.storage.model_weights",
            "raglite.external_data.storage.model_selection",
            "raglite.external_data.storage.wrapper",
            "raglite.external_data.storage",
        ]

        for module_name in storage_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                if "circular" in str(e).lower() or "cannot import" in str(e).lower():
                    raise AssertionError(
                        f"Circular dependency detected in {module_name}: {e}"
                    ) from e
                raise

    def test_no_circular_dependencies_clients(self) -> None:
        """Client package modules should not have circular dependencies."""
        # Clear any cached imports
        modules_to_clear = [
            k for k in sys.modules.keys() if k.startswith("raglite.external_data.clients")
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

        # Import each module individually
        client_modules = [
            "raglite.external_data.clients.base",
            "raglite.external_data.clients.basegov.config",
            "raglite.external_data.clients.basegov.impic",
            "raglite.external_data.clients.basegov.ted_api",
            "raglite.external_data.clients.basegov.ocds",
            "raglite.external_data.clients.basegov.parsers",
            "raglite.external_data.clients.basegov.client",
            "raglite.external_data.clients.basegov",
            "raglite.external_data.clients.ecb.models",
            "raglite.external_data.clients.ecb.config",
            "raglite.external_data.clients.ecb.utils",
            "raglite.external_data.clients.ecb.fetchers",
            "raglite.external_data.clients.ecb.parsers",
            "raglite.external_data.clients.ecb.client",
            "raglite.external_data.clients.ecb",
            "raglite.external_data.clients.eurostat.config",
            "raglite.external_data.clients.eurostat.utils",
            "raglite.external_data.clients.eurostat.fetchers",
            "raglite.external_data.clients.eurostat.parsers",
            "raglite.external_data.clients.eurostat.client",
            "raglite.external_data.clients.eurostat",
        ]

        for module_name in client_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                if "circular" in str(e).lower() or "cannot import" in str(e).lower():
                    raise AssertionError(
                        f"Circular dependency detected in {module_name}: {e}"
                    ) from e
                raise

    def test_backward_compatibility_shims_work(self) -> None:
        """Backward compatibility shim files should re-export correctly."""
        # Test basegov shim
        from raglite.external_data.clients.basegov import BaseGovClient as ShimBaseGovClient
        from raglite.external_data.clients.basegov.client import BaseGovClient

        assert ShimBaseGovClient is BaseGovClient, "basegov shim should re-export BaseGovClient"

        # Test ecb shim
        from raglite.external_data.clients.ecb import ECBClient as ShimECBClient
        from raglite.external_data.clients.ecb.client import ECBClient

        assert ShimECBClient is ECBClient, "ecb shim should re-export ECBClient"

        # Test eurostat shim
        from raglite.external_data.clients.eurostat import EurostatClient as ShimEurostatClient
        from raglite.external_data.clients.eurostat.client import EurostatClient

        assert ShimEurostatClient is EurostatClient, "eurostat shim should re-export EurostatClient"
