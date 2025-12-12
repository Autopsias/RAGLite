# Sprint Change Proposal: Epic 6 Forecasting Accuracy Extension

**SCP ID:** SCP-2025-12-12-001
**Date:** 2025-12-12
**Status:** APPROVED
**Requestor:** Ricardo (via SM workflow)
**Epic:** 6 - Advanced Forecasting with External Data

---

## Section 1: Issue Summary

### Problem Statement

Variable Cost MAPE is at **41.43%** (target <8%), with only **5/8 variables** passing their accuracy targets. This indicates Epic 6 success criteria #6 ("Forecast accuracy validation: ±10% or better") has not been fully met.

### When/How Discovered

- Discovered during validation runs on 2025-12-12
- Evidence: `scripts/validate-cement-forecasting-12vars.py` output
- Root cause analysis documented in `docs/briefings/unified-forecasting-improvement-epic.md`

### Root Cause Analysis (Five Whys)

| Level | Question | Finding |
|-------|----------|---------|
| Why 1 | Why is Variable Cost MAPE at 41%? | Data from multiple entities mixed (Portugal + Tunisia + Brazil) |
| Why 2 | Why are entities mixed? | No entity detection in extraction logic |
| Why 3 | Why no entity detection? | Original design assumed single-entity data |
| Why 4 | Why wrong regressors? | Using generic macro indicators instead of cost drivers |
| Why 5 | Why no construction indicators? | INE Building Permits API broken (wrong indicator ID) |

### Evidence

| Variable | Current MAPE | Target | Status |
|----------|-------------|--------|--------|
| Revenue | 2.51% | <5% | PASS |
| EBITDA | 1.18% | <5% | PASS |
| Sales Volume | 4.18% | <5% | PASS |
| **Variable Cost** | **41.43%** | <8% | **FAIL** |
| Avg Selling Price | N/A | <6% | SKIP (extraction failed) |
| Capacity Utilization | N/A | <10% | SKIP (extraction failed) |
| TTF Gas Price | 5.27% | <12% | PASS |
| Diesel Price | 0.12% | <10% | PASS |

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Description |
|------|--------|-------------|
| **Epic 6** | MAJOR | Reopen epic, add 9 new stories (6.15-6.23) |
| Epic 5 | MINOR | Cloud deployment blocked until Epic 6 complete |
| Epic 7 | NONE | Technical debt work independent |

### Story Impact

**Current Stories (Completed):**
- Stories 6.1-6.14: No changes required, already done

**New Stories (To Add):**

| Story | Name | Effort | Priority | Dependencies |
|-------|------|--------|----------|--------------|
| 6.15 | Entity-Specific Variable Cost Extraction | 4h | P0 | None |
| 6.16 | Add Eurostat Construction & Industrial Indicators | 8h | P1 | None |
| 6.17 | Add ECB Macroeconomic Indicators | 4h | P1 | None |
| 6.18 | Fix INE Building Permits API | 4h | P1 | None |
| 6.19 | Add EC Construction Confidence Index | 6h | P2 | None |
| 6.20 | Update Regressor Configuration for Cement Industry | 4h | P1 | 6.16-6.19 |
| 6.21 | Unified Validation Script | 8h | P1 | 6.15, 6.20 |
| 6.22 | MCP Validation Tool Integration | 6h | P2 | 6.21 |
| 6.23 | Variable Cost MAPE Final Validation | 4h | P0 | All above |

**Total Effort:** 52 hours

### Artifact Conflicts

| Artifact | Update Required | Scope |
|----------|-----------------|-------|
| `docs/prd/epic-6-advanced-forecasting-external-data.md` | YES | Add stories 6.15-6.23, update success criteria |
| `docs/sprint-artifacts/sprint-status.yaml` | YES | Reopen Epic 6, add new story entries |
| `docs/architecture/6-external-data-pipeline-epic-6.md` | YES | Add new data sources, entity detection |
| Story files | CREATE | 9 new story files in `docs/stories/` |

### Technical Impact

**Files to Modify:**

| File | Changes |
|------|---------|
| `raglite/forecasting/timeseries_extract.py` | Add entity detection for Portugal |
| `raglite/forecasting/regressor_config.py` | Add new regressors, update mappings |
| `raglite/forecasting/regressor_fetch.py` | Add fetch logic for new regressors |
| `raglite/external_data/clients/eurostat.py` | Add construction_output, industrial_production |
| `raglite/external_data/clients/ecb.py` | Add gdp_growth, inflation |
| `raglite/external_data/clients/ine.py` | Fix building permits indicator ID |
| `raglite/main.py` | Add new MCP tools |

**Files to Create:**

| File | Purpose |
|------|---------|
| `raglite/external_data/clients/ec_surveys.py` | EC Business Surveys client |
| `scripts/validate-forecasting-unified.py` | Unified validation script |
| `tests/integration/test_new_regressors.py` | Integration tests for new indicators |
| `tests/integration/test_variable_cost_extraction.py` | Entity-specific extraction tests |

---

## Section 3: Recommended Approach

### Chosen Path: Direct Adjustment

**Extend Epic 6** with 9 new stories (6.15-6.23) focused on:

1. **Data Quality** (Phase 1): Entity-specific extraction for Portugal
2. **External Regressors** (Phase 2): Add 6 new Eurostat/ECB/EC indicators
3. **Unified Validation** (Phase 3): Single script, all MAPE methods
4. **MCP Integration** (Phase 4): Expose validation tools via MCP

### Rationale

- Epic 6 success criteria not fully met (Variable Cost MAPE at 41%)
- Logical extension of existing forecasting work
- Reuses existing infrastructure (API clients, regressor framework)
- Avoids creating new epic for closely related work

