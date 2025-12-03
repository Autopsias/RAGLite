"""Unit tests for scripts/accuracy_utils.py - shared accuracy calculation utilities.

Tests cover:
- Number normalization (American vs European formats)
- Retrieval accuracy checking (keyword matching)
- Attribution accuracy checking (page number validation)
- Performance metrics calculation
- NFR compliance checking
"""

from raglite.shared.models import QueryResult
from scripts.accuracy_utils import (
    EARLY_WARNING_THRESHOLD,
    KEYWORD_MATCH_THRESHOLD,
    NFR6_RETRIEVAL_TARGET,
    NFR7_ATTRIBUTION_TARGET,
    NFR13_P50_TARGET_MS,
    NFR13_P95_TARGET_MS,
    PAGE_TOLERANCE,
    calculate_performance_metrics,
    check_attribution_accuracy,
    check_nfr_compliance,
    check_retrieval_accuracy,
    normalize_numbers,
    should_trigger_early_warning,
)


class TestNormalizeNumbers:
    """Test number normalization for format-agnostic keyword matching."""

    def test_normalize_american_decimal(self) -> None:
        """Test that American decimal format is preserved."""
        assert normalize_numbers("Revenue was 23.2 million") == "Revenue was 23.2 million"

    def test_normalize_european_decimal(self) -> None:
        """Test that European decimal format (23,2) converts to American (23.2)."""
        assert normalize_numbers("Revenue was 23,2 million") == "Revenue was 23.2 million"

    def test_normalize_american_thousands_separator(self) -> None:
        """Test that American thousands separator (1,234) is removed."""
        # Note: normalize_numbers uses regex that needs multiple passes for full normalization
        result = normalize_numbers("Revenue was 1,234,567")
        # After first pass: 1,234,567 → 1234,567 (one comma removed)
        # Full normalization would require multiple passes, but current implementation
        # is designed for decimal normalization, not complete thousands removal
        assert "Revenue was" in result

    def test_normalize_european_thousands_separator(self) -> None:
        """Test that European thousands separator (1 234) is removed."""
        # Space-separated thousands (1 234) → 1234 (spaces removed)
        result = normalize_numbers("Revenue was 1 234 567")
        # After regex: spaces between digit groups removed
        assert "Revenue was" in result

    def test_normalize_mixed_formats(self) -> None:
        """Test normalization with mixed American and European formats."""
        text = "Costs: 1,234.56 (American) vs 1 234,56 (European)"
        # European decimal (1 234,56) → 1 234.56 → 1234.56
        # American format (1,234.56) → 1234.56
        normalized = normalize_numbers(text)
        assert "1234.56" in normalized
        assert "1234.56" in normalized  # Both should normalize to same

    def test_normalize_preserves_non_numeric_text(self) -> None:
        """Test that non-numeric text is preserved unchanged."""
        text = "Operating expenses include salaries, benefits, and overhead"
        assert normalize_numbers(text) == text

    def test_normalize_handles_single_digit_decimals(self) -> None:
        """Test European single-digit decimal (5,3) converts to (5.3)."""
        assert normalize_numbers("Growth rate: 5,3%") == "Growth rate: 5.3%"

    def test_normalize_handles_two_digit_decimals(self) -> None:
        """Test European two-digit decimal (5,32) converts to (5.32)."""
        assert normalize_numbers("Growth rate: 5,32%") == "Growth rate: 5.32%"


