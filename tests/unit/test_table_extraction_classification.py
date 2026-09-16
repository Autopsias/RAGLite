"""Tests for header classification (June 2025 fix).

These tests validate the fix for the June 2025 PDF extraction bug where
'Currency (1000 EUR)' was misclassified as METRIC due to the 'currency'
pattern in metric_patterns.
"""


class TestHeaderClassification:
    """Tests for header classification (June 2025 fix).

    These tests validate the fix for the June 2025 PDF extraction bug where
    'Currency (1000 EUR)' was misclassified as METRIC due to the 'currency'
    pattern in metric_patterns.
    """

    def test_currency_with_unit_is_unknown(self):
        """Test that 'Currency (1000 EUR)' is classified as UNKNOWN, not METRIC.

        This is the root cause of the June 2025 PDF extraction bug where
        'Currency (1000 EUR)' was misclassified as METRIC due to the
        'currency' pattern in metric_patterns.
        """
        from raglite.ingestion.adaptive_table.classification import HeaderType, classify_header

        result = classify_header("Currency (1000 EUR)")
        assert result == HeaderType.UNKNOWN, (
            f"Expected UNKNOWN for unit descriptor, got {result}. "
            "Unit descriptors should not be classified as METRIC."
        )

    def test_currency_exchange_rate_is_metric(self):
        """Test that 'Currency Exchange Rate' is still classified as METRIC.

        This ensures the fix doesn't break legitimate currency-related metrics.
        """
        from raglite.ingestion.adaptive_table.classification import HeaderType, classify_header

        result = classify_header("Currency Exchange Rate")
        assert result == HeaderType.METRIC, (
            f"Expected METRIC for currency exchange rate, got {result}. "
            "The fix should not break legitimate metric classification."
        )

    def test_unit_descriptors_are_unknown(self):
        """Test that various unit descriptors are classified as UNKNOWN."""
        from raglite.ingestion.adaptive_table.classification import HeaderType, classify_header

        unit_descriptors = [
            "Currency (1000 EUR)",
            "Currency (EUR million)",
            "1000 EUR",
            "1000 USD",
            "Unit",
            "Units",
            "UOM",
        ]

        for descriptor in unit_descriptors:
            result = classify_header(descriptor)
            assert result == HeaderType.UNKNOWN, (
                f"Expected UNKNOWN for unit descriptor '{descriptor}', got {result}"
            )
