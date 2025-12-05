# 6. External Data Pipeline Architecture (Epic 6)

**Version:** 1.0
**Date:** 2025-12-04
**Epic:** Epic 6 - Advanced Forecasting with External Data
**Sprint Change Proposal:** SCP-2025-12-04-001

---

## Overview

Epic 6 extends RAGLite's forecasting capabilities from univariate time-series (Epic 4 Prophet-only) to multi-variate forecasting using external Portuguese/EU data sources. This document specifies the architecture for external data ingestion, storage, refresh, and integration with the forecasting engine.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  External Data Pipeline (Epic 6)                            │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  1. DATA SOURCES (External APIs & Manual)                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐        │
│  │ INE API     │  │ BPstat API  │  │ OMIE API     │        │
│  │ (JSON)      │  │ (JSON)      │  │ (JSON)       │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘        │
│         │                │                 │                 │
│  ┌──────▼──────┐  ┌─────▼──────┐  ┌───────▼────────┐       │
│  │ IPMA API    │  │ EU Oil     │  │ Manual Sources │       │
│  │ (JSON)      │  │ Bulletin   │  │ (CSV/Scraping) │       │
│  └──────┬──────┘  └──────┬─────┘  └───────┬────────┘       │
│         │                │                 │                 │
└─────────┼────────────────┼─────────────────┼─────────────────┘
          │                │                 │
          ▼                ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│  2. INGESTION LAYER (raglite/external_data/clients/)        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Client Abstract Base Class                      │  │
│  │  ├─ fetch_data(date_range) → DataFrame               │  │
│  │  ├─ validate_data(df) → bool                         │  │
│  │  ├─ retry_with_backoff(func, attempts=3)             │  │
│  │  └─ handle_errors(exception) → fallback_data         │  │
│  └──────────────────────────────────────────────────────┘  │
│         ▲         ▲         ▲         ▲         ▲          │
│         │         │         │         │         │          │
│  ┌──────┴─┐  ┌───┴───┐  ┌──┴───┐  ┌──┴───┐  ┌──┴────┐    │
│  │INEClient│ │BPstat │  │OMIE  │  │IPMA  │  │Manual │    │
│  │         │ │Client │  │Client│  │Client│  │Client │    │
│  └─────────┘ └───────┘  └──────┘  └──────┘  └───────┘    │
│                                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  3. VALIDATION & NORMALIZATION                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Pydantic Data Models                                │  │
│  │  ├─ ExternalDataPoint(date, metric, value, unit)     │  │
│  │  ├─ ExternalDataSource(name, api_endpoint, freq)     │  │
│  │  └─ DataValidationError(source, reason, timestamp)   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Normalization Pipeline                              │  │
│  │  ├─ Convert date formats to ISO 8601                 │  │
│  │  ├─ Standardize units (EUR, MWh, count, etc.)        │  │
│  │  ├─ Handle missing values (interpolate/forward-fill) │  │
│  │  └─ Detect outliers (Z-score >3σ flagged)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  4. STORAGE LAYER (PostgreSQL)                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Table: external_data_sources                        │  │
│  │  ├─ id (PK)                                          │  │
│  │  ├─ source_name (UNIQUE)                             │  │
│  │  ├─ api_endpoint                                     │  │
│  │  ├─ refresh_frequency (daily/weekly/monthly)         │  │
│  │  ├─ last_refresh_at                                  │  │
│  │  └─ metadata (JSONB)                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Table: external_data_points                         │  │
│  │  ├─ id (PK)                                          │  │
│  │  ├─ source_id (FK → external_data_sources.id)        │  │
│  │  ├─ date (indexed)                                   │  │
│  │  ├─ metric_name (indexed)                            │  │
│  │  ├─ value (NUMERIC)                                  │  │
│  │  ├─ unit                                             │  │
│  │  └─ UNIQUE(source_id, date, metric_name)             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  5. DATA REFRESH SCHEDULER (APScheduler)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  APScheduler BackgroundScheduler                     │  │
│  │  ├─ JobStore: PostgreSQL (persistent jobs)           │  │
│  │  ├─ Executor: ThreadPoolExecutor (async HTTP calls)  │  │
│  │  └─ Timezone: UTC                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Scheduled Jobs                                      │  │
│  │  ├─ Daily 06:00 UTC: IPMA, OMIE, CO₂ EUA             │  │
│  │  ├─ Weekly Sunday 06:00: Building Permits, Diesel    │  │
│  │  └─ Monthly 1st 06:00: INE indexes, ATIC cement      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Error Handling                                      │  │
│  │  ├─ Retry failed jobs: 3 attempts, exponential       │  │
│  │  ├─ Log failures: ERROR level with context           │  │
│  │  └─ Staleness detection: Alert if >30 days old       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  6. FORECASTING INTEGRATION                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Prophet Multi-Variate (Story 6.3)                   │  │
│  │  ├─ add_regressor('building_permits')                │  │
│  │  ├─ add_regressor('electricity_price')               │  │
│  │  ├─ add_regressor('mortgage_loans')                  │  │
│  │  ├─ add_regressor('weather_temp')                    │  │
│  │  └─ add_regressor('diesel_price')                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Model Ensemble (Story 6.4)                          │  │
│  │  ├─ Prophet (multi-variate): 40% weight              │  │
│  │  ├─ LinearRegression (scikit-learn): 30% weight      │  │
│  │  ├─ XGBRegressor (XGBoost): 30% weight               │  │
│  │  └─ Weighted average for final forecast              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  7. MCP TOOLS (User Interface)                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  query_external_data(source, date_range, metric)     │  │
│  │  • Query specific data source                        │  │
│  │  • Date range: ISO format or shortcuts               │  │
│  │  • Returns: Time-series as JSON/markdown table       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  refresh_external_data(source_name=None)             │  │
│  │  • Manual trigger for data refresh                   │  │
│  │  • source_name=None: Refresh all sources             │  │
│  │  • Returns: Refresh status per source                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  get_financial_forecast() [Enhanced]                 │  │
│  │  • Now supports multi-variate forecasting            │  │
│  │  • Model selection: prophet/linear/xgboost/ensemble  │  │
│  │  • Returns: Forecast with confidence intervals       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow Sequence

