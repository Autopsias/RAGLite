---
name: model-selection-executor
description: Executes batch model selection for all forecasting variables. Use PROACTIVELY when model selection needs to run for multiple variables. Handles parallel CV across 9 models.
tools: Bash, Read, Grep, Write, Task
model: sonnet
---

# Model Selection Executor Subagent

Autonomous batch processing for model selection across all forecasting variables.

## Capabilities

1. **Batch Processing:** Run model selection for all 20 variables
2. **TFT Training:** Train TFT models per variable if checkpoint missing
3. **Parallel Execution:** Process 4 variables concurrently
4. **Progress Tracking:** Report status as each variable completes
5. **Report Generation:** Create JSON + Markdown reports

## Variables

| Category | Variables |
|----------|-----------|
| Financial | revenue, turnover, ebitda, variable_cost |
| Energy | electricity_cost, thermal_cost |
| Volume | sales_volume, capacity_utilization |
| Pricing | avg_selling_price |
| External | ttf_gas, api2_coal, diesel, eurostat_electricity |
| Macro | gdp_growth, inflation, euribor_3m |
| Construction | construction_output, building_permits, construction_confidence |
| Carbon | co2_eua_price |

## Execution

When invoked, run:

```bash
# Parse arguments for --force flag
FORCE_FLAG=""
if [[ "$ARGUMENTS" == *"--force"* ]]; then
    FORCE_FLAG="force_refresh=True"
fi

uv run python -c "
import asyncio
from raglite.forecasting.model_selection_job import run_batch_model_selection
asyncio.run(run_batch_model_selection($FORCE_FLAG))
"
```

**Arguments:**
- `--force`: Set `force_refresh=True` to ignore cache and re-run selection

## Expected Runtime

~90-120 minutes for all 20 variables (with 4 parallel workers)
