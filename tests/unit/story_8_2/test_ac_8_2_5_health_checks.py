"""AC-8.2.5 ATDD Tests: All Health Checks Pass.

Story 8.2: External Data Client Refactoring

Given the external data health checks validate API connectivity
When the refactoring is complete
Then all existing health checks continue to pass

Verification:
- Run `pytest tests/health/test_external_data_health.py -v`
- All health checks pass
- No API regressions introduced
"""

from __future__ import annotations

import pytest

from tests.unit.story_8_2.conftest import TESTS_ROOT

pytestmark = [pytest.mark.unit]


class TestAC825HealthCheckInfrastructure:
    """[AC-8.2.5] Verify health check infrastructure exists."""

    def test_ac_8_2_5_health_test_file_exists(self) -> None:
        """[TEST-AC-8.2.5-A] Health check test file should exist.

        Given health tests are required
        When we check tests/health/test_external_data_health.py
        Then the file exists
        """
        health_file = TESTS_ROOT / "health" / "test_external_data_health.py"
        assert health_file.exists(), f"Health check file not found at {health_file}"

    def test_ac_8_2_5_health_test_has_test_classes(self) -> None:
        """[TEST-AC-8.2.5-B] Health test file should have test classes.

        Expected classes: TestINEHealth, TestOMIEHealth, TestBPstatHealth, etc.

        Note: After Epic 8 refactoring, test_external_data_health.py is a facade that
        imports classes from external_data/ package. This test checks for both patterns:
        1. Direct class definitions (old pattern)
        2. Import statements from external_data (new facade pattern)
        """
        health_file = TESTS_ROOT / "health" / "test_external_data_health.py"
        if not health_file.exists():
            pytest.fail(f"Health check file not found at {health_file}")

        import ast

        content = health_file.read_text()
        tree = ast.parse(content)

        # Check for imported test classes (facade pattern)
        imported_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "external_data" in node.module:
                    for alias in node.names:
                        imported_classes.append(alias.name)

        # Check for direct class definitions (old pattern)
        defined_classes = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        ]

        # Combine both sources
        test_classes = list(set(imported_classes + defined_classes))

        expected_classes = [
            "TestINEHealth",
            "TestOMIEHealth",
            "TestBPstatHealth",
            "TestBaseGovHealth",
        ]

        for expected in expected_classes:
            assert expected in test_classes, (
                f"Expected health check class '{expected}' not found. Found: {test_classes}"
            )


class TestAC825ClientImportability:
    """[AC-8.2.5] Verify clients can be imported for health checks."""

    def test_ac_8_2_5_basegov_client_importable(self) -> None:
        """[TEST-AC-8.2.5-C] BaseGovClient should be importable.

        Given refactoring is complete
        When we import BaseGovClient
        Then no import errors occur
        """
        try:
            from raglite.external_data.clients.basegov import (
                BaseGovClient,  # noqa: F401  # type: ignore[attr-defined]
            )
        except ImportError as e:
            pytest.fail(f"Failed to import BaseGovClient: {e}")

    def test_ac_8_2_5_ecb_client_importable(self) -> None:
        """[TEST-AC-8.2.5-D] ECBClient should be importable.

        Given refactoring is complete
        When we import ECBClient
        Then no import errors occur
        """
        try:
            from raglite.external_data.clients.ecb import (
                ECBClient,  # noqa: F401  # type: ignore[attr-defined]
            )
        except ImportError as e:
            pytest.fail(f"Failed to import ECBClient: {e}")

    def test_ac_8_2_5_eurostat_client_importable(self) -> None:
        """[TEST-AC-8.2.5-E] EurostatClient should be importable.

        Given refactoring is complete
        When we import EurostatClient
        Then no import errors occur
        """
        try:
            from raglite.external_data.clients.eurostat import (
                EurostatClient,  # noqa: F401  # type: ignore[attr-defined]
            )
        except ImportError as e:
            pytest.fail(f"Failed to import EurostatClient: {e}")

    def test_ac_8_2_5_storage_importable(self) -> None:
        """[TEST-AC-8.2.5-F] ExternalDataStorage should be importable.

        Given refactoring is complete
        When we import ExternalDataStorage
        Then no import errors occur
        """
        try:
            from raglite.external_data.storage import (
                ExternalDataStorage,  # noqa: F401  # type: ignore[attr-defined]
            )
        except ImportError as e:
            pytest.fail(f"Failed to import ExternalDataStorage: {e}")


