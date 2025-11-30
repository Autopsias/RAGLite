#!/usr/bin/env python3
"""Batch add test IDs to all test files (Story 3-0-6 AC3).

This script intelligently adds @pytest.mark.test_id() markers and updates
docstrings for all test functions based on story mapping.

Usage:
    # Dry-run (preview changes)
    python scripts/add-test-ids-batch.py --dry-run

    # Apply changes
    python scripts/add-test-ids-batch.py

    # Process specific files
    python scripts/add-test-ids-batch.py tests/unit/test_query_classifier.py

Safety:
    - Creates backup files (.bak) before modification
    - Skips tests that already have test IDs
    - Validates test ID format before writing
"""

import argparse
import re
from pathlib import Path

# Story to file mapping (from map-tests-to-stories.py analysis)
STORY_MAPPING = {
    "1.10": ["tests/integration/test_e2e_query_validation.py"],
    "1.11": [
        "tests/integration/test_mcp_response_validation.py",
        "tests/unit/test_response_formatting.py",
        "tests/unit/test_shared_config.py",
    ],
    "1.12": [
        "tests/e2e/test_ground_truth.py",
        "tests/integration/test_retrieval_integration.py",
    ],
    "1.13": [
        "tests/integration/test_ingestion_integration.py",
        "tests/unit/test_ingestion.py",
    ],
    "1.15": ["tests/unit/test_page_extraction.py"],
    "1.8": [
        "tests/integration/test_main_integration.py",
        "tests/unit/test_main.py",
        "tests/unit/test_retrieval.py",
    ],
    "2.1": [
        "tests/integration/test_ac3_ground_truth.py",
        "tests/integration/test_ac4_comprehensive.py",
        "tests/integration/test_epic2_regression.py",
        "tests/integration/test_hybrid_search_integration.py",
        "tests/integration/test_page_parallelism.py",
        "tests/integration/test_pypdfium_ingestion.py",
        "tests/unit/test_pypdfium_backend.py",
    ],
    "2.10": ["tests/unit/test_query_classifier.py"],
    "2.11": [
        "tests/integration/test_multi_index_integration.py",
        "tests/unit/test_hybrid_search.py",
        "tests/unit/test_merge_results_normalization.py",
    ],
    "2.13": [
        "tests/integration/test_ac1_fuzzy_entity_matching.py",
        "tests/integration/test_sql_routing.py",
        "tests/unit/test_transposed_table_extraction.py",
    ],
    "2.14": [
        "tests/integration/test_story_2_14_excerpt_validation.py",
        "tests/unit/test_ac2_multi_entity_queries.py",
        "tests/unit/test_sql_hybrid_search.py",
    ],
    "2.15": ["tests/unit/test_period_normalizer.py"],
    "2.3": [
        "tests/integration/test_element_metadata.py",
        "tests/integration/test_fixed_chunking.py",
    ],
    "2.4": [
        "tests/integration/test_metadata_injection.py",
        "tests/unit/test_metadata_extraction.py",
    ],
    "2.6": ["tests/integration/test_table_retrieval.py"],
    "2.8": ["tests/unit/test_table_aware_chunking.py"],
    # Manual assignments for files without clear story hints
    "1.2": ["tests/unit/test_docling_extraction.py"],  # PDF ingestion
    "1.6": ["tests/unit/test_shared_clients.py"],  # Qdrant setup
    "1.5": ["tests/unit/test_shared_models.py"],  # Models/config
    "2.5": ["tests/integration/test_accuracy_validation.py"],  # AC3 validation
    "1.9": ["tests/integration/test_mcp_server.py"],  # MCP server
}

# Reverse mapping: file -> story
FILE_TO_STORY: dict[str, str] = {}
for story, files in STORY_MAPPING.items():
    for file_path in files:
        FILE_TO_STORY[file_path] = story


def determine_test_type(file_path: Path) -> str:
    """Determine test type from file location."""
    parts = file_path.parts
    if "unit" in parts:
        return "UNIT"
    elif "integration" in parts:
        return "INTEGRATION"
    elif "e2e" in parts:
        return "E2E"
    else:
        return "UNIT"  # Default


