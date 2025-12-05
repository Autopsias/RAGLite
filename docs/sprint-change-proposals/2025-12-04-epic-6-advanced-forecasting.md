# Sprint Change Proposal: Epic 6 - Advanced Forecasting with External Data

**Proposal ID:** SCP-2025-12-04-001
**Date:** 2025-12-04
**Status:** ✅ APPROVED
**Submitted By:** Bob (Scrum Master)
**Approved By:** Ricardo (Product Owner)

---

## Executive Summary

This Sprint Change Proposal inserts a new **Epic 6: Advanced Forecasting with External Data** between Epic 4 (DONE) and Epic 5 (Architecture-only). The change enhances RAGLite's forecasting capabilities from simple univariate time-series (Prophet-based) to multi-variate forecasting using external Portuguese/EU data sources and diverse predictive models.

**Impact:**
- **Timeline:** +3-4 weeks to production deployment (Epic 5 delayed)
- **Scope:** 8 new stories, 3 new technology approvals
- **Value:** 20-30% forecasting accuracy improvement, correlation analysis with macro-economic drivers

**Decision:** ✅ **APPROVED** (all components)

---

## Problem Statement

### Current State (Epic 4 Complete)

RAGLite's forecasting engine (Story 4.2) uses:
- **Algorithm:** Prophet statistical forecasting only
- **Data:** Historical time-series from internal documents (univariate)
- **Accuracy:** ±15% (NFR10 target met)
- **Limitations:**
  - No external data sources (macro-economic indicators)
  - No correlation analysis (cannot link drivers to outcomes)
  - Single model (Prophet only, no ensemble)

### Desired State (Epic 6 Goal)

Enhanced forecasting with:
1. **External Data Sources:** Tier 1/2 Portuguese datasets (INE, BPstat, OMIE, IPMA, etc.)
2. **Multi-Variate Models:** Prophet with external regressors (building permits, energy prices, weather, credit)
3. **Model Diversity:** Ensemble of Prophet + scikit-learn + XGBoost for robustness
4. **Automated Refresh:** Scheduled data updates (daily/weekly/monthly based on source)

### Trigger

User (Ricardo) initiated Correct Course workflow with:
- 27-page comprehensive research: "High-Level Overview.pdf" (Tier 1/2 data sources for cement industry)
- Explicit requirement: "External data sources + diverse predictive models"
- Timing preference: **BEFORE** Epic 5 cloud migration

---

## Epic Impact Assessment

### Epic Sequencing Change

**Original Sequence:**
```
Epic 4 (DONE) → Epic 5 (Production Readiness) → Production
                  └─ Week 12 target
```

**Approved Sequence:**
```
Epic 4 (DONE) → Epic 6 (Advanced Forecasting) → Epic 5 (Production Readiness) → Production
                          └─ 3-4 weeks                └─ 3 weeks                    └─ Week 16 target
```

**Rationale for Epic 6 First:**
1. ✅ Story 5.1 only architecture-approved, no implementation started
2. ✅ Testing external APIs locally is easier than in cloud
3. ✅ Validate data refresh frequency before AWS billing starts
4. ✅ Story 5.2 deployment plan incomplete without Epic 6 data pipelines
5. ✅ User explicit preference: "before we execute cloud migration"

### Dependencies

| Dependency | Status | Resolution |
|------------|--------|------------|
| Epic 4 Complete | ✅ DONE | No blocker |
| PostgreSQL | ⚠️ CONDITIONAL (Phase 2B) | ✅ APPROVED - Promote to unconditional |
| APScheduler | ❌ NOT IN STACK | ✅ APPROVED - Add to tech stack |
| scikit-learn | ❌ NOT IN STACK | ✅ APPROVED - Add to tech stack |
| XGBoost | ❌ NOT IN STACK | ✅ APPROVED - Add to tech stack |

### Blockers Resolved

**Epic 5 Story 5.2 (Cloud Deployment) was BLOCKED by:**
- Missing Epic 6 data pipeline deployment requirements
- No external API access configuration
- No data refresh scheduling mechanism

**Resolution:** Epic 6 completion unblocks Epic 5 implementation.

---

