# Architect Agent Handoff: Epic 6 Architecture Updates

**Handoff Date:** 2025-12-04
**From:** Bob (Scrum Master)
**To:** Architect Agent
**Sprint Change Proposal:** SCP-2025-12-04-001 (APPROVED)

---

## Executive Summary

Ricardo (Product Owner) has approved **Epic 6: Advanced Forecasting with External Data** to be inserted between Epic 4 and Epic 5. This handoff provides everything the Architect agent needs to update architecture documents, technology stack, and create the external data pipeline architecture.

**Your Mission:**
1. Update architecture executive summary (diagrams, decision matrix)
2. Update technology stack definitive table
3. Create external data pipeline architecture document
4. Update AWS deployment architecture for Epic 6 components
5. Validate architecture consistency across all documents

---

## Context: Epic 6 Architecture Requirements

### New System Components

Epic 6 adds the following architectural components to RAGLite:

1. **External Data Ingestion Layer**
   - API clients for Portuguese/EU data sources (INE, BPstat, OMIE, IPMA, etc.)
   - Data validation and normalization pipeline
   - Error handling and retry logic

2. **External Data Storage**
   - PostgreSQL database for historical time-series data
   - Schema: `external_data_sources` + `external_data_points` tables
   - 5-year data retention (2020-2025)

3. **Data Refresh Scheduler**
   - APScheduler for periodic data updates (daily/weekly/monthly)
   - Manual refresh trigger via MCP tool
   - Staleness detection and alerting

4. **Enhanced Forecasting Engine**
   - Multi-variate Prophet (external regressors)
   - Model ensemble framework (Prophet + scikit-learn + XGBoost)
   - Weighted voting for predictions

5. **New MCP Tools**
   - `query_external_data()` - Query external sources
   - `refresh_external_data()` - Manual data refresh
   - Enhanced `get_financial_forecast()` - Multi-model support

---

## Architecture Document Updates

### 1. Update: `docs/architecture/2-executive-summary.md`

#### Section: Architectural Decision Summary (Lines 40-76)

**UPDATE: PostgreSQL Decision (Line 50)**

**Current:**
```markdown
| **SQL Database** | PostgreSQL | 16.10 LTS | Structured table storage for financial data | ⚠️ CONDITIONAL (Phase 2B) |
```

**Change To:**
```markdown
| **SQL Database** | PostgreSQL | 16.10 LTS | Structured table storage + external data (Epic 6) | ✅ APPROVED (Epic 6) |
```

**ADD: New Technologies (After line 57)**

```markdown
| **Task Scheduler** | APScheduler | 3.10+ | Periodic external data refresh (Epic 6) | ✅ APPROVED (Epic 6) |
| **ML Ensemble** | scikit-learn | 1.5+ | Model ensemble framework (Epic 6) | ✅ APPROVED (Epic 6) |
| **Gradient Boosting** | XGBoost | 2.1+ | Advanced forecasting ensemble (Epic 6) | ✅ APPROVED (Epic 6) |
```

---

#### Section: Architecture at a Glance (Lines 180-221)

**UPDATE: Monolithic Architecture Diagram**

**Current Diagram Missing:**
- External data pipeline
- PostgreSQL for external data
- Data refresh scheduler

**Updated Diagram:**

```markdown
## Architecture at a Glance (v1.2 - Epic 6 Enhanced)

```
┌──────────────────────────────────────────────────────────┐
│  MCP Clients (Claude Code, Claude Desktop)              │
└────────────────────┬─────────────────────────────────────┘
                     │ Model Context Protocol
