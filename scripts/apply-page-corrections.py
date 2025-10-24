#!/usr/bin/env python3
"""Apply systematic page number corrections to ground truth fixture.

This script applies high-confidence page number corrections identified by
the Option B investigation and page mapping analysis.

Usage:
    python scripts/apply-page-corrections.py --phase 1  # High-confidence only
    python scripts/apply-page-corrections.py --phase 2  # + Medium-confidence
    python scripts/apply-page-corrections.py --phase 3  # + Low-confidence (manual review required)
"""

import argparse
import re
from pathlib import Path

# High-confidence corrections (score >=0.75)
HIGH_CONFIDENCE_CORRECTIONS = {
    5: (46, 7, 0.760, "Packaging costs"),
    8: (46, 43, 0.763, "Electricity consumption"),
    14: (46, 31, 0.725, "EBITDA per ton"),
    31: (46, 17, 0.858, "FTE employees"),
    32: (46, 43, 0.876, "Clinker production"),
    33: (46, 95, 0.772, "Reliability factor"),
    34: (46, 95, 0.812, "Utilization factor"),
    35: (46, 43, 0.798, "Performance factor"),
    37: (46, 7, 0.791, "Employee costs per ton"),
    23: (77, 3, 0.858, "Capex"),
    25: (77, 3, 0.773, "Working capital"),
    27: (77, 3, 0.844, "Net interest"),
    28: (77, 137, 0.835, "Cash set free"),
    41: (108, 95, 0.808, "Tunisia employees"),
    46: (46, 1, 0.830, "Insurance costs"),
    47: (46, 102, 0.781, "Rents"),
    49: (46, 111, 0.800, "Specialized labour"),
}

# Medium-confidence corrections (score 0.65-0.75)
MEDIUM_CONFIDENCE_CORRECTIONS = {
    1: (46, 42, 0.679, "Variable cost"),
    2: (46, 31, 0.710, "Thermal energy cost"),
    3: (46, 31, 0.726, "Electricity cost"),
    6: (46, 43, 0.684, "Alternative fuel rate"),
    7: (46, 7, 0.673, "Maintenance costs"),
    9: (46, 43, 0.659, "Thermal consumption"),
    13: (46, 31, 0.700, "EBITDA margin"),
    20: (46, 23, 0.718, "EBITDA improvement"),
    29: (77, 17, 0.691, "EBITDA Portugal+Group"),
    40: (46, 17, 0.705, "FTEs in sales"),
    43: (46, 31, 0.756, "Other costs"),
    45: (46, 7, 0.723, "Sales costs"),
    48: (46, 111, 0.662, "Production services"),
}

# Low-confidence corrections (score <0.65) - MANUAL REVIEW REQUIRED
LOW_CONFIDENCE_CORRECTIONS = {
    10: (46, 109, 0.612, "External electricity price"),
    12: (46, 156, 0.605, "Fuel rate vs thermal"),
    15: (46, 121, 0.633, "Unit variable margin"),
    26: (77, 23, 0.614, "Income tax"),
    36: (46, 36, 0.639, "CO2 emissions"),
    38: (46, 17, 0.643, "FTEs distribution"),
    39: (108, 87, 0.636, "Tunisia headcount"),
    42: (46, 155, 0.642, "Employee efficiency"),
    44: (46, 63, 0.600, "Distribution costs"),
    50: (46, 112, 0.633, "Fixed costs breakdown"),
}


