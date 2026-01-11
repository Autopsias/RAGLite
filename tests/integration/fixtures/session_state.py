"""Session state management for integration test fixtures.

This module defines global variables shared across session-scoped fixtures.
These track the baseline state for test isolation and restoration.

Global Variables:
    session_sample_pdf_chunk_count: Baseline Qdrant chunk count after session ingestion
    session_snapshot_name: Qdrant snapshot name for fast restoration
    session_postgresql_row_count: PostgreSQL baseline row count for restoration
    session_sample_pdf_result: Ingestion result metadata (filename, page_count)
    session_ingestion_duration: Time taken for session PDF ingestion (seconds)
    session_collection_dirty: Flag indicating collection needs restoration (P0 lazy restoration)
    session_needs_reingestion: Flag indicating full re-ingestion is required
"""

# Track session-level expected Qdrant state for test isolation
session_sample_pdf_chunk_count: int | None = None
session_snapshot_name: str | None = None
session_postgresql_row_count: int | None = None
session_sample_pdf_result = None
session_ingestion_duration: float = 0.0

# P0 lazy restoration: Track if collection needs restoration before next clean test
session_collection_dirty: bool = False
session_needs_reingestion: bool = False
