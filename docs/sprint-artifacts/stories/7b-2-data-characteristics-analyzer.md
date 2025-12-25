# Story 7B.2: Data Characteristics Analyzer

**Epic:** 7B - Intelligent Model Selection Framework
**Status:** drafted

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

---

## Prerequisites

- **Story 7B.1 (ARIMA/ETS Wrappers):** Must be complete. ARIMA/ETS models are needed for model recommendations.

---

## Story

As a developer,
I want a data characteristics analyzer that performs statistical tests on time-series data,
so that the model selection framework can make informed pre-selection of candidate models based on stationarity, seasonality, trend, and volatility characteristics.

---

## Context

The model selection framework (Story 7B.3) will test all 9 models via cross-validation, but this is computationally expensive. A data characteristics analyzer can pre-filter candidates by analyzing the time-series properties, enabling smarter model recommendations.

### Why Data Characteristics Analysis?

Per Epic 7: Intelligent Model Selection Framework (`docs/prd/epic-7-intelligent-model-selection.md`):

1. **Stationarity** - ADF + KPSS tests determine if data is stationary (ARIMA-friendly) or needs differencing
2. **Seasonality** - ACF analysis detects seasonal patterns (ETS, SARIMA, Prophet)
3. **Trend** - Linear regression detects significant trends (damped ETS, Prophet)
4. **Volatility** - Coefficient of variation identifies high-volatility series (ML models like XGBoost)

### Model Recommendation Logic

| Characteristic | Recommended Models |
|---------------|-------------------|
| Stationary | ARIMA, Linear |
| Non-stationary | Prophet, ETS, ARIMA with differencing |
| Strong seasonality | SARIMA, ETS, Prophet |
| High volatility | XGBoost, LightGBM, CatBoost |
| Cold-start (<12 points) | Chronos-2 |
| Complex multivariate | TFT |

---

## Acceptance Criteria

### AC1: Combined ADF + KPSS Stationarity Test
**Given** the need to classify time-series stationarity
**When** running stationarity analysis
**Then**:
- [ ] Implement ADF test (Augmented Dickey-Fuller, null: non-stationary)
- [ ] Implement KPSS test (null: stationary)
- [ ] Apply Kwiatkowski protocol for combined interpretation:
  - ADF p<0.05 AND KPSS p>0.05 -> STATIONARY
  - ADF p>=0.05 AND KPSS p<=0.05 -> NON_STATIONARY
  - Both reject or neither -> TREND_STATIONARY or DIFFERENCE_STATIONARY
- [ ] Return stationarity enum and both p-values
- [ ] Suggest differencing order (0, 1, or 2)

### AC2: Seasonality Detection via ACF Analysis
**Given** the need to identify seasonal patterns
**When** analyzing autocorrelation
**Then**:
- [ ] Compute ACF for up to 2x seasonal period (24 lags for monthly, 8 for quarterly)
- [ ] Detect seasonal peaks at lag=seasonal_period
- [ ] Calculate seasonal strength (0-1 based on ACF peak magnitude)
- [ ] Classify seasonality type: NONE, ADDITIVE, MULTIPLICATIVE
- [ ] Return seasonal period (12 for M, 4 for Q) and strength

### AC3: Trend Detection via Linear Regression
**Given** the need to identify significant trends
**When** fitting linear regression to time-series
**Then**:
- [ ] Fit OLS regression: y = a + b*t
- [ ] Calculate trend slope (b coefficient)
- [ ] Calculate trend significance (p-value of slope)
- [ ] Classify trend as significant if p-value < 0.05
- [ ] Return slope, significance, and direction (up/down/flat)

### AC4: Volatility Measurement
**Given** the need to quantify data variability
**When** analyzing volatility
**Then**:
- [ ] Calculate coefficient of variation (CV = std/mean)
- [ ] Calculate rolling volatility (standard deviation over windows)
- [ ] Classify volatility: LOW (<0.1), MEDIUM (0.1-0.3), HIGH (>0.3)
- [ ] Return CV value and classification