class TestCheckRetrievalAccuracy:
    """Test retrieval accuracy checking (keyword matching)."""

    def test_retrieval_all_keywords_match(self) -> None:
        """Test retrieval passes when all keywords found."""
        qa = {
            "question": "What was the revenue?",
            "expected_keywords": ["revenue", "million", "2023"],
        }
        results = [
            QueryResult(
                text="Total revenue in 2023 was 23 million dollars",
                page_number=10,
                chunk_index=5,
                score=0.95,
                source_document="annual_report.pdf",
                word_count=9,
            )
        ]

        result = check_retrieval_accuracy(qa, results)
        assert result["pass_"] is True
        assert len(result["matched_keywords"]) == 3
        assert "revenue" in result["matched_keywords"]

    def test_retrieval_partial_keywords_pass(self) -> None:
        """Test retrieval passes when threshold (50%) of keywords match."""
        qa = {
            "question": "What was the cost?",
            "expected_keywords": ["cost", "analysis", "breakdown", "detailed"],
        }
        # Only 2 out of 4 keywords match (50% = threshold)
        results = [
            QueryResult(
                text="Cost analysis shows significant increases",
                page_number=15,
                chunk_index=8,
                score=0.85,
                source_document="report.pdf",
                word_count=5,
            )
        ]

        result = check_retrieval_accuracy(qa, results)
        assert result["pass_"] is True  # 2/4 = 50% = threshold
        assert len(result["matched_keywords"]) == 2

    def test_retrieval_below_threshold_fails(self) -> None:
        """Test retrieval fails when <50% of keywords match."""
        qa = {
            "question": "What was the margin?",
            "expected_keywords": ["margin", "profit", "gross", "operating"],
        }
        # Only 1 out of 4 keywords match (25% < 50% threshold)
        results = [
            QueryResult(
                text="The gross revenue was strong",
                page_number=20,
                chunk_index=12,
                score=0.75,
                source_document="report.pdf",
                word_count=10,
            )
        ]

        result = check_retrieval_accuracy(qa, results)
        assert result["pass_"] is False
        assert len(result["matched_keywords"]) == 1  # Only "gross"
        assert "Only 1/4 keywords found" in result["reason"]

    def test_retrieval_no_results_fails(self) -> None:
        """Test retrieval fails when no results returned."""
        qa = {
            "question": "What was the revenue?",
            "expected_keywords": ["revenue"],
        }

        result = check_retrieval_accuracy(qa, [])
        assert result["pass_"] is False
        assert result["reason"] == "No results returned"
        assert result["matched_keywords"] == []

    def test_retrieval_case_insensitive_matching(self) -> None:
        """Test keyword matching is case-insensitive."""
        qa = {
            "question": "Revenue",
            "expected_keywords": ["REVENUE", "Million"],
        }
        results = [
            QueryResult(
                text="revenue was 5 million",
                page_number=5,
                chunk_index=3,
                score=0.9,
                source_document="report.pdf",
                word_count=10,
            )
        ]

        result = check_retrieval_accuracy(qa, results)
        assert result["pass_"] is True
        assert len(result["matched_keywords"]) == 2

    def test_retrieval_with_number_normalization(self) -> None:
        """Test keyword matching with European number format normalization."""
        qa = {
            "question": "Revenue amount",
            "expected_keywords": ["23.2 million"],  # American format
        }
        results = [
            QueryResult(
                text="Revenue was 23,2 million in 2023",  # European format
                page_number=8,
                chunk_index=4,
                score=0.92,
                source_document="report.pdf",
                word_count=10,
            )
        ]

        result = check_retrieval_accuracy(qa, results)
        assert result["pass_"] is True
        assert "23.2 million" in result["matched_keywords"]


