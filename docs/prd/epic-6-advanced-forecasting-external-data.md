# Epic 6: Advanced Forecasting with External Data

**Epic Goal:** Enhance forecasting capabilities with multi-variate models using external Portuguese/EU data sources for cement industry demand prediction, enabling correlation analysis between macro-economic drivers and business KPIs.

**Priority:** P0 (blocks Epic 5 cloud deployment)

**Timeline:** 3-4 weeks (14-20 days)

**Dependencies:** Epic 4 (DONE)

**Status:** 🟡 READY TO START

---

## Strategic Context

### Problem Statement

Current forecasting (Epic 4) uses:
- **Algorithm:** Prophet-only (no ensemble)
- **Data:** Historical time-series from internal documents (univariate)
- **Accuracy:** ±15% (NFR10 met, but can improve)
- **Limitation:** No external macro-economic indicators

### User Requirements

Ricardo provided comprehensive research:
- **Document:** `docs/High-Level Overview.pdf` (27 pages)
- **Coverage:** Tier 1/2 data sources for cement industry demand prediction
- **Data Sources:** 20+ Portuguese/EU datasets with API access methods
- **Use Case:** Cement industry (can generalize to other sectors)

### Business Impact

1. **External Data Sources:** Portuguese/EU datasets (INE, BPstat, OMIE, IPMA)
2. **Multi-Variate Models:** Correlation analysis between drivers (building permits, energy prices, weather) and business outcomes
3. **Model Diversity:** Ensemble beyond Prophet (scikit-learn, XGBoost)
4. **Automated Refresh:** Scheduled data updates
5. **Accuracy Improvement:** 20-30% improvement (±15% → ±10%)

---

## Technology Stack Changes

| Technology | Version | Purpose | Approval Status |
|------------|---------|---------|-----------------|
| **PostgreSQL** | 16.10 LTS | External data storage | ✅ APPROVED (promoted from conditional) |
| **APScheduler** | 3.10+ | Periodic data refresh | ✅ APPROVED (new) |
| **scikit-learn** | 1.5+ | ML ensemble (Linear Regression) | ✅ APPROVED (new) |
| **XGBoost** | 2.1+ | Gradient boosting ensemble | ✅ APPROVED (new) |

**Already in Stack:**
- httpx (HTTP client for API calls)
- pandas (data manipulation)
- Prophet (existing forecasting baseline)
- Pydantic (data validation)

---

## Data Sources Reference

### Tier 1 Sources (11 datasets - MANDATORY)

| Source | Data | API/Access | Frequency |
|--------|------|------------|-----------|
| **INE API** | Building Permits | JSON API | Monthly |
| **INE API** | Construction Output Index | JSON API | Monthly |
| **INE API** | Construction Cost Index | JSON API | Monthly |
| **ATIC** | Cement Consumption | Manual CSV (if no API) | Monthly |
| **Banco de Portugal BPstat** | Mortgage Loans | BPstat API | Monthly |
| **OMIE** | Electricity Prices | OMIE API | Daily |
| **EU Oil Bulletin** | Diesel Prices | API/CSV | Weekly |
| **IPMA** | Weather Data (temp, rainfall) | IPMA API | Daily |
| **Base.gov.pt** | Public Works Contracts | CSV/Web Scraping | Monthly |
| **Manual** | Coal/Petcoke Prices | Web scraping | Monthly |
| **Manual** | CO₂ EUA Prices | Web scraping | Daily |

### Tier 2 Sources (9 datasets - CONDITIONAL)

**Decision Gate:** ONLY if Story 6.7 accuracy validation <±12% with Tier 1 only

| Source | Data | API/Access |
|--------|------|------------|
| **INE API** | House Price Index | JSON API |
| **Banco de Portugal** | Bank Appraisal Values | BPstat API |
| **INE API** | Construction Confidence Indicator | JSON API |
| **Eurostat COMEXT** | Trade Data | API |
| Others per research PDF | Various | Various |

---

## Epic Success Criteria

1. ✅ Tier 1 data sources integrated (11 datasets: INE, BPstat, OMIE, IPMA, etc.)
2. ✅ Multi-variate Prophet forecasting operational with external regressors
3. ✅ Model ensemble framework delivering 20-30% accuracy improvement over Epic 4 baseline
4. ✅ Automated data refresh scheduler operational (daily/weekly/monthly)
5. ✅ PostgreSQL external data storage schema implemented
6. ✅ Forecast accuracy validation: ±10% or better (vs Epic 4 ±15%)
7. ✅ MCP tools for external data queries and multi-model forecasting

---

## Story 6.1: Tier 1 External Data Source Integration

**Priority:** P0
**Estimated Effort:** 2-3 days

**User Story:**
As a system, I want to integrate Tier 1 Portuguese data sources (INE, BPstat, OMIE, IPMA, etc.), so that forecasting models can use macro-economic drivers for improved accuracy.

**Acceptance Criteria:**

1. ✅ **API Clients Implemented** for Tier 1 sources:
   - INE API (Building Permits, Construction Output Index, Construction Cost Index)
   - ATIC (Cement Consumption - CSV if no API available)
   - Banco de Portugal BPstat (Mortgage Loans)
   - OMIE (Electricity Prices)
   - EU Oil Bulletin (Diesel Prices)
   - IPMA (Weather Data: temperature, rainfall)
   - Base.gov.pt (Public Works Contracts - CSV or web scraping)
   - Manual sources: Coal/Petcoke, CO₂ EUA (web scraping or CSV)

