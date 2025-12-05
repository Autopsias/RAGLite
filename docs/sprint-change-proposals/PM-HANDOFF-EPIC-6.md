# PM Agent Handoff: Epic 6 Story Creation

**Handoff Date:** 2025-12-04
**From:** Bob (Scrum Master)
**To:** PM Agent
**Sprint Change Proposal:** SCP-2025-12-04-001 (APPROVED)

---

## Executive Summary

Ricardo (Product Owner) has approved a new **Epic 6: Advanced Forecasting with External Data** to be inserted between Epic 4 (DONE) and Epic 5 (currently blocked). This handoff provides everything PM Agent needs to create Epic 6 PRD and 8 user stories.

**Your Mission:**
1. Create Epic 6 PRD file
2. Update PRD index and epic list
3. Draft 8 Epic 6 stories (6.1-6.8) using SM's create-story workflow
4. Update Epic 5 story references (Stories 5.1, 5.2, 5.13)

---

## Context: Why Epic 6?

### Problem Statement

Current forecasting (Epic 4) uses:
- **Algorithm:** Prophet-only (no ensemble)
- **Data:** Historical time-series from internal documents (univariate)
- **Accuracy:** ±15% (NFR10 met, but can improve)
- **Limitation:** No external macro-economic indicators

User requires:
1. **External Data Sources:** Portuguese/EU datasets (INE, BPstat, OMIE, IPMA)
2. **Multi-Variate Models:** Correlation analysis between drivers (building permits, energy prices, weather) and business outcomes
3. **Model Diversity:** Ensemble beyond Prophet (scikit-learn, XGBoost)
4. **Automated Refresh:** Scheduled data updates

### User Requirements (from Research PDFs)

Ricardo provided comprehensive research:
- **Document:** `docs/High-Level Overview.pdf` (27 pages)
- **Coverage:** Tier 1/2 data sources for cement industry demand prediction
- **Data Sources:** 20+ Portuguese/EU datasets with API access methods
- **Use Case:** Cement industry (can generalize to other sectors)

### Sprint Change Decision

**APPROVED Sequence:**
```
Epic 4 (DONE) → Epic 6 (NEW) → Epic 5 (Production)
```

**Rationale:**
- Story 5.1 only architecture-approved, no implementation started
- Testing external APIs locally easier than in cloud
- Story 5.2 deployment incomplete without Epic 6 data pipelines
- User explicit preference: "before we execute cloud migration"

---

## Epic 6 Specification

### Epic Goal

Enhance forecasting capabilities with multi-variate models using external Portuguese/EU data sources for cement industry demand prediction, enabling correlation analysis between macro-economic drivers and business KPIs.

### Epic Success Criteria

1. ✅ Tier 1 data sources integrated (11 datasets: INE, BPstat, OMIE, IPMA, etc.)
2. ✅ Multi-variate Prophet forecasting operational with external regressors
3. ✅ Model ensemble framework delivering 20-30% accuracy improvement over Epic 4 baseline
4. ✅ Automated data refresh scheduler operational (daily/weekly/monthly)
5. ✅ PostgreSQL external data storage schema implemented
6. ✅ Forecast accuracy validation: ±10% or better (vs Epic 4 ±15%)
7. ✅ MCP tools for external data queries and multi-model forecasting

### Epic Priority

**Priority:** P0 (blocks Epic 5 cloud deployment)

### Epic Timeline

**Duration:** 3-4 weeks (14-20 days)

---

## Technology Stack Changes (APPROVED)

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

## Data Sources (from Research PDF)

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

## Story Breakdown (8 Stories)

### Story 6.1: Tier 1 External Data Source Integration

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

### Story 6.2: PostgreSQL External Data Schema & Storage

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

### Story 6.3: Prophet Multi-Variate Forecasting (External Regressors)

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

### Story 6.4: Model Ensemble Framework (scikit-learn, XGBoost)

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

### Story 6.5: Automated Data Refresh Scheduler (APScheduler)

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

### Story 6.6: External Data Query Tool (MCP)

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

### Story 6.7: Multi-Variate Forecast Accuracy Validation

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

### Story 6.8: Tier 2 Data Sources Integration (Conditional)

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

## Epic 5 Story Updates Required

### Story 5.1: Cloud Infrastructure Architecture

**Current Status:** Architecture APPROVED (2025-12-04), implementation NOT started

**Updates Needed:**

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

**Updates Needed:**

1. ADD: Epic 6 forecasting module to container build (Stories 6.3-6.4 code)
2. ADD: PostgreSQL external data schema deployment (Story 6.2 migrations)
3. ADD: AWS EventBridge configuration for data refresh (replace APScheduler in cloud)
4. ADD: External API credentials in AWS Secrets Manager (INE, BPstat, OMIE, IPMA tokens)
5. ADD: Security group rules for outbound API calls (HTTPS to external sources)

### Story 5.13: API Documentation (MCP Tool Reference)

