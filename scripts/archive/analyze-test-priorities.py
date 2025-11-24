#!/usr/bin/env python
"""Analyze test priority distribution across the test suite.

This script scans all test files for @pytest.mark.priority markers
and generates a comprehensive report showing distribution and estimated
execution times.

Story: 3-0-7 (Priority Classification System)
"""

import re
from collections import defaultdict
from pathlib import Path


def extract_priorities():
    """Extract all test priorities from test files.

    Returns:
        tuple: (priorities_dict, total_tests) where priorities_dict maps
               priority level to list of test file paths
    """
    test_files = sorted(Path("tests").rglob("test_*.py"))
    priorities = defaultdict(list)
    test_details = defaultdict(list)  # Store test details
    total_tests = 0

    for test_file in test_files:
        content = test_file.read_text()

        # Find all test functions with priority markers
        # Pattern: @pytest.mark.priority("Px") followed by optional decorators, then def test_
        # Use DOTALL to match across multiple lines (decorators)
        test_pattern = r'@pytest\.mark\.priority\("([^"]+)"\)[^\n]*?\n(?:[^\n]*@[^\n]+\n)*\s*(?:async\s+)?def\s+(test_\w+)'

        for match in re.finditer(test_pattern, content, re.DOTALL):
            priority = match.group(1)
            test_name = match.group(2)
            priorities[priority].append(str(test_file))
            test_details[priority].append(f"{test_file.name}::{test_name}")
            total_tests += 1

    return priorities, test_details, total_tests


def calculate_percentiles(items: list[float], percentile: float) -> float:
    """Calculate percentile value from a sorted list.

    Args:
        items: Sorted list of values
        percentile: Percentile to calculate (0-100)

    Returns:
        Value at the specified percentile
    """
    if not items:
        return 0.0

    k = (len(items) - 1) * (percentile / 100)
    f = int(k)
    c = f + 1

    if c >= len(items):
        return items[-1]

    return items[f] + (k - f) * (items[c] - items[f])


def generate_priority_report():
    """Generate markdown priority distribution report."""
    priorities, test_details, total = extract_priorities()

    print("# Test Priority Distribution Report\n")
    print("**Generated:** 2025-11-05")
    print(f"**Total Tests:** {total}\n")

    print("## Summary\n")
    print("This report shows the distribution of test priorities across the RAGLite")
    print("test suite, enabling smart CI/CD execution strategies.\n")

    print("## Distribution\n")
    print("| Priority | Count | Percentage | Target | Status |")
    print("|----------|-------|------------|--------|--------|")

    targets = {"P0": (15, 20), "P1": (30, 40), "P2": (30, 40), "P3": (10, 20)}

    for priority in ["P0", "P1", "P2", "P3"]:
        count = len(test_details[priority])
        pct = (count / total * 100) if total > 0 else 0
        min_target, max_target = targets[priority]
        status = "✅" if min_target <= pct <= max_target else "⚠️"
        print(f"| {priority} | {count} | {pct:.1f}% | {min_target}-{max_target}% | {status} |")

    print("\n## Execution Times (Estimated)\n")
    print("| Test Set | Priority | Tests | Est. Time |")
    print("|----------|----------|-------|-----------|")

    p0_count = len(test_details["P0"])
    p1_count = len(test_details["P1"])
    p0_p1_count = p0_count + p1_count

    # Estimate: 2 seconds per unit test, 30 seconds per integration test (conservative)
    # Rough estimate: 60% unit (2s), 40% integration (30s) → avg ~13s per test
    avg_time_per_test = 13  # seconds

    print(f"| Smoke Tests | P0 only | {p0_count} | ~{p0_count * avg_time_per_test / 60:.0f} min |")
    print(
        f"| Pre-Merge | P0+P1 | {p0_p1_count} | ~{p0_p1_count * avg_time_per_test / 60:.0f} min |"
    )
    print(f"| Full Suite | All | {total} | ~{total * avg_time_per_test / 60:.0f} min |")

    print("\n## CI Cost Optimization\n")
    print("**Current CI workflow:**")
    print(f"- Full suite every commit: ~{total * avg_time_per_test / 60:.0f} min × 50 commits/day")
    print(f"- **Total CI time:** ~{total * avg_time_per_test / 60 * 50 / 60:.1f} hours/day\n")

    print("**With priority-based CI:**")
    print(f"- Pre-merge (P0+P1): ~{p0_p1_count * avg_time_per_test / 60:.0f} min × 50 commits/day")
    print(f"- **Total CI time:** ~{p0_p1_count * avg_time_per_test / 60 * 50 / 60:.1f} hours/day")

    reduction_pct = ((total - p0_p1_count) / total * 100) if total > 0 else 0
    print(f"- **Savings:** {reduction_pct:.0f}% reduction in CI time")

    print("\n## Priority Definitions\n")
    print("| Priority | Definition | Execution |")
    print("|----------|-----------|-----------|")
    print("| **P0** | Accuracy gates, security, data corruption prevention | Every commit |")
    print("| **P1** | Core features, common user workflows | Pre-merge |")
    print("| **P2** | Edge cases, integrations, performance optimizations | Nightly |")
    print("| **P3** | Nice-to-have, rare scenarios, performance benchmarks | Weekly |")

    print("\n## Test Commands\n")
    print("```bash")
    print("# Run P0 smoke tests (critical path only)")
    print("pytest tests/ -k 'priority and P0'")
    print()
    print("# Run P0+P1 pre-merge tests")
    print("pytest tests/ -k 'priority and (P0 or P1)'")
    print()
    print("# Run full test suite")
    print("pytest tests/")
    print("```")

    # Detailed breakdown by priority
    print("\n## Detailed Test Breakdown\n")
    for priority in ["P0", "P1", "P2", "P3"]:
        if test_details[priority]:
            print(f"### {priority} Tests ({len(test_details[priority])} tests)\n")
            # Group by file
            files = defaultdict(list)
            for test_detail in sorted(test_details[priority]):
                file_name = test_detail.split("::")[0]
                test_name = test_detail.split("::")[1] if "::" in test_detail else test_detail
                files[file_name].append(test_name)

            for file_name in sorted(files.keys()):
                print(f"**{file_name}** ({len(files[file_name])} tests)")
                for test_name in files[file_name][:5]:  # Show first 5 tests per file
                    print(f"  - {test_name}")
                if len(files[file_name]) > 5:
                    print(f"  - ... ({len(files[file_name]) - 5} more tests)")
                print()

    print("\n---\n")
    print("**Report generated by:** `scripts/analyze-test-priorities.py`")
    print("**Story:** 3-0-7 (Priority Classification System)")


if __name__ == "__main__":
    generate_priority_report()
