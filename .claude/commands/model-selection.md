---
argument-hint: [variable|--all] [--force] [--dry-run]
description: Run model selection for forecasting variables. Use --all for batch processing.
allowed-tools: Bash, Read, Grep, Task
---

# Model Selection Command

Run model selection for forecasting variables to determine the optimal model per variable.

## Usage

- `/model-selection <variable>` - Run for single variable (e.g., `/model-selection ebitda`)
- `/model-selection --all` - Run for all 20 variables (delegates to subagent)
- `/model-selection <variable> --force` - Ignore cache and re-run selection
- `/model-selection --all --dry-run` - Preview without caching

## Arguments

- `$ARGUMENTS` contains the arguments passed to the command

## Action Logic

1. Parse arguments to determine mode (single or batch)
2. If `--all` is specified:
   - Delegate to model-selection-executor subagent via Task tool
   - Report: "Delegating to model-selection-executor subagent for batch processing..."
3. If single variable specified:
   - Call `run_single_variable_selection()` from model_selection_job.py
   - Display results with model comparison table
4. If `--force` specified, set force_refresh=True
5. If `--dry-run` specified, set dry_run=True (no caching)

## Execution

When invoked, parse arguments and execute:

```python
# Parse arguments
args = "$ARGUMENTS".strip().split()
variable = None
force_refresh = False
dry_run = False
run_all = False

for arg in args:
    if arg == "--all":
        run_all = True
    elif arg == "--force":
        force_refresh = True
    elif arg == "--dry-run":
        dry_run = True
    elif not arg.startswith("--"):
        variable = arg

# Execute based on mode
if run_all:
    # Delegate to subagent
    print("Delegating to model-selection-executor subagent for batch processing...")
    # Use Task tool to invoke model-selection-executor subagent
else:
    # Run for single variable
    import asyncio
    from raglite.forecasting.model_selection_job import run_single_variable_selection

    result = asyncio.run(run_single_variable_selection(
        variable=variable,
        force_refresh=force_refresh,
        dry_run=dry_run
    ))
```

## Example Outputs

Single variable:
```
EBITDA Model Selection Results:
Best Model: ARIMA(1,1,1)
MAPE: 8.2% | MASE: 0.42
Regressors: None

Model Comparison:
| Model    | MAPE   | MASE | Status |
|----------|--------|------|--------|
| ARIMA    | 8.2%   | 0.42 | BEST   |
| Prophet  | 84.7%  | 4.23 |        |
| ETS      | 12.1%  | 0.58 |        |
```
