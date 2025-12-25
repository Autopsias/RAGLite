# Story 7b-5: Model Selection Slash Commands & Subagent

Status: Drafted

## Story Header

- **Epic:** 7b - Intelligent Model Selection Framework
- **Priority:** P0
- **Effort:** 1 day
- **Status:** drafted
- **Dependencies:** 7b-3 (Per-Variable Model Selection via Cross-Validation), 7b-4 (Model Selection Cache in PostgreSQL)

## User Story

As a developer/data scientist,
I want Claude Code slash commands and subagent to run model selection on-demand,
So that I can trigger model selection for forecasting variables without writing Python code.

## Background

Stories 7b-3 and 7b-4 implement the model selection framework and PostgreSQL caching. This story creates the user-facing interface: a slash command `/model-selection` for on-demand execution and a `model-selection-executor` subagent for autonomous batch processing of all 20 forecasting variables.

## Acceptance Criteria

### AC-7b.5.1: Slash Command Definition

**Given** a Claude Code session is active
**When** I run `/model-selection <variable>` for a single variable (e.g., `/model-selection ebitda`)
**Then** model selection runs for that specific variable and displays:
  - The best model name and configuration
  - MAPE and MASE scores
  - Regressor usage (if applicable)
  - Comparison table of all tested models

**And** when I run `/model-selection --all`
**Then** the command delegates to the `model-selection-executor` subagent for batch processing

**Verification:**
- Slash command file exists at `.claude/commands/model-selection.md`
- Single variable execution works correctly
- `--all` flag triggers subagent delegation
- `--force` flag ignores cache and re-runs selection
- `--dry-run` flag shows preview without caching

### AC-7b.5.2: Model-Selection-Executor Subagent

**Given** the model-selection-executor subagent is invoked
**When** it receives a batch processing request (via `/model-selection --all` or direct invocation)
**Then** the subagent:
  - Processes all 20 forecasting variables
  - Runs model selection for each variable using `run_batch_model_selection()`
  - Reports progress as each variable completes
  - Generates JSON and Markdown reports

**Verification:**
- Subagent file exists at `.claude/agents/model-selection-executor.md`
- Subagent handles batch processing autonomously
- Progress updates displayed during execution
- Reports generated upon completion

### AC-7b.5.3: `run_batch_model_selection()` Python Function

**Given** the `raglite/forecasting/model_selection_job.py` module exists
**When** `run_batch_model_selection()` is called with a list of variables
**Then** the function:
  - Iterates through all specified variables (default: ALL_VARIABLES list of 20)
  - Calls `select_best_model()` for each variable
  - Caches results using `cache_model_selection()`
  - Returns a dictionary of variable_name -> ModelSelectionResult

**Verification:**
- Function signature matches specification
- ALL_VARIABLES list contains 20 forecasting variables
- Each variable processed and cached
- Results aggregated and returned

### AC-7b.5.4: Parallel Execution (4 Workers)

**Given** batch model selection is running for multiple variables
**When** `run_batch_model_selection()` executes
**Then** up to 4 variables are processed concurrently using asyncio.Semaphore
**And** progress is logged as each variable completes

**Verification:**
- Semaphore limits concurrent executions to 4
- Parallel execution reduces total runtime
- No race conditions in cache writes
- Progress logging shows parallel completion

### AC-7b.5.5: Cache Results in PostgreSQL

**Given** model selection completes for a variable
**When** the result is returned
**Then** `cache_model_selection()` from Story 7b-4 is called to store:
  - Best model and configuration
  - MAPE/MASE scores
  - Regressor set
  - Data characteristics
  - 7-day TTL

**Verification:**
- Each completed variable is cached immediately
- Cache entries visible in PostgreSQL model_selection table
- Upsert behavior for re-running selection

### AC-7b.5.6: Generate JSON + Markdown Report

**Given** batch model selection completes for all variables
**When** report generation runs
**Then** two report files are created in `reports/` directory:
  - `model-selection-{timestamp}.json` - Full results with all candidate data
  - `model-selection-{timestamp}.md` - Summary table with best models

**And** the Markdown report contains:
  - Summary statistics (variables processed, runtime, best/worst performers)
  - Table with variable, best_model, MAPE, MASE, regressors columns
  - Timestamp and metadata

