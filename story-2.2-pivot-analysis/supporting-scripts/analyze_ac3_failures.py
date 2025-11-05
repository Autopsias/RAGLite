"""Analyze AC3 test failures to identify patterns.

This script parses the test output to identify which queries passed/failed
and categorizes them to find root causes of the accuracy regression.
"""

import re
from pathlib import Path

# Parse test output
test_output = Path("/tmp/ac3_test_results.txt").read_text()

# Extract query results
query_pattern = r"\[(\d+)/50\] (.+?)\.\.\. .+? (✓|✗) \((\d+)ms\)"
matches = re.findall(query_pattern, test_output)

passed_queries = []
failed_queries = []

for match in matches:
    query_num, query_text, result, latency = match
    query_info = {"num": int(query_num), "text": query_text.strip(), "latency_ms": int(latency)}

    if result == "✓":
        passed_queries.append(query_info)
    else:
        failed_queries.append(query_info)


# Categorize queries by type
def categorize_query(query_text):
    """Categorize query by what it's asking for."""
    text_lower = query_text.lower()

    # Cost-related queries
    if any(term in text_lower for term in ["cost", "costs", "price"]):
        if "variable" in text_lower:
            return "Variable Costs"
        elif "fixed" in text_lower:
            return "Fixed Costs"
        elif "employee" in text_lower or "labour" in text_lower:
            return "Employee Costs"
        else:
            return "Other Costs"

    # Energy/consumption queries
    elif any(term in text_lower for term in ["energy", "electricity", "thermal", "fuel"]):
        if "consumption" in text_lower:
            return "Energy Consumption"
        elif "rate" in text_lower or "percentage" in text_lower:
            return "Energy Metrics"
        else:
            return "Energy Costs"

    # Financial metrics
    elif "ebitda" in text_lower:
        return "EBITDA Metrics"

    # Cash flow
    elif "cash" in text_lower or "capex" in text_lower or "debt" in text_lower:
        return "Cash Flow/Financial Position"

    # Headcount/FTE
    elif "fte" in text_lower or "employee" in text_lower or "headcount" in text_lower:
        return "Headcount/FTEs"

    # Production/capacity
    elif any(
        term in text_lower
        for term in ["production", "capacity", "utilization", "reliability", "performance factor"]
    ):
        return "Production/Capacity Metrics"

    # Environmental
    elif "co2" in text_lower or "emissions" in text_lower:
        return "Environmental Metrics"

    # Materials
    elif "raw material" in text_lower or "packaging" in text_lower:
        return "Materials"

    # Comparison/analysis
    elif "compare" in text_lower or "relationship" in text_lower or "breakdown" in text_lower:
        return "Comparative/Analytical"

    else:
        return "Other"


# Categorize all queries
passed_categories = {}
failed_categories = {}

for query in passed_queries:
    category = categorize_query(query["text"])
    if category not in passed_categories:
        passed_categories[category] = []
    passed_categories[category].append(query)

for query in failed_queries:
    category = categorize_query(query["text"])
    if category not in failed_categories:
        failed_categories[category] = []
    failed_categories[category].append(query)

# Print analysis
print("=" * 80)
print("AC3 FAILURE ANALYSIS - ELEMENT-AWARE CHUNKING")
print("=" * 80)
print("\nOVERALL RESULTS:")
print(f"  PASSED: {len(passed_queries)}/50 queries ({len(passed_queries) * 2}%)")
print(f"  FAILED: {len(failed_queries)}/50 queries ({len(failed_queries) * 2}%)")
print("  BASELINE: 28/50 queries (56%)")
print(f"  REGRESSION: {len(failed_queries) - (50 - 28)} queries worse than baseline")

print(f"\n{'-' * 80}")
print("FAILURE PATTERNS BY CATEGORY:")
print(f"{'-' * 80}")

all_categories = set(list(passed_categories.keys()) + list(failed_categories.keys()))
category_stats = []

for category in sorted(all_categories):
    passed_count = len(passed_categories.get(category, []))
    failed_count = len(failed_categories.get(category, []))
    total = passed_count + failed_count
    pass_rate = (passed_count / total * 100) if total > 0 else 0

    category_stats.append(
        {
            "category": category,
            "passed": passed_count,
            "failed": failed_count,
            "total": total,
            "pass_rate": pass_rate,
        }
    )

# Sort by pass rate (worst first)
category_stats.sort(key=lambda x: x["pass_rate"])

for stat in category_stats:
    status = (
        "❌ CRITICAL"
        if stat["pass_rate"] < 30
        else ("⚠️  POOR" if stat["pass_rate"] < 60 else "✓ OK")
    )
    print(
        f"\n{stat['category']}: {stat['passed']}/{stat['total']} passed ({stat['pass_rate']:.0f}%) {status}"
    )

    # Show failed queries for categories with <50% pass rate
    if stat["pass_rate"] < 50 and stat["category"] in failed_categories:
        for query in failed_categories[stat["category"]][:3]:  # Show first 3
            print(f"  [{query['num']}] {query['text'][:70]}...")

print(f"\n{'-' * 80}")
print("TOP 10 MOST COMMON FAILURE CATEGORIES:")
print(f"{'-' * 80}")

for i, stat in enumerate(category_stats[:10], 1):
    if stat["failed"] > 0:
        print(f"{i}. {stat['category']}: {stat['failed']} failures")

print(f"\n{'-' * 80}")
print("SAMPLE FAILED QUERIES (First 15):")
print(f"{'-' * 80}")

for query in failed_queries[:15]:
    category = categorize_query(query["text"])
    print(f"[{query['num']}] {category}: {query['text']}")

print(f"\n{'-' * 80}")
print("SAMPLE PASSED QUERIES (First 10):")
print(f"{'-' * 80}")

for query in passed_queries[:10]:
    category = categorize_query(query["text"])
    print(f"[{query['num']}] {category}: {query['text']}")

print(f"\n{'=' * 80}")
print("KEY INSIGHTS:")
print(f"{'=' * 80}")

# Calculate insights
worst_category = category_stats[0]
best_category = category_stats[-1]

print("\n1. WORST PERFORMING CATEGORY:")
print(f"   '{worst_category['category']}' - {worst_category['pass_rate']:.0f}% pass rate")
print(f"   {worst_category['failed']} failures out of {worst_category['total']} queries")

print("\n2. BEST PERFORMING CATEGORY:")
print(f"   '{best_category['category']}' - {best_category['pass_rate']:.0f}% pass rate")
print(f"   {best_category['passed']} passes out of {best_category['total']} queries")

print("\n3. REGRESSION ANALYSIS:")
print("   Baseline had 28 correct queries (56%)")
print("   Element-aware has 19 correct queries (38%)")
print("   Lost 9 queries that were working in baseline")
print("   This suggests element-aware chunking is splitting critical context")

print(f"\n{'=' * 80}\n")