## Artifact Conflicts and Resolutions

### PRD Updates (PM Agent)

| File | Change | Status |
|------|--------|--------|
| `docs/prd/epic-6-advanced-forecasting-external-data.md` | ✅ CREATE new epic file | To Do |
| `docs/prd/epic-list.md` | ✅ ADD Epic 6 entry | To Do |
| `docs/prd/index.md` | ✅ ADD Epic 6 to TOC | To Do |
| `docs/prd/epic-5-production-readiness-real-time-operations.md` | ⚠️ UPDATE Stories 5.1, 5.2, 5.13 | To Do |

### Architecture Updates (Architect Agent)

| File | Change | Status |
|------|--------|--------|
| `docs/architecture/2-executive-summary.md` | ⚠️ UPDATE architecture diagram, decision matrix | To Do |
| `docs/architecture/5-technology-stack-definitive.md` | ⚠️ UPDATE tech stack table (add 3 new technologies) | To Do |
| `docs/architecture/[NEW]-external-data-pipeline.md` | ✅ CREATE external data architecture | To Do |

### Sprint Status Updates (SM Agent)

| File | Change | Status |
|------|--------|--------|
| `docs/sprint-artifacts/sprint-status.yaml` | ✅ ADD Epic 6 section | To Do |
| `docs/sprint-status.yaml` | ✅ UPDATE epic-4: done, add Epic 6 | To Do |

---

## Technology Stack Changes

### New Technologies APPROVED

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| **PostgreSQL** | 16.10 LTS | External data storage | ✅ Already conditionally approved (Phase 2B), now UNCONDITIONAL |
| **APScheduler** | 3.10+ | Periodic data refresh scheduler | Lightweight, no external dependencies, widely used |
| **scikit-learn** | 1.5+ | ML model ensemble (Linear Regression) | Industry standard, numpy/scipy compatible |
| **XGBoost** | 2.1+ | Gradient boosting ensemble | State-of-art forecasting, production-proven |

### Alternative Considerations (Rejected)

| Alternative | Why Rejected |
|-------------|--------------|
| AWS EventBridge (instead of APScheduler) | Cloud-only, requires Epic 5 first, contradicts user preference |
| Prophet-only (no ensemble) | Limits model diversity, reduces accuracy potential |
| Manual data refresh | Unsustainable, requires user intervention |

---

## Epic 6: Detailed Specification

### Epic Goal

Enhance forecasting capabilities with multi-variate models using external Portuguese/EU data sources for cement industry demand prediction, enabling correlation analysis between macro-economic drivers and business KPIs.

### Success Criteria

1. ✅ Tier 1 data sources integrated (11 datasets: INE, BPstat, OMIE, IPMA, etc.)
2. ✅ Multi-variate Prophet forecasting operational with external regressors
3. ✅ Model ensemble framework delivering 20-30% accuracy improvement over Epic 4 baseline
4. ✅ Automated data refresh scheduler operational (daily/weekly/monthly)
5. ✅ PostgreSQL external data storage schema implemented
6. ✅ Forecast accuracy validation: ±10% or better (vs Epic 4 ±15%)
7. ✅ MCP tools for external data queries and multi-model forecasting

### Timeline

**Estimated Duration:** 3-4 weeks (14-20 days)

**Story Breakdown:**

| Story | Description | Effort | Priority |
|-------|-------------|--------|----------|
| **6.1** | Tier 1 External Data Source Integration | 2-3 days | P0 |
| **6.2** | PostgreSQL External Data Schema & Storage | 1-2 days | P0 |
| **6.3** | Prophet Multi-Variate Forecasting (External Regressors) | 2-3 days | P0 |
| **6.4** | Model Ensemble Framework (scikit-learn, XGBoost) | 3-4 days | P1 |
| **6.5** | Automated Data Refresh Scheduler (APScheduler) | 1-2 days | P0 |
| **6.6** | External Data Query Tool (MCP) | 1 day | P1 |
| **6.7** | Multi-Variate Forecast Accuracy Validation | 2 days | P0 |
| **6.8** | Tier 2 Data Sources Integration (Conditional) | 2-3 days | P2 |

