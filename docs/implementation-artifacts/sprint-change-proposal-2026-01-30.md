# Sprint Change Proposal: Data Quality at Ingestion

**Date:** 2026-01-30
**Author:** Bob (Scrum Master Agent)
**Severity:** P0 - Blocks Epic 4 (Forecasting)
**Scope:** MODERATE - Architectural change requiring backlog reorganization

---

## 1. Issue Summary

### Problem Statement

Financial forecasting achieves only ~15% data usability due to raw period/unit/entity storage without classification at ingestion time. The current approach of post-extraction fix scripts has failed to sustainably address the root cause after 20+ iterations.

### Discovery Context

- **Trigger:** Repeated failure to achieve acceptable data quality for EBITDA forecasting
- **Investigation:** Comprehensive codebase analysis + MCP research on ETL best practices
- **Root Cause:** Ingestion pipeline stores data without sufficient metadata for downstream processing

### Evidence

| Metric | Current State | Impact |
|--------|---------------|--------|
| GROUP EBITDA usability | 292 records → 2 usable | 99.3% data loss |
| NULL units | 42.7% of all records | Cannot normalize values |
| Unique unit values | 12,010 | Scale mixing (1000x errors) |
| Period format variants | ~30+ formats | 85% unparseable |
| Fix scripts created | 20+ | Unsustainable maintenance |

---

## 2. Impact Analysis

### 2.1 Epic Impact

| Epic | Status | Change Required |
|------|--------|-----------------|
| **Epic 4** (Forecasting) | BLOCKED | Depends on data quality resolution |
| **NEW Epic 9** | PROPOSED | "Data Quality at Ingestion" |
| Epic 5 (Production) | No change | Depends on Epic 4 |

### 2.2 Story Impact

| Story | Impact |
|-------|--------|
| Story 4.1 (Time-Series Extraction) | Blocked - requires clean data foundation |
| Story 4.2 (Forecasting Engine) | Blocked - depends on Story 4.1 |
| Stories 4.3-4.10 | Cascading delay |

### 2.3 Artifact Conflicts

| Artifact | Conflict | Resolution |
|----------|----------|------------|
| PRD Epic 4 | Assumes extractable time-series data | Add prerequisite dependency |
| Architecture | Missing classification layer | Add LLM classification at ingestion |
| Database Schema | No classification columns | Schema migration required |

### 2.4 Technical Impact

| Component | Files Affected | Change Type |
|-----------|----------------|-------------|
| Database | `migrations/002_*.py` | Migration |
| Ingestion | `raglite/ingestion/adaptive_table/` | Extend |
| Storage | `raglite/ingestion/storage/table_store.py` | Modify |
| Forecasting | `raglite/forecasting/timeseries/sql_extraction_*.py` | Simplify |
| Scripts | `scripts/fix_*.py` | Archive |

---

## 3. Recommended Approach

### Selected Path: Architecture Change - LLM Classification at Ingestion

**Why This Approach:**

1. **Pattern exists:** `llm_inference.py` already does LLM-based unit inference successfully
2. **Research supports:** Industry best practice is "LLM for semantic understanding at extraction time, deterministic logic for validation"
3. **Sustainable:** Eliminates fix script maintenance cycle permanently
4. **Foundation:** Enables reliable forecasting without post-hoc data gymnastics

### Alternatives Considered

| Option | Assessment | Verdict |
|--------|------------|---------|
| Quick fix (more scripts) | Continues unsustainable cycle | NOT VIABLE |
| Rollback | No work to roll back | N/A |
| **Architecture change** | Addresses root cause | **RECOMMENDED** |

### Effort & Risk

| Aspect | Estimate |
|--------|----------|
| Effort | Medium (1-2 weeks) |
| Risk | Low (extends existing patterns) |
| Timeline impact | Delays Epic 4 by 1-2 weeks |
| ROI | High - eliminates recurring fix costs |

