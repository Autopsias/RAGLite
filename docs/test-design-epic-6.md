# Test Design: Epic 6 - Advanced Forecasting with External Data

**Date:** 2025-12-12
**Author:** Ricardo
**Status:** Party-Approved ✅
**Reviewed By:** Tea, Dev, Architect, PM, SM (Party Mode 2025-12-12)

---

## Executive Summary

**Scope:** Full test design for Epic 6 (23 stories: 6.1-6.23)

**Risk Summary:**
- Total risks identified: 14
- High-priority risks (≥6): 5
- Critical categories: DATA, PERF, TECH, SEC

**Coverage Summary:**
- P0 scenarios: 28
- P1 scenarios: 35
- P2/P3 scenarios: 22
- **Total effort**: ~52 hours (~7 days) with Claude Code assistance

**Quality Gate:**
- **Minimum**: 10/12 variables meet MAPE targets
- **Target**: 12/12 variables meet MAPE targets

---

## Risk Assessment

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
|---------|----------|-------------|-------------|--------|-------|------------|-------|----------|
| R-001 | DATA | **Variable Cost MAPE at 41.43%** - Multi-entity data mixing (PT/TN/BR) causes 33% coefficient of variation | 3 | 3 | 9 | Entity detection filter (Story 6.15), Portugal-only extraction | DEV | Sprint 6 |
| R-002 | PERF | **Ensemble forecast timeout** - 7 models + external data may exceed 15s NFR | 2 | 3 | 6 | Model caching, parallel execution, timeout guards | DEV | Sprint 6 |
| R-003 | TECH | **API rate limiting** - INE/BPstat/OMIE may throttle or block requests | 2 | 3 | 6 | Exponential backoff, VCR.py mocking, cache fallback | DEV | Sprint 6 |
| R-004 | DATA | **Missing historical data** - Gaps in 2020-2025 data prevent regressor alignment | 2 | 3 | 6 | Interpolation, forward-fill (max 3 points), 10% threshold | DEV | Sprint 6 |
| R-005 | SEC | **API credential exposure** - External API keys in environment variables | 2 | 3 | 6 | AWS Secrets Manager (Epic 5), .env exclusion from git | DEV | Sprint 5 |

### Medium-Priority Risks (Score 3-4)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
|---------|----------|-------------|-------------|--------|-------|------------|-------|
| R-006 | TECH | **INE Building Permits bug** - Wrong indicator ID returns death statistics | 3 | 1 | 3 | Story 6.18 fix, Eurostat backup source | DEV |
| R-007 | PERF | **PostgreSQL query slowdown** - 5-year date range queries >500ms | 2 | 2 | 4 | Proper indexing, EXPLAIN ANALYZE validation | DEV |
| R-008 | TECH | **Prophet regressor limit** - Too many regressors cause overfitting | 2 | 2 | 4 | Max 7 regressors, correlation >0.5 filter | DEV |
| R-009 | OPS | **Scheduler job persistence** - APScheduler jobs lost on restart | 2 | 2 | 4 | PostgreSQL JobStore, job ID tracking | DEV |

### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
|---------|----------|-------------|-------------|--------|-------|--------|
| R-010 | OPS | Data staleness >30 days | 1 | 2 | 2 | Monitor via staleness detection |
| R-011 | BUS | Tier 2 sources needed | 1 | 2 | 2 | Conditional Story 6.8 gate |
| R-012 | TECH | XGBoost/CatBoost hyperparameter drift | 1 | 2 | 2 | Weekly backtest job |
| R-013 | TECH | Chronos-2 cold-start latency | 2 | 1 | 2 | Model caching, lazy loading |
| R-014 | OPS | TFT training timeout on CPU | 2 | 1 | 2 | GPU fallback, training budget |

### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

## Test Coverage Plan

### P0 (Critical) - Run on every commit

**Criteria**: Blocks core journey + High risk (≥6) + No workaround

