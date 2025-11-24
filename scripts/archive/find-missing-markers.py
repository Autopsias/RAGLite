#!/usr/bin/env python
"""Find test functions that are missing @pytest.mark.priority markers.

Story: 3-0-7 (Priority Classification System)
"""

import re
from pathlib import Path


def find_tests_without_priority(file_path: Path) -> list[tuple[int, str]]:
    """Find test functions missing priority markers.

    Args:
        file_path: Path to test file

    Returns:
        List of (line_number, test_name) tuples for tests without priority markers
    """
    content = file_path.read_text()
    lines = content.split("\n")

    tests_without_priority = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for test function definitions
        match = re.match(r"^\s*(?:async\s+)?def\s+(test_\w+)", line)
        if match:
            test_name = match.group(1)

            # Check if there's a priority marker above
            has_priority = False
            j = i - 1
            while j >= 0:
                prev_line = lines[j].strip()
                if "@pytest.mark.priority" in prev_line:
                    has_priority = True
                    break
                if prev_line and not prev_line.startswith("@"):
                    # Hit a non-decorator line, stop searching
                    break
                j -= 1

            if not has_priority:
                tests_without_priority.append((i + 1, test_name))

        i += 1

    return tests_without_priority


def main():
    """Main execution function."""
    print("Finding tests without @pytest.mark.priority markers...\n")

    test_files = sorted(Path("tests").rglob("test_*.py"))

    total_missing = 0
    files_with_missing = []

    for test_file in test_files:
        missing_tests = find_tests_without_priority(test_file)

        if missing_tests:
            print(f"\n{test_file}:")
            for line_num, test_name in missing_tests:
                print(f"  Line {line_num}: {test_name}")
                total_missing += 1
            files_with_missing.append(test_file)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total tests missing priority markers: {total_missing}")
    print(f"Files with missing markers: {len(files_with_missing)}")


if __name__ == "__main__":
    main()
