"""Initialize PostgreSQL TEST database schema for integration testing.

This script creates the required tables in the test database (port 5433).

Story 4.0.5: Database separation - ensures test database has proper schema
before running integration tests.

CRITICAL (2025-11-23): Uses Settings from environment to get database credentials.
This ensures the script works correctly in both local and CI environments.

Usage:
    python scripts/init-test-postgresql.py
"""

import logging
import os
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Set test environment BEFORE importing Settings
os.environ["APP_ENV"] = "test"
os.environ["TESTING"] = "true"

# Import Settings after setting environment
from raglite.shared.config import Settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_test_database_schema() -> None:
    """Create the financial_chunks and financial_tables tables in TEST database.

    Uses Settings from environment to determine connection parameters.
    This ensures the script works correctly in both local and CI environments.

    CRITICAL (2025-11-23): Settings loaded from environment variables:
    - POSTGRES_PORT (default: 5433 in test mode)
    - POSTGRES_DB (e.g., raglite_ci in CI, raglite_test locally)
    - POSTGRES_USER (e.g., raglite_ci in CI, raglite_test locally)
    - POSTGRES_PASSWORD (e.g., raglite_ci in CI, raglite_test locally)

    CRITICAL FIX (2025-12-18): Uses PostgreSQL advisory lock (lock_id=424242) to prevent
    race conditions when pytest-xdist runs multiple workers in parallel (gw0, gw1, gw2, gw3).
    Only one worker will hold the lock and initialize the schema; others wait or skip if
    schema already exists.

    Raises:
        psycopg2.Error: If database connection or schema creation fails
    """
    # Get settings from environment
    settings = Settings()

    conn = None
    cursor = None

    try:
        # Connect to TEST PostgreSQL
        logger.info(
            f"Connecting to TEST PostgreSQL at {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # CRITICAL FIX (2025-12-18): Acquire advisory lock to prevent race conditions
        # Lock ID: 424242 (arbitrary constant for RAGLite test schema initialization)
        # This prevents multiple pytest-xdist workers from initializing simultaneously
        SCHEMA_INIT_LOCK_ID = 424242
        logger.info(f"Attempting to acquire advisory lock {SCHEMA_INIT_LOCK_ID}...")

        # Try to acquire lock (non-blocking)
        cursor.execute("SELECT pg_try_advisory_lock(%s)", (SCHEMA_INIT_LOCK_ID,))
        lock_acquired = cursor.fetchone()[0]

        if not lock_acquired:
            # Another worker is initializing - check if schema already exists
            logger.info("Another worker is initializing schema - checking if complete...")
            max_wait_seconds = 30
            check_interval = 0.5
            checks = 0

            while checks < (max_wait_seconds / check_interval):
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'financial_chunks'
                    )
                    """
                )
                if cursor.fetchone()[0]:
                    logger.info("✅ Schema already initialized by another worker")
                    return
                import time

                time.sleep(check_interval)
                checks += 1

            logger.warning("Schema not found after waiting - proceeding anyway")
            return

        try:
            logger.info("✅ Advisory lock acquired - proceeding with schema initialization")

            # Double-check schema doesn't exist (belt and suspenders)
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'financial_chunks'
                )
                """
            )
            if cursor.fetchone()[0]:
                logger.info("Schema already exists - skipping initialization")
                return

            # Create financial_chunks table
            logger.info("Creating financial_chunks table...")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS financial_chunks (
                -- Core fields
                chunk_id UUID PRIMARY KEY,
                document_id TEXT NOT NULL,
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
            # NOTE: Schema matches migrations/002_create_financial_tables.sql exactly
            logger.info("Creating financial_tables table...")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS financial_tables (
                    -- Primary key
                    id SERIAL PRIMARY KEY,

                    -- Document metadata
                    document_id VARCHAR(255) NOT NULL,
                    page_number INT NOT NULL,
                    table_index INT NOT NULL,
                    table_caption TEXT,

                    -- Structured columns for querying
                    entity VARCHAR(255),           -- e.g., "Portugal Cement", "Spain Ready-Mix"
                    entity_normalized VARCHAR(100), -- Canonical entity name from entity_mappings
                    metric VARCHAR(255),            -- e.g., "variable costs", "thermal energy"
                    period VARCHAR(100),            -- e.g., "Aug-25 YTD", "Q2 2025"
                    fiscal_year INT,                -- e.g., 2025
                    value DECIMAL(15,2),            -- Numeric value
                    unit VARCHAR(50),               -- e.g., "EUR/ton", "GJ/ton"

                    -- Additional metadata
                    row_index INT,
                    column_name VARCHAR(255),
                    section_type VARCHAR(100) DEFAULT 'Table',
                    created_at TIMESTAMP DEFAULT NOW(),

                    -- Full context for attribution and fallback
                    chunk_text TEXT                 -- Original table chunk text for context
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

            # Index 5: Entity search on financial_tables (matches migration 002)
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entity
                ON financial_tables(entity);
            """
            )
            logger.info("✓ idx_entity created (entity on financial_tables)")

            # Index 6: Metric search on financial_tables (matches migration 002)
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_metric
                ON financial_tables(metric);
            """
            )
            logger.info("✓ idx_metric created (metric on financial_tables)")

            # Index 7: Period filtering on financial_tables (matches migration 002)
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_period
                ON financial_tables(period);
            """
            )
            logger.info("✓ idx_period created (period on financial_tables)")

            # Index 8: Fiscal year filtering on financial_tables (matches migration 002)
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_fiscal_year
                ON financial_tables(fiscal_year);
            """
            )
            logger.info("✓ idx_fiscal_year created")

            # Index 9: Document+page composite index (matches migration 002)
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_document_page
                ON financial_tables(document_id, page_number);
            """
            )
            logger.info("✓ idx_document_page created (document_id, page_number)")

            # Index 10: Entity normalized filtering (matches migration 005)
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_entity_normalized
                ON financial_tables(entity_normalized);
            """
            )
            logger.info("✓ idx_entity_normalized created (entity_normalized)")

            # Install pg_trgm extension for fuzzy matching (Story 2.14)
            logger.info("Installing pg_trgm extension for fuzzy matching...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            logger.info("✓ pg_trgm extension installed")

            # Create GIN trigram indexes for fast ILIKE queries (Migration 003)
            logger.info("Creating GIN trigram indexes for fuzzy matching...")

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_financial_tables_entity_trgm
                ON financial_tables USING gin(entity gin_trgm_ops);
            """
            )
            logger.info("✓ idx_financial_tables_entity_trgm created (fuzzy entity search)")

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_financial_tables_metric_trgm
                ON financial_tables USING gin(metric gin_trgm_ops);
            """
            )
            logger.info("✓ idx_financial_tables_metric_trgm created (fuzzy metric search)")

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_financial_tables_period_trgm
                ON financial_tables USING gin(period gin_trgm_ops);
            """
            )
            logger.info("✓ idx_financial_tables_period_trgm created (fuzzy period search)")

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

            # Create ORM-based tables (Story 7b-4, 6.12, etc.)
            # These tables are defined in raglite.external_data.orm_models
            logger.info("Creating ORM-based tables (model_selection, model_weights, etc.)...")
            try:
                from sqlalchemy import create_engine

                from raglite.external_data.orm_models import Base as ORMBase

                # Build SQLAlchemy connection URL
                db_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
                engine = create_engine(db_url)

                # Create all ORM tables that don't exist yet
                ORMBase.metadata.create_all(engine)
                logger.info(
                    "✓ ORM tables created (model_selection, model_weights, external_data_*, model_registry)"
                )

                # Verify ORM tables
                cursor.execute(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('model_selection', 'model_weights', 'external_data_sources', 'external_data_points', 'model_registry')
                    ORDER BY table_name;
                    """
                )
                orm_tables = [row[0] for row in cursor.fetchall()]
                logger.info(f"✓ ORM tables verified: {orm_tables}")

            except ImportError as e:
                logger.warning(f"Could not import ORM models (optional): {e}")
            except Exception as e:
                logger.warning(f"ORM table creation failed (optional, may already exist): {e}")

            logger.info("✅ TEST PostgreSQL schema initialization complete!")
            logger.info(f"   - Database: {settings.postgres_db} (port {settings.postgres_port})")
            logger.info("   - financial_chunks (chunks with metadata)")
            logger.info("   - financial_tables (structured table data)")
            logger.info("   - entity_mappings (canonical entity names)")
            logger.info("   - model_selection (model selection cache - Story 7b-4)")
            logger.info("   - model_weights (adaptive ensemble weights - Story 6.12)")
            logger.info("   - external_data_sources/points (regressor data)")
            logger.info("   - model_registry (model metadata)")

        except psycopg2.Error as e:
            logger.error(f"❌ Database error: {e}")
            sys.exit(1)
        finally:
            # Release advisory lock if we acquired it
            if lock_acquired:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (SCHEMA_INIT_LOCK_ID,))
                logger.info("Advisory lock released")
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
    create_test_database_schema()