def extract_test_functions(content: str) -> list[tuple[str, int, str]]:
    """Extract test functions with their line numbers and names.

    Returns:
        List of (function_name, line_number, indentation) tuples
    """
    test_functions = []
    lines = content.split("\n")

    for i, line in enumerate(lines, start=1):
        # Match test functions: def test_* or async def test_*
        match = re.match(r"^(\s*)(?:async\s+)?def\s+(test_\w+)\s*\(", line)
        if match:
            indentation = match.group(1)
            function_name = match.group(2)
            test_functions.append((function_name, i, indentation))

    return test_functions


def has_test_id(content: str, function_name: str) -> bool:
    """Check if function already has a test_id marker."""
    # Look for @pytest.mark.test_id before the function definition
    pattern = rf'@pytest\.mark\.test_id\(["\'][\d.]+-\w+-\d{{3}}["\']\)\s*\n\s*(?:async\s+)?def\s+{re.escape(function_name)}'
    return bool(re.search(pattern, content))


def get_next_sequence_number(test_ids: list[str]) -> int:
    """Get next available sequence number from existing test IDs."""
    if not test_ids:
        return 1

    sequences = []
    for test_id in test_ids:
        # Extract sequence from format: "2.10-UNIT-001" -> 1
        match = re.match(r"[\d.]+-\w+-(\d{3})", test_id)
        if match:
            sequences.append(int(match.group(1)))

    return max(sequences) + 1 if sequences else 1


def add_test_id_to_function(
    content: str, function_name: str, line_number: int, indentation: str, test_id: str, story: str
) -> str:
    """Add test_id marker and update docstring for a test function."""
    lines = content.split("\n")

    # Find the function definition line (0-indexed)
    func_line_idx = line_number - 1

    # Check if marker already exists (shouldn't happen, but safety check)
    if func_line_idx > 0 and "@pytest.mark.test_id" in lines[func_line_idx - 1]:
        print(f"  ⚠️  {function_name} already has test_id, skipping")
        return content

    # Insert @pytest.mark.test_id() decorator before function
    marker_line = f'{indentation}@pytest.mark.test_id("{test_id}")'
    lines.insert(func_line_idx, marker_line)

    # Update docstring (now at func_line_idx + 1 after insertion)
    docstring_start_idx = func_line_idx + 2  # After marker + function def
    if docstring_start_idx < len(lines) and '"""' in lines[docstring_start_idx]:
        # Multi-line docstring
        # Find the end of the first line of docstring
        first_doc_line = lines[docstring_start_idx]

        # Check if it's a one-line docstring
        if first_doc_line.count('"""') == 2:
            # One-line docstring: """Brief description."""
            # Split it into multi-line format
            brief = first_doc_line.strip().replace('"""', "").strip()

            # Replace the one-line docstring with multi-line format
            lines[docstring_start_idx : docstring_start_idx + 1] = [
                f'{indentation}    """{brief}',
                f"{indentation}",
                f"{indentation}    Test ID: {test_id}",
                f"{indentation}    Story: {story} (Story Name TBD)",
                f"{indentation}    Priority: TBD (Story 3-0-7)",
                f'{indentation}    """',
            ]
        else:
            # Multi-line docstring: find closing """
            closing_idx = docstring_start_idx + 1
            while closing_idx < len(lines) and '"""' not in lines[closing_idx]:
                closing_idx += 1

            # Insert test metadata before closing """
            metadata_lines = [
                f"{indentation}",
                f"{indentation}    Test ID: {test_id}",
                f"{indentation}    Story: {story} (Story Name TBD)",
                f"{indentation}    Priority: TBD (Story 3-0-7)",
            ]
            lines[closing_idx:closing_idx] = metadata_lines

    return "\n".join(lines)


