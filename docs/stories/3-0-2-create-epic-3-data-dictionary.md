# Story 3.0.2: Create Epic 3 Data Dictionary

**Status:** drafted
**Epic:** Epic 3 - AI Intelligence & Orchestration (Prep Sprint)
**Priority:** 🔴 CRITICAL (Prevents ground truth misalignment)
**Effort:** 1 day
**Owner:** Murat (Test Architect)

## Story

As a **test architect preparing for Epic 3**,
I want **a data dictionary documenting available analytical query data**,
so that **ground truth tests align with actual database content and we avoid Epic 2's 12% → 77.6% issue**.

## Context

**From Epic 2 Retrospective (2025-11-05):**

Ricardo (Project Lead): "We should have checked ground truth adequacy to reality much, much earlier."

**Root Cause (Epic 2):**
- Ground truth created from requirements, not database inspection
- Queries asked for data that doesn't exist ("Q3 2025" vs "Aug-25 YTD")
- Test misalignment caused 12% accuracy (66pp below implementation's actual 77.6%)

**Impact on Epic 3:**
- Epic 3 analytical queries require different data than Epic 2 retrieval queries
- Agentic workflows need validated data for multi-step reasoning
- Data dictionary prevents repeating Epic 2's ground truth disaster

**Strategic Decision:**
- Data-first approach: Inspect database BEFORE creating test queries
- Document available metrics, periods, entities, limitations
- All future test queries verified against dictionary

## Acceptance Criteria

### AC1: Database Inspection (4 hours)

**Goal:** Query database and catalog all available data for analytical queries

**Technical Approach:**

```python
# Script: scripts/inspect-database-for-epic-3.py (~150 lines)

import asyncio
import json
from raglite.shared.clients import get_db_client

async def inspect_database():
    """Inspect PostgreSQL financial_tables and catalog available data."""

    db = get_db_client()

    # Query all unique metrics
    metrics_query = "SELECT DISTINCT metric FROM financial_tables ORDER BY metric;"
    metrics = await db.execute(metrics_query)

    # Query all unique periods
    periods_query = "SELECT DISTINCT period FROM financial_tables ORDER BY period;"
    periods = await db.execute(periods_query)

    # Query all unique entities
    entities_query = "SELECT DISTINCT entity FROM financial_tables ORDER BY entity;"
    entities = await db.execute(entities_query)

    # Query all unique currencies
    currencies_query = "SELECT DISTINCT currency FROM financial_tables ORDER BY currency;"
    currencies = await db.execute(currencies_query)

    # Build comprehensive data catalog
    catalog = {
        "metrics": [row["metric"] for row in metrics],
        "periods": [row["period"] for row in periods],
        "entities": [row["entity"] for row in entities],
        "currencies": [row["currency"] for row in currencies],
        "total_rows": await db.execute("SELECT COUNT(*) FROM financial_tables;"),
    }

    # Save JSON for programmatic access
    with open("docs/data-dictionary-epic-3.json", "w") as f:
        json.dump(catalog, f, indent=2)

    return catalog
```

**Success Criteria:**
- ✅ All unique metrics cataloged (EBITDA, Variable Cost, Revenue, etc.)
- ✅ All unique periods cataloged (Aug-25, Sep-25, YTD variants, etc.)
- ✅ All unique entities cataloged (Portugal, Tunisia, Angola, Brazil, Group, etc.)
- ✅ Currency limitations documented (EUR only)
- ✅ JSON catalog saved: `docs/data-dictionary-epic-3.json`

**Files Created:**
- `scripts/inspect-database-for-epic-3.py` (~150 lines)
- `docs/data-dictionary-epic-3.json` (JSON catalog)

### AC2: Create Data Dictionary Document (2 hours)

**Goal:** Human-readable markdown documentation of available data

**Technical Approach:**

Create comprehensive data dictionary: `docs/data-dictionary-epic-3.md`

```markdown
# Data Dictionary - Epic 3 Analytical Queries

**Generated:** 2025-11-05
**Source:** PostgreSQL financial_tables (170,142 rows)
**Purpose:** Validate test queries align with actual database content

---

## Available Metrics

| Metric | Description | Sample Value | Unit |
|--------|-------------|--------------|------|
| EBITDA | Earnings before interest, taxes, depreciation, amortization | 191.8 | million EUR |
| Variable Cost | Variable production costs | -23.4 | EUR/ton |
| Revenue | Total revenue | 379.2 | million EUR |
| Fixed Cost | Fixed operating costs | 145.6 | million EUR |
| [... complete list with examples] |

**Total Metrics:** {{count}}

---

## Available Periods

| Period Format | Example | Description |
|---------------|---------|-------------|
| Month-Year | Aug-25 | Single month actual |
| Month-YTD | Aug-25 YTD | Year-to-date through month |
| Quarter | Q3-25 | Quarter period (if available) |

**Period Mappings (from Story 2.15):**
- Q3 2025 → [Jul-25, Aug-25, Sep-25, Aug-25 YTD]
- Q2 2025 → [Apr-25, May-25, Jun-25, Jun-25 YTD]
- Q1 2025 → [Jan-25, Feb-25, Mar-25, Mar-25 YTD]

**Available Periods:** {{list all unique periods}}

---

## Available Entities

| Entity | Full Name | Country | Type |
|--------|-----------|---------|------|
| Portugal Cement | Portugal Cement Operations | Portugal | Cement |
| Tunisia Cement | Tunisia Cement Operations | Tunisia | Cement |
| Secil Angola | Angola Operations | Angola | Cement |
| [... complete list] |

**Entity Aliases (from Story 2.14 AC1):**
- "Group" → "Currency (1000 EUR)" (fuzzy match)
- "Angola" → "Secil Angola"
- "Brazil" → "Adrianopolis" OR "Pomerode"

**Total Entities:** {{count}}

---

## Available Currencies

- **EUR (Euro)** - PRIMARY CURRENCY (all data)
- ❌ AOA (Angolan Kwanza) - NOT AVAILABLE
- ❌ BRL (Brazilian Real) - NOT AVAILABLE
- ❌ TND (Tunisian Dinar) - NOT AVAILABLE

**Limitation:** Currency conversion NOT supported (Story 2.14 AC5)

---

## Data Limitations

### Missing Metrics
- ❌ Headcount / FTE data (not extracted from PDF)
- ❌ G&A expenses (not in tables)
- ❌ Growth rate baselines (requires time series)

### Missing Period Variants
- ❌ Budget periods (B Aug-25) - not separately stored
- ❌ Forecast periods - not available

### Missing Entities
- [List any entities mentioned in PRD but not in database]

---

## Test Query Validation Rules

**BEFORE creating ANY test query:**

1. **Metric Check:** Is metric in "Available Metrics" table?
   - YES → Proceed
   - NO → Remove query OR use available metric

2. **Period Check:** Is period in "Available Periods" OR mappable via Story 2.15?
   - YES → Proceed
   - NO → Remove query OR use available period

3. **Entity Check:** Is entity in "Available Entities" OR fuzzy-matchable?
   - YES → Proceed
   - NO → Remove query OR use available entity

4. **Currency Check:** Does query request EUR?
   - YES → Proceed
   - NO → Convert to EUR request OR remove query

**Enforcement:** All Epic 3 test queries MUST pass these checks BEFORE validation execution.

---

## References

- [Source: PostgreSQL financial_tables schema](raglite/shared/models.py)
- [Source: Story 2.15 Period Normalization](raglite/retrieval/period_normalizer.py)
- [Source: Story 2.14 Fuzzy Entity Matching](raglite/retrieval/query_classifier.py)
```

**Success Criteria:**
- ✅ Data dictionary created: `docs/data-dictionary-epic-3.md`
- ✅ All sections complete (metrics, periods, entities, currencies, limitations)
- ✅ Test query validation rules documented
- ✅ Examples and counts included

**Files Created:**
- `docs/data-dictionary-epic-3.md` (human-readable dictionary)

### AC3: Winston Architecture Review (30 minutes)

**Goal:** Verify data dictionary completeness and Epic 3 readiness

**Technical Approach:**

Winston reviews:
1. Completeness (all metrics, periods, entities documented)
2. Limitations explicitly stated (no hidden assumptions)
3. Test query validation rules clear
4. Epic 3 stories can use dictionary as ground truth source

**Success Criteria:**
- ✅ Winston architecture approval documented
- ✅ Data dictionary approved for Epic 3 test creation
- ✅ Epic 3 test queries blocked until dictionary validated

## Tasks / Subtasks

### Task 1: Database Inspection (AC1) - 4 hours

- [ ] **Subtask 1.1:** Create inspection script
  - File: `scripts/inspect-database-for-epic-3.py`
  - Query all unique metrics, periods, entities, currencies

- [ ] **Subtask 1.2:** Execute inspection
  - Run script against PostgreSQL financial_tables
  - Verify 170,142 rows accessible

- [ ] **Subtask 1.3:** Generate JSON catalog
  - Save to: `docs/data-dictionary-epic-3.json`
  - Include: metrics, periods, entities, currencies, row count

### Task 2: Create Data Dictionary (AC2) - 2 hours

- [ ] **Subtask 2.1:** Write markdown documentation
  - File: `docs/data-dictionary-epic-3.md`
  - Structure: Metrics, Periods, Entities, Currencies, Limitations

- [ ] **Subtask 2.2:** Add examples and counts
  - Sample values for each metric
  - Complete list of all periods, entities

- [ ] **Subtask 2.3:** Document validation rules
  - Test query validation checklist
  - Enforcement guidelines

### Task 3: Architecture Review (AC3) - 30 minutes

- [ ] **Subtask 3.1:** Winston reviews dictionary
  - Completeness check
  - Limitations documented

- [ ] **Subtask 3.2:** Approval
  - Winston signs off
  - Epic 3 test creation unblocked

## Dev Notes

### Data-First Methodology

**Lesson from Epic 2:**
- Requirements-first approach caused 66pp accuracy gap
- Ground truth asked for non-existent data
- Data-first prevents this entirely

**New Process:**
1. Inspect database → Document available data
2. Create test queries from dictionary
3. Validate queries against dictionary BEFORE execution

### Epic 3 Analytical Queries

**Difference from Epic 2:**
- Epic 2: Retrieval queries (simple metric lookups)
- Epic 3: Analytical queries (calculations, trends, multi-step reasoning)

**Data Requirements:**
- Time series data (YoY growth, trend analysis)
- Multiple metrics (margin = EBITDA / Revenue)
- Multi-entity comparisons (Portugal vs Tunisia)

### Testing Standards

**Dictionary as Single Source of Truth:**
- All test queries validated against dictionary
- No assumptions about data availability
- Explicit documentation of limitations

### References

**Source Documents:**
- [Epic 2 Retrospective](docs/retrospectives/epic-2-retro-2025-11-05.md) - Ground truth misalignment issue
- [Epic 3 Prep Tech Spec](docs/tech-spec-epic-3-prep.md#story-302) - Data dictionary spec
- [Action Item 1](docs/retrospectives/epic-2-retro-2025-11-05.md#action-item-1-data-validation-first) - Data validation first mandate

## Dev Agent Record

### Context Reference

<!-- Story Context XML path will be added here if generated -->

### Agent Model Used

Claude 3.7 Sonnet (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

---

**Story Created:** 2025-11-05
**Created By:** Bob (Scrum Master) - Batch create from Epic 3 Prep tech spec
**Next Step:** Review story, then run `story-ready` or `story-context` to mark ready for dev