| ID | Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
|----|-------------|------------|-----------|------------|-------|-------|
| 6.1-P0-001 | Tier 1 API clients functional | Integration | R-003 | 11 | QA | One per data source |
| 6.1-P0-002 | API retry with exponential backoff | Unit | R-003 | 3 | DEV | 3 attempts validation |
| 6.2-P0-001 | PostgreSQL schema creation | Integration | R-007 | 1 | QA | Alembic migration |
| 6.2-P0-002 | Data points CRUD operations | Unit | R-004 | 4 | DEV | Create/Read/Update/Delete |
| 6.3-P0-001 | Multi-variate Prophet with regressors | Integration | R-008 | 3 | QA | 5-7 regressors |
| 6.3-P0-002 | Missing data interpolation | Unit | R-004 | 5 | DEV | Linear, spline, forward-fill |
| 6.4-P0-001 | Ensemble voting (3+ models) | Integration | R-002 | 1 | QA | Weighted average |
| 6.4-P0-002 | Model fallback on failure | Unit | R-002 | 3 | DEV | Prophet-only fallback |
| 6.5-P0-001 | APScheduler job execution | Integration | R-009 | 3 | QA | Daily/Weekly/Monthly |
| 6.7-P0-001 | Accuracy validation ≤10% MAPE | E2E | R-001 | 1 | QA | Ground truth test set |
| 6.7-P0-002 | Baseline comparison (vs Epic 4) | E2E | R-001 | 1 | QA | 20-30% improvement |
| 6.12-P0-001 | CatBoost ensemble integration | Integration | - | 1 | QA | Adaptive weights |
| 6.13-P0-001 | Chronos-2 cold-start path | Integration | R-013 | 1 | QA | <6 data points |
| 6.15-P0-001 | Entity detection Portugal-only | Unit | R-001 | 5 | DEV | PT/TN/BR patterns |
| 6.15-P0-002 | Variable Cost MAPE <8% | E2E | R-001 | 1 | QA | Regression gate |
| 6.15-P0-003 | Portugal-only CV <15% | Unit | R-001 | 1 | DEV | Statistical validation |
| 6.2-P0-003 | PostgreSQL composite index | Integration | R-007 | 1 | QA | EXPLAIN ANALYZE |
| 6.23-P0-001 | 10/12 variables passing targets | E2E | R-001 | 1 | QA | Final validation |

**Total P0**: 30 tests, ~30 hours (with Claude Code)

### P1 (High) - Run on PR to main

**Criteria**: Important features + Medium risk (3-4) + Common workflows

| ID | Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
|----|-------------|------------|-----------|------------|-------|-------|
| 6.1-P1-001 | INE API data validation | Unit | R-006 | 3 | DEV | Pydantic models |
| 6.1-P1-002 | BPstat API client | Integration | - | 2 | QA | Mortgage loans |
| 6.1-P1-003 | OMIE electricity prices | Integration | - | 2 | QA | Daily data |
| 6.1-P1-004 | IPMA weather data | Integration | - | 2 | QA | Temp, rainfall |
| 6.2-P1-001 | Query performance <500ms | Integration | R-007 | 1 | QA | EXPLAIN ANALYZE |
| 6.2-P1-002 | Data retention policy | Unit | - | 2 | DEV | Soft delete |
| 6.3-P1-001 | Correlation analysis (Pearson) | Unit | R-008 | 3 | DEV | >0.5 threshold |
| 6.3-P1-002 | Regressor selection logic | Unit | R-008 | 2 | DEV | Top 5-7 |
| 6.4-P1-001 | XGBoost hyperparameter tuning | Unit | - | 2 | DEV | Grid search |
| 6.4-P1-002 | Model weight configuration | Unit | - | 2 | DEV | 40/30/30 |
| 6.5-P1-001 | Manual refresh MCP tool | Integration | - | 1 | QA | Force refresh |
| 6.5-P1-002 | Staleness detection | Unit | R-010 | 2 | DEV | >30 days alert |
| 6.6-P1-001 | query_external_data MCP tool | Integration | - | 3 | QA | Date range parsing |
| 6.12-P1-001 | Adaptive weights calculation | Unit | - | 3 | DEV | Backtest-driven |
| 6.12-P1-002 | Model weights persistence | Integration | - | 1 | QA | PostgreSQL table |
| 6.14-P1-001 | TFT training workflow | Integration | R-014 | 1 | QA | <30 min |
| 6.16-P1-001 | Eurostat construction output | Integration | - | 2 | QA | SDMX API |
| 6.17-P1-001 | ECB GDP/inflation | Integration | - | 2 | QA | SDW API |
| 6.18-P1-001 | INE building permits fix | Integration | R-006 | 2 | QA | Correct indicator |
| 6.20-P1-001 | Cement-industry regressor mappings | Unit | - | 4 | DEV | Per variable |
| 6.21-P1-001 | Unified validation script | E2E | - | 1 | QA | All 12 vars |
| 6.22-P1-001 | MCP validation tools | Integration | - | 3 | QA | 3 new tools |

**Total P1**: 35 tests, ~35 hours