┌────────────────────▼─────────────────────────────────────┐
│  RAGLite Monolithic Server (FastMCP)                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  MCP Tools Layer                                   │ │
│  │  • ingest_financial_document()                     │ │
│  │  • query_financial_documents()                     │ │
│  │  • get_financial_forecast() [Enhanced - Epic 6]    │ │
│  │  • query_external_data() [NEW - Epic 6]            │ │
│  │  • refresh_external_data() [NEW - Epic 6]          │ │
│  │  • generate_insights()                             │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Business Logic Modules                            │ │
│  │  ├─ ingestion/     → PDF extraction, chunking      │ │
│  │  ├─ retrieval/     → Vector search, synthesis      │ │
│  │  ├─ forecasting/   → Multi-variate, ensemble [E6]  │ │
│  │  ├─ insights/      → Anomaly detection, trends     │ │
│  │  └─ external_data/ → API clients, scheduler [NEW]  │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Shared Utilities                                  │ │
│  │  ├─ config.py      → Settings, environment vars    │ │
│  │  ├─ logging.py     → Structured logging            │ │
│  │  ├─ models.py      → Pydantic data models          │ │
│  │  ├─ clients.py     → Qdrant, Claude, PostgreSQL    │ │
│  │  └─ scheduler.py   → APScheduler [NEW - Epic 6]    │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────────┐      ┌──────────────────────────────┐
│  Data Layer      │      │  External Data Sources (API) │
│  ├─ Qdrant       │      │  ├─ INE (Building Permits)   │
│  ├─ PostgreSQL   │◄─────┤  ├─ BPstat (Mortgages)       │
│  │   • Financial│      │  ├─ OMIE (Electricity)       │
│  │   • External │      │  ├─ IPMA (Weather)           │
│  │     Data [E6]│      │  └─ Others (Tier 1/2)        │
│  └─ S3/Local FS  │      └──────────────────────────────┘
└──────────────────┘               ▲
                                   │
                          ┌────────┴─────────┐
                          │  Data Refresh    │
                          │  Scheduler       │
                          │  (APScheduler)   │
                          └──────────────────┘
```

**Deployment:** 2 Docker containers (app + Qdrant) + PostgreSQL (shared with RAG)
```

---

#### Section: AWS Production Deployment Architecture (Lines 227-312)

**UPDATE: Add External Data Components**

**Insert After Line 267 (Storage diagram):**

```markdown

### External Data Integration (Epic 6)

```
┌──────────────────────────────────────────────────────┐
│  AgentCore Runtime (FastMCP Server)                  │
│  ├─ External Data API Clients (httpx async)          │
│  ├─ Data Refresh Scheduler (AWS EventBridge)         │
│  └─ Forecasting Engine (multi-variate + ensemble)    │
└────────────────┬─────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌─────────────────┐   ┌──────────────────────────────┐
│ PostgreSQL      │   │ External APIs (HTTPS)        │
│ (EC2 t4g.small) │   │ ├─ INE API (JSON)            │
│ Tables:         │   │ ├─ BPstat API (JSON)         │
│ • external_data │   │ ├─ OMIE API (JSON)           │
│   _sources      │   │ ├─ IPMA API (JSON)           │
│ • external_data │   │ └─ EU Oil Bulletin (CSV)     │
│   _points       │   └──────────────────────────────┘
└─────────────────┘            ▲
                               │
                    ┌──────────┴──────────┐
                    │ AWS Secrets Manager │
                    │ (API Keys/Tokens)   │
                    └─────────────────────┘
```

**Cost Update:**
- API Egress: ~$1-2/month (HTTPS calls to external sources)
- PostgreSQL Storage: ~$0.50/month (500MB external data)
- AWS EventBridge: $0 (free tier covers <1M events/month)
- **Total:** $14-18/month (was $14-16/month)
```

**UPDATE: Migration Timeline (AC9)**

Add to Week 1 tasks:
```markdown
- Configure AWS Secrets Manager for external API credentials (INE, BPstat, OMIE, IPMA)
- Deploy PostgreSQL external data schema (Alembic migrations from Story 6.2)
- Initial external data load (2020-2025 historical via Story 6.1 API clients)
```

Add to Week 2 tasks:
```markdown
- Configure AWS EventBridge rules for data refresh (daily/weekly/monthly)
- Test external API connectivity from AgentCore Runtime (security groups)
- Validate forecasting ensemble in cloud environment
```

---

### 2. Update: `docs/architecture/5-technology-stack-definitive.md`

#### Section: Technology Stack Table (Lines 5-46)

**UPDATE: PostgreSQL Status (Line 15)**

**Current:**
```markdown
| **SQL Database** | PostgreSQL | 16.10 (LTS) | 2025-11-05 | Structured table storage for financial data | ⚠️ CONDITIONAL (Phase 2B/2C): IF Phase 2A fixed chunking <70% accuracy. PG 18 latest, 16.10 stable LTS |
```

**Change To:**
```markdown
| **SQL Database** | PostgreSQL | 16.10 (LTS) | 2025-12-04 | Structured table storage + external data (Epic 6) | ✅ APPROVED (Epic 6): Financial tables (Phase 2B) + external data sources. PG 18 latest, 16.10 stable LTS |
```

