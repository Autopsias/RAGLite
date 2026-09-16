"""Shared helper functions for Story 8.5 ATDD tests."""

import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


def run_pytest_collect(
    test_path: str,
    warnings_filter: str = "default::DeprecationWarning",
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    """Run pytest collection and capture output.

    Args:
        test_path: Path to test file or directory
        warnings_filter: Warning filter to use (default: DeprecationWarning)
        timeout: Timeout in seconds

    Returns:
        Completed process with stdout/stderr
    """
    project_root = get_project_root()

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(project_root / test_path),
            "--collect-only",
            "-W",
            warnings_filter,
            "-q",
        ],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        timeout=timeout,
    )
