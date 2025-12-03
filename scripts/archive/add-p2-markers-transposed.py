#!/usr/bin/env python3
"""Add P2 priority markers to transposed table extraction tests."""

import re

# Read the file
with open("tests/unit/test_transposed_table_extraction.py") as f:
    content = f.read()

# Define test replacements
replacements = [
    (
        "2.13-UNIT-004",
        "insufficient_metrics_threshold",
        "Edge case: insufficient metrics ratio test",
    ),
    ("2.13-UNIT-005", "insufficient_rows", "Edge case: insufficient rows test"),
    (
        "2.13-UNIT-006",
        "single_header_transposed",
        "Advanced feature: transposed table extraction",
    ),
    (
        "2.13-UNIT-007",
        "multi_header_transposed",
        "Advanced feature: multi-header transposed extraction",
    ),
    ("2.13-UNIT-008", "handles_empty_cells", "Edge case: empty cell handling"),
    ("2.13-UNIT-009", "metric_parsing", "Advanced feature: metric parsing"),
    (
        "2.13-UNIT-010",
        "column_name_generation",
        "Advanced feature: column name generation",
    ),
    ("2.13-UNIT-011", "metadata_fields", "Advanced feature: metadata extraction"),
]

for test_id, _test_name, justification in replacements:
    # Find the test pattern
    pattern = rf'(@pytest\.mark\.test_id\("{test_id}"\)\n)(    def test_.*?\(.*?\):\n        """.*?\n    \n        Test ID: {test_id}\n        Story: 2.13 \(Story Name TBD\)\n        Priority: )(TBD \(Story 3-0-7\))'

    replacement = rf'\1    @pytest.mark.priority("P2")\n\2P2 (Medium) - {justification}'

    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write the file back
with open("tests/unit/test_transposed_table_extraction.py", "w") as f:
    f.write(content)

print("Updated transposed table extraction tests with P2 markers")