2. ✅ **Data Validation:** Pydantic models for each source with proper type hints
3. ✅ **Error Handling:** Retry logic for API failures (3 attempts with exponential backoff)
4. ✅ **Fallback Strategy:** Use cached data if API unavailable (stale data tolerance: 30 days)
5. ✅ **Historical Data Load:** Initial load covers 2020-2025 period (5 years)
6. ✅ **Unit Tests:** 80%+ coverage for each API client
7. ✅ **Integration Tests:** Successful data retrieval from each source (use VCR.py for API mocking)

**Technical Notes:**
- Use `httpx` async client for HTTP requests
- Store API credentials in environment variables (`.env` file)
- Rate limiting: Respect API quotas (e.g., INE: 100 req/min)
- Data format: Store as pandas DataFrames initially, convert to Pydantic models

**Dependencies:**
- None (can start immediately)

**NFRs:**
- API response time: <5s p95
- Data freshness: <30 days (alert if stale)

---

## Story 6.2: PostgreSQL External Data Schema & Storage

**Priority:** P0
**Estimated Effort:** 1-2 days

**User Story:**
As a system, I want to store external data sources in PostgreSQL, so that forecasting models can query historical macro-economic data efficiently.

**Acceptance Criteria:**

1. ✅ **PostgreSQL Schema Created:**
   ```sql
   -- Metadata table
   CREATE TABLE external_data_sources (
       id SERIAL PRIMARY KEY,
       source_name VARCHAR(100) NOT NULL UNIQUE,  -- e.g., "INE_BuildingPermits"
       api_endpoint TEXT,
       data_type VARCHAR(50),  -- e.g., "time_series", "index"
       refresh_frequency VARCHAR(20),  -- e.g., "daily", "weekly", "monthly"
       last_refresh_at TIMESTAMP,
       created_at TIMESTAMP DEFAULT NOW(),
       metadata JSONB  -- Additional source-specific metadata
   );

   -- Time-series data points table
   CREATE TABLE external_data_points (
       id SERIAL PRIMARY KEY,
       source_id INTEGER REFERENCES external_data_sources(id),
       date DATE NOT NULL,
       metric_name VARCHAR(100) NOT NULL,  -- e.g., "building_permits_count"
       value NUMERIC NOT NULL,
       unit VARCHAR(50),  -- e.g., "count", "EUR", "MWh"
       metadata JSONB,  -- Additional data-specific metadata
       created_at TIMESTAMP DEFAULT NOW(),
       UNIQUE(source_id, date, metric_name)
   );

   -- Indexes for fast queries
   CREATE INDEX idx_data_points_source_date ON external_data_points(source_id, date);
   CREATE INDEX idx_data_points_metric ON external_data_points(metric_name);
   CREATE INDEX idx_sources_name ON external_data_sources(source_name);
   ```

2. ✅ **Migration Script:** Alembic migration for schema creation
3. ✅ **SQLAlchemy ORM Models:** `ExternalDataSource`, `ExternalDataPoint` classes
4. ✅ **Data Retention Policy:** Keep 5 years historical data, archive older (soft delete)
5. ✅ **Query Performance:** <500ms for 5-year date range queries (validated with EXPLAIN ANALYZE)
6. ✅ **Unit Tests:** CRUD operations for both tables (80%+ coverage)
7. ✅ **Integration Tests:** Schema creation, data insertion, complex queries

**Technical Notes:**
- Use PostgreSQL 16.10 LTS (already approved)
- JSONB for flexible metadata storage (source-specific fields)
- Composite unique constraint prevents duplicate data points
- Soft delete for retention policy (add `deleted_at` column)

**Dependencies:**
- Story 6.1 (API clients ready to populate data)

**NFRs:**
- Query performance: <500ms p95 for 5-year range
- Data integrity: Foreign key constraints enforced
- Scalability: Handle 10K+ data points per source

---

## Story 6.3: Prophet Multi-Variate Forecasting (External Regressors)

**Priority:** P0
**Estimated Effort:** 2-3 days

**User Story:**
As a system, I want to use external regressors in Prophet forecasting, so that predictions account for macro-economic drivers beyond historical trends.

**Acceptance Criteria:**

1. ✅ **Enhance `raglite/forecasting/hybrid.py`:**
   - Add `external_regressors` parameter to `generate_forecast()` function
   - Support Prophet `add_regressor()` for 5-7 top correlated drivers
   - Example regressors: building_permits, electricity_price, mortgage_loans, weather_temp, diesel_price

2. ✅ **Regressor Selection:**
   - Automated correlation analysis (Pearson correlation coefficient)
   - Select top 5-7 regressors with correlation >0.5
   - Fallback to manual selection if correlation analysis fails

3. ✅ **Handle Missing Data:**
   - Interpolation for missing regressor values (linear or spline)
   - Forward-fill for edge cases (up to 3 data points)
   - Raise error if >10% of regressor data missing

4. ✅ **Forecast Accuracy Validation:**
   - Compare multi-variate vs univariate (Epic 4 baseline)
   - Expected improvement: 20-30% reduction in RMSE
   - Document accuracy metrics in forecast result

5. ✅ **Backward Compatibility:**
   - `external_regressors=None` defaults to Epic 4 univariate behavior
   - No breaking changes to existing `generate_forecast()` calls

6. ✅ **Unit Tests:**
   - Multi-variate forecasting with valid regressors (85%+ coverage)
   - Missing data handling (interpolation scenarios)
   - Correlation analysis edge cases

7. ✅ **Integration Tests:**
   - End-to-end forecast with real external data from PostgreSQL
   - Accuracy comparison: multi-variate vs univariate

**Technical Notes:**
- Prophet `add_regressor()` requires regressor values for both historical and future periods
- Future regressor values: Use latest available data (assume constant for forecast horizon)
- Correlation analysis: Use `scipy.stats.pearsonr` or `pandas.DataFrame.corr()`

