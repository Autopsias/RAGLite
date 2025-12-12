# Forecasting Model Validation Guide

**Date**: 2025-12-12
**Purpose**: Validate forecasting models against cement industry variables
**Scope**: MAPE accuracy for 8 business variables

---

## Quick Start

```bash
# Run full validation
uv run python scripts/validate-all-forecasting-models.py
```

**Expected Runtime**: ~5 minutes

---

## Primary Validation Script

### `scripts/validate-all-forecasting-models.py`

Validates 7 forecasting models + ensemble across 8 cement industry variables.

**Models Tested**:
- Prophet (statistical baseline)
- Linear Regression, XGBoost, LightGBM, CatBoost (ML)
- Chronos-2 (foundation model)
- TFT (deep learning)
- Ensemble (weighted combination)

**Variables Tested**:
| Variable | Target MAPE | Category |
|----------|-------------|----------|
| Revenue | <5.0% | Financial |
| EBITDA | <5.0% | Financial |
| Sales Volume | <5.0% | Production |
| Variable Cost | <8.0% | Cost |
| Avg Selling Price | <6.0% | Pricing |
| Capacity Utilization | <10.0% | Production |
| TTF Gas Price | <10.0% | External |
| Diesel Price | <10.0% | External |

---

## Command Options

```bash
# Full validation (all 8 variables, all models)
uv run python scripts/validate-all-forecasting-models.py --full

# Single variable (quick check)
uv run python scripts/validate-all-forecasting-models.py --variable Revenue

# Single model
uv run python scripts/validate-all-forecasting-models.py --model chronos

# Force TFT retraining before validation
uv run python scripts/validate-all-forecasting-models.py --train-tft

# Skip TFT (faster)
uv run python scripts/validate-all-forecasting-models.py --skip-tft

# Test Chronos cold-start scenario
uv run python scripts/validate-all-forecasting-models.py --cold-start

# Validate adaptive weights (Story 6.12)
uv run python scripts/validate-all-forecasting-models.py --validate-weights

# Export results to JSON
uv run python scripts/validate-all-forecasting-models.py --export-json

# Verbose output
uv run python scripts/validate-all-forecasting-models.py -v
```

---

## Output Interpretation

### Per-Variable Summary

```
PER-VARIABLE SUMMARY:
  Revenue: 2.51% (PASS)           <- Below 5% target
  EBITDA: 1.18% (PASS)            <- Below 5% target
  Sales Volume: 4.18% (PASS)      <- Below 5% target
  Variable Cost: 41.43% (FAIL)    <- Above 8% target
  Avg Selling Price: No data      <- Extraction failed
  Capacity Utilization: No data   <- Extraction failed
  TTF Gas Price: 5.27% (PASS)     <- Below 10% target
  Diesel Price: 0.12% (PASS)      <- Below 10% target

Variables Passed: 5/8
```

### Model Comparison Matrix

```
Variable             prophet    linear     chronos    tft        ensemble
--------------------------------------------------------------------------------
Revenue                  N/A       N/A      99.09%       N/A        2.51%
EBITDA                   N/A       N/A      90.21%       N/A        1.18%
Sales Volume             N/A       N/A       4.18%       N/A        4.18%
```

### MAPE Quality Scale

| MAPE | Quality | Action |
|------|---------|--------|
| <5% | Excellent | No action needed |
| 5-10% | Good | Monitor |
| 10-20% | Acceptable | Consider improvements |
| 20-50% | Poor | Investigation needed |
| >50% | Unacceptable | Fix required |

---

## Debugging High MAPE

### Step 1: Identify the Problem

```bash
# Check which variables are failing
uv run python scripts/validate-all-forecasting-models.py 2>&1 | grep -E "(FAIL|No data)"
```

### Step 2: Check Data Extraction

```bash
uv run python << 'EOF'
import asyncio
import sys
sys.path.insert(0, '.')

async def check_extraction(metric: str):
    from raglite.forecasting.timeseries_extract import extract_timeseries_from_sql
    try:
        result = await extract_timeseries_from_sql(metric=metric, min_points=6)
        if result:
            print(f"✓ {metric}: {len(result.points)} points extracted")
            print(f"  Range: {result.points[0].date} to {result.points[-1].date}")
            print(f"  Values: {[p.value for p in result.points[:3]]}...")
        else:
            print(f"✗ {metric}: No data returned")
    except Exception as e:
        print(f"✗ {metric}: {type(e).__name__} - {e}")

asyncio.run(check_extraction("variable_cost"))
EOF
```

### Step 3: Check Qdrant Fallback Data

```bash
uv run python << 'EOF'
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchText

client = QdrantClient(host='localhost', port=6333)
metric = "Variable Cost"

results, _ = client.scroll(
    collection_name="financial_docs",
    scroll_filter=Filter(must=[FieldCondition(key="text", match=MatchText(text=metric))]),
    limit=5,
    with_payload=True,
)

print(f"Found {len(results)} chunks containing '{metric}'")
for r in results[:3]:
    source = r.payload.get("source_document", "unknown")
    text = r.payload.get("text", "")[:150]
    print(f"\n=== {source} ===")
    print(text)
EOF
```

---

## Common Issues and Fixes

| Symptom | Cause | Solution |
|---------|-------|----------|
| "No data" for variable | SQL extraction failed, no Qdrant fallback | Add metric to `METRIC_CATEGORY_MAP` |
| MAPE >100% | Wrong data scale/units | Check European decimal parsing |
| MAPE exactly 0% | Bug in accuracy calculation | Check `accuracy_metrics` in hybrid.py |
| Inconsistent values | Mixing entities/currencies | Add entity-specific extraction |
| Qdrant fallback failed | Missing `re` import or parsing error | Check function has all imports |

---

## Before/After Comparison

```bash
# Capture baseline
uv run python scripts/validate-all-forecasting-models.py 2>&1 > validation-before.txt

# Make changes...

# Capture after
uv run python scripts/validate-all-forecasting-models.py 2>&1 > validation-after.txt

# Compare key metrics
diff <(grep -E "^\s+(Revenue|EBITDA|Sales|Variable|Avg|Capacity|TTF|Diesel):" validation-before.txt) \
     <(grep -E "^\s+(Revenue|EBITDA|Sales|Variable|Avg|Capacity|TTF|Diesel):" validation-after.txt)
```

---

## Session Handoff Template

When ending a session, record:

```
Session: YYYY-MM-DD
Command: uv run python scripts/validate-all-forecasting-models.py
Result: X/8 variables passing

Passing:
- Revenue: X.XX%
- EBITDA: X.XX%
- ...

Failing:
- Variable Cost: XX.XX% (reason)
- ...

Changes Made:
- file1.py: description
- file2.py: description

Next Steps:
- Investigation or fix needed
```
