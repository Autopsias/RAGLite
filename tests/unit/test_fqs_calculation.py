"""Unit tests for FQS (Forecast Quality Score) calculation.

Tests the calculate_fqs() function with various MAPE/MASE combinations.
"""

import pytest

from raglite.forecasting.validation_metrics import calculate_fqs, calculate_system_fqs


class TestCalculateFQS:
    """Test cases for calculate_fqs function."""

    def test_perfect_forecast(self):
        """Perfect forecast (MAPE=0, MASE=0) should give FQS=100."""
        fqs = calculate_fqs(mape=0.0, mase=0.0)
        assert fqs == 100.0

    def test_excellent_forecast(self):
        """Excellent forecast (MAPE=5%, MASE=0.5) should give FQS~79."""
        fqs = calculate_fqs(mape=5.0, mase=0.5)
        # A_MAPE = 1 - 5/100 = 0.95
        # A_MASE = 1 - 0.5/2 = 0.75
        # FQS = 100 * (0.35 * 0.95 + 0.65 * 0.75) = 100 * (0.3325 + 0.4875) = 82.0
        assert fqs == pytest.approx(82.0, rel=0.01)

    def test_good_forecast(self):
        """Good forecast (MAPE=10%, MASE=0.8) should give FQS~72."""
        fqs = calculate_fqs(mape=10.0, mase=0.8)
        # A_MAPE = 1 - 10/100 = 0.90
        # A_MASE = 1 - 0.8/2 = 0.60
        # FQS = 100 * (0.35 * 0.90 + 0.65 * 0.60) = 100 * (0.315 + 0.39) = 70.5
        assert fqs == pytest.approx(70.5, rel=0.01)

    def test_moderate_forecast(self):
        """Moderate forecast (MAPE=20%, MASE=1.0) should give FQS~60.5."""
        fqs = calculate_fqs(mape=20.0, mase=1.0)
        # A_MAPE = 1 - 20/100 = 0.80
        # A_MASE = 1 - 1.0/2 = 0.50
        # FQS = 100 * (0.35 * 0.80 + 0.65 * 0.50) = 100 * (0.28 + 0.325) = 60.5
        assert fqs == pytest.approx(60.5, rel=0.01)

    def test_poor_forecast(self):
        """Poor forecast (MAPE=50%, MASE=2.0) should give FQS~17.5."""
        fqs = calculate_fqs(mape=50.0, mase=2.0)
        # A_MAPE = 1 - 50/100 = 0.50
        # A_MASE = 1 - 2.0/2 = 0.0
        # FQS = 100 * (0.35 * 0.50 + 0.65 * 0.0) = 100 * (0.175 + 0) = 17.5
        assert fqs == pytest.approx(17.5, rel=0.01)

    def test_terrible_forecast(self):
        """Terrible forecast (MAPE=100%, MASE=4.0) should give FQS=0."""
        fqs = calculate_fqs(mape=100.0, mase=4.0)
        # A_MAPE = max(0, 1 - 100/100) = 0
        # A_MASE = max(0, 1 - 4.0/2) = max(0, -1) = 0
        # FQS = 100 * (0.35 * 0 + 0.65 * 0) = 0
        assert fqs == 0.0

    def test_none_inputs(self):
        """Both None inputs should return None."""
        fqs = calculate_fqs(mape=None, mase=None)
        assert fqs is None

    def test_mape_only(self):
        """Only MAPE provided (MASE=None) should use 100% MAPE weight."""
        fqs = calculate_fqs(mape=10.0, mase=None)
        # A_MAPE = 1 - 10/100 = 0.90
        # FQS = 100 * (1.0 * 0.90) = 90.0
        assert fqs == pytest.approx(90.0, rel=0.01)

    def test_mase_only(self):
        """Only MASE provided (MAPE=None) should use 100% MASE weight."""
        fqs = calculate_fqs(mape=None, mase=0.5)
        # A_MASE = 1 - 0.5/2 = 0.75
        # FQS = 100 * (1.0 * 0.75) = 75.0
        assert fqs == pytest.approx(75.0, rel=0.01)

    def test_capped_negative_values(self):
        """Extreme MAPE/MASE values should be capped at 0."""
        fqs = calculate_fqs(mape=150.0, mase=3.0)
        # A_MAPE = max(0, 1 - 150/100) = max(0, -0.5) = 0
        # A_MASE = max(0, 1 - 3.0/2) = max(0, -0.5) = 0
        # FQS = 0
        assert fqs == 0.0

    def test_custom_weights(self):
        """Custom weights (50/50) should balance MAPE and MASE equally."""
        fqs = calculate_fqs(mape=10.0, mase=0.5, w_mape=0.5, w_mase=0.5)
        # A_MAPE = 1 - 10/100 = 0.90
        # A_MASE = 1 - 0.5/2 = 0.75
        # FQS = 100 * (0.5 * 0.90 + 0.5 * 0.75) = 100 * (0.45 + 0.375) = 82.5
        assert fqs == pytest.approx(82.5, rel=0.01)