**Verification:**
- Reports directory created if not exists
- JSON file contains complete ModelSelectionResult data
- Markdown file is human-readable with summary table
- Timestamp in filename for versioning

### AC-7b.5.7: Progress Logging with Status Updates

**Given** batch model selection is in progress
**When** each variable completes processing
**Then** a status update is printed:
```
[1/20] EBITDA: Testing 9 models...
  -> Best: ARIMA(1,1,1) | MAPE: 8.2% | MASE: 0.42
[2/20] Revenue: Testing 9 models...
  -> Best: Prophet | MAPE: 3.8% | MASE: 1.28 | Regressors: euribor_3m, diesel
...
[20/20] Complete!

## Summary
- Variables processed: 20
- Total runtime: 87 minutes
- Best performers: revenue (3.8%), co2_eua_price (0.2%)
- Needs attention: capacity_utilization (still high MAPE)
```

**Verification:**
- Progress format shows [N/Total] Variable: Status
- Best model and scores displayed per variable
- Summary section at completion
- Highlights best and worst performers

### AC-7b.5.8: Runtime Less Than 120 Minutes for All 20 Variables

**Given** batch model selection runs for all 20 forecasting variables
**When** using 4 parallel workers
**Then** total runtime is less than 120 minutes (2 hours)

**Verification:**
- Performance test with timeout assertion
- Parallel execution (4 workers) reduces runtime vs sequential
- TFT training uses reduced epochs (50) and early stopping
- Final runtime logged in summary

## Technical Specification

### Slash Command File

File: `.claude/commands/model-selection.md`

```yaml
---
argument-hint: [variable|--all] [--force] [--dry-run]
description: Run model selection for forecasting variables. Use --all for batch processing.
allowed-tools: Bash, Read, Grep, Task
---

# Model Selection Slash Command

## Usage

- `/model-selection <variable>` - Run selection for a single variable
- `/model-selection --all` - Run batch selection for all 20 variables (delegates to subagent)
- `/model-selection <variable> --force` - Force re-selection ignoring cache
- `/model-selection --all --dry-run` - Preview what would be selected without caching

## Single Variable Execution

For a single variable, execute:
```bash
uv run python -c "
import asyncio
from raglite.forecasting.model_selection import select_best_model
from raglite.external_data.storage import cache_model_selection

async def main():
    result = await select_best_model('$1', force_refresh='$2' == '--force')
    if '$2' != '--dry-run':
        await cache_model_selection(result)
    print(f'Best model: {result.best_model}')
    print(f'MAPE: {result.best_mape:.2%}')
    print(f'MASE: {result.best_mase:.2f}')
    print(f'Regressors: {result.best_regressor_set}')

asyncio.run(main())
"
```

## Batch Execution (--all)

When `--all` is specified, delegate to the model-selection-executor subagent:

> Use the model-selection-executor subagent to run batch model selection for all forecasting variables.
```

### Subagent File

File: `.claude/agents/model-selection-executor.md`

```yaml
---
name: model-selection-executor
description: Executes batch model selection for all forecasting variables. Use PROACTIVELY when model selection needs to run for multiple variables. Handles parallel CV across 9 models.
tools: Bash, Read, Grep, Write, Task
model: sonnet
---

# Model Selection Executor Subagent

## Purpose

This subagent autonomously executes batch model selection for all 20 forecasting variables in the RAGLite system. It handles:

1. **Parallel Execution:** Process 4 variables concurrently
2. **TFT Training:** Train TFT models on-demand with checkpoint caching
3. **Progress Tracking:** Report status as each variable completes
4. **Report Generation:** Create JSON + Markdown reports in reports/

## Variables to Process

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

## Execution Steps

1. **Initialize:**
   - Import run_batch_model_selection from model_selection_job.py
   - Verify PostgreSQL connection
   - Create reports/ directory if needed

2. **Execute Batch Processing:**
   ```bash
   uv run python -c "
   import asyncio
   from raglite.forecasting.model_selection_job import run_batch_model_selection

   async def main():
       results = await run_batch_model_selection(workers=4)
       print(f'Completed: {len(results)} variables')

   asyncio.run(main())
   "
   ```

3. **Monitor Progress:**
   - Watch stdout for [N/20] progress updates
   - Note any failures or warnings

4. **Verify Reports:**
   - Check reports/ for generated JSON and Markdown files
   - Display summary from Markdown report

5. **Validate Cache:**
   ```bash
   docker exec raglite-postgresql psql -U raglite -d raglite \
     -c "SELECT variable_name, best_model, best_mape FROM model_selection ORDER BY best_mape"
   ```

## Force Refresh

To ignore existing cache and re-run selection:
```bash
uv run python -c "
import asyncio
from raglite.forecasting.model_selection_job import run_batch_model_selection