**Dependencies:**
- Story 6.1 (external data sources)
- Story 6.2 (PostgreSQL schema)

**NFRs:**
- Forecast generation time: <10s p95 (with 5-7 regressors)
- Accuracy improvement: ≥20% reduction in RMSE vs Epic 4 baseline

---

## Story 6.4: Model Ensemble Framework (scikit-learn, XGBoost)

**Priority:** P1
**Estimated Effort:** 3-4 days

**User Story:**
As a system, I want to use diverse predictive models beyond Prophet, so that forecasting leverages multiple algorithms for improved accuracy and robustness.

**Acceptance Criteria:**

1. ✅ **Implement Ensemble Framework:**
   - **Prophet:** Existing baseline (multi-variate from Story 6.3)
   - **Linear Regression:** scikit-learn `LinearRegression` with external regressors
   - **XGBoost Regressor:** `xgboost.XGBRegressor` for gradient boosting
   - **Ensemble Voting:** Weighted average of 3 models (configurable weights)

2. ✅ **Model Configuration:**
   - Environment variable: `FORECASTING_MODELS=prophet,linear,xgboost` (comma-separated)
   - Enable/disable models individually
   - Default weights: Prophet 40%, Linear 30%, XGBoost 30%

3. ✅ **Hyperparameter Tuning (XGBoost):**
   - Use grid search or Optuna for hyperparameter optimization
   - Parameters: `n_estimators`, `max_depth`, `learning_rate`, `subsample`
   - Cross-validation: 5-fold time-series split

4. ✅ **Model Performance Comparison:**
   - Calculate RMSE, MAE, MAPE for each model
   - Log performance metrics to structured logging
   - Select best model if ensemble underperforms individual

5. ✅ **Fallback Strategy:**
   - If ensemble fails, fallback to Prophet-only (Epic 4 behavior)
   - Log warning and continue with degraded performance

6. ✅ **Unit Tests:**
   - Each model (Prophet, Linear, XGBoost) tested independently (80%+ coverage)
   - Ensemble voting logic validated
   - Model selection via configuration

7. ✅ **Integration Tests:**
   - End-to-end ensemble forecasting with real data
   - Hyperparameter tuning execution (fast test mode)
   - Performance comparison across models

**Technical Notes:**
- scikit-learn: Already widely used, stable API
- XGBoost: Install via pip (`xgboost>=2.1`)
- Ensemble weights: Can be optimized via meta-learner (future enhancement)
- Time-series split: Use `sklearn.model_selection.TimeSeriesSplit`

**Dependencies:**
- Story 6.3 (multi-variate Prophet as baseline)

**NFRs:**
- Ensemble forecast time: <15s p95 (3 models in parallel)
- Accuracy improvement: 10-15% reduction in RMSE vs Story 6.3 multi-variate Prophet

---

## Story 6.5: Automated Data Refresh Scheduler (APScheduler)

**Priority:** P0
**Estimated Effort:** 1-2 days

**User Story:**
As a system, I want to automatically refresh external data sources on a schedule, so that forecasting models use the most current macro-economic data without manual intervention.

**Acceptance Criteria:**

1. ✅ **APScheduler Integration:**
   - Install `APScheduler>=3.10`
   - Configure `BackgroundScheduler` for async execution
   - Store job state in PostgreSQL (persistent across restarts)

2. ✅ **Refresh Schedule Configuration:**
   - **Daily:** Weather (IPMA), Electricity Prices (OMIE), CO₂ EUA
   - **Weekly:** Building Permits (INE), Mortgage Loans (BPstat), Diesel Prices
   - **Monthly:** Construction Output, Cost Index (INE), Cement Consumption (ATIC)
   - Configuration via environment variables: `REFRESH_SCHEDULE_DAILY=06:00`, `REFRESH_SCHEDULE_WEEKLY=Sunday 06:00`, etc.

3. ✅ **Error Notifications:**
   - Log failed refresh attempts to structured logging (ERROR level)
   - Optional: Email/Slack notifications (future enhancement, not required for MVP)
   - Retry failed jobs: 3 attempts with exponential backoff

4. ✅ **Manual Trigger Endpoint:**
   - MCP tool: `refresh_external_data(source_name=None)` (None = all sources)
   - Force refresh regardless of schedule
   - Return refresh status for each source

5. ✅ **Data Staleness Detection:**
   - Alert if external data >30 days old (WARNING level log)
   - Mark source as stale in `external_data_sources.last_refresh_at`
   - Forecasting continues with stale data (degraded mode)

6. ✅ **Unit Tests:**
   - Scheduler configuration and job execution (80%+ coverage)
   - Error handling and retry logic
   - Manual trigger via MCP tool

7. ✅ **Integration Tests:**
   - Scheduled refresh executes successfully
   - Staleness detection triggers warnings
   - Manual refresh via MCP tool

**Technical Notes:**
- APScheduler: Lightweight, no external dependencies (vs Celery which needs Redis/RabbitMQ)
- Job persistence: Store jobs in PostgreSQL using `APScheduler.jobstores.sqlalchemy`
- Timezone: Use UTC for all scheduled jobs
- Graceful shutdown: Ensure scheduler shuts down cleanly on app exit

**Dependencies:**
- Story 6.1 (API clients)
- Story 6.2 (PostgreSQL schema)

**NFRs:**
- Refresh execution time: <5 minutes p95 (all sources)
- Reliability: 99%+ successful refresh rate (with retries)

---

## Story 6.6: External Data Query Tool (MCP)

**Priority:** P1
**Estimated Effort:** 1 day

**User Story:**
As a user, I want to query external data sources via MCP, so that I can explore macro-economic drivers and validate data quality conversationally.