### Effort Estimate

| Phase | Stories | Effort | Parallelizable |
|-------|---------|--------|----------------|
| Phase 1 | 6.15 | 4h | Yes (Track B) |
| Phase 2 | 6.16-6.19 | 22h | Yes (Track A) |
| Merge | 6.20 | 4h | No |
| Phase 3 | 6.21 | 8h | No |
| Phase 4 | 6.22-6.23 | 10h | Partial |
| **Total** | 9 stories | **52h** | ~40h parallelizable |

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Eurostat API rate limiting | Medium | Medium | Implement caching, batch requests |
| Entity detection errors | Medium | High | Conservative filtering, manual review fallback |
| Low correlation with targets | Medium | Medium | A/B test regressors, keep fallback |
| Data gaps in historical series | Medium | Low | Interpolation, exclude if >10% missing |
| INE indicator still wrong | Low | High | Validate against web interface first |

### Timeline Impact

- **Epic 6 completion:** Delayed by ~1-2 weeks
- **Epic 5 start:** Blocked until Epic 6 complete
- **Critical path:** 6.15 → 6.20 → 6.21 → 6.23

---

## Section 4: Detailed Change Proposals

### 4.1 Sprint Status Update

**File:** `docs/sprint-artifacts/sprint-status.yaml`

**OLD:**
```yaml
epic-6: done
```

**NEW:**
```yaml
epic-6: in-progress  # Reopened for accuracy improvements

# NEW STORIES - Forecasting Accuracy & Data Quality (SCP-2025-12-12-001)
# Goal: Variable Cost MAPE from 41% to <8%, 10/12 variables passing
# Total Effort: 52 hours
6-15-entity-specific-variable-cost-extraction: backlog
6-16-eurostat-construction-industrial-indicators: backlog
6-17-ecb-macroeconomic-indicators: backlog
6-18-fix-ine-building-permits-api: backlog
6-19-ec-construction-confidence-index: backlog
6-20-regressor-config-cement-industry: backlog
6-21-unified-validation-script: backlog
6-22-mcp-validation-tool-integration: backlog
6-23-variable-cost-mape-final-validation: backlog
```

**Rationale:** Epic 6 success criteria #6 not met; adding stories to address accuracy gap.

---

### 4.2 Epic 6 PRD Update

**File:** `docs/prd/epic-6-advanced-forecasting-external-data.md`

**Section: Epic Success Criteria**

**OLD:**
```markdown
## Epic Success Criteria

1. ✅ Tier 1 data sources integrated
...
6. ✅ Forecast accuracy validation: ±10% or better
```

**NEW:**
```markdown
## Epic Success Criteria (Updated 2025-12-12)

1. ✅ Tier 1 data sources integrated (11 datasets)
2. ✅ Multi-variate Prophet forecasting operational
3. ✅ Model ensemble framework (5 models + adaptive weights)
4. ✅ Automated data refresh scheduler operational
5. ✅ PostgreSQL external data storage schema
6. ⚠️ Forecast accuracy validation: **Variable Cost MAPE <8%** (currently 41%)
7. ⚠️ **10/12 variables meeting MAPE targets** (currently 5/8)
8. ✅ MCP tools for external data queries and multi-model forecasting
9. 🆕 Entity-specific data extraction for Portugal
10. 🆕 Cement-industry-specific regressors (construction, industrial)
11. 🆕 Unified validation with all MAPE methods
12. 🆕 MCP validation tools for accuracy monitoring
```

**Rationale:** Reflect true status and add new success criteria for accuracy improvements.

---

### 4.3 New Story Definitions (Summary)

Full story definitions to be added to Epic 6 PRD. See briefing document for complete acceptance criteria:
`docs/briefings/unified-forecasting-improvement-epic.md`

---

## Section 5: Implementation Handoff

### Change Scope Classification: **MODERATE**

Requires backlog reorganization and SM coordination.

### Handoff Recipients

| Role | Responsibility |
|------|----------------|
| **Scrum Master** | Update sprint-status.yaml, create story files |
| **Dev Team** | Implement stories 6.15-6.23 |
| **PM** | Approve scope extension (implicit via SCP approval) |

### Success Criteria

| Metric | Current | Target | Validation |
|--------|---------|--------|------------|
| Variable Cost MAPE | 41.43% | <8% | Holdout validation |
| Variables passing | 5/8 | 10/12 | Unified validation script |
| Data coefficient of variation | 33% | <15% | Standard deviation analysis |
| External regressors | 5 | 11 | regressor_config.py count |
| MCP forecasting tools | 1 | 4 | main.py tool count |

### Next Steps

1. ✅ Sprint Change Proposal approved
2. ⏳ Update sprint-status.yaml
3. ⏳ Update Epic 6 PRD
4. ⏳ Update architecture document
5. ⏳ Create story files (6.15-6.23)
6. ⏳ Begin implementation with 6.15 (P0)

---

## Appendix: References

- **Briefing Document:** `docs/briefings/unified-forecasting-improvement-epic.md`
- **Epic 6 PRD:** `docs/prd/epic-6-advanced-forecasting-external-data.md`
- **Sprint Status:** `docs/sprint-artifacts/sprint-status.yaml`
- **Architecture:** `docs/architecture/6-external-data-pipeline-epic-6.md`
- **Validation Script:** `scripts/validate-cement-forecasting-12vars.py`

---

**Approval:**
- [x] Ricardo (Requestor) - 2025-12-12
- [x] SM Agent (Facilitator) - 2025-12-12
