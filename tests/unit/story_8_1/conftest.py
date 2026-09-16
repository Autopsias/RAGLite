"""Shared fixtures and utilities for Story 8.1 acceptance tests."""

from pathlib import Path

import pytest

# Constants for file size limits (from .claude/rules/file-size-limits.md)
HARD_LIMIT_LOC = 500
WARNING_THRESHOLD_LOC = 400

# Project root for file path calculations
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def count_lines(file_path: Path) -> int:
    """Count total lines in a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Total line count
    """
    if not file_path.exists():
        return 0
    try:
        with open(file_path, encoding="utf-8") as f:
            return len(f.readlines())
    except Exception:
        return 0


def get_python_files(directory: Path) -> list[Path]:
    """Get all Python files in a directory recursively.

    Args:
        directory: Directory to search

    Returns:
        List of Python file paths
    """
    if not directory.exists():
        return []
    return list(directory.rglob("*.py"))


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def hard_limit() -> int:
    """Get the hard LOC limit for files."""
    return HARD_LIMIT_LOC