**Acceptance Criteria:**

1. ✅ **MCP Tool Defined:**
   ```python
   @mcp.tool()
   async def query_external_data(
       source: str,  # e.g., "INE_BuildingPermits", "OMIE_Electricity"
       date_range: str,  # e.g., "2024-01-01:2024-12-31" or "last_30_days"
       metric: str = None  # Optional: specific metric name
   ) -> str:
       """Query external data sources and return time-series data."""
   ```

2. ✅ **Query Support:**
   - Single source or "all" for all sources
   - Date range: ISO format (`YYYY-MM-DD:YYYY-MM-DD`) or shortcuts (`last_30_days`, `last_year`)
   - Metric filtering: Return specific metric or all metrics for source

3. ✅ **Response Format:**
   - Time-series data as JSON or markdown table
   - Include source attribution, data frequency, last refresh timestamp
   - Example: "Building Permits (INE): 1,234 permits in Jan 2024 (last refreshed: 2024-02-01)"

4. ✅ **Data Visualization Hints:**
   - Suggest chart types for Claude Desktop (e.g., "This data would look great as a line chart")
   - Return data in format suitable for plotting (date, value pairs)

5. ✅ **Test Queries:**
   - "Show me building permits for Q1 2025"
   - "What's the latest electricity price from OMIE?"
   - "Compare mortgage loans and building permits for last year"

6. ✅ **Unit Tests:** 80%+ coverage for MCP tool logic

**Technical Notes:**
- Use Pydantic models for query parameters and response
- Date range parsing: Use `dateutil.parser` or pandas `pd.to_datetime()`
- Visualization hints: Metadata field in MCP response

**Dependencies:**
- Story 6.2 (PostgreSQL schema with data)

**NFRs:**
- Query response time: <2s p95 for 1-year range

---

## Story 6.7: Multi-Variate Forecast Accuracy Validation

**Priority:** P0
**Estimated Effort:** 2 days

**User Story:**
As a developer, I want to validate multi-variate forecasting accuracy, so that Epic 6 enhancements demonstrably improve predictions vs Epic 4 baseline.

**Acceptance Criteria:**

1. ✅ **Ground Truth Test Set:**
   - Create 20+ cement demand forecast scenarios (monthly data, 2020-2024)
   - Include known outcomes (actual cement consumption from ATIC)
   - Cover seasonal patterns, economic shocks (COVID, energy crisis)

2. ✅ **Baseline Comparison:**
   - Epic 4 Prophet-only (univariate): Current ±15% accuracy
   - Story 6.3 Prophet multi-variate: Expected ±12% accuracy
   - Story 6.4 Ensemble: Expected ±10% accuracy (target)

3. ✅ **Accuracy Metrics:**
   - **RMSE** (Root Mean Squared Error): Primary metric
   - **MAE** (Mean Absolute Error): Secondary metric
   - **MAPE** (Mean Absolute Percentage Error): Percentage accuracy
   - **Target:** ±10% or better (20-30% improvement vs Epic 4 ±15%)

4. ✅ **Automated Performance Report:**
   - Script: `scripts/validate-epic6-accuracy.py`
   - Output: Markdown report with comparison table
   - Include: Model name, RMSE, MAE, MAPE, improvement %

5. ✅ **Success Threshold:**
   - If accuracy ≥±10%: Epic 6 APPROVED, proceed to Epic 5
   - If accuracy <±12%: TRIGGER Story 6.8 (Tier 2 sources)
   - If accuracy <±14% after Tier 2: Re-evaluate with PM/Architect

6. ✅ **Regression Tests:**
   - Prevent accuracy degradation in future changes
   - CI/CD gate: Fail if accuracy drops below ±12%

**Technical Notes:**
- Use `sklearn.metrics` for RMSE, MAE
- MAPE: Custom calculation (avoid division by zero)
- Ground truth data: CSV file in `tests/ground_truth/cement_demand_2020_2024.csv`

**Dependencies:**
- Story 6.3 (multi-variate Prophet)
- Story 6.4 (ensemble framework)

**NFRs:**
- Validation execution time: <5 minutes for 20 scenarios
- Accuracy improvement: ≥20% reduction in MAPE vs Epic 4

---

## Story 6.8: Tier 2 Data Sources Integration (Conditional)

**Priority:** P2 (CONDITIONAL)
**Estimated Effort:** 2-3 days

**User Story:**
As a system, I want to integrate Tier 2 data sources (House Price Index, Bank Appraisals, Confidence Indicators), so that forecasting can leverage additional economic signals if Tier 1 sources are insufficient.

**Acceptance Criteria:**

1. ⚠️ **DECISION GATE:** ONLY execute if Story 6.7 accuracy validation <±12% with Tier 1 only

2. ✅ **API Clients for Tier 2 Sources:**
   - INE: House Price Index, Construction Confidence Indicator
   - Banco de Portugal: Bank Appraisal Values
   - Eurostat COMEXT: Trade Data
   - Other sources per research PDF

3. ✅ **PostgreSQL Schema Extension:**
   - Add Tier 2 sources to `external_data_sources` table
   - Populate `external_data_points` with Tier 2 historical data (2020-2025)

4. ✅ **Update Prophet Regressors:**
   - Add top 3-5 Tier 2 regressors to Story 6.3 multi-variate model
   - Re-run correlation analysis with Tier 1 + Tier 2 combined

5. ✅ **Re-Validate Accuracy:**
   - Re-run Story 6.7 validation script with Tier 2 data
   - Target: ±10% accuracy with Tier 1 + Tier 2
   - Document improvement from Tier 2 addition

