#!/usr/bin/env python3
"""Refactor storage.py into modular package structure.

Story 8.2 Task 3: Automated extraction script.
"""

from pathlib import Path

# Read the full storage.py file
storage_file = Path("raglite/external_data/storage.py")
content = storage_file.read_text()

# Split into logical sections based on line numbers from story analysis
lines = content.splitlines(keepends=True)

# Extract imports and header (lines 1-58)
header_lines = lines[0:58]

# Core CRUD methods (lines 119-457)
core_start = 118  # 0-indexed
core_end = 457
core_lines = lines[core_start:core_end]

# Freshness tracking (lines 458-705)
freshness_start = 457
freshness_end = 705
freshness_lines = lines[freshness_start:freshness_end]

# Tier 2 storage (lines 706-974)
tier2_start = 705
tier2_end = 974
tier2_lines = lines[tier2_start:tier2_end]

# Model weights (lines 975-1290)
weights_start = 974
weights_end = 1290
weights_lines = lines[weights_start:weights_end]

# Model selection caching (lines 1291-1634)
selection_start = 1290
selection_lines = lines[selection_start:]

print(f"Total lines: {len(lines)}")
print(f"Core: {len(core_lines)} lines")
print(f"Freshness: {len(freshness_lines)} lines")
print(f"Tier2: {len(tier2_lines)} lines")
print(f"Weights: {len(weights_lines)} lines")
print(f"Selection: {len(selection_lines)} lines")