asyncio.run(run_batch_model_selection(force_refresh=True, workers=4))
"
```

## Expected Runtime

- Target: <120 minutes for all 20 variables
- With 4 parallel workers: ~60-90 minutes typical
- TFT training adds ~5 minutes per variable (first run only)

## Output Format

Progress updates during execution:
```
[1/20] ebitda: Testing 9 models...
  -> Best: arima | MAPE: 8.2% | MASE: 0.42
[2/20] revenue: Testing 9 models...
  -> Best: prophet | MAPE: 3.8% | MASE: 1.28 | Regressors: euribor_3m, diesel
...
```

## Error Handling

- Individual variable failures are logged but don't stop batch
- At least 80% of variables should succeed
- Failed variables listed in summary for retry
```

### Core Python Module

File: `raglite/forecasting/model_selection_job.py`

```python
"""Batch model selection job for slash command execution.

This module provides the core logic for running model selection across
multiple forecasting variables in parallel, with progress tracking and
report generation.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from raglite.forecasting.model_selection import (
    select_best_model,
    ModelSelectionResult,
    CANDIDATE_MODELS,
)
from raglite.external_data.storage import cache_model_selection

logger = logging.getLogger(__name__)

# All 20 forecasting variables
ALL_VARIABLES = [
    # Financial
    "revenue",
    "turnover",
    "ebitda",
    "variable_cost",
    # Energy
    "electricity_cost",
    "thermal_cost",
    # Volume
    "sales_volume",
    "capacity_utilization",
    # Pricing
    "avg_selling_price",
    # External
    "ttf_gas",
    "api2_coal",
    "diesel",
    "eurostat_electricity",
    # Macro
    "gdp_growth",
    "inflation",
    "euribor_3m",
    # Construction
    "construction_output",
    "building_permits",
    "construction_confidence",
    # Carbon
    "co2_eua_price",
]


async def run_batch_model_selection(
    variables: list[str] | None = None,
    workers: int = 4,
    force_refresh: bool = False,
    output_dir: str = "reports",
) -> dict[str, ModelSelectionResult]:
    """Run model selection for multiple variables in parallel.

    Args:
        variables: List of variable names (default: ALL_VARIABLES)
        workers: Number of parallel workers (default: 4)
        force_refresh: Ignore existing cache and re-run selection
        output_dir: Directory for report output (default: "reports")

    Returns:
        Dictionary of variable_name -> ModelSelectionResult
    """
    start_time = datetime.now()
    variables = variables or ALL_VARIABLES
    results: dict[str, ModelSelectionResult] = {}
    errors: dict[str, str] = {}

    # Create semaphore for parallel limiting
    semaphore = asyncio.Semaphore(workers)

    async def process_variable(
        var_name: str, index: int, total: int
    ) -> tuple[str, ModelSelectionResult | Exception]:
        """Process a single variable with semaphore limiting."""
        async with semaphore:
            print(f"[{index}/{total}] {var_name}: Testing {len(CANDIDATE_MODELS)} models...")
            try:
                result = await select_best_model(var_name, force_refresh=force_refresh)

                # Format output
                reg_info = ""
                if result.best_with_regressors and result.best_regressor_set:
                    reg_info = f" | Regressors: {', '.join(result.best_regressor_set)}"

                print(
                    f"  -> Best: {result.best_model} | "
                    f"MAPE: {result.best_mape:.1%} | "
                    f"MASE: {result.best_mase:.2f}{reg_info}"
                )

                # Cache result immediately
                await cache_model_selection(result)

                return var_name, result

            except Exception as e:
                logger.error(f"Failed to process {var_name}: {e}")
                print(f"  -> ERROR: {e}")
                return var_name, e

    # Run all variables in parallel (limited by semaphore)
    tasks = [
        process_variable(var, i + 1, len(variables))
        for i, var in enumerate(variables)
    ]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results and errors
    for item in completed:
        if isinstance(item, Exception):
            # This shouldn't happen with return_exceptions=True in inner try/except
            logger.error(f"Unexpected error in gather: {item}")
        else:
            var_name, result_or_error = item
            if isinstance(result_or_error, Exception):
                errors[var_name] = str(result_or_error)
            else:
                results[var_name] = result_or_error

    # Calculate runtime
    end_time = datetime.now()
    runtime_minutes = (end_time - start_time).total_seconds() / 60

    # Print summary
    print("\n" + "=" * 60)
    print("## Summary")
    print(f"- Variables processed: {len(results)}/{len(variables)}")
    print(f"- Total runtime: {runtime_minutes:.1f} minutes")

    if results:
        # Find best and worst performers
        sorted_by_mape = sorted(results.items(), key=lambda x: x[1].best_mape)
        best_performers = sorted_by_mape[:3]
        worst_performers = sorted_by_mape[-3:]

        print(f"- Best performers: {', '.join(f'{v} ({r.best_mape:.1%})' for v, r in best_performers)}")
        print(f"- Needs attention: {', '.join(f'{v} ({r.best_mape:.1%})' for v, r in worst_performers)}")

    if errors:
        print(f"- Failures: {', '.join(errors.keys())}")

    print("=" * 60)

    # Generate reports
    await _generate_reports(results, errors, output_dir, runtime_minutes)

    return results


async def _generate_reports(
    results: dict[str, ModelSelectionResult],
    errors: dict[str, str],
    output_dir: str,
    runtime_minutes: float,
) -> None:
    """Generate JSON and Markdown reports.

    Args:
        results: Successful model selection results
        errors: Variables that failed with error messages
        output_dir: Directory for report output
        runtime_minutes: Total execution time in minutes
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # JSON report
    json_path = output_path / f"model-selection-{timestamp}.json"
    json_data = {
        "timestamp": timestamp,
        "runtime_minutes": runtime_minutes,
        "success_count": len(results),
        "error_count": len(errors),
        "results": {
            var: {
                "best_model": r.best_model,
                "best_mape": r.best_mape,
                "best_mase": r.best_mase,
                "use_regressors": r.best_with_regressors,
                "regressor_set": r.best_regressor_set,
                "cv_folds": r.cv_folds,
                "runtime_seconds": r.runtime_seconds,
                "candidate_count": len(r.candidate_results),
            }
            for var, r in results.items()
        },
        "errors": errors,
    }

    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)

    logger.info(f"JSON report written to {json_path}")

    # Markdown report
    md_path = output_path / f"model-selection-{timestamp}.md"
    md_lines = [
        "# Model Selection Report",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Runtime:** {runtime_minutes:.1f} minutes",
        f"**Variables:** {len(results)} succeeded, {len(errors)} failed",
        "",
        "## Results Summary",
        "",
        "| Variable | Best Model | MAPE | MASE | Regressors |",
        "|----------|------------|------|------|------------|",
    ]

    # Sort by MAPE for the table
    for var, r in sorted(results.items(), key=lambda x: x[1].best_mape):
        regs = ", ".join(r.best_regressor_set) if r.best_regressor_set else "-"
        md_lines.append(
            f"| {var} | {r.best_model} | {r.best_mape:.1%} | {r.best_mase:.2f} | {regs} |"
        )

    md_lines.extend([
        "",
        "## Best Performers",
        "",
    ])

    sorted_results = sorted(results.items(), key=lambda x: x[1].best_mape)
    for var, r in sorted_results[:5]:
        md_lines.append(f"- **{var}**: {r.best_model} with {r.best_mape:.1%} MAPE")

    if errors:
        md_lines.extend([
            "",
            "## Failures",
            "",
        ])
        for var, err in errors.items():
            md_lines.append(f"- **{var}**: {err}")

    md_lines.extend([
        "",
        "---",
        f"*Report generated by RAGLite model selection batch job*",
    ])

    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    logger.info(f"Markdown report written to {md_path}")
    print(f"\nReports saved to:")
    print(f"  - {json_path}")
    print(f"  - {md_path}")


async def run_single_variable_selection(
    variable_name: str,
    force_refresh: bool = False,
    dry_run: bool = False,
) -> ModelSelectionResult:
    """Run model selection for a single variable.

    Convenience function for slash command single-variable execution.

    Args:
        variable_name: Name of the variable to process
        force_refresh: Ignore cache and re-run selection
        dry_run: If True, don't cache the result

    Returns:
        ModelSelectionResult for the variable
    """
    print(f"Running model selection for {variable_name}...")
    print(f"Testing {len(CANDIDATE_MODELS)} models: {', '.join(CANDIDATE_MODELS)}")

    result = await select_best_model(variable_name, force_refresh=force_refresh)

    if not dry_run:
        await cache_model_selection(result)
        print(f"\nResult cached in PostgreSQL (expires in 7 days)")
    else:
        print(f"\nDry run - result NOT cached")

    # Display detailed results
    print("\n" + "=" * 60)
    print(f"## Model Selection Results for {variable_name}")
    print("=" * 60)
    print(f"Best Model: {result.best_model}")
    print(f"MAPE: {result.best_mape:.2%}")
    print(f"MASE: {result.best_mase:.2f}")
    print(f"Use Regressors: {result.best_with_regressors}")
    if result.best_regressor_set:
        print(f"Regressor Set: {', '.join(result.best_regressor_set)}")
    print(f"CV Folds: {result.cv_folds}")
    print(f"Runtime: {result.runtime_seconds:.1f} seconds")

    # Show candidate comparison table
    print("\n### All Candidates Tested")
    print("-" * 60)
    print(f"{'Model':<20} {'MAPE':>10} {'MASE':>10} {'Status':>15}")
    print("-" * 60)

    for config_key, metrics in sorted(
        result.candidate_results.items(),
        key=lambda x: x[1].get("mape", float("inf"))
    ):
        mape = metrics.get("mape", float("inf"))
        mase = metrics.get("mase", float("inf"))
        status = "ERROR" if "error" in metrics else ("BEST" if config_key.startswith(result.best_model) else "")

        if mape == float("inf"):
            mape_str = "N/A"
        else:
            mape_str = f"{mape:.2%}"

        if mase == float("inf"):
            mase_str = "N/A"
        else:
            mase_str = f"{mase:.2f}"

        print(f"{config_key:<20} {mape_str:>10} {mase_str:>10} {status:>15}")

    return result
```