**Technical Notes:**
- Only execute if Tier 1 insufficient (saves 2-3 days if not needed)
- Tier 2 sources may have lower data quality/frequency than Tier 1

**Dependencies:**
- Story 6.7 decision gate

**NFRs:**
- Same as Story 6.1 (API clients)

---

## Story 6.12: CatBoost Integration + Adaptive Weights

**Priority:** P0
**Estimated Effort:** 2-3 days
**Sprint Change Proposal:** SCP-2025-12-10-001

**User Story:**
As a system, I want to integrate CatBoost into the forecasting ensemble with adaptive backtest-driven weights, so that model selection is optimized automatically based on actual performance.

**Acceptance Criteria:**

1. ✅ **CatBoost Integration:**
   - Add `catboost>=1.2` to dependencies
   - Implement `CatBoostRegressor` in `raglite/forecasting/hybrid.py`
   - Support categorical variables natively (fuel types, regions, etc.)
   - Follow existing XGBoost/LightGBM patterns for consistency

2. ✅ **Adaptive Weights System:**
   - Create PostgreSQL `model_weights` table:
     ```sql
     CREATE TABLE model_weights (
         id SERIAL PRIMARY KEY,
         metric_name VARCHAR(100) NOT NULL,
         model_name VARCHAR(50) NOT NULL,
         weight NUMERIC(5,4) NOT NULL,
         backtest_rmse NUMERIC,
         backtest_mape NUMERIC,
         has_regressors BOOLEAN DEFAULT TRUE,
         data_points INTEGER,
         calculated_at TIMESTAMP DEFAULT NOW(),
         UNIQUE(metric_name, model_name)
     );
     ```

3. ✅ **Weekly Backtest Job:**
   - Integrate with APScheduler (Story 6.5)
   - Calculate rolling backtest: train on months 1-9, test on 10-12
   - Weight formula: `weight = 1 / (RMSE + ε)`, normalized to sum to 1.0
   - Store results in `model_weights` table

4. ✅ **Adaptive Weight Behavior:**
   - No regressors available → Chronos-2 weight ×2, regressor-dependent models ×0.3
   - Model fails during forecast → Removed from ensemble, weights re-normalized
   - New metric (no history) → Default equal weights until backtest data exists
   - Weight caps: Min 5%, Max 50% per model (maintain diversity)

5. ✅ **MCP Tool (Admin):**
   - `recalculate_model_weights(metric=None)` - Force weight recalculation
   - If metric=None, recalculate all metrics
   - Returns new weights and previous weights for comparison

6. ✅ **Unit Tests:** 80%+ coverage for CatBoost and weight calculation
7. ✅ **Integration Tests:** Ensemble with adaptive weights, backtest job execution

**Technical Notes:**
- CatBoost API mirrors XGBoost/LightGBM - straightforward integration
- Backtest job runs Sunday 3am (after data refresh)
- Weights cached in PostgreSQL, loaded at forecast time (no runtime cost)

**Dependencies:**
- Story 6.4 (existing ensemble framework)
- Story 6.5 (APScheduler integration)

**NFRs:**
- CatBoost inference: <1s
- Backtest job: <10 minutes for all metrics
- Weight lookup: <100ms from PostgreSQL

**Validation Requirements (MANDATORY):**
```bash
# BEFORE implementation - capture baseline
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data > validation-pre-6.12.txt

# AFTER implementation - verify no regression
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data > validation-post-6.12.txt

# Compare: Avg MAPE must be ≤ 2.05% (no regression from baseline)
# Verify: CatBoost appears in ensemble_weights with weight > 0
# Verify: model_weights table populated in PostgreSQL
```

---

## Story 6.13: Chronos-2 Integration (Cold-Start & Ensemble Member)

**Priority:** P0
**Estimated Effort:** 2-3 days
**Sprint Change Proposal:** SCP-2025-12-10-001

**User Story:**
As a system, I want to integrate Chronos-2 as both a cold-start handler and ensemble member, so that forecasting works even with limited data or missing external regressors.

**Acceptance Criteria:**

1. ✅ **Chronos-2 Integration:**
   - Add `chronos-forecasting>=2.0` to dependencies
   - Use `amazon/chronos-bolt-small` model (250× faster than original)
   - Support CPU inference (GPU optional for better performance)
   - Implement lazy loading pattern (like `_get_prophet_class()`)

2. ✅ **Cold-Start Path (< 6 data points):**
   - Route to Chronos-2 only when `len(data_points) < MIN_DATA_POINTS`
   - Zero-shot forecasting (no training required)
   - Return prediction with confidence intervals
   - Log: "Cold-start path: using Chronos-2 zero-shot"

3. ✅ **Ensemble Member Path (≥ 6 data points):**
   - Add Chronos-2 as weighted ensemble member
   - Chronos-2 supports covariates (use external regressors when available)
   - Weight determined by adaptive backtest system (Story 6.12)

4. ✅ **Fallback Behavior (No Regressors):**
   - When external regressors unavailable, auto-boost Chronos-2 weight
   - Chronos-2 works well without regressors (pure time-series model)
   - Log: "No regressors available: boosting Chronos-2 weight"

5. ✅ **Model Caching:**
   - Load Chronos-2 model once on first use
   - Reuse across all forecast calls in session
   - Avoid 10-30s cold-start penalty on repeated calls

6. ✅ **Inference Performance:**
   - Chronos-2 component: <2 seconds per forecast
   - Benchmark on startup, log if exceeds threshold

7. ✅ **Unit Tests:** 80%+ coverage
8. ✅ **Integration Tests:**
   - Cold-start scenario (3 data points → Chronos-2 only)
   - Fallback scenario (no regressors → boosted weight)
   - Ensemble scenario (full ensemble with Chronos-2 member)