---

## 4. Detailed Change Proposals

### Change 1: Database Schema Extension

**File:** `migrations/002_add_classification_columns.py` (NEW)

```sql
-- Add classification columns to financial_tables
ALTER TABLE financial_tables ADD COLUMN period_type VARCHAR(20);
ALTER TABLE financial_tables ADD COLUMN value_type VARCHAR(20) DEFAULT 'actual';
ALTER TABLE financial_tables ADD COLUMN entity_level VARCHAR(20);
ALTER TABLE financial_tables ADD COLUMN period_normalized VARCHAR(20);

-- Add indexes for query performance
CREATE INDEX idx_period_type ON financial_tables(period_type);
CREATE INDEX idx_value_type ON financial_tables(value_type);
CREATE INDEX idx_entity_level ON financial_tables(entity_level);

-- Column definitions:
-- period_type: 'monthly_actual', 'ytd_actual', 'budget', 'ytd_budget', 'unknown'
-- value_type: 'actual', 'budget', 'forecast'
-- entity_level: 'country', 'region', 'group', 'consolidated'
-- period_normalized: Clean period without prefixes (e.g., "Dec-21")
```

**Rationale:** Enable filtering at query time instead of parsing at extraction time.

---

### Change 2: New Classification Module

**File:** `raglite/ingestion/adaptive_table/classification/data_type.py` (NEW)

**Purpose:** Centralize classification logic for periods, value types, and entity levels.

**Key Functions:**

```python
def classify_period_type(period: str, table_context: dict) -> tuple[str, str]:
    """Classify period and return (period_type, normalized_period).

    Classification rules:
    - "B Dec-21" → ("budget", "Dec-21")
    - "YTD Jun-24" → ("ytd_actual", "Jun-24")
    - "Dec-21" → ("monthly_actual", "Dec-21")
    - "YTD B Dec-21" → ("ytd_budget", "Dec-21")

    Uses regex first, LLM for ambiguous cases.
    """

def classify_value_type(
    period: str,
    table_caption: str,
    section_heading: str
) -> str:
    """Classify value type from context clues.

    Returns: 'actual', 'budget', or 'forecast'

    Context clues:
    - "Budget 2026" in caption → 'budget'
    - "Forecast" in heading → 'forecast'
    - "B " prefix in period → 'budget'
    - Default → 'actual'
    """

def classify_entity_level(
    entity: str,
    table_caption: str,
    document_context: dict
) -> str:
    """Classify entity hierarchy level.

    Returns: 'country', 'region', 'group', 'consolidated'

    Known mappings:
    - "Portugal", "Brazil", "Tunisia" → 'country'
    - "Iberia", "Africa" → 'region'
    - "GROUP", "Group" → 'group'
    - "Consolidated" → 'consolidated'

    LLM fallback for unknown entities.
    """
```

**Rationale:** Move `period_classification.py` logic to ingestion layer and extend it.

---

### Change 3: Extend Table Storage

**File:** `raglite/ingestion/storage/table_store.py`

**Section:** `_prepare_table_records()`

**OLD:**
```python
record = (
    document_id,
    row.get("page_number"),
    row.get("table_index"),
    row.get("table_caption"),
    row.get("entity"),
    row.get("metric"),
    row.get("period"),
    row.get("fiscal_year"),
    row.get("value"),
    row.get("unit"),
    row.get("row_index"),
    row.get("column_name"),
    row.get("chunk_text"),
)
```

**NEW:**
```python
record = (
    document_id,
    row.get("page_number"),
    row.get("table_index"),
    row.get("table_caption"),
    row.get("entity"),
    row.get("metric"),
    row.get("period"),
    row.get("fiscal_year"),
    row.get("value"),
    row.get("unit"),
    row.get("row_index"),
    row.get("column_name"),
    row.get("chunk_text"),
    row.get("period_type"),        # NEW
    row.get("value_type"),         # NEW
    row.get("entity_level"),       # NEW
    row.get("period_normalized"),  # NEW
)
```

