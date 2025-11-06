#!/usr/bin/env python3
"""Add P2 priority markers to integration tests."""

import os
import re


def add_p2_marker_simple(filepath, test_ids_with_justifications):
    """Add P2 markers using a simpler approach."""

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return 0

    with open(filepath) as f:
        content = f.read()

    count = 0
    for test_id, justification in test_ids_with_justifications:
        # Skip if already has priority marker
        if (
            f'@pytest.mark.test_id("{test_id}")' in content
            and "@pytest.mark.priority"
            not in content[
                content.find(f'@pytest.mark.test_id("{test_id}")') - 100 : content.find(
                    f'@pytest.mark.test_id("{test_id}")'
                )
                + 200
            ]
        ):
            # Add priority marker after test_id
            pattern = f'(@pytest\\.mark\\.test_id\\("{test_id}"\\))'
            replacement = '\\1\n    @pytest.mark.priority("P2")'
            new_content = re.sub(pattern, replacement, content)

            if new_content != content:
                content = new_content

                # Update Priority line in docstring
                pattern2 = rf"(Test ID: {re.escape(test_id)}.*?\n.*?Priority: )(?:TBD \(Story 3-0-7\)|P\d+ \(.*?\))"
                replacement2 = f"\\1P2 (Medium) - {justification}"
                content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)
                count += 1

    if count > 0:
        with open(filepath, "w") as f:
            f.write(content)

    return count


# Integration test files to update
files = [
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
    (
        "tests/integration/test_table_retrieval.py",
        [
            # Skip TR-INT-001 (already P0)
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
            # Skip 2.13-INT-001 and 2.13-INT-002 (already P0)
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
            # Skip RI-INT-001 (already P0)
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
            # Skip MCP-INT-001 and MCP-INT-002 (already P0)
            ("MCP-INT-003", "Integration test: MCP server"),
        ],
    ),
    (
        "tests/integration/test_ingestion_integration.py",
        [
            # Skip II-INT-001 through II-INT-006 (already P0)
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

total = 0
for filepath, tests in files:
    count = add_p2_marker_simple(filepath, tests)
    if count > 0:
        print(f"Updated {filepath}: {count} tests marked as P2")
        total += count

print(f"\nTotal P2 integration tests added: {total}")
