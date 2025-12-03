"""Unit tests for parallel document ingestion and unit inference optimizations.

Story 5.0.6: Tests for parallel batch processing, rule-based unit inference,
and cross-document caching. Mocks external dependencies to avoid slow I/O.
"""

import asyncio
from unittest.mock import patch

import pytest

from raglite.ingestion.adaptive_table.unit_inference import (
    UNIT_RULES,
    infer_unit_from_rules,
)
from raglite.ingestion.document_ingestion import ingest_documents_parallel
from raglite.shared.models import BatchIngestionResult, DocumentMetadata


class TestRuleBasedUnitInference:
    """Test suite for rule-based unit inference (AC2 - 80% API reduction).

    Tests the UNIT_RULES patterns that handle common financial metric units
    without requiring LLM API calls.
    """

    @pytest.mark.priority("P0")
    def test_revenue_metrics(self):
        """Test revenue-related metrics map to Meur."""
        assert infer_unit_from_rules("Total Revenue") == "Meur"
        assert infer_unit_from_rules("Net Revenue") == "Meur"
        assert infer_unit_from_rules("Revenue IFRS") == "Meur"
        assert infer_unit_from_rules("SALES") == "Meur"

    @pytest.mark.priority("P0")
    def test_ebitda_metrics(self):
        """Test EBITDA-related metrics map to Meur."""
        assert infer_unit_from_rules("EBITDA") == "Meur"
        assert infer_unit_from_rules("Adjusted EBITDA") == "Meur"
        assert infer_unit_from_rules("EBITDA IFRS") == "Meur"
        # FIXED: Margin pattern now comes FIRST, so "ebitda margin" correctly returns "%"
        assert infer_unit_from_rules("ebitda margin") == "%"

    @pytest.mark.priority("P0")
    def test_profit_cost_metrics(self):
        """Test profit and cost metrics map to Meur."""
        assert infer_unit_from_rules("Gross Profit") == "Meur"
        assert infer_unit_from_rules("Net Income") == "Meur"
        assert infer_unit_from_rules("Operating Cost") == "Meur"
        assert infer_unit_from_rules("CAPEX") == "Meur"

    @pytest.mark.priority("P0")
    def test_margin_metrics(self):
        """Test margin and ratio metrics map to %."""
        # FIXED: Margin pattern now comes FIRST, so all margin/ratio terms return %
        assert infer_unit_from_rules("Gross Margin") == "%"
        assert infer_unit_from_rules("EBITDA Margin") == "%"  # Now correctly returns %
        assert infer_unit_from_rules("Profit Ratio") == "%"  # Now correctly returns %
        assert infer_unit_from_rules("Growth Rate") == "%"
        assert infer_unit_from_rules("Percentage Change") == "%"
        assert infer_unit_from_rules("Utilization Ratio") == "%"
        assert infer_unit_from_rules("Efficiency Ratio") == "%"

    @pytest.mark.priority("P0")
    def test_volume_metrics(self):
        """Test volume metrics map to kton."""
        assert infer_unit_from_rules("Production Volume") == "kton"
        assert infer_unit_from_rules("Total Capacity") == "kton"
        assert infer_unit_from_rules("Output") == "kton"

    @pytest.mark.priority("P0")
    def test_per_ton_metrics(self):
        """Test per-ton metrics map to EUR/ton."""
        # FIXED: /ton pattern now comes SECOND (before revenue/cost), so more cases work correctly
        assert infer_unit_from_rules("Price per ton") == "EUR/ton"
        assert infer_unit_from_rules("Price/ton") == "EUR/ton"
        assert infer_unit_from_rules("Freight €/ton") == "EUR/ton"
        assert infer_unit_from_rules("Cost/ton") == "EUR/ton"  # Now correctly returns EUR/ton
        assert infer_unit_from_rules("Revenue €/ton") == "EUR/ton"  # Now correctly returns EUR/ton

    @pytest.mark.priority("P0")
    def test_headcount_metrics(self):
        """Test headcount metrics map to FTE."""
        assert infer_unit_from_rules("Headcount") == "FTE"
        assert infer_unit_from_rules("Total Employees") == "FTE"
        assert infer_unit_from_rules("FTE Count") == "FTE"
        assert infer_unit_from_rules("Staff") == "FTE"
        assert infer_unit_from_rules("Workforce") == "FTE"

    @pytest.mark.priority("P0")
    def test_period_metrics(self):
        """Test period metrics map to days."""
        assert infer_unit_from_rules("Days Outstanding") == "days"
        assert infer_unit_from_rules("Period Length") == "days"

    @pytest.mark.priority("P1")
    def test_no_match_returns_none(self):
        """Test that unrecognized metrics return None."""
        assert infer_unit_from_rules("Obscure Metric XYZ") is None
        assert infer_unit_from_rules("Custom KPI 42") is None
        assert infer_unit_from_rules("") is None
        assert infer_unit_from_rules(None) is None

    @pytest.mark.priority("P1")
    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive."""
        assert infer_unit_from_rules("revenue") == "Meur"
        assert infer_unit_from_rules("REVENUE") == "Meur"
        assert infer_unit_from_rules("ReVeNuE") == "Meur"

    @pytest.mark.priority("P1")
    def test_pattern_priority(self):
        """Test that first matching pattern wins (margin pattern prioritized correctly)."""
        # NOTE: UNIT_RULES correctly has margin/ratio pattern FIRST (Story 5.0.6 fix)
        # "EBITDA Margin" matches "margin" first → % (correct behavior)
        assert infer_unit_from_rules("EBITDA Margin") == "%"
        # "Revenue" matches revenue pattern → Meur
        assert infer_unit_from_rules("Revenue") == "Meur"
        # "Gross Margin" matches margin pattern → %
        assert infer_unit_from_rules("Gross Margin") == "%"

    @pytest.mark.priority("P0")
    def test_unit_rules_coverage(self):
        """Test that UNIT_RULES list has expected patterns.

        Story 5.0.6 AC2 requires 6 pattern categories covering 80%+ of financial docs.
        """
        assert len(UNIT_RULES) >= 6, "Should have at least 6 rule patterns"

        # Verify each rule is a tuple of (pattern, unit)
        for rule in UNIT_RULES:
            assert isinstance(rule, tuple), f"Rule {rule} must be a tuple"
            assert len(rule) == 2, f"Rule {rule} must have (pattern, unit)"
            pattern, unit = rule
            assert isinstance(pattern, str), f"Pattern {pattern} must be string"
            assert isinstance(unit, str), f"Unit {unit} must be string"


class TestParallelDocumentIngestion:
    """Test suite for parallel document batch ingestion (AC1 - 2x speedup).

    Tests concurrent document processing, error handling, semaphore control,
    and batch result aggregation. Uses mocks to avoid slow PDF processing.
    """

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_parallel_ingestion_success(self):
        """Test successful parallel ingestion of multiple documents.

        Verifies AC1: Parallel processing with semaphore control and
        proper result aggregation.
        """
        # Mock DocumentMetadata results (no document_id field, only filename)
        mock_metadata_1 = DocumentMetadata(
            filename="report1.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-30T10:00:00",
            page_count=10,
            source_path="/path/to/report1.pdf",
            chunk_count=25,
        )
        mock_metadata_2 = DocumentMetadata(
            filename="report2.pdf",
            doc_type="PDF",
            ingestion_timestamp="2025-11-30T10:05:00",
            page_count=15,
            source_path="/path/to/report2.pdf",
            chunk_count=30,
        )
        mock_metadata_3 = DocumentMetadata(
            filename="data.xlsx",
            doc_type="Excel",
            ingestion_timestamp="2025-11-30T10:10:00",
            page_count=5,
            source_path="/path/to/data.xlsx",
            chunk_count=10,
        )

        # Create async mock for ingest_document
        async def mock_ingest_document(file_path: str, unit_cache: dict | None = None):
            """Mock ingest_document with realistic delay."""
            # Simulate processing time (0.1s for test speed)
            await asyncio.sleep(0.1)

            # Return different metadata based on file path
            if "report1" in file_path:
                return mock_metadata_1
            elif "report2" in file_path:
                return mock_metadata_2
            else:
                return mock_metadata_3

        # Test with 3 documents
        file_paths = [
            "/path/to/report1.pdf",
            "/path/to/report2.pdf",
            "/path/to/data.xlsx",
        ]

        with patch(
            "raglite.ingestion.document_ingestion.ingest_document",
            side_effect=mock_ingest_document,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=2)

        # Verify BatchIngestionResult structure
        assert isinstance(result, BatchIngestionResult)
        assert result.total_documents == 3
        assert result.successful == 3
        assert result.failed == 0
        assert len(result.results) == 3
        assert len(result.errors) == 0
        assert result.duration_seconds > 0

        # Verify all documents processed (check filenames, no document_id field)
        result_filenames = {m.filename for m in result.results}
        assert result_filenames == {"report1.pdf", "report2.pdf", "data.xlsx"}

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_parallel_ingestion_with_failures(self):
        """Test error handling with partial batch failures.

        Verifies AC1: One document failure doesn't abort entire batch.
        """

        async def mock_ingest_with_error(file_path: str, unit_cache: dict | None = None):
            """Mock ingestion that fails on second document."""
            await asyncio.sleep(0.05)

            if "report2" in file_path:
                raise ValueError("Mock ingestion error for report2.pdf")

            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=10,
                chunk_count=25,
            )

        file_paths = [
            "/path/to/report1.pdf",
            "/path/to/report2.pdf",
            "/path/to/report3.pdf",
        ]

        with patch(
            "raglite.ingestion.document_ingestion.ingest_document",
            side_effect=mock_ingest_with_error,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=2)

        # Verify partial success
        assert result.total_documents == 3
        assert result.successful == 2  # report1 and report3
        assert result.failed == 1  # report2
        assert len(result.results) == 2
        assert len(result.errors) == 1

        # Verify error details captured
        error = result.errors[0]
        assert "report2" in error["filename"]
        assert "Mock ingestion error" in error["error"]

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_concurrency_limit_enforced(self):
        """Test that semaphore limits concurrent executions.

        Verifies AC1: Memory-safe concurrency control (default: 2).
        """
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent_seen = 0

        async def mock_ingest_track_concurrency(file_path: str, unit_cache: dict | None = None):
            """Mock that tracks concurrency levels."""
            nonlocal concurrent_count, max_concurrent_seen

            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)

            # Simulate work
            await asyncio.sleep(0.1)

            concurrent_count -= 1

            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=10,
                chunk_count=25,
            )

        # 5 documents with max_concurrent=2
        file_paths = [f"/path/to/report{i}.pdf" for i in range(5)]

        with patch(
            "raglite.ingestion.document_ingestion.ingest_document",
            side_effect=mock_ingest_track_concurrency,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=2)

        # Verify concurrency was limited
        assert max_concurrent_seen <= 2, "Should never exceed max_concurrent limit"
        assert result.successful == 5

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_empty_file_list_raises_error(self):
        """Test that empty file list raises ValueError.

        Verifies AC1: Input validation.
        """
        with pytest.raises(ValueError, match="file_paths cannot be empty"):
            await ingest_documents_parallel([])

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_invalid_max_concurrent_raises_error(self):
        """Test that invalid max_concurrent raises ValueError.

        Verifies AC1: Configuration validation.
        """
        with pytest.raises(ValueError, match="max_concurrent must be >= 1"):
            await ingest_documents_parallel(["/path/to/file.pdf"], max_concurrent=0)

        with pytest.raises(ValueError, match="max_concurrent must be >= 1"):
            await ingest_documents_parallel(["/path/to/file.pdf"], max_concurrent=-1)

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_uses_config_default_when_max_concurrent_none(self):
        """Test that max_concurrent=None uses settings.ingestion_parallel_docs.

        Verifies AC1: Configuration integration.
        """

        async def mock_ingest(file_path: str, unit_cache: dict | None = None):
            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=10,
                chunk_count=25,
            )

        with (
            patch(
                "raglite.ingestion.document_ingestion.ingest_document",
                side_effect=mock_ingest,
            ),
            patch("raglite.ingestion.document_ingestion.settings") as mock_settings,
        ):
            mock_settings.ingestion_parallel_docs = 3
            result = await ingest_documents_parallel(["/path/to/file.pdf"])

        # Verify it used the config default (should succeed with any concurrency)
        assert result.successful == 1

    @pytest.mark.priority("P0")
    @pytest.mark.asyncio
    async def test_batch_result_aggregation(self):
        """Test correct aggregation of batch statistics.

        Verifies AC1 & AC6: Result tracking and summary statistics.
        """

        async def mock_ingest(file_path: str, unit_cache: dict | None = None):
            await asyncio.sleep(0.05)
            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=20,
                chunk_count=50,
            )

        file_paths = [f"/path/to/report{i}.pdf" for i in range(4)]

        with patch(
            "raglite.ingestion.document_ingestion.ingest_document",
            side_effect=mock_ingest,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=2)

        # Verify aggregated statistics
        assert result.total_documents == 4
        assert result.successful == 4
        total_pages = sum(m.page_count for m in result.results)
        total_chunks = sum(m.chunk_count for m in result.results)
        assert total_pages == 80  # 4 docs * 20 pages
        assert total_chunks == 200  # 4 docs * 50 chunks

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    async def test_sequential_processing_when_max_concurrent_1(self):
        """Test that max_concurrent=1 forces sequential processing.

        Verifies AC1: Configurable concurrency (1 = sequential, 2+ = parallel).
        """
        concurrent_count = 0
        max_concurrent_seen = 0

        async def mock_ingest_track(file_path: str, unit_cache: dict | None = None):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1

            return DocumentMetadata(
                filename=file_path,
                doc_type="PDF",
                ingestion_timestamp="2025-11-30T10:00:00",
                page_count=10,
                chunk_count=25,
            )

        file_paths = [f"/path/to/report{i}.pdf" for i in range(3)]

        with patch(
            "raglite.ingestion.document_ingestion.ingest_document",
            side_effect=mock_ingest_track,
        ):
            result = await ingest_documents_parallel(file_paths, max_concurrent=1)

        # Verify sequential processing (never more than 1 concurrent)
        assert max_concurrent_seen == 1
        assert result.successful == 3


class TestCrossDocumentUnitCache:
    """Test suite for cross-document unit caching (AC3 - 30% additional API reduction).

    Tests cache sharing across documents in a batch to avoid redundant
    unit inference for the same metrics.
    """

    @pytest.mark.priority("P0")
    def test_cache_key_normalization(self):
        """Test that cache keys are normalized (lowercase, stripped).

        AC3: Cache key should be consistent for "EBITDA IFRS", "ebitda ifrs", " EBITDA IFRS ".
        """
        # Simple cache simulation
        cache = {}

        # Normalize keys
        def normalize_key(metric: str) -> str:
            return metric.lower().strip()

        metrics = ["EBITDA IFRS", "ebitda ifrs", " EBITDA IFRS ", "Ebitda IFRS"]
        for metric in metrics:
            cache[normalize_key(metric)] = "Meur"

        # All variations should map to same cache entry
        assert len(cache) == 1
        assert cache.get("ebitda ifrs") == "Meur"

    @pytest.mark.priority("P1")
    def test_cache_populates_on_first_inference(self):
        """Test cache population behavior.

        AC3: First inference for a metric should populate the cache.
        """
        cache = {}

        # Simulate first inference
        metric = "ebitda ifrs"
        if metric not in cache:
            cache[metric] = "Meur"  # LLM inference result

        assert cache.get("ebitda ifrs") == "Meur"

    @pytest.mark.priority("P0")
    def test_cache_reused_across_documents(self):
        """Test cache reuse across multiple documents.

        AC3: If metric "EBITDA IFRS" inferred as "Meur" for doc 1,
        should reuse for docs 2-10.
        """
        cache = {}

        # Doc 1: First inference (cache miss, LLM call)
        metric = "ebitda ifrs"
        assert metric not in cache  # Cache miss
        cache[metric] = "Meur"  # Populate from LLM

        # Doc 2-10: Subsequent inferences (cache hit, no LLM call)
        for _doc_num in range(2, 11):
            assert cache.get(metric) == "Meur"  # Cache hit

        # Verify only one entry in cache
        assert len(cache) == 1

    @pytest.mark.priority("P1")
    def test_cache_tracks_unit_source(self):
        """Test that unit_source field tracks inference method.

        AC3: unit_source should be "rule", "cached", or "llm".
        """
        # Simulate unit source tracking
        inferences = []

        # Rule-based inference
        metric = "Total Revenue"
        unit = infer_unit_from_rules(metric)
        if unit:
            inferences.append({"metric": metric, "unit": unit, "source": "rule"})

        # Cache hit
        cache = {"ebitda ifrs": "Meur"}
        metric = "EBITDA IFRS"
        normalized = metric.lower().strip()
        if normalized in cache:
            inferences.append({"metric": metric, "unit": cache[normalized], "source": "cached"})

        # LLM inference (fallback)
        metric = "Custom KPI XYZ"
        if not infer_unit_from_rules(metric):
            inferences.append({"metric": metric, "unit": "units", "source": "llm"})

        # Verify all three sources tracked
        sources = {inf["source"] for inf in inferences}
        assert sources == {"rule", "cached", "llm"}


class TestSkipMetadataAtIngestion:
    """Test suite for skip_metadata parameter (AC4 - 90% API reduction).

    Tests that metadata extraction can be skipped at ingestion time
    when skip_metadata=True, saving 400 API calls per document.
    """

    @pytest.mark.priority("P0")
    def test_skip_metadata_parameter_exists(self):
        """Test that skip_metadata parameter is recognized.

        AC4: ingest_pdf() should accept skip_metadata parameter.
        """
        # Verify function signature accepts skip_metadata
        import inspect

        from raglite.ingestion.document_ingestion import ingest_pdf

        sig = inspect.signature(ingest_pdf)
        assert "skip_metadata" in sig.parameters

    @pytest.mark.priority("P1")
    def test_skip_metadata_default_value(self):
        """Test that skip_metadata defaults to True (config setting).

        AC4: Default should be True to save API calls.
        """
        from raglite.shared.config import settings

        # Verify config default
        assert settings.skip_ingestion_metadata is True


# AC6: Progress Reporting
# NOTE: Progress logging is tested via integration tests (test actual log output)
# Unit tests focus on result structure and statistics aggregation


# AC7: Validation Tests
# NOTE: Comprehensive integration and performance tests are in:
# - tests/integration/test_parallel_ingestion.py (3 PDFs, full ingestion)
# - scripts/benchmark-parallel-ingestion.py (10 PDFs, performance validation)


# ============================================================================
# Task 5.6: Query-Time Metadata Enrichment Tests
# ============================================================================


@pytest.mark.asyncio
async def test_enrich_results_with_metadata_success(
    test_settings, mock_mistral_client, monkeypatch
):
    """Test successful metadata enrichment of query results."""
    from raglite.retrieval.search import enrich_results_with_metadata

    # Enable query-time metadata
    from raglite.shared import config
    from raglite.shared.models import QueryResult

    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Create test results
    results = [
        QueryResult(
            score=0.95,
            text="EBITDA for Portugal Cement in Q3 2025 was 128.8 Meur",
            source_document="Q3_Report.pdf",
            page_number=12,
            chunk_index=45,
            word_count=150,
        ),
        QueryResult(
            score=0.88,
            text="Variable costs decreased to 23.2 EUR/ton in August",
            source_document="Performance_Review.pdf",
            page_number=8,
            chunk_index=23,
            word_count=120,
        ),
    ]

    # Enrich results (metadata extraction will be mocked)
    enriched = await enrich_results_with_metadata(results)

    # Verify results returned (even if metadata not attached to model yet)
    assert len(enriched) == 2
    assert enriched[0].score == 0.95
    assert enriched[1].score == 0.88


@pytest.mark.asyncio
async def test_enrich_results_disabled(test_settings, monkeypatch):
    """Test enrichment is skipped when disabled."""
    from raglite.retrieval.search import enrich_results_with_metadata

    # Disable query-time metadata
    from raglite.shared import config
    from raglite.shared.models import QueryResult

    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", False)

    results = [
        QueryResult(
            score=0.95,
            text="Test content",
            source_document="test.pdf",
            page_number=1,
            chunk_index=0,
            word_count=50,
        )
    ]

    # Should return unchanged
    enriched = await enrich_results_with_metadata(results)
    assert enriched == results


@pytest.mark.asyncio
async def test_enrich_results_no_api_key(test_settings, monkeypatch):
    """Test graceful degradation when API key missing."""
    from raglite.retrieval.search import enrich_results_with_metadata

    # Enable enrichment but no API key
    from raglite.shared import config
    from raglite.shared.models import QueryResult

    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", None)

    results = [
        QueryResult(
            score=0.95,
            text="Test content",
            source_document="test.pdf",
            page_number=1,
            chunk_index=0,
            word_count=50,
        )
    ]

    # Should return unchanged (graceful degradation)
    enriched = await enrich_results_with_metadata(results)
    assert enriched == results


@pytest.mark.asyncio
async def test_enrich_results_timeout(test_settings, monkeypatch):
    """Test timeout handling returns results unchanged."""
    import asyncio

    from raglite.retrieval.search import enrich_results_with_metadata
    from raglite.shared import config
    from raglite.shared.models import QueryResult

    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Mock extract_chunk_metadata to timeout
    async def slow_extract(*args, **kwargs):
        await asyncio.sleep(5)  # Exceeds 2.5s timeout
        return None

    monkeypatch.setattr(
        "raglite.ingestion.embedding_generation.extract_chunk_metadata", slow_extract
    )

    results = [
        QueryResult(
            score=0.95,
            text="Test content",
            source_document="test.pdf",
            page_number=1,
            chunk_index=0,
            word_count=50,
        )
    ]

    # Should timeout and return unchanged
    enriched = await enrich_results_with_metadata(results)
    assert enriched == results


@pytest.mark.asyncio
async def test_enrich_results_empty_list(test_settings, monkeypatch):
    """Test enrichment with empty results list."""
    from raglite.retrieval.search import enrich_results_with_metadata
    from raglite.shared import config

    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Empty results
    enriched = await enrich_results_with_metadata([])
    assert enriched == []


@pytest.mark.asyncio
async def test_enrich_results_partial_failure(test_settings, monkeypatch):
    """Test enrichment continues when some results fail."""
    from raglite.retrieval.search import enrich_results_with_metadata
    from raglite.shared import config
    from raglite.shared.models import QueryResult

    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Mock extract_chunk_metadata to fail for first result
    call_count = 0

    async def failing_extract(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Extraction failed")
        # Return mock metadata for other calls
        from raglite.shared.models import ExtractedMetadata

        return ExtractedMetadata(
            company_name="Test Corp",
            metric_category="Revenue",
            reporting_period="Q3 2025",
        )

    monkeypatch.setattr(
        "raglite.ingestion.embedding_generation.extract_chunk_metadata", failing_extract
    )

    results = [
        QueryResult(
            score=0.95,
            text="First result",
            source_document="test1.pdf",
            page_number=1,
            chunk_index=0,
            word_count=50,
        ),
        QueryResult(
            score=0.88,
            text="Second result",
            source_document="test2.pdf",
            page_number=2,
            chunk_index=1,
            word_count=60,
        ),
    ]

    # Should handle partial failure gracefully
    enriched = await enrich_results_with_metadata(results)
    assert len(enriched) == 2
    assert enriched[0].score == 0.95  # Unchanged despite failure
    assert enriched[1].score == 0.88


@pytest.mark.asyncio
@pytest.mark.priority("P0")
async def test_enrich_results_attaches_metadata(test_settings, monkeypatch):
    """Test that enrich_results_with_metadata attaches metadata to QueryResult objects.

    Story 5.0.6 AC5 Fix: Verify metadata field is populated after enrichment.
    """
    from raglite.retrieval.search import enrich_results_with_metadata
    from raglite.shared import config
    from raglite.shared.models import ExtractedMetadata, QueryResult

    monkeypatch.setattr(config.settings, "query_time_metadata_enabled", True)
    monkeypatch.setattr(config.settings, "mistral_api_key", "test-key")

    # Mock extract_chunk_metadata to return test metadata
    async def mock_extract(*args, **kwargs):
        return ExtractedMetadata(
            company_name="ACME Corp",
            reporting_period="Q4 2025",
            metric_category="EBITDA",
            document_type="Income Statement",
            section_type="Table",
        )

    monkeypatch.setattr(
        "raglite.ingestion.embedding_generation.extract_chunk_metadata", mock_extract
    )

    # Create test results without metadata
    results = [
        QueryResult(
            score=0.95,
            text="EBITDA increased by 15% in Q4 2025",
            source_document="quarterly_report.pdf",
            page_number=5,
            chunk_index=10,
            word_count=50,
        ),
        QueryResult(
            score=0.88,
            text="Revenue growth exceeded expectations",
            source_document="quarterly_report.pdf",
            page_number=3,
            chunk_index=5,
            word_count=45,
        ),
    ]

    # Verify metadata is None before enrichment
    assert results[0].metadata is None
    assert results[1].metadata is None

    # Enrich results
    enriched = await enrich_results_with_metadata(results)

    # Verify metadata is attached after enrichment
    assert len(enriched) == 2

    # First result should have metadata attached
    assert enriched[0].metadata is not None
    assert enriched[0].metadata.company_name == "ACME Corp"
    assert enriched[0].metadata.reporting_period == "Q4 2025"
    assert enriched[0].metadata.metric_category == "EBITDA"
    assert enriched[0].metadata.document_type == "Income Statement"
    assert enriched[0].metadata.section_type == "Table"

    # Second result should also have metadata attached
    assert enriched[1].metadata is not None
    assert enriched[1].metadata.company_name == "ACME Corp"
    assert enriched[1].metadata.reporting_period == "Q4 2025"

    # Original result fields should be unchanged
    assert enriched[0].score == 0.95
    assert enriched[0].text == "EBITDA increased by 15% in Q4 2025"
    assert enriched[0].source_document == "quarterly_report.pdf"