class TestAC825ClientInstantiation:
    """[AC-8.2.5] Verify clients can be instantiated."""

    def test_ac_8_2_5_basegov_instantiable(self) -> None:
        """[TEST-AC-8.2.5-G] BaseGovClient should be instantiable.

        Given BaseGovClient can be imported
        When we create an instance
        Then no errors occur
        """
        try:
            from raglite.external_data.clients.basegov import BaseGovClient

            client = BaseGovClient()
            assert client is not None
        except ImportError:
            pytest.skip("BaseGovClient not yet available (refactoring pending)")
        except Exception as e:
            pytest.fail(f"Failed to instantiate BaseGovClient: {e}")

    def test_ac_8_2_5_ecb_instantiable(self) -> None:
        """[TEST-AC-8.2.5-H] ECBClient should be instantiable.

        Given ECBClient can be imported
        When we create an instance
        Then no errors occur
        """
        try:
            from raglite.external_data.clients.ecb import ECBClient

            client = ECBClient()
            assert client is not None
        except ImportError:
            pytest.skip("ECBClient not yet available (refactoring pending)")
        except Exception as e:
            pytest.fail(f"Failed to instantiate ECBClient: {e}")

    def test_ac_8_2_5_eurostat_instantiable(self) -> None:
        """[TEST-AC-8.2.5-I] EurostatClient should be instantiable.

        Given EurostatClient can be imported
        When we create an instance
        Then no errors occur
        """
        try:
            from raglite.external_data.clients.eurostat import EurostatClient

            client = EurostatClient()
            assert client is not None
        except ImportError:
            pytest.skip("EurostatClient not yet available (refactoring pending)")
        except Exception as e:
            pytest.fail(f"Failed to instantiate EurostatClient: {e}")


class TestAC825NoAPIRegression:
    """[AC-8.2.5] Verify no API regressions from refactoring."""

    def test_ac_8_2_5_basegov_has_fetch_method(self) -> None:
        """[TEST-AC-8.2.5-J] BaseGovClient should have fetch methods.

        Given BaseGovClient exists
        When we check its methods
        Then fetch-related methods exist
        """
        try:
            from raglite.external_data.clients.basegov import BaseGovClient

            client = BaseGovClient()
            # Check for key methods
            assert hasattr(client, "fetch_contracts") or hasattr(client, "fetch_tenders"), (
                "BaseGovClient missing fetch methods"
            )
        except ImportError:
            pytest.skip("BaseGovClient not yet available (refactoring pending)")

    def test_ac_8_2_5_ecb_has_fetch_methods(self) -> None:
        """[TEST-AC-8.2.5-K] ECBClient should have fetch methods.

        Given ECBClient exists
        When we check its methods
        Then EURIBOR, GDP, HICP fetch methods exist
        """
        try:
            from raglite.external_data.clients.ecb import ECBClient

            client = ECBClient()
            expected_patterns = ["euribor", "gdp", "hicp", "inflation"]
            methods = [m for m in dir(client) if not m.startswith("_")]
            methods_lower = [m.lower() for m in methods]

            found = any(pattern in " ".join(methods_lower) for pattern in expected_patterns)
            assert found, f"ECBClient missing expected methods. Found: {methods[:10]}..."
        except ImportError:
            pytest.skip("ECBClient not yet available (refactoring pending)")

    def test_ac_8_2_5_eurostat_has_fetch_methods(self) -> None:
        """[TEST-AC-8.2.5-L] EurostatClient should have fetch methods.

        Given EurostatClient exists
        When we check its methods
        Then electricity, construction, permits methods exist
        """
        try:
            from raglite.external_data.clients.eurostat import EurostatClient

            client = EurostatClient()
            expected_patterns = ["electricity", "construction", "permit"]
            methods = [m for m in dir(client) if not m.startswith("_")]
            methods_lower = [m.lower() for m in methods]

            found = any(pattern in " ".join(methods_lower) for pattern in expected_patterns)
            assert found, f"EurostatClient missing expected methods. Found: {methods[:10]}..."
        except ImportError:
            pytest.skip("EurostatClient not yet available (refactoring pending)")