### 1. Initial Data Load (Story 6.1)

```
User → MCP Tool: refresh_external_data(source_name=None)
     ↓
API Clients: Fetch 2020-2025 historical data (11 Tier 1 sources)
     ↓
Validation: Pydantic models validate data integrity
     ↓
PostgreSQL: Insert into external_data_points table
     ↓
Response: {
  "status": "success",
  "sources_refreshed": 11,
  "data_points_added": 1,234,
  "date_range": "2020-01-01 to 2025-12-04"
}
```

### 2. Scheduled Data Refresh (Story 6.5)

```
APScheduler: Trigger daily job at 06:00 UTC
     ↓
API Clients: Fetch latest data (IPMA, OMIE, CO₂ EUA)
     ↓
Validation: Check for missing values, outliers
     ↓
PostgreSQL: Upsert into external_data_points (UNIQUE constraint prevents duplicates)
     ↓
Logging: INFO "Data refresh successful for 3 sources"
     ↓
(If error)
     ↓
Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
     ↓
(If still fails)
     ↓
Logging: ERROR "Data refresh failed for OMIE after 3 attempts"
     ↓
Staleness Detection: Mark source as stale, alert if >30 days
```

### 3. Multi-Variate Forecast (Story 6.3)

```
User → MCP Tool: get_financial_forecast(metric="cement_demand", periods_ahead=4)
     ↓
PostgreSQL: Query external_data_points for 5-year historical data
     ↓
Correlation Analysis: Calculate Pearson correlation for each regressor
     ↓
Regressor Selection: Top 5 regressors with correlation >0.5
     ↓
Prophet: Add selected regressors via add_regressor()
     ↓
Forecast: Generate 4-period-ahead prediction with confidence intervals
     ↓
Response: {
  "metric": "cement_demand",
  "forecast": [
    {"date": "2025-01", "value": 123.4, "lower": 110.2, "upper": 136.6},
    {"date": "2025-02", "value": 125.8, "lower": 112.0, "upper": 139.6},
    ...
  ],
  "regressors_used": ["building_permits", "electricity_price", "mortgage_loans", "weather_temp", "diesel_price"],
  "accuracy": "±10.2%",
  "improvement_vs_baseline": "+25.3%"
}
```

