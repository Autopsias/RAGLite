# Forecasting Model Validation Guide

**Purpose:** Standard methodology for validating forecasting model accuracy across all epics
**Source:** Lessons learned from Epic 6 Stories 6.7, 6.10, 6.11 (2025-12-08 to 2025-12-09)
**Status:** MANDATORY for all forecasting-related stories

---

## Executive Summary

This guide documents the validation methodology that achieved **97% accuracy improvement** (2.05% MAPE) in Epic 6. All future forecasting work MUST follow this methodology to ensure reproducible, comparable results.

---

## 1. Baseline Capture (BEFORE Implementation)

### Required Steps

```bash
# Step 1: Run all validation scripts and capture output
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data > validation-pre-STORY_ID.txt 2>&1

# Step 2: Run MCP validation
uv run python scripts/validate-mcp-multivariate-forecasting.py > validation-mcp-pre-STORY_ID.txt 2>&1

# Step 3: Run ground truth validation
uv run python scripts/validate-epic6-accuracy.py > validation-gt-pre-STORY_ID.txt 2>&1
```

### What to Record

| Metric | Where to Find | Expected Baseline |
|--------|---------------|-------------------|
| **Avg MAPE** | Summary section of validation output | 2.05% |
| **8-var pass rate** | "Passed: X/8" in output | 8/8 (100%) |
| **Per-variable MAPE** | Individual variable results | See table below |

### Per-Variable Baseline (Epic 6 Reference)

| Variable | Baseline | Multi-var | Target |
|----------|----------|-----------|--------|
| Revenue | 51.5% | 2.8% | <5.0% |
| EBITDA | 131.6% | 2.5% | <5.0% |
| Sales Volume | 119.8% | 0.8% | <5.0% |
| Electricity Cost | 85.2% | 3.0% | <8.0% |
| Thermal Energy | 54.0% | 2.6% | <10.0% |
| Variable Cost | 72.3% | 0.7% | <8.0% |
| Avg Selling Price | 63.6% | 1.6% | <6.0% |
| Capacity Utilization | 133.6% | 2.5% | <10.0% |

---

## 2. External Data Requirements

### APIs with Historical Data (USE FOR VALIDATION)

| API | Records | Date Range | Regressor Names |
|-----|---------|------------|-----------------|
| **ICE API2 Coal** | 751 | 2+ years | `api2_coal` |
| **ICE TTF Gas** | 752 | 2+ years | `ttf_gas` |
| **BPstat EURIBOR** | 83 | 2018-2025 | `euribor_3m` |
| **Eurostat Electricity** | 5+ | 2020+ | `eurostat_electricity` |
| **EU Oil Bulletin** | - | 2+ years | `diesel` |

### APIs NOT Suitable for Validation

| API | Reason | Use Case |
|-----|--------|----------|
| OMIE Electricity | Last 7 days only | Production only |
| CO2 EUA | Last 7 days only | Production only |
| INE Building Permits | Wrong indicator (returns death stats) | DO NOT USE |

### Regressor Selection by Variable Type

```python
REGRESSOR_CONFIG = {
    "financial": ["euribor_3m", "diesel", "ttf_gas", "api2_coal"],
    "energy": ["eurostat_electricity", "ttf_gas", "api2_coal"],
    "production": ["euribor_3m", "diesel", "ttf_gas"],
    "pricing": ["diesel", "euribor_3m", "ttf_gas"],
}
```

---

## 3. Model-Specific Validation

### Prophet Multi-Variate (Baseline Model)

```python
# Test pattern
result = await generate_forecast(
    metric="revenue",
    historical_data=train_data,
    external_regressors=regressors,
    frequency="M",
)
assert result.model_type == "prophet_multivariate"
assert mape <= 0.0205, f"Regression! MAPE={mape:.2%} > 2.05%"
```

### Ensemble (4-6 Models)

```python
# Test pattern
result = await generate_ensemble_forecast(
    metric="revenue",
    historical_data=train_data,
    external_regressors=regressors,
    models=["prophet", "linear", "xgboost", "lightgbm", "catboost", "chronos"],
)
assert len(result.ensemble_weights) >= 4, "Ensemble should have 4+ models"
assert sum(result.ensemble_weights.values()) == pytest.approx(1.0, abs=0.001)
```

### Cold-Start (Chronos-2)

```python
# Test pattern - <6 data points should trigger Chronos-2
short_data = TimeSeriesData(points=train_data.points[:5])
result = await generate_forecast(metric="new_metric", historical_data=short_data)
assert "chronos" in result.model_type.lower(), "Cold-start should use Chronos-2"
```

### TFT (Training Workflow)

```python
# Test training
train_result = await retrain_forecasting_models(models="tft", force=True)
assert train_result.status == "success"

# Test inference
result = await generate_ensemble_forecast(models=["tft"])
# TFT weight may be 0 if not trained - graceful degradation is OK
```

