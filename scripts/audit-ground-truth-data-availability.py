#!/usr/bin/env python3
"""Ground Truth Data Availability Audit Script.

Audits each of the 50 ground truth queries against actual database content to identify
misalignments between test queries and available data.

Usage:
    python scripts/audit-ground-truth-data-availability.py

Output:
    docs/validation/story-2.15-ground-truth-audit.json
"""

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg2
import psycopg2.extras

from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QueryIntent:
    """Parsed query intent with extracted entities, metrics, periods."""

    entity: str | None
    metric: str | None
    period: str | None
    currency: str | None
    raw_query: str


@dataclass
class AvailabilityStatus:
    """Data availability status for a query."""

    status: str  # AVAILABLE, PERIOD_MISMATCH, MISSING_METRIC, MISSING_ENTITY, CURRENCY_MISMATCH
    actual_period: str | None = None
    actual_entity: str | None = None
    available_metrics: list[str] | None = None
    actual_currency: str | None = None
    details: str = ""


@dataclass
class AuditResult:
    """Audit result for a single ground truth query."""

    query_id: int
    question: str
    parsed_intent: QueryIntent
    availability: AvailabilityStatus
    recommendation: str


def parse_query_intent(question: str) -> QueryIntent:
    """Extract entity, metric, period, and currency from natural language query.

    Args:
        question: Natural language query

    Returns:
        QueryIntent with parsed components
    """
    # Entity patterns (from Story 2.14 learnings)
    entity_patterns = [
        r"(Portugal|Tunisia|Angola|Brazil|Spain|Group|Secil|Cement|Ready-Mix)",
        r"(cement operations?|ready-mix operations?)",
    ]

    entity = None
    for pattern in entity_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            entity = match.group(1)
            break

    # Metric patterns
    metric_patterns = [
        r"(EBITDA|EBIT|revenue|costs?|expenses?)",
        r"(variable costs?|fixed costs?|distribution costs?|employee costs?)",
        r"(thermal energy|CO2 emissions|clinker ratio)",
        r"(frequency ratio|safety|health)",
    ]

    metric = None
    for pattern in metric_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            metric = match.group(1).lower()
            break

    # Period patterns
    period_patterns = [
        r"Q([1-4])[\s]?(25|2025)",  # Q3 2025, Q3 25
        r"(H[12])[\s]?(25|2025)",  # H1 2025
        r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s-]?(25|2025)",  # August 2025
        r"(FY|fiscal year)[\s]?(25|2025)",  # FY2025
        r"(Aug-25|Jun-25|Mar-25|Dec-25)",  # Database format
    ]

    period = None
    for pattern in period_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            period = match.group(0)
            break

    # Currency patterns
    currency_patterns = [
        r"(million\s+)?(EUR|AOA|BRL|USD)",
        r"(euro|euros)",
    ]

    currency = None
    for pattern in currency_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            currency = match.group(0) if match.lastindex is None else match.group(match.lastindex)
            currency = currency.upper() if len(currency) == 3 else "EUR"
            break

    return QueryIntent(
        entity=entity,
        metric=metric,
        period=period,
        currency=currency,
        raw_query=question,
    )