### 4. Model Ensemble Forecast (Story 6.4)

```
User → MCP Tool: get_financial_forecast(metric="cement_demand", model="ensemble")
     ↓
Prophet Multi-Variate: Generate forecast (40% weight)
     ↓
LinearRegression (scikit-learn): Generate forecast (30% weight)
     ↓
XGBRegressor (XGBoost): Generate forecast (30% weight)
     ↓
Ensemble Voting: Weighted average of 3 models
     ↓
Response: {
  "metric": "cement_demand",
  "forecast": [...],
  "ensemble_details": {
    "prophet_forecast": 123.4,
    "linear_forecast": 121.8,
    "xgboost_forecast": 124.2,
    "weighted_average": 123.3
  },
  "accuracy": "±8.7%",
  "improvement_vs_prophet_only": "+32.1%"
}
```

---

## Component Specifications

### API Clients (Story 6.1)

**Base Class:** `ExternalDataClient` (abstract)

```python
class ExternalDataClient(ABC):
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.http_client = httpx.AsyncClient(timeout=30.0)

    @abstractmethod
    async def fetch_data(self, date_range: tuple[date, date]) -> pd.DataFrame:
        """Fetch data from external source for given date range."""
        pass

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate data integrity using Pydantic models."""
        pass

    async def retry_with_backoff(self, func, attempts: int = 3):
        """Retry failed API calls with exponential backoff."""
        pass

    def handle_errors(self, exception: Exception) -> pd.DataFrame:
        """Fallback to cached data if API unavailable."""
        pass
```

**Concrete Implementations:**
- `INEClient` - Portugal Statistics (Building Permits, Indexes)
- `BPstatClient` - Banco de Portugal (Mortgage Loans)
- `OMIEClient` - Iberian Electricity Market
- `IPMAClient` - Portugal Weather Service
- `ManualDataClient` - CSV/Web Scraping for manual sources

---

### PostgreSQL Schema (Story 6.2)

```sql
-- Metadata table
CREATE TABLE external_data_sources (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL UNIQUE,
    api_endpoint TEXT,
    data_type VARCHAR(50),
    refresh_frequency VARCHAR(20),
    last_refresh_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Time-series data points table
CREATE TABLE external_data_points (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES external_data_sources(id),
    date DATE NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value NUMERIC NOT NULL,
    unit VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_id, date, metric_name)
);

-- Indexes for performance
CREATE INDEX idx_data_points_source_date ON external_data_points(source_id, date);
CREATE INDEX idx_data_points_metric ON external_data_points(metric_name);
CREATE INDEX idx_sources_name ON external_data_sources(source_name);
```

---

### Data Refresh Scheduler (Story 6.5)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(url=settings.postgresql_url)
}

scheduler = BackgroundScheduler(jobstores=jobstores, timezone='UTC')

# Daily refresh (06:00 UTC)
scheduler.add_job(
    refresh_daily_sources,  # IPMA, OMIE, CO₂ EUA
    trigger='cron',
    hour=6,
    minute=0,
    id='daily_refresh',
    replace_existing=True
)

# Weekly refresh (Sunday 06:00 UTC)
scheduler.add_job(
    refresh_weekly_sources,  # Building Permits, Diesel
    trigger='cron',
    day_of_week='sun',
    hour=6,
    minute=0,
    id='weekly_refresh',
    replace_existing=True
)