**Total:** 14-20 days (8 stories, 1 conditional)

### Data Sources (from Research PDFs)

**Tier 1 Sources (11 datasets):**
- Building Permits (INE API)
- Cement Consumption (ATIC - manual CSV if no API)
- Construction Output Index (INE API)
- Mortgage Loans (Banco de Portugal BPstat API)
- Electricity Price (OMIE API)
- Coal/Petcoke Price (manual web scraping)
- CO₂ EUA Price (manual web scraping)
- Diesel Price (EU Oil Bulletin API)
- Weather Data (IPMA API)
- Public Works Contracts (Base.gov.pt - CSV/scraping)
- Construction Cost Index (INE API)

**Tier 2 Sources (9 datasets - conditional):**
- House Price Index (INE)
- Bank Appraisal Values (Banco de Portugal)
- Construction Confidence Indicator (INE)
- Trade Data (Eurostat COMEXT)
- Others per research PDF

---

## Epic 5: Required Modifications

### Story 5.1: Cloud Infrastructure Architecture (IN-PROGRESS)

**Current Status:** Architecture APPROVED (2025-12-04), implementation NOT started

**Changes Required:**

1. **AC2 (Architecture Diagram):**
   - ADD: External data pipeline (INE, BPstat, OMIE, IPMA APIs)
   - ADD: PostgreSQL external data storage
   - ADD: Data refresh scheduler (APScheduler or AWS EventBridge)

2. **AC3 (Service Comparison Matrix):**
   - ADD: APScheduler OR AWS EventBridge comparison
   - ADD: PostgreSQL external data schema

3. **AC4 (Cost Optimization):**
   - UPDATE: API egress costs (~$1-2/month additional)
   - UPDATE: PostgreSQL storage for external data

4. **AC9 (Migration Plan):**
   - ADD: Epic 6 data migration steps:
     - PostgreSQL schema deployment
     - Initial external data load (2020-2025 historical)
     - Data refresh scheduler configuration

### Story 5.2: Containerization & Cloud Deployment (BACKLOG)

**Changes Required:**

1. ADD: Epic 6 forecasting module to container build
2. ADD: PostgreSQL external data schema deployment
3. ADD: AWS EventBridge configuration (if APScheduler not used locally)
4. ADD: External API credentials in AWS Secrets Manager (INE, BPstat, OMIE, IPMA)

### Story 5.13: API Documentation (BACKLOG)

**Changes Required:**

1. ADD: Document Epic 6 MCP tools:
   - `query_external_data(source, date_range, metric)`
   - `forecast_with_model(metric, model_type, periods_ahead)`
   - Updated `get_financial_forecast()` with multi-model support

---

## Implementation Plan

### Phase 1: Immediate Actions (Week 1)

**SM (Bob) - This Week:**
- ✅ Generate Sprint Change Proposal document
- ✅ Update `sprint-status.yaml` with Epic 6 section
- ✅ Route to PM and Architect agents

**PM Agent - Next:**
- CREATE: `docs/prd/epic-6-advanced-forecasting-external-data.md`
- UPDATE: `docs/prd/epic-list.md`, `docs/prd/index.md`
- DRAFT: 8 Epic 6 stories (6.1-6.8)

**Architect Agent - Next:**
- UPDATE: `docs/architecture/2-executive-summary.md`
- UPDATE: `docs/architecture/5-technology-stack-definitive.md`
- CREATE: External data pipeline architecture diagram

### Phase 2: Epic 6 Execution (Weeks 2-4)

**Dev Agent:**
- Story 6.1: Tier 1 data source integration (2-3 days)
- Story 6.2: PostgreSQL schema (1-2 days)
- Story 6.3: Multi-variate Prophet (2-3 days)
- Story 6.4: Model ensemble (3-4 days)
- Story 6.5: Data refresh scheduler (1-2 days)
- Story 6.6: MCP tools (1 day)
- Story 6.7: Accuracy validation (2 days)
- Story 6.8: Tier 2 sources (conditional, 2-3 days)

**QA Agent:**
- Unit tests for each story (80%+ coverage)
- Integration tests for external API calls
- Accuracy validation test suite

### Phase 3: Epic 5 Execution (Weeks 5-7)

