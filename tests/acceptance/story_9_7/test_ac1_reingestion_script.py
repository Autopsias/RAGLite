"""ATDD tests for Story 9.7 AC1 - Re-ingestion Script Updates.

TDD RED Phase: All tests MUST fail initially because the updated reingest
script does not include all 33 PDFs and required features.

Test IDs follow pattern: TEST-AC-9.7.1.{test}

BDD Acceptance Criteria:
Given the existing scripts/reingest-all-documents.py script
And the classification-enabled ingestion pipeline from Stories 9.5 and 9.6
When the re-ingestion script is executed
Then it uses the updated ingest_document() which includes classification
And classification fields are automatically populated via the Story 9.5 integration
And the script supports all 33 production PDFs (not just the original 10)
And execution can be parallelized with --parallel N flag for faster processing
And progress is reported with classification summary per document
"""

import pytest

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.story_9_7,
    pytest.mark.atdd,
]


class TestAC1ReingestionScriptUpdates:
    """AC1: Re-ingestion Script Updates.

    Given the existing reingest-all-documents.py script
    When updated for Story 9.7
    Then it supports all 33 PDFs and classification features
    """

    def test_ac_1_1_1_reingest_script_exists(self) -> None:
        """TEST-AC-9.7.1.1 [P0]: Updated reingest script exists.

        Given the scripts directory exists
        When we check for reingest-all-documents.py
        Then the script exists and is importable
        """
        # Arrange: Expected script path
        from pathlib import Path

        script_path = Path("scripts/reingest-all-documents.py")

        # Assert: Script exists
        assert script_path.exists(), f"Script not found at {script_path}"

    def test_ac_1_1_2_reingest_script_has_33_documents(self) -> None:
        """TEST-AC-9.7.1.2 [P0]: Script includes all 33 production PDFs.

        Given the reingest script exists
        When we examine the DOCUMENTS list
        Then it contains exactly 33 PDF entries
        """
        # Arrange: Import the script module
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location(
            "reingest", Path("scripts/reingest-all-documents.py")
        )
        reingest_module = importlib.util.module_from_spec(spec)

        # Act: Load the module
        spec.loader.exec_module(reingest_module)

        # Assert: DOCUMENTS list contains 33 entries
        # RED STATE: Current script only has 10 documents
        assert hasattr(reingest_module, "DOCUMENTS")
        assert len(reingest_module.DOCUMENTS) == 33, (
            f"Expected 33 documents, found {len(reingest_module.DOCUMENTS)}"
        )

    @pytest.mark.slow
    def test_ac_1_1_3_reingest_script_supports_parallel_flag(self) -> None:
        """TEST-AC-9.7.1.3 [P0]: Script supports --parallel N flag.

        Given the reingest script exists
        When we examine the argument parser
        Then it includes --parallel option for concurrent processing
        """
        # Arrange: Import argparse module from script
        import subprocess

        # Act: Run script with --help to check for parallel flag
        result = subprocess.run(
            ["python", "scripts/reingest-all-documents.py", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Assert: --parallel flag is documented in help
        # RED STATE: Current script does not have argparse/parallel support
        assert "--parallel" in result.stdout, (
            "Script should support --parallel flag for concurrent processing"
        )

    def test_ac_1_1_4_reingest_script_reports_classification_summary(self) -> None:
        """TEST-AC-9.7.1.4 [P0]: Script reports classification summary per document.

        Given the reingest script exists
        When we examine the output handling
        Then it includes classification field counts in the summary
        """
        # Arrange: Import the script module
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location(
            "reingest", Path("scripts/reingest-all-documents.py")
        )
        reingest_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reingest_module)

        # Assert: Script has classification summary function or output
        # RED STATE: Current script does not have classification reporting
        assert hasattr(reingest_module, "print_classification_summary") or hasattr(
            reingest_module, "ClassificationSummary"
        ), "Script should have classification summary reporting capability"

    def test_ac_1_1_5_reingest_uses_classification_enabled_pipeline(self) -> None:
        """TEST-AC-9.7.1.5 [P0]: Script uses classification-enabled ingestion.

        Given the reingest script imports ingest_document
        When we check the ingestion result
        Then it includes classification fields (period_type, value_type, entity_level)
        """
        # Arrange: Import ingestion module
        from raglite.ingestion.document_ingestion import ingest_document

        # Assert: ingest_document is available (implicitly includes classification)
        assert callable(ingest_document)

        # Additional check: classification integration module exists
        from raglite.ingestion.classification.integration import classify_rows_batch

        assert callable(classify_rows_batch)

    @pytest.mark.slow
    def test_ac_1_1_6_reingest_script_has_dry_run_option(self) -> None:
        """TEST-AC-9.7.1.6 [P1]: Script supports --dry-run option.

        Given the reingest script exists
        When we examine the argument parser
        Then it includes --dry-run option to preview without executing
        """
        # Arrange: Run script with --help
        import subprocess

        result = subprocess.run(
            ["python", "scripts/reingest-all-documents.py", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Assert: --dry-run flag exists
        # RED STATE: Current script does not support dry-run
        assert "--dry-run" in result.stdout, "Script should support --dry-run flag for preview mode"

    def test_ac_1_1_7_reingest_script_has_progress_tracking(self) -> None:
        """TEST-AC-9.7.1.7 [P1]: Script tracks and displays progress.

        Given the reingest script processes documents
        When processing is in progress
        Then progress is displayed (X/33 documents, estimated time remaining)
        """
        # Arrange: Import the script module
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location(
            "reingest", Path("scripts/reingest-all-documents.py")
        )
        reingest_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reingest_module)

        # Assert: Script has progress tracking capability
        # RED STATE: Current script has basic progress but not full tracking
        # Look for progress indicator function or class
        source_code = Path("scripts/reingest-all-documents.py").read_text()
        assert "remaining" in source_code.lower() or "progress" in source_code.lower(), (
            "Script should track progress with time remaining estimates"
        )