### P2 (Medium) - Run nightly/weekly

**Criteria**: Secondary features + Low risk (1-2) + Edge cases

| ID | Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
|----|-------------|------------|-----------|------------|-------|-------|
| 6.1-P2-001 | EU Oil Bulletin parsing | Unit | - | 2 | DEV | Weekly CSV |
| 6.1-P2-002 | Manual CSV ingestion | Unit | - | 2 | DEV | Coal/Petcoke |
| 6.4-P2-001 | Ensemble performance comparison | Unit | - | 2 | DEV | RMSE/MAE/MAPE |
| 6.5-P2-001 | Scheduler timezone handling | Unit | - | 2 | DEV | UTC |
| 6.6-P2-001 | Data visualization hints | Unit | - | 1 | DEV | Chart suggestions |
| 6.8-P2-001 | Tier 2 source integration | Integration | R-011 | 3 | QA | Conditional gate |
| 6.13-P2-001 | Chronos-2 covariate support | Unit | - | 2 | DEV | External regressors |
| 6.14-P2-001 | TFT graceful degradation | Unit | R-014 | 2 | DEV | Skip if not trained |
| 6.19-P2-001 | EC Construction Confidence | Integration | - | 2 | QA | New client |
| 6.21-P2-001 | JSON export format | Unit | - | 1 | DEV | MCP-compatible |
| 6.22-P2-001 | get_regressor_data tool | Integration | - | 1 | QA | Live data fetch |

**Total P2**: 20 tests, ~10 hours

### P3 (Low) - Run on-demand

**Criteria**: Nice-to-have + Exploratory + Performance benchmarks

| ID | Requirement | Test Level | Test Count | Owner | Notes |
|----|-------------|------------|------------|-------|-------|
| 6.4-P3-001 | Model ensemble stress test | E2E | 1 | QA | 100 forecasts |
| 6.5-P3-001 | Scheduler recovery after crash | Integration | 1 | QA | Persistent jobs |

**Total P3**: 2 tests, ~1 hour

---

## Execution Order

### Smoke Tests (<5 min)

**Purpose**: Fast feedback, catch build-breaking issues

- [ ] PostgreSQL connection valid (30s)
- [ ] Qdrant connection valid (30s)
- [ ] At least 1 external API reachable (1min)
- [ ] `generate_forecast()` returns result (1min)
- [ ] MCP server starts without error (30s)

**Total**: 5 scenarios

### P0 Tests (<30 min)

**Purpose**: Critical path validation

- [ ] Entity detection filters Portugal-only (Unit)
- [ ] Multi-variate Prophet with 5 regressors (Integration)
- [ ] Ensemble forecast <15s (E2E)
- [ ] Variable Cost MAPE <8% (E2E)
- [ ] API retry logic works (Unit)
- [ ] Accuracy ≤10% MAPE (E2E)
- [ ] PostgreSQL composite index validation (Integration)

**Total**: 28 scenarios (~1 min average per test)

### P1 Tests (<45 min)

**Purpose**: Important feature coverage

- [ ] All Tier 1 API clients functional (Integration)
- [ ] PostgreSQL queries <500ms (Integration)
- [ ] MCP tools return valid responses (Integration)
- [ ] Correlation analysis selects top regressors (Unit)

**Total**: 35 scenarios

### P2/P3 Tests (<60 min)

**Purpose**: Full regression coverage

- [ ] Tier 2 sources (Integration)
- [ ] Edge cases (Unit)
- [ ] Stress tests (E2E)

**Total**: 22 scenarios

---

## Resource Estimates

### Test Development Effort (with Claude Code)

| Priority | Count | Hours/Test | Total Hours | Notes |
|----------|-------|------------|-------------|-------|
| P0 | 28 | 1.0 | 28 | Claude Code handles fixtures, boilerplate |
| P1 | 35 | 0.5 | 18 | Standard patterns, high reuse |
| P2 | 20 | 0.25 | 5 | Simple scenarios |
| P3 | 2 | 0.5 | 1 | Exploratory |
| **Total** | **85** | **-** | **~52** | **~7 days (1 sprint)** |

**Claude Code Efficiency Gains:**
- 2x speedup on boilerplate/fixtures
- Pattern reuse across similar test cases
- Automated assertion generation
- Solo dev + AI = effective 1.5-2 devs

### Prerequisites

**Test Data:**
- `cement_demand_2020_2024.csv` ground truth (faker-based, static)
- VCR.py cassettes for API mocking (recorded responses)
- PostgreSQL test fixtures (external_data_sources, external_data_points)

