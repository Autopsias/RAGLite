#!/usr/bin/env python3
"""Re-ingest 20-page test PDF with improved header classification.

Goal: Validate that UNKNOWN 35% → 4.3% improvement translates to:
- NULL metric: 77.5% → <25%
- NULL entity: 86.5% → <30%
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.pipeline import ingest_document
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Re-ingest 20-page test PDF with improved patterns."""
    pdf_path = Path("docs/sample pdf/test-pages-1-20.pdf")

    logger.info("=" * 80)
    logger.info("RE-INGESTION: 20-Page Test with Improved Header Classification")
    logger.info("=" * 80)
    logger.info(f"PDF: {pdf_path}")
    logger.info("")

    # Clear existing data
    logger.info("Clearing existing data from financial_tables...")
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM financial_tables")
    conn.commit()
    logger.info("✅ Cleared existing data")
    logger.info("")

    # Ingest with improved classification
    logger.info("Starting ingestion with improved header classification...")
    logger.info("")

    try:
        await ingest_document(str(pdf_path))
        logger.info("✅ Ingestion complete")
    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}")
        raise
    logger.info("")

    # Analyze results
    logger.info("=" * 80)
    logger.info("DATA QUALITY ANALYSIS")
    logger.info("=" * 80)

    # Total rows
    cursor.execute("SELECT COUNT(*) FROM financial_tables")
    total_rows = cursor.fetchone()[0]
    logger.info(f"Total rows extracted: {total_rows}")
    logger.info("")

    # NULL field statistics
    cursor.execute(
        """
        SELECT
            COUNT(CASE WHEN entity IS NULL THEN 1 END) as null_entity,
            COUNT(CASE WHEN metric IS NULL THEN 1 END) as null_metric,
            COUNT(CASE WHEN period IS NULL THEN 1 END) as null_period,
            COUNT(CASE WHEN value IS NULL THEN 1 END) as null_value
        FROM financial_tables
    """
    )
    null_entity, null_metric, null_period, null_value = cursor.fetchone()

    logger.info("NULL Field Statistics:")
    logger.info(
        f"  NULL entity: {null_entity}/{total_rows} ({null_entity / total_rows * 100:.1f}%)"
    )
    logger.info(
        f"  NULL metric: {null_metric}/{total_rows} ({null_metric / total_rows * 100:.1f}%)"
    )
    logger.info(
        f"  NULL period: {null_period}/{total_rows} ({null_period / total_rows * 100:.1f}%)"
    )
    logger.info(f"  NULL value:  {null_value}/{total_rows} ({null_value / total_rows * 100:.1f}%)")
    logger.info("")

    # Compare to baseline
    logger.info("COMPARISON TO BASELINE (Full PDF results):")
    logger.info("  NULL entity: 86.5% (baseline) → ? (current)")
    logger.info("  NULL metric: 77.5% (baseline) → ? (current)")
    logger.info("")

    # Success criteria
    target_entity_null = 0.30 * total_rows  # 30% target
    target_metric_null = 0.25 * total_rows  # 25% target

    logger.info("SUCCESS CRITERIA:")
    if null_entity <= target_entity_null:
        logger.info(f"  ✅ NULL entity: {null_entity / total_rows * 100:.1f}% (target: <30%)")
    else:
        logger.info(f"  ❌ NULL entity: {null_entity / total_rows * 100:.1f}% (target: <30%)")

    if null_metric <= target_metric_null:
        logger.info(f"  ✅ NULL metric: {null_metric / total_rows * 100:.1f}% (target: <25%)")
    else:
        logger.info(f"  ❌ NULL metric: {null_metric / total_rows * 100:.1f}% (target: <25%)")

    logger.info("")

    # Sample data quality
    logger.info("=" * 80)
    logger.info("SAMPLE DATA (first 10 rows)")
    logger.info("=" * 80)

    cursor.execute(
        """
        SELECT entity, metric, period, value, unit
        FROM financial_tables
        LIMIT 10
    """
    )

    for i, (entity, metric, period, value, unit) in enumerate(cursor.fetchall(), 1):
        logger.info(
            f"{i:2d}. entity={entity or 'NULL':20s} | metric={metric or 'NULL':30s} | "
            f"period={period or 'NULL':15s} | value={value} | unit={unit or 'N/A'}"
        )

    logger.info("")

    # Pattern distribution
    logger.info("=" * 80)
    logger.info("FIELD COMPLETENESS PATTERNS")
    logger.info("=" * 80)

    cursor.execute(
        """
        SELECT
            CASE WHEN entity IS NULL THEN 'NULL' ELSE 'HAS' END as entity_status,
            CASE WHEN metric IS NULL THEN 'NULL' ELSE 'HAS' END as metric_status,
            CASE WHEN period IS NULL THEN 'NULL' ELSE 'HAS' END as period_status,
            CASE WHEN value IS NULL THEN 'NULL' ELSE 'HAS' END as value_status,
            COUNT(*) as count
        FROM financial_tables
        GROUP BY entity_status, metric_status, period_status, value_status
        ORDER BY count DESC
        LIMIT 10
    """
    )

    for entity_status, metric_status, period_status, value_status, count in cursor.fetchall():
        pct = count / total_rows * 100
        pattern = f"{entity_status:4s}|{metric_status:4s}|{period_status:4s}|{value_status:4s}"
        logger.info(f"  {pattern}: {count:5d} ({pct:5.1f}%)")

    logger.info("")

    # Determine next steps
    logger.info("=" * 80)
    logger.info("NEXT STEPS")
    logger.info("=" * 80)

    both_pass = null_entity <= target_entity_null and null_metric <= target_metric_null

    if both_pass:
        logger.info("✅ 20-page test PASSED!")
        logger.info("")
        logger.info("Recommended next step:")
        logger.info("  1. Re-ingest full 160-page PDF")
        logger.info("  2. Run AC4 validation")
        logger.info("  3. Target: ≥70% overall, ≥75% SQL")
    else:
        logger.info("⚠️  20-page test shows improvement but below targets")
        logger.info("")
        logger.info("Possible causes:")
        logger.info("  - Some headers still not classified (need more patterns)")
        logger.info("  - Orientation detection still struggling")
        logger.info("")
        logger.info("Options:")
        logger.info("  A. Add more missing patterns (analyze remaining UNKNOWN headers)")
        logger.info("  B. Implement Phase 2: Orientation-aware extraction")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