# Monthly refresh (1st of month 06:00 UTC)
scheduler.add_job(
    refresh_monthly_sources,  # INE Indexes, ATIC Cement
    trigger='cron',
    day=1,
    hour=6,
    minute=0,
    id='monthly_refresh',
    replace_existing=True
)

scheduler.start()
```

---

## NFR Validation

### Performance (NFR13)

| Metric | Target | Validation |
|--------|--------|------------|
| API fetch time | <5s p95 | Story 6.1 integration tests |
| PostgreSQL query | <500ms for 5-year range | Story 6.2 EXPLAIN ANALYZE |
| Multi-variate forecast | <10s p95 | Story 6.3 performance tests |
| Ensemble forecast | <15s p95 | Story 6.4 performance tests |
| Data refresh (all sources) | <5 min p95 | Story 6.5 integration tests |

### Accuracy (Epic 6 Success Criteria)

| Metric | Target | Validation |
|--------|--------|------------|
| Multi-variate Prophet | ±12% MAPE | Story 6.7 ground truth |
| Ensemble (3 models) | ±10% MAPE | Story 6.7 ground truth |
| Improvement vs Epic 4 | 20-30% reduction in RMSE | Story 6.7 baseline comparison |

### Reliability

| Metric | Target | Implementation |
|--------|--------|----------------|
| API retry success | 99%+ (with 3 attempts) | Story 6.1 retry logic |
| Data staleness alert | <30 days | Story 6.5 detection |
| Scheduler uptime | 99.9%+ | APScheduler persistent jobs |

---

## Cloud Deployment Considerations (Story 5.2)

### Local Development (Docker Compose)

- APScheduler runs in FastMCP app container
- PostgreSQL shared with RAG data (different schema)
- API calls direct from app container (no proxy)

### AWS Production (AgentCore Runtime)

- **Replace APScheduler with AWS EventBridge:**
  - EventBridge rules trigger Lambda functions
  - Lambda invokes MCP tool: `refresh_external_data(source_name)`
  - Cost: $0 (free tier covers <1M events/month)

- **Security:**
  - API credentials in AWS Secrets Manager
  - Security groups allow outbound HTTPS to external sources
  - VPC endpoints NOT needed (public APIs)

- **Cost Impact:**
  - API egress: ~$1-2/month (HTTPS calls to external sources)
  - PostgreSQL storage: ~$0.50/month (500MB external data)
  - **Total:** +$1.50-2.50/month vs current estimate

---

## Migration Path (Epic 6 → Epic 5)

1. **Local Development (Epic 6 implementation):**
   - Use APScheduler for data refresh
   - Test with Docker Compose PostgreSQL
   - Validate accuracy locally before cloud deployment

2. **Cloud Deployment (Story 5.2):**
   - Migrate APScheduler jobs to AWS EventBridge
   - Deploy PostgreSQL schema to EC2 instance
   - Initial data load (2020-2025) via Story 6.1 API clients
   - Store API credentials in AWS Secrets Manager
   - Test data refresh via EventBridge triggers

3. **Post-Deployment (Epic 5 complete):**
   - Monitor API costs (CloudWatch)
   - Tune refresh frequencies if needed
   - Expand to Tier 2 sources if accuracy insufficient

---

## References

- Sprint Change Proposal: `docs/sprint-change-proposals/2025-12-04-epic-6-advanced-forecasting.md`
- PM Handoff: `docs/sprint-change-proposals/PM-HANDOFF-EPIC-6.md`
- Research Document: `docs/High-Level Overview.pdf` (27 pages)
- Epic 4 Forecasting: `raglite/forecasting/hybrid.py`
- Technology Stack: `docs/architecture/5-technology-stack-definitive.md`

---

**Document Version:** 1.0
**Last Updated:** 2025-12-04
**Status:** Ready for Epic 6 Implementation
