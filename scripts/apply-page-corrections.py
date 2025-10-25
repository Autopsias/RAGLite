#!/usr/bin/env python3
"""
Apply page number corrections to ground truth file.

This script applies the validated page number corrections from Story 2.9 validation
to the tests/fixtures/ground_truth.py file, adding inline comments for traceability.

Usage:
    uv run python scripts/apply-page-corrections.py
"""

import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Corrections from validation (question_id -> new_page_number)
CORRECTIONS = {
    1: 20,  # cost_analysis
    2: 20,  # cost_analysis
    3: 33,  # cost_analysis
    4: 33,  # cost_analysis
    5: 33,  # cost_analysis
    8: 15,  # cost_analysis
    11: 20,  # cost_analysis
    14: 20,  # margins
    15: 33,  # margins
    16: 20,  # margins
    17: 20,  # margins
    19: 20,  # margins
    20: 20,  # margins
    24: 23,  # financial_performance
    29: 3,  # financial_performance
    30: 23,  # financial_performance
    31: 17,  # safety_metrics
    36: 15,  # safety_metrics
    38: 6,  # workforce
    39: 16,  # workforce
    40: 4,  # workforce
    41: 9,  # workforce
    42: 35,  # workforce
    43: 20,  # operating_expenses
    44: 33,  # operating_expenses
    45: 33,  # operating_expenses
    47: 35,  # operating_expenses
    50: 20,  # operating_expenses
}


def apply_corrections():
    """Apply page number corrections to ground truth file."""
    print("=" * 80)
    print("APPLYING PAGE NUMBER CORRECTIONS - Story 2.9 AC2")
    print("=" * 80)
    print()
    print(f"Applying {len(CORRECTIONS)} page number corrections...")
    print()

    ground_truth_path = project_root / "tests" / "fixtures" / "ground_truth.py"

    # Read the file
    with open(ground_truth_path) as f:
        content = f.read()

    # Track changes
    changes_made = []

    # Apply corrections
    for question_id, new_page in sorted(CORRECTIONS.items()):
        # Find the question dict in the file
        # Pattern: "id": <question_id>, ... "expected_page_number": <old_page>,
        pattern = rf'("id":\s*{question_id},[\s\S]*?"expected_page_number":\s*)(\d+)(,)'

        def replacement(match, q_id=question_id, new_pg=new_page):
            """Replacement function to add comment."""
            old_page = match.group(2)
            if int(old_page) == new_pg:
                # Already correct, skip
                return match.group(0)

            changes_made.append((q_id, int(old_page), new_pg))
            # Return updated line with comment
            return f"{match.group(1)}{new_pg}{match.group(3)}  # Updated Story 2.9: {old_page} → {new_pg}"

        # Apply replacement
        content, num_subs = re.subn(pattern, replacement, content)

        if num_subs == 0:
            print(f"  ⚠️  Warning: Could not find question {question_id} in file")
        elif num_subs > 1:
            print(f"  ⚠️  Warning: Multiple matches for question {question_id}")

    # Write back to file
    with open(ground_truth_path, "w") as f:
        f.write(content)

    # Summary
    print(f"\n✅ Applied {len(changes_made)} corrections")
    print()
    print("Changes made:")
    print("-" * 80)

    for q_id, old_page, new_page in changes_made:
        print(f"  Q{q_id:2d}: Page {old_page:3d} → {new_page:3d}")

    print()
    print(f"📝 File updated: {ground_truth_path}")
    print()
    print("Next steps:")
    print(
        '  1. Verify Python syntax: python -c "from tests.fixtures.ground_truth import GROUND_TRUTH_QA"'
    )
    print("  2. Spot-check corrections in the file")
    print("  3. Proceed to Story 2.9 AC3 (validation documentation)")
    print()

    return changes_made


if __name__ == "__main__":
    apply_corrections()
