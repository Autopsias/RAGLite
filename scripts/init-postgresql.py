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

        # Create financial_tables table (Story 2.8+)
        logger.info("Creating financial_tables table...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_tables (
                document_id UUID NOT NULL,
                page_number INTEGER NOT NULL,
                table_index INTEGER NOT NULL,
                table_caption TEXT,
                entity VARCHAR(200),
                metric VARCHAR(200),
                period VARCHAR(100),
                fiscal_year VARCHAR(50),
                value TEXT,
                unit VARCHAR(50),
                row_index INTEGER,
                column_name VARCHAR(200),
                chunk_text TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """
        )
        logger.info("✓ financial_tables table created")

        # Create entity_mappings table (Story 2.14)
        logger.info("Creating entity_mappings table...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_mappings (
                canonical_name VARCHAR(200) PRIMARY KEY,
                raw_mentions TEXT[],
                entity_type VARCHAR(100),
                section_context TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """
        )
        logger.info("✓ entity_mappings table created")

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

        # Index 5: Entity search on financial_tables
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_entity_metric
            ON financial_tables(entity, metric);
        """
        )
        logger.info("✓ idx_entity_metric created (entity, metric on financial_tables)")

        # Index 6: Period filtering on financial_tables
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fiscal_year
            ON financial_tables(fiscal_year);
        """
        )
        logger.info("✓ idx_fiscal_year created")

        # Verify schema creation for all tables
        for table_name in ["financial_chunks", "financial_tables", "entity_mappings"]:
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """,
                (table_name,),
            )
            columns = cursor.fetchall()
            logger.info(f"✓ {table_name}: {len(columns)} columns verified")

        # Verify indexes (across all tables)
        cursor.execute(
            """
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE tablename IN ('financial_chunks', 'financial_tables', 'entity_mappings')
            ORDER BY tablename, indexname;
        """
        )
        indexes = cursor.fetchall()
        logger.info(f"✓ Index verification: {len(indexes)} total indexes created")

        logger.info("✅ PostgreSQL schema initialization complete!")
        logger.info("   - financial_chunks (chunks with metadata)")
        logger.info("   - financial_tables (structured table data)")
        logger.info("   - entity_mappings (canonical entity names)")

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
