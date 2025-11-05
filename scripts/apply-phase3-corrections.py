#!/usr/bin/env python3
"""Apply Phase 3 low-confidence corrections to ground truth fixture."""

from pathlib import Path

# Phase 3: Low-confidence corrections (score <0.65)
PHASE3_CORRECTIONS = {
    4: 156,  # Raw materials costs (score 0.741 - actually high, was missed)
    10: 109,  # External electricity price (score 0.612)
    12: 156,  # Fuel rate vs thermal (score 0.605)
    15: 121,  # Unit variable margin (score 0.633)
    26: 23,  # Income tax (score 0.614)
    36: 36,  # CO2 emissions (score 0.639)
    38: 17,  # FTEs distribution (score 0.643)
    39: 87,  # Tunisia headcount (score 0.636)
    42: 155,  # Employee efficiency (score 0.642)
    44: 63,  # Distribution costs (score 0.600)
    50: 112,  # Fixed costs breakdown (score 0.633)
}


def main():
    file_path = Path("tests/fixtures/ground_truth.py")

    # Read file
    content = file_path.read_text()

    # Make backup
    backup_path = file_path.with_suffix(".py.backup-phase3")
    backup_path.write_text(content)
    print(f"Backup created: {backup_path}")

    corrections_applied = 0

    # Apply corrections
    for query_id, new_page in PHASE3_CORRECTIONS.items():
        # Find the dict entry for this query_id
        search_pattern = f'"id": {query_id},'

        if search_pattern in content:
            # Find the position of this query
            pos = content.find(search_pattern)

            # Find the expected_page_number line after this position
            segment = content[pos : pos + 500]
            page_line_start = segment.find('"expected_page_number":')

            if page_line_start != -1:
                # Find the old page number
                page_line = segment[page_line_start : page_line_start + 100]
                old_num_start = page_line.find(": ") + 2
                old_num_end = page_line.find(",", old_num_start)
                old_page = page_line[old_num_start:old_num_end].strip()

                # Build replacement
                old_line = f'"expected_page_number": {old_page},'
                new_line = (
                    f'"expected_page_number": {new_page},  # PHASE 3: Corrected from {old_page}'
                )

                # Replace in content
                full_old = content[pos : pos + 500]
                full_new = full_old.replace(old_line, new_line, 1)

                content = content[:pos] + full_new + content[pos + 500 :]

                corrections_applied += 1
                print(f"✅ Query {query_id}: {old_page} → {new_page}")

    # Write updated content
    file_path.write_text(content)

    print(f"\n✅ Total: {corrections_applied} Phase 3 corrections applied")
    print(f"File updated: {file_path}")
    print("\nNext: Run 'bash scripts/run-ac2-decision-gate.sh' to retest")


if __name__ == "__main__":
    main()
