"""AC-8.2.3 ATDD Tests: Shared Base Class for Common Client Patterns.

Story 8.2: External Data Client Refactoring

Given the three API clients (BaseGov, ECB, Eurostat) share common patterns
When the refactoring is complete
Then a shared base class exists with:
  - Retry logic with exponential backoff
  - Caching infrastructure
  - Common HTTP error handling
  - Logging patterns

Verification:
- Base class exists at `raglite/external_data/clients/base.py`
- All three clients inherit from the base class
- Retry logic is DRY (single implementation)
- Unit tests validate base class functionality
"""

from __future__ import annotations

import ast

import pytest

from tests.unit.story_8_2.conftest import (
    BASE_CLIENT_FILE,
    BASEGOV_PACKAGE,
    ECB_PACKAGE,
    EUROSTAT_PACKAGE,
    HARD_LOC_LIMIT,
    count_lines_simple,
)

pytestmark = [pytest.mark.unit]


class TestAC823BaseClassExists:
    """[AC-8.2.3] Verify shared base class exists."""

    def test_ac_8_2_3_base_client_file_exists(self) -> None:
        """[TEST-AC-8.2.3-A] base.py should exist in clients/.

        Given refactoring is complete
        When we check raglite/external_data/clients/base.py
        Then the file exists
        """
        assert BASE_CLIENT_FILE.exists(), f"Base client file not found at {BASE_CLIENT_FILE}"

    def test_ac_8_2_3_base_client_under_limit(self) -> None:
        """[TEST-AC-8.2.3-B] base.py should be < 500 LOC.

        Target is ~200 LOC per story spec.
        """
        if not BASE_CLIENT_FILE.exists():
            pytest.fail(f"base.py not found at {BASE_CLIENT_FILE}")

        loc = count_lines_simple(BASE_CLIENT_FILE)
        assert loc < HARD_LOC_LIMIT, f"base.py has {loc} LOC, expected < {HARD_LOC_LIMIT}"

    def test_ac_8_2_3_base_client_has_class(self) -> None:
        """[TEST-AC-8.2.3-C] base.py should define BaseExternalClient class.

        Given base.py exists
        When we parse the file
        Then it defines a class named BaseExternalClient
        """
        if not BASE_CLIENT_FILE.exists():
            pytest.fail(f"base.py not found at {BASE_CLIENT_FILE}")

        content = BASE_CLIENT_FILE.read_text()
        tree = ast.parse(content)

        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        assert "BaseExternalClient" in class_names, (
            f"BaseExternalClient class not found in base.py. Found classes: {class_names}"
        )


class TestAC823BaseClassFeatures:
    """[AC-8.2.3] Verify base class has required features."""

    def test_ac_8_2_3_base_has_retry_method(self) -> None:
        """[TEST-AC-8.2.3-D] Base class should have retry logic method.

        Expected method: _fetch_with_retry or similar
        """
        if not BASE_CLIENT_FILE.exists():
            pytest.fail(f"base.py not found at {BASE_CLIENT_FILE}")

        content = BASE_CLIENT_FILE.read_text()
        tree = ast.parse(content)

        method_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "BaseExternalClient":
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_names.append(item.name)

        retry_methods = [m for m in method_names if "retry" in m.lower()]
        assert len(retry_methods) > 0, (
            f"No retry method found in BaseExternalClient. Methods found: {method_names}"
        )

    def test_ac_8_2_3_base_has_cache_init(self) -> None:
        """[TEST-AC-8.2.3-E] Base class should have caching infrastructure.

        Expected: _init_cache method or cache attribute
        """
        if not BASE_CLIENT_FILE.exists():
            pytest.fail(f"base.py not found at {BASE_CLIENT_FILE}")

        content = BASE_CLIENT_FILE.read_text()

        # Check for cache-related code
        cache_indicators = ["_cache", "_init_cache", "cache", "ExternalDataCache"]
        has_cache = any(indicator in content for indicator in cache_indicators)

        assert has_cache, (
            "No caching infrastructure found in base.py. "
            "Expected _init_cache method or cache attribute."
        )

    def test_ac_8_2_3_base_has_error_handling(self) -> None:
        """[TEST-AC-8.2.3-F] Base class should handle HTTP errors.

        Expected: ExternalDataFetchError import or raise statement
        """
        if not BASE_CLIENT_FILE.exists():
            pytest.fail(f"base.py not found at {BASE_CLIENT_FILE}")

        content = BASE_CLIENT_FILE.read_text()

        error_indicators = [
            "ExternalDataFetchError",
            "HTTPStatusError",
            "TimeoutException",
        ]
        has_error_handling = any(indicator in content for indicator in error_indicators)

        assert has_error_handling, (
            "No HTTP error handling found in base.py. "
            "Expected ExternalDataFetchError or httpx exception handling."
        )

    def test_ac_8_2_3_base_has_logging(self) -> None:
        """[TEST-AC-8.2.3-G] Base class should have logging patterns.

        Expected: logger attribute or get_logger import
        """
        if not BASE_CLIENT_FILE.exists():
            pytest.fail(f"base.py not found at {BASE_CLIENT_FILE}")

        content = BASE_CLIENT_FILE.read_text()

        logging_indicators = ["self.logger", "get_logger", "logging.getLogger"]
        has_logging = any(indicator in content for indicator in logging_indicators)

        assert has_logging, (
            "No logging infrastructure found in base.py. "
            "Expected logger attribute or get_logger import."
        )