def apply_corrections(ground_truth_path: Path, corrections: dict, phase_name: str) -> int:
    """Apply corrections to ground truth file.

    Args:
        ground_truth_path: Path to ground_truth.py file
        corrections: Dict of {query_id: (old_page, new_page, score, description)}
        phase_name: Name of correction phase for logging

    Returns:
        Number of corrections applied
    """
    content = ground_truth_path.read_text()
    corrections_applied = 0

    for query_id, (old_page, new_page, score, description) in corrections.items():
        # Find the question entry
        pattern = rf'"id":\s*{query_id},\n.*?"expected_page_number":\s*{old_page},'

        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            # Replace with corrected page and add comment
            replacement = (
                f'"id": {query_id},\n'
                f"        # CORRECTED ({phase_name}): Was {old_page} (headers/wrong section), "
                f"now {new_page} (actual data, score {score:.3f} - {description})\n"
                f'        "expected_page_number": {new_page},'
            )

            # Create the old string pattern more precisely
            old_pattern = f'"id": {query_id},\n(.*?)"expected_page_number": {old_page},'

            # Find and replace
            content = re.sub(
                old_pattern, replacement, content, count=1, flags=re.MULTILINE | re.DOTALL
            )

            corrections_applied += 1
            print(
                f"✅ Query {query_id}: {description} - Page {old_page} → {new_page} (score {score:.3f})"
            )
        else:
            print(f"⚠️  Query {query_id}: Pattern not found (already corrected or format changed)")

    # Write updated content
    ground_truth_path.write_text(content)
    return corrections_applied


def main():
    parser = argparse.ArgumentParser(description="Apply page number corrections to ground truth")
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Correction phase: 1=high-confidence only, 2=+medium, 3=+low (manual review)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be corrected without modifying file"
    )

    args = parser.parse_args()

    ground_truth_path = Path("tests/fixtures/ground_truth.py")

    if not ground_truth_path.exists():
        print(f"❌ ERROR: {ground_truth_path} not found")
        return 1

    print("=" * 80)
    print("GROUND TRUTH PAGE NUMBER CORRECTIONS")
    print("=" * 80)
    print()

    # Apply corrections based on phase
    total_corrections = 0

    if args.phase >= 1:
        print(
            f"Phase 1: Applying {len(HIGH_CONFIDENCE_CORRECTIONS)} high-confidence corrections (score >=0.75)"
        )
        print("-" * 80)
        if not args.dry_run:
            count = apply_corrections(ground_truth_path, HIGH_CONFIDENCE_CORRECTIONS, "Phase 1")
            total_corrections += count
            print(f"\n✅ Phase 1 complete: {count} corrections applied")
        else:
            print("DRY RUN - Would apply:")
            for qid, (old, new, score, desc) in HIGH_CONFIDENCE_CORRECTIONS.items():
                print(f"  Query {qid}: {desc} - {old} → {new} (score {score:.3f})")
        print()

    if args.phase >= 2:
        print(
            f"Phase 2: Applying {len(MEDIUM_CONFIDENCE_CORRECTIONS)} medium-confidence corrections (score 0.65-0.75)"
        )
        print("-" * 80)
        if not args.dry_run:
            count = apply_corrections(ground_truth_path, MEDIUM_CONFIDENCE_CORRECTIONS, "Phase 2")
            total_corrections += count
            print(f"\n✅ Phase 2 complete: {count} corrections applied")
        else:
            print("DRY RUN - Would apply:")
            for qid, (old, new, score, desc) in MEDIUM_CONFIDENCE_CORRECTIONS.items():
                print(f"  Query {qid}: {desc} - {old} → {new} (score {score:.3f})")
        print()

    if args.phase >= 3:
        print(
            f"Phase 3: Applying {len(LOW_CONFIDENCE_CORRECTIONS)} low-confidence corrections (score <0.65)"
        )
        print("⚠️  WARNING: These require manual PDF verification before final deployment")
        print("-" * 80)
        if not args.dry_run:
            count = apply_corrections(ground_truth_path, LOW_CONFIDENCE_CORRECTIONS, "Phase 3")
            total_corrections += count
            print(f"\n✅ Phase 3 complete: {count} corrections applied")
        else:
            print("DRY RUN - Would apply:")
            for qid, (old, new, score, desc) in LOW_CONFIDENCE_CORRECTIONS.items():
                print(f"  Query {qid}: {desc} - {old} → {new} (score {score:.3f})")
        print()

    if not args.dry_run:
        print("=" * 80)
        print(f"TOTAL: {total_corrections} corrections applied to {ground_truth_path}")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Run: bash scripts/run-ac2-decision-gate.sh")
        print("2. Review accuracy improvement")
        print("3. If <70%, apply next phase corrections")
    else:
        print("=" * 80)
        print("DRY RUN COMPLETE - No changes made")
        print("Run without --dry-run to apply corrections")
        print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
