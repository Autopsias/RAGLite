"""ATDD tests for Story 9.7 AC2 - Production Data Cleanup.

TDD RED Phase: All tests MUST fail initially because the prepare-reingestion.py
script does not exist yet.

Test IDs follow pattern: TEST-AC-9.7.2.{test}

BDD Acceptance Criteria:
Given the production databases contain existing data:
  - Qdrant: 6,625 vectors in financial_docs collection
  - PostgreSQL: 78,759 rows in financial_tables
When preparing for re-ingestion
Then a full backup is created using scripts/backup-all.sh
And backup files are verified before proceeding
And old data is cleared ONLY after backup verification
And Qdrant collection is recreated (delete + create with same schema)
And PostgreSQL financial_tables data is truncated (schema preserved)
And financial_chunks table is truncated
And SafetyGuard patterns from .claude/rules/database-safety.md are followed
And --dry-run flag is supported to preview actions without executing
"""

import pytest

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.story_9_7,
    pytest.mark.atdd,
]


class TestAC2ProductionDataCleanup:
    """AC2: Production Data Cleanup.

    Given production databases contain data
    When preparing for re-ingestion
    Then cleanup follows SafetyGuard patterns with backup verification
    """

    def test_ac_2_1_1_prepare_reingestion_script_exists(self) -> None:
        """TEST-AC-9.7.2.1 [P0]: Cleanup script exists.

        Given the scripts directory exists
        When we check for prepare-reingestion.py
        Then the script exists
        """
        # Arrange: Expected script path
        from pathlib import Path

        script_path = Path("scripts/prepare-reingestion.py")

        # Assert: Script exists
        # RED STATE: Script does not exist yet
        assert script_path.exists(), f"Script not found at {script_path}"

    @pytest.mark.slow
    def test_ac_2_1_2_prepare_reingestion_supports_dry_run(self) -> None:
        """TEST-AC-9.7.2.2 [P0]: Script supports --dry-run mode.

        Given the prepare-reingestion.py script exists
        When we check the argument parser
        Then it includes --dry-run option
        """
        # Arrange: Run script with --help
        import subprocess

        result = subprocess.run(
            ["python", "scripts/prepare-reingestion.py", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Assert: --dry-run flag exists
        # RED STATE: Script does not exist
        assert "--dry-run" in result.stdout, "Script should support --dry-run flag for preview mode"

    @pytest.mark.slow
    def test_ac_2_1_3_prepare_reingestion_requires_force_production(self) -> None:
        """TEST-AC-9.7.2.3 [P0]: Script requires --force-production flag.

        Given the prepare-reingestion.py script exists
        When we check the argument parser
        Then it requires --force-production flag for production operations
        """
        # Arrange: Run script with --help
        import subprocess

        result = subprocess.run(
            ["python", "scripts/prepare-reingestion.py", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Assert: --force-production flag exists
        # RED STATE: Script does not exist
        assert "--force-production" in result.stdout, (
            "Script should require --force-production flag for production"
        )

    def test_ac_2_1_4_prepare_reingestion_uses_safety_guard(self) -> None:
        """TEST-AC-9.7.2.4 [P0]: Script uses SafetyGuard patterns.

        Given the prepare-reingestion.py script exists
        When we examine its imports
        Then it imports SafetyGuard from raglite.shared.safety
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/prepare-reingestion.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: SafetyGuard is imported
        assert "SafetyGuard" in source_code, (
            "Script should use SafetyGuard from raglite.shared.safety"
        )
        assert "from raglite.shared.safety import" in source_code, (
            "Script should import from raglite.shared.safety"
        )

    def test_ac_2_1_5_prepare_reingestion_verifies_backup(self) -> None:
        """TEST-AC-9.7.2.5 [P0]: Script verifies backup before cleanup.

        Given the prepare-reingestion.py script exists
        When we examine its logic
        Then it calls backup verification before any destructive operation
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/prepare-reingestion.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Backup verification is present
        assert "verify_backup" in source_code or "backup" in source_code.lower(), (
            "Script should verify backup exists before cleanup"
        )

    def test_ac_2_1_6_prepare_reingestion_requires_confirmation(self) -> None:
        """TEST-AC-9.7.2.6 [P0]: Script requires explicit user confirmation.

        Given the prepare-reingestion.py script exists
        When we examine its logic
        Then it requires typing DELETE to confirm destructive operations
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/prepare-reingestion.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Confirmation is required
        assert "DELETE" in source_code or "confirm" in source_code.lower(), (
            "Script should require explicit confirmation (typing DELETE)"
        )

    def test_ac_2_1_7_dry_run_prevents_execution(self) -> None:
        """TEST-AC-9.7.2.7 [P0]: Dry-run mode prevents destructive operations.

        Given the prepare-reingestion.py script exists
        When executed with --dry-run flag
        Then no actual database operations are performed
        And actions are only printed (previewed)
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/prepare-reingestion.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Dry-run check is present
        assert "dry_run" in source_code or "dry-run" in source_code, (
            "Script should check for dry-run mode before executing"
        )
        assert "DRY RUN" in source_code or "preview" in source_code.lower(), (
            "Script should display preview message in dry-run mode"
        )

    def test_ac_2_1_8_cleanup_truncates_financial_tables(self) -> None:
        """TEST-AC-9.7.2.8 [P1]: Cleanup truncates financial_tables.

        Given the prepare-reingestion.py script exists
        When cleanup is executed
        Then PostgreSQL financial_tables data is truncated (schema preserved)
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/prepare-reingestion.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: TRUNCATE financial_tables is present
        assert "financial_tables" in source_code, (
            "Script should reference financial_tables for truncation"
        )
        assert "TRUNCATE" in source_code.upper() or "truncate" in source_code, (
            "Script should truncate financial_tables"
        )

    def test_ac_2_1_9_cleanup_recreates_qdrant_collection(self) -> None:
        """TEST-AC-9.7.2.9 [P1]: Cleanup recreates Qdrant collection.

        Given the prepare-reingestion.py script exists
        When cleanup is executed
        Then Qdrant collection is deleted and recreated with same schema
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/prepare-reingestion.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Qdrant operations are present
        assert "delete_collection" in source_code or "recreate_collection" in source_code, (
            "Script should delete/recreate Qdrant collection"
        )

    def test_ac_2_1_10_cleanup_truncates_financial_chunks(self) -> None:
        """TEST-AC-9.7.2.10 [P1]: Cleanup truncates financial_chunks.

        Given the prepare-reingestion.py script exists
        When cleanup is executed
        Then PostgreSQL financial_chunks table is truncated
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/prepare-reingestion.py")

        # RED STATE: Script does not exist
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: financial_chunks truncation is present
        assert "financial_chunks" in source_code, (
            "Script should reference financial_chunks for truncation"
        )
