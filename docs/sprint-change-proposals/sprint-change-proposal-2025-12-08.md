# Sprint Change Proposal: SCP-2025-12-08-001

**Date:** 2025-12-08
**Status:** APPROVED
**Scope:** Minor (Development Team Implementation)
**Approver:** Ricardo

---

## Issue Summary

### Triggering Story
**Story ID:** 6.9 - External Data Source Client Fixes
**Discovery:** Post-implementation analysis of Story 6.1 clients + MCP-assisted API research

### Problem Statement

6 out of 8 external data source clients implemented in Story 6.1 have significant issues preventing them from fetching data correctly:

| Client | Root Cause | Severity | Fix Effort |
|--------|-----------|----------|------------|
| **INE** | Date filtering excludes monthly data due to mid-month comparison | Low | 30 min |
| **Commodities/CO2** | API domain deprecated (`ember-climate.org` → `ember-energy.org`) | Critical | 30 min |
| **OMIE** | URL pattern completely wrong + CSV format changed | Critical | 2-3 hours |
| **BPstat** | Wrong series IDs (returns FX rates not mortgage data!) + API endpoint changed | Critical | 4-6 hours |
| **EU Oil Bulletin** | XML endpoint deprecated, now XLSX only | Critical | 4-6 hours |
| **BaseGov** | Assumed JSON API doesn't exist (HTML-only portal) | Critical | 6-8 hours |

**Only 2 clients functional:** IPMA (Weather), ATIC (Cement/CSV)

### Evidence

- INE API returns 200 OK but 0 records due to date filtering bug
- Ember API returns: *"Domain deprecated as of 2025-01-01"*
- OMIE URLs return 404 (wrong path structure)
- BPstat series 12532089 returns "Egyptian Pound exchange rate" not mortgage data
- EU Oil Bulletin XML endpoint redirects to homepage (302)
- BaseGov `/pesquisa/resultados` returns 404 (no JSON API exists)

---

## Impact Analysis

### Epic Impact
- **Epic 6:** Remains in-progress; Story 6.9 added as bugfix story
- **Story 6.1:** Status note added acknowledging partial completion
- **Story 6.7:** Accuracy validation (9.0% MAPE) may improve with full data
- **Epic 5:** No impact - blocked status unchanged

### Artifact Conflicts
| Artifact | Impact | Action |
|----------|--------|--------|
| PRD Epic 6 | Story 6.1 AC claims all clients work | Note partial completion |
| Architecture | Generic client specs | Update with specific patterns |
| Code files | 6 clients need fixes | Story 6.9 implementation |
| pyproject.toml | Missing openpyxl | Add dependency |

### MVP Impact
**None.** Story 6.9 delivers the original Epic 6 intent.

---

## Recommended Approach

### Selected Path: Direct Adjustment

Add Story 6.9 as new bugfix story within Epic 6.

**Rationale:**
1. Research already done - Story 6.9 contains verified fix instructions
2. Fixes are well-scoped (URL changes, parser updates, new dependencies)
3. Phased implementation allows quick wins (P0 in 1 hour)
4. No architectural changes required
5. Maintains Epic 6 business value (multi-variate forecasting with full data)

### Alternatives Considered

| Option | Verdict | Reason |
|--------|---------|--------|
| Rollback Story 6.1 | Rejected | Unnecessary - loses working clients |
| Reduce MVP scope | Rejected | Undermines Epic 6 business value |

---

## Detailed Change Proposals

### Sprint Status Update

```yaml
# ADD to development_status:
6-9-external-data-source-fixes: in-progress
```

### Implementation Phases

**Phase 1 - Quick Wins (1 hour) - P0:**
1. **INE:** Change date comparison to first-of-month (`start_date.replace(day=1)`)
2. **Commodities/CO2:** Update domain to `api.ember-energy.org`

**Phase 2 - Medium Effort (2-3 hours) - P0:**
3. **OMIE:**
   - New URL: `https://www.omie.es/es/file-download?parents=marginalpdbc&filename=...`
   - Enable `follow_redirects=True`
   - Update CSV parser for `MARGINALPDBC;YEAR;MONTH;DAY;HOUR;PT;ES` format

**Phase 3 - Complex Fixes (15-20 hours) - P1/P2:**
4. **BPstat:**
   - Correct series ID: `12710733` (median mortgage rate)
   - New endpoint: `https://bpstat.bportugal.pt/api/observations/`
5. **EU Oil Bulletin:**
   - Switch to XLSX parsing with openpyxl
   - URL: `https://energy.ec.europa.eu/document/download/906e60ca-8b6a-44e7-8589-652854d2fd3f_en`
6. **BaseGov:**
   - Implement dados.gov.pt OCDS dataset integration
   - Dataset: `https://dados.gov.pt/pt/datasets/ocds-portal-base-www-base-gov-pt/`

### New Dependencies

```toml
# pyproject.toml
[project.dependencies]
openpyxl = ">=3.1.0"  # EU Oil Bulletin XLSX parsing
```

---

## Implementation Handoff

### Change Scope: MINOR

Targeted bugfix story - direct development team implementation.

### Responsibilities

| Role | Responsibility |
|------|----------------|
| **Dev** | Execute Story 6.9 per detailed instructions in story file |
| **SM** | Update sprint-status.yaml, monitor progress |
| **QA** | Verify all 8 clients return data after fixes |

### Success Criteria

- [ ] All 8 external data source clients can fetch data
- [ ] Unit tests pass for each client
- [ ] Integration test confirms real data retrieval
- [ ] No regressions in Story 6.7 forecasting accuracy (9.0% MAPE)
- [ ] New dependencies documented in pyproject.toml

### Timeline

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1 | 1 hour | P0 |
| Phase 2 | 2-3 hours | P0 |
| Phase 3 | 15-20 hours | P1/P2 |

**Total:** 17-24 hours (~2-3 days)

---

## Approval Record

| Field | Value |
|-------|-------|
| Proposal ID | SCP-2025-12-08-001 |
| Created | 2025-12-08 |
| Status | APPROVED |
| Approved By | Ricardo |
| Approval Date | 2025-12-08 |

---

## References

- Story File: `docs/stories/6.9-external-data-source-fixes.md`
- Epic 6 PRD: `docs/prd/epic-6-advanced-forecasting-external-data.md`
- Architecture: `docs/architecture/6-external-data-pipeline-epic-6.md`
- Sprint Status: `docs/sprint-artifacts/sprint-status.yaml`