**Technical Notes:**
- Chronos-2 (October 2025) supports covariates - major upgrade from original
- Use `BaseChronosPipeline.from_pretrained("amazon/chronos-bolt-small")`
- CPU device_map for local development, GPU optional for production
- 120M parameters, context up to 8,192 tokens

**Dependencies:**
- Story 6.12 (adaptive weights system)

**NFRs:**
- Cold-start forecast: <3s total
- Ensemble with Chronos-2: <5s total (meets existing NFR)
- Model load: <30s first time, <1ms cached

**Validation Requirements (MANDATORY):**
```bash
# BEFORE implementation - capture baseline
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data > validation-pre-6.13.txt

# AFTER implementation - verify no regression
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data > validation-post-6.13.txt

# Cold-start specific test (NEW)
uv run python -c "
from raglite.forecasting.hybrid import generate_forecast
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint
from datetime import datetime
import asyncio

# Create minimal data (3 points - should trigger Chronos-2)
points = [TimeSeriesPoint(date=datetime(2024, i, 1), value=100+i*5, label=f'M{i}') for i in range(1, 4)]
data = TimeSeriesData(metric_name='test_cold_start', points=points, interval='monthly')
result = asyncio.run(generate_forecast('test_cold_start', data, periods_ahead=3))
print(f'Model used: {result.model_type}')
assert 'chronos' in result.model_type.lower(), 'Cold-start should use Chronos-2'
print('✅ Cold-start validation PASSED')
"

# Compare: Avg MAPE must be ≤ 2.05% (no regression from baseline)
# Verify: Cold-start works with <6 data points
# Verify: Chronos-2 appears in ensemble for ≥6 data points
```

---

## Story 6.14: TFT Integration with Training Workflow

**Priority:** P1
**Estimated Effort:** 4-5 days
**Sprint Change Proposal:** SCP-2025-12-10-001

**User Story:**
As a system, I want to integrate Temporal Fusion Transformer (TFT) with offline training workflow, so that complex multivariate patterns with attention-based explainability are captured for financial KPIs.

**Acceptance Criteria:**

1. ✅ **TFT Implementation:**
   - Add `pytorch-forecasting>=1.0` to dependencies
   - Implement TFT model using `TemporalFusionTransformer.from_dataset()`
   - Support static, known-future, and observed covariates
   - Follow pytorch-forecasting best practices

2. ✅ **Model Registry Table:**
   ```sql
   CREATE TABLE model_registry (
       id SERIAL PRIMARY KEY,
       model_type VARCHAR(50) NOT NULL,
       model_version VARCHAR(20) NOT NULL,
       checkpoint_path TEXT NOT NULL,
       metrics_json JSONB,
       trained_at TIMESTAMP DEFAULT NOW(),
       is_active BOOLEAN DEFAULT FALSE,
       UNIQUE(model_type, model_version)
   );
   ```

3. ✅ **Offline Training Workflow:**
   - **Trigger 1:** Weekly scheduled (Sunday 2am, before weight calculation)
   - **Trigger 2:** After data refresh (Story 6.5 completion hook)
   - **Trigger 3:** Manual MCP tool: `retrain_forecasting_models(models="tft")`
   - Training time: <30 minutes for full dataset
   - Save best checkpoint by validation loss

4. ✅ **Training Process:**
   - Create `TimeSeriesDataSet` with encoder_length, prediction_length, covariates
   - Train with PyTorch Lightning `Trainer` (max_epochs=50, early stopping)
   - Validate on holdout set (last 12 months)
   - Log training metrics to structured logging
   - Store checkpoint path in `model_registry`

5. ✅ **Graceful Degradation:**
   - If TFT not trained → Skip in ensemble (weight = 0)
   - If TFT training fails → Log error, continue without TFT
   - If checkpoint corrupted → Fall back to previous version
   - Ensemble always works regardless of TFT state

6. ✅ **MCP Tool:**
   - `retrain_forecasting_models(models="tft,catboost", force=False)`
   - `models`: Comma-separated list or "all"
   - `force`: Retrain even if recent checkpoint exists
   - Returns: Training status, metrics, checkpoint path

7. ✅ **Inference Performance:**
   - TFT inference: <1 second (pre-trained model forward pass)
   - Load checkpoint on first use, cache for session

8. ✅ **Unit Tests:** 80%+ coverage
9. ✅ **Integration Tests:**
   - Training workflow end-to-end
   - Model registry operations
   - Ensemble with TFT (when trained)
   - Graceful degradation (TFT not available)

**Technical Notes:**
- TFT requires offline training (unlike Chronos-2 zero-shot)
- Training on GPU recommended (~5-10 minutes), CPU fallback (~30-60 minutes)
- Model checkpoint ~50-100MB per trained model
- TFT shines with 30+ external features (RAGLite has 11+)

**Dependencies:**
- Story 6.12 (adaptive weights system)
- Story 6.13 (Chronos-2 for comparison)

**NFRs:**
- Training time: <30 minutes on GPU, <60 minutes on CPU
- Inference time: <1 second
- Checkpoint size: <100MB per model