async def check_data_availability(
    conn: "psycopg2.extensions.connection",
    entity: str | None,
    metric: str | None,
    period: str | None,
    currency: str | None,
) -> AvailabilityStatus:
    """Check if data exists in financial_tables for the given query components.

    Args:
        conn: PostgreSQL connection
        entity: Company/division name
        metric: Cost type or metric
        period: Time period
        currency: Currency code

    Returns:
        AvailabilityStatus indicating data availability
    """
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # Check entity availability with fuzzy matching
        if entity:
            cursor.execute(
                """
                SELECT entity, similarity(entity, %s) as sim
                FROM financial_tables
                WHERE similarity(entity, %s) > 0.3
                ORDER BY sim DESC
                LIMIT 1
                """,
                (entity, entity),
            )
            entity_result = cursor.fetchone()

            if not entity_result:
                return AvailabilityStatus(
                    status="MISSING_ENTITY",
                    details=f"Entity '{entity}' not found in database",
                )

            actual_entity = entity_result["entity"]
        else:
            actual_entity = None

        # Check metric availability
        if metric:
            cursor.execute(
                """
                SELECT DISTINCT metric
                FROM financial_tables
                WHERE metric ILIKE %s
                LIMIT 5
                """,
                (f"%{metric}%",),
            )
            metric_results = cursor.fetchall()

            if not metric_results:
                return AvailabilityStatus(
                    status="MISSING_METRIC",
                    actual_entity=actual_entity,
                    details=f"Metric '{metric}' not found in database",
                )

            available_metrics = [r["metric"] for r in metric_results]
        else:
            available_metrics = None

        # Check period availability
        if period:
            # Normalize period format (Q3 2025 → Aug-25, etc.)
            period_variants = _get_period_variants(period)

            cursor.execute(
                """
                SELECT DISTINCT period
                FROM financial_tables
                WHERE period = ANY(%s)
                LIMIT 1
                """,
                (period_variants,),
            )
            period_result = cursor.fetchone()

            if not period_result:
                # Period mismatch - find closest available periods
                cursor.execute(
                    """
                    SELECT DISTINCT period
                    FROM financial_tables
                    ORDER BY period DESC
                    LIMIT 5
                    """,
                )
                available_periods = [r["period"] for r in cursor.fetchall()]

                return AvailabilityStatus(
                    status="PERIOD_MISMATCH",
                    actual_entity=actual_entity,
                    available_metrics=available_metrics,
                    details=f"Period '{period}' not found. Available: {', '.join(available_periods[:3])}",
                )

            actual_period = period_result["period"]
        else:
            actual_period = None

        # Check currency (EUR only in current database)
        if currency and currency not in ["EUR", "euro", "euros"]:
            return AvailabilityStatus(
                status="CURRENCY_MISMATCH",
                actual_entity=actual_entity,
                available_metrics=available_metrics,
                actual_period=actual_period,
                actual_currency="EUR",
                details=f"Currency '{currency}' not available. Database contains EUR only",
            )

        # All components available
        return AvailabilityStatus(
            status="AVAILABLE",
            actual_entity=actual_entity,
            available_metrics=available_metrics,
            actual_period=actual_period,
            actual_currency="EUR",
            details="All query components found in database",
        )

    except Exception as e:
        logger.error(f"Error checking data availability: {e}", exc_info=True)
        return AvailabilityStatus(
            status="ERROR",
            details=f"Database query failed: {str(e)}",
        )
    finally:
        cursor.close()


def _get_period_variants(period: str) -> list[str]:
    """Get database period variants for a given period string.

    Args:
        period: Period string (e.g., "Q3 2025", "August 2025")

    Returns:
        List of database period format variants
    """
    period_upper = period.upper()

    # Quarter mappings
    if "Q1" in period_upper or "FIRST QUARTER" in period_upper:
        return ["Jan-25", "Feb-25", "Mar-25", "Jan-25 YTD", "Mar-25 YTD", "Q1-25"]
    elif "Q2" in period_upper or "SECOND QUARTER" in period_upper:
        return ["Apr-25", "May-25", "Jun-25", "Apr-25 YTD", "Jun-25 YTD", "Q2-25"]
    elif "Q3" in period_upper or "THIRD QUARTER" in period_upper:
        return ["Jul-25", "Aug-25", "Sep-25", "Jul-25 YTD", "Aug-25 YTD", "Q3-25"]
    elif "Q4" in period_upper or "FOURTH QUARTER" in period_upper:
        return ["Oct-25", "Nov-25", "Dec-25", "Oct-25 YTD", "Dec-25 YTD", "Q4-25"]

    # Month-year patterns
    month_map = {
        "JAN": "Jan-25",
        "FEB": "Feb-25",
        "MAR": "Mar-25",
        "APR": "Apr-25",
        "MAY": "May-25",
        "JUN": "Jun-25",
        "JUL": "Jul-25",
        "AUG": "Aug-25",
        "SEP": "Sep-25",
        "OCT": "Oct-25",
        "NOV": "Nov-25",
        "DEC": "Dec-25",
    }

    for month_abbr, db_period in month_map.items():
        if month_abbr in period_upper or month_abbr.capitalize() in period:
            return [db_period, f"{db_period} YTD"]

    # Direct database format
    if re.match(r"[A-Z][a-z]{2}-\d{2}$", period):
        return [period, f"{period} YTD"]

    # Default: return as-is
    return [period]


def generate_recommendation(query: dict, availability: AvailabilityStatus) -> str:
    """Generate normalization recommendation based on availability status.

    Args:
        query: Ground truth query object
        availability: Data availability status

    Returns:
        Recommendation string for how to normalize or handle the query
    """
    if availability.status == "AVAILABLE":
        return "✅ Keep as-is (data available)"

    elif availability.status == "PERIOD_MISMATCH":
        return f"🔄 Replace period format: Use database format from {availability.details}"

    elif availability.status == "MISSING_METRIC":
        return f"❌ Remove query: Metric '{availability.details}' not in database"

    elif availability.status == "MISSING_ENTITY":
        return f"❌ Remove query: Entity '{availability.details}' not in database"

    elif availability.status == "CURRENCY_MISMATCH":
        return "🔄 Replace currency with EUR OR remove query (database is EUR-only)"

    elif availability.status == "ERROR":
        return f"⚠️ Manual review needed: {availability.details}"

    return "⚠️ Unknown status - manual review needed"


