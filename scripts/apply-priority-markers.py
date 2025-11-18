#!/usr/bin/env python3
"""Apply priority markers to unclassified tests automatically.

Story 3-0-7: Priority Classification System
Adds @pytest.mark.priority() decorators to test functions.
"""

import re
import sys
from pathlib import Path

# Classification rules (copied from batch-classify-tests.py)
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

PRIORITY_DEFINITIONS = {
    "P0": "Critical",
    "P1": "High",
    "P2": "Medium",
    "P3": "Low",
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

        tests.append(
            {
                "name": test_name,
                "file": file_path,
                "has_priority": has_priority,
                "test_id": test_id,
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


def analyze_all_tests():
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


def add_priority_marker(
    file_path: Path, test_name: str, priority: str, test_id: str = None
) -> bool:
    """Add priority marker to a specific test function."""
    content = file_path.read_text()

    # Find the test function
    # Pattern: Match test function with optional existing decorators and docstring
    pattern = rf'((?:@pytest\.mark\.\w+.*?\n)*)\s*(async\s+)?def\s+{re.escape(test_name)}\s*\([^)]*\)[^:]*:\s*"""([^"]*?)"""'

    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"  ⚠️  Could not find test function: {test_name}")
        return False

    decorators = match.group(1) or ""
    is_async = match.group(2) or ""
    docstring = match.group(3).strip()

    # Check if already has priority
    if "@pytest.mark.priority" in decorators:
        print(f"  ⏭️  {test_name}: Already has priority")
        return False

    # Build new decorators with priority marker
    # Insert priority marker after test_id if present, otherwise at the beginning
    if "@pytest.mark.test_id" in decorators:
        # Add after test_id
        new_decorators = decorators.rstrip() + f'\n@pytest.mark.priority("{priority}")\n'
    else:
        # Add as first decorator
        new_decorators = f'@pytest.mark.priority("{priority}")\n' + decorators

    # Update docstring with priority info if not already present
    priority_label = PRIORITY_DEFINITIONS[priority]
    if "Priority:" not in docstring:
        # Add priority to docstring (after Story line if present, otherwise at end)
        docstring_lines = docstring.split("\n")

        # Find where to insert (after Story line or after first line)
        insert_idx = 1  # After brief description
        for i, line in enumerate(docstring_lines):
            if "Story:" in line:
                insert_idx = i + 1
                break

        # Insert priority line
        priority_line = f"    Priority: {priority} ({priority_label})"
        docstring_lines.insert(insert_idx, priority_line)
        new_docstring = "\n".join(docstring_lines)
    else:
        new_docstring = docstring

    # Build replacement
    replacement = f'{new_decorators}{is_async}def {test_name}({match.group(0).split("(", 1)[1].split(")", 1)[0]}):\n    """{new_docstring}"""'

    # Replace in content
    new_content = content.replace(match.group(0), replacement)

    # Write back
    file_path.write_text(new_content)

    print(f"  ✅ {test_name}: Added {priority} ({priority_label})")
    return True


def apply_all_priorities():
    """Apply priority markers to all unclassified tests."""
    print("Analyzing tests...")
    classified, unclassified = analyze_all_tests()

    print(f"\nFound {len(unclassified)} tests to classify\n")

    if not unclassified:
        print("✅ All tests already classified!")
        return

    # Group by file for efficient processing
    by_file = {}
    for test in unclassified:
        file_path = test["file"]
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(test)

    total_added = 0
    failed = 0

    # Process each file
    for file_path in sorted(by_file.keys()):
        tests = by_file[file_path]
        print(f"\n📄 {file_path.relative_to('tests')} ({len(tests)} tests)")

        for test in tests:
            priority = test["recommended_priority"]
            success = add_priority_marker(file_path, test["name"], priority, test.get("test_id"))
            if success:
                total_added += 1
            else:
                failed += 1

    print(f"\n{'=' * 60}")
    print(f"✅ Added priority markers to {total_added} tests")
    if failed > 0:
        print(f"⚠️  Failed to process {failed} tests")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    import sys

    # Confirm before proceeding
    print("=" * 60)
    print("BATCH PRIORITY MARKER APPLICATION")
    print("=" * 60)
    print("\nThis will add @pytest.mark.priority() decorators to")
    print("all unclassified tests based on automated analysis.")
    print()

    response = input("Proceed? [y/N]: ")
    if response.lower() != "y":
        print("Aborted.")
        sys.exit(0)

    apply_all_priorities()
