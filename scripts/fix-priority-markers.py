#!/usr/bin/env python
"""Replace old @pytest.mark.p0/p1/p2/p3 markers with new @pytest.mark.priority("P0") format.

This script:
1. Finds all instances of old priority markers
2. Replaces them with new format
3. Creates backups and validates pytest collection

Story: 3-0-7 (Priority Classification System)
"""

import re
import shutil
import subprocess
from pathlib import Path

# Files that need marker replacement
FAILED_FILES = [
    "tests/e2e/test_ground_truth.py",
    "tests/integration/test_ac3_ground_truth.py",
    "tests/integration/test_page_parallelism.py",
    "tests/unit/test_docling_extraction.py",
    "tests/unit/test_period_normalizer.py",
    "tests/unit/test_shared_clients.py",
    "tests/unit/test_shared_config.py",
    "tests/unit/test_shared_models.py",
]


def replace_priority_markers(file_path: Path) -> bool:
    """Replace old priority markers with new format.

    Args:
        file_path: Path to test file

    Returns:
        True if successful, False otherwise
    """
    # Create backup
    backup_path = file_path.with_suffix(".py.bak")
    shutil.copy2(file_path, backup_path)

    try:
        content = file_path.read_text()

        # Replace markers (preserve indentation)
        replacements = {
            r"@pytest\.mark\.p0": '@pytest.mark.priority("P0")',
            r"@pytest\.mark\.p1": '@pytest.mark.priority("P1")',
            r"@pytest\.mark\.p2": '@pytest.mark.priority("P2")',
            r"@pytest\.mark\.p3": '@pytest.mark.priority("P3")',
        }

        for old_pattern, new_marker in replacements.items():
            content = re.sub(old_pattern, new_marker, content)

        # Write the modified content
        file_path.write_text(content)

        return True

    except Exception as e:
        print(f"ERROR replacing markers in {file_path}: {e}")
        # Restore from backup
        shutil.copy2(backup_path, file_path)
        return False


def validate_pytest_collection(file_path: Path) -> bool:
    """Validate that pytest can collect tests from the file.

    Args:
        file_path: Path to test file

    Returns:
        True if collection succeeds, False otherwise
    """
    result = subprocess.run(
        ["pytest", str(file_path), "--collect-only", "-q"],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def main():
    """Main execution function."""
    print("Story 3-0-7: Fixing priority markers in failed files\n")

    files_processed = 0
    files_failed = []

    for file_path_str in FAILED_FILES:
        file_path = Path(file_path_str)
        print(f"Processing: {file_path}")

        if not file_path.exists():
            print("  ✗ File not found")
            files_failed.append((file_path, "file not found"))
            continue

        # Replace markers
        if replace_priority_markers(file_path):
            # Validate pytest collection
            if validate_pytest_collection(file_path):
                print("  ✓ Markers replaced and validated")
                # Remove backup
                backup_path = file_path.with_suffix(".py.bak")
                if backup_path.exists():
                    backup_path.unlink()
                files_processed += 1
            else:
                print("  ✗ pytest collection failed, restored from backup")
                files_failed.append((file_path, "pytest collection failed"))
                # Restore from backup
                backup_path = file_path.with_suffix(".py.bak")
                if backup_path.exists():
                    shutil.copy2(backup_path, file_path)
        else:
            print("  ✗ Failed to replace markers")
            files_failed.append((file_path, "marker replacement failed"))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files processed: {files_processed}/{len(FAILED_FILES)}")

    if files_failed:
        print(f"\n⚠️  Failed files ({len(files_failed)}):")
        for file_path, reason in files_failed:
            print(f"  - {file_path}: {reason}")
    else:
        print("\n✓ All files processed successfully")


if __name__ == "__main__":
    main()
