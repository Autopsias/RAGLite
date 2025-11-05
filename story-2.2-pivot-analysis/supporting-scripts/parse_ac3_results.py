"""Simple parser for AC3 test results."""

import re
from pathlib import Path

# Read test output
output = Path("/tmp/ac3_test_results.txt").read_text()

# Extract all query lines with their numbers
query_lines = re.findall(r"\[(\d+)/50\] (.+?)\.\.\.", output)

# Extract all pass/fail indicators with latencies
result_lines = re.findall(r"(✓|✗) \((\d+)ms\)", output)

print("=" * 80)
print("AC3 TEST RESULTS ANALYSIS")
print("=" * 80)

if len(query_lines) == len(result_lines) == 50:
    passed = []
    failed = []

    for _i, ((num, query_text), (result, latency)) in enumerate(
        zip(query_lines, result_lines, strict=False), 1
    ):
        query_info = {
            "num": int(num),
            "text": query_text.strip(),
            "result": result,
            "latency": int(latency),
        }

        if result == "✓":
            passed.append(query_info)
        else:
            failed.append(query_info)

    print("\nOVERALL RESULTS:")
    print(f"  PASSED: {len(passed)}/50 queries ({len(passed) * 2}%)")
    print(f"  FAILED: {len(failed)}/50 queries ({len(failed) * 2}%)")
    print("  BASELINE: 28/50 queries (56%)")
    print(f"  REGRESSION: {28 - len(passed)} queries lost vs baseline")

    print(f"\n{'-' * 80}")
    print(f"PASSED QUERIES ({len(passed)}):")
    print(f"{'-' * 80}")
    for q in passed:
        print(f"  [{q['num']:2d}] {q['text']}")

    print(f"\n{'-' * 80}")
    print(f"FAILED QUERIES ({len(failed)}):")
    print(f"{'-' * 80}")
    for q in failed:
        print(f"  [{q['num']:2d}] {q['text']}")

    # Categorize failures
    print(f"\n{'-' * 80}")
    print("FAILURE ANALYSIS BY TYPE:")
    print(f"{'-' * 80}")

    # Cost queries
    cost_failed = [q for q in failed if "cost" in q["text"].lower()]
    print(
        f"\nCOST-RELATED FAILURES: {len(cost_failed)}/{len([q for q in query_lines if 'cost' in q[1].lower()])}"
    )
    for q in cost_failed[:5]:
        print(f"  [{q['num']:2d}] {q['text'][:70]}")

    # EBITDA queries
    ebitda_failed = [q for q in failed if "ebitda" in q["text"].lower()]
    print(
        f"\nEBITDA-RELATED FAILURES: {len(ebitda_failed)}/{len([q for q in query_lines if 'ebitda' in q[1].lower()])}"
    )
    for q in ebitda_failed:
        print(f"  [{q['num']:2d}] {q['text'][:70]}")

    # Energy queries
    energy_failed = [
        q
        for q in failed
        if any(term in q["text"].lower() for term in ["energy", "electricity", "thermal", "fuel"])
    ]
    print(
        f"\nENERGY-RELATED FAILURES: {len(energy_failed)}/{len([q for q in query_lines if any(term in q[1].lower() for term in ['energy', 'electricity', 'thermal', 'fuel'])])}"
    )
    for q in energy_failed[:5]:
        print(f"  [{q['num']:2d}] {q['text'][:70]}")

    # Cash flow queries
    cash_failed = [
        q
        for q in failed
        if any(
            term in q["text"].lower()
            for term in ["cash", "capex", "debt", "working capital", "tax"]
        )
    ]
    print(
        f"\nCASH FLOW-RELATED FAILURES: {len(cash_failed)}/{len([q for q in query_lines if any(term in q[1].lower() for term in ['cash', 'capex', 'debt', 'working capital', 'tax'])])}"
    )
    for q in cash_failed[:5]:
        print(f"  [{q['num']:2d}] {q['text'][:70]}")

    # Employee/FTE queries
    fte_failed = [
        q
        for q in failed
        if any(term in q["text"].lower() for term in ["fte", "employee", "headcount"])
    ]
    print(
        f"\nHEADCOUNT-RELATED FAILURES: {len(fte_failed)}/{len([q for q in query_lines if any(term in q[1].lower() for term in ['fte', 'employee', 'headcount'])])}"
    )
    for q in fte_failed[:5]:
        print(f"  [{q['num']:2d}] {q['text'][:70]}")

    print(f"\n{'=' * 80}")
    print("KEY INSIGHTS:")
    print(f"{'=' * 80}")
    print(f"\n1. Lost {28 - len(passed)} queries that were working in baseline")
    print("2. Element-aware chunking appears to be breaking up critical data")
    print("3. 504 chunks vs 321 baseline = 57% more chunks may be diluting results")
    print("4. Tables may be over-fragmented, losing semantic coherence")

else:
    print(f"\nERROR: Found {len(query_lines)} queries and {len(result_lines)} results")
    print("Expected 50 of each")