**Rationale:** Store classification results at ingestion time.

---

### Change 4: Integrate Classification into Extraction

**File:** `raglite/ingestion/adaptive_table/core/processing.py`

**Section:** Row processing loop

**OLD:**
```python
# Period stored as-is without classification
row["period"] = period_str
row["entity"] = entity_str
```

**NEW:**
```python
from ..classification.data_type import (
    classify_period_type,
    classify_value_type,
    classify_entity_level
)

# Classify at extraction time
period_type, period_normalized = classify_period_type(
    period_str,
    {"caption": table_caption, "heading": section_heading}
)
value_type = classify_value_type(period_str, table_caption, section_heading)
entity_level = classify_entity_level(entity_str, table_caption, document_context)

# Store both original and classified values
row["period"] = period_str  # Keep original for debugging
row["period_type"] = period_type
row["period_normalized"] = period_normalized
row["value_type"] = value_type
row["entity_level"] = entity_level
```

**Rationale:** Classification happens once at ingestion, not repeatedly at extraction.

---

### Change 5: Simplify Forecasting Extraction

**File:** `raglite/forecasting/timeseries/sql_extraction_query.py`

**OLD:**
```sql
SELECT period, fiscal_year, SUM(value) as total_value, COUNT(*) as row_count,
       MAX(document_id) as source_doc, bool_or(is_ytd) as is_ytd, unit
FROM financial_tables
WHERE metric ILIKE %s
  AND value IS NOT NULL
GROUP BY period, fiscal_year, unit
ORDER BY fiscal_year, period
-- Post-extraction: Parse period format, filter budget data, handle YTD conversion, etc.
```

**NEW:**
```sql
SELECT period_normalized as period, fiscal_year, SUM(value) as total_value,
       COUNT(*) as row_count, MAX(document_id) as source_doc,
       (period_type = 'ytd_actual') as is_ytd, unit
FROM financial_tables
WHERE metric ILIKE %s
  AND value IS NOT NULL
  AND period_type IN ('monthly_actual', 'ytd_actual')  -- Filter at query time!
  AND value_type = 'actual'                             -- No budget mixing!
  AND entity_level = %s                                 -- Proper entity filtering!
GROUP BY period_normalized, fiscal_year, period_type, unit
ORDER BY fiscal_year, period_normalized
```

**Rationale:** Database does the filtering; extraction code becomes trivial.

---

### Change 6: Deprecate Fix Scripts

**Action:** Move to `scripts/archive/deprecated-data-quality/`

| Script | Replacement |
|--------|-------------|
| `scripts/fix_ebitda_scale.py` | Unit normalization at ingestion |
| `scripts/fix_ebitda_scale_v2.py` | Unit normalization at ingestion |
| `scripts/fix_unit_standardization.py` | Unit normalization at ingestion |
| `scripts/fix_unit_magnitude_inference.py` | LLM inference at ingestion |
| `scripts/fix_unit_context_inference.py` | LLM inference at ingestion |
| `scripts/fix_structural_cleanup.py` | Entity classification at ingestion |
| `scripts/fix_ratio_decomposition.py` | Proper metric typing |
| `scripts/fix_currency_cleanup.py` | Unit standardization |
| `scripts/fix_forecasting_variables.py` | Proper classification eliminates need |

**Rationale:** Fix scripts address symptoms; classification addresses cause.

---

## 5. Implementation Handoff

### Scope Classification: MODERATE

Requires backlog reorganization and PO/SM coordination, but not fundamental replan.

### Handoff Recipients

| Role | Responsibility |
|------|----------------|
| **Development Team** | Implement classification module, schema migration, integration |
| **SM (Bob)** | Create Epic 9 stories, update sprint backlog, track dependencies |
| **Architect** | Review classification prompt design, approve schema changes |
| **PO** | Prioritize Epic 9 relative to Epic 4 timeline |

