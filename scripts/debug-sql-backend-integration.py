#!/usr/bin/env python3
"""AC0 SQL Backend Integration & Debugging - Story 2.14.

Debug script to diagnose and fix PostgreSQL returning 0 results for all SQL queries.

This script:
1. Tests SQL connectivity
2. Validates financial_tables schema
3. Executes sample queries and verifies results
4. Checks data consistency (entity names, periods, columns)
5. Verifies fuzzy matching capability
6. Documents all findings for Story 2.14 implementation
"""

import asyncio
import sys
from dataclasses import dataclass

from raglite.retrieval.query_classifier import generate_sql_query
from raglite.shared.clients import get_postgresql_connection
from raglite.shared.config import settings
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TestResult:
    """Result of a single test."""

    test_name: str
    passed: bool
    message: str
    details: dict | None = None


async def test_sql_connectivity() -> TestResult:
    """Test PostgreSQL connection and basic connectivity."""
    logger.info("=" * 80)
    logger.info("TEST 1: PostgreSQL Connectivity")
    logger.info("=" * 80)

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Simple connectivity test
        cursor.execute("SELECT 1 AS test")
        result = cursor.fetchone()
        cursor.close()

        if result and result[0] == 1:
            logger.info("✅ PostgreSQL connectivity: OK")
            return TestResult(
                test_name="SQL Connectivity",
                passed=True,
                message="PostgreSQL connection established successfully",
                details={
                    "host": settings.postgres_host,
                    "port": settings.postgres_port,
                    "database": settings.postgres_db,
                },
            )
        else:
            logger.error("❌ PostgreSQL connectivity: FAILED - Invalid response")
            return TestResult(
                test_name="SQL Connectivity",
                passed=False,
                message="PostgreSQL returned invalid response to connectivity test",
            )

    except Exception as e:
        logger.error(f"❌ PostgreSQL connectivity: FAILED - {e}")
        return TestResult(
            test_name="SQL Connectivity",
            passed=False,
            message=f"PostgreSQL connection failed: {e}",
        )


async def test_financial_tables_exists() -> TestResult:
    """Test that financial_tables table exists and is accessible."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Check financial_tables Table Exists")
    logger.info("=" * 80)

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'financial_tables'
            )
        """
        )
        exists = cursor.fetchone()[0]

        if not exists:
            logger.error("❌ financial_tables table: NOT FOUND")
            cursor.close()
            return TestResult(
                test_name="Table Exists",
                passed=False,
                message="financial_tables table does not exist in database",
            )

        # Get table info
        cursor.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'financial_tables'
            ORDER BY ordinal_position
        """
        )
        columns = cursor.fetchall()
        column_info = {col[0]: col[1] for col in columns}

        logger.info("✅ financial_tables table: FOUND")
        logger.info(f"   Columns ({len(column_info)}): {list(column_info.keys())}")

        # Check row count
        cursor.execute("SELECT COUNT(*) FROM financial_tables")
        row_count = cursor.fetchone()[0]
        logger.info(f"   Row count: {row_count}")

        cursor.close()

        if row_count == 0:
            logger.warning("⚠️  financial_tables is EMPTY - no data ingested")
            return TestResult(
                test_name="Table Exists",
                passed=True,
                message="Table exists but is empty",
                details={"row_count": 0, "columns": list(column_info.keys())},
            )

        return TestResult(
            test_name="Table Exists",
            passed=True,
            message=f"financial_tables table found with {row_count} rows",
            details={"row_count": row_count, "columns": list(column_info.keys())},
        )

    except Exception as e:
        logger.error(f"❌ financial_tables check: FAILED - {e}")
        return TestResult(
            test_name="Table Exists",
            passed=False,
            message=f"Failed to check table: {e}",
        )


async def test_sample_queries() -> TestResult:
    """Test generated SQL queries from natural language."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Generated SQL Queries")
    logger.info("=" * 80)

    test_queries = [
        "What is the variable cost for Portugal Cement in August 2025?",
        "What is the EBITDA for Tunisia in Q3 2025?",
        "How much is the revenue for Brazil?",
    ]

    query_results = []

    for natural_query in test_queries:
        logger.info(f"\nQuery: {natural_query}")
        logger.info("-" * 80)

        try:
            # Generate SQL
            sql = await generate_sql_query(natural_query)

            if not sql:
                logger.error("  ❌ SQL generation failed - returned None")
                query_results.append(
                    {
                        "natural_query": natural_query,
                        "sql": None,
                        "result_count": 0,
                        "error": "SQL generation failed",
                    }
                )
                continue

            logger.info(f"  Generated SQL:\n  {sql[:200]}...")

            # Execute SQL
            conn = get_postgresql_connection()
            cursor = conn.cursor()

            try:
                cursor.execute(sql)
                rows = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description]

                logger.info(f"  Results: {len(rows)} rows")

                if rows:
                    logger.info(f"  First row: {dict(zip(col_names, rows[0], strict=False))}")
                else:
                    logger.warning("  ⚠️  Query returned 0 results")

                query_results.append(
                    {
                        "natural_query": natural_query,
                        "sql": sql,
                        "result_count": len(rows),
                        "error": None,
                        "columns": col_names,
                    }
                )

            except Exception as sql_error:
                logger.error(f"  ❌ SQL execution failed: {sql_error}")
                query_results.append(
                    {
                        "natural_query": natural_query,
                        "sql": sql,
                        "result_count": 0,
                        "error": str(sql_error),
                    }
                )

            cursor.close()

        except Exception as e:
            logger.error(f"  ❌ Query processing failed: {e}")
            query_results.append(
                {
                    "natural_query": natural_query,
                    "error": str(e),
                }
            )

    # Summary
    successful = [q for q in query_results if q.get("result_count", 0) > 0]
    logger.info(f"\n✅ Successful queries: {len(successful)}/{len(test_queries)}")

    return TestResult(
        test_name="Sample Queries",
        passed=len(successful) > 0,
        message=f"{len(successful)}/{len(test_queries)} queries returned results",
        details={"query_results": query_results},
    )