**Dev Agent:**
- Story 5.1: Cloud infrastructure (update per Epic 6 changes)
- Story 5.2: Cloud deployment (include Epic 6 components)
- Stories 5.3-5.14: Remaining production features

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **External API failures** | Medium | High | Retry logic, fallback to cached data, error notifications |
| **Data source changes** | Low | Medium | API version pinning, data validation with Pydantic |
| **Accuracy below target** | Low | High | Decision gate at Story 6.7, Tier 2 sources as backup |
| **Timeline overrun** | Medium | Medium | Conditional Story 6.8 (Tier 2), XGBoost optional |
| **AWS cost increase** | Low | Low | API egress minimal (~$1-2/month), monitor usage |

---

## Success Metrics

### Epic 6 Completion Criteria

1. ✅ All 7 mandatory stories (6.1-6.7) complete and approved
2. ✅ Forecast accuracy: ±10% or better (20-30% improvement vs Epic 4 baseline)
3. ✅ External data coverage: 2020-2025 historical period for Tier 1 sources
4. ✅ Data refresh: Automated scheduler operational (daily/weekly/monthly)
5. ✅ Model ensemble: 3+ models operational (Prophet, scikit-learn, XGBoost)
6. ✅ Unit test coverage: 80%+ for Epic 6 modules
7. ✅ Integration tests: External API calls validated

### Epic 5 Unblocking Criteria

1. ✅ Story 5.2 deployment plan includes Epic 6 data pipelines
2. ✅ AWS cost estimate updated for external data
3. ✅ Cloud deployment tested with Epic 6 components

---

## Approval Record

**Proposal Submitted:** 2025-12-04
**Submitted By:** Bob (Scrum Master, BMAD)

**Approvals:**

| Decision | Approval Status | Approved By | Date |
|----------|----------------|-------------|------|
| **A. Epic Sequencing:** Epic 6 before Epic 5 | ✅ APPROVED | Ricardo (Product Owner) | 2025-12-04 |
| **B. Technology: APScheduler 3.10+** | ✅ APPROVED | Ricardo (Product Owner) | 2025-12-04 |
| **B. Technology: scikit-learn 1.5+** | ✅ APPROVED | Ricardo (Product Owner) | 2025-12-04 |
| **B. Technology: XGBoost 2.1+** | ✅ APPROVED | Ricardo (Product Owner) | 2025-12-04 |
| **C. Timeline: +3-4 weeks delay** | ✅ APPROVED | Ricardo (Product Owner) | 2025-12-04 |

**Overall Status:** ✅ **APPROVED - PROCEED WITH IMPLEMENTATION**

---

## Next Steps

1. **SM (Bob):** Update `sprint-status.yaml` with Epic 6 section
2. **PM Agent:** Create Epic 6 PRD and draft stories (6.1-6.8)
3. **Architect Agent:** Update architecture documents and tech stack
4. **Dev Agent:** Begin Story 6.1 implementation (after story creation)

---

## Appendices

### Appendix A: Research Documents

1. **High-Level Overview.pdf** (27 pages)
   - Driver-to-Data-Source Map for cement industry
   - Tier 1/Tier 2 data source catalogue
   - Integration plan and API access methods

### Appendix B: Current Forecasting Implementation

- **File:** `raglite/forecasting/hybrid.py`
- **Method:** Prophet + Mistral Large reasoning
- **Accuracy:** ±15% (NFR10 met)
- **Limitations:** Univariate time-series only, no external regressors

### Appendix C: Epic Sequencing Diagram

```
APPROVED SEQUENCE:

Epic 0: Week 0 Spike (DONE)
   ↓
Epic 1: Foundation (DONE)
   ↓
Epic 2: Advanced RAG (DONE)
   ↓
Epic 3: Agentic Orchestration (DONE)
   ↓
Epic 4: Forecasting & Insights (DONE)
   ↓
Epic 6: Advanced Forecasting ← NEW (3-4 weeks)
   ↓
Epic 5: Production Readiness (3 weeks)
   ↓
Production Deployment (Week 16)
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-04
**Status:** ✅ APPROVED - Ready for Implementation