### Proposed Epic 9 Stories

| Story | Description | Estimate |
|-------|-------------|----------|
| 9.1 | Schema migration - add classification columns | 0.5 days |
| 9.2 | Classification module - period_type classification | 1 day |
| 9.3 | Classification module - value_type classification | 0.5 days |
| 9.4 | Classification module - entity_level classification | 0.5 days |
| 9.5 | Integration - connect classification to extraction | 1 day |
| 9.6 | Storage extension - store classification fields | 0.5 days |
| 9.7 | Re-ingestion - process existing PDFs with new pipeline | 1 day |
| 9.8 | Forecasting query simplification | 1 day |
| 9.9 | Validation - verify data quality improvement | 0.5 days |
| **Total** | | **6.5 days** |

### Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Schema migration | Successful | All new columns exist |
| Classification accuracy | >95% | Manual review of 100 sample records |
| Data usability | >90% | Forecasting extraction uses 90%+ of records |
| Unit NULL rate | <10% | Down from 42.7% |
| Period parseability | >95% | Down from ~15% |
| Fix script dependencies | 0 | No fix scripts needed post-ingestion |

### Dependencies

```
Epic 9 (Data Quality at Ingestion)
    └── Story 9.1 (Schema)
    └── Stories 9.2-9.4 (Classification modules) [parallel]
    └── Story 9.5 (Integration) [depends on 9.2-9.4]
    └── Story 9.6 (Storage) [depends on 9.1, 9.5]
    └── Story 9.7 (Re-ingestion) [depends on 9.6]
    └── Story 9.8 (Forecasting) [depends on 9.7]
    └── Story 9.9 (Validation) [depends on 9.8]
        └── Epic 4 (Forecasting) UNBLOCKED
```

---

## 6. Approval

### Requested Actions

- [ ] **PO Approval:** Confirm Epic 9 priority and timeline impact
- [ ] **Architect Approval:** Confirm schema design and classification approach
- [ ] **Team Acknowledgment:** Understand scope and dependencies

### Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Owner | | | |
| Architect | | | |
| Tech Lead | | | |
| Scrum Master | Bob (SM Agent) | 2026-01-30 | Prepared |

---

## Appendix A: Research References

### Industry Best Practices

> "Use LLMs for semantic understanding at extraction time, and deterministic logic for validation and structure."
> — Perplexity Research on ETL Pipeline Design, 2026

### Key Research Sources

1. **Perplexity Ask:** "Best practices for extracting structured tabular data from financial PDFs"
2. **Exa Web Search:** "LLM-based financial document extraction unit disambiguation"
3. **Medium/Substack:** Multiple articles on LLM integration in ETL pipelines

### Recommended Pattern

```
PDF → Layout-Aware Extraction → LLM Classification → Validation → Normalized Storage
         (Docling)              (Mistral/Claude)      (Rules)      (PostgreSQL)
```

---

## Appendix B: Current vs Target Architecture

### Current Flow (Problematic)

```
PDF
 ↓
Docling Extraction
 ↓
Raw Storage (period="B Dec-21", unit=NULL, entity="Portugal")
 ↓
Fix Scripts (20+ iterations)
 ↓
Forecasting Extraction (85% data loss)
 ↓
Poor Forecasts
```

### Target Flow (Proposed)

```
PDF
 ↓
Docling Extraction
 ↓
LLM Classification Layer  ← NEW
 ↓
Classified Storage (period_type="budget", period_normalized="Dec-21",
                    value_type="budget", entity_level="country", unit="M EUR")
 ↓
Simple SQL Queries with WHERE clauses
 ↓
Forecasting Extraction (>90% data usability)
 ↓
Accurate Forecasts
```

---

**Document Generated:** 2026-01-30 by Correct Course Workflow
**Next Review:** After PO/Architect approval
