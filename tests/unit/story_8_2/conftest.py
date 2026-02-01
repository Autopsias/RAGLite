"""Shared fixtures and utilities for Story 8.2 ATDD tests.

Story 8.2: External Data Client Refactoring

Provides common utilities for:
- File size validation
- Module structure verification
- Path constants
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
RAGLITE_ROOT = PROJECT_ROOT / "raglite"
TESTS_ROOT = PROJECT_ROOT / "tests"

# External data paths
EXTERNAL_DATA_DIR = RAGLITE_ROOT / "external_data"
CLIENTS_DIR = EXTERNAL_DATA_DIR / "clients"
STORAGE_DIR = EXTERNAL_DATA_DIR / "storage"

# Target file paths (current large files)
STORAGE_FILE = EXTERNAL_DATA_DIR / "storage.py"
BASEGOV_FILE = CLIENTS_DIR / "basegov.py"
ECB_FILE = CLIENTS_DIR / "ecb.py"
EUROSTAT_FILE = CLIENTS_DIR / "eurostat.py"

# Expected submodule paths after refactoring
BASEGOV_PACKAGE = CLIENTS_DIR / "basegov"
ECB_PACKAGE = CLIENTS_DIR / "ecb"
EUROSTAT_PACKAGE = CLIENTS_DIR / "eurostat"
STORAGE_PACKAGE = EXTERNAL_DATA_DIR / "storage"
BASE_CLIENT_FILE = CLIENTS_DIR / "base.py"

# LOC limits
HARD_LOC_LIMIT = 500
SHIM_LOC_LIMIT = 100

# Test paths
EXTERNAL_DATA_TESTS_DIR = TESTS_ROOT / "unit" / "external_data"


def count_lines_of_code(file_path: Path) -> int:
    """Count non-empty, non-comment lines in a Python file.

    Args:
        file_path: Path to Python file

    Returns:
        Line count excluding blank lines and comments
    """
    if not file_path.exists():
        return 0

    loc = 0
    in_multiline_string = False
    multiline_char = None

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            # Handle multiline strings
            if not in_multiline_string:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    multiline_char = stripped[:3]
                    if stripped.count(multiline_char) == 1:
                        in_multiline_string = True
                    continue
                if stripped and not stripped.startswith("#"):
                    loc += 1
            else:
                if multiline_char in stripped:
                    in_multiline_string = False
                    multiline_char = None

    return loc


def count_lines_simple(file_path: Path) -> int:
    """Count total lines in file (simple count for consistency with story).

    Args:
        file_path: Path to file

    Returns:
        Total line count
    """
    if not file_path.exists():
        return 0
    with open(file_path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def get_python_files(directory: Path) -> list[Path]:
    """Get all Python files in a directory (non-recursive).

    Args:
        directory: Directory path

    Returns:
        List of Python file paths
    """
    if not directory.exists():
        return []
    return list(directory.glob("*.py"))


def get_python_files_recursive(directory: Path) -> list[Path]:
    """Get all Python files in a directory (recursive).

    Args:
        directory: Directory path

    Returns:
        List of Python file paths
    """
    if not directory.exists():
        return []
    return list(directory.rglob("*.py"))


@pytest.fixture
def project_root() -> Path:
    """Return project root path."""
    return PROJECT_ROOT


@pytest.fixture
def external_data_dir() -> Path:
    """Return external_data directory path."""
    return EXTERNAL_DATA_DIR


@pytest.fixture
def clients_dir() -> Path:
    """Return clients directory path."""
    return CLIENTS_DIR
