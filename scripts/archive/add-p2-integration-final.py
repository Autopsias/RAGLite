#!/usr/bin/env python3
"""Add P2 priority markers to integration tests with correct test IDs."""

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
                            r"Priority: .*",
                            f"Priority: P2 (Medium) - {justification}",
                            lines[j],
                        )
                        modified = True
                        break

    if modified:
        with open(filepath, "w") as f:
            f.writelines(lines)

    return modified


# Process all integration test files with correct test IDs
total = 0

# test_pypdfium_ingestion.py (4 tests)
file = "tests/integration/test_pypdfium_ingestion.py"
tests = [
    ("2.1-INTEGRATION-020", "Performance optimization: pypdfium integration"),
    ("2.1-INTEGRATION-021", "Performance optimization: pypdfium table accuracy"),
    ("2.1-INTEGRATION-022", "Performance optimization: pypdfium memory usage"),
    ("2.1-INTEGRATION-023", "Performance optimization: pypdfium validation"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_page_parallelism.py (3 tests)
file = "tests/integration/test_page_parallelism.py"
tests = [
    ("2.1-INTEGRATION-017", "Performance optimization: page parallelism"),
    ("2.1-INTEGRATION-018", "Performance optimization: parallel speedup"),
    ("2.1-INTEGRATION-019", "Performance optimization: parallel consistency"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_metadata_injection.py (10 tests)
file = "tests/integration/test_metadata_injection.py"
tests = [
    ("2.4-INTEGRATION-001", "Advanced feature: LLM metadata injection"),
    ("2.4-INTEGRATION-002", "Advanced feature: LLM metadata extraction"),
    ("2.4-INTEGRATION-003", "Advanced feature: LLM metadata enrichment"),
    ("2.4-INTEGRATION-004", "Advanced feature: metadata multi-index routing"),
    ("2.4-INTEGRATION-005", "Advanced feature: metadata-based query classification"),
    ("2.4-INTEGRATION-006", "Advanced feature: metadata validation"),
    ("2.4-INTEGRATION-007", "Advanced feature: metadata consistency"),
    ("2.4-INTEGRATION-008", "Advanced feature: metadata performance"),
    ("2.4-INTEGRATION-009", "Advanced feature: metadata accuracy"),
    ("2.4-INTEGRATION-010", "Advanced feature: metadata coverage"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_e2e_query_validation.py (5 tests)
file = "tests/integration/test_e2e_query_validation.py"
tests = [
    ("1.10-INTEGRATION-001", "E2E validation: query workflow"),
    ("1.10-INTEGRATION-002", "E2E validation: metadata extraction"),
    ("1.10-INTEGRATION-003", "E2E validation: response formatting"),
    ("1.10-INTEGRATION-004", "E2E validation: error handling"),
    ("1.10-INTEGRATION-005", "E2E validation: performance"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_story_2_14_excerpt_validation.py (6 tests)
file = "tests/integration/test_story_2_14_excerpt_validation.py"
tests = [
    ("2.14-INTEGRATION-001", "Story-specific validation: excerpt extraction"),
    ("2.14-INTEGRATION-002", "Story-specific validation: excerpt relevance"),
    ("2.14-INTEGRATION-003", "Story-specific validation: excerpt accuracy"),
    ("2.14-INTEGRATION-004", "Story-specific validation: excerpt formatting"),
    ("2.14-INTEGRATION-005", "Story-specific validation: excerpt metadata"),
    ("2.14-INTEGRATION-006", "Story-specific validation: excerpt coverage"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_table_retrieval.py (skip 2.6-INTEGRATION-001 which is P0, mark rest as P2)
file = "tests/integration/test_table_retrieval.py"
tests = [
    ("2.6-INTEGRATION-002", "Advanced feature: table chunk retrieval"),
    ("2.6-INTEGRATION-003", "Advanced feature: table metadata filtering"),
    ("2.6-INTEGRATION-004", "Advanced feature: table query matching"),
    ("2.6-INTEGRATION-005", "Advanced feature: transposed table retrieval"),
    ("2.6-INTEGRATION-006", "Advanced feature: table accuracy validation"),
    ("2.6-INTEGRATION-007", "Advanced feature: table context preservation"),
    ("2.6-INTEGRATION-008", "Advanced feature: table relevance scoring"),
    ("2.6-INTEGRATION-009", "Advanced feature: multi-table queries"),
    ("2.6-INTEGRATION-010", "Advanced feature: table formatting"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_sql_routing.py (skip 2.13-INTEGRATION-009 and 010 which are P0, mark rest as P2)
file = "tests/integration/test_sql_routing.py"
tests = [
    ("2.13-INTEGRATION-011", "Advanced feature: SQL query routing"),
    ("2.13-INTEGRATION-012", "Advanced feature: SQL table selection"),
    ("2.13-INTEGRATION-013", "Advanced feature: SQL query translation"),
    ("2.13-INTEGRATION-014", "Advanced feature: SQL result formatting"),
    ("2.13-INTEGRATION-015", "Advanced feature: SQL error handling"),
    ("2.13-INTEGRATION-016", "Advanced feature: SQL performance"),
    ("2.13-INTEGRATION-017", "Advanced feature: SQL metadata mapping"),
    ("2.13-INTEGRATION-018", "Advanced feature: SQL multi-table joins"),
    ("2.13-INTEGRATION-019", "Advanced feature: SQL aggregation queries"),
    ("2.13-INTEGRATION-020", "Advanced feature: SQL filter conditions"),
    ("2.13-INTEGRATION-021", "Advanced feature: SQL date handling"),
    ("2.13-INTEGRATION-022", "Advanced feature: SQL numeric precision"),
    ("2.13-INTEGRATION-023", "Advanced feature: SQL null handling"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_retrieval_integration.py (skip 1.12-INTEGRATION-001 which is P0, mark rest as P2)
file = "tests/integration/test_retrieval_integration.py"
tests = [
    ("1.12-INTEGRATION-002", "Integration test: retrieval accuracy"),
    ("1.12-INTEGRATION-003", "Integration test: retrieval ranking"),
    ("1.12-INTEGRATION-004", "Integration test: retrieval metadata"),
    ("1.12-INTEGRATION-005", "Integration test: retrieval performance"),
    ("1.12-INTEGRATION-006", "Integration test: retrieval error handling"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_mcp_server.py (skip 1.13-INTEGRATION-001 and 002 which are P0, mark rest as P2)
file = "tests/integration/test_mcp_server.py"
tests = [
    ("1.13-INTEGRATION-003", "Integration test: MCP error handling"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_ingestion_integration.py (skip 1.13-INTEGRATION-001 through 006 which are P0, mark rest as P2)
file = "tests/integration/test_ingestion_integration.py"
tests = [
    ("1.13-INTEGRATION-007", "Integration test: ingestion error recovery"),
    ("1.13-INTEGRATION-008", "Integration test: ingestion validation"),
    ("1.13-INTEGRATION-009", "Integration test: ingestion metadata extraction"),
    ("1.13-INTEGRATION-010", "Integration test: ingestion chunking"),
    ("1.13-INTEGRATION-011", "Integration test: ingestion performance"),
    ("1.13-INTEGRATION-012", "Integration test: ingestion memory usage"),
    ("1.13-INTEGRATION-013", "Integration test: ingestion consistency"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

# test_main_integration.py (6 tests)
file = "tests/integration/test_main_integration.py"
tests = [
    ("1.8-INTEGRATION-001", "Integration test: main workflow"),
    ("1.8-INTEGRATION-002", "Integration test: main error handling"),
    ("1.8-INTEGRATION-003", "Integration test: main configuration"),
    ("1.8-INTEGRATION-004", "Integration test: main performance"),
    ("1.8-INTEGRATION-005", "Integration test: main reliability"),
    ("1.8-INTEGRATION-006", "Integration test: main scalability"),
]
file_count = 0
for test_id, justification in tests:
    if add_p2_marker(file, test_id, justification):
        file_count += 1
        total += 1
if file_count > 0:
    print(f"Updated {file}: {file_count} tests marked as P2")

print(f"\nTotal P2 integration tests added: {total}")