### AC5: Data Quality Metrics
**Given** the need to assess data suitability for modeling
**When** analyzing data quality
**Then**:
- [ ] Calculate data length (number of observations)
- [ ] Calculate missing ratio (NaN / total)
- [ ] Count outliers using IQR method (|x - median| > 1.5 * IQR)
- [ ] Return quality metrics in DataCharacteristics

### AC6: Return DataCharacteristics with Model Recommendations
**Given** all characteristics are analyzed
**When** returning results
**Then**:
- [ ] Return `DataCharacteristics` dataclass with all metrics
- [ ] Include `recommended_models: list[str]` based on characteristics
- [ ] Include `model_rationale: str` explaining why models were recommended
- [ ] Prioritize recommendations (best model first)
- [ ] Handle edge cases (short series, constant values)

### AC7: Unit Tests for All Analyzers
**Given** the need for reliable data analysis
**When** running the test suite
**Then**:
- [ ] Unit tests in `tests/unit/test_data_analyzer.py`
- [ ] Coverage >80% for new module
- [ ] Test cases: stationary data, trending data, seasonal data, volatile data
- [ ] Test edge cases: short series, constant values, NaN handling
- [ ] Test model recommendations match expected patterns

---

## Technical Design

### File Structure

```
raglite/forecasting/
  data_analyzer.py    # NEW: Data characteristics analyzer (~350 LOC)
tests/unit/
  test_data_analyzer.py  # NEW: Unit tests (~200 LOC)
```

### Data Classes and Enums

```python
# raglite/forecasting/data_analyzer.py

from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss, acf
from scipy import stats


class Stationarity(Enum):
    """Stationarity classification based on ADF + KPSS tests."""
    STATIONARY = "stationary"              # ADF rejects, KPSS fails to reject
    TREND_STATIONARY = "trend_stationary"  # Both reject or conflicting
    DIFFERENCE_STATIONARY = "difference_stationary"  # Needs differencing
    NON_STATIONARY = "non_stationary"      # ADF fails to reject, KPSS rejects


class SeasonalityType(Enum):
    """Seasonality classification."""
    NONE = "none"
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"


class VolatilityLevel(Enum):
    """Volatility classification."""
    LOW = "low"       # CV < 0.1
    MEDIUM = "medium" # 0.1 <= CV < 0.3
    HIGH = "high"     # CV >= 0.3


class TrendDirection(Enum):
    """Trend direction classification."""
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


@dataclass
class DataCharacteristics:
    """Complete data characteristics for model selection."""
    # Stationarity
    stationarity: Stationarity
    adf_pvalue: float
    kpss_pvalue: float
    suggested_differencing: int

    # Seasonality
    seasonality_type: SeasonalityType
    seasonal_period: int | None
    seasonal_strength: float  # 0-1

    # Trend
    trend_slope: float
    trend_significance: float
    trend_direction: TrendDirection

    # Volatility
    coefficient_of_variation: float
    volatility_level: VolatilityLevel

    # Data quality
    data_length: int
    missing_ratio: float
    outlier_count: int

    # Recommendations
    recommended_models: list[str]
    model_rationale: str
```

### Main Function Signature

