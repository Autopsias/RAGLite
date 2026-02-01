"""Embedding model warmup fixture.

Pre-warms the Fin-E5 model before PDF ingestion.
"""

import sys
import time

import pytest

from .service_checking import check_and_skip_if_unavailable
from .test_detection import has_integration_tests, is_postgresql_only_tests


@pytest.fixture(scope="session", autouse=True)
def warmup_embedding_model(request):
    """Pre-warm Fin-E5 model (60-70s) before PDF ingestion. Skipped if --skip-ingestion."""
    if request.config.option.collectonly:
        yield
        return

    # PERFORMANCE FIX (2025-12-18): Skip for unit-only test runs
    # This saves 60-70s and 2GB memory when running only unit tests
    if not has_integration_tests(request):
        print(
            "\n⚡ UNIT TESTS ONLY: Skipping embedding model warmup (saves 60-70s)", file=sys.stderr
        )
        yield
        return

    # PERFORMANCE FIX (2025-12-21): Skip for PostgreSQL-only tests (Story 7b-4)
    # These tests don't need Qdrant or embedding model
    if is_postgresql_only_tests(request):
        print("\n⚡ POSTGRESQL ONLY TESTS: Skipping embedding model warmup", file=sys.stderr)
        yield
        return

    skip_ingestion = request.config.getoption("--skip-ingestion", default=False)
    if skip_ingestion:
        print(
            "\n⚡ SKIP INGESTION MODE: Skipping embedding model warmup (saves 60-70s)",
            file=sys.stderr,
        )
        yield
        return

    check_and_skip_if_unavailable()
    from raglite.shared.clients import get_embedding_model

    model_load_start = time.time()
    model = get_embedding_model()
    model_load_duration = time.time() - model_load_start
    dim = model.get_sentence_embedding_dimension()
    print(
        f"✅ Embedding model ready: {dim} dimensions (Fin-E5 loaded in {model_load_duration:.1f}s)",
        file=sys.stderr,
    )
    print(f"📊 MODEL LOAD PERF: Model loading took {model_load_duration:.1f}s", file=sys.stderr)
    yield
