"""Analyze LLM-based metadata auto-classification accuracy.

Story 2.11 AC3: Measure extraction accuracy and usage frequency to determine
whether to keep or disable auto-classification feature.

Decision Criteria:
- IF accuracy <80% OR usage <10%: DISABLE (incorrect filters hurt more than help)
- ELSE: KEEP enabled (working well, adds value)

Usage:
    python scripts/analyze-auto-classification-accuracy.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from raglite.retrieval.query_classifier import classify_query_metadata  # noqa: E402
from tests.fixtures.ground_truth import GROUND_TRUTH_QA  # noqa: E402


async def analyze_auto_classification_accuracy():
    """Analyze accuracy of LLM-based metadata extraction.

    Compares auto-extracted filters against ground truth to determine
    if auto-classification helps or hinders retrieval.
    """
    print("=" * 80)
    print("AUTO-CLASSIFICATION ACCURACY ANALYSIS")
    print("=" * 80)
    print(f"\nAnalyzing {len(GROUND_TRUTH_QA)} ground truth queries")
    print("\nAuto-Classification Feature:")
    print("  - Extracts metadata filters from queries using Claude API")
    print(
        "  - Example: 'EBITDA for Portugal' → {'metric_category': 'EBITDA', 'company_name': 'Portugal'}"
    )
    print("  - Used for score boosting (soft filtering) in hybrid search")
    print("\n" + "=" * 80)

    results = {
        "total_queries": 0,
        "queries_with_metadata": 0,
        "correct_extractions": 0,
        "incorrect_extractions": 0,
        "no_extraction": 0,
        "extraction_examples": [],
    }

    for qa in GROUND_TRUTH_QA:
        query = qa["question"]

        results["total_queries"] += 1

        # Extract metadata using auto-classification
        try:
            extracted = await classify_query_metadata(query)
        except Exception as e:
            print(f"  Error extracting metadata for '{query[:50]}...': {e}")
            results["no_extraction"] += 1
            continue

        # Analyze extraction quality
        has_fiscal_period = "fiscal_period" in extracted and extracted["fiscal_period"]
        has_company = "company_name" in extracted and extracted["company_name"]
        has_department = "department_name" in extracted and extracted["department_name"]
        has_metric = "metric_category" in extracted and extracted["metric_category"]
        has_any_metadata = has_fiscal_period or has_company or has_department or has_metric

        if has_any_metadata:
            results["queries_with_metadata"] += 1

            # Heuristic validation: Check if extracted values appear in query
            # This is not perfect but gives us a reasonable accuracy estimate
            query_lower = query.lower()
            extraction_valid = True
            invalid_fields = []

            # Validate fiscal period
            if has_fiscal_period:
                fiscal = extracted["fiscal_period"]
                # Check if ANY token from fiscal period appears in query
                fiscal_tokens = fiscal.lower().split()
                if not any(token in query_lower for token in fiscal_tokens):
                    extraction_valid = False
                    invalid_fields.append(f"fiscal_period='{fiscal}' (not in query)")

            # Validate company name
            if has_company:
                company = extracted["company_name"]
                # Check if company name or substring appears in query
                company_tokens = company.lower().split()
                if not any(token in query_lower for token in company_tokens if len(token) > 2):
                    extraction_valid = False
                    invalid_fields.append(f"company_name='{company}' (not in query)")

            # Validate metric category
            if has_metric:
                metric = extracted["metric_category"]
                # Check if metric appears in query
                metric_lower = metric.lower()
                if metric_lower not in query_lower:
                    # Check for common abbreviations
                    metric_abbrev = {
                        "ebitda": ["ebitda", "earnings"],
                        "revenue": ["revenue", "sales", "turnover"],
                        "margin": ["margin"],
                        "cost": ["cost", "expense"],
                    }
                    metric_found = False
                    for abbrev_list in metric_abbrev.values():
                        if any(abbrev in query_lower for abbrev in abbrev_list):
                            metric_found = True
                            break

                    if not metric_found:
                        extraction_valid = False
                        invalid_fields.append(f"metric_category='{metric}' (not in query)")

            if extraction_valid:
                results["correct_extractions"] += 1
            else:
                results["incorrect_extractions"] += 1
                # Store example of incorrect extraction
                if len(results["extraction_examples"]) < 5:
                    results["extraction_examples"].append(
                        {
                            "query": query,
                            "extracted": extracted,
                            "invalid_fields": invalid_fields,
                        }
                    )
        else:
            results["no_extraction"] += 1

    # Calculate accuracy
    if results["queries_with_metadata"] > 0:
        accuracy = (results["correct_extractions"] / results["queries_with_metadata"]) * 100
    else:
        accuracy = 0.0

    usage_percent = (results["queries_with_metadata"] / results["total_queries"]) * 100

    # Print results
    print("\n" + "=" * 80)
    print("\nANALYSIS RESULTS:")
    print("=" * 80)
    print(f"\nTotal queries analyzed: {results['total_queries']}")
    print(
        f"Queries with extracted metadata: {results['queries_with_metadata']} ({usage_percent:.1f}%)"
    )
    print(f"Correct extractions: {results['correct_extractions']}")
    print(f"Incorrect extractions: {results['incorrect_extractions']}")
    print(f"No metadata extracted: {results['no_extraction']}")
    print(f"\nExtraction accuracy: {accuracy:.1f}%")
    print(f"Usage frequency: {usage_percent:.1f}%")

    # Show incorrect extraction examples
    if results["extraction_examples"]:
        print("\n" + "=" * 80)
        print("\nEXAMPLES OF INCORRECT EXTRACTIONS:")
        print("=" * 80)
        for i, example in enumerate(results["extraction_examples"], 1):
            print(f"\nExample {i}:")
            print(f"  Query: {example['query']}")
            print(f"  Extracted: {example['extracted']}")
            print(f"  Issues: {', '.join(example['invalid_fields'])}")

    # Recommendations
    print("\n" + "=" * 80)
    print("\nRECOMMENDATIONS:")
    print("=" * 80)

    decision = None

    if accuracy < 80:
        decision = "DISABLE"
        print("\n⚠️  RECOMMENDATION: DISABLE auto-classification")
        print(f"   Reason: Accuracy {accuracy:.1f}% < 80% threshold")
        print("   Impact: Incorrect filters eliminate correct chunks (hard filters)")
        print("   Action: Remove auto_classify parameter from hybrid_search()")
    elif usage_percent < 10:
        decision = "DISABLE"
        print("\nℹ️  RECOMMENDATION: DISABLE auto-classification")
        print(f"   Reason: Usage {usage_percent:.1f}% < 10% threshold (low impact)")
        print("   Impact: Feature rarely triggers, simplicity preferred")
        print("   Action: Remove auto_classify logic for code simplicity")
    else:
        decision = "KEEP"
        print("\n✅ RECOMMENDATION: KEEP auto-classification enabled")
        print(f"   Accuracy: {accuracy:.1f}% (above 80% threshold)")
        print(f"   Usage: {usage_percent:.1f}% (above 10% threshold)")
        print("   Impact: Working well, adds value to retrieval")
        print("   Action: Add logging for extracted filters (debugging)")

    # Save results
    output_path = (
        project_root / "docs" / "validation" / "story-2.11-auto-classification-analysis.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "total_queries": results["total_queries"],
        "queries_with_metadata": results["queries_with_metadata"],
        "correct_extractions": results["correct_extractions"],
        "incorrect_extractions": results["incorrect_extractions"],
        "no_extraction": results["no_extraction"],
        "accuracy_percent": accuracy,
        "usage_percent": usage_percent,
        "decision": decision,
        "recommendation": f"{decision} auto-classification ({'accuracy' if accuracy < 80 else 'usage'} threshold)"
        if decision == "DISABLE"
        else "KEEP auto-classification enabled",
        "extraction_examples": results["extraction_examples"],
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    print("\n" + "=" * 80)

    return decision, accuracy


if __name__ == "__main__":
    print("\n")
    decision, accuracy = asyncio.run(analyze_auto_classification_accuracy())
    print(f"\n✅ Decision: {decision} auto-classification")
    print(f"   Accuracy: {accuracy:.1f}%")

    if decision == "DISABLE":
        print("\n   Next Steps:")
        print("   1. Remove auto_classify parameter from hybrid_search()")
        print("   2. Remove auto_classify logic from multi_index_search()")
        print("   3. Update documentation")
    else:
        print("\n   Next Steps:")
        print("   1. Add logging for extracted filters")
        print("   2. Monitor accuracy in production")
        print("   3. Consider per-field accuracy metrics")

    print("\n")
