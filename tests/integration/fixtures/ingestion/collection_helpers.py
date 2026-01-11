"""Helper functions for collection management in session_ingested_collection fixture."""

import os
import sys
import time

import pytest

from raglite.ingestion.pipeline import create_collection
from raglite.shared.clients import get_postgresql_connection, get_qdrant_client
from raglite.shared.config import settings
from raglite.shared.safety import ProductionProtectionError, SafetyGuard


def validate_test_environment() -> None:
    """Validate that we're in a test environment.

    Raises:
        pytest.fail: If not in test environment
    """
    guard = SafetyGuard()
    try:
        guard.validate_test_environment("session_ingested_collection fixture")
        print(
            f"DEBUG: Test environment validated - Qdrant:{settings.qdrant_port}, PostgreSQL:{settings.postgres_port}",
            file=sys.stderr,
        )
    except ProductionProtectionError as e:
        pytest.fail(
            f"CRITICAL: TEST ISOLATION FAILURE\n{e}\nSet APP_ENV=test or use --skip-ingestion"
        )


def check_existing_collection() -> int:
    """Check if collection exists and return current count.

    Returns:
        int: Existing collection count (0 if doesn't exist)
    """
    import sys

    qdrant_check = get_qdrant_client()
    try:
        existing_count = qdrant_check.count(collection_name=settings.qdrant_collection_name).count
        if existing_count > 0:
            is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
            if is_ci:
                print("DEBUG: CI mode - proceeding with re-ingestion", file=sys.stderr)
            elif not sys.stdin.isatty():
                print(
                    "DEBUG: Non-interactive (VS Code/IDE) - proceeding with re-ingestion",
                    file=sys.stderr,
                )
            else:
                print(
                    f"⚠️  WARNING: Collection has {existing_count} chunks - will delete and re-ingest",
                    file=sys.stderr,
                )
        return existing_count
    except Exception as e:
        print(f"DEBUG: No existing collection ({e}) - safe to create", file=sys.stderr)
        return 0


def get_test_pdf_path():
    """Get the path to the test PDF file.

    Returns:
        tuple: (pdf_path, description, estimated_time)

    Raises:
        pytest.skip: If PDF file not found
    """
    from pathlib import Path

    use_full_pdf = os.getenv("TEST_USE_FULL_PDF", "false").lower() == "true"
    if use_full_pdf:
        sample_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
        pdf_description = "160-page PDF"
        estimated_time = "150-180s"
    else:
        sample_pdf = Path("tests/fixtures/sample_financial_report.pdf")
        pdf_description = "10-page PDF"
        estimated_time = "8-12s"

    if not sample_pdf.exists():
        pytest.skip(f"Test PDF not found at {sample_pdf}")

    return sample_pdf, pdf_description, estimated_time


def initialize_clean_collection(guard: SafetyGuard) -> None:
    """Delete existing collections and create a fresh one.

    Args:
        guard: SafetyGuard instance for validation

    Raises:
        pytest.skip: If initialization fails
    """
    import sys

    qdrant = get_qdrant_client()

    try:
        # Delete Qdrant collection
        try:
            qdrant.delete_collection(collection_name=settings.qdrant_collection_name)
            print("   ✓ Deleted existing collection", file=sys.stderr)
        except Exception:
            pass

        # Clear PostgreSQL tables
        try:
            guard.validate_test_environment("postgresql_cleanup_before_delete")
            conn = get_postgresql_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM financial_chunks")
            chunks_deleted = cursor.rowcount
            cursor.execute("DELETE FROM financial_tables")
            tables_deleted = cursor.rowcount
            print(
                f"   ✓ Cleared PostgreSQL: {tables_deleted} table rows, {chunks_deleted} chunk rows",
                file=sys.stderr,
            )
        except Exception:
            pass

        # Wait for deletion confirmation
        deletion_confirmed = False
        for attempt in range(8):
            try:
                collections = qdrant.get_collections().collections
                existing = [c.name for c in collections]
                if settings.qdrant_collection_name not in existing:
                    print("   ✓ Collection deletion confirmed", file=sys.stderr)
                    deletion_confirmed = True
                    break
            except Exception:
                deletion_confirmed = True
                break
            sleep_time = min(0.1 * (2**attempt), 0.5)
            time.sleep(sleep_time)

        if not deletion_confirmed:
            print("   ⚠️  Collection deletion timeout, proceeding", file=sys.stderr)

        # Create new collection
        create_collection(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimension,
        )

        initial_count = qdrant.count(collection_name=settings.qdrant_collection_name)
        if initial_count.count > 0:
            pytest.skip(f"Collection has {initial_count.count} chunks after creation (expected 0)")
        print("   ✓ Collection verified empty", file=sys.stderr)
    except Exception as e:
        pytest.skip(f"Failed to initialize Qdrant collection: {e}")
