"""Summary Test: AC-8.5 Overall Verification.

This test verifies that all deprecation cleanup is complete.

Story: docs/stories/8-5-deprecation-cleanup.md
Epic: 8 - Technical Debt Reduction
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest


class TestAC85DeprecationCleanupSummary:
    """Summary test to verify all deprecation cleanup is complete."""

    @pytest.mark.priority("P0")
    def test_ac_8_5_summary_all_deprecations_resolved(self):
        """TEST-AC-8.5.SUMMARY: All deprecation issues should be resolved.

        Given: Story 8.5 deprecation cleanup requirements
        When: All targeted deprecation sources are checked
        Then: Zero deprecation warnings from raglite code
        """
        project_root = Path(__file__).parent.parent.parent.parent

        issues = []

        # Check 1: historical_data usage in test files
        for test_file in [
            "tests/unit/test_mcp_edge_cases.py",
            "tests/unit/test_hybrid_forecasting.py",
        ]:
            file_path = project_root / test_file
            if file_path.exists():
                content = file_path.read_text()
                if re.search(r"generate_forecast\s*\([^)]*historical_data\s*=", content):
                    issues.append(f"deprecated historical_data in {test_file}")

        # Check 2: Fixture markers on fixtures
        for test_file in [
            "tests/integration/test_chunking_core.py",
            "tests/integration/test_chunking_slow.py",
            "tests/integration/test_chunking_extended.py",
        ]:
            file_path = project_root / test_file
            if file_path.exists():
                content = file_path.read_text()
                # Simple heuristic: @pytest.mark.* followed by @pytest.fixture
                if re.search(r"@pytest\.mark\.\w+.*\n.*@pytest\.fixture", content, re.MULTILINE):
                    issues.append(f"marker on fixture in {test_file}")

        # Check 3: Import deprecation warnings
        result = subprocess.run(
            [
                sys.executable,
                "-W",
                "error::DeprecationWarning",
                "-c",
                "from raglite.ingestion.document_ingestion import ingest_document",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30,
        )

        if result.returncode != 0:
            issues.append(f"import deprecation: {result.stderr[:200]}")

        assert len(issues) == 0, (
            f"Found {len(issues)} deprecation issue(s) to resolve:\n"
            + "\n".join(f"  - {issue}" for issue in issues)
        )
