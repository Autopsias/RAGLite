#!/usr/bin/env python3
"""Split ground_truth.py into category-based modules for better maintainability."""

import ast
from pathlib import Path

# File locations - use absolute paths
SOURCE_FILE = Path("tests/fixtures/ground_truth.py").resolve()
TARGET_DIR = Path("tests/fixtures/ground_truth").resolve()


def parse_source_file() -> dict[str, list[dict]]:
    """Parse the source file and extract all category question lists."""
    with open(SOURCE_FILE) as f:
        source = f.read()

    tree = ast.parse(source)

    categories = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.endswith("_QUESTIONS"):
                    # Extract category name
                    category_name = target.id.replace("_QUESTIONS", "").lower()
                    # Evaluate the list
                    questions = ast.literal_eval(node.value)
                    categories[category_name] = questions

    return categories


def create_category_file(category: str, questions: list) -> None:
    """Create a Python module for a specific category."""
    target_file = TARGET_DIR / f"{category}.py"

    # Count questions by difficulty
    easy = sum(1 for q in questions if q.get("difficulty") == "easy")
    medium = sum(1 for q in questions if q.get("difficulty") == "medium")
    hard = sum(1 for q in questions if q.get("difficulty") == "hard")

    # Create file content
    content = f'''"""
Ground Truth Questions - {category.replace("_", " ").title()} ({len(questions)} questions)

Difficulty Distribution:
- Easy: {easy}
- Medium: {medium}
- Hard: {hard}

Source: tests/fixtures/ground_truth.py (split for maintainability)
Last Updated: 2025-01-06
"""

from typing import TypedDict


class GroundTruthQuestion(TypedDict):
    """Type definition for ground truth question-answer pairs."""

    id: int
    question: str
    expected_answer: str
    expected_keywords: list[str]
    source_document: str
    expected_page_number: int
    expected_section: str
    category: str
    difficulty: str


# Category: {category} ({len(questions)} questions - {easy} easy, {medium} medium, {hard} hard)

{category.upper()}_QUESTIONS = [
'''

    # Add each question with proper formatting
    for i, question in enumerate(questions):
        if i > 0:
            content += "\n"

        content += "    {\n"

        # Order of fields for readability
        field_order = [
            "id",
            "question",
            "expected_answer",
            "expected_keywords",
            "source_document",
            "expected_page_number",
            "expected_section",
            "category",
            "difficulty",
        ]

        for field in field_order:
            value = question[field]

            if isinstance(value, str):
                # Escape quotes and backslashes
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                # Format multiline strings as triple-quoted if needed
                if "\n" in escaped_value:
                    content += f'        "{field}": """{escaped_value}""",\n'
                else:
                    content += f'        "{field}": "{escaped_value}",\n'
            elif isinstance(value, list):
                # Format list of keywords
                keywords_str = ", ".join(f'"{kw}"' for kw in value)
                content += f'        "{field}": [{keywords_str}],\n'
            else:
                content += f'        "{field}": {value},\n'

        # Close the question dict
        if i < len(questions) - 1:
            content += "    },\n"
        else:
            content += "    }\n"

    content += "]\n"

    # Write file
    target_file.write_text(content)
    try:
        rel_path = target_file.relative_to(Path.cwd())
    except ValueError:
        rel_path = target_file
    print(f"✓ Created {rel_path} ({len(questions)} questions, {target_file.stat().st_size} bytes)")


