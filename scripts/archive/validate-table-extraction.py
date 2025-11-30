#!/usr/bin/env python
"""Validate table extraction accuracy for Story 2.13 AC1.

Tests the TableExtractor class on a sample financial document and validates:
- Table detection (tables found)
- Structure parsing (entity, metric, period, value, unit)
- Data accuracy (>90% of rows have valid data)
- Year extraction (fiscal_year populated correctly)
"""

import asyncio
import sys
from pathlib import Path

from raglite.ingestion.table_extraction import TableExtractor
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def validate_extraction(pdf_path: str) -> dict:
    """Validate table extraction accuracy on a test document.

    Args:
        pdf_path: Path to test PDF

    Returns:
        Dictionary with validation metrics
    """
    logger.info(f"Starting table extraction validation on {pdf_path}")

    # Extract tables
    extractor = TableExtractor()
    table_rows = await extractor.extract_tables(pdf_path)

    if not table_rows:
        logger.error("No tables extracted - validation failed")
        return {
            "status": "FAILED",
            "error": "No tables found in document",
            "total_rows": 0,
        }

    # Analyze extracted data
    total_rows = len(table_rows)
    unique_tables = len({row["table_index"] for row in table_rows})

    # Count valid fields
    rows_with_entity = sum(1 for row in table_rows if row.get("entity"))
    rows_with_metric = sum(1 for row in table_rows if row.get("metric"))
    rows_with_period = sum(1 for row in table_rows if row.get("period"))
    rows_with_value = sum(1 for row in table_rows if row.get("value") is not None)
    rows_with_unit = sum(1 for row in table_rows if row.get("unit"))
    rows_with_year = sum(1 for row in table_rows if row.get("fiscal_year"))

    # Calculate accuracy metrics
    entity_accuracy = (rows_with_entity / total_rows) * 100 if total_rows > 0 else 0
    metric_accuracy = (rows_with_metric / total_rows) * 100 if total_rows > 0 else 0
    period_accuracy = (rows_with_period / total_rows) * 100 if total_rows > 0 else 0
    value_accuracy = (rows_with_value / total_rows) * 100 if total_rows > 0 else 0
    year_accuracy = (rows_with_year / total_rows) * 100 if total_rows > 0 else 0

    # Overall accuracy: at least 90% of rows should have entity, metric, and value
    valid_rows = sum(
        1
        for row in table_rows
        if row.get("entity") and row.get("metric") and row.get("value") is not None
    )
    overall_accuracy = (valid_rows / total_rows) * 100 if total_rows > 0 else 0

    # Sample extraction results
    sample_rows = table_rows[:5] if len(table_rows) >= 5 else table_rows

    logger.info(
        "Table extraction validation complete",
        extra={
            "total_rows": total_rows,
            "unique_tables": unique_tables,
            "overall_accuracy": f"{overall_accuracy:.1f}%",
            "entity_accuracy": f"{entity_accuracy:.1f}%",
            "metric_accuracy": f"{metric_accuracy:.1f}%",
            "value_accuracy": f"{value_accuracy:.1f}%",
        },
    )

    # Print results
    print("\n" + "=" * 80)
    print("TABLE EXTRACTION VALIDATION RESULTS")
    print("=" * 80)
    print(f"\nDocument: {Path(pdf_path).name}")
    print(f"Tables Found: {unique_tables}")
    print(f"Total Rows Extracted: {total_rows}")
    print("\nACCURACY METRICS:")
    print(f"  Overall (entity + metric + value):  {overall_accuracy:.1f}%")
    print(f"  Entity field:                        {entity_accuracy:.1f}%")
    print(f"  Metric field:                        {metric_accuracy:.1f}%")
    print(f"  Period field:                        {period_accuracy:.1f}%")
    print(f"  Value field:                         {value_accuracy:.1f}%")
    print(f"  Unit field:                          {rows_with_unit / total_rows * 100:.1f}%")
    print(f"  Fiscal Year field:                   {year_accuracy:.1f}%")

    print("\nSAMPLE EXTRACTED ROWS:")
    for i, row in enumerate(sample_rows, 1):
        print(f"\n  Row {i}:")
        print(f"    Entity:      {row.get('entity', 'N/A')}")
        print(f"    Metric:      {row.get('metric', 'N/A')}")
        print(f"    Period:      {row.get('period', 'N/A')}")
        print(f"    Fiscal Year: {row.get('fiscal_year', 'N/A')}")
        print(f"    Value:       {row.get('value', 'N/A')}")
        print(f"    Unit:        {row.get('unit', 'N/A')}")
        print(f"    Page:        {row.get('page_number', 'N/A')}")

    print("\n" + "=" * 80)

    # Determine pass/fail
    if overall_accuracy >= 90:
        print(f"\n✅ VALIDATION PASSED: {overall_accuracy:.1f}% accuracy (≥90% required)")
        status = "PASSED"
    else:
        print(f"\n❌ VALIDATION FAILED: {overall_accuracy:.1f}% accuracy (<90% required)")
        status = "FAILED"

    print("=" * 80 + "\n")

    return {
        "status": status,
        "total_rows": total_rows,
        "unique_tables": unique_tables,
        "overall_accuracy": overall_accuracy,
        "entity_accuracy": entity_accuracy,
        "metric_accuracy": metric_accuracy,
        "period_accuracy": period_accuracy,
        "value_accuracy": value_accuracy,
        "year_accuracy": year_accuracy,
        "valid_rows": valid_rows,
    }


async def main():
    """Run validation on test document."""
    # Use the 10-page test document
    test_doc = "docs/sample pdf/test-10-pages.pdf"

    if not Path(test_doc).exists():
        logger.error(f"Test document not found: {test_doc}")
        print(f"❌ ERROR: Test document not found: {test_doc}")
        sys.exit(1)

    results = await validate_extraction(test_doc)

    # Exit with appropriate code
    if results["status"] == "PASSED":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