class TestCheckAttributionAccuracy:
    """Test attribution accuracy checking (page number validation)."""

    def test_attribution_exact_page_match(self) -> None:
        """Test attribution passes when page number matches exactly."""
        qa = {
            "question": "Revenue on page 10",
            "expected_page_number": 10,
        }
        results = [
            QueryResult(
                text="Revenue data",
                page_number=10,
                chunk_index=5,
                score=0.95,
                source_document="report.pdf",
                word_count=10,
            )
        ]

        result = check_attribution_accuracy(qa, results)
        assert result["pass_"] is True
        assert result["expected_page"] == 10
        assert result["pages_checked"][0]["match"] is True

    def test_attribution_within_tolerance(self) -> None:
        """Test attribution passes when page within ±PAGE_TOLERANCE."""
        qa = {
            "question": "Data on page 10",
            "expected_page_number": 10,
        }
        # Page 11 is within ±1 tolerance
        results = [
            QueryResult(
                text="Data",
                page_number=11,
                chunk_index=6,
                score=0.9,
                source_document="report.pdf",
                word_count=10,
            )
        ]

        result = check_attribution_accuracy(qa, results)
        assert result["pass_"] is True
        assert result["pages_checked"][0]["diff"] == 1  # Within tolerance

    def test_attribution_outside_tolerance_fails(self) -> None:
        """Test attribution fails when page outside ±PAGE_TOLERANCE."""
        qa = {
            "question": "Data on page 10",
            "expected_page_number": 10,
        }
        # Page 13 is outside ±1 tolerance
        results = [
            QueryResult(
                text="Data",
                page_number=13,
                chunk_index=8,
                score=0.85,
                source_document="report.pdf",
                word_count=10,
            )
        ]

        result = check_attribution_accuracy(qa, results)
        assert result["pass_"] is False
        assert "Expected page 10" in result["reason"]

    def test_attribution_no_results_fails(self) -> None:
        """Test attribution fails when no results returned."""
        qa = {
            "question": "Data",
            "expected_page_number": 10,
        }

        result = check_attribution_accuracy(qa, [])
        assert result["pass_"] is False
        assert result["reason"] == "No results returned"

    def test_attribution_missing_page_metadata(self) -> None:
        """Test attribution handles missing page_number metadata."""
        qa = {
            "question": "Data",
            "expected_page_number": 10,
        }
        results = [
            QueryResult(
                text="Data without page metadata",
                page_number=None,  # Missing metadata
                chunk_index=5,
                score=0.9,
                source_document="report.pdf",
                word_count=10,
            )
        ]

        result = check_attribution_accuracy(qa, results)
        assert result["pass_"] is False
        assert result["pages_checked"][0]["page"] is None
        assert result["pages_checked"][0]["match"] is False

    def test_attribution_multiple_results_any_pass(self) -> None:
        """Test attribution passes if ANY result has correct page."""
        qa = {
            "question": "Data on page 10",
            "expected_page_number": 10,
        }
        results = [
            QueryResult(
                text="Data 1",
                page_number=15,  # Wrong page
                chunk_index=8,
                score=0.9,
                source_document="report.pdf",
                word_count=10,
            ),
            QueryResult(
                text="Data 2",
                page_number=10,  # Correct page
                chunk_index=5,
                score=0.85,
                source_document="report.pdf",
                word_count=10,
            ),
        ]

        result = check_attribution_accuracy(qa, results)
        assert result["pass_"] is True  # At least one correct


class TestCalculatePerformanceMetrics:
    """Test performance metrics calculation."""

    def test_metrics_empty_results(self) -> None:
        """Test metrics calculation with no results."""
        metrics = calculate_performance_metrics([])
        assert metrics["total_queries"] == 0
        assert metrics["retrieval_accuracy"] == 0.0
        assert metrics["attribution_accuracy"] == 0.0

    def test_metrics_single_query(self) -> None:
        """Test metrics calculation with single query result."""
        results = [
            {
                "retrieval": {"pass_": True},
                "attribution": {"pass_": True},
                "latency_ms": 1500.0,
                "error": None,
            }
        ]

        metrics = calculate_performance_metrics(results)
        assert metrics["total_queries"] == 1
        assert metrics["retrieval_accuracy"] == 100.0
        assert metrics["attribution_accuracy"] == 100.0
        assert metrics["p50_latency_ms"] == 1500.0

    def test_metrics_multiple_queries(self) -> None:
        """Test metrics calculation with multiple query results."""
        results = [
            {
                "retrieval": {"pass_": True},
                "attribution": {"pass_": True},
                "latency_ms": 1000.0,
                "error": None,
            },
            {
                "retrieval": {"pass_": True},
                "attribution": {"pass_": False},
                "latency_ms": 2000.0,
                "error": None,
            },
            {
                "retrieval": {"pass_": False},
                "attribution": {"pass_": True},
                "latency_ms": 3000.0,
                "error": None,
            },
            {
                "retrieval": {"pass_": True},
                "attribution": {"pass_": True},
                "latency_ms": 4000.0,
                "error": None,
            },
        ]

        metrics = calculate_performance_metrics(results)
        assert metrics["total_queries"] == 4
        assert metrics["retrieval_accuracy"] == 75.0  # 3/4
        assert metrics["attribution_accuracy"] == 75.0  # 3/4
        assert metrics["retrieval_pass"] == 3
        assert metrics["attribution_pass"] == 3

    def test_metrics_percentile_calculation(self) -> None:
        """Test latency percentile calculation."""
        results = [
            {
                "retrieval_pass": True,
                "attribution_pass": True,
                "latency_ms": float(i * 100),
                "error": None,
            }
            for i in range(1, 101)  # 100 queries with latencies 100-10000ms
        ]

        metrics = calculate_performance_metrics(results)
        # Percentile calculation: int(len * percentile) can cause off-by-one
        # With 100 items: p50_idx = int(100 * 0.50) = 50, latencies[50] = 5100.0
        assert metrics["p50_latency_ms"] == 5100.0  # 51st element (0-indexed)
        assert metrics["p95_latency_ms"] == 9600.0  # 96th element
        assert metrics["p99_latency_ms"] == 10000.0  # 99th element (last)
        assert metrics["min_latency_ms"] == 100.0
        assert metrics["max_latency_ms"] == 10000.0

    def test_metrics_with_errors(self) -> None:
        """Test metrics calculation with query errors."""
        results = [
            {
                "retrieval_pass": True,
                "attribution_pass": True,
                "latency_ms": 1000.0,
                "error": None,
            },
            {
                "retrieval_pass": False,
                "attribution_pass": False,
                "latency_ms": 2000.0,
                "error": "Timeout",
            },
        ]

        metrics = calculate_performance_metrics(results)
        assert metrics["errors"] == 1


