#!/usr/bin/env python3
"""Validate classification accuracy against ground truth.

This script compares database classification results against manually
verified ground truth data to calculate accuracy percentages.

Exit codes:
    0 - All accuracy targets met (period_type >= 95%, others >= 90%)
    1 - Accuracy below targets
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime

import psycopg2


@dataclass
class GroundTruthEntry:
    """Ground truth entry for validation."""

    document: str
    table_index: int
    row_index: int
    period: str
    entity: str
    expected_period_type: str
    expected_value_type: str
    expected_entity_level: str
    page: int | None = None  # Optional - not used for matching


@dataclass
class AccuracyResult:
    """Accuracy validation result."""

    metric: str
    expected_threshold: float
    actual_accuracy: float
    passed: bool


def load_ground_truth(path: Path) -> list[GroundTruthEntry]:
    """Load ground truth from JSON file."""
    with open(path) as f:
        data = json.load(f)

    entries = []
    for entry_data in data["entries"]:
        # Filter to only fields in dataclass (allows optional page field)
        allowed_fields = {
            "document",
            "table_index",
            "row_index",
            "period",
            "entity",
            "expected_period_type",
            "expected_value_type",
            "expected_entity_level",
            "page",
        }
        filtered_data = {k: v for k, v in entry_data.items() if k in allowed_fields}
        entries.append(GroundTruthEntry(**filtered_data))

    return entries


def query_actual_classification(conn_str: str, entry: GroundTruthEntry) -> tuple[str, str, str]:
    """Query actual classification from database.

    Matches rows by document content (entity + period), not PDF location.
    Page numbers are for RAG source attribution, not data identification.

    Returns:
        Tuple of (period_type, value_type, entity_level)
    """
    conn = psycopg2.connect(conn_str)
    try:
        with conn.cursor() as cur:
            # Query by document identifier and data content (entity + period)
            # Use LIKE for flexible entity matching (handles variations like
            # "Portugal" vs "Portugal Cement")
            # Order by period_type DESC NULLS LAST to prefer classified rows
            cur.execute(
                """
                SELECT period_type, value_type, entity_level
                FROM financial_tables
                WHERE document_id LIKE %s
                  AND period = %s
                  AND entity LIKE %s
                ORDER BY period_type DESC NULLS LAST
                LIMIT 1;
            """,
                (f"%{entry.document}%", entry.period, f"%{entry.entity}%"),
            )

            row = cur.fetchone()
            if row:
                return row[0], row[1], row[2]
            return None, None, None
    finally:
        conn.close()


def calculate_accuracy(ground_truth: list[GroundTruthEntry], conn_str: str) -> tuple[dict, list]:
    """Calculate accuracy for each classification field.

    Returns:
        Tuple of (accuracy_dict, misclassifications_list)
    """
    correct = {"period_type": 0, "value_type": 0, "entity_level": 0}
    total = len(ground_truth)
    misclassifications = []

    for entry in ground_truth:
        actual_period, actual_value, actual_entity = query_actual_classification(conn_str, entry)

        # Check each field
        if actual_period == entry.expected_period_type:
            correct["period_type"] += 1
        else:
            misclassifications.append(
                {
                    "document": entry.document,
                    "period": entry.period,
                    "entity": entry.entity,
                    "field": "period_type",
                    "expected": entry.expected_period_type,
                    "actual": actual_period,
                }
            )

        if actual_value == entry.expected_value_type:
            correct["value_type"] += 1
        else:
            misclassifications.append(
                {
                    "document": entry.document,
                    "period": entry.period,
                    "entity": entry.entity,
                    "field": "value_type",
                    "expected": entry.expected_value_type,
                    "actual": actual_value,
                }
            )

        if actual_entity == entry.expected_entity_level:
            correct["entity_level"] += 1
        else:
            misclassifications.append(
                {
                    "document": entry.document,
                    "period": entry.period,
                    "entity": entry.entity,
                    "field": "entity_level",
                    "expected": entry.expected_entity_level,
                    "actual": actual_entity,
                }
            )

    # Calculate percentages
    accuracy = {
        "period_type": 100 * correct["period_type"] / total,
        "value_type": 100 * correct["value_type"] / total,
        "entity_level": 100 * correct["entity_level"] / total,
    }

    return accuracy, misclassifications


def generate_report(
    accuracy: dict, misclassifications: list, results: list[AccuracyResult], output_path: Path
) -> None:
    """Generate accuracy report in markdown."""
    with open(output_path, "w") as f:
        f.write("# Classification Accuracy Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Summary table
        f.write("## Accuracy Summary\n\n")
        f.write("| Metric | Target | Actual | Status |\n")
        f.write("|--------|--------|--------|--------|\n")

        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            f.write(
                f"| {result.metric} | >= {result.expected_threshold}% | "
                f"{result.actual_accuracy:.1f}% | {status} |\n"
            )

        # Misclassifications
        if misclassifications:
            f.write(f"\n## Misclassifications ({len(misclassifications)})\n\n")
            f.write("| Document | Period | Entity | Field | Expected | Actual |\n")
            f.write("|----------|--------|--------|-------|----------|--------|\n")

            for error in misclassifications[:20]:  # Show first 20
                f.write(
                    f"| {error['document']} | {error['period']} | {error['entity']} | "
                    f"{error['field']} | {error['expected']} | {error['actual']} |\n"
                )

            if len(misclassifications) > 20:
                f.write(f"\n*... and {len(misclassifications) - 20} more*\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate classification accuracy against ground truth"
    )
    parser.add_argument(
        "--ground-truth",
        default="tests/fixtures/classification_ground_truth.json",
        help="Ground truth JSON file path",
    )
    parser.add_argument(
        "--output",
        default="docs/sprint-artifacts/classification-accuracy-report.md",
        help="Output report path",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed misclassifications",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("CLASSIFICATION ACCURACY VALIDATION")
    print("=" * 80)
    print()

    # Load ground truth
    gt_path = Path(args.ground_truth)
    if not gt_path.exists():
        print(f"❌ ERROR: Ground truth file not found: {gt_path}")
        return 1

    print(f"Loading ground truth: {gt_path}")
    ground_truth = load_ground_truth(gt_path)
    print(f"Loaded {len(ground_truth)} ground truth entries")
    print()

    # Use explicit production database settings (not test/CI)
    # Production database: localhost:5432/raglite
    postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port = os.environ.get("POSTGRES_PORT", "5432")
    postgres_db = os.environ.get("POSTGRES_DB", "raglite")
    postgres_user = os.environ.get("POSTGRES_USER", "raglite")
    postgres_password = os.environ.get("POSTGRES_PASSWORD", "raglite")

    # Build connection string
    conn_str = (
        f"postgresql://{postgres_user}:{postgres_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_db}"
    )
    print(f"Connecting to: {postgres_host}:{postgres_port}/{postgres_db}")

    # Calculate accuracy
    print("Calculating accuracy...")
    accuracy, misclassifications = calculate_accuracy(ground_truth, conn_str)

    print()
    print("Results:")

    # Check against targets
    results = [
        AccuracyResult(
            metric="period_type",
            expected_threshold=95.0,
            actual_accuracy=accuracy["period_type"],
            passed=accuracy["period_type"] >= 95.0,
        ),
        AccuracyResult(
            metric="value_type",
            expected_threshold=90.0,
            actual_accuracy=accuracy["value_type"],
            passed=accuracy["value_type"] >= 90.0,
        ),
        AccuracyResult(
            metric="entity_level",
            expected_threshold=90.0,
            actual_accuracy=accuracy["entity_level"],
            passed=accuracy["entity_level"] >= 90.0,
        ),
    ]

    all_passed = True
    for result in results:
        status = "✅" if result.passed else "❌"
        print(
            f"{status} {result.metric}: {result.actual_accuracy:.1f}% "
            f"(target: >= {result.expected_threshold}%)"
        )
        if not result.passed:
            all_passed = False

    # Show misclassifications
    if misclassifications and args.verbose:
        print(f"\nMisclassifications ({len(misclassifications)}):")
        for error in misclassifications[:10]:  # Show first 10
            print(
                f"  {error['document']} {error['period']}/{error['entity']}: {error['field']} "
                f"expected={error['expected']}, actual={error['actual']}"
            )

    print()

    # Generate report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating report: {output_path}")
    generate_report(accuracy, misclassifications, results, output_path)
    print("✅ Report saved")

    print()
    print("=" * 80)
    if all_passed:
        print("✅ VALIDATION PASSED - ALL TARGETS MET")
        print("=" * 80)
        return 0
    else:
        print("❌ VALIDATION FAILED - BELOW TARGETS")
        print("=" * 80)
        print("Review misclassifications in report.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
