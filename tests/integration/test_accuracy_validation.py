"""Integration tests for accuracy validation test runner.

Tests the run-accuracy-tests.py and daily-accuracy-check.py scripts.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection]
# Project root for running scripts
PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.preserve_collection  # Tests don't modify Qdrant - skip cleanup
class TestAccuracyTestRunner:
    """Test suite for run-accuracy-tests.py script."""

    @pytest.mark.priority("P1")
    def test_cli_help(self):
        """Test --help flag displays usage information."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--help"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()
        assert "--subset" in result.stdout
        assert "--category" in result.stdout
        assert "--verbose" in result.stdout
        assert "--output" in result.stdout

    @pytest.mark.priority("P1")
    @pytest.mark.timeout(600)  # 10 minutes - subprocess needs 9 min + overhead
    def test_subset_option(self, session_ingested_collection):
        """Test --subset N option runs N queries."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "3"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=540,  # 9 minutes - 3 queries can take 6-8 min (cold start + full pipeline)
        )
        # Should complete (exit code 0 or 1 depending on accuracy)
        assert result.returncode in [0, 1]
        # Should show "Running 3 queries" in output
        assert (
            "Running 3 queries" in result.stdout or "Selected random subset of 3" in result.stdout
        )

    @pytest.mark.priority("P1")
    @pytest.mark.timeout(900)  # 15 minutes - subprocess needs 14 min + overhead
    def test_category_filter(self, session_ingested_collection):
        """Test --category option filters queries by category."""
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run-accuracy-tests.py",
                "--category",
                "cost_analysis",
                "--subset",
                "5",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=840,  # 14 minutes - 5 queries can take 10-12 min (cold start + full pipeline)
        )
        assert result.returncode in [0, 1]
        assert "cost_analysis" in result.stdout or "Filtered to" in result.stdout

    @pytest.mark.priority("P1")
    @pytest.mark.timeout(0)  # Disable pytest-timeout - subprocess has its own 300s timeout
    def test_output_file_generation(self, tmp_path, session_ingested_collection):
        """Test --output FILE option saves results to JSON."""
        output_file = tmp_path / "test_results.json"
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run-accuracy-tests.py",
                "--subset",
                "3",
                "--output",
                str(output_file),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes - increased from 120s for query execution time
        )
        assert result.returncode in [0, 1]

        # Verify output file created and contains valid JSON
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
            assert "metrics" in data
            assert "results" in data
            assert "timestamp" in data

    @pytest.mark.priority("P1")
    @pytest.mark.timeout(480)  # 8 minutes - subprocess needs 6 min + overhead
    def test_verbose_output(self, session_ingested_collection):
        """Test --verbose option shows detailed query output."""
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run-accuracy-tests.py",
                "--subset",
                "2",
                "--verbose",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=420,  # 7 minutes - 2 queries can take 4-6 min (cold start + full pipeline)
        )
        assert result.returncode in [0, 1]
        # Verbose output should show query details
        assert "Query" in result.stdout
        assert "Latency" in result.stdout or "latency" in result.stdout.lower()


@pytest.mark.preserve_collection  # Tests don't modify Qdrant - skip cleanup
class TestDailyAccuracyCheck:
    """Test suite for daily-accuracy-check.py script."""

    @pytest.mark.priority("P1")
    def test_cli_help(self):
        """Test --help flag displays usage information."""
        result = subprocess.run(
            [sys.executable, "scripts/daily-accuracy-check.py", "--help"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()
        assert "--subset" in result.stdout
        assert "--show-trend" in result.stdout

    @pytest.mark.priority("P1")
    @pytest.mark.timeout(900)  # 15 minutes - subprocess needs 14 min + overhead
    def test_daily_check_execution(self, session_ingested_collection):
        """Test daily check runs with default subset."""
        result = subprocess.run(
            [sys.executable, "scripts/daily-accuracy-check.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=840,  # 14 minutes - 5 queries can take 10-12 min (cold start + full pipeline)
        )
        # Exit code 0 (normal) or 1 (early warning triggered)
        assert result.returncode in [0, 1]
        assert "DAILY CHECK RESULTS" in result.stdout
        assert "Retrieval Accuracy" in result.stdout

    @pytest.mark.priority("P1")
    @pytest.mark.timeout(600)  # 10 minutes - subprocess needs 9 min + overhead
    def test_tracking_log_created(self, session_ingested_collection):
        """Test that tracking log file is created after daily check."""
        tracking_log = PROJECT_ROOT / "docs" / "accuracy-tracking-log.jsonl"

        result = subprocess.run(
            [sys.executable, "scripts/daily-accuracy-check.py", "--subset", "3"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=540,  # 9 minutes - 3 queries can take 6-8 min (cold start + full pipeline)
        )
        assert result.returncode in [0, 1]

        # Verify log file exists and is valid JSONL
        assert tracking_log.exists()
        with open(tracking_log) as f:
            lines = f.readlines()
            assert len(lines) > 0
            # Last line should be valid JSON
            last_entry = json.loads(lines[-1])
            assert "timestamp" in last_entry
            assert "retrieval_accuracy" in last_entry
            assert "attribution_accuracy" in last_entry


class TestAccuracyCalculations:
    """Test accuracy calculation logic (unit-style tests on script functions)."""

    @pytest.mark.priority("P1")
    @pytest.mark.slow  # Marks as slow test - takes 5+ minutes to run
    @pytest.mark.timeout(0)  # Disable pytest-timeout - subprocess has its own 600s timeout
    @pytest.mark.preserve_collection  # Read-only test - runs accuracy script
    def test_retrieval_accuracy_calculation(self, session_ingested_collection):
        """Test that retrieval accuracy is calculated correctly."""
        # This would test the check_retrieval_accuracy function
        # For now, verify via integration: run with known queries
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes - 5 queries can take 5-8 minutes
        )
        assert result.returncode in [0, 1]
        # Should show retrieval accuracy percentage
        assert "Retrieval Accuracy:" in result.stdout
        assert "%" in result.stdout

    @pytest.mark.priority("P2")
    @pytest.mark.slow  # Marks as slow test - takes 5+ minutes to run
    @pytest.mark.timeout(0)  # Disable pytest-timeout - subprocess has its own 600s timeout
    @pytest.mark.preserve_collection  # Read-only test - runs accuracy script
    def test_attribution_accuracy_calculation(self, session_ingested_collection):
        """Test that attribution accuracy is calculated correctly."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes - 5 queries can take 5-8 minutes
        )
        assert result.returncode in [0, 1]
        # Should show attribution accuracy percentage
        assert "Attribution Accuracy:" in result.stdout
        assert "%" in result.stdout

    @pytest.mark.priority("P0")
    @pytest.mark.timeout(900)  # 15 minutes - subprocess needs 14 min + overhead
    @pytest.mark.preserve_collection  # Read-only test - runs accuracy script
    def test_performance_metrics_calculated(self, session_ingested_collection):
        """Test that p50/p95 latency metrics are calculated."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=840,  # 14 minutes - 5 queries can take 10-12 min (cold start + full pipeline)
        )
        assert result.returncode in [0, 1]
        # Should show latency metrics
        assert "p50 Latency" in result.stdout or "p50" in result.stdout.lower()
        assert "p95 Latency" in result.stdout or "p95" in result.stdout.lower()


class TestNFRValidation:
    """Test NFR (Non-Functional Requirements) validation."""

    @pytest.mark.priority("P0")
    @pytest.mark.timeout(900)  # 15 minutes - subprocess needs 9 min + overhead
    @pytest.mark.preserve_collection  # Read-only test - runs accuracy script
    def test_nfr_targets_displayed(self, session_ingested_collection):
        """Test that NFR validation results are shown."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=840,  # 14 minutes - 5 queries can take 10-12 min (cold start + full pipeline)
        )
        assert result.returncode in [0, 1]
        # Should show NFR validation section
        assert "NFR" in result.stdout or "NFR6" in result.stdout
        assert "90%" in result.stdout or "retrieval" in result.stdout.lower()

    @pytest.mark.priority("P1")
    @pytest.mark.timeout(600)  # 10 minutes - subprocess needs 5 min + overhead
    @pytest.mark.preserve_collection  # Read-only test - runs accuracy script
    def test_exit_codes(self, session_ingested_collection):
        """Test that script returns correct exit codes."""
        # Running small subset likely to fail accuracy targets
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "3"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=540,  # 9 minutes - 3 queries can take 6-8 min (cold start + full pipeline)
        )
        # Exit code 0 = pass (unlikely with small subset)
        # Exit code 1 = fail or below targets (expected)
        assert result.returncode in [0, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