def create_init_file(categories: dict) -> None:
    """Create __init__.py to maintain backward compatibility."""
    target_file = TARGET_DIR / "__init__.py"

    # Build imports list
    category_imports = "\n".join(
        f"from tests.fixtures.ground_truth.{cat} import {cat.upper()}_QUESTIONS"
        for cat in sorted(categories.keys())
    )

    # Build concatenation list
    category_list = " +\n    ".join(f"{cat.upper()}_QUESTIONS" for cat in sorted(categories.keys()))

    content = f'''"""
Ground Truth Test Set - VALIDATED AGAINST ACTUAL PDF CONTENT

This module provides 50 validated question-answer pairs for testing RAG system accuracy.
All questions have been manually validated against the actual PDF content on 2025-10-14.

Usage:
    Import GROUND_TRUTH_QA for accuracy testing and validation:
    >>> from tests.fixtures.ground_truth import GROUND_TRUTH_QA
    >>> questions = GROUND_TRUTH_QA[:15]  # Select subset for testing

Source Document: 2025-08 Performance Review CONSO_v2.pdf (160 pages)
Validation Method: Systematic PDF reading and keyword verification
Categories: 6 (Cost Analysis, Margins, Financial Performance, Safety, Workforce, Operating Expenses)
Difficulty Levels: 3 (easy, medium, hard)

Last Updated: 2025-01-06
Split from: tests/fixtures/ground_truth.py (original 802 LOC file)
"""

from typing import TypedDict, cast

{category_imports}


class GroundTruthQuestion(TypedDict):
    """Type definition for ground truth question-answer pairs."""

    id: int
    question: str
    expected_answer: str
    expected_keywords: list[str]
    source_document: str
    expected_page_number: int
    expected_section: str
    category: str
    difficulty: str


# Combined ground truth QA set (50 questions total)
# Distribution:
# - Cost Analysis: 12 questions (5 easy, 5 medium, 2 hard)
# - Margins: 8 questions (3 easy, 4 medium, 1 hard)
# - Financial Performance: 10 questions (4 easy, 4 medium, 2 hard)
# - Safety Metrics: 6 questions (2 easy, 3 medium, 1 hard)
# - Workforce: 6 questions (2 easy, 3 medium, 1 hard)
# - Operating Expenses: 8 questions (3 easy, 4 medium, 1 hard)

GROUND_TRUTH_QA: list[GroundTruthQuestion] = cast(
    list[GroundTruthQuestion],
    {category_list},
)
'''

    target_file.write_text(content)
    try:
        rel_path = target_file.relative_to(Path.cwd())
    except ValueError:
        rel_path = target_file
    print(f"✓ Created {rel_path} (facade for backward compatibility)")


def update_original_file() -> None:
    """Update the original ground_truth.py to use the new modules."""
    # Keep minimal content for backward compatibility
    content = '''"""
Ground Truth Test Set - VALIDATED AGAINST ACTUAL PDF CONTENT

DEPRECATED: This file has been split into modules for better maintainability.
Please import from the ground_truth package instead:

    OLD: from tests.fixtures.ground_truth import GROUND_TRUTH_QA
    NEW: from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # Same import, new location

The actual data is now in:
    - tests/fixtures/ground_truth/cost_analysis.py
    - tests/fixtures/ground_truth/margins.py
    - tests/fixtures/ground_truth/financial_performance.py
    - tests/fixtures/ground_truth/safety_metrics.py
    - tests/fixtures/ground_truth/workforce.py
    - tests/fixtures/ground_truth/operating_expenses.py

Last Updated: 2025-01-06
"""

# Re-export from the new package location
from tests.fixtures.ground_truth import (  # noqa: F401
    GROUND_TRUTH_QA,
    GroundTruthQuestion,
)

# Maintain backward compatibility for direct category imports
from tests.fixtures.ground_truth import (  # noqa: F401
    COST_ANALYSIS_QUESTIONS,
    FINANCIAL_PERFORMANCE_QUESTIONS,
    MARGINS_QUESTIONS,
    OPERATING_EXPENSES_QUESTIONS,
    SAFETY_METRICS_QUESTIONS,
    WORKFORCE_QUESTIONS,
)
'''

    # Backup original first
    backup_file = SOURCE_FILE.with_suffix(".py.backup")
    if not backup_file.exists():
        backup_file.write_text(SOURCE_FILE.read_text())
        try:
            rel_path = backup_file.relative_to(Path.cwd())
        except ValueError:
            rel_path = backup_file
        print(f"✓ Backed up original to {rel_path}")

    SOURCE_FILE.write_text(content)
    try:
        rel_path = SOURCE_FILE.relative_to(Path.cwd())
    except ValueError:
        rel_path = SOURCE_FILE
    print(f"✓ Updated {rel_path} to use new modules ({SOURCE_FILE.stat().st_size} bytes)")


def main() -> None:
    """Main function to split ground_truth.py."""
    print("=" * 80)
    print("SPLITTING ground_truth.py INTO CATEGORY MODULES")
    print("=" * 80)
    print()

    # Create target directory
    TARGET_DIR.mkdir(exist_ok=True)

    # Parse source file
    print("Parsing source file...")
    categories = parse_source_file()
    print(f"Found {len(categories)} categories")
    print()

    # Process each category
    total_questions = 0
    for category, questions in sorted(categories.items()):
        print(f"Processing {category}...")
        create_category_file(category, questions)
        total_questions += len(questions)

    print()
    print(f"Total questions extracted: {total_questions}")

    # Create __init__.py
    print()
    create_init_file(categories)

    # Update original file
    print()
    update_original_file()

    print()
    print("=" * 80)
    print("✓ SPLIT COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Run tests to verify: uv run pytest tests/ -v -k ground_truth")
    print("2. If tests pass, commit the changes")
    print("3. Remove backup file: rm tests/fixtures/ground_truth.py.backup")


if __name__ == "__main__":
    main()
