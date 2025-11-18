#!/usr/bin/env python3
"""Add P2 priority markers to edge case and integration tests."""

import os
import re


def add_p2_marker(filepath, test_id, justification):
    """Add P2 marker to a specific test."""

    if not os.path.exists(filepath):
        return False

    with open(filepath) as f:
        lines = f.readlines()

    modified = False
    for i, line in enumerate(lines):
        if f'@pytest.mark.test_id("{test_id}")' in line:
            # Check if next line already has priority marker
            if i + 1 < len(lines) and "@pytest.mark.priority" not in lines[i + 1]:
                # Insert priority marker
                lines.insert(i + 1, '    @pytest.mark.priority("P2")\n')

                # Update docstring (look for Priority: line within next 10 lines)
                for j in range(i + 2, min(i + 12, len(lines))):
                    if "Priority:" in lines[j] and ("TBD" in lines[j] or "Priority: P" in lines[j]):
                        lines[j] = re.sub(
                            r"Priority: .*", f"Priority: P2 (Medium) - {justification}", lines[j]
                        )
                        modified = True
                        break

    if modified:
        with open(filepath, "w") as f:
            f.writelines(lines)

    return modified


# Process all files
total = 0
files_to_update = [
    # Unit tests - period normalizer (36 tests)
    (
        "tests/unit/test_period_normalizer.py",
        [(f"2.15-UNIT-{i:03d}", "Advanced feature: period normalization") for i in range(1, 37)],
    ),
    # Unit tests - other files
    (
        "tests/unit/test_docling_extraction.py",
        [
            ("1.2-UNIT-001", "External integration: Docling library"),
        ],
    ),
    (
        "tests/unit/test_page_extraction.py",
        [
            ("1.15-UNIT-001", "Advanced feature: page-level extraction"),
            ("1.15-UNIT-002", "Advanced feature: page-level metadata"),
            ("1.15-UNIT-003", "Advanced feature: page-level processing"),
            ("1.15-UNIT-004", "Advanced feature: page-level validation"),
            ("1.15-UNIT-005", "Advanced feature: page-level structure"),
        ],
    ),
    (
        "tests/unit/test_pypdfium_backend.py",
        [
            ("2.1-UNIT-001", "Performance optimization: pypdfium backend"),
            ("2.1-UNIT-002", "Performance optimization: pypdfium backend"),
            ("2.1-UNIT-003", "Performance optimization: pypdfium backend"),
            ("2.1-UNIT-004", "Performance optimization: pypdfium backend"),
        ],
    ),
    (
        "tests/unit/test_ac2_multi_entity_queries.py",
        [
            ("2.14-UNIT-001", "Advanced feature: multi-entity queries"),
            ("2.14-UNIT-002", "Advanced feature: multi-entity queries"),
            ("2.14-UNIT-003", "Advanced feature: multi-entity queries"),
            ("2.14-UNIT-004", "Advanced feature: multi-entity queries"),
            ("2.14-UNIT-005", "Advanced feature: multi-entity queries"),
            ("2.14-UNIT-006", "Advanced feature: multi-entity queries"),
        ],
    ),
    # Integration tests
    (
        "tests/integration/test_pypdfium_ingestion.py",
        [
            ("2.1-INT-001", "Performance optimization: pypdfium integration"),
            ("2.1-INT-002", "Performance optimization: pypdfium memory"),
            ("2.1-INT-003", "Performance optimization: pypdfium consistency"),
            ("2.1-INT-004", "Performance optimization: pypdfium validation"),
        ],
    ),
    (
        "tests/integration/test_page_parallelism.py",
        [
            ("2.2-INT-001", "Performance optimization: page parallelism"),
            ("2.2-INT-002", "Performance optimization: parallel speedup"),
            ("2.2-INT-003", "Performance optimization: parallel consistency"),
        ],
    ),
    (
        "tests/integration/test_metadata_injection.py",
        [
            ("2.4-INT-001", "Advanced feature: LLM metadata injection"),
            ("2.4-INT-002", "Advanced feature: LLM metadata injection"),
            ("2.4-INT-003", "Advanced feature: LLM metadata injection"),
            ("2.4-INT-004", "Advanced feature: LLM metadata injection"),
            ("2.4-INT-005", "Advanced feature: LLM metadata injection"),
            ("2.4-INT-006", "Advanced feature: LLM metadata injection"),
            ("2.4-INT-007", "Advanced feature: LLM metadata injection"),
            ("2.4-INT-008", "Advanced feature: LLM metadata injection"),
            ("2.4-INT-009", "Advanced feature: LLM metadata injection"),
            ("2.4-INT-010", "Advanced feature: LLM metadata injection"),
        ],
    ),
    (
        "tests/integration/test_e2e_query_validation.py",
        [
            ("E2E-QUERY-001", "E2E validation: query workflow"),
            ("E2E-QUERY-002", "E2E validation: query workflow"),
            ("E2E-QUERY-003", "E2E validation: query workflow"),
            ("E2E-QUERY-004", "E2E validation: query workflow"),
            ("E2E-QUERY-005", "E2E validation: query workflow"),
        ],
    ),
    (
        "tests/integration/test_story_2_14_excerpt_validation.py",
        [
            ("2.14-INT-001", "Story-specific validation: excerpt extraction"),
            ("2.14-INT-002", "Story-specific validation: excerpt extraction"),
            ("2.14-INT-003", "Story-specific validation: excerpt extraction"),
            ("2.14-INT-004", "Story-specific validation: excerpt extraction"),
            ("2.14-INT-005", "Story-specific validation: excerpt extraction"),
            ("2.14-INT-006", "Story-specific validation: excerpt extraction"),
        ],
    ),
    # Tests with some P0 already marked - only mark remaining as P2
    (
        "tests/integration/test_table_retrieval.py",
        [
            ("TR-INT-002", "Advanced feature: table retrieval"),
            ("TR-INT-003", "Advanced feature: table retrieval"),
            ("TR-INT-004", "Advanced feature: table retrieval"),
            ("TR-INT-005", "Advanced feature: table retrieval"),
            ("TR-INT-006", "Advanced feature: table retrieval"),
            ("TR-INT-007", "Advanced feature: table retrieval"),
            ("TR-INT-008", "Advanced feature: table retrieval"),
            ("TR-INT-009", "Advanced feature: table retrieval"),
            ("TR-INT-010", "Advanced feature: table retrieval"),
        ],
    ),
    (
        "tests/integration/test_sql_routing.py",
        [
            ("2.13-INT-003", "Advanced feature: SQL routing"),
            ("2.13-INT-004", "Advanced feature: SQL routing"),
            ("2.13-INT-005", "Advanced feature: SQL routing"),
            ("2.13-INT-006", "Advanced feature: SQL routing"),
            ("2.13-INT-007", "Advanced feature: SQL routing"),
            ("2.13-INT-008", "Advanced feature: SQL routing"),
            ("2.13-INT-009", "Advanced feature: SQL routing"),
            ("2.13-INT-010", "Advanced feature: SQL routing"),
            ("2.13-INT-011", "Advanced feature: SQL routing"),
            ("2.13-INT-012", "Advanced feature: SQL routing"),
            ("2.13-INT-013", "Advanced feature: SQL routing"),
            ("2.13-INT-014", "Advanced feature: SQL routing"),
            ("2.13-INT-015", "Advanced feature: SQL routing"),
        ],
    ),
    (
        "tests/integration/test_retrieval_integration.py",
        [
            ("RI-INT-002", "Integration test: retrieval workflow"),
            ("RI-INT-003", "Integration test: retrieval workflow"),
            ("RI-INT-004", "Integration test: retrieval workflow"),
            ("RI-INT-005", "Integration test: retrieval workflow"),
            ("RI-INT-006", "Integration test: retrieval workflow"),
        ],
    ),
    (
        "tests/integration/test_mcp_server.py",
        [
            ("MCP-INT-003", "Integration test: MCP server"),
        ],
    ),
    (
        "tests/integration/test_ingestion_integration.py",
        [
            ("II-INT-007", "Integration test: ingestion workflow"),
            ("II-INT-008", "Integration test: ingestion workflow"),
            ("II-INT-009", "Integration test: ingestion workflow"),
            ("II-INT-010", "Integration test: ingestion workflow"),
            ("II-INT-011", "Integration test: ingestion workflow"),
            ("II-INT-012", "Integration test: ingestion workflow"),
            ("II-INT-013", "Integration test: ingestion workflow"),
        ],
    ),
    (
        "tests/integration/test_main_integration.py",
        [
            ("MAIN-INT-001", "Integration test: main workflow"),
            ("MAIN-INT-002", "Integration test: main workflow"),
            ("MAIN-INT-003", "Integration test: main workflow"),
            ("MAIN-INT-004", "Integration test: main workflow"),
            ("MAIN-INT-005", "Integration test: main workflow"),
            ("MAIN-INT-006", "Integration test: main workflow"),
        ],
    ),
]

for filepath, updates in files_to_update:
    file_count = 0
    for test_id, justification in updates:
        if add_p2_marker(filepath, test_id, justification):
            file_count += 1
            total += 1
    if file_count > 0:
        print(f"Updated {filepath}: {file_count} tests marked as P2")

print(f"\nTotal P2 tests added: {total}")
