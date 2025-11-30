#!/usr/bin/env python
"""Add @pytest.mark.priority() markers to all unclassified tests.

This script:
1. Scans all test files for test functions without priority markers
2. Classifies tests based on name/docstring patterns
3. Adds priority markers in the correct format
4. Creates backups and validates pytest collection

Story: 3-0-7 (Priority Classification System)
"""

import re
import shutil
from pathlib import Path

# Classification patterns (check in order P0 -> P1 -> P2 -> P3)
PRIORITY_PATTERNS = {
    "P0": [
        r"ground_truth",
        r"accuracy.*validation",
        r"baseline",
        r"regression.*floor",
        r"gate",
        r"epic.*completion",
        r"security",
        r"data.*corruption",
        r"ac3",  # AC3 ground truth tests
        r"ac4",  # AC4 comprehensive tests
    ],
    "P1": [
        r"hybrid.*search",
        r"query.*classif",
        r"mcp.*server",
        r"ingestion",
        r"retrieval",
        r"embedding",
        r"core",
        r"search.*integration",
        r"response.*format",
        r"main.*integration",
    ],
    "P2": [
        r"fuzzy",
        r"transposed",
        r"metadata",
        r"multi.*entity",
        r"optimization",
        r"performance",
        r"edge.*case",
        r"sql.*routing",
        r"table.*aware",
        r"element.*metadata",
        r"fixed.*chunking",
        r"page.*parallelism",
        r"pypdfium",
        r"multi.*index",
        r"ac1",  # AC1 fuzzy matching tests
        r"ac2",  # AC2 multi-entity tests
    ],
    "P3": [
        r"period.*normalizer",
        r"rare",
        r"benchmark",
        r"malformed",
        r"invalid",
        r"error.*handling",
    ],
}


def classify_test(test_name: str, docstring: str, file_path: Path) -> str:
    """Classify a test based on name, docstring, and file location.

    Args:
        test_name: Name of the test function
        docstring: Test docstring (or empty string)
        file_path: Path to the test file

    Returns:
        Priority level: "P0", "P1", "P2", or "P3"
    """
    # Combine test name and docstring for pattern matching
    search_text = f"{test_name} {docstring}".lower()

    # Apply default rules based on directory
    if "e2e" in str(file_path):
        return "P0"  # E2E tests are critical path

    # Check patterns in order P0 -> P1 -> P2 -> P3
    for priority, patterns in PRIORITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                return priority

    # Default rules by directory
    if "integration" in str(file_path):
        return "P1"  # Integration tests are core features
    elif "unit" in str(file_path):
        return "P2"  # Unit tests are edge cases

    # Final fallback
    return "P2"


def extract_test_info(file_path: Path) -> list[tuple[str, str, int]]:
    """Extract test functions that need priority markers.

    Args:
        file_path: Path to test file

    Returns:
        List of (test_name, docstring, line_number) tuples
    """
    content = file_path.read_text()
    lines = content.split("\n")

    tests_needing_markers = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for test function definitions
        if re.match(r"^\s*(async\s+)?def\s+test_", line):
            # Check if previous lines have @pytest.mark.priority
            has_priority = False
            j = i - 1
            while j >= 0 and (lines[j].strip().startswith("@") or lines[j].strip() == ""):
                if "@pytest.mark.priority" in lines[j]:
                    has_priority = True
                    break
                if lines[j].strip() and not lines[j].strip().startswith("@"):
                    break
                j -= 1

            if not has_priority:
                # Extract test name
                match = re.match(r"^\s*(?:async\s+)?def\s+(test_\w+)", line)
                if match:
                    test_name = match.group(1)

                    # Extract docstring (next non-empty line if it's a docstring)
                    docstring = ""
                    k = i + 1
                    if k < len(lines) and '"""' in lines[k]:
                        # Multi-line docstring
                        docstring_lines = [lines[k]]
                        k += 1
                        while k < len(lines) and '"""' not in lines[k]:
                            docstring_lines.append(lines[k])
                            k += 1
                        if k < len(lines):
                            docstring_lines.append(lines[k])
                        docstring = " ".join(docstring_lines)

                    tests_needing_markers.append((test_name, docstring, i))

        i += 1

    return tests_needing_markers