**Validation Requirements (MANDATORY):**
```bash
# BEFORE implementation - capture baseline
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data > validation-pre-6.14.txt

# AFTER implementation - verify no regression
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data > validation-post-6.14.txt

# TFT Training workflow test (NEW)
uv run python -c "
from raglite.main import retrain_forecasting_models
import asyncio

# Test training workflow
result = asyncio.run(retrain_forecasting_models(models='tft', force=True))
print(f'Status: {result.status}')
print(f'Checkpoint: {result.checkpoint_path}')
assert result.status == 'success', 'TFT training failed'
print('✅ TFT training validation PASSED')
"

# TFT Graceful degradation test
uv run python -c "
from raglite.forecasting.hybrid import generate_ensemble_forecast
import asyncio

# Should work even if TFT not trained (graceful degradation)
result = asyncio.run(generate_ensemble_forecast(...))
print(f'Models used: {list(result.ensemble_weights.keys())}')
# TFT weight may be 0 if not trained - that's OK
print('✅ Graceful degradation validation PASSED')
"

# Compare: Avg MAPE must be ≤ 2.05% (no regression from baseline)
# Verify: TFT training completes in <30 min (GPU) or <60 min (CPU)
# Verify: model_registry table has TFT checkpoint
# Verify: Ensemble works even if TFT unavailable (graceful degradation)
```

---

## Testing Methodology for Stories 6.12-6.14 (CRITICAL)

**Source:** Stories 6.7, 6.10, 6.11 validation results (2025-12-08 to 2025-12-09)

### Validated Baseline Results (BEFORE Model Enhancement)

| Test Suite | Variables | Avg MAPE | Improvement | Status |
|------------|-----------|----------|-------------|--------|
| **Story 6.10** (12-var cement) | 8/8 PASS | **2.05%** | 97.3% | ✅ |
| **Story 6.11** (MCP ensemble) | 8/8 PASS | **2.2%** | 97% | ✅ |
| **Story 6.7** (cement demand) | 1/1 PASS | **9.0%** | 40% | ✅ |

**Best Baseline for Comparison:** Story 6.10 = **2.05% avg MAPE** (8 cement industry variables)

### Per-Variable Baseline (Story 6.10 Results)

| Variable | Baseline MAPE | Multi-var MAPE | Target |
|----------|---------------|----------------|--------|
| Revenue | 51.5% | **2.8%** | <5.0% |
| EBITDA | 131.6% | **2.5%** | <5.0% |
| Sales Volume | 119.8% | **0.8%** | <5.0% |
| Electricity Cost | 85.2% | **3.0%** | <8.0% |
| Thermal Energy | 54.0% | **2.6%** | <10.0% |
| Variable Cost | 72.3% | **0.7%** | <8.0% |
| Avg Selling Price | 63.6% | **1.6%** | <6.0% |
| Capacity Utilization | 133.6% | **2.5%** | <10.0% |

### Required Validation Scripts

```bash
# PRIMARY: 12-variable cement forecasting (Story 6.10)
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data

# MCP multi-variate validation (Story 6.11)
uv run python scripts/validate-mcp-multivariate-forecasting.py

# MCP ensemble validation (Story 6.11)
uv run python scripts/validate-mcp-ensemble-forecasting.py

# Cement demand ground truth (Story 6.7)
uv run python scripts/validate-epic6-accuracy.py
```

### Model-Specific Validation Requirements

#### For CatBoost (Story 6.12)
```python
# Run ensemble with CatBoost enabled
result = await generate_ensemble_forecast(
    metric="revenue",
    historical_data=train_data,
    external_regressors=regressors,
    models=["prophet", "linear", "xgboost", "lightgbm", "catboost"],
)
assert result.ensemble_weights.get("catboost", 0) > 0, "CatBoost not in ensemble"
assert mape <= 0.0205, f"Regression! MAPE={mape:.2%} exceeds 2.05% baseline"
```

#### For Chronos-2 (Story 6.13)
```python
# Test 1: Cold-start path (<6 data points)
short_data = TimeSeriesData(points=train_data.points[:5])  # Only 5 points
result = await generate_forecast(metric="new_metric", historical_data=short_data)
assert "chronos" in result.model_type.lower(), "Cold-start should use Chronos-2"

# Test 2: Ensemble member (≥6 data points)
result = await generate_ensemble_forecast(
    metric="revenue",
    historical_data=train_data,
    models=["prophet", "chronos"],
)
assert result.ensemble_weights.get("chronos", 0) > 0, "Chronos not in ensemble"
```

#### For TFT (Story 6.14)
```python
# Test 1: Training workflow
train_result = await retrain_forecasting_models(models="tft", force=True)
assert train_result.status == "success"
assert Path(train_result.checkpoint_path).exists()

# Test 2: Inference with trained model
result = await generate_ensemble_forecast(
    metric="revenue",
    historical_data=train_data,
    models=["prophet", "tft"],
)
# TFT may have weight=0 if not trained - that's graceful degradation
```

#### For Adaptive Weights (Story 6.12)
```python
# Verify weights stored in PostgreSQL
weights = await get_model_weights(metric="revenue")
assert sum(weights.values()) == pytest.approx(1.0, abs=0.001)
assert all(0.05 <= w <= 0.50 for w in weights.values()), "Weight caps violated"
```

### Working Regressors by Variable Type

| Variable Type | Regressors | Source |
|--------------|------------|--------|
| **Financial** (Revenue, EBITDA) | euribor_3m, diesel, ttf_gas, api2_coal | ECB, EU Oil, ICE |
| **Energy** (Electricity, Thermal) | eurostat_electricity, ttf_gas, api2_coal | Eurostat, ICE |
| **Production** (Volume, Capacity) | euribor_3m, diesel, ttf_gas | ECB, EU Oil, ICE |
| **Pricing** (Avg Selling Price) | diesel, euribor_3m, ttf_gas | EU Oil, ECB, ICE |

### APIs with Historical Data (USE FOR VALIDATION)

| API | Historical Range | Records | Use Case |
|-----|------------------|---------|----------|
| **ICE API2 Coal** | 751 days | 751 | ✅ Energy costs |
| **ICE TTF Gas** | 752 days | 752 | ✅ Energy costs |
| **BPstat EURIBOR** | 2018-2025 | 83 | ✅ Financial metrics |
| **Eurostat Electricity** | 2020+ | 5+ | ✅ Industrial prices |

