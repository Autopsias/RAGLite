#!/usr/bin/env python3
"""Validate ground truth test set structure and distribution.

This script performs automated validation of the ground truth data structure
without requiring the actual PDF or running queries. It checks:

- Total question count (≥50)
- Required fields present in all questions
- Category distribution matches targets
- Difficulty distribution is 40/40/20
- No duplicate question IDs
- Page numbers are valid integers
- Expected keywords are non-empty

Usage:
    python scripts/validate_ground_truth.py

Exit codes:
    0: All validations passed
    1: One or more validations failed
"""

import sys
from pathlib import Path

# Add raglite package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


def validate_ground_truth() -> tuple[bool, list[str]]:
    """Validate ground truth test set structure and distribution.

    Returns:
        Tuple of (success: bool, errors: list[str])
    """
    errors = []

    # Expected distributions
    EXPECTED_TOTAL = 50
    EXPECTED_CATEGORIES = {
        "cost_analysis": 12,
        "margins": 8,
        "financial_performance": 10,
        "safety_metrics": 6,
        "workforce": 6,
        "operating_expenses": 8,
    }
    EXPECTED_DIFFICULTIES = {
        "easy": 20,
        "medium": 20,
        "hard": 10,
    }
    REQUIRED_FIELDS = [
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

    # Validation 1: Total count
    actual_total = len(GROUND_TRUTH_QA)
    if actual_total < EXPECTED_TOTAL:
        errors.append(f"✗ Total questions: Expected ≥{EXPECTED_TOTAL}, got {actual_total}")
    else:
        print(f"✓ Total questions: {actual_total} (target: {EXPECTED_TOTAL})")

    # Validation 2: Required fields
    missing_fields_count = 0
    for i, qa in enumerate(GROUND_TRUTH_QA, 1):
        missing = [field for field in REQUIRED_FIELDS if field not in qa]
        if missing:
            errors.append(f"✗ Question ID {qa.get('id', i)}: Missing fields {missing}")
            missing_fields_count += 1

    if missing_fields_count == 0:
        print(f"✓ Required fields: All {len(REQUIRED_FIELDS)} fields present in all questions")
    else:
        print(f"✗ Required fields: {missing_fields_count} questions missing fields")

    # Validation 3: Unique IDs
    ids = [qa["id"] for qa in GROUND_TRUTH_QA if "id" in qa]
    duplicate_ids = [id_ for id_ in ids if ids.count(id_) > 1]
    if duplicate_ids:
        errors.append(f"✗ Duplicate IDs found: {set(duplicate_ids)}")
    else:
        print(f"✓ Unique IDs: All {len(ids)} question IDs are unique")

    # Validation 4: Category distribution
    category_counts = {}
    for qa in GROUND_TRUTH_QA:
        cat = qa.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("\n📊 Category Distribution:")
    category_errors = []
    for cat, expected in EXPECTED_CATEGORIES.items():
        actual = category_counts.get(cat, 0)
        status = "✓" if actual == expected else "✗"
        print(f"  {status} {cat}: {actual}/{expected} questions")
        if actual != expected:
            category_errors.append(f"{cat}: expected {expected}, got {actual}")

    if category_errors:
        errors.append(f"✗ Category distribution mismatch: {', '.join(category_errors)}")

    # Validation 5: Difficulty distribution
    difficulty_counts = {}
    for qa in GROUND_TRUTH_QA:
        diff = qa.get("difficulty", "unknown")
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

    print("\n📊 Difficulty Distribution:")
    difficulty_errors = []
    for diff, expected in EXPECTED_DIFFICULTIES.items():
        actual = difficulty_counts.get(diff, 0)
        percentage = (actual / len(GROUND_TRUTH_QA) * 100) if GROUND_TRUTH_QA else 0
        target_pct = expected / EXPECTED_TOTAL * 100
        status = "✓" if actual == expected else "✗"
        print(
            f"  {status} {diff}: {actual}/{expected} ({percentage:.0f}%, target: {target_pct:.0f}%)"
        )
        if actual != expected:
            difficulty_errors.append(f"{diff}: expected {expected}, got {actual}")

    if difficulty_errors:
        errors.append(f"✗ Difficulty distribution mismatch: {', '.join(difficulty_errors)}")

    # Validation 6: Page numbers are valid integers
    invalid_pages = []
    for qa in GROUND_TRUTH_QA:
        page = qa.get("expected_page_number")
        if not isinstance(page, int) or page < 1:
            invalid_pages.append(f"ID {qa.get('id')}: {page}")

    if invalid_pages:
        errors.append(f"✗ Invalid page numbers: {', '.join(invalid_pages[:5])}...")
    else:
        print(f"\n✓ Page numbers: All {len(GROUND_TRUTH_QA)} are valid integers")

    # Validation 7: Expected keywords are non-empty
    empty_keywords = []
    for qa in GROUND_TRUTH_QA:
        keywords = qa.get("expected_keywords", [])
        if not keywords or not isinstance(keywords, list):
            empty_keywords.append(f"ID {qa.get('id')}")

    if empty_keywords:
        errors.append(f"✗ Empty keywords: {', '.join(empty_keywords[:5])}...")
    else:
        print("✓ Expected keywords: All questions have non-empty keyword lists")

    # Validation 8: Source document consistency
    source_docs = {qa.get("source_document") for qa in GROUND_TRUTH_QA}
    print(f"\n✓ Source documents: {len(source_docs)} unique document(s)")
    for doc in source_docs:
        count = sum(1 for qa in GROUND_TRUTH_QA if qa.get("source_document") == doc)
        print(f"  - {doc}: {count} questions")

    return len(errors) == 0, errors


def main():
    """Run validation and report results."""
    print("=" * 80)
    print("GROUND TRUTH TEST SET VALIDATION")
    print("=" * 80)
    print()

    success, errors = validate_ground_truth()

    if success:
        print("\n" + "=" * 80)
        print("✅ ALL VALIDATIONS PASSED")
        print("=" * 80)
        print("\nThe ground truth test set structure is valid and ready for use.")
        print("Next steps:")
        print("  1. Manual PDF validation (see docs/qa/assessments/1.12A-validation-checklist.md)")
        print("  2. Import test: pytest raglite/tests/test_ground_truth.py")
        print("  3. Integration: Use in scripts/run-accuracy-tests.py (Story 1.12B)")
        return 0
    else:
        print("\n" + "=" * 80)
        print("❌ VALIDATION FAILURES")
        print("=" * 80)
        for error in errors:
            print(f"  {error}")
        print("\nPlease fix the errors above and run validation again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