```python
def analyze_data_characteristics(
    series: pd.Series,
    frequency: str = "M",
) -> DataCharacteristics:
    """Analyze time-series for model selection.

    Args:
        series: Time series data (pandas Series with DatetimeIndex)
        frequency: Time frequency ("M" for monthly, "Q" for quarterly)

    Returns:
        DataCharacteristics with all metrics and model recommendations

    Raises:
        ValueError: If series is too short (<4 observations) or all NaN
    """
    # 1. Clean data
    clean_series = _clean_series(series)

    # 2. Test stationarity (ADF + KPSS)
    stationarity_result = _test_stationarity(clean_series)

    # 3. Detect seasonality
    seasonality_result = _detect_seasonality(clean_series, frequency)

    # 4. Detect trend
    trend_result = _detect_trend(clean_series)

    # 5. Measure volatility
    volatility_result = _measure_volatility(clean_series)

    # 6. Assess data quality
    quality_result = _assess_data_quality(series)  # Original with NaNs

    # 7. Generate recommendations
    recommended_models, rationale = _recommend_models(
        stationarity_result,
        seasonality_result,
        trend_result,
        volatility_result,
        quality_result,
    )

    return DataCharacteristics(
        stationarity=stationarity_result.stationarity,
        adf_pvalue=stationarity_result.adf_pvalue,
        kpss_pvalue=stationarity_result.kpss_pvalue,
        suggested_differencing=stationarity_result.suggested_differencing,
        seasonality_type=seasonality_result.seasonality_type,
        seasonal_period=seasonality_result.seasonal_period,
        seasonal_strength=seasonality_result.seasonal_strength,
        trend_slope=trend_result.slope,
        trend_significance=trend_result.significance,
        trend_direction=trend_result.direction,
        coefficient_of_variation=volatility_result.cv,
        volatility_level=volatility_result.level,
        data_length=quality_result.data_length,
        missing_ratio=quality_result.missing_ratio,
        outlier_count=quality_result.outlier_count,
        recommended_models=recommended_models,
        model_rationale=rationale,
    )
```

### Model Recommendation Logic

```python
def _recommend_models(
    stationarity: StationarityResult,
    seasonality: SeasonalityResult,
    trend: TrendResult,
    volatility: VolatilityResult,
    quality: DataQualityResult,
) -> tuple[list[str], str]:
    """Generate model recommendations based on data characteristics."""
    candidates = []
    rationale_parts = []

    # Cold-start: prefer Chronos-2 for short series
    if quality.data_length < 12:
        candidates.append("chronos")
        rationale_parts.append(f"Short series ({quality.data_length} points) - Chronos-2 for zero-shot")
        return candidates, "; ".join(rationale_parts)

    # Stationarity-based recommendations
    if stationarity.stationarity == Stationarity.STATIONARY:
        candidates.extend(["arima", "linear"])
        rationale_parts.append("Stationary data - ARIMA/Linear preferred")
    elif stationarity.stationarity == Stationarity.NON_STATIONARY:
        candidates.extend(["prophet", "ets", "arima"])
        rationale_parts.append("Non-stationary - Prophet/ETS/ARIMA with differencing")

    # Seasonality-based recommendations
    if seasonality.seasonal_strength > 0.3:
        if "arima" in candidates:
            candidates[candidates.index("arima")] = "sarima"  # Upgrade to SARIMA
        if "ets" not in candidates:
            candidates.append("ets")
        if "prophet" not in candidates:
            candidates.append("prophet")
        rationale_parts.append(f"Strong seasonality ({seasonality.seasonal_strength:.2f}) - SARIMA/ETS/Prophet")

    # Volatility-based recommendations
    if volatility.level == VolatilityLevel.HIGH:
        candidates.extend(["xgboost", "lightgbm", "catboost"])
        rationale_parts.append(f"High volatility (CV={volatility.cv:.2f}) - ML models")

    # Trend-based recommendations
    if trend.direction != TrendDirection.FLAT and trend.significance < 0.05:
        if "prophet" not in candidates:
            candidates.append("prophet")
        rationale_parts.append("Significant trend - Prophet for changepoints")

    # Always include TFT for complex patterns (lower priority)
    if quality.data_length >= 24:
        candidates.append("tft")

    # Deduplicate while preserving order
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)

    rationale = "; ".join(rationale_parts) if rationale_parts else "Default model selection"

    return unique_candidates, rationale
```

### Helper Functions