async def audit_ground_truth() -> list[AuditResult]:
    """Audit each ground truth query against actual database content.

    Returns:
        List of audit results for all queries
    """
    # Load original ground truth
    ground_truth_path = Path("tests/ground_truth.json")
    if not ground_truth_path.exists():
        raise FileNotFoundError(f"Ground truth file not found: {ground_truth_path}")

    with open(ground_truth_path) as f:
        ground_truth_data = json.load(f)

    queries = ground_truth_data.get("questions", [])
    if not queries:
        raise ValueError("No questions found in ground truth file")

    logger.info(f"Auditing {len(queries)} ground truth queries")

    # Connect to PostgreSQL
    conn = get_postgresql_connection()

    audit_results: list[AuditResult] = []

    for query in queries:
        query_id = query.get("id")
        question = query.get("question")

        if not question:
            logger.warning(f"Skipping query {query_id}: no question text")
            continue

        logger.debug(f"Auditing query {query_id}: {question[:60]}...")

        # Parse query intent
        parsed = parse_query_intent(question)

        # Check data availability
        availability = await check_data_availability(
            conn,
            entity=parsed.entity,
            metric=parsed.metric,
            period=parsed.period,
            currency=parsed.currency,
        )

        # Generate recommendation
        recommendation = generate_recommendation(query, availability)

        audit_results.append(
            AuditResult(
                query_id=query_id,
                question=question,
                parsed_intent=parsed,
                availability=availability,
                recommendation=recommendation,
            )
        )

    return audit_results


async def main():
    """Main audit execution."""
    print("=" * 80)
    print("GROUND TRUTH DATA AVAILABILITY AUDIT")
    print("=" * 80)
    print()

    # Run audit
    audit_results = await audit_ground_truth()

    # Calculate statistics
    status_counts = {}
    for result in audit_results:
        status = result.availability.status
        status_counts[status] = status_counts.get(status, 0) + 1

    total_queries = len(audit_results)

    # Print summary
    print("\nAudit Summary:")
    print("-" * 80)
    print(f"Total Queries: {total_queries}")
    print()
    print("Availability Breakdown:")
    for status, count in sorted(status_counts.items()):
        percentage = (count / total_queries) * 100
        print(f"  {status:20s}: {count:3d} queries ({percentage:5.1f}%)")

    # Save audit report
    output_dir = Path("docs/validation")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "story-2.15-ground-truth-audit.json"

    audit_data = {
        "metadata": {
            "total_queries": total_queries,
            "status_counts": status_counts,
            "audit_date": "2025-11-04",
        },
        "results": [
            {
                "query_id": r.query_id,
                "question": r.question,
                "parsed_intent": {
                    "entity": r.parsed_intent.entity,
                    "metric": r.parsed_intent.metric,
                    "period": r.parsed_intent.period,
                    "currency": r.parsed_intent.currency,
                },
                "availability": {
                    "status": r.availability.status,
                    "actual_period": r.availability.actual_period,
                    "actual_entity": r.availability.actual_entity,
                    "available_metrics": r.availability.available_metrics,
                    "actual_currency": r.availability.actual_currency,
                    "details": r.availability.details,
                },
                "recommendation": r.recommendation,
            }
            for r in audit_results
        ],
    }

    with open(output_path, "w") as f:
        json.dump(audit_data, f, indent=2)

    print()
    print("-" * 80)
    print(f"✅ Audit report saved: {output_path}")
    print()

    # Recommendations summary
    print("Normalization Recommendations:")
    print("-" * 80)
    keep_count = sum(1 for r in audit_results if r.availability.status == "AVAILABLE")
    modify_count = sum(
        1
        for r in audit_results
        if r.availability.status in ["PERIOD_MISMATCH", "CURRENCY_MISMATCH"]
    )
    remove_count = sum(
        1 for r in audit_results if r.availability.status in ["MISSING_METRIC", "MISSING_ENTITY"]
    )

    print(f"  ✅ Keep as-is:     {keep_count} queries")
    print(f"  🔄 Modify format: {modify_count} queries")
    print(f"  ❌ Remove:         {remove_count} queries")
    print()
    print(f"Expected normalized ground truth size: {keep_count + modify_count} queries")
    print()


if __name__ == "__main__":
    asyncio.run(main())