**Updates Needed:**

1. ADD: Document Epic 6 MCP tools:
   - `query_external_data(source, date_range, metric)` (Story 6.6)
   - `refresh_external_data(source_name)` (Story 6.5 manual trigger)
   - `forecast_with_model(metric, model_type, periods_ahead)` (Story 6.4 ensemble selection)

2. UPDATE: `get_financial_forecast()` documentation:
   - Now supports multi-variate forecasting (Story 6.3)
   - Now supports model selection: "prophet", "linear", "xgboost", "ensemble" (Story 6.4)

---

## PRD File Template

**File:** `docs/prd/epic-6-advanced-forecasting-external-data.md`

**Structure:**
```markdown
# Epic 6: Advanced Forecasting with External Data

**Epic Goal:** [Copy from "Epic Specification" section above]

**Priority:** P0 (blocks Epic 5)

**Timeline:** 3-4 weeks (14-20 days)

**Dependencies:** Epic 4 (DONE)

**Technology Stack Changes:**
[Table of APScheduler, scikit-learn, XGBoost, PostgreSQL approvals]

---

## Story 6.1: Tier 1 External Data Source Integration
[Full story from "Story Breakdown" section]

## Story 6.2: PostgreSQL External Data Schema & Storage
[Full story from "Story Breakdown" section]

... [Continue for all 8 stories]

---

## Data Sources Reference

**Tier 1 Sources:** [Table from "Data Sources" section]

**Tier 2 Sources:** [Table from "Data Sources" section]

---

## Epic Success Criteria
[Copy from "Epic Specification" section]

---

## References

- Sprint Change Proposal: SCP-2025-12-04-001
- Research Document: `docs/High-Level Overview.pdf`
- Epic 4 Forecasting: `raglite/forecasting/hybrid.py`
```

---

## Action Items for PM Agent

### Immediate Tasks (Create Stories)

1. **Create Epic 6 PRD:**
   - File: `docs/prd/epic-6-advanced-forecasting-external-data.md`
   - Use template above
   - Copy full story specifications from "Story Breakdown" section

2. **Update PRD Index:**
   - File: `docs/prd/index.md`
   - Add Epic 6 entry after Epic 4

3. **Update Epic List:**
   - File: `docs/prd/epic-list.md`
   - Add Epic 6 between Epic 4 and Epic 5

4. **Draft 8 Stories:**
   - Use SM's `*create-story` workflow (YOLO mode recommended)
   - Stories: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8
   - Reference: Full story specs in "Story Breakdown" section above

5. **Update Epic 5 Stories:**
   - Story 5.1: Add Epic 6 requirements (see "Epic 5 Story Updates" section)
   - Story 5.2: Add Epic 6 deployment components
   - Story 5.13: Add Epic 6 MCP tool documentation

### Story Creation Command

**Recommended Approach:**
```bash
# Activate SM agent
/bmad:bmm:agents:sm

# Select: *create-story
# Input: "Story 6.1" (PM will draft each story using research PDF as context)

# Repeat for Stories 6.2-6.8
```

**Alternative (if PM can create stories directly):**
- Use research PDF: `docs/High-Level Overview.pdf`
- Use Sprint Change Proposal: `docs/sprint-change-proposals/2025-12-04-epic-6-advanced-forecasting.md`
- Copy story specs from this handoff document

---

## Key Decisions Already Made (Approved by Ricardo)

✅ Epic 6 before Epic 5 (no cloud migration until Epic 6 complete)
✅ APScheduler for local data refresh
✅ scikit-learn for ML ensemble
✅ XGBoost for gradient boosting
✅ PostgreSQL unconditional approval (no longer conditional on Phase 2B)
✅ 3-4 week timeline acceptable (+4 weeks to production)

---

## Resources

**Documents:**
- Sprint Change Proposal: `docs/sprint-change-proposals/2025-12-04-epic-6-advanced-forecasting.md`
- Research PDF: `docs/High-Level Overview.pdf` (27 pages)
- Epic 4 Implementation: `raglite/forecasting/hybrid.py` (existing Prophet baseline)

**Sprint Status:**
- Epic 6 section added: `docs/sprint-status.yaml` (lines 132-148)
- Epic 6 section added: `docs/sprint-artifacts/sprint-status.yaml` (lines 110-126)

**Contacts:**
- User/Product Owner: Ricardo (final approval authority)
- Scrum Master: Bob (this handoff)
- Architect: (next to update architecture docs)

---

## Questions for PM Agent?

If you need clarification on any story, refer to:
1. Sprint Change Proposal document (comprehensive specification)
2. Research PDF (data source details)
3. Contact Ricardo for product-level decisions
4. Contact Bob (SM) for process questions

---

**Handoff Complete. Ready for PM Agent to create Epic 6 stories.**

**Next Step:** Activate PM agent and use `*create-story` workflow for Stories 6.1-6.8.