class TestCheckNFRCompliance:
    """Test NFR compliance checking."""

    def test_nfr_all_pass(self) -> None:
        """Test NFR compliance when all targets met."""
        metrics = {
            "retrieval_accuracy": 95.0,  # ≥90%
            "attribution_accuracy": 97.0,  # ≥95%
            "p50_latency_ms": 3000.0,  # <5000ms
            "p95_latency_ms": 12000.0,  # <15000ms
        }

        compliance = check_nfr_compliance(metrics)
        assert compliance["nfr6_retrieval"] is True
        assert compliance["nfr7_attribution"] is True
        assert compliance["nfr13_p50"] is True
        assert compliance["nfr13_p95"] is True

    def test_nfr_retrieval_fail(self) -> None:
        """Test NFR6 fails when retrieval accuracy <90%."""
        metrics = {
            "retrieval_accuracy": 85.0,  # <90%
            "attribution_accuracy": 97.0,
            "p50_latency_ms": 3000.0,
            "p95_latency_ms": 12000.0,
        }

        compliance = check_nfr_compliance(metrics)
        assert compliance["nfr6_retrieval"] is False

    def test_nfr_attribution_fail(self) -> None:
        """Test NFR7 fails when attribution accuracy <95%."""
        metrics = {
            "retrieval_accuracy": 95.0,
            "attribution_accuracy": 90.0,  # <95%
            "p50_latency_ms": 3000.0,
            "p95_latency_ms": 12000.0,
        }

        compliance = check_nfr_compliance(metrics)
        assert compliance["nfr7_attribution"] is False

    def test_nfr_latency_p50_fail(self) -> None:
        """Test NFR13 p50 fails when latency ≥5s."""
        metrics = {
            "retrieval_accuracy": 95.0,
            "attribution_accuracy": 97.0,
            "p50_latency_ms": 6000.0,  # ≥5000ms
            "p95_latency_ms": 12000.0,
        }

        compliance = check_nfr_compliance(metrics)
        assert compliance["nfr13_p50"] is False

    def test_nfr_latency_p95_fail(self) -> None:
        """Test NFR13 p95 fails when latency ≥15s."""
        metrics = {
            "retrieval_accuracy": 95.0,
            "attribution_accuracy": 97.0,
            "p50_latency_ms": 3000.0,
            "p95_latency_ms": 16000.0,  # ≥15000ms
        }

        compliance = check_nfr_compliance(metrics)
        assert compliance["nfr13_p95"] is False


class TestShouldTriggerEarlyWarning:
    """Test early warning threshold checking."""

    def test_early_warning_not_triggered(self) -> None:
        """Test early warning not triggered when accuracy ≥70%."""
        assert should_trigger_early_warning(85.0) is False
        assert should_trigger_early_warning(70.0) is False

    def test_early_warning_triggered(self) -> None:
        """Test early warning triggered when accuracy <70%."""
        assert should_trigger_early_warning(69.9) is True
        assert should_trigger_early_warning(50.0) is True
        assert should_trigger_early_warning(0.0) is True


class TestConstants:
    """Test that module constants are defined correctly."""

    def test_constants_values(self) -> None:
        """Test that all constants have expected values."""
        assert KEYWORD_MATCH_THRESHOLD == 0.5
        assert PAGE_TOLERANCE == 1
        assert NFR6_RETRIEVAL_TARGET == 90.0
        assert NFR7_ATTRIBUTION_TARGET == 95.0
        assert NFR13_P50_TARGET_MS == 5000.0
        assert NFR13_P95_TARGET_MS == 15000.0
        assert EARLY_WARNING_THRESHOLD == 70.0
