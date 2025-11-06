#!/usr/bin/env python3
"""Generate test coverage report showing story-to-test mapping (Story 3-0-6 AC4).

This script analyzes all test files, extracts test IDs, and generates a
comprehensive markdown report showing which stories have test coverage.

Usage:
    python scripts/generate-test-coverage-report.py
    python scripts/generate-test-coverage-report.py --output docs/test-coverage-report.md

Output:
    - Markdown report with story-to-test mapping
    - Coverage statistics by epic and story
    - Breakdown by test type (UNIT/INTEGRATION/E2E/PERF)
    - Stories without test coverage (if any)
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path


def extract_test_ids_from_file(file_path: Path) -> list[tuple[str, str, int]]:
    """Extract all test IDs from a test file.

    Args:
        file_path: Path to test file

    Returns:
        List of (test_id, function_name, line_number) tuples
    """
    content = file_path.read_text()
    test_ids = []

    # Pattern: @pytest.mark.test_id("2.10-UNIT-001")
    pattern = r'@pytest\.mark\.test_id\(["\']([^"\']+)["\']\)\s*\n\s*(?:async\s+)?def\s+(test_\w+)'

    for match in re.finditer(pattern, content):
        test_id = match.group(1)
        function_name = match.group(2)
        # Find line number
        line_number = content[: match.start()].count("\n") + 1
        test_ids.append((test_id, function_name, line_number))

    return test_ids


def parse_test_id(test_id: str) -> tuple[str, str, str, int]:
    """Parse test ID into components.

    Args:
        test_id: Test ID in format "2.10-UNIT-001"

    Returns:
        Tuple of (epic, story, test_type, sequence)
    """
    match = re.match(r"^(\d+)\.(\d+)-(\w+)-(\d{3})$", test_id)
    if not match:
        raise ValueError(f"Invalid test ID format: {test_id}")

    epic = match.group(1)
    story = match.group(2)
    test_type = match.group(3)
    sequence = int(match.group(4))

    return epic, story, test_type, sequence


def generate_coverage_report(project_root: Path) -> str:
    """Generate test coverage report in markdown format.

    Args:
        project_root: Root directory of the project

    Returns:
        Markdown report as string
    """
    tests_dir = project_root / "tests"

    # Find all test files
    test_files = list(tests_dir.rglob("test_*.py"))
    # Exclude conftest and fixtures
    test_files = [f for f in test_files if "conftest" not in f.stem and "fixtures" not in str(f)]

    # Extract all test IDs
    all_test_ids = []
    file_test_mapping = {}  # file -> [(test_id, function_name, line_number)]

    for test_file in sorted(test_files):
        test_ids = extract_test_ids_from_file(test_file)
        if test_ids:
            rel_path = test_file.relative_to(project_root)
            file_test_mapping[str(rel_path)] = test_ids
            all_test_ids.extend(test_ids)

    # Group by story
    story_tests = defaultdict(lambda: {"UNIT": [], "INTEGRATION": [], "E2E": [], "PERF": []})

    for test_id, func_name, _line_num in all_test_ids:
        try:
            epic, story, test_type, sequence = parse_test_id(test_id)
            story_key = f"{epic}.{story}"
            story_tests[story_key][test_type].append((test_id, func_name))
        except ValueError as e:
            print(f"Warning: {e}")
            continue

    # Generate markdown report
    report_lines = [
        "# Test Coverage Report",
        "",
        f"**Generated:** {Path(__file__).name}",
        "**Story:** 3-0-6 (Test ID Traceability System)",
        "**Purpose:** Track test coverage by story for traceability",
        "",
        "---",
        "",
        "## Summary Statistics",
        "",
        f"- **Total Test Files:** {len(file_test_mapping)}",
        f"- **Total Tests with IDs:** {len(all_test_ids)}",
        f"- **Stories with Tests:** {len(story_tests)}",
        "",
        "### Test Type Distribution",
        "",
    ]

    # Calculate type distribution
    type_counts = defaultdict(int)
    for story_data in story_tests.values():
        for test_type, tests in story_data.items():
            type_counts[test_type] += len(tests)

    report_lines.append("| Test Type | Count | Percentage |")
    report_lines.append("|-----------|-------|------------|")
    for test_type in ["UNIT", "INTEGRATION", "E2E", "PERF"]:
        count = type_counts[test_type]
        percentage = (count / len(all_test_ids) * 100) if all_test_ids else 0
        report_lines.append(f"| {test_type} | {count} | {percentage:.1f}% |")

    total_count = sum(type_counts.values())
    report_lines.append(f"| **Total** | **{total_count}** | **100.0%** |")
    report_lines.append("")

    # Epic-level summary
    epic_summary = defaultdict(lambda: {"stories": set(), "tests": 0})
    for story_key, story_data in story_tests.items():
        epic = story_key.split(".")[0]
        epic_summary[epic]["stories"].add(story_key)
        epic_summary[epic]["tests"] += sum(len(tests) for tests in story_data.values())

    report_lines.extend(
        [
            "### Coverage by Epic",
            "",
            "| Epic | Stories | Total Tests |",
            "|------|---------|-------------|",
        ]
    )

    for epic in sorted(epic_summary.keys(), key=int):
        stories_count = len(epic_summary[epic]["stories"])
        tests_count = epic_summary[epic]["tests"]
        report_lines.append(f"| Epic {epic} | {stories_count} | {tests_count} |")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Detailed story breakdown
    report_lines.extend(
        [
            "## Detailed Coverage by Story",
            "",
        ]
    )

    for story_key in sorted(story_tests.keys(), key=lambda x: tuple(map(int, x.split(".")))):
        story_data = story_tests[story_key]

        # Calculate total tests for this story
        total_story_tests = sum(len(tests) for tests in story_data.values())

        report_lines.extend(
            [
                f"### Story {story_key} ({total_story_tests} tests)",
                "",
            ]
        )

        # Breakdown by test type
        for test_type in ["UNIT", "INTEGRATION", "E2E", "PERF"]:
            tests = story_data[test_type]
            if tests:
                report_lines.append(f"**{test_type} Tests ({len(tests)}):**")
                report_lines.append("")
                for test_id, func_name in sorted(tests):
                    report_lines.append(f"- `{test_id}` - {func_name}")
                report_lines.append("")

    report_lines.extend(
        [
            "---",
            "",
            "## Test Files",
            "",
            "Complete list of test files with test ID counts:",
            "",
            "| File | Test IDs | Location |",
            "|------|----------|----------|",
        ]
    )

    for file_path in sorted(file_test_mapping.keys()):
        test_count = len(file_test_mapping[file_path])
        # Determine test type from path
        if "/unit/" in file_path:
            location = "Unit Tests"
        elif "/integration/" in file_path:
            location = "Integration Tests"
        elif "/e2e/" in file_path:
            location = "E2E Tests"
        else:
            location = "Other"

        report_lines.append(f"| `{file_path}` | {test_count} | {location} |")

    report_lines.extend(
        [
            "",
            "---",
            "",
            "## Usage",
            "",
            "### Finding Tests for a Story",
            "",
            "```bash",
            "# Run all tests for Story 2.10",
            'pytest tests/ -k "2.10" -v',
            "",
            "# Run only unit tests for Story 2.10",
            'pytest tests/unit/ -k "2.10" -v',
            "",
            "# Run only integration tests for Epic 2",
            'pytest tests/integration/ -k "2." -v',
            "```",
            "",
            "### Viewing Test IDs in Code",
            "",
            "```bash",
            "# Search for all Story 2.10 test IDs",
            'grep -r "2.10-" tests/',
            "",
            "# List all test IDs in a file",
            'grep "@pytest.mark.test_id" tests/unit/test_query_classifier.py',
            "```",
            "",
            "---",
            "",
            "## Notes",
            "",
            "- **Test ID Format:** `{epic}.{story}-{type}-{seq}` (e.g., `2.10-UNIT-001`)",
            "- **Parametrized Tests:** Share the same test ID across all parameter variations",
            "- **Sequence Numbers:** Unique within each story-type combination, assigned globally across all files",
            "",
            "**Related Documentation:**",
            "- Testing Guidelines: `docs/testing-guidelines.md`",
            "- Story 3-0-6: `docs/stories/3-0-6-test-id-traceability-system.md`",
            "- Story 3-0-7: `docs/stories/3-0-7-priority-classification-system.md`",
            "",
        ]
    )

    return "\n".join(report_lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate test coverage report by story (Story 3-0-6 AC4)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="docs/test-coverage-report.md",
        help="Output file path (default: docs/test-coverage-report.md)",
    )
    args = parser.parse_args()

    print("📊 Generating Test Coverage Report (Story 3-0-6 AC4)")
    print("=" * 60)

    # Get project root
    project_root = Path(__file__).parent.parent

    # Generate report
    print("Analyzing test files...")
    report = generate_coverage_report(project_root)

    # Write to file
    output_path = project_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    print(f"\n✅ Report generated: {output_path}")
    print(f"📄 View with: cat {output_path}")
    print("\n💡 Quick stats:")

    # Print summary
    lines = report.split("\n")
    for line in lines:
        if (
            line.startswith("- **Total Test Files:**")
            or line.startswith("- **Total Tests with IDs:**")
            or line.startswith("- **Stories with Tests:**")
        ):
            print(f"  {line}")


if __name__ == "__main__":
    main()
