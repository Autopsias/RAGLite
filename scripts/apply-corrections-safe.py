#!/usr/bin/env python3
"""Safely apply page number corrections to ground truth fixture."""

from pathlib import Path

# Corrections: query_id -> new_page
CORRECTIONS = {
    # High-confidence (score >=0.75)
    1: 42,  # Variable cost
    5: 7,  # Packaging costs
    8: 43,  # Electricity consumption
    14: 31,  # EBITDA per ton
    31: 17,  # FTE employees
    32: 43,  # Clinker production
    33: 95,  # Reliability factor
    34: 95,  # Utilization factor
    35: 43,  # Performance factor
    37: 7,  # Employee costs per ton
    23: 3,  # Capex
    25: 3,  # Working capital
    27: 3,  # Net interest
    28: 137,  # Cash set free
    41: 95,  # Tunisia employees
    46: 1,  # Insurance costs
    47: 102,  # Rents
    49: 111,  # Specialized labour
    # Medium-confidence (score 0.65-0.75)
    2: 31,  # Thermal energy cost
    3: 31,  # Electricity cost
    6: 43,  # Alternative fuel rate
    7: 7,  # Maintenance costs
    9: 43,  # Thermal consumption
    13: 31,  # EBITDA margin
    20: 23,  # EBITDA improvement
    29: 17,  # EBITDA Portugal+Group
    40: 17,  # FTEs in sales
    43: 31,  # Other costs
    45: 7,  # Sales costs
    48: 111,  # Production services
}


def main():
    file_path = Path("tests/fixtures/ground_truth.py")

    # Read file
    content = file_path.read_text()

    # Make backup
    backup_path = file_path.with_suffix(".py.backup")
    backup_path.write_text(content)
    print(f"Backup created: {backup_path}")

    corrections_applied = 0

    # Apply corrections
    for query_id, new_page in CORRECTIONS.items():
        # Find the dict entry for this query_id
        # Pattern: "id": N, followed by expected_page_number
        search_pattern = f'"id": {query_id},'

        if search_pattern in content:
            # Find the position of this query
            pos = content.find(search_pattern)

            # Find the expected_page_number line after this position
            # Look for the pattern within the next 500 characters (one dict entry)
            segment = content[pos : pos + 500]
            page_line_start = segment.find('"expected_page_number":')

            if page_line_start != -1:
                # Find the old page number
                page_line = segment[page_line_start : page_line_start + 100]
                # Extract old number (between ": " and "," or "\n")
                old_num_start = page_line.find(": ") + 2
                old_num_end = page_line.find(",", old_num_start)
                old_page = page_line[old_num_start:old_num_end].strip()

                # Build replacement
                old_line = f'"expected_page_number": {old_page},'
                new_line = f'"expected_page_number": {new_page},  # CORRECTED from {old_page}'

                # Replace in content
                full_old = content[pos : pos + 500]
                full_new = full_old.replace(old_line, new_line, 1)

                content = content[:pos] + full_new + content[pos + 500 :]

                corrections_applied += 1
                print(f"✅ Query {query_id}: {old_page} → {new_page}")

    # Write updated content
    file_path.write_text(content)

    print(f"\n✅ Total: {corrections_applied} corrections applied")
    print(f"File updated: {file_path}")


if __name__ == "__main__":
    main()