async def test_data_consistency() -> TestResult:
    """Test data consistency: entity names, periods, column values."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Data Consistency")
    logger.info("=" * 80)

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Check unique entities
        cursor.execute("SELECT COUNT(DISTINCT entity) FROM financial_tables")
        unique_entities = cursor.fetchone()[0]
        logger.info(f"✅ Unique entities: {unique_entities}")

        # Sample entity values
        cursor.execute("SELECT DISTINCT entity FROM financial_tables LIMIT 10")
        entities = cursor.fetchall()
        logger.info(f"   Sample entities: {[e[0] for e in entities]}")

        # Check periods
        cursor.execute("SELECT COUNT(DISTINCT period) FROM financial_tables")
        unique_periods = cursor.fetchone()[0]
        logger.info(f"✅ Unique periods: {unique_periods}")

        cursor.execute("SELECT DISTINCT period FROM financial_tables LIMIT 10")
        periods = cursor.fetchall()
        logger.info(f"   Sample periods: {[p[0] for p in periods]}")

        # Check metrics
        cursor.execute("SELECT COUNT(DISTINCT metric) FROM financial_tables")
        unique_metrics = cursor.fetchone()[0]
        logger.info(f"✅ Unique metrics: {unique_metrics}")

        cursor.execute("SELECT DISTINCT metric FROM financial_tables LIMIT 10")
        metrics = cursor.fetchall()
        logger.info(f"   Sample metrics: {[m[0] for m in metrics]}")

        # Check NULL values
        cursor.execute(
            """
            SELECT
                COUNT(*) as null_entity,
                SUM(CASE WHEN entity IS NULL THEN 1 ELSE 0 END) as null_count
            FROM financial_tables
        """
        )
        result = cursor.fetchone()
        logger.info(f"✅ NULL entity check: {result}")

        cursor.close()

        return TestResult(
            test_name="Data Consistency",
            passed=True,
            message="Data consistency verified",
            details={
                "unique_entities": unique_entities,
                "unique_periods": unique_periods,
                "unique_metrics": unique_metrics,
            },
        )

    except Exception as e:
        logger.error(f"❌ Data consistency check: FAILED - {e}")
        return TestResult(
            test_name="Data Consistency",
            passed=False,
            message=f"Data consistency check failed: {e}",
        )


async def test_fuzzy_matching_setup() -> TestResult:
    """Test if pg_trgm extension is available for fuzzy matching."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Fuzzy Matching Setup (pg_trgm)")
    logger.info("=" * 80)

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Check if pg_trgm extension exists
        cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_trgm')")
        exists = cursor.fetchone()[0]

        if exists:
            logger.info("✅ pg_trgm extension: INSTALLED")
        else:
            logger.warning("⚠️  pg_trgm extension: NOT INSTALLED")
            logger.info("   This is needed for fuzzy entity matching (AC1)")

        # Check for GIN indexes
        cursor.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename='financial_tables'
            AND indexname LIKE '%trgm%'
        """
        )
        indexes = cursor.fetchall()
        logger.info(f"✅ GIN indexes for fuzzy matching: {len(indexes)}")
        for idx in indexes:
            logger.info(f"   {idx[0]}")

        cursor.close()

        return TestResult(
            test_name="Fuzzy Matching Setup",
            passed=exists,
            message="pg_trgm extension ready for fuzzy matching"
            if exists
            else "pg_trgm not installed - needed for AC1",
            details={"pg_trgm_installed": exists, "gin_indexes": len(indexes)},
        )

    except Exception as e:
        logger.error(f"❌ Fuzzy matching setup check: FAILED - {e}")
        return TestResult(
            test_name="Fuzzy Matching Setup",
            passed=False,
            message=f"Fuzzy matching setup check failed: {e}",
        )


async def main() -> int:
    """Run all diagnostic tests and report findings."""
    logger.info("\n")
    logger.info("🔍 AC0 SQL BACKEND INTEGRATION DIAGNOSTIC REPORT")
    logger.info("=" * 80)
    logger.info(f"PostgreSQL Host: {settings.postgres_host}")
    logger.info(f"PostgreSQL Port: {settings.postgres_port}")
    logger.info(f"PostgreSQL DB: {settings.postgres_db}")
    logger.info("=" * 80)

    results = []

    # Run all tests
    results.append(await test_sql_connectivity())
    results.append(await test_financial_tables_exists())
    results.append(await test_sample_queries())
    results.append(await test_data_consistency())
    results.append(await test_fuzzy_matching_setup())

    # Summary report
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    for result in results:
        status = "✅" if result.passed else "❌"
        logger.info(f"{status} {result.test_name}: {result.message}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    # Return exit code
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