**ADD: New Technologies (After Line 21 - Prophet)**

```markdown
| **Task Scheduler** | APScheduler | 3.10+ | 2025-12-04 | Periodic external data refresh | Lightweight Python scheduler, persistent jobs in PostgreSQL, no external deps |
| **ML Framework** | scikit-learn | 1.5+ | 2025-12-04 | Model ensemble (Linear Regression) | Industry standard ML library, numpy/scipy compatible |
| **Gradient Boosting** | XGBoost | 2.1+ | 2025-12-04 | Advanced forecasting ensemble | State-of-art boosting for time-series, production-proven |
```

---

#### Section: Technology Stack Approval Status (Lines 49-77)

**UPDATE: Remove PostgreSQL from Conditional, Add Epic 6 Technologies**

**Remove This Section (Lines 57-66):**
```markdown
**Phase 2B-C (CONDITIONAL - Decision Gate Approval)**:
- ⚠️ **PostgreSQL**: ONLY if Phase 2A Fixed Chunking <70% accuracy (requires Structured Multi-Index)
  - **Trigger**: Phase 2A decision gate (T+17, Week 3 Day 3)
  - **Probability**: 15% (research suggests 80% chance Phase 2A achieves 68-72%)
  - **Decision Authority**: PM (John) approves based on accuracy validation results
```

**Replace With:**
```markdown
**Epic 6 (APPROVED - 2025-12-04)**:
- ✅ **PostgreSQL 16.10 LTS**: APPROVED for Epic 6 external data storage
  - **Rationale**: Store Tier 1/2 time-series data (INE, BPstat, OMIE, IPMA, etc.)
  - **Schema**: `external_data_sources` + `external_data_points` tables
  - **Decision Authority**: Ricardo (Product Owner) - SCP-2025-12-04-001

- ✅ **APScheduler 3.10+**: APPROVED for periodic data refresh
  - **Rationale**: Lightweight Python scheduler, persistent jobs in PostgreSQL
  - **Alternative Considered**: AWS EventBridge (cloud-only, rejected for local dev)
  - **Decision Authority**: Ricardo (Product Owner) - SCP-2025-12-04-001

- ✅ **scikit-learn 1.5+**: APPROVED for ML ensemble framework
  - **Rationale**: Industry standard, integrates with Prophet for multi-model forecasting
  - **Models**: Linear Regression with external regressors
  - **Decision Authority**: Ricardo (Product Owner) - SCP-2025-12-04-001

- ✅ **XGBoost 2.1+**: APPROVED for gradient boosting ensemble
  - **Rationale**: State-of-art forecasting accuracy, production-proven
  - **Alternative Considered**: LightGBM (XGBoost chosen for better documentation)
  - **Decision Authority**: Ricardo (Product Owner) - SCP-2025-12-04-001
```

---

#### Section: Add Epic 6 Dependencies (After Line 77)

**ADD NEW SECTION:**

```markdown
---

## Epic 6: Advanced Forecasting with External Data

**Timeline:** 3-4 weeks (14-20 days)
**Status:** Backlog (waiting for PM to create stories)
**Dependencies:** Epic 4 complete (DONE)

### New Dependencies

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **PostgreSQL** | 16.10 LTS | External data storage | Structured time-series data for 11 Tier 1 sources, 5-year retention |
| **APScheduler** | 3.10+ | Data refresh scheduler | Daily/weekly/monthly refresh for external sources, persistent jobs |
| **scikit-learn** | 1.5+ | ML ensemble | Linear Regression for multi-variate forecasting |
| **XGBoost** | 2.1+ | Gradient boosting | Advanced ensemble for 20-30% accuracy improvement |
| **httpx** | 0.28.1+ | HTTP client | Async API calls to INE, BPstat, OMIE, IPMA (already approved) |
| **pandas** | 2.0+ | Data manipulation | Time-series processing (already approved) |

### External Data Sources (Tier 1)

**11 datasets integrated via API/CSV:**
1. **INE (Portugal Statistics):** Building Permits, Construction Output Index, Construction Cost Index
2. **ATIC:** Cement Consumption (CSV if no API)
3. **Banco de Portugal BPstat:** Mortgage Loans
4. **OMIE:** Electricity Prices (Iberian market)
5. **EU Oil Bulletin:** Diesel Prices
6. **IPMA (Portugal Weather):** Temperature, Rainfall
7. **Base.gov.pt:** Public Works Contracts
8. **Manual/Scraping:** Coal/Petcoke Prices, CO₂ EUA Prices

**Tier 2 Sources (Conditional):** 9 additional datasets IF Story 6.7 accuracy <±12%

### Architecture Impact

**New Modules:**
- `raglite/external_data/` - API clients, data validation, scheduler
- `raglite/forecasting/ensemble.py` - Multi-model framework (Prophet + scikit-learn + XGBoost)

**Enhanced Modules:**
- `raglite/forecasting/hybrid.py` - Add multi-variate Prophet with external regressors
- `raglite/shared/clients.py` - Add PostgreSQL external data client

**Database Schema:**
- PostgreSQL tables: `external_data_sources`, `external_data_points`
- Indexes: (source_id, date), (metric_name)

**MCP Tools:**
- `query_external_data(source, date_range, metric)` - Query external sources
- `refresh_external_data(source_name)` - Manual data refresh trigger
- Enhanced `get_financial_forecast()` - Multi-model support

---
```

