"""Session state management for integration test fixtures.

This module defines global variables shared across session-scoped fixtures.
These track the baseline state for test isolation and restoration.

Global Variables:
    session_sample_pdf_chunk_count: Baseline Qdrant chunk count after session ingestion
    session_snapshot_name: Qdrant snapshot name for fast restoration
    session_postgresql_row_count: PostgreSQL baseline row count for restoration
    session_sample_pdf_result: Ingestion result metadata (filename, page_count)
    session_ingestion_duration: Time taken for session PDF ingestion (seconds)
"""

# Track session-level expected Qdrant state for test isolation
session_sample_pdf_chunk_count: int | None = None
session_snapshot_name: str | None = None
session_postgresql_row_count: int | None = None
session_sample_pdf_result = None
session_ingestion_duration: float = 0.0
