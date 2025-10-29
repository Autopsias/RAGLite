"""Initialize PostgreSQL database schema for financial metadata storage.

This script creates the financial_chunks table with 15 metadata fields
and optimized indexes for the Phase 2B multi-index retrieval architecture.

Usage:
    python scripts/init-postgresql.py
"""

import logging
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_database_schema(
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "raglite",
    user: str = "raglite",
    password: str = "raglite",
) -> None:
    """Create the financial_chunks table with metadata fields and indexes.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        dbname: Database name
        user: Database user
        password: Database password

    Raises:
        psycopg2.Error: If database connection or schema creation fails
    """
    conn = None
    cursor = None

    try:
        # Connect to PostgreSQL
        logger.info(f"Connecting to PostgreSQL at {host}:{port}/{dbname}")
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create financial_chunks table
        logger.info("Creating financial_chunks table...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_chunks (
                -- Core fields
                chunk_id UUID PRIMARY KEY,
                document_id UUID NOT NULL,
                page_number INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,

                -- Document-Level Metadata (7 fields - from ExtractedMetadata model)
                document_type VARCHAR(100),           -- Income Statement, Balance Sheet, etc.
                reporting_period VARCHAR(50),         -- Q1 2024, Aug-25 YTD, FY 2023
                time_granularity VARCHAR(50),         -- Daily, Weekly, Monthly, Quarterly, YTD
                company_name VARCHAR(100),            -- Portugal Cement, CIMPOR, etc.
                geographic_jurisdiction VARCHAR(50),  -- Portugal, EU, APAC, Americas, Global
                data_source_type VARCHAR(50),         -- Audited, Internal Report, etc.
                version_date VARCHAR(50),             -- 2025-08-15, 2024-Q3-Final

                -- Chunk/Section-Level Metadata (5 fields)
                section_type VARCHAR(50),             -- Narrative, Table, Footnote, etc.
                metric_category VARCHAR(100),         -- Revenue, EBITDA, Operating Expenses, etc.
                units VARCHAR(50),                    -- EUR, USD, EUR/ton, Percentage, etc.
                department_scope VARCHAR(100),        -- Operations, Finance, Production, etc.

                -- Table-Specific Metadata (3 fields)
                table_context TEXT,                   -- LLM description of table purpose
                table_name VARCHAR(200),              -- Actual table title from document
                statistical_summary TEXT,             -- Mean, Min, Max, Trend stats

                -- Search optimization
                content_tsv TSVECTOR,                 -- Full-text search vector
                embedding_id VARCHAR(100),            -- Link to Qdrant vector ID

                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """
        )
        logger.info("✓ financial_chunks table created")

        # Create indexes for fast filtering
        logger.info("Creating indexes...")

        # Index 1: Composite index for company + metric queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_company_metric
            ON financial_chunks(company_name, metric_category);
        """
        )
        logger.info("✓ idx_company_metric created (company_name, metric_category)")

        # Index 2: Time period filtering
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reporting_period
            ON financial_chunks(reporting_period);
        """
        )
        logger.info("✓ idx_reporting_period created")

        # Index 3: Full-text search using GIN index
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_content_tsv
            ON financial_chunks USING GIN(content_tsv);
        """
        )
        logger.info("✓ idx_content_tsv created (GIN index for full-text search)")

        # Index 4: Section type filtering (table vs narrative)
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_section_type
            ON financial_chunks(section_type);
        """
        )
        logger.info("✓ idx_section_type created")

        # Verify schema creation
        cursor.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'financial_chunks'
            ORDER BY ordinal_position;
        """
        )
        columns = cursor.fetchall()
        logger.info(f"✓ Schema verification: {len(columns)} columns created")

        # Verify indexes
        cursor.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'financial_chunks';
        """
        )
        indexes = cursor.fetchall()
        logger.info(f"✓ Index verification: {len(indexes)} indexes created")

        logger.info("✅ PostgreSQL schema initialization complete!")

    except psycopg2.Error as e:
        logger.error(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    create_database_schema()
