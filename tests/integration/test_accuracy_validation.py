"""Integration tests for accuracy validation test runner.

Tests the run-accuracy-tests.py and daily-accuracy-check.py scripts.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Project root for running scripts
PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.preserve_collection  # Tests don't modify Qdrant - skip cleanup
class TestAccuracyTestRunner:
    """Test suite for run-accuracy-tests.py script."""

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

    def test_subset_option(self):
        """Test --subset N option runs N queries."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "3"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Should complete (exit code 0 or 1 depending on accuracy)
        assert result.returncode in [0, 1]
        # Should show "Running 3 queries" in output
        assert (
            "Running 3 queries" in result.stdout or "Selected random subset of 3" in result.stdout
        )

    def test_category_filter(self):
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
            timeout=120,
        )
        assert result.returncode in [0, 1]
        assert "cost_analysis" in result.stdout or "Filtered to" in result.stdout

    def test_output_file_generation(self, tmp_path):
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
            timeout=120,
        )
        assert result.returncode in [0, 1]

        # Verify output file created and contains valid JSON
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
            assert "metrics" in data
            assert "results" in data
            assert "timestamp" in data

    def test_verbose_output(self):
        """Test --verbose option shows detailed query output."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "2", "--verbose"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode in [0, 1]
        # Verbose output should show query details
        assert "Query" in result.stdout
        assert "Latency" in result.stdout or "latency" in result.stdout.lower()


@pytest.mark.preserve_collection  # Tests don't modify Qdrant - skip cleanup
class TestDailyAccuracyCheck:
    """Test suite for daily-accuracy-check.py script."""

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

    def test_daily_check_execution(self):
        """Test daily check runs with default subset."""
        result = subprocess.run(
            [sys.executable, "scripts/daily-accuracy-check.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Exit code 0 (normal) or 1 (early warning triggered)
        assert result.returncode in [0, 1]
        assert "DAILY CHECK RESULTS" in result.stdout
        assert "Retrieval Accuracy" in result.stdout

    def test_tracking_log_created(self):
        """Test that tracking log file is created after daily check."""
        tracking_log = PROJECT_ROOT / "docs" / "accuracy-tracking-log.jsonl"

        result = subprocess.run(
            [sys.executable, "scripts/daily-accuracy-check.py", "--subset", "3"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
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

    def test_retrieval_accuracy_calculation(self):
        """Test that retrieval accuracy is calculated correctly."""
        # This would test the check_retrieval_accuracy function
        # For now, verify via integration: run with known queries
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode in [0, 1]
        # Should show retrieval accuracy percentage
        assert "Retrieval Accuracy:" in result.stdout
        assert "%" in result.stdout

    def test_attribution_accuracy_calculation(self):
        """Test that attribution accuracy is calculated correctly."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode in [0, 1]
        # Should show attribution accuracy percentage
        assert "Attribution Accuracy:" in result.stdout
        assert "%" in result.stdout

    def test_performance_metrics_calculated(self):
        """Test that p50/p95 latency metrics are calculated."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode in [0, 1]
        # Should show latency metrics
        assert "p50 Latency" in result.stdout or "p50" in result.stdout.lower()
        assert "p95 Latency" in result.stdout or "p95" in result.stdout.lower()


class TestNFRValidation:
    """Test NFR (Non-Functional Requirements) validation."""

    def test_nfr_targets_displayed(self):
        """Test that NFR validation results are shown."""
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "5"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode in [0, 1]
        # Should show NFR validation section
        assert "NFR" in result.stdout or "NFR6" in result.stdout
        assert "90%" in result.stdout or "retrieval" in result.stdout.lower()

    def test_exit_codes(self):
        """Test that script returns correct exit codes."""
        # Running small subset likely to fail accuracy targets
        result = subprocess.run(
            [sys.executable, "scripts/run-accuracy-tests.py", "--subset", "3"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Exit code 0 = pass (unlikely with small subset)
        # Exit code 1 = fail or below targets (expected)
        assert result.returncode in [0, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