---

### 3. CREATE: `docs/architecture/6-external-data-pipeline-epic-6.md`

**NEW FILE - Complete External Data Pipeline Architecture**

```markdown
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
```

---

## Action Items for Architect Agent

### Immediate Tasks (Update Architecture Docs)

1. **UPDATE:** `docs/architecture/2-executive-summary.md`
   - Line 50: Change PostgreSQL from CONDITIONAL to APPROVED
   - Add 3 new technologies: APScheduler, scikit-learn, XGBoost
   - Lines 180-221: Update architecture diagram with external data pipeline
   - Lines 227-312: Update AWS deployment for Epic 6 components

2. **UPDATE:** `docs/architecture/5-technology-stack-definitive.md`
   - Line 15: Update PostgreSQL status to APPROVED (Epic 6)
   - Add APScheduler, scikit-learn, XGBoost to tech stack table
   - Update approval status section (remove PostgreSQL from conditional, add Epic 6 section)
   - Add Epic 6 dependencies section

3. **CREATE:** `docs/architecture/6-external-data-pipeline-epic-6.md`
   - Complete external data pipeline architecture (copy from template above)
   - Data flow diagrams
   - Component specifications
   - NFR validation matrix
   - Cloud deployment considerations

4. **VALIDATE:** Architecture consistency
   - Ensure all Epic 6 references align across documents
   - Verify technology stack versions match
   - Check deployment cost estimates updated

---

## Key Decisions Already Made (Approved by Ricardo)

✅ Epic 6 external data pipeline architecture
✅ PostgreSQL unconditional approval (Epic 6 use case)
✅ APScheduler for local dev, AWS EventBridge for cloud
✅ Multi-variate Prophet + ensemble (3 models)
✅ 11 Tier 1 data sources (INE, BPstat, OMIE, IPMA, etc.)
✅ 5-year data retention (2020-2025)

---

## Resources

**Documents:**
- Sprint Change Proposal: `docs/sprint-change-proposals/2025-12-04-epic-6-advanced-forecasting.md`
- PM Handoff: `docs/sprint-change-proposals/PM-HANDOFF-EPIC-6.md`
- Research PDF: `docs/High-Level Overview.pdf` (27 pages, data source details)

**Current Architecture:**
- Executive Summary: `docs/architecture/2-executive-summary.md`
- Tech Stack: `docs/architecture/5-technology-stack-definitive.md`
- Epic 4 Forecasting: `raglite/forecasting/hybrid.py` (Prophet baseline)

**Sprint Status:**
- Epic 6 added: `docs/sprint-status.yaml` (lines 132-148)
- Epic 6 added: `docs/sprint-artifacts/sprint-status.yaml` (lines 110-126)

---

## Questions for Architect Agent?

If you need clarification on architecture decisions, refer to:
1. Sprint Change Proposal (comprehensive technical specifications)
2. Research PDF (data source API details)
3. Contact Ricardo for product-level decisions
4. Contact Bob (SM) for process questions

---

**Handoff Complete. Ready for Architect Agent to update architecture documents.**

**Next Step:** Activate Architect agent and reference this handoff document.
