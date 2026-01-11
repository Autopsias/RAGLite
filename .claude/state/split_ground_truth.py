#!/usr/bin/env python3
"""Split ground_truth.py into category-based modules for better maintainability."""

import re
from pathlib import Path

# File locations
SOURCE_FILE = Path("tests/fixtures/ground_truth.py")
TARGET_DIR = Path("tests/fixtures/ground_truth")

# Category ranges based on grep analysis
# Line numbers from grep output
CATEGORIES = {
    "cost_analysis": (64, 233),
    "margins": (234, 368),
    "financial_performance": (369, 520),
    "safety_metrics": (521, 599),
    "workforce": (600, 688),
    "operating_expenses": (689, 793),
}


def extract_category_questions(category: str, start_line: int, end_line: int) -> list[dict]:
    """Extract questions for a specific category from the source file."""
    with open(SOURCE_FILE) as f:
        lines = f.readlines()

    # Extract the category section (adjust for 0-indexing)
    category_lines = lines[start_line - 1 : end_line]

    # Join and parse the list
    content = "".join(category_lines)

    # Extract the list using regex
    match = re.search(rf"{category.upper()}_QUESTIONS\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find {category.upper()}_QUESTIONS list")

    # Evaluate the list literal safely
    questions_str = f"[{match.group(1)}]"
    questions: list[dict] = eval(questions_str)

    return questions


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

    # Add each question with proper indentation
    for i, question in enumerate(questions):
        if i == 0:
            content += "    {\n"
        else:
            content += "\n    {\n"

        for key, value in question.items():
            if isinstance(value, str):
                # Escape quotes in strings
                value = value.replace('"', '\\"')
                content += f'        "{key}": "{value}",\n'
            elif isinstance(value, list):
                # Format list of keywords
                keywords = ", ".join(f'"{kw}"' for kw in value)
                content += f'        "{key}": [{keywords}],\n'
            else:
                content += f'        "{key}": {value},\n'

        if i < len(questions) - 1:
            content += "    },"
        else:
            content += "    }"

    content += "\n]\n"

    # Write file
    target_file.write_text(content)
    print(f"Created {target_file} ({len(questions)} questions, {target_file.stat().st_size} bytes)")


def create_init_file() -> None:
    """Create __init__.py to maintain backward compatibility."""
    target_file = TARGET_DIR / "__init__.py"

    content = '''"""
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

from tests.fixtures.ground_truth.cost_analysis import COST_ANALYSIS_QUESTIONS
from tests.fixtures.ground_truth.financial_performance import (
    FINANCIAL_PERFORMANCE_QUESTIONS,
)
from tests.fixtures.ground_truth.margins import MARGINS_QUESTIONS
from tests.fixtures.ground_truth.operating_expenses import OPERATING_EXPENSES_QUESTIONS
from tests.fixtures.ground_truth.safety_metrics import SAFETY_METRICS_QUESTIONS
from tests.fixtures.ground_truth.workforce import WORKFORCE_QUESTIONS


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
    COST_ANALYSIS_QUESTIONS
    + MARGINS_QUESTIONS
    + FINANCIAL_PERFORMANCE_QUESTIONS
    + SAFETY_METRICS_QUESTIONS
    + WORKFORCE_QUESTIONS
    + OPERATING_EXPENSES_QUESTIONS,
)
'''

    target_file.write_text(content)
    print(f"Created {target_file} (facade for backward compatibility)")


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
        print(f"Backed up original to {backup_file}")

    SOURCE_FILE.write_text(content)
    print(f"Updated {SOURCE_FILE} to use new modules")


def main() -> None:
    """Main function to split ground_truth.py."""
    print("=" * 80)
    print("SPLITTING ground_truth.py INTO CATEGORY MODULES")
    print("=" * 80)
    print()

    # Create target directory
    TARGET_DIR.mkdir(exist_ok=True)

    # Process each category
    all_questions = []
    for category, (start, end) in CATEGORIES.items():
        print(f"Processing {category}...")
        questions = extract_category_questions(category, start, end)
        create_category_file(category, questions)
        all_questions.extend(questions)

    print()
    print(f"Total questions extracted: {len(all_questions)}")

    # Create __init__.py
    print()
    create_init_file()

    # Update original file
    print()
    update_original_file()

    print()
    print("=" * 80)
    print("SPLIT COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Run tests to verify: uv run pytest tests/ -v")
    print("2. If tests pass, commit the changes")
    print("3. Remove backup file: rm tests/fixtures/ground_truth.py.backup")


if __name__ == "__main__":
    main()