```python
def _test_stationarity(series: pd.Series) -> StationarityResult:
    """Test stationarity using ADF + KPSS (Kwiatkowski protocol)."""
    # ADF test (null: non-stationary)
    adf_result = adfuller(series, autolag='AIC')
    adf_pvalue = adf_result[1]

    # KPSS test (null: stationary)
    # Note: KPSS may raise warnings for short series
    try:
        kpss_result = kpss(series, regression='c', nlags='auto')
        kpss_pvalue = kpss_result[1]
    except Exception:
        kpss_pvalue = 0.5  # Inconclusive fallback

    # Kwiatkowski protocol interpretation
    if adf_pvalue < 0.05 and kpss_pvalue > 0.05:
        stationarity = Stationarity.STATIONARY
        differencing = 0
    elif adf_pvalue >= 0.05 and kpss_pvalue <= 0.05:
        stationarity = Stationarity.NON_STATIONARY
        differencing = 1
    elif adf_pvalue < 0.05 and kpss_pvalue <= 0.05:
        stationarity = Stationarity.TREND_STATIONARY
        differencing = 1
    else:
        stationarity = Stationarity.DIFFERENCE_STATIONARY
        differencing = 1

    return StationarityResult(
        stationarity=stationarity,
        adf_pvalue=adf_pvalue,
        kpss_pvalue=kpss_pvalue,
        suggested_differencing=differencing,
    )


def _detect_seasonality(series: pd.Series, frequency: str) -> SeasonalityResult:
    """Detect seasonality via ACF peak analysis."""
    seasonal_period = 12 if frequency == "M" else 4

    # Compute ACF
    nlags = min(len(series) - 1, seasonal_period * 2)
    if nlags < seasonal_period:
        return SeasonalityResult(
            seasonality_type=SeasonalityType.NONE,
            seasonal_period=None,
            seasonal_strength=0.0,
        )

    acf_values = acf(series, nlags=nlags, fft=True)

    # Check for peak at seasonal lag
    seasonal_acf = abs(acf_values[seasonal_period]) if len(acf_values) > seasonal_period else 0.0

    # Determine seasonality type based on coefficient of variation pattern
    # Multiplicative if variance scales with level
    if seasonal_acf > 0.3:
        # Simple heuristic: if high-value periods have proportionally higher variance
        mean_series = series.mean()
        if mean_series > 0:
            upper_half = series[series > mean_series]
            lower_half = series[series <= mean_series]
            if len(upper_half) > 2 and len(lower_half) > 2:
                cv_upper = upper_half.std() / upper_half.mean() if upper_half.mean() != 0 else 0
                cv_lower = lower_half.std() / lower_half.mean() if lower_half.mean() != 0 else 0
                seasonality_type = SeasonalityType.MULTIPLICATIVE if cv_upper > cv_lower * 1.2 else SeasonalityType.ADDITIVE
            else:
                seasonality_type = SeasonalityType.ADDITIVE
        else:
            seasonality_type = SeasonalityType.ADDITIVE
    else:
        seasonality_type = SeasonalityType.NONE

    return SeasonalityResult(
        seasonality_type=seasonality_type,
        seasonal_period=seasonal_period if seasonal_acf > 0.1 else None,
        seasonal_strength=seasonal_acf,
    )


def _detect_trend(series: pd.Series) -> TrendResult:
    """Detect trend via linear regression."""
    # Create time index
    t = np.arange(len(series))

    # OLS regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(t, series.values)

    # Determine direction
    if p_value < 0.05:
        direction = TrendDirection.UP if slope > 0 else TrendDirection.DOWN
    else:
        direction = TrendDirection.FLAT

    return TrendResult(
        slope=slope,
        significance=p_value,
        direction=direction,
    )


def _measure_volatility(series: pd.Series) -> VolatilityResult:
    """Measure volatility using coefficient of variation."""
    mean_val = series.mean()
    std_val = series.std()

    # Handle zero/near-zero mean
    if abs(mean_val) < 1e-10:
        cv = float('inf') if std_val > 0 else 0.0
    else:
        cv = abs(std_val / mean_val)

    # Classify volatility
    if cv < 0.1:
        level = VolatilityLevel.LOW
    elif cv < 0.3:
        level = VolatilityLevel.MEDIUM
    else:
        level = VolatilityLevel.HIGH

    return VolatilityResult(cv=cv, level=level)


def _assess_data_quality(series: pd.Series) -> DataQualityResult:
    """Assess data quality metrics."""
    data_length = len(series)
    missing_count = series.isna().sum()
    missing_ratio = missing_count / data_length if data_length > 0 else 0.0

    # Outlier detection using IQR
    clean_series = series.dropna()
    if len(clean_series) >= 4:
        q1 = clean_series.quantile(0.25)
        q3 = clean_series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_count = ((clean_series < lower_bound) | (clean_series > upper_bound)).sum()
    else:
        outlier_count = 0

    return DataQualityResult(
        data_length=data_length,
        missing_ratio=missing_ratio,
        outlier_count=outlier_count,
    )


def _clean_series(series: pd.Series) -> pd.Series:
    """Clean series by handling NaN values."""
    # Drop NaN values for analysis
    clean = series.dropna()

    if len(clean) < 4:
        raise ValueError(f"Series too short after cleaning: {len(clean)} observations (minimum: 4)")

    if clean.std() == 0:
        raise ValueError("Constant series cannot be analyzed for time-series properties")

    return clean
```