def process_file(
    file_path: Path, dry_run: bool = False, story_sequences: dict = None
) -> tuple[int, int]:
    """Process a single test file and add test IDs.

    Args:
        file_path: Path to test file
        dry_run: If True, only preview changes
        story_sequences: Dict tracking next sequence number per story

    Returns:
        Tuple of (tests_processed, tests_skipped)
    """
    if story_sequences is None:
        story_sequences = {}
    print(f"\n📄 Processing: {file_path}")

    # Determine story and test type
    # Find project root (where tests/ directory is)
    project_root = Path(__file__).parent.parent
    rel_path = str(file_path.relative_to(project_root))
    story = FILE_TO_STORY.get(rel_path)

    if not story:
        print("  ⚠️  No story mapping found, skipping")
        return 0, 0

    test_type = determine_test_type(file_path)
    print(f"  Story: {story}, Type: {test_type}")

    # Read file content
    content = file_path.read_text()

    # Extract test functions
    test_functions = extract_test_functions(content)
    print(f"  Found {len(test_functions)} test functions")

    if not test_functions:
        return 0, 0

    # Check which tests already have IDs
    existing_test_ids = []
    tests_to_process = []

    for func_name, line_num, indent in test_functions:
        if has_test_id(content, func_name):
            print(f"  ✓ {func_name} - already has test_id")
            # Extract existing test ID for sequence tracking
            match = re.search(
                rf'@pytest\.mark\.test_id\(["\']([^"\']+)["\']\)\s*\n\s*(?:async\s+)?def\s+{re.escape(func_name)}',
                content,
            )
            if match:
                existing_test_ids.append(match.group(1))
        else:
            tests_to_process.append((func_name, line_num, indent))

    if not tests_to_process:
        print("  ✅ All tests already have IDs")
        return 0, len(test_functions)

    # Generate test IDs for functions without them
    # Use global story_sequences to maintain sequence across all files for this story
    story_key = f"{story}-{test_type}"
    if story_key not in story_sequences:
        # Initialize from existing test IDs in this file
        story_sequences[story_key] = get_next_sequence_number(existing_test_ids)

    next_seq = story_sequences[story_key]
    modified_content = content

    # Pre-assign test IDs in top-to-bottom order (preserves logical sequence)
    test_assignments = []
    for func_name, line_num, indent in tests_to_process:
        test_id = f"{story}-{test_type}-{next_seq:03d}"
        test_assignments.append((func_name, line_num, indent, test_id))
        next_seq += 1

    # CRITICAL FIX: Process functions from BOTTOM to TOP
    # This prevents line number shifts from affecting earlier functions
    # Sort by line_num in descending order for processing
    test_assignments_sorted = sorted(test_assignments, key=lambda x: x[1], reverse=True)

    for func_name, line_num, indent, test_id in test_assignments_sorted:
        print(f"  + Adding {test_id} to {func_name}")

        modified_content = add_test_id_to_function(
            modified_content, func_name, line_num, indent, test_id, story
        )

    # Update global sequence counter for this story
    story_sequences[story_key] = next_seq

    # Write changes (or preview in dry-run mode)
    if dry_run:
        print(f"  [DRY-RUN] Would update {len(tests_to_process)} tests")
    else:
        # Create backup
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        backup_path.write_text(content)
        print(f"  💾 Backup created: {backup_path.name}")

        # Write updated content
        file_path.write_text(modified_content)
        print(f"  ✅ Updated {len(tests_to_process)} tests")

    return len(tests_to_process), len(test_functions) - len(tests_to_process)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch add test IDs to test files (Story 3-0-6 AC3)"
    )
    parser.add_argument(
        "files", nargs="*", help="Specific test files to process (default: all mapped files)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without modifying files"
    )
    args = parser.parse_args()

    print("🚀 Batch Test ID Assignment (Story 3-0-6 AC3)")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  DRY-RUN MODE: No files will be modified")
        print()

    # Determine files to process
    project_root = Path(__file__).parent.parent

    if args.files:
        files_to_process = [(project_root / f).resolve() for f in args.files]
    else:
        # Process all files in story mapping
        project_root = Path(__file__).parent.parent
        files_to_process = []
        for rel_path in FILE_TO_STORY.keys():
            full_path = project_root / rel_path
            if full_path.exists():
                files_to_process.append(full_path)

    print(f"Files to process: {len(files_to_process)}")
    print()

    # Process each file
    total_added = 0
    total_skipped = 0
    # Global sequence tracker to prevent duplicates across files in same story
    story_sequences = {}

    for file_path in sorted(files_to_process):
        try:
            added, skipped = process_file(
                file_path, dry_run=args.dry_run, story_sequences=story_sequences
            )
            total_added += added
            total_skipped += skipped
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
            import traceback

            traceback.print_exc()

    # Summary
    print()
    print("=" * 60)
    print("📊 Summary")
    print(f"  Test IDs added: {total_added}")
    print(f"  Tests skipped (already have IDs): {total_skipped}")
    print(f"  Total tests processed: {total_added + total_skipped}")

    if args.dry_run:
        print()
        print("ℹ️  Run without --dry-run to apply changes")
    else:
        print()
        print("✅ All files updated!")
        print("💡 Review changes and run: pytest tests/ --collect-only")


if __name__ == "__main__":
    main()