def add_priority_marker(file_path: Path, test_info: list[tuple[str, str, int]]) -> bool:
    """Add priority markers to a test file.

    Args:
        file_path: Path to test file
        test_info: List of (test_name, docstring, line_number) tuples

    Returns:
        True if successful, False otherwise
    """
    if not test_info:
        return True  # Nothing to do

    # Create backup
    backup_path = file_path.with_suffix(".py.bak")
    shutil.copy2(file_path, backup_path)

    try:
        content = file_path.read_text()
        lines = content.split("\n")

        # Process in reverse order to maintain line numbers
        for test_name, docstring, line_num in reversed(test_info):
            # Classify the test
            priority = classify_test(test_name, docstring, file_path)

            # Find the insertion point (after test_id marker if present, or before def)
            insert_line = line_num

            # Check if there's a @pytest.mark.test_id marker above
            j = line_num - 1
            while j >= 0 and lines[j].strip().startswith("@pytest.mark"):
                j -= 1

            # Insert after last decorator
            insert_line = j + 1

            # Get indentation from the def line
            def_line = lines[line_num]
            indent = len(def_line) - len(def_line.lstrip())

            # Create the priority marker
            priority_marker = " " * indent + f'@pytest.mark.priority("{priority}")'

            # Insert the marker
            lines.insert(insert_line, priority_marker)

        # Write the modified content
        file_path.write_text("\n".join(lines))

        return True

    except Exception as e:
        print(f"ERROR adding markers to {file_path}: {e}")
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
    import subprocess

    result = subprocess.run(
        ["pytest", str(file_path), "--collect-only", "-q"],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def main():
    """Main execution function."""
    print("Story 3-0-7: Adding priority markers to all tests\n")

    test_files = sorted(Path("tests").rglob("test_*.py"))

    files_processed = 0
    markers_added = 0
    failed_files = []

    priority_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}

    for test_file in test_files:
        print(f"Processing: {test_file}")

        # Extract tests needing markers
        tests_info = extract_test_info(test_file)

        if not tests_info:
            print("  ✓ No markers needed (already classified)")
            continue

        print(f"  Found {len(tests_info)} tests needing markers")

        # Classify and count
        for test_name, docstring, _ in tests_info:
            priority = classify_test(test_name, docstring, test_file)
            priority_counts[priority] += 1
            print(f"    - {test_name} → {priority}")

        # Add markers
        if add_priority_marker(test_file, tests_info):
            # Validate pytest collection
            if validate_pytest_collection(test_file):
                print("  ✓ Markers added and validated")
                # Remove backup
                backup_path = test_file.with_suffix(".py.bak")
                if backup_path.exists():
                    backup_path.unlink()
                files_processed += 1
                markers_added += len(tests_info)
            else:
                print("  ✗ pytest collection failed, restored from backup")
                failed_files.append((test_file, "pytest collection failed"))
                # Restore from backup
                backup_path = test_file.with_suffix(".py.bak")
                if backup_path.exists():
                    shutil.copy2(backup_path, test_file)
        else:
            print("  ✗ Failed to add markers")
            failed_files.append((test_file, "marker addition failed"))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files modified: {files_processed}")
    print(f"Markers added: {markers_added}")
    print("\nPriority Distribution:")
    total = sum(priority_counts.values())
    for priority in ["P0", "P1", "P2", "P3"]:
        count = priority_counts[priority]
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {priority}: {count:3d} ({pct:5.1f}%)")

    if failed_files:
        print(f"\n⚠️  Failed files ({len(failed_files)}):")
        for file_path, reason in failed_files:
            print(f"  - {file_path}: {reason}")

    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)

    # Run full pytest collection
    import subprocess

    result = subprocess.run(
        ["pytest", "tests/", "--collect-only", "-q"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✓ All tests pass pytest collection")
    else:
        print("✗ pytest collection failed:")
        print(result.stdout)
        print(result.stderr)

    # Run priority analysis
    print("\nRunning priority analysis script...")
    result = subprocess.run(
        ["python", "scripts/analyze-test-priorities.py"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)


if __name__ == "__main__":
    main()
