# Epic 9: Data Quality at Ingestion - Development Tracking

**Status:** In Progress
**Branch:** `feature/epic-9-data-quality-at-ingestion`
**Started:** 2026-01-31
**Target Completion:** 2026-02-11 (6.5 dev days)

---

## Overview

Epic 9 implements a robust classification system at the ingestion layer to eliminate data quality issues that are blocking forecasting (Epic 4). By classifying data semantically during ingestion, we avoid downstream ambiguity and enable simpler, more reliable forecasting queries.

**Sprint Change Proposal:** `docs/implementation-artifacts/sprint-change-proposal-2026-01-30.md`

---

## Foundation

Commit `58fbc9e` ("feat(forecasting): period classification and data quality foundation for Epic 9") merged to main provides:
- `PeriodType` enum with 13 period types
- Portuguese month abbreviation support (Jan-24 -> January 2024)
- 4-digit year format support (2024 -> Year 2024)
- Classification report generation with usability metrics

---

## Story Progress

| ID | Story | Status | Estimate | Completed |
|----|-------|--------|----------|-----------|
| 9.1 | Schema migration - add classification columns | Not Started | 0.5 days | - |
| 9.2 | Classification module - period_type classification | Not Started | 1 day | - |
| 9.3 | Classification module - value_type classification | Not Started | 0.5 days | - |
| 9.4 | Classification module - entity_level classification | Not Started | 0.5 days | - |
| 9.5 | Integration - connect classification to extraction | Not Started | 1 day | - |
| 9.6 | Storage extension - store classification fields | Not Started | 0.5 days | - |
| 9.7 | Re-ingestion - process existing PDFs with new pipeline | Not Started | 1 day | - |
| 9.8 | Forecasting query simplification | Not Started | 1 day | - |
| 9.9 | Validation - verify data quality improvement | Not Started | 0.5 days | - |

**Total:** 6.5 days

---

## Success Criteria

### AC1: Classification Accuracy
- [ ] Period type classification: 95%+ accuracy (20+ PDFs)
- [ ] Value type classification: 90%+ accuracy
- [ ] Entity level classification: 90%+ accuracy

### AC2: Forecasting Query Simplification
- [ ] Period normalization logic removed from forecasting module
- [ ] Direct queries by `period_type`: `WHERE period_type = 'monthly'`
- [ ] 50+ LOC reduction in forecasting module

### AC3: Data Usability
- [ ] 100% of ingested data has all classification fields (no NULLs)
- [ ] Classification reports generated for every ingestion
- [ ] Ground truth dataset: 50+ classified examples

### AC4: System Impact
- [ ] Ingestion time increase: <20%
- [ ] No breaking changes to MCP tools
- [ ] All existing tests pass

---

## Architecture

### New Modules

```
raglite/ingestion/classification/
├── __init__.py
├── models.py                    # Classification dataclasses
├── period_classifier.py         # Period type classification (merged)
├── value_type_classifier.py     # Story 9.3
└── entity_level_classifier.py   # Story 9.4
```

### Database Schema

```sql
-- Story 9.1
ALTER TABLE financial_tables ADD COLUMN period_type VARCHAR(50);
ALTER TABLE financial_tables ADD COLUMN value_type VARCHAR(50);
ALTER TABLE financial_tables ADD COLUMN entity_level VARCHAR(100);
```

### Integration Points

- `DoclingTableExtractor` - Hook classification after extraction (Story 9.5)
- `PostgreSQLTableStorage` - Store classification fields (Story 9.6)
- `FinancialForecastingService` - Simplified queries (Story 9.8)

---

## Development Notes

### Current Blockers
- None

### Design Decisions
- Classification runs synchronously after extraction (acceptable <20% overhead)
- Columns nullable during development for safety
- Re-ingestion as separate story to validate on existing data

### Risk Mitigation
- Keep existing forecasting logic until validation passes
- Nullable columns allow gradual migration
- Ground truth dataset ensures quality before production deployment

---

## Testing Strategy

1. **Unit tests:** 95%+ coverage on classification modules
2. **Integration tests:** End-to-end classification pipeline
3. **Ground truth validation:** 50+ manually classified examples
4. **Classification reports:** Generated for every test ingestion
5. **Regression tests:** Forecasting after simplification

---

## Next Steps

1. Story 9.1: Schema migration (add classification columns)
2. Story 9.2: Period type classification module
3. Story 9.3: Value type classification module

---

## References

- Sprint Change Proposal: `docs/implementation-artifacts/sprint-change-proposal-2026-01-30.md`
- Foundation Commit: `58fbc9e` (merged to main)
- Related Epic: Epic 4 (Financial Forecasting) - blocked until Epic 9 complete
