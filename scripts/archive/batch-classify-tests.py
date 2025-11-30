#!/usr/bin/env python3
"""Batch classify unclassified tests with AI-assisted priority assignment.

Story 3-0-7: Priority Classification System
Analyzes test functions and assigns P0/P1/P2/P3 priorities based on:
- Test purpose (from docstring)
- Test type (unit/integration/e2e)
- Story context
- Classification decision tree
"""

import re
from pathlib import Path

# Priority classification decision tree
CLASSIFICATION_RULES = {
    "P0": [
        "ground_truth",
        "accuracy",
        "security",
        "sql_injection",
        "data_corruption",
        "epic.*completion",
        "gate",
        "baseline",
        "regression.*floor",
    ],
    "P1": [
        "core",
        "hybrid_search",
        "query_classification",
        "mcp_server",
        "ingestion",
        "retrieval",
        "embedding",
        "search.*integration",
    ],
    "P2": [
        "edge_case",
        "fuzzy",
        "transposed",
        "metadata",
        "optimization",
        "performance",
        "multi_entity",
    ],
    "P3": [
        "period_normalizer",
        "rare",
        "benchmark",
        "malformed",
    ],
}


def extract_test_functions(file_path: Path) -> list[dict]:
    """Extract all test functions from a file with context."""
    content = file_path.read_text()

    # Find all test functions with their decorators and docstrings
    pattern = r'(@pytest\.mark\.\w+.*?\n)*\s*(async\s+)?def\s+(test_\w+)\s*\([^)]*\)[^:]*:\s*"""([^"]*?)"""'

    tests = []
    for match in re.finditer(pattern, content, re.DOTALL | re.MULTILINE):
        decorators = match.group(1) or ""
        is_async = match.group(2) is not None
        test_name = match.group(3)
        docstring = match.group(4).strip()

        # Check if already has priority
        has_priority = "@pytest.mark.priority" in decorators

        # Get test ID if present
        test_id_match = re.search(r'@pytest\.mark\.test_id\("([^"]+)"\)', decorators)
        test_id = test_id_match.group(1) if test_id_match else None

        # Get story number from test ID
        story = None
        if test_id:
            story_match = re.match(r"(\d+\.\d+)", test_id)
            story = story_match.group(1) if story_match else None

        tests.append(
            {
                "name": test_name,
                "file": file_path,
                "has_priority": has_priority,
                "test_id": test_id,
                "story": story,
                "docstring": docstring,
                "is_async": is_async,
                "decorators": decorators,
            }
        )

    return tests


def classify_test(test: dict) -> str:
    """Classify a test based on rules and context."""
    name = test["name"].lower()
    docstring = test["docstring"].lower()
    test_id = test["test_id"] or ""

    # Combine all context for matching
    context = f"{name} {docstring} {test_id}"

    # Check P0 rules first (highest priority)
    for keyword in CLASSIFICATION_RULES["P0"]:
        if re.search(keyword, context, re.IGNORECASE):
            return "P0"

    # Check P1 rules
    for keyword in CLASSIFICATION_RULES["P1"]:
        if re.search(keyword, context, re.IGNORECASE):
            return "P1"

    # Check P2 rules
    for keyword in CLASSIFICATION_RULES["P2"]:
        if re.search(keyword, context, re.IGNORECASE):
            return "P2"

    # Check P3 rules
    for keyword in CLASSIFICATION_RULES["P3"]:
        if re.search(keyword, context, re.IGNORECASE):
            return "P3"

    # Default classification by test type
    if "integration" in str(test["file"]):
        return "P1"  # Integration tests are typically core features
    elif "e2e" in str(test["file"]):
        return "P0"  # E2E tests are critical path
    else:
        return "P2"  # Unit tests default to P2 (edge cases)


def analyze_all_tests() -> tuple[list[dict], list[dict]]:
    """Analyze all test files and return classified/unclassified tests."""
    test_dir = Path("tests")
    test_files = list(test_dir.rglob("test_*.py"))

    classified = []
    unclassified = []

    for test_file in test_files:
        if ".bak" in str(test_file) or "__pycache__" in str(test_file):
            continue

        tests = extract_test_functions(test_file)

        for test in tests:
            if test["has_priority"]:
                classified.append(test)
            else:
                # Auto-classify
                priority = classify_test(test)
                test["recommended_priority"] = priority
                unclassified.append(test)

    return classified, unclassified


def generate_classification_report(classified: list[dict], unclassified: list[dict]):
    """Generate a report showing classification results."""
    print("# Batch Test Classification Report")
    print()
    print(f"**Total Tests:** {len(classified) + len(unclassified)}")
    print(f"**Already Classified:** {len(classified)}")
    print(f"**Unclassified:** {len(unclassified)}")
    print()

    if not unclassified:
        print("✅ All tests are classified!")
        return

    # Group unclassified by recommended priority
    by_priority = {"P0": [], "P1": [], "P2": [], "P3": []}
    for test in unclassified:
        priority = test["recommended_priority"]
        by_priority[priority].append(test)

    print("## Recommended Classifications")
    print()

    for priority in ["P0", "P1", "P2", "P3"]:
        tests = by_priority[priority]
        if not tests:
            continue

        print(f"### {priority} - {len(tests)} tests")
        print()

        # Group by file
        by_file = {}
        for test in tests:
            file_name = test["file"].name
            if file_name not in by_file:
                by_file[file_name] = []
            by_file[file_name].append(test)

        for file_name in sorted(by_file.keys()):
            file_tests = by_file[file_name]
            print(f"**{file_name}** ({len(file_tests)} tests)")
            for test in file_tests:
                test_id = test["test_id"] or "NO-ID"
                print(f"  - `{test['name']}` (ID: {test_id})")
            print()

    # Summary by file
    print("## Files Requiring Updates")
    print()

    files_to_update = {}
    for test in unclassified:
        file_path = test["file"]
        if file_path not in files_to_update:
            files_to_update[file_path] = []
        files_to_update[file_path].append(test)

    for file_path in sorted(files_to_update.keys()):
        tests = files_to_update[file_path]
        print(f"- `{file_path.relative_to('tests')}`: {len(tests)} tests")

    print()
    print(f"**Total Files:** {len(files_to_update)}")


if __name__ == "__main__":
    print("Analyzing tests...")
    classified, unclassified = analyze_all_tests()
    generate_classification_report(classified, unclassified)
