#!/usr/bin/env python3
"""Validate data quality from adaptive extraction on 20-page test."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.types.doc import TableItem

from raglite.ingestion.adaptive_table_extraction import extract_table_data_adaptive
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def validate_row_data_quality(row: dict) -> list[str]:
    """Check for common data corruption patterns.

    Returns list of issues found.
    """
    issues = []

    # Check 1: Year values in entity field (e.g., "2024" in entity)
    if row.get("entity") and isinstance(row["entity"], str):
        if any(year in row["entity"] for year in ["2023", "2024", "2025", "2026"]):
            issues.append(f"Year in entity field: '{row['entity']}'")

    # Check 2: Period values in metric field
    if row.get("metric") and isinstance(row["metric"], str):
        if any(
            kw in row["metric"].lower() for kw in ["ytd", "q1", "q2", "q3", "q4", "aug", "budget"]
        ):
            issues.append(f"Period keyword in metric field: '{row['metric']}'")

    # Check 3: Metric values in period field
    if row.get("period") and isinstance(row["period"], str):
        if any(
            kw in row["period"].lower() for kw in ["ebitda", "revenue", "sales", "margin", "cost"]
        ):
            issues.append(f"Metric keyword in period field: '{row['period']}'")

    # Check 4: Missing value but has text
    if row.get("value") is None:
        issues.append("NULL value extracted")

    return issues


def main():
    """Validate data quality on 20-page test."""
    pdf_path = Path("docs/sample pdf/test-pages-1-20.pdf")

    logger.info("=" * 80)
    logger.info("DATA QUALITY VALIDATION - Pages 1-20")
    logger.info("=" * 80)
    logger.info(f"PDF: {pdf_path}")
    logger.info("")

    # Convert PDF
    logger.info("Converting PDF...")
    converter = DocumentConverter(allowed_formats=[InputFormat.PDF])
    result = converter.convert(pdf_path)

    if not result.document:
        logger.error("PDF conversion failed!")
        return

    logger.info("✅ Conversion complete")
    logger.info("")

    # Extract all tables
    logger.info("Extracting and validating tables...")
    logger.info("")

    total_rows = 0
    total_issues = 0
    tables_with_issues = 0
    issue_details = []

    table_count = 0
    for element, _ in result.document.iterate_items():
        if isinstance(element, TableItem):
            # Get page number
            page_no = None
            if hasattr(element, "prov") and element.prov:
                for prov_item in element.prov:
                    if hasattr(prov_item, "page_no"):
                        page_no = prov_item.page_no
                        break

            if page_no is None:
                continue

            table_count += 1

            # Extract table
            rows = extract_table_data_adaptive(
                table_item=element,
                result=result,
                table_index=table_count,
                document_id="test-pages-1-20",
                page_number=page_no,
            )

            if not rows:
                continue

            # Validate each row
            table_issues = []
            for row in rows:
                issues = validate_row_data_quality(row)
                if issues:
                    total_issues += len(issues)
                    table_issues.extend(issues)
                    # Log first few issues for this row
                    for issue in issues[:2]:  # Max 2 issues per row to avoid spam
                        issue_details.append(
                            {
                                "page": page_no,
                                "table": table_count,
                                "issue": issue,
                                "row_sample": {
                                    "entity": row.get("entity"),
                                    "metric": row.get("metric"),
                                    "period": row.get("period"),
                                    "value": row.get("value"),
                                    "extraction_method": row.get("extraction_method"),
                                },
                            }
                        )

            total_rows += len(rows)

            if table_issues:
                tables_with_issues += 1
                logger.warning(
                    f"Page {page_no}, Table {table_count}: {len(table_issues)} issues in {len(rows)} rows"
                )
            else:
                logger.info(f"✅ Page {page_no}, Table {table_count}: {len(rows)} rows - NO ISSUES")

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("DATA QUALITY SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total rows extracted: {total_rows}")
    logger.info(f"Total issues found: {total_issues}")
    logger.info(f"Tables with issues: {tables_with_issues}/{table_count}")

    if total_rows > 0:
        issue_rate = (total_issues / total_rows) * 100
        logger.info(f"Issue rate: {issue_rate:.1f}%")

        if issue_rate < 5:
            logger.info("✅ PASS: Issue rate < 5% - Data quality acceptable")
        elif issue_rate < 15:
            logger.warning("⚠️ WARNING: Issue rate 5-15% - Some data corruption")
        else:
            logger.error(f"❌ FAIL: Issue rate {issue_rate:.1f}% - Significant data corruption")

    # Show sample issues
    if issue_details:
        logger.info("")
        logger.info("Sample Issues (first 10):")
        for i, detail in enumerate(issue_details[:10], 1):
            logger.info(f"\n{i}. Page {detail['page']}, Table {detail['table']}")
            logger.info(f"   Issue: {detail['issue']}")
            logger.info(
                f"   Row: entity={detail['row_sample']['entity']}, "
                f"metric={detail['row_sample']['metric']}, "
                f"period={detail['row_sample']['period']}"
            )
            logger.info(f"   Method: {detail['row_sample'].get('extraction_method', 'N/A')}")


if __name__ == "__main__":
    main()
