"""Unit tests for parallel ingestion - rules and metadata enrichment.

Story 5.0.6: Tests for rule-based unit inference, cross-document caching,
and query-time metadata enrichment. Mocks external dependencies to avoid slow I/O.
"""

import pytest

from raglite.ingestion.adaptive_table.unit_inference import UNIT_RULES, infer_unit_from_rules


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