### Files to Create

| File | Action | Lines |
|------|--------|-------|
| .claude/commands/model-selection.md | Create | ~50 |
| .claude/agents/model-selection-executor.md | Create | ~80 |
| raglite/forecasting/model_selection_job.py | Create | +250 |

## Tasks

- [ ] Task 1: Create slash command file (AC-7b.5.1)
  - [ ] 1.1 Create `.claude/commands/model-selection.md`
  - [ ] 1.2 Add YAML frontmatter with argument-hint and allowed-tools
  - [ ] 1.3 Document single-variable execution
  - [ ] 1.4 Document --all delegation to subagent
  - [ ] 1.5 Document --force and --dry-run flags

- [ ] Task 2: Create subagent file (AC-7b.5.2)
  - [ ] 2.1 Create `.claude/agents/model-selection-executor.md`
  - [ ] 2.2 Add YAML frontmatter with name, description, tools, model
  - [ ] 2.3 Document variables to process (20 total)
  - [ ] 2.4 Document execution steps
  - [ ] 2.5 Document error handling and expected runtime

- [ ] Task 3: Create model_selection_job.py module (AC-7b.5.3)
  - [ ] 3.1 Create `raglite/forecasting/model_selection_job.py`
  - [ ] 3.2 Define ALL_VARIABLES list with 20 variables
  - [ ] 3.3 Add imports for model_selection and storage modules
  - [ ] 3.4 Add logging configuration

