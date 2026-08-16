"""Unit tests for multi-metric pass/fail logic.

Story 6.27: Multi-Metric Pass/Fail Logic Tests

Tests for pass/fail logic and diagnostics.
"""

from __future__ import annotations

# =============================================================================
# Story 6.27: Multi-Metric Pass/Fail Logic Tests
# =============================================================================


class TestDeterminePassStatus:
    """Tests for determine_pass_status function."""

    def test_mape_primary_passes(self):
        """Test MAPE primary metric pass."""
        # Import at runtime to avoid issues with the script path
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))
        from validate_forecasting_unified import determine_pass_status

        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
            primary_metric="mape",
        )
        passed, metric, mase_only = determine_pass_status(
            mape=8.0, smape=12.0, mase=0.9, config=config
        )
        assert passed is True
        assert metric == "mape"
        assert mase_only is False

    def test_mape_primary_fails(self):
        """Test MAPE primary metric fail."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))
        from validate_forecasting_unified import determine_pass_status

        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
            primary_metric="mape",
        )
        passed, metric, mase_only = determine_pass_status(
            mape=15.0, smape=12.0, mase=0.9, config=config
        )
        assert passed is False
        assert metric == "mape"
        assert mase_only is False

    def test_smape_primary_passes(self):
        """Test SMAPE primary metric pass."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))
        from validate_forecasting_unified import determine_pass_status

        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
            primary_metric="smape",
            target_smape=15.0,
        )
        passed, metric, mase_only = determine_pass_status(
            mape=50.0, smape=12.0, mase=0.9, config=config
        )
        assert passed is True
        assert metric == "smape"
        assert mase_only is False

    def test_mase_only_pass_enabled(self):
        """Test MASE-only pass when enabled and MASE excellent."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))
        from validate_forecasting_unified import determine_pass_status

        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
            allow_mase_only_pass=True,
            target_mase=1.0,
        )
        passed, metric, mase_only = determine_pass_status(
            mape=84.0, smape=50.0, mase=0.58, config=config
        )
        assert passed is True
        assert metric == "mase"
        assert mase_only is True

    def test_mase_only_pass_disabled(self):
        """Test MASE-only pass doesn't apply when disabled."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))
        from validate_forecasting_unified import determine_pass_status

        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
            allow_mase_only_pass=False,
        )
        passed, metric, mase_only = determine_pass_status(
            mape=84.0, smape=50.0, mase=0.58, config=config
        )
        assert passed is False
        assert mase_only is False

    def test_secondary_mase_gate_enforced(self):
        """Test MAPE passes but MASE > 1.5 fails."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))
        from validate_forecasting_unified import determine_pass_status

        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
            primary_metric="mape",
        )
        # MAPE would pass (8.0 < 10.0) but MASE > 1.5 blocks it
        passed, metric, mase_only = determine_pass_status(
            mape=8.0, smape=12.0, mase=1.8, config=config
        )
        assert passed is False  # MASE gate blocks

    def test_mase_none_allows_mape_pass(self):
        """Test that None MASE doesn't block MAPE pass."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))
        from validate_forecasting_unified import determine_pass_status

        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
            primary_metric="mape",
        )
        passed, metric, mase_only = determine_pass_status(
            mape=8.0, smape=None, mase=None, config=config
        )
        assert passed is True
        assert metric == "mape"


class TestDiagnoseFailure:
    """Tests for diagnose_failure function."""

    def test_high_mape_good_mase_suggests_mase_only(self):
        """Test high MAPE but good MASE suggests MASE-only pass."""
        from raglite.forecasting.report_generator import diagnose_failure
        from raglite.forecasting.validation_schema import (
            MultiMetricValues,
            VariableValidationResult,
        )

        var = VariableValidationResult(
            variable_name="test",
            display_name="Test",
            target_mape=10.0,
            actual_mape=84.0,
            passed=False,
            metrics=MultiMetricValues(mape=84.0, mase=0.58),
        )
        diagnosis = diagnose_failure(var)
        assert not diagnosis.requires_data_fix
        assert "MASE-only" in diagnosis.recommendation

    def test_both_poor_suggests_data_fix(self):
        """Test both MAPE and MASE poor suggests data fix."""
        from raglite.forecasting.report_generator import diagnose_failure
        from raglite.forecasting.validation_schema import (
            MultiMetricValues,
            VariableValidationResult,
        )

        var = VariableValidationResult(
            variable_name="test",
            display_name="Test",
            target_mape=10.0,
            actual_mape=5660.0,
            passed=False,
            metrics=MultiMetricValues(mape=5660.0, mase=45.0),
        )
        diagnosis = diagnose_failure(var)
        assert diagnosis.requires_data_fix
        assert "data quality" in diagnosis.root_cause.lower()

    def test_borderline_mase_suggests_threshold(self):
        """Test borderline MASE suggests threshold adjustment."""
        from raglite.forecasting.report_generator import diagnose_failure
        from raglite.forecasting.validation_schema import (
            MultiMetricValues,
            VariableValidationResult,
        )

        var = VariableValidationResult(
            variable_name="test",
            display_name="Test",
            target_mape=10.0,
            actual_mape=25.0,
            passed=False,
            metrics=MultiMetricValues(mape=25.0, mase=1.2),
        )
        diagnosis = diagnose_failure(var)
        assert not diagnosis.requires_data_fix
        assert "threshold" in diagnosis.recommendation.lower()


class TestVariableConfigDefaults:
    """Tests for VariableConfig default values (Story 6.27 backward compatibility)."""

    def test_default_primary_metric(self):
        """Test default primary_metric is 'mape'."""
        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
        )
        assert config.primary_metric == "mape"

    def test_default_allow_mase_only_pass(self):
        """Test default allow_mase_only_pass is False."""
        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
        )
        assert config.allow_mase_only_pass is False

    def test_default_target_mase(self):
        """Test default target_mase is 1.0."""
        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
        )
        assert config.target_mase == 1.0

    def test_default_target_smape_is_none(self):
        """Test default target_smape is None."""
        from raglite.forecasting.validation_schema import VariableConfig

        config = VariableConfig(
            name="test",
            display_name="Test",
            unit="EUR",
            regressors=[],
            target_mape=10.0,
            db_metric_aliases=[],
        )
        assert config.target_smape is None


class TestVariableValidationResultDefaults:
    """Tests for VariableValidationResult default values (Story 6.27)."""

    def test_default_primary_metric_used(self):
        """Test default primary_metric_used is 'mape'."""
        from raglite.forecasting.validation_schema import VariableValidationResult

        result = VariableValidationResult(
            variable_name="test",
            display_name="Test",
            target_mape=10.0,
            actual_mape=8.0,
            passed=True,
        )
        assert result.primary_metric_used == "mape"

    def test_default_mase_only_pass(self):
        """Test default mase_only_pass is False."""
        from raglite.forecasting.validation_schema import VariableValidationResult

        result = VariableValidationResult(
            variable_name="test",
            display_name="Test",
            target_mape=10.0,
            actual_mape=8.0,
            passed=True,
        )
        assert result.mase_only_pass is False

    def test_default_bias_alert(self):
        """Test default bias_alert is False."""
        from raglite.forecasting.validation_schema import VariableValidationResult

        result = VariableValidationResult(
            variable_name="test",
            display_name="Test",
            target_mape=10.0,
            actual_mape=8.0,
            passed=True,
        )
        assert result.bias_alert is False
        assert result.bias_alert_message == ""