**Tooling:**
- pytest + pytest-asyncio for async tests
- VCR.py for API mocking
- hypothesis for property-based testing (edge cases)
- pytest-benchmark for performance validation

**Environment:**
- Docker Compose (Qdrant test:6335, PostgreSQL test:5433)
- APP_ENV=test (SafetyGuard enforcement)
- API credentials in test .env file

---

## VCR.py Cassette Strategy

**Best Practice (Party-Approved):** Live during development → Record cassettes → CI replay

### Development Phases

| Phase | Days | Activity | VCR Mode |
|-------|------|----------|----------|
| **Phase 1: Initial Dev** | 1-3 | Live API calls for rapid iteration | `record_mode='new_episodes'` |
| **Phase 2: Stabilization** | 4-5 | Record cassettes after API interactions stabilize | `record_mode='once'` |
| **Phase 3: CI/CD** | 6+ | Replay cassettes only, no network calls | `record_mode='none'` |

### Implementation

```python
# tests/conftest.py
import vcr

my_vcr = vcr.VCR(
    cassette_library_dir='tests/fixtures/cassettes/',
    record_mode='none',  # CI mode: replay only
    filter_headers=['Authorization', 'X-API-Key'],
    filter_query_parameters=['api_key'],
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query'],
)

# For local development with recording:
# VCR_RECORD_MODE=once pytest tests/integration/
```

### Cassette Maintenance

- **Monthly refresh job**: Re-record cassettes to catch API changes
- **Filter sensitive data**: API keys, timestamps, nonces
- **Directory structure**: `tests/fixtures/cassettes/{source_name}/`

---

## Quality Gate Criteria

### Pass/Fail Thresholds

- **P0 pass rate**: 100% (no exceptions)
- **P1 pass rate**: ≥95% (waivers required for failures)
- **P2/P3 pass rate**: ≥90% (informational)
- **High-risk mitigations**: 100% complete or approved waivers

### Coverage Targets

- **Critical paths**: ≥80%
- **External API clients**: 100% (11 Tier 1 sources)
- **Forecasting models**: 100% (7 models + ensemble)
- **MCP tools**: 100% (all Epic 6 tools)

### Non-Negotiable Requirements

- [ ] All P0 tests pass
- [ ] No high-risk (≥6) items unmitigated
- [ ] Variable Cost MAPE <8% (R-001 mitigation)
- [ ] Ensemble forecast <15s (R-002 mitigation)
- [ ] **Minimum**: 10/12 variables meet MAPE targets
- [ ] **Target**: 12/12 variables meet MAPE targets (stretch goal)

---

## Mitigation Plans

### R-001: Variable Cost MAPE at 41.43% (Score: 9)

**Mitigation Strategy:**
1. Implement entity detection (Story 6.15) to filter Portugal-only data
2. Normalize values to EUR/ton with range validation (-150 to -350)
3. Add cement-industry-specific regressors (construction_output, industrial_production)
4. Update regressor mappings (Story 6.20)

**Owner:** DEV Team
**Timeline:** Sprint 6 (Stories 6.15, 6.20)
**Status:** Planned
**Verification:** `validate-forecasting-unified.py --variable variable_cost` returns MAPE <8%

### R-002: Ensemble Forecast Timeout (Score: 6)

**Mitigation Strategy:**
1. Implement model caching (load once, reuse across calls)
2. Run Prophet/Linear/XGBoost in parallel (ThreadPoolExecutor)
3. Add timeout guard (15s max, fallback to best single model)
4. Chronos-2 lazy loading pattern

**Owner:** DEV Team
**Timeline:** Sprint 6 (Stories 6.4, 6.13)
**Status:** Planned
**Verification:** `pytest tests/integration/test_ensemble_forecasting.py -k timeout`

### R-003: API Rate Limiting (Score: 6)

**Mitigation Strategy:**
1. Exponential backoff (3 attempts: 1s, 2s, 4s)
2. **Per-source rate limit configurations:**
   - INE: 100 req/min
   - OMIE: 50 req/min
   - BPstat: 30 req/min (most fragile)
   - Eurostat: 60 req/min
   - ECB: 100 req/min
3. VCR.py cassettes for testing (no live API calls in CI)
4. Cached fallback data (stale data tolerance: 30 days)

**Owner:** DEV Team
**Timeline:** Sprint 6 (Story 6.1)
**Status:** Implemented (verify in tests)
**Verification:** `pytest tests/unit/test_external_data_clients.py -k retry`