- [ ] Task 4: Implement run_batch_model_selection() (AC-7b.5.3, AC-7b.5.4, AC-7b.5.5)
  - [ ] 4.1 Add function signature with workers, force_refresh, output_dir params
  - [ ] 4.2 Create asyncio.Semaphore for parallel limiting
  - [ ] 4.3 Implement process_variable() inner function
  - [ ] 4.4 Call select_best_model() for each variable
  - [ ] 4.5 Call cache_model_selection() after each completion
  - [ ] 4.6 Collect results and errors
  - [ ] 4.7 Print summary at completion

- [ ] Task 5: Implement progress logging (AC-7b.5.7)
  - [ ] 5.1 Print [N/Total] format for each variable
  - [ ] 5.2 Show best model and scores per variable
  - [ ] 5.3 Show regressor info if applicable
  - [ ] 5.4 Print summary section at completion
  - [ ] 5.5 Highlight best and worst performers

- [ ] Task 6: Implement _generate_reports() (AC-7b.5.6)
  - [ ] 6.1 Create reports/ directory if not exists
  - [ ] 6.2 Generate JSON report with timestamp filename
  - [ ] 6.3 Include all ModelSelectionResult data in JSON
  - [ ] 6.4 Generate Markdown report with summary table
  - [ ] 6.5 Include best performers and failures sections
  - [ ] 6.6 Log report file paths