### Adaptive Weights

```python
# Verify weights in PostgreSQL
weights = await get_model_weights(metric="revenue")
assert sum(weights.values()) == pytest.approx(1.0, abs=0.001)
assert all(0.05 <= w <= 0.50 for w in weights.values()), "Weight caps: 5%-50%"
```

---

## 4. Post-Implementation Validation

### Required Steps

```bash
# Step 1: Run same validation scripts
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data > validation-post-STORY_ID.txt 2>&1

# Step 2: Compare with baseline
diff validation-pre-STORY_ID.txt validation-post-STORY_ID.txt | head -50

# Step 3: Extract key metrics
grep -E "Passed:|Average.*MAPE:" validation-post-STORY_ID.txt
```

### Success Criteria

| Criterion | Requirement | Validation |
|-----------|-------------|------------|
| **No Regression** | Avg MAPE ≤ 2.05% | Compare pre/post |
| **All Variables Pass** | 8/8 (100%) | Check "Passed: X/8" |
| **New Model Active** | Weight > 0 in ensemble | Check ensemble_weights |
| **Cold-Start Works** | Chronos-2 for <6 points | Test with short data |
| **Training Works** | TFT checkpoint created | Check model_registry |

---

## 5. CI/CD Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/ci.yaml
- name: Forecasting Accuracy Regression
  run: |
    uv run pytest tests/integration/test_epic6_accuracy_regression.py -v
    uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data
  env:
    MAPE_CI_GATE: 0.12        # FAIL if MAPE > 12%
    MAPE_WARNING: 0.025       # WARN if MAPE > 2.5%
    MAPE_BASELINE: 0.0205     # Reference baseline
```

### Test File Requirements

```
tests/
├── integration/
│   └── test_epic6_accuracy_regression.py  # CI/CD gate
├── validation/
│   └── test_forecast_accuracy.py          # MAPE calculation
└── ground_truth/
    └── cement_demand_2020_2024.csv        # 60 months of data
```

---

## 6. Troubleshooting

### Common Issues and Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| High MAPE (>10%) | Validation fails | Check regressor alignment |
| NaN in regressors | "Found NaN in column" | Use working APIs (see Section 2) |
| Timeout | Script hangs | Use cached external data |
| Wrong entity data | Mixed GROUP/regional | Check entity normalization |
| Model not in ensemble | Weight = 0 | Verify model training |

### Debug Commands

```bash
# Check external data availability
uv run python -c "
from raglite.external_data.clients.ice_futures import ICEFuturesClient
import asyncio
from datetime import date

client = ICEFuturesClient()
data = asyncio.run(client.fetch_api2_coal(date(2022, 1, 1), date(2024, 12, 31)))
print(f'API2 Coal: {len(data)} records')
"

# Check PostgreSQL model weights
docker exec raglite-postgresql psql -U raglite -d raglite -c "SELECT * FROM model_weights ORDER BY calculated_at DESC LIMIT 10;"

# Check ensemble configuration
uv run python -c "
from raglite.shared.config import settings
print(f'Prophet weight: {settings.ensemble_weight_prophet}')
print(f'Linear weight: {settings.ensemble_weight_linear}')
print(f'XGBoost weight: {settings.ensemble_weight_xgboost}')
print(f'LightGBM weight: {settings.ensemble_weight_lightgbm}')
"
```

---

## 7. Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| **Baseline Report** | `docs/baseline-accuracy-2025-12-10.md` | Current baseline metrics |
| **Story 6.10** | `docs/stories/6.10-forecasting-data-quality.md` | Entity normalization, regressor fixes |
| **Story 6.11** | `docs/stories/6.11-mcp-multivariate-forecasting.md` | MCP interface, model selection |
| **Story 6.7** | `docs/stories/6.7-multi-variate-forecast-accuracy-validation.md` | Ground truth validation |
| **Ground Truth CSV** | `tests/ground_truth/cement_demand_2020_2024.csv` | 60 months test data |
| **CI Test** | `tests/integration/test_epic6_accuracy_regression.py` | Regression gate |

---

## 8. Checklist for New Forecasting Stories

Before starting implementation:
- [ ] Run baseline validation and save output
- [ ] Document current MAPE for all 8 variables
- [ ] Verify external data APIs are accessible

During implementation:
- [ ] Use working regressors (see Section 2)
- [ ] Add model-specific tests (see Section 3)
- [ ] Update ensemble_weights if adding new model

After implementation:
- [ ] Run post-implementation validation
- [ ] Compare with baseline (no regression)
- [ ] Verify all 8 variables still pass
- [ ] Update CI/CD if thresholds change
- [ ] Document any baseline improvements

---

*Created: 2025-12-10*
*Based on: Epic 6 validation methodology*
*Maintainer: Dev Team*