---

## Test-to-Story Traceability

### Story 6.1: Tier 1 External Data Source Integration

| AC | Tests | Level | Priority |
|----|-------|-------|----------|
| AC1: API Clients Implemented | 6.1-P0-001, 6.1-P1-001 to 6.1-P1-004 | Integration | P0, P1 |
| AC2: Data Validation | 6.1-P1-001 | Unit | P1 |
| AC3: Error Handling | 6.1-P0-002 | Unit | P0 |
| AC4: Fallback Strategy | 6.1-P0-002 | Unit | P0 |
| AC5: Historical Data Load | 6.1-P0-001 | Integration | P0 |
| AC6: Unit Tests 80%+ | All 6.1 unit tests | Unit | P1 |
| AC7: Integration Tests | 6.1-P0-001 | Integration | P0 |

### Story 6.7: Accuracy Validation

| AC | Tests | Level | Priority |
|----|-------|-------|----------|
| AC1: Ground Truth Test Set | 6.7-P0-001 | E2E | P0 |
| AC2: Baseline Comparison | 6.7-P0-002 | E2E | P0 |
| AC3: Accuracy Metrics | 6.7-P0-001 | E2E | P0 |
| AC4: Automated Report | 6.7-P0-001 | E2E | P0 |
| AC5: Success Threshold | 6.7-P0-001, 6.23-P0-001 | E2E | P0 |
| AC6: Regression Tests | `test_epic6_accuracy_regression.py` | CI | P0 |

**AC6 Explicit Test File:** `tests/integration/test_epic6_accuracy_regression.py`
- Runs in CI on every PR to main
- MAPE gate: 12% max, 2.5% regression warning
- Validates all 12 variables against targets

### Story 6.15: Entity-Specific Variable Cost Extraction

| AC | Tests | Level | Priority |
|----|-------|-------|----------|
| AC1: Entity detection >95% accuracy | 6.15-P0-001 | Unit | P0 |
| AC2: Portugal-only CV <15% | 6.15-P0-003 | Unit | P0 |
| AC3: EUR/ton normalization | 6.15-P0-001 | Unit | P0 |
| AC4: Variable Cost MAPE <25% | 6.15-P0-002 | E2E | P0 |
| AC5: No regression in other metrics | 6.23-P0-001 | E2E | P0 |

**AC2 CV Validation Test (NEW):**
```python
# tests/unit/test_entity_detection.py
def test_portugal_only_coefficient_of_variation():
    """AC2: Portugal-only data has CV < 15%."""
    data = extract_variable_cost_portugal_only()
    cv = data.std() / data.mean() * 100
    assert cv < 15, f"CV {cv:.1f}% exceeds 15% threshold"
```

---

## Existing Test Coverage Analysis

### Tests Found (15+ files)

| File | Type | Coverage |
|------|------|----------|
| `tests/unit/test_external_data_clients.py` | Unit | Tier 1 API clients |
| `tests/unit/test_external_data_mcp.py` | Unit | MCP tool logic |
| `tests/unit/test_external_data_orm.py` | Unit | ORM models |
| `tests/unit/test_external_data_storage.py` | Unit | Storage layer |
| `tests/unit/test_ensemble_forecasting.py` | Unit | Ensemble voting |
| `tests/unit/test_hybrid_forecasting.py` | Unit | Prophet multi-variate |
| `tests/unit/test_multivariate_forecasting.py` | Unit | Regressor handling |
| `tests/integration/test_external_data_integration.py` | Integration | Full pipeline |
| `tests/integration/test_external_data_mcp.py` | Integration | MCP via protocol |
| `tests/integration/test_external_data_schema.py` | Integration | PostgreSQL schema |
| `tests/integration/test_forecast_external.py` | Integration | Forecast + external |
| `tests/integration/test_epic6_accuracy_regression.py` | Integration | Accuracy gates |
| `tests/health/test_external_data_health.py` | Health | API connectivity |
| `tests/validation/test_forecast_accuracy.py` | Validation | Ground truth |

### Coverage Gaps Identified

