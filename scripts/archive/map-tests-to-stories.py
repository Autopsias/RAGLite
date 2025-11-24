#!/usr/bin/env python3
"""Map test files to stories for systematic test ID assignment.

This script analyzes test files to identify which story they belong to,
helping with systematic test ID rollout for Story 3-0-6.

Usage:
    python scripts/map-tests-to-stories.py
"""

import re
from collections import defaultdict
from pathlib import Path


def extract_story_hints(file_path: Path, content: str) -> list[str]:
    """Extract story hints from test file content.

    Looks for:
    - Story references in docstrings
    - Story numbers in comments
    - AC references (e.g., AC1, AC2)
    - Filename patterns
    """
    hints = []

    # Check filename for story patterns
    filename = file_path.stem

    # Pattern: test_story_2_10_something.py or test_ac3_ground_truth.py
    story_patterns = [
        r"story[_-]?(\d+)[._-](\d+)",
        r"ac(\d+)",
        r"(\d+)[._-](\d+)[._-]",
    ]

    for pattern in story_patterns:
        matches = re.findall(pattern, filename, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                hints.append(f"{match[0]}.{match[1]}" if len(match) > 1 else f"AC{match[0]}")
            else:
                hints.append(match)

    # Check content for story references
    content_patterns = [
        r"Story\s+(\d+)\.(\d+)",
        r"story[_\s]+(\d+)\.(\d+)",
        r"Epic\s+(\d+)",
        r"AC(\d+)",
        r'test_id:\s*"?(\d+\.\d+)',
    ]

    for pattern in content_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple) and len(match) == 2:
                hints.append(f"{match[0]}.{match[1]}")
            elif isinstance(match, tuple):
                hints.append(f"AC{match[0]}")
            else:
                hints.append(match)

    # Check for specific story keywords
    story_keywords = {
        "query_classifier": "2.10",
        "table_aware_chunking": "2.8",
        "ground_truth": "2.5",
        "sql_routing": "2.13",
        "pypdfium": "2.1",
        "page_parallelism": "2.2",
        "fixed_chunking": "2.3",
        "contextual": "2.4",
        "hybrid_search": "2.7",
        "multi_index": "2.7",
        "fuzzy_entity": "2.13",
    }

    filename_lower = filename.lower()
    for keyword, story in story_keywords.items():
        if keyword in filename_lower:
            hints.append(story)

    return list(set(hints))  # Remove duplicates


def count_tests_in_file(content: str) -> int:
    """Count number of test functions in file."""
    # Count test functions (def test_* or async def test_*)
    test_functions = re.findall(r"(?:async\s+)?def\s+(test_\w+)", content)
    return len(test_functions)


def determine_test_type(file_path: Path) -> str:
    """Determine test type from file location."""
    parts = file_path.parts
    if "unit" in parts:
        return "UNIT"
    elif "integration" in parts:
        return "INTEGRATION"
    elif "e2e" in parts:
        return "E2E"
    elif "perf" in parts or "performance" in parts:
        return "PERF"
    else:
        return "UNKNOWN"


def main():
    """Analyze test files and generate story mapping."""
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "tests"

    # Find all test files
    test_files = list(test_dir.rglob("test_*.py"))

    # Exclude conftest.py and helper files
    test_files = [f for f in test_files if "conftest" not in f.stem and "fixtures" not in str(f)]

    print("# Test File → Story Mapping")
    print("# Generated for Story 3-0-6 (Test ID Assignment)")
    print(f"# Total test files: {len(test_files)}")
    print()

    # Group by story
    story_map = defaultdict(list)
    unknown_files = []

    for test_file in sorted(test_files):
        content = test_file.read_text()
        test_count = count_tests_in_file(content)
        test_type = determine_test_type(test_file)
        story_hints = extract_story_hints(test_file, content)

        rel_path = test_file.relative_to(project_root)

        if story_hints:
            # Use most specific hint (longest)
            primary_story = max(story_hints, key=lambda x: len(x))
            story_map[primary_story].append((rel_path, test_count, test_type, story_hints))
        else:
            unknown_files.append((rel_path, test_count, test_type))

    # Print story mapping
    print("## Files Mapped to Stories\n")
    for story in sorted(
        story_map.keys(),
        key=lambda x: (
            # Sort by epic.story number
            float(x) if "." in x and x.replace(".", "").isdigit() else 999
        ),
    ):
        files = story_map[story]
        total_tests = sum(count for _, count, _, _ in files)
        print(f"### Story {story} ({len(files)} files, ~{total_tests} tests)\n")
        for file_path, test_count, test_type, hints in files:
            hints_str = ", ".join(hints) if len(hints) > 1 else hints[0]
            print(f"- `{file_path}` ({test_count} tests, {test_type}) - Hints: {hints_str}")
        print()

    # Print unknown files
    if unknown_files:
        total_unknown_tests = sum(count for _, count, _ in unknown_files)
        print(
            f"## Files Needing Manual Story Assignment ({len(unknown_files)} files, ~{total_unknown_tests} tests)\n"
        )
        for file_path, test_count, test_type in unknown_files:
            print(f"- `{file_path}` ({test_count} tests, {test_type})")
        print()

    # Summary statistics
    total_tests = sum(sum(count for _, count, _, _ in files) for files in story_map.values())
    total_tests += sum(count for _, count, _ in unknown_files)

    print("## Summary\n")
    print(f"- **Total test files:** {len(test_files)}")
    print(f"- **Total tests (estimated):** ~{total_tests}")
    print(
        f"- **Files with story hints:** {len(story_map)} stories, {len(test_files) - len(unknown_files)} files"
    )
    print(f"- **Files needing manual review:** {len(unknown_files)} files")
    print()

    print("## Next Steps\n")
    print("1. Review story assignments above")
    print("2. Manually assign stories to 'unknown' files")
    print("3. Start adding test IDs using format: `{story}-{type}-{seq}`")
    print("4. Example: `2.10-UNIT-001` for first unit test in Story 2.10")


if __name__ == "__main__":
    main()
