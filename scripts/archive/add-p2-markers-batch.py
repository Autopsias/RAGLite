#!/usr/bin/env python3
"""Add P2 priority markers to edge case and integration tests."""

import os
import re


def update_test_file(filepath, test_updates):
    """Update a test file with P2 markers."""

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return 0

    with open(filepath) as f:
        content = f.read()

    count = 0
    for test_id, justification in test_updates:
        # Check if already has priority marker
        if f'@pytest.mark.test_id("{test_id}")' in content:
            # Look for the test function
            pattern = rf'(@pytest\.mark\.test_id\("{test_id}"\))\n(    def test_\w+.*?\):\n        """.*?(?:\n.*?)*?Priority: )(?:TBD \(Story 3-0-7\)|P\d+ \(.*?\))'

            # Check if already has a priority marker
            if not re.search(
                rf'@pytest\.mark\.test_id\("{test_id}"\)\n    @pytest\.mark\.priority',
                content,
            ):
                # Add priority marker
                replacement = (
                    rf'\1\n    @pytest.mark.priority("P2")\n\2P2 (Medium) - {justification}'
                )
                new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                if new_content != content:
                    content = new_content
                    count += 1

    if count > 0:
        with open(filepath, "w") as f:
            f.write(content)

    return count


# Define all P2 test updates
updates = {
    # Unit tests - Edge cases and advanced features
    "tests/unit/test_period_normalizer.py": [
        ("2.15-UNIT-001", "Advanced feature: period normalization"),
        ("2.15-UNIT-002", "Advanced feature: period normalization"),
        ("PN-UNIT-003", "Advanced feature: period normalization"),
        ("PN-UNIT-004", "Advanced feature: period normalization"),
        ("PN-UNIT-005", "Advanced feature: period normalization"),
        ("PN-UNIT-006", "Advanced feature: period normalization"),
        ("PN-UNIT-007", "Advanced feature: period normalization"),
        ("PN-UNIT-008", "Advanced feature: period normalization"),
        ("PN-UNIT-009", "Advanced feature: period normalization"),
        ("PN-UNIT-010", "Advanced feature: period normalization"),
        ("PN-UNIT-011", "Advanced feature: period normalization"),
        ("PN-UNIT-012", "Advanced feature: period normalization"),
        ("PN-UNIT-013", "Advanced feature: period normalization"),
        ("PN-UNIT-014", "Advanced feature: period normalization"),
        ("PN-UNIT-015", "Advanced feature: period normalization"),
        ("PN-UNIT-016", "Advanced feature: period normalization"),
        ("PN-UNIT-017", "Advanced feature: period normalization"),
        ("PN-UNIT-018", "Advanced feature: period normalization"),
        ("PN-UNIT-019", "Advanced feature: period normalization"),
        ("PN-UNIT-020", "Advanced feature: period normalization"),
        ("PN-UNIT-021", "Advanced feature: period normalization"),
        ("PN-UNIT-022", "Advanced feature: period normalization"),
        ("PN-UNIT-023", "Advanced feature: period normalization"),
        ("PN-UNIT-024", "Advanced feature: period normalization"),
        ("PN-UNIT-025", "Advanced feature: period normalization"),
        ("PN-UNIT-026", "Advanced feature: period normalization"),
        ("PN-UNIT-027", "Advanced feature: period normalization"),
        ("PN-UNIT-028", "Advanced feature: period normalization"),
        ("PN-UNIT-029", "Advanced feature: period normalization"),
        ("PN-UNIT-030", "Advanced feature: period normalization"),
        ("PN-UNIT-031", "Advanced feature: period normalization"),
        ("PN-UNIT-032", "Advanced feature: period normalization"),
        ("PN-UNIT-033", "Advanced feature: period normalization"),
        ("PN-UNIT-034", "Advanced feature: period normalization"),
        ("PN-UNIT-035", "Advanced feature: period normalization"),
        ("PN-UNIT-036", "Advanced feature: period normalization"),
    ],
    "tests/unit/test_docling_extraction.py": [
        ("DOCLING-UNIT-001", "External integration: Docling library"),
    ],
    "tests/unit/test_page_extraction.py": [
        ("PAGE-UNIT-001", "Advanced feature: page-level extraction"),
        ("PAGE-UNIT-002", "Advanced feature: page-level metadata"),
        ("PAGE-UNIT-003", "Advanced feature: page-level processing"),
        ("PAGE-UNIT-004", "Advanced feature: page-level validation"),
        ("PAGE-UNIT-005", "Advanced feature: page-level structure"),
    ],
    "tests/unit/test_pypdfium_backend.py": [
        ("PYPDFIUM-UNIT-001", "Performance optimization: pypdfium backend"),
        ("PYPDFIUM-UNIT-002", "Performance optimization: pypdfium backend"),
        ("PYPDFIUM-UNIT-003", "Performance optimization: pypdfium backend"),
        ("PYPDFIUM-UNIT-004", "Performance optimization: pypdfium backend"),
    ],
    "tests/unit/test_ac2_multi_entity_queries.py": [
        ("AC2-UNIT-001", "Advanced feature: multi-entity queries"),
        ("AC2-UNIT-002", "Advanced feature: multi-entity queries"),
        ("AC2-UNIT-003", "Advanced feature: multi-entity queries"),
        ("AC2-UNIT-004", "Advanced feature: multi-entity queries"),
        ("AC2-UNIT-005", "Advanced feature: multi-entity queries"),
        ("AC2-UNIT-006", "Advanced feature: multi-entity queries"),
    ],
    # Integration tests - External system integrations
    "tests/integration/test_pypdfium_ingestion.py": [
        ("2.1-INT-001", "Performance optimization: pypdfium integration"),
        ("2.1-INT-002", "Performance optimization: pypdfium memory"),
        ("2.1-INT-003", "Performance optimization: pypdfium consistency"),
        ("2.1-INT-004", "Performance optimization: pypdfium validation"),
    ],
    "tests/integration/test_page_parallelism.py": [
        ("2.2-INT-001", "Performance optimization: page parallelism"),
        ("2.2-INT-002", "Performance optimization: parallel speedup"),
        ("2.2-INT-003", "Performance optimization: parallel consistency"),
    ],
    "tests/integration/test_metadata_injection.py": [
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
    "tests/integration/test_e2e_query_validation.py": [
        ("E2E-QUERY-001", "E2E validation: query workflow"),
        ("E2E-QUERY-002", "E2E validation: query workflow"),
        ("E2E-QUERY-003", "E2E validation: query workflow"),
        ("E2E-QUERY-004", "E2E validation: query workflow"),
        ("E2E-QUERY-005", "E2E validation: query workflow"),
    ],
    "tests/integration/test_story_2_14_excerpt_validation.py": [
        ("2.14-INT-001", "Story-specific validation: excerpt extraction"),
        ("2.14-INT-002", "Story-specific validation: excerpt extraction"),
        ("2.14-INT-003", "Story-specific validation: excerpt extraction"),
        ("2.14-INT-004", "Story-specific validation: excerpt extraction"),
        ("2.14-INT-005", "Story-specific validation: excerpt extraction"),
        ("2.14-INT-006", "Story-specific validation: excerpt extraction"),
    ],
    # Tests with some P0 already marked - only mark remaining as P2
    "tests/integration/test_table_retrieval.py": [
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
    "tests/integration/test_sql_routing.py": [
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
    "tests/integration/test_retrieval_integration.py": [
        # Skip RI-INT-001 (already P0)
        ("RI-INT-002", "Integration test: retrieval workflow"),
        ("RI-INT-003", "Integration test: retrieval workflow"),
        ("RI-INT-004", "Integration test: retrieval workflow"),
        ("RI-INT-005", "Integration test: retrieval workflow"),
        ("RI-INT-006", "Integration test: retrieval workflow"),
    ],
    "tests/integration/test_mcp_server.py": [
        # Skip MCP-INT-001 and MCP-INT-002 (already P0)
        ("MCP-INT-003", "Integration test: MCP server"),
    ],
    "tests/integration/test_ingestion_integration.py": [
        # Skip II-INT-001 through II-INT-006 (already P0)
        ("II-INT-007", "Integration test: ingestion workflow"),
        ("II-INT-008", "Integration test: ingestion workflow"),
        ("II-INT-009", "Integration test: ingestion workflow"),
        ("II-INT-010", "Integration test: ingestion workflow"),
        ("II-INT-011", "Integration test: ingestion workflow"),
        ("II-INT-012", "Integration test: ingestion workflow"),
        ("II-INT-013", "Integration test: ingestion workflow"),
    ],
    "tests/integration/test_main_integration.py": [
        ("MAIN-INT-001", "Integration test: main workflow"),
        ("MAIN-INT-002", "Integration test: main workflow"),
        ("MAIN-INT-003", "Integration test: main workflow"),
        ("MAIN-INT-004", "Integration test: main workflow"),
        ("MAIN-INT-005", "Integration test: main workflow"),
        ("MAIN-INT-006", "Integration test: main workflow"),
    ],
}

# Process all files
total = 0
for filepath, test_updates in updates.items():
    count = update_test_file(filepath, test_updates)
    if count > 0:
        print(f"Updated {filepath}: {count} tests marked as P2")
        total += count

print(f"\nTotal P2 tests added: {total}")
