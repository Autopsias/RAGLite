"""Tests for per-period error calculation."""

import pytest

from tests.validation.forecast_accuracy.validator import ForecastAccuracyValidator


@pytest.fixture
def validator() -> ForecastAccuracyValidator:
    """Create validator instance for tests."""
    return ForecastAccuracyValidator(threshold_pct=15.0)


class TestPerPeriodErrors:
    """Tests for per-period error calculation."""

    def test_per_period_errors_basic(self, validator: ForecastAccuracyValidator):
        """Test per-period error calculation."""
        actuals = [100.0, 200.0, 150.0]
        predictions = [110.0, 180.0, 150.0]

        errors = validator.get_per_period_errors(actuals, predictions)

        assert len(errors) == 3
        assert errors[0] == pytest.approx(10.0)  # 10% error
        assert errors[1] == pytest.approx(10.0)  # 10% error
        assert errors[2] == pytest.approx(0.0)  # 0% error