| Gap | Story | Priority | Action |
|-----|-------|----------|--------|
| Entity detection tests | 6.15 | P0 | NEW: Add to unit tests |
| CV validation (Portugal-only) | 6.15 | P0 | NEW: Add 6.15-P0-003 |
| CatBoost integration | 6.12 | P0 | NEW: Add to ensemble tests |
| Chronos-2 cold-start | 6.13 | P0 | NEW: Add integration test |
| PostgreSQL composite index | 6.2 | P0 | NEW: Add index validation test |
| TFT training workflow | 6.14 | P1 | NEW: Add integration test |
| Eurostat construction output | 6.16 | P1 | NEW: Add client test |
| ECB GDP/inflation | 6.17 | P1 | NEW: Add client test |
| EC Construction Confidence | 6.19 | P2 | NEW: Add client test |
| Unified validation script | 6.21 | P1 | NEW: Add E2E test |
| MCP validation tools | 6.22 | P1 | NEW: Add integration tests |

---

## Assumptions and Dependencies

### Assumptions

1. External API credentials available in test environment (.env)
2. VCR.py cassettes recorded for all Tier 1 API responses
3. PostgreSQL test database (port 5433) available via Docker Compose
4. Ground truth dataset (`cement_demand_2020_2024.csv`) is accurate
5. Epic 4 baseline accuracy (±15%) is reproducible

### Dependencies

1. **Story 6.1 → 6.2**: API clients needed before PostgreSQL storage
2. **Story 6.2 → 6.3**: Schema needed before multi-variate forecasting
3. **Story 6.3 → 6.4**: Multi-variate Prophet needed before ensemble
4. **Story 6.12 → 6.13**: Adaptive weights needed before Chronos-2 weighting
5. **Stories 6.15-6.20 → 6.21**: All improvements before unified validation

### Risks to Plan

- **Risk**: API cassettes become stale (external API changes)
  - **Impact**: Integration tests fail on updated endpoints
  - **Contingency**: Scheduled cassette refresh job (monthly)

- **Risk**: Ground truth data incomplete for new stories
  - **Impact**: Accuracy validation gaps
  - **Contingency**: Extend ground truth with synthetic scenarios

---

## CI Integration

### Accuracy Regression Gate

```yaml
# .github/workflows/ci.yaml - Epic 6 accuracy gate
- name: Run Epic 6 accuracy regression tests
  run: |
    uv run pytest tests/integration/test_epic6_accuracy_regression.py -v
    uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data
  env:
    MAPE_CI_GATE: 0.12  # Fail if MAPE > 12%
    MAPE_WARNING: 0.025  # Warning if MAPE > 2.5% (regression from 2.05%)
```

### Test Execution by Priority

```bash
# P0 only (critical, <10 min)
pytest tests/ -m "p0" --tb=short

# P0 + P1 (PR validation, <30 min)
pytest tests/ -m "p0 or p1" --tb=short

# Full regression (nightly, <60 min)
pytest tests/ --tb=short
```

---

## Approval

**Test Design Approved By:**

- [ ] Product Manager: Ricardo Date: ____
- [ ] Tech Lead: ____ Date: ____
- [ ] QA Lead: ____ Date: ____

**Comments:**

---

---

## Appendix

### Knowledge Base References

- `risk-governance.md` - Risk classification framework
- `probability-impact.md` - Risk scoring methodology
- `test-levels-framework.md` - Test level selection
- `test-priorities-matrix.md` - P0-P3 prioritization

### Related Documents

- PRD: `docs/prd/epic-6-advanced-forecasting-external-data.md`
- Architecture: `docs/architecture/6-external-data-pipeline-epic-6.md`
- Validation Methodology: `docs/prd/epic-6-advanced-forecasting-external-data.md#testing-methodology-for-stories-612-614-critical`

---

**Generated by**: BMad TEA Agent - Test Architect Module
**Workflow**: `.bmad/bmm/testarch/test-design`
**Version**: 4.1 (BMad v6)

---

## Party Mode Review Summary (2025-12-12)

**Participants:** Tea, Dev, Architect, PM, SM

**Key Decisions:**
1. ✅ Quality gate: 10/12 minimum, 12/12 target
2. ✅ Effort: ~52 hours with Claude Code (7 days, 1 sprint)
3. ✅ VCR Strategy: Live dev → Record cassettes → CI replay
4. ✅ R-003: Per-source retry configs (INE: 100, OMIE: 50, BPstat: 30)
5. ✅ New tests: CV validation (6.15-P0-003), PostgreSQL index (6.2-P0-003)
6. ✅ AC6 explicit: `test_epic6_accuracy_regression.py`
7. ✅ P0 timing: 30 min (realistic vs 15 min)

**Research Citation:**
- VCR.py best practice: Perplexity synthesis from GeeksforGeeks, Speakeasy, LambdaTest (2025)
