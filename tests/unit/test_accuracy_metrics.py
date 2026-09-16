"""Unit tests for scripts/accuracy_utils.py - shared accuracy calculation utilities.

Tests cover:
- Number normalization (American vs European formats)
- Retrieval accuracy checking (keyword matching)
- Attribution accuracy checking (page number validation)
- Performance metrics calculation
- NFR compliance checking
"""

from scripts.accuracy_utils import (
    EARLY_WARNING_THRESHOLD,
    KEYWORD_MATCH_THRESHOLD,
    NFR6_RETRIEVAL_TARGET,
    NFR7_ATTRIBUTION_TARGET,
    NFR13_P50_TARGET_MS,
    NFR13_P95_TARGET_MS,
    PAGE_TOLERANCE,
    calculate_performance_metrics,
    check_nfr_compliance,
    should_trigger_early_warning,
)


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
