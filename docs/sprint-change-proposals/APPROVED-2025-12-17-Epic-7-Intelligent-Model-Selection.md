Epic 7: Intelligent Model Selection Framework

 Document Info

 - Type: Epic PRD / Technical Specification
 - Status: READY FOR IMPLEMENTATION
 - Created: 2025-12-17
 - Epic Owner: Dev Team

 ---
 Executive Summary

 Implement intelligent per-variable model selection for RAGLite forecasting by leveraging ALL available models through
 cross-validation. Currently, Prophet is used for all variables regardless of data characteristics, resulting in poor accuracy for
 some metrics (EBITDA: 84.77% MAPE). This epic adds ARIMA/ETS models and creates a selection framework that chooses the optimal
 model per variable.

 Complete Model Inventory

 | Model              | Status   | Best For                    | Implementation                |
 |--------------------|----------|-----------------------------|-------------------------------|
 | Prophet            | Existing | Regime changes, seasonality | hybrid.py                     |
 | XGBoost            | Existing | High-dimensional features   | hybrid.py                     |
 | LightGBM           | Existing | Fast gradient boosting      | hybrid.py                     |
 | CatBoost           | Existing | Categorical variables       | hybrid.py                     |
 | Chronos-2          | Existing | Cold-start, zero-shot       | hybrid.py                     |
 | TFT                | Existing | Complex multivariate        | hybrid.py (requires training) |
 | Linear/Ridge/Lasso | Existing | Simple trends               | hybrid.py                     |
 | ARIMA/SARIMA       | NEW      | Stationary financial data   | Story 7.1                     |
 | ETS                | NEW      | Trend + seasonality         | Story 7.1                     |

 Total: 9 models available for intelligent selection

 ---
 Problem Statement

 Current Issues

 | Variable             | Current MAPE | Target | Root Cause                           |
 |----------------------|--------------|--------|--------------------------------------|
 | EBITDA               | 84.77%       | <5%    | Prophet over-predicts (bias +15.47)  |
 | Capacity Utilization | 104.49%      | <10%   | Wrong model for operational data     |
 | Electricity Cost     | 121.57%      | <8%    | MASE 6.11 - worse than naive         |
 | Sales Volume         | 27.16%       | <10%   | No model selection for seasonal data |

 Root Cause Analysis

 1. No model selection - Prophet used regardless of data characteristics
 2. Missing statistical models - ARIMA/ETS not available for stationary data
 3. No data analysis - Stationarity/seasonality not considered
 4. Static configuration - No per-variable optimization

 ---
 Solution Architecture

 ┌─────────────────────────────────────────────────────────────────────────┐
 │                     MODEL SELECTION FRAMEWORK                            │
 ├─────────────────────────────────────────────────────────────────────────┤
 │                                                                          │
 │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
 │  │ DATA         │───▶│ MODEL        │───▶│ POSTGRESQL CACHE         │  │
 │  │ ANALYZER     │    │ SELECTION    │    │ (model_selection table)  │  │
 │  │              │    │ (CV-based)   │    │                          │  │
 │  │ • ADF/KPSS   │    │              │    │ • best_model             │  │
 │  │ • ACF/PACF   │    │ 9 MODELS:    │    │ • regressors             │  │
 │  │ • Trend      │    │ • ARIMA      │    │ • MAPE/MASE              │  │
 │  │ • Seasonality│    │ • ETS        │    │ • 7-day TTL              │  │
 │  │ • Volatility │    │ • Prophet    │    │                          │  │
 │  └──────────────┘    │ • XGBoost    │    └──────────────────────────┘  │
 │                      │ • LightGBM   │               │                   │
 │                      │ • CatBoost   │               │                   │
 │                      │ • Chronos-2  │               ▼                   │
 │                      │ • TFT        │    ┌──────────────────────────┐  │
 │                      │ • Linear     │    │ MCP QUERY (<5s)          │  │
 │                      └──────────────┘    │                          │  │
 │                                          │ Cache lookup → Selected  │  │
 │                                          │ model → Forecast         │  │
 │                                          └──────────────────────────┘  │
 └─────────────────────────────────────────────────────────────────────────┘

 ---
 Stories

 Story 7.1: Add ARIMA/ETS Model Wrappers

 Priority: P0 | Effort: 1 day

 Goal: Implement fit_arima() and fit_ets() functions matching existing model patterns.

 Acceptance Criteria:
 - AC1: fit_arima() using pmdarima's auto_arima for automatic (p,d,q) selection
 - AC2: fit_ets() using statsmodels ExponentialSmoothing
 - AC3: Both support exogenous variables (ARIMAX/ETSX)
 - AC4: Handle monthly (M) and quarterly (Q) frequencies
 - AC5: Return predictions + confidence intervals matching ForecastPoint
 - AC6: Graceful fallback if fitting fails
 - AC7: Unit tests with >80% coverage

 Technical Specification:

 # New dependency: pyproject.toml
 "pmdarima>=2.0,<3.0"

 # In hybrid.py
 async def fit_arima(
     y_train: pd.Series,
     X_train: pd.DataFrame | None = None,  # Exogenous regressors
     forecast_horizon: int = 4,
     frequency: str = "M",
 ) -> tuple[Any, dict, np.ndarray, np.ndarray]:
     """Fit ARIMA using pmdarima auto_arima."""
     import pmdarima as pm

     model = pm.auto_arima(
         y_train, X=X_train,
         seasonal=True, m=12 if frequency == "M" else 4,
         stepwise=True, suppress_warnings=True,
         max_p=3, max_q=3, max_d=2,
         information_criterion='aic',
     )
     predictions, conf_int = model.predict(
         n_periods=forecast_horizon,
         X=X_future,
         return_conf_int=True
     )
     return model, {"aic": model.aic(), "order": model.order}, predictions, conf_int


 async def fit_ets(
     y_train: pd.Series,
     forecast_horizon: int = 4,
     frequency: str = "M",
 ) -> tuple[Any, dict, np.ndarray, np.ndarray]:
     """Fit ETS using statsmodels ExponentialSmoothing."""
     from statsmodels.tsa.holtwinters import ExponentialSmoothing

     model = ExponentialSmoothing(
         y_train,
         trend='add', seasonal='add', damped_trend=True,
         seasonal_periods=12 if frequency == "M" else 4,
     ).fit(optimized=True)

     forecast = model.get_forecast(steps=forecast_horizon)
     return model, {"aic": model.aic}, forecast.predicted_mean, forecast.conf_int()

 Files to Modify:
 | File                                | Action        | Lines |
 |-------------------------------------|---------------|-------|
 | raglite/forecasting/hybrid.py       | Add functions | +200  |
 | pyproject.toml                      | Add pmdarima  | +1    |
 | tests/unit/test_arima_ets_models.py | Create        | +150  |

 ---
 Story 7.2: Data Characteristics Analyzer

 Priority: P0 | Effort: 1 day

 Goal: Implement statistical tests to analyze time-series for model pre-selection.

 Acceptance Criteria:
 - AC1: Combined ADF + KPSS stationarity test
 - AC2: Seasonality detection via ACF peak analysis
 - AC3: Trend detection via linear regression
 - AC4: Volatility measurement (coefficient of variation)
 - AC5: Data quality metrics (gaps, outliers, length)
 - AC6: Return DataCharacteristics with model recommendations
 - AC7: Unit tests for all analyzers

 Technical Specification:

 # New file: raglite/forecasting/data_analyzer.py

 from dataclasses import dataclass
 from enum import Enum
 from statsmodels.tsa.stattools import adfuller, kpss, acf

 class Stationarity(Enum):
     STATIONARY = "stationary"
     TREND_STATIONARY = "trend_stationary"
     DIFFERENCE_STATIONARY = "difference_stationary"
     NON_STATIONARY = "non_stationary"

 class SeasonalityType(Enum):
     NONE = "none"
     ADDITIVE = "additive"
     MULTIPLICATIVE = "multiplicative"

 @dataclass
 class DataCharacteristics:
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

     # Volatility
     coefficient_of_variation: float

     # Data quality
     data_length: int
     missing_ratio: float
     outlier_count: int

     # Recommendations
     recommended_models: list[str]
     model_rationale: str


 def analyze_data_characteristics(series: pd.Series, frequency: str = "M") -> DataCharacteristics:
     """Analyze time-series for model selection."""
     # ADF test (null: non-stationary)
     adf_p = adfuller(series, autolag='AIC')[1]

     # KPSS test (null: stationary)
     kpss_p = kpss(series, regression='c', nlags='auto')[1]

     # Combined interpretation (Kwiatkowski protocol)
     if adf_p < 0.05 and kpss_p > 0.05:
         stationarity = Stationarity.STATIONARY
     elif adf_p >= 0.05 and kpss_p <= 0.05:
         stationarity = Stationarity.NON_STATIONARY
     else:
         stationarity = Stationarity.TREND_STATIONARY

     # Seasonality via ACF
     seasonal_period = 12 if frequency == "M" else 4
     acf_vals = acf(series, nlags=seasonal_period * 2)
     seasonal_strength = abs(acf_vals[seasonal_period])

     # Model recommendations based on characteristics
     models = _recommend_models(stationarity, seasonal_strength, ...)

     return DataCharacteristics(...)

 Files to Create:
 | File                                 | Action | Lines |
 |--------------------------------------|--------|-------|
 | raglite/forecasting/data_analyzer.py | Create | +350  |
 | tests/unit/test_data_analyzer.py     | Create | +200  |

 ---
 Story 7.3: Per-Variable Model Selection via Cross-Validation

 Priority: P0 | Effort: 2.5 days

 Goal: Cross-validate ALL 9 models per variable and select optimal.

 Acceptance Criteria:
 - AC1: select_best_model() with TimeSeriesSplit CV
 - AC2: Test ALL 9 models: ARIMA, ETS, Prophet, XGBoost, LightGBM, CatBoost, Chronos-2, TFT, Linear
 - AC3: Compare with/without regressors for each model
 - AC4: Select winner by holdout MAPE (primary) + MASE (secondary)
 - AC5: Skip models that fail gracefully
 - AC6: Return ModelSelectionResult with all candidates
 - AC7: Runtime <10 minutes per variable

 Technical Specification:

 # New file: raglite/forecasting/model_selection.py

 from dataclasses import dataclass
 from sklearn.model_selection import TimeSeriesSplit

 # All 9 available models
 CANDIDATE_MODELS = [
     "arima",      # NEW - Story 7.1
     "ets",        # NEW - Story 7.1
     "prophet",    # Existing
     "xgboost",    # Existing
     "lightgbm",   # Existing
     "catboost",   # Existing
     "chronos",    # Existing (Chronos-2)
     "tft",        # Existing (if trained)
     "linear",     # Existing (Linear/Ridge/Lasso)
 ]

 @dataclass
 class ModelSelectionResult:
     variable_name: str
     best_model: str
     best_mape: float
     best_mase: float
     best_with_regressors: bool
     best_regressor_set: list[str]
     candidate_results: dict[str, dict]  # All models tested
     data_characteristics: DataCharacteristics
     cv_folds: int
     runtime_seconds: float


 async def select_best_model(
     variable_name: str,
     historical_data: pd.Series,
     external_regressors: dict[str, pd.Series] | None = None,
     cv_folds: int = 5,
 ) -> ModelSelectionResult:
     """Select best model for variable via cross-validation."""

     # 1. Analyze data characteristics
     data_chars = analyze_data_characteristics(historical_data)

     # 2. Pre-filter models based on data
     candidate_models = _filter_candidates(data_chars, CANDIDATE_MODELS)

     # 3. Cross-validate each model
     tscv = TimeSeriesSplit(n_splits=cv_folds)
     results = {}

     for model_name in candidate_models:
         for use_regs in [False, True]:
             try:
                 cv_metrics = await _cv_evaluate(
                     model_name, historical_data,
                     external_regressors if use_regs else None,
                     tscv
                 )
                 results[f"{model_name}_{use_regs}"] = cv_metrics
             except Exception as e:
                 logger.warning(f"Model {model_name} failed: {e}")

     # 4. Select best by MAPE, then MASE
     best = min(results.items(), key=lambda x: (x[1]["mape"], x[1]["mase"]))

     return ModelSelectionResult(
         variable_name=variable_name,
         best_model=best[0].split("_")[0],
         best_mape=best[1]["mape"],
         ...
     )

 Model Selection Logic:

 For each variable:
   1. Run data analyzer → get characteristics
   2. Pre-filter models:
      - If non-stationary → prefer ARIMA, ETS, Prophet
      - If seasonal → prefer SARIMA, Prophet, ETS
      - If high volatility → prefer XGBoost, LightGBM
      - If cold-start (<12 points) → prefer Chronos-2
      - TFT always included (trained on-demand)
   3. TFT Training (if needed):
      - Check for existing checkpoint: models/tft/{variable_name}/
      - If missing or >7 days old → train with reduced epochs (50)
      - Save checkpoint for future CV runs
   4. Cross-validate remaining candidates (5-fold)
   5. Select winner by MAPE (primary), MASE (secondary)
   6. Cache result in PostgreSQL

 TFT Training Integration:

 TFT (Temporal Fusion Transformer) requires training before evaluation. During batch model selection:

 1. On-Demand Training: TFT is trained per variable during CV if checkpoint missing
 2. Checkpoint Caching: Trained models saved to models/tft/{variable_name}/
 3. TTL Alignment: Checkpoints expire at same 7-day TTL as model selection cache
 4. Reduced Epochs: Use max_epochs=50 (vs 100) for faster batch processing
 5. Early Stopping: Stop training if validation loss plateaus for 5 epochs
 6. GPU Acceleration: Auto-detect CUDA/MPS for faster training

 Files to Create:
 | File                                      | Action | Lines |
 |-------------------------------------------|--------|-------|
 | raglite/forecasting/model_selection.py    | Create | +500  |
 | tests/integration/test_model_selection.py | Create | +250  |

 ---
 Story 7.4: Model Selection Cache in PostgreSQL

 Priority: P0 | Effort: 1 day

 Goal: Cache selection results for fast MCP query-time lookups.

 Acceptance Criteria:
 - AC1: New model_selection PostgreSQL table
 - AC2: Store best_model, regressors, MAPE, MASE per variable
 - AC3: get_cached_model_selection() with <100ms lookup
 - AC4: invalidate_model_selection() for manual refresh
 - AC5: 7-day TTL with automatic expiration
 - AC6: Migration script

 Database Schema:

 -- migrations/006_add_model_selection.sql

 CREATE TABLE model_selection (
     id SERIAL PRIMARY KEY,
     variable_name VARCHAR(100) NOT NULL UNIQUE,
     best_model VARCHAR(50) NOT NULL,
     best_mape NUMERIC(8,4) NOT NULL,
     best_mase NUMERIC(8,4),
     use_regressors BOOLEAN DEFAULT FALSE,
     regressor_list JSONB,
     candidate_results JSONB,
     data_characteristics JSONB,
     selected_at TIMESTAMP DEFAULT NOW(),
     expires_at TIMESTAMP NOT NULL
 );

 CREATE INDEX idx_model_selection_variable ON model_selection(variable_name);
 CREATE INDEX idx_model_selection_expires ON model_selection(expires_at);

 Files to Modify:
 | File                                   | Action            | Lines |
 |----------------------------------------|-------------------|-------|
 | raglite/external_data/orm_models.py    | Add ORM           | +40   |
 | raglite/external_data/storage.py       | Add cache methods | +100  |
 | migrations/006_add_model_selection.sql | Create            | +20   |

 ---
 Story 7.5: Model Selection Slash Commands & Subagent

 Priority: P0 | Effort: 1 day

 Goal: Claude Code slash commands and subagent to run model selection on-demand.

 Acceptance Criteria:
 - AC1: /model-selection slash command for batch and single-variable selection
 - AC2: model-selection-executor subagent for autonomous batch processing
 - AC3: run_batch_model_selection() Python function for core logic
 - AC4: Parallel execution (4 workers) within subagent
 - AC5: Cache results in PostgreSQL
 - AC6: Generate JSON + Markdown report to reports/
 - AC7: Progress logging with status updates
 - AC8: Runtime <120 minutes for all 20 variables

 ---
 Slash Command: /model-selection

 File: .claude/commands/model-selection.md

 ---
 argument-hint: [variable|--all] [--force] [--dry-run]
 description: Run model selection for forecasting variables. Use --all for batch processing.
 allowed-tools: Bash, Read, Grep, Task
 ---

 # Model Selection Command

 Run intelligent model selection for RAGLite forecasting variables.

 ## Arguments
 - `$1`: Variable name OR `--all` for all 20 variables
 - `$2`: Optional: `--force` to ignore cache, `--dry-run` for preview

 ## Current Cache Status
 !`docker exec raglite-postgresql psql -U raglite -d raglite -t -c "SELECT COUNT(*) FROM model_selection WHERE expires_at > NOW()"
 2>/dev/null || echo "0"` variables cached

 ## Action

 Based on the arguments provided: $ARGUMENTS

 If running for all variables or multiple variables, delegate to the model-selection-executor subagent.

 If running for a single variable:
 1. Call `select_best_model()` from `raglite/forecasting/model_selection.py`
 2. Display results with model comparison table
 3. Update PostgreSQL cache

 If --dry-run: Show what would be selected without caching.
 If --force: Ignore existing cache and re-run selection.

 ---
 Subagent: model-selection-executor

 File: .claude/agents/model-selection-executor.md

 ---
 name: model-selection-executor
 description: Executes batch model selection for all forecasting variables. Use PROACTIVELY when model selection needs to run for
 multiple variables. Handles parallel CV across 9 models.
 tools: Bash, Read, Grep, Write, Task
 model: sonnet
 ---

 # Model Selection Executor Agent

 You are a specialized agent for executing batch model selection across RAGLite forecasting variables.

 ## Your Capabilities

 1. **Batch Processing**: Run model selection for all 20 variables
 2. **TFT Training**: Train TFT models per variable (on-demand during CV)
 3. **Parallel Execution**: Process 4 variables concurrently
 4. **Progress Tracking**: Report status as each variable completes
 5. **Report Generation**: Create JSON + Markdown reports

 ## Execution Process

 ### Step 1: Initialize
 ```bash
 # Check current cache status
 docker exec raglite-postgresql psql -U raglite -d raglite -c \
   "SELECT variable_name, best_model, best_mape, expires_at FROM model_selection ORDER BY variable_name"

 Step 2: TFT Training (On-Demand)

 For TFT to be included in model selection, it must be trained per variable:

 from raglite.forecasting.hybrid import _train_tft_model

 # Train TFT during CV if not already trained for this variable
 # Models saved to: models/tft/{variable_name}/
 tft_checkpoint = await _train_tft_model(
     variable_name=var_name,
     historical_data=data,
     max_epochs=50,  # Reduced for batch processing
     early_stopping_patience=5,
 )

 TFT Training Strategy:
 - Train with max_epochs=50 (reduced from 100 for faster batch)
 - Early stopping if validation loss plateaus
 - Save checkpoint per variable to models/tft/{variable_name}/
 - Skip training if checkpoint exists and is <7 days old
 - GPU acceleration if available (CUDA/MPS)

 Step 3: Run Selection

 For each variable, invoke the model selection logic:

 from raglite.forecasting.model_selection import select_best_model
 from raglite.forecasting.model_selection_job import run_batch_model_selection

 # For batch processing (includes TFT training)
 results = await run_batch_model_selection(
     variables=ALL_VARIABLES,  # 20 variables
     workers=4,  # Parallel workers
     force_refresh=False,  # Or True if --force
     train_tft=True,  # Train TFT models during CV
 )

 Step 4: Report Results

 After completion, generate:
 1. reports/model-selection-YYYYMMDD-HHMMSS.json - Full results
 2. reports/model-selection-YYYYMMDD-HHMMSS.md - Summary report

 Step 5: Cache Update

 All results are automatically cached in PostgreSQL with 7-day TTL.

 Variables to Process

 | Category     | Variables                                                      |
 |--------------|----------------------------------------------------------------|
 | Financial    | revenue, turnover, ebitda, variable_cost                       |
 | Energy       | electricity_cost, thermal_cost                                 |
 | Volume       | sales_volume, capacity_utilization                             |
 | Pricing      | avg_selling_price                                              |
 | External     | ttf_gas, api2_coal, diesel, eurostat_electricity               |
 | Macro        | gdp_growth, inflation, euribor_3m                              |
 | Construction | construction_output, building_permits, construction_confidence |
 | Carbon       | co2_eua_price                                                  |

 Output Format

 Report progress as:
 [1/20] EBITDA: Testing 9 models...
   → Best: ARIMA(1,1,1) | MAPE: 8.2% | MASE: 0.42
 [2/20] Revenue: Testing 9 models...
   → Best: Prophet | MAPE: 3.8% | MASE: 1.28 | Regressors: euribor_3m, diesel
 ...
 [20/20] Complete!

 ## Summary
 - Variables processed: 20
 - Total runtime: 87 minutes
 - Best performers: revenue (3.8%), co2_eua_price (0.2%)
 - Needs attention: capacity_utilization (still high MAPE)

 ---

 #### Core Python Module

 **File:** `raglite/forecasting/model_selection_job.py`

 ```python
 """Batch model selection job for slash command execution."""

 import asyncio
 from datetime import datetime
 from pathlib import Path

 from raglite.forecasting.model_selection import (
     select_best_model,
     ModelSelectionResult,
     CANDIDATE_MODELS,
 )
 from raglite.external_data.storage import cache_model_selection
 from raglite.shared.config import settings

 ALL_VARIABLES = [
     "revenue", "turnover", "ebitda", "variable_cost",
     "electricity_cost", "thermal_cost",
     "sales_volume", "capacity_utilization",
     "avg_selling_price",
     "ttf_gas", "api2_coal", "diesel", "eurostat_electricity",
     "gdp_growth", "inflation", "euribor_3m",
     "construction_output", "building_permits", "construction_confidence",
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
         workers: Number of parallel workers
         force_refresh: Ignore existing cache
         output_dir: Directory for report output

     Returns:
         Dictionary of variable_name -> ModelSelectionResult
     """
     variables = variables or ALL_VARIABLES
     results = {}

     # Create semaphore for parallel limiting
     semaphore = asyncio.Semaphore(workers)

     async def process_variable(var_name: str, index: int) -> tuple[str, ModelSelectionResult]:
         async with semaphore:
             print(f"[{index}/{len(variables)}] {var_name}: Testing {len(CANDIDATE_MODELS)} models...")
             result = await select_best_model(var_name, force_refresh=force_refresh)
             print(f"  → Best: {result.best_model} | MAPE: {result.best_mape:.2%} | MASE: {result.best_mase:.2f}")

             # Cache result
             await cache_model_selection(result)
             return var_name, result

     # Run in parallel
     tasks = [
         process_variable(var, i + 1)
         for i, var in enumerate(variables)
     ]
     completed = await asyncio.gather(*tasks, return_exceptions=True)

     # Collect results
     for item in completed:
         if isinstance(item, Exception):
             print(f"Error: {item}")
         else:
             var_name, result = item
             results[var_name] = result

     # Generate reports
     await _generate_reports(results, output_dir)

     return results


 async def _generate_reports(results: dict[str, ModelSelectionResult], output_dir: str):
     """Generate JSON and Markdown reports."""
     timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
     output_path = Path(output_dir)
     output_path.mkdir(exist_ok=True)

     # JSON report
     json_path = output_path / f"model-selection-{timestamp}.json"
     # ... serialize results to JSON

     # Markdown report
     md_path = output_path / f"model-selection-{timestamp}.md"
     # ... generate markdown summary table

 ---
 Files to Create:
 | File                                       | Action | Lines |
 |--------------------------------------------|--------|-------|
 | .claude/commands/model-selection.md        | Create | ~50   |
 | .claude/agents/model-selection-executor.md | Create | ~80   |
 | raglite/forecasting/model_selection_job.py | Create | +250  |

 ---
 Usage Examples

 # Via Claude Code slash command
 > /model-selection ebitda
 # Runs selection for single variable, shows results

 > /model-selection --all
 # Delegates to model-selection-executor subagent for batch processing

 > /model-selection revenue --force
 # Force re-selection ignoring cache

 > /model-selection --all --dry-run
 # Preview what would be selected without caching

 Direct subagent invocation:
 > Use the model-selection-executor subagent to run model selection for all variables

 > Have the model-selection-executor rerun selection with --force for financial metrics

 ---
 Story 7.6: MCP Integration with Model Selection

 Priority: P0 | Effort: 1.5 days

 Goal: Use cached model selection in get_financial_forecast MCP tool.

 Acceptance Criteria:
 - AC1: Modify generate_forecast() to check cache first
 - AC2: Route to correct model (ARIMA/ETS/Prophet/XGBoost/etc.)
 - AC3: Use selected regressor set from cache
 - AC4: Fallback to Prophet if cache miss or model fails
 - AC5: Add model_source and model_selection_reason to response
 - AC6: Maintain <5s query time with cache hit
 - AC7: E2E tests for MCP integration

 Modified Flow:

 # In hybrid.py - generate_forecast()

 async def generate_forecast(
     metric: str,
     historical_data: TimeSeriesData,
     periods_ahead: int = 4,
     external_regressors: dict | None = None,
     use_model_selection: bool = True,  # NEW
 ) -> ForecastResult:

     # 1. Check model selection cache
     if use_model_selection:
         cached = get_cached_model_selection(metric)
         if cached and not cached.is_expired:
             model_to_use = cached.best_model
             regressor_set = cached.best_regressor_set if cached.use_regressors else None
             model_source = "cached"
         else:
             model_to_use = "prophet"  # Default fallback
             model_source = "default"

     # 2. Route to appropriate model
     if model_to_use == "arima":
         result = await _generate_arima_forecast(...)
     elif model_to_use == "ets":
         result = await _generate_ets_forecast(...)
     elif model_to_use == "xgboost":
         result = await _generate_xgboost_forecast(...)
     elif model_to_use == "chronos":
         result = await _generate_chronos_forecast(...)
     elif model_to_use == "tft":
         result = await _generate_tft_forecast(...)
     else:  # prophet, linear, lightgbm, catboost
         result = await _generate_prophet_forecast(...)

     # 3. Add selection metadata
     result.model_source = model_source
     result.model_selection_reason = cached.data_characteristics.model_rationale

     return result

 Enhanced MCP Response:

 {
   "metric_name": "ebitda",
   "forecast": [...],
   "model_type": "arima_1_1_1",
   "model_source": "cached",
   "model_selection_reason": "ARIMA selected: data is difference-stationary (ADF p=0.02), low seasonality (strength=0.12). CV MAPE:
  8.2% vs Prophet 84.7%",
   "regressors_used": null,
   "confidence_reasoning": "..."
 }

 Files to Modify:
 | File                                  | Action                                      | Lines |
 |---------------------------------------|---------------------------------------------|-------|
 | raglite/forecasting/hybrid.py         | Modify generate_forecast, add model routers | +300  |
 | raglite/shared/models.py              | Add model_source, model_selection_reason    | +10   |
 | raglite/main.py                       | Update ForecastQueryResponse                | +20   |
 | tests/e2e/test_mcp_model_selection.py | Create                                      | +150  |

 ---
 Expected Model Selection by Variable

 Based on data characteristics analysis:

 | Variable             | Expected Model  | Rationale                                |
 |----------------------|-----------------|------------------------------------------|
 | ebitda               | ARIMA(1,1,1)    | Financial, difference-stationary         |
 | revenue              | Prophet         | Regime changes, construction seasonality |
 | variable_cost        | ARIMA or Linear | Stationary cost metric                   |
 | sales_volume         | SARIMA          | Strong 12-month seasonality              |
 | electricity_cost     | ETS(M,A,M)      | Multiplicative energy seasonality        |
 | thermal_cost         | ARIMAX          | Fuel price correlation                   |
 | avg_selling_price    | ETS             | Damped pricing trends                    |
 | capacity_utilization | Prophet or ETS  | Operational with changepoints            |
 | ttf_gas_price        | ARIMA           | Commodity, stationary in differences     |
 | petcoke_price        | XGBoost         | High volatility, multiple drivers        |
 | co2_eua_price        | Prophet         | Energy market regime changes             |
 | euribor_3m           | ARIMA           | Interest rate, mean-reverting            |
 | gdp_growth           | Chronos-2       | Limited data, zero-shot                  |
 | inflation            | Prophet         | Policy regime changes                    |
 | construction_output  | SARIMA          | Strong seasonal construction             |

 ---
 Implementation Timeline

 Week 1:
 ├── Day 1: Story 7.1 (ARIMA/ETS wrappers)
 ├── Day 2: Story 7.2 (Data analyzer)
 ├── Days 3-5: Story 7.3 (Model selection with all 9 models)

 Week 2:
 ├── Day 1: Story 7.4 (PostgreSQL cache)
 ├── Day 2: Story 7.5 (CLI tool)
 ├── Days 3-4: Story 7.6 (MCP integration)
 ├── Day 5: Validation & bug fixes

 Total Effort: 10 development days

 ---
 Dependencies

 New Dependency:
 # pyproject.toml
 [project]
 dependencies = [
     # ... existing ...
     "pmdarima>=2.0,<3.0",  # Auto-ARIMA
 ]

 Already Available:
 - statsmodels (ETS, ADF, KPSS) - via Prophet
 - scipy (statistical tests)
 - sklearn (TimeSeriesSplit)
 - All existing model libraries (XGBoost, LightGBM, CatBoost, pytorch-forecasting, chronos-forecasting)

 ---
 Success Criteria

 | Metric                        | Current | Target |
 |-------------------------------|---------|--------|
 | EBITDA MAPE                   | 84.77%  | <15%   |
 | Variables meeting MAPE target | 6/20    | 15/20  |
 | Average FQS                   | 65.9    | >75    |
 | MCP query time (cache hit)    | N/A     | <5s    |
 | Model selection coverage      | 0%      | 100%   |

 ---
 Risk Mitigation

 | Risk                       | Probability | Impact | Mitigation                                                      |
 |----------------------------|-------------|--------|-----------------------------------------------------------------|
 | ARIMA/ETS fitting failures | Medium      | Low    | Graceful fallback to Prophet                                    |
 | CV runtime too long        | Medium      | Medium | Pre-filter candidates, parallel execution                       |
 | Cache staleness            | Low         | Medium | 7-day TTL, manual invalidation                                  |
 | TFT training failures      | Low         | Low    | On-demand training with early stopping; skip if GPU unavailable |
 | TFT training too slow      | Medium      | Medium | Reduced epochs (50), early stopping, checkpoint caching         |
 | Chronos-2 cold-start       | Low         | Low    | Use for <12 data points only                                    |

 ---
 Validation Plan

 Per-Story Validation

 # After each story
 uv run python scripts/validate_forecasting_unified.py --full

 # Compare MAPE before/after for key variables

 Final Validation

 # 1. Run model selection for all variables (via slash command)
 > /model-selection --all
 # Or invoke subagent: Use model-selection-executor to run batch selection

 # 2. Verify cache populated
 docker exec raglite-postgresql psql -U raglite -d raglite \
   -c "SELECT variable_name, best_model, best_mape FROM model_selection ORDER BY best_mape"

 # 3. Test MCP forecast
 # Via Claude Desktop: "Forecast EBITDA for 2026"
 # Verify response includes model_source: "cached"

 # 4. Full validation run
 uv run python scripts/validate_forecasting_unified.py --full --export-json

 ---
 Files Summary

 | File                                       | Action | Story    | Lines           |
 |--------------------------------------------|--------|----------|-----------------|
 | raglite/forecasting/hybrid.py              | Modify | 7.1, 7.6 | +500            |
 | raglite/forecasting/data_analyzer.py       | Create | 7.2      | +350            |
 | raglite/forecasting/model_selection.py     | Create | 7.3      | +500            |
 | raglite/forecasting/model_selection_job.py | Create | 7.5      | +250            |
 | models/tft/{variable_name}/                | Create | 7.3/7.5  | TFT checkpoints |
 | raglite/external_data/orm_models.py        | Modify | 7.4      | +40             |
 | raglite/external_data/storage.py           | Modify | 7.4      | +100            |
 | raglite/shared/models.py                   | Modify | 7.6      | +10             |
 | raglite/main.py                            | Modify | 7.6      | +20             |
 | migrations/006_add_model_selection.sql     | Create | 7.4      | +20             |
 | .claude/commands/model-selection.md        | Create | 7.5      | ~50             |
 | .claude/agents/model-selection-executor.md | Create | 7.5      | ~80             |
 | pyproject.toml                             | Modify | 7.1      | +1              |
 | tests/unit/test_arima_ets_models.py        | Create | 7.1      | +150            |
 | tests/unit/test_data_analyzer.py           | Create | 7.2      | +200            |
 | tests/integration/test_model_selection.py  | Create | 7.3      | +250            |
 | tests/e2e/test_mcp_model_selection.py      | Create | 7.6      | +150            |

 Total New Code: ~2,670 lines (Python) + ~130 lines (Slash Command/Subagent)

 ---
 Quick Start After Implementation

 # 1. Run model selection for all variables (~90-120 min)
 # Via Claude Code slash command:
 > /model-selection --all

 # Or invoke subagent directly:
 > Use the model-selection-executor subagent to run batch selection

 # 2. Check selection results
 cat reports/model-selection-*.md

 # Or query PostgreSQL directly:
 docker exec raglite-postgresql psql -U raglite -d raglite \
   -c "SELECT variable_name, best_model, best_mape FROM model_selection ORDER BY best_mape"

 # 3. Verify via MCP (Claude Desktop)
 # "Forecast EBITDA for Q1 2026"
 # Response should show model_source: "cached" and selected model

 # 4. For single variable selection:
 > /model-selection ebitda

 # 5. Force refresh cache:
 > /model-selection --all --force