### APIs with Recent Data Only (PRODUCTION ONLY - NOT FOR VALIDATION)

| API | Range | Why Not for Validation |
|-----|-------|------------------------|
| OMIE Electricity | Last 7 days | No historical overlap |
| CO2_EUA | Last 7 days | No historical overlap |
| EU Oil Bulletin | Last 14 days | No historical overlap |
| INE Building Permits | ❌ BROKEN | Wrong indicator (returns death stats) |

### Success Criteria for Stories 6.12-6.14

| Metric | Current Baseline | Target | Validation Method |
|--------|------------------|--------|-------------------|
| **Avg MAPE (8 vars)** | 2.05% | ≤ 2.05% | `validate-cement-forecasting-12vars.py` |
| **8-var pass rate** | 100% | 100% | All 8 variables within target |
| **Cold-start** | FAILS | WORKS | Test with 3-5 data points |
| **Models in ensemble** | 4 | 6 | Verify ensemble_weights includes all |
| **Adaptive weights** | Static | Adaptive | Check PostgreSQL model_weights table |
| **TFT training** | N/A | <30 min | Time training workflow |

### CI/CD Integration

```yaml
# .github/workflows/ci.yaml - Add accuracy regression gate
- name: Run accuracy regression tests
  run: |
    uv run pytest tests/integration/test_epic6_accuracy_regression.py -v
    uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data
  env:
    MAPE_CI_GATE: 0.12  # Fail if MAPE > 12%
    MAPE_WARNING: 0.025  # Warning if MAPE > 2.5% (regression from 2.05%)
```

### Reference Documents

- **Baseline report:** `docs/baseline-accuracy-2025-12-10.md`
- **Ground truth:** `tests/ground_truth/cement_demand_2020_2024.csv`
- **Validation scripts:** `scripts/validate-*.py`
- **CI tests:** `tests/integration/test_epic6_accuracy_regression.py`
- **Story 6.10:** `docs/stories/6.10-forecasting-data-quality.md`
- **Story 6.11:** `docs/stories/6.11-mcp-multivariate-forecasting.md`

---

## Epic Impact on Epic 5

### Story 5.1: Cloud Infrastructure Architecture

**Updates Required:**

1. **AC2 (Architecture Diagram):**
   - ADD: External data pipeline (INE, BPstat, OMIE, IPMA APIs) → PostgreSQL
   - ADD: Data refresh scheduler (APScheduler or AWS EventBridge)
   - SHOW: Connection from AgentCore Runtime to external APIs

2. **AC4 (Cost Optimization):**
   - UPDATE: API egress costs (~$1-2/month additional for external API calls)
   - UPDATE: PostgreSQL storage for external data (~500MB historical data)

3. **AC9 (Migration Plan):**
   - ADD: **Epic 6 Data Migration Steps:**
     - Deploy PostgreSQL schema (Story 6.2 migrations)
     - Initial external data load (2020-2025 historical via Story 6.1 API clients)
     - Configure data refresh scheduler (APScheduler → AWS EventBridge migration)
     - Migrate API credentials to AWS Secrets Manager

### Story 5.2: Containerization & Cloud Deployment

**Updates Required:**

1. ADD: Epic 6 forecasting module to container build (Stories 6.3-6.4 code)
2. ADD: PostgreSQL external data schema deployment (Story 6.2 migrations)
3. ADD: AWS EventBridge configuration for data refresh (replace APScheduler in cloud)
4. ADD: External API credentials in AWS Secrets Manager (INE, BPstat, OMIE, IPMA tokens)
5. ADD: Security group rules for outbound API calls (HTTPS to external sources)

### Story 5.13: API Documentation (MCP Tool Reference)

**Updates Required:**

1. ADD: Document Epic 6 MCP tools:
   - `query_external_data(source, date_range, metric)` (Story 6.6)
   - `refresh_external_data(source_name)` (Story 6.5 manual trigger)
   - `forecast_with_model(metric, model_type, periods_ahead)` (Story 6.4 ensemble selection)

2. UPDATE: `get_financial_forecast()` documentation:
   - Now supports multi-variate forecasting (Story 6.3)
   - Now supports model selection: "prophet", "linear", "xgboost", "ensemble" (Story 6.4)

---

## References

- **Sprint Change Proposal:** SCP-2025-12-04-001
- **Research Document:** `docs/High-Level Overview.pdf` (27 pages)
- **Data Source Summary:** `docs/Summary of Access Paths for Tier 1 & Tier 2 Data Sources (Portugal).pdf`
- **Epic 4 Forecasting Implementation:** `raglite/forecasting/hybrid.py`
- **Technology Stack Document:** `docs/architecture/5-technology-stack-definitive.md`

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **API Rate Limits** | Implement exponential backoff, use VCR.py for tests, respect quotas |
| **Data Quality Issues** | Pydantic validation, outlier detection, fallback to cached data |
| **Model Complexity** | Start with Prophet multi-variate (Story 6.3), ensemble optional (Story 6.4) |
| **Accuracy Not Met** | Tier 2 sources as backup (Story 6.8), decision gate at Story 6.7 |
| **Timeline Overrun** | P1 stories (6.4, 6.6) can be deferred if needed, focus on P0 first |

---

## Next Steps

1. ✅ Epic 6 PRD APPROVED (this document)
2. Draft individual story files (6.1-6.8) in `docs/stories/`
3. Update Epic 5 stories (5.1, 5.2, 5.13) with Epic 6 requirements
4. Update technology stack document with approved libraries
5. Begin Story 6.1 implementation (Tier 1 API clients)
