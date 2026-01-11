"""Assessment utilities for validation reports.

Story 6.26: Multi-Metric Validation Enhancement
Thresholds and assessment functions for MAPE, MASE, and status determination.
"""

from __future__ import annotations

# =============================================================================
# Assessment Thresholds
# =============================================================================

# MAPE thresholds for assessment status
MAPE_THRESHOLDS = {
    "excellent": 5.0,  # <5%: Excellent - suitable for financial reporting
    "good": 10.0,  # 5-10%: Good - acceptable for planning
    "moderate": 20.0,  # 10-20%: Moderate - use with caution
    "poor": 30.0,  # 20-30%: Poor - investigate root cause
    # >30%: Critical
}

# MASE thresholds for assessment status
MASE_THRESHOLDS = {
    "excellent": 0.5,  # <0.5: Excellent - model provides significant value
    "good": 0.8,  # 0.5-0.8: Good - model outperforms naïve substantially
    "marginal": 1.0,  # 0.8-1.0: Marginal - model barely beats naïve
    # >1.0: Poor - naïve forecast would be better
}


def get_mape_assessment(mape: float | None) -> str:
    """Get assessment status based on MAPE value."""
    if mape is None:
        return "unknown"
    if mape < MAPE_THRESHOLDS["excellent"]:
        return "excellent"
    if mape < MAPE_THRESHOLDS["good"]:
        return "good"
    if mape < MAPE_THRESHOLDS["moderate"]:
        return "moderate"
    if mape < MAPE_THRESHOLDS["poor"]:
        return "poor"
    return "critical"


def get_mase_assessment(mase: float | None) -> str:
    """Get assessment status based on MASE value."""
    if mase is None:
        return "unknown"
    if mase < MASE_THRESHOLDS["excellent"]:
        return "excellent"
    if mase < MASE_THRESHOLDS["good"]:
        return "good"
    if mase < MASE_THRESHOLDS["marginal"]:
        return "marginal"
    return "poor"


def get_status_emoji(passed: bool, mape: float | None = None) -> str:
    """Get status emoji based on pass/fail and MAPE value."""
    if not passed:
        return "❌"
    if mape is not None and mape < 5.0:
        return "✅"
    return "✅" if passed else "⚠️"


# =============================================================================
# Metric Explanation Content
# =============================================================================

METRIC_EXPLANATIONS = """## Understanding the Metrics

### MAPE (Mean Absolute Percentage Error)
**What it measures:** Average percentage deviation from actual values
**Target:** Variable-specific (see table below)
**Interpretation:**
- <5%: Excellent - suitable for financial reporting
- 5-10%: Good - acceptable for planning
- 10-20%: Moderate - use with caution
- >20%: Poor - investigate root cause

### MASE (Mean Absolute Scaled Error)
**What it measures:** Forecast accuracy relative to a naïve baseline (previous period's value)
**Target:** <1.0 (beating the naïve forecast)
**Interpretation:**
- <0.5: Excellent - model provides significant value over naïve baseline
- 0.5-0.8: Good - model outperforms naïve substantially
- 0.8-1.0: Marginal - model barely beats naïve
- >1.0: Poor - naïve forecast would be better

### SMAPE (Symmetric MAPE)
**What it measures:** Percentage error bounded 0-200%, treats over/under equally
**When to use:** Volatile metrics where MAPE skews results
**Interpretation:** Similar to MAPE but more stable for commodities

### RMSE (Root Mean Square Error)
**What it measures:** Average error in original units, penalizes large errors
**When to use:** When large errors are especially costly (risk management)
**Interpretation:** Lower is better; compare only within same variable

### MAE (Mean Absolute Error)
**What it measures:** Simple average of absolute errors in original units
**When to use:** When you want interpretable error in data units
**Interpretation:** Lower is better; more robust to outliers than RMSE

### Bias (Mean Error)
**What it measures:** Systematic over-prediction (positive) or under-prediction (negative)
**Target:** Close to 0
**Interpretation:**
- Positive: Model tends to over-predict (conservative)
- Negative: Model tends to under-predict (optimistic)
- Near 0: Model is well-calibrated

### FQS (Forecast Quality Score)
**What it measures:** Composite quality metric combining MAPE and MASE (0-100 scale)
**Target:** ≥65 (Good), ≥80 (Excellent)
**Formula:** FQS = 100 × [0.35 × A_MAPE + 0.65 × A_MASE]
**Interpretation:**
- ≥80: Excellent - high confidence in forecast quality
- 65-79: Good - acceptable for planning decisions
- 50-64: Moderate - use with caution
- <50: Poor - forecast needs investigation
**Note:** MASE-weighted (65%) per Hyndman (2006) recommendation for cross-series comparability
"""
