"""AC-8.5-2: Verify import paths work without deprecation warnings."""

import subprocess
import sys

import pytest

from .shared_helpers import get_project_root

# Mark all tests in this module
pytestmark = [
    pytest.mark.atdd,
    pytest.mark.story_8_5,
]


class TestAC852ImportPathDeprecation:
    """AC-8.5-2: Verify import paths work without deprecation warnings."""

    @pytest.mark.priority("P1")
    def test_ac_8_5_2_1_package_imports_no_warning(self):
        """TEST-AC-8.5.2.1: Importing from document_ingestion package should not warn.

        Given: The refactored document_ingestion package
        When: Core functions are imported from the package
        Then: No deprecation warning should be raised
        """
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # These imports should work without deprecation warnings
            from raglite.ingestion.document_ingestion import (  # noqa: F401
                extract_excel,
                ingest_document,
                ingest_pdf,
            )

            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]

            assert len(deprecation_warnings) == 0, (
                f"Found {len(deprecation_warnings)} deprecation warning(s) on import:\n"
                + "\n".join(str(x.message) for x in deprecation_warnings)
            )

    @pytest.mark.priority("P2")
    def test_ac_8_5_2_2_scripts_use_valid_imports(self):
        """TEST-AC-8.5.2.2: Scripts should use imports that don't emit warnings.

        Given: Scripts in the scripts/ directory
        When: Their import statements are analyzed
        Then: They should not use deprecated import patterns
        """
        project_root = get_project_root()
        scripts_dir = project_root / "scripts"

        problematic_scripts = []

        for script in scripts_dir.glob("*.py"):
            content = script.read_text()

            # Check for imports that might trigger deprecation
            # The shim file emits warning, direct submodule imports are preferred
            if "from raglite.ingestion.document_ingestion import" in content:
                # This is fine - package __init__.py re-exports properly
                pass

            # Check for problematic patterns (if any exist)
            # Pattern: importing from the shim file directly when package exists
            if "from raglite.ingestion import document_ingestion" in content:
                # Importing the module itself (not from it) may trigger shim
                problematic_scripts.append(script.name)

        # This should pass when imports are properly structured
        assert len(problematic_scripts) == 0, (
            f"Scripts with potentially problematic imports: {problematic_scripts}"
        )

    @pytest.mark.priority("P1")
    def test_ac_8_5_2_3_verify_import_command_succeeds(self):
        """TEST-AC-8.5.2.3: Python import with warning escalation should succeed.

        Given: Python with -W error::DeprecationWarning flag
        When: Importing from raglite.ingestion.document_ingestion
        Then: Command should exit with code 0 (no warnings escalated to errors)
        """
        project_root = get_project_root()

        result = subprocess.run(
            [
                sys.executable,
                "-W",
                "error::DeprecationWarning",
                "-c",
                "from raglite.ingestion.document_ingestion import ingest_document, ingest_pdf, extract_excel",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=30,
        )

        assert result.returncode == 0, (
            f"Import failed with deprecation warning escalated to error.\n"
            f"stderr: {result.stderr}\n"
            f"stdout: {result.stdout}"
        )
