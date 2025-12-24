"""Service availability checking for integration tests.

This module provides utilities to check if Qdrant and PostgreSQL services are available
before running integration tests. This prevents collection-time hangs when services are down.

Functions:
    check_service_available: Check if a service is reachable (1-second timeout)
    get_service_availability: Get cached service availability (checks only once)
    check_and_skip_if_unavailable: Skip tests if required services are unavailable
"""

import os
import socket
import sys

import pytest

# Get connection settings from environment (same as shared.config.Settings)
# CRITICAL FIX (2025-11-19): Integration tests MUST use TEST database ports
# Production: Qdrant 6333, PostgreSQL 5432
# Test: Qdrant 6335, PostgreSQL 5433 (Story 4.0.5 database separation)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6335"))  # TEST port (was 6333)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))  # TEST port (was 5432)


def check_service_available(host: str, port: int, service_name: str) -> bool:
    """Check if service is reachable with optimized 1-second timeout."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Reduced from 5s to 1s for faster discovery
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"DEBUG: {service_name} available at {host}:{port}", file=sys.stderr)
            return True
        else:
            print(
                f"DEBUG: {service_name} connection refused at {host}:{port}",
                file=sys.stderr,
            )
            return False
    except Exception as e:
        print(f"DEBUG: {service_name} check failed: {e}", file=sys.stderr)
        return False


# PERFORMANCE: Lazy service checking - only check when actually needed
# This avoids 10+ second delay during test discovery
qdrant_available = None  # Will be checked on first use
postgres_available = None  # Will be checked on first use


def get_service_availability() -> tuple[bool, bool]:
    """Get cached service availability, checking only once."""
    global qdrant_available, postgres_available

    if qdrant_available is None:
        qdrant_available = check_service_available(QDRANT_HOST, QDRANT_PORT, "Qdrant")
    if postgres_available is None:
        postgres_available = check_service_available(POSTGRES_HOST, POSTGRES_PORT, "PostgreSQL")

    return qdrant_available, postgres_available


# PERFORMANCE: Move service check to first fixture execution to avoid test discovery delay
# Services will be checked when first test runs, not during module import
def check_and_skip_if_unavailable():
    """Check services and skip if unavailable - called from fixtures, not module import.

    Enhanced (2025-12-24): Now attempts auto-restart of stopped containers before skipping.
    This addresses the strategic recommendation from test-strategy-analyst.
    """
    qdrant_avail, postgres_avail = get_service_availability()

    if not qdrant_avail or not postgres_avail:
        # Try auto-restart before giving up
        pg_msg = ""
        try:
            from tests.integration.fixtures.container_lifecycle import ensure_container_running

            if not postgres_avail:
                pg_ok, pg_msg = ensure_container_running(
                    "raglite-postgresql-test", POSTGRES_PORT, "PostgreSQL", auto_restart=True
                )
                if pg_ok:
                    print(f"DEBUG: {pg_msg}", file=sys.stderr)
                    postgres_avail = True
                    # Reset cache
                    global postgres_available
                    postgres_available = True

                    # If PostgreSQL was restarted, initialize schema
                    if "restarted" in pg_msg:
                        from tests.integration.fixtures.container_lifecycle import (
                            initialize_test_database_schema,
                        )

                        initialize_test_database_schema()

            if not qdrant_avail:
                qd_ok, qd_msg = ensure_container_running(
                    "raglite-qdrant-test", QDRANT_PORT, "Qdrant", auto_restart=True
                )
                if qd_ok:
                    print(f"DEBUG: {qd_msg}", file=sys.stderr)
                    qdrant_avail = True
                    # Reset cache
                    global qdrant_available
                    qdrant_available = True

        except ImportError:
            # container_lifecycle not available, continue with original behavior
            pass

    if not qdrant_avail or not postgres_avail:
        missing = []
        if not qdrant_avail:
            missing.append(f"Qdrant ({QDRANT_HOST}:{QDRANT_PORT})")
        if not postgres_avail:
            missing.append(f"PostgreSQL ({POSTGRES_HOST}:{POSTGRES_PORT})")

        skip_reason = f"Integration tests require: {', '.join(missing)}"
        print(f"DEBUG: Skipping all integration tests - {skip_reason}", file=sys.stderr)
        pytest.skip(skip_reason, allow_module_level=True)