---

## Tasks / Subtasks

### Task 1: Create data_analyzer.py with Enums and Dataclasses (AC6)
- [ ] Create `raglite/forecasting/data_analyzer.py`
- [ ] Define `Stationarity` enum
- [ ] Define `SeasonalityType` enum
- [ ] Define `VolatilityLevel` enum
- [ ] Define `TrendDirection` enum
- [ ] Define `DataCharacteristics` dataclass
- [ ] Define helper result dataclasses (StationarityResult, SeasonalityResult, etc.)
- [ ] Verify: `python -c "from raglite.forecasting.data_analyzer import DataCharacteristics, Stationarity"`

### Task 2: Implement Stationarity Tests (AC1)
- [ ] Implement `_test_stationarity()` with ADF test
- [ ] Add KPSS test with error handling
- [ ] Implement Kwiatkowski protocol interpretation
- [ ] Calculate suggested differencing order
- [ ] Add docstrings and type hints

### Task 3: Implement Seasonality Detection (AC2)
- [ ] Implement `_detect_seasonality()` with ACF computation
- [ ] Handle frequency-based seasonal periods (M=12, Q=4)
- [ ] Calculate seasonal strength from ACF peaks
- [ ] Detect multiplicative vs additive seasonality
- [ ] Handle short series gracefully

### Task 4: Implement Trend Detection (AC3)
- [ ] Implement `_detect_trend()` with scipy.stats.linregress
- [ ] Calculate slope and significance
- [ ] Classify trend direction (UP/DOWN/FLAT)
- [ ] Add docstrings and type hints

### Task 5: Implement Volatility Measurement (AC4)
- [ ] Implement `_measure_volatility()` with CV calculation
- [ ] Handle zero/near-zero mean edge case
- [ ] Classify volatility level (LOW/MEDIUM/HIGH)
- [ ] Add docstrings and type hints

### Task 6: Implement Data Quality Assessment (AC5)
- [ ] Implement `_assess_data_quality()` with length calculation
- [ ] Calculate missing ratio
- [ ] Implement IQR-based outlier detection
- [ ] Handle edge cases (very short series)

### Task 7: Implement Model Recommendation Logic (AC6)
- [ ] Implement `_recommend_models()` function
- [ ] Add cold-start detection (<12 points -> Chronos-2)
- [ ] Add stationarity-based recommendations
- [ ] Add seasonality-based recommendations
- [ ] Add volatility-based recommendations
- [ ] Add trend-based recommendations
- [ ] Generate rationale string
- [ ] Deduplicate and prioritize models

