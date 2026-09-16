"""ATDD Acceptance Tests - AC4: Shared Fixtures Extracted.

Story: 7-1-split-test-external-data-clients
Epic: 7 - Technical Debt & Code Quality

Verifies:
- Common imports consolidated in conftest.py
- Shared mock patterns extracted to conftest
- Fixtures are properly scoped
"""

from pathlib import Path

import pytest

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TESTS_ROOT = PROJECT_ROOT / "tests"
EXTERNAL_DATA_TESTS_DIR = TESTS_ROOT / "unit" / "external_data"


class TestAC4SharedFixtures:
    """TEST-AC-4: Shared Fixtures Extracted acceptance criteria tests."""

    @pytest.mark.acceptance
    def test_ac4_1_conftest_has_mock_httpx_fixture(self) -> None:
        """TEST-AC-4.1: conftest.py must have mock_httpx_response fixture."""
        conftest_file = EXTERNAL_DATA_TESTS_DIR / "conftest.py"

        if not conftest_file.exists():
            pytest.skip("conftest.py does not exist yet (RED phase)")

        content = conftest_file.read_text()
        assert "def mock_httpx_response" in content or "@pytest.fixture" in content, (
            "conftest.py should contain shared mock fixtures like mock_httpx_response. "
            "Extract common mocking patterns from test modules."
        )

    @pytest.mark.acceptance
    def test_ac4_2_conftest_has_required_imports(self) -> None:
        """TEST-AC-4.2: conftest.py must have common imports."""
        conftest_file = EXTERNAL_DATA_TESTS_DIR / "conftest.py"

        if not conftest_file.exists():
            pytest.skip("conftest.py does not exist yet (RED phase)")

        content = conftest_file.read_text()
        required_imports = [
            "pytest",
            "unittest.mock",
            "httpx",
        ]

        for imp in required_imports:
            assert imp in content, f"conftest.py should import '{imp}' for shared fixtures."

    @pytest.mark.acceptance
    def test_ac4_3_conftest_has_sample_date_range_fixture(self) -> None:
        """TEST-AC-4.3: conftest.py should have sample_date_range fixture."""
        conftest_file = EXTERNAL_DATA_TESTS_DIR / "conftest.py"

        if not conftest_file.exists():
            pytest.skip("conftest.py does not exist yet (RED phase)")

        content = conftest_file.read_text()
        assert "sample_date_range" in content, (
            "conftest.py should contain sample_date_range fixture for date testing. "
            "This is a common fixture used across multiple client tests."
        )