- [ ] Task 7: Implement run_single_variable_selection() helper
  - [ ] 7.1 Add function for single-variable execution
  - [ ] 7.2 Support force_refresh and dry_run flags
  - [ ] 7.3 Display detailed results and candidate comparison table
  - [ ] 7.4 Cache result unless dry_run

- [ ] Task 8: Write unit tests (all ACs)
  - [ ] 8.1 Create tests/unit/test_model_selection_job.py
  - [ ] 8.2 Test ALL_VARIABLES list completeness
  - [ ] 8.3 Test run_batch_model_selection with mocked dependencies
  - [ ] 8.4 Test _generate_reports() output format
  - [ ] 8.5 Test run_single_variable_selection()

- [ ] Task 9: Write integration tests (AC-7b.5.8)
  - [ ] 9.1 Create tests/integration/test_model_selection_job.py
  - [ ] 9.2 Test batch execution with real database
  - [ ] 9.3 Test parallel execution with semaphore
  - [ ] 9.4 Test report generation to filesystem
  - [ ] 9.5 Performance test with <120 minute assertion

- [ ] Task 10: Validation (MANDATORY)
  - [ ] 10.1 Verify slash command file syntax
  - [ ] 10.2 Verify subagent file syntax
  - [ ] 10.3 Run unit tests: `uv run pytest tests/unit/test_model_selection_job.py -v`
  - [ ] 10.4 Run integration tests: `uv run pytest tests/integration/test_model_selection_job.py -v`
  - [ ] 10.5 Test slash command manually: `/model-selection ebitda`
  - [ ] 10.6 Test batch execution: `/model-selection --all`
  - [ ] 10.7 Verify reports generated in reports/ directory
  - [ ] 10.8 Verify cache entries in PostgreSQL

## Dev Notes

### Architecture References