### Task 8: Implement Main analyze_data_characteristics() (AC1-AC6)
- [ ] Implement `analyze_data_characteristics()` main function
- [ ] Implement `_clean_series()` helper
- [ ] Wire all components together
- [ ] Add comprehensive error handling
- [ ] Add docstrings and type hints
- [ ] Verify: `python -c "from raglite.forecasting.data_analyzer import analyze_data_characteristics"`

### Task 9: Create Unit Tests (AC7)
- [ ] Create `tests/unit/test_data_analyzer.py`
- [ ] Test stationary data classification
- [ ] Test non-stationary data classification
- [ ] Test seasonal data detection
- [ ] Test trend detection (up, down, flat)
- [ ] Test volatility classification
- [ ] Test data quality metrics
- [ ] Test model recommendations for various patterns
- [ ] Test edge cases: short series, constant values, NaN handling
- [ ] Run: `pytest tests/unit/test_data_analyzer.py -v`

### Task 10: Validate Coverage (AC7)
- [ ] Run coverage: `pytest tests/unit/test_data_analyzer.py --cov=raglite/forecasting/data_analyzer --cov-report=term-missing`
- [ ] Verify >80% coverage
- [ ] Add tests for any uncovered paths

### Task 11: Integration Smoke Test
- [ ] Test with real financial data shapes
- [ ] Verify recommendations match expected patterns for known data types
- [ ] Verify no import errors when integrated with forecasting module

---

## Dev Notes

### Architecture References

- **Data Analysis Patterns:** `docs/architecture/6-complete-reference-implementation.md` defines data processing patterns
- **Dataclass Standards:** Use Python dataclasses for structured return types (per coding-standards.md)
- **Error Handling:** Raise specific ValueError with context (per coding-standards.md)

### statsmodels Already Available

The `statsmodels` library is already a dependency (via Prophet). Functions needed:
- `statsmodels.tsa.stattools.adfuller` - ADF test
- `statsmodels.tsa.stattools.kpss` - KPSS test
- `statsmodels.tsa.stattools.acf` - Autocorrelation function

### scipy Already Available

The `scipy` library is already a dependency. Functions needed:
- `scipy.stats.linregress` - OLS linear regression

### No New Dependencies Required

All statistical functions are available from existing dependencies (statsmodels, scipy, numpy, pandas).

### Kwiatkowski Protocol

The combined ADF + KPSS interpretation:

| ADF Result | KPSS Result | Interpretation |
|------------|-------------|----------------|
| Reject (p<0.05) | Fail to reject (p>0.05) | STATIONARY |
| Fail to reject | Reject | NON_STATIONARY |
| Reject | Reject | TREND_STATIONARY |
| Fail to reject | Fail to reject | DIFFERENCE_STATIONARY |

### File Size Target

- `data_analyzer.py`: ~350 LOC
- `test_data_analyzer.py`: ~200 LOC

Both well under the 500 LOC limit.

### Testing Strategy

1. Use synthetic data with known properties (stationary, trending, seasonal)
2. Use fixtures for edge cases (short series, constant values, NaN data)
3. Verify model recommendations match expected patterns
4. Compare output structures, not exact statistical values (which vary)

---

## References

- [Epic 7: Intelligent Model Selection](../../prd/epic-7-intelligent-model-selection.md) - Parent epic (Section: Story 7.2)
- [Story 7B.1: ARIMA/ETS Wrappers](./7b-1-add-arima-ets-model-wrappers.md) - Prerequisite story
- [statsmodels ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html) - ADF test reference
- [statsmodels KPSS](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html) - KPSS test reference
- [scipy.stats.linregress](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.linregress.html) - Linear regression

---

## Dev Agent Record

### Agent Model Used

(To be filled by implementing agent)

### Debug Log References

(To be filled by implementing agent)

### Completion Notes List

(To be filled by implementing agent)

### File List

**Files to Create:**
- `raglite/forecasting/data_analyzer.py` (~350 LOC)
- `tests/unit/test_data_analyzer.py` (~200 LOC)

**Files to Modify:**
- None (self-contained module)

**Total New Code:** ~550 LOC