class TestCalculateSystemFQS:
    """Test cases for calculate_system_fqs function."""

    def test_average_fqs(self):
        """Average FQS should be calculated correctly."""
        results = [
            {"name": "var1", "fqs": 80.0, "data_quality_exempt": False},
            {"name": "var2", "fqs": 60.0, "data_quality_exempt": False},
            {"name": "var3", "fqs": 70.0, "data_quality_exempt": False},
        ]
        system_fqs = calculate_system_fqs(results)
        assert system_fqs["average_fqs"] == pytest.approx(70.0, rel=0.01)
        assert system_fqs["controllable_fqs"] == pytest.approx(70.0, rel=0.01)
        assert system_fqs["min_fqs"] == pytest.approx(60.0, rel=0.01)
        assert system_fqs["max_fqs"] == pytest.approx(80.0, rel=0.01)

    def test_controllable_fqs_excludes_exempt(self):
        """Controllable FQS should exclude data_quality_exempt variables."""
        results = [
            {"name": "var1", "fqs": 80.0, "data_quality_exempt": False},
            {"name": "var2", "fqs": 20.0, "data_quality_exempt": True},  # Exempt
            {"name": "var3", "fqs": 60.0, "data_quality_exempt": False},
        ]
        system_fqs = calculate_system_fqs(results)
        # Average includes all: (80 + 20 + 60) / 3 = 53.33
        assert system_fqs["average_fqs"] == pytest.approx(53.33, rel=0.01)
        # Controllable excludes exempt: (80 + 60) / 2 = 70
        assert system_fqs["controllable_fqs"] == pytest.approx(70.0, rel=0.01)
        assert system_fqs["exempt_variables"] == ["var2"]

    def test_empty_results(self):
        """Empty results should return None for all aggregations."""
        system_fqs = calculate_system_fqs([])
        assert system_fqs["average_fqs"] is None
        assert system_fqs["controllable_fqs"] is None
        assert system_fqs["min_fqs"] is None
        assert system_fqs["max_fqs"] is None

    def test_all_exempt(self):
        """All exempt variables should give controllable_fqs=None."""
        results = [
            {"name": "var1", "fqs": 50.0, "data_quality_exempt": True},
            {"name": "var2", "fqs": 40.0, "data_quality_exempt": True},
        ]
        system_fqs = calculate_system_fqs(results)
        assert system_fqs["average_fqs"] == pytest.approx(45.0, rel=0.01)
        assert system_fqs["controllable_fqs"] is None
        assert system_fqs["exempt_variables"] == ["var1", "var2"]

    def test_none_fqs_skipped(self):
        """Variables with None FQS should be skipped."""
        results = [
            {"name": "var1", "fqs": 80.0, "data_quality_exempt": False},
            {"name": "var2", "fqs": None, "data_quality_exempt": False},
            {"name": "var3", "fqs": 60.0, "data_quality_exempt": False},
        ]
        system_fqs = calculate_system_fqs(results)
        # Average: (80 + 60) / 2 = 70 (var2 skipped)
        assert system_fqs["average_fqs"] == pytest.approx(70.0, rel=0.01)