- [Source: docs/prd/epic-7-intelligent-model-selection.md#Story 7.5]
- [Source: docs/architecture/5-technology-stack-definitive.md]
- [Source: raglite/forecasting/model_selection.py] - Story 7b-3 select_best_model()
- [Source: raglite/external_data/storage.py] - Story 7b-4 cache_model_selection()

### Existing Patterns to Follow

**Slash Command Pattern (.claude/commands/):**
```yaml
---
argument-hint: [args]
description: Brief description
allowed-tools: Tool1, Tool2
---

# Command Name

Instructions for Claude Code to execute...
```

**Subagent Pattern (.claude/agents/):**
```yaml
---
name: agent-name
description: What the agent does
tools: Tool1, Tool2, Tool3
model: sonnet
---

# Agent Name

Purpose and execution steps...
```

**Async Batch Pattern:**
```python
semaphore = asyncio.Semaphore(workers)

async def process_item(item):
    async with semaphore:
        # Limited concurrent execution
        return await do_work(item)

results = await asyncio.gather(*[process_item(i) for i in items])
```

### Key Technical Details

1. **Parallel Execution:**
   - asyncio.Semaphore limits to 4 concurrent workers
   - Prevents overwhelming database/model resources
   - Still significantly faster than sequential execution

2. **Progress Format:**
   - [N/Total] prefix for easy tracking
   - Best model and key scores on each completion
   - Summary section with overall statistics

3. **Report Generation:**
   - JSON for programmatic consumption
   - Markdown for human readability
   - Timestamp in filename for versioning

4. **Slash Command Delegation:**
   - Single variable: Execute directly
   - Batch (--all): Delegate to subagent for autonomous processing

### Variables List (20 Total)

| Category | Variables | Count |
|----------|-----------|-------|
| Financial | revenue, turnover, ebitda, variable_cost | 4 |
| Energy | electricity_cost, thermal_cost | 2 |
| Volume | sales_volume, capacity_utilization | 2 |
| Pricing | avg_selling_price | 1 |
| External | ttf_gas, api2_coal, diesel, eurostat_electricity | 4 |
| Macro | gdp_growth, inflation, euribor_3m | 3 |
| Construction | construction_output, building_permits, construction_confidence | 3 |
| Carbon | co2_eua_price | 1 |
| **Total** | | **20** |

### Performance Budget

| Scenario | Target Time |
|----------|-------------|
| Single variable | <10 minutes |
| All 20 variables (4 workers) | <120 minutes |
| Report generation | <10 seconds |

### NFRs

- **Runtime:** <120 minutes for full batch (20 variables, 4 workers)
- **Parallelism:** 4 concurrent workers maximum
- **Report Format:** Valid JSON and readable Markdown
- **Test Coverage:** 80%+ for new code
- **Error Handling:** Individual failures don't stop batch

## Testing Requirements

### Unit Tests (tests/unit/test_model_selection_job.py)

- Test ALL_VARIABLES list has 20 entries
- Test run_batch_model_selection with mocked select_best_model
- Test _generate_reports creates both JSON and Markdown
- Test run_single_variable_selection output format
- Test progress logging format
- Test error handling for failed variables

### Integration Tests (tests/integration/test_model_selection_job.py)

- Test batch execution with real database connection
- Test parallel execution respects semaphore limit
- Test reports generated to filesystem
- Test cache populated after batch completion
- Performance test: <120 minutes for all variables

### Validation Checklist

```bash
# Verify slash command syntax
cat .claude/commands/model-selection.md

# Verify subagent syntax
cat .claude/agents/model-selection-executor.md

# Unit tests
uv run pytest tests/unit/test_model_selection_job.py -v

# Integration tests
APP_ENV=test uv run pytest tests/integration/test_model_selection_job.py -v

# Manual test - single variable
# In Claude Code session:
# /model-selection ebitda

# Manual test - batch (invokes subagent)
# In Claude Code session:
# /model-selection --all

# Verify reports generated
ls -la reports/model-selection-*.json reports/model-selection-*.md

# Verify cache populated
docker exec raglite-postgresql psql -U raglite -d raglite \
  -c "SELECT variable_name, best_model, best_mape FROM model_selection ORDER BY best_mape"
```

## Definition of Done

- [ ] All 8 acceptance criteria verified with passing tests
- [ ] Slash command file created at `.claude/commands/model-selection.md`
- [ ] Subagent file created at `.claude/agents/model-selection-executor.md`
- [ ] `model_selection_job.py` implemented with batch and single-variable functions
- [ ] Unit tests passing with 80%+ coverage on new code
- [ ] Integration tests passing
- [ ] Performance test confirms <120 minutes for all 20 variables
- [ ] Reports generated in correct format
- [ ] Cache entries visible in PostgreSQL after batch run
- [ ] Docstrings added to all public functions
- [ ] Ready for Story 7b-6 (MCP Integration)

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

(To be filled during implementation)

### Debug Log References

N/A

### Completion Notes List

(To be filled during implementation)

### File List

**To Create:**
- `.claude/commands/model-selection.md` - Slash command for model selection
- `.claude/agents/model-selection-executor.md` - Subagent for batch processing
- `raglite/forecasting/model_selection_job.py` - Batch execution module
- `tests/unit/test_model_selection_job.py` - Unit tests
- `tests/integration/test_model_selection_job.py` - Integration tests

**To Reference:**
- `raglite/forecasting/model_selection.py` - Story 7b-3 select_best_model()
- `raglite/external_data/storage.py` - Story 7b-4 cache_model_selection()

### Change Log

- 2025-12-21: Story drafted with all 8 acceptance criteria in BDD format