class TestAC823ClientsInheritFromBase:
    """[AC-8.2.3] Verify all clients inherit from base class."""

    def test_ac_8_2_3_basegov_inherits_base(self) -> None:
        """[TEST-AC-8.2.3-H] BaseGovClient should inherit from BaseExternalClient.

        Given basegov/client.py exists
        When we parse the class definition
        Then BaseGovClient inherits from BaseExternalClient
        """
        client_file = BASEGOV_PACKAGE / "client.py"
        if not client_file.exists():
            pytest.fail(f"basegov/client.py not found at {client_file}")

        content = client_file.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and "BaseGov" in node.name:
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_names.append(base.attr)

                assert "BaseExternalClient" in base_names, (
                    f"BaseGovClient does not inherit from BaseExternalClient. Bases: {base_names}"
                )
                return

        pytest.fail("No BaseGov-related class found in basegov/client.py")

    def test_ac_8_2_3_ecb_inherits_base(self) -> None:
        """[TEST-AC-8.2.3-I] ECBClient should inherit from BaseExternalClient.

        Given ecb/client.py exists
        When we parse the class definition
        Then ECBClient inherits from BaseExternalClient
        """
        client_file = ECB_PACKAGE / "client.py"
        if not client_file.exists():
            pytest.fail(f"ecb/client.py not found at {client_file}")

        content = client_file.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and "ECB" in node.name:
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_names.append(base.attr)

                assert "BaseExternalClient" in base_names, (
                    f"ECBClient does not inherit from BaseExternalClient. Bases: {base_names}"
                )
                return

        pytest.fail("No ECB-related class found in ecb/client.py")

    def test_ac_8_2_3_eurostat_inherits_base(self) -> None:
        """[TEST-AC-8.2.3-J] EurostatClient should inherit from BaseExternalClient.

        Given eurostat/client.py exists
        When we parse the class definition
        Then EurostatClient inherits from BaseExternalClient
        """
        client_file = EUROSTAT_PACKAGE / "client.py"
        if not client_file.exists():
            pytest.fail(f"eurostat/client.py not found at {client_file}")

        content = client_file.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and "Eurostat" in node.name:
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_names.append(base.attr)

                assert "BaseExternalClient" in base_names, (
                    f"EurostatClient does not inherit from BaseExternalClient. Bases: {base_names}"
                )
                return

        pytest.fail("No Eurostat-related class found in eurostat/client.py")


class TestAC823RetryLogicDRY:
    """[AC-8.2.3] Verify retry logic is DRY (single implementation)."""

    def test_ac_8_2_3_no_duplicate_retry_in_clients(self) -> None:
        """[TEST-AC-8.2.3-K] Client files should not duplicate retry logic.

        Given clients inherit from BaseExternalClient
        When we check client files for retry implementation
        Then retry logic is only in base.py (not duplicated)
        """
        client_files = [
            BASEGOV_PACKAGE / "client.py",
            ECB_PACKAGE / "client.py",
            EUROSTAT_PACKAGE / "client.py",
        ]

        violations = []
        for client_file in client_files:
            if not client_file.exists():
                continue

            content = client_file.read_text()

            # Check for retry patterns that should be in base class
            retry_patterns = [
                "retry_delays",
                "exponential backoff",
                "max_retries",
                "for attempt in range",
            ]

            for pattern in retry_patterns:
                if pattern.lower() in content.lower():
                    violations.append(f"{client_file.name} contains '{pattern}'")

        assert not violations, (
            f"Retry logic duplicated in client files (should be in base.py): {violations}"
        )
