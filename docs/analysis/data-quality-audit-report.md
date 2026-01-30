# Data Quality Audit Report - RAGLite Financial Database

**Date:** 2026-01-28 (Updated)
**Database:** PostgreSQL `raglite`
**Total Records:** 461,637 rows
**Unique Metrics:** 982
**Unique Entities:** 880

---

## Remediation Status

### Phase 3 (Completed): Unit Inference
- NULL units reduced: 59.6% → 13%
- Contaminated units eliminated: ~7,200 → 0
- Original units preserved: 98.6%

### Phase 4 (Implemented): Comprehensive Cleanup
Scripts created for all major issues:
- `scripts/fix_structural_cleanup.py` - Phase 4A: Empty metrics, entity contamination
- `scripts/fix_ratio_decomposition.py` - Phase 4B: Ratio metric (1,604 → <20 units)
- `scripts/fix_currency_cleanup.py` - Phase 4C: Currency metric (317 → <10 units)
- `scripts/fix_ebitda_scale.py` - Phase 4D: kEUR/M EUR mixing
- `scripts/fix_forecasting_variables.py` - Phase 4E: Forecasting readiness
- `scripts/verify_all_variables_quality.py` - Comprehensive validation

---

## Executive Summary

This audit reveals **critical data quality issues** that directly impact forecasting accuracy. The most severe issues require immediate remediation before any forecasting can be trusted.

| Issue Category | Severity | Records Affected | Impact |
|----------------|----------|------------------|--------|
| Missing unit information | CRITICAL | 197,318 (42.7%) | Cannot normalize values |
| Unit scale mixing (EUR/kEUR/MEUR) | CRITICAL | All financial metrics | 1000x calculation errors |
| Malformed unit fields | CRITICAL | ~4,000+ rows | Data corruption |
| 88.9% negative Variable Costs | CRITICAL | 1,503 of 1,691 rows | Sign convention issue |
| Metrics stored as entities | HIGH | 489 rows | Entity aggregation pollution |
| NULL financial values | HIGH | 62,351 (13.5%) | Missing data gaps |
| Future year data corruption | MEDIUM | 624 rows | Fiscal years 2026, 2030, 2045 |

---

## Database Overview

| Metric | Value |
|--------|-------|
| **Total Rows** | 461,648 |
| **NULL Values** | 62,351 (13.5%) |
| **Missing Units** | 197,318 (42.7%) |
| **Negative Values** | 61,924 (13.4%) |
| **Unique Units** | 12,010 |
| **Unique Metrics** | 982 |
| **Unique Entities** | 846 |

---

## P0: Critical Issues (Blocks Forecasting)

### Issue 1: Unit Scale Mixing (EUR/kEUR/MEUR)

**Problem:** EBITDA values are stored in mixed units within the same dataset, causing 1000x calculation errors.

**Evidence:**
```
EBITDA unit distribution:
- (empty): 4,403 rows, avg: 125.74, range: -694 to 995
- EUR:     2,964 rows, avg: 39,008.82, range: -1.39M to 5.99M (clearly different scale!)
- K EUR:   736 rows, avg: 5,011.27, range: -459k to 620k
- M EUR:   150 rows, avg: 220.97, range: -885 to 9,742
- Meur:    242 rows, avg: 25.12, range: -6,970 to 973
```

**Root Cause:**
- SQL query (`sql_extraction_query.py:121-123`) uses threshold `> 1000` for inline conversion
- Python post-processing (`_normalization.py:26`) uses threshold `> 10000` for EBITDA
- **These thresholds are inconsistent, causing double-conversion or no conversion**

**Swing Ratio Analysis:**
| Entity | Min Value | Max Value | Swing Ratio |
|--------|-----------|-----------|-------------|
| Angola | -173,904 | 1,259,578 | 7.2x |
| Group | -536,530 | 785,878 | 1.5x |
| Portugal | -459,856 | 620,923 | 1.4x |
| Currency (1000 EUR) | -466 | 1,742 | 3.7x |

**HIGH VARIANCE detected in 30/30 sampled metric/entity combinations.**

---

### Issue 2: 88.9% Negative Variable Costs

**Problem:** 1,503 of 1,691 Variable Cost records (88.9%) are negative.

**Evidence by Entity:**
| Entity | Total | Negatives | Positives | Pattern |
|--------|-------|-----------|-----------|---------|
| (empty) | 516 | 502 (97.3%) | 6 | Consistent negative |
| Portugal | 555 | 292 (52.6%) | 263 | Mixed |
| Brazil | 294 | 268 (91.2%) | 26 | Mostly negative |
| Lebanon* | 270 | 265 (98.1%) | 5 | Consistent negative |
| Tunisia | 269 | 264 (98.1%) | 5 | Consistent negative |
| Ready-Mix | 178 | 0 (0%) | 178 | All positive |

**Root Cause Options:**
1. **Accounting convention:** Costs stored as negative by design (outflows)
2. **Data entry error:** Sign convention not enforced at ingestion
3. **Mixed sources:** Different documents use different conventions

**Current Handling:** `get_cost_metrics()` in `sql_extraction_config.py:161-176` marks Variable Cost for absolute value conversion. The `convert_cost_to_absolute()` function handles this correctly.

**Recommendation:** Document that negative costs are by design and the extraction pipeline handles this via Step 6 normalization.

---

### Issue 3: Malformed Unit Fields

**Problem:** 4,000+ rows have corrupted, invalid, or misplaced data in the `unit` field.

**Examples of Corruption:**
| Unit Value | Count | Issue Type |
|------------|-------|------------|
| `0` | 752 | Numeric in unit field |
| `-` | 648 | Invalid placeholder |
| `0.0` | 329 | Numeric in unit field |
| `Aug-25`, `Aug-24` | 560 | Period code in unit field |
| `!` | 150 | Symbol corruption |
| `) ##########` | 56 | Excel overflow corruption |
| `7`, `3`, `2`, `6` | 241 | Pure integers |
| `0.2`, `0.1` | 126 | Decimal numbers |

**Total Malformed:** ~4,000+ rows with clearly invalid unit values

**Root Cause:** PDF/Excel extraction placing values in wrong columns, or Excel formatting corruption bleeding into data fields.

---

### Issue 4: Double Normalization Bug

**Problem:** SQL query and Python post-processing use different thresholds for kEUR→EUR conversion.

**Code Analysis:**

**File: `sql_extraction_query.py` (lines 119-124)**
```python
CASE
    WHEN value > 1000 THEN value / 1000.0  # Threshold: 1000
    ELSE value
END as value
```

**File: `_normalization.py` (line 26)**
```python
EBITDA_KEUR_THRESHOLD = 10000  # Threshold: 10000
```

**Impact:**
- Values between 1,000 and 10,000 are divided by 1000 in SQL but NOT flagged for conversion in Python
- Values > 10,000 are divided by 1000 in SQL AND then divided by 1000 again in Python (double conversion = 1,000,000x error)

---

## P1: High Priority Issues

### Issue 5: Entity Column Contamination

**Problem:** 489 rows have metrics/financial items stored in the `entity_normalized` column instead of the `metric` column.

**Contaminated Entities:**
| Entity Value | Row Count | Should Be |
|--------------|-----------|-----------|
| CF from Operations | 115 | metric |
| De(in)crease Trade Working Capital | 109 | metric |
| CF from Operating Activities | 106 | metric |
| Net interest expenses | 99 | metric |
| Trade Working Capital | 22 | metric |
| Other Working Capital Variances | 8 | metric |

**Impact:** These rows pollute entity-level aggregations when querying by entity (e.g., "GROUP EBITDA" includes cash flow items).

---

### Issue 6: Negative Revenue/Turnover Records

**Analysis of Cost-Like Metrics:**
| Metric | Total | Negatives | % Negative |
|--------|-------|-----------|------------|
| Electrical Energy | 720 | 720 | 100% |
| Cost of Goods Sold | 13 | 13 | 100% |
| Other Fixed | 720 | 718 | 99.7% |
| Employee | 720 | 718 | 99.7% |
| Other Variable Costs | 725 | 719 | 99.2% |
| Thermal Energy | 720 | 712 | 98.9% |
| Fixed Costs | 1,758 | 1,570 | 89.3% |
| Variable Cost | 1,691 | 1,503 | 88.9% |

**Interpretation:** Cost metrics being stored as negative is a valid accounting convention. The extraction pipeline already handles this via `convert_cost_to_absolute()`.

---

### Issue 7: Future Year Data Corruption

**Fiscal Years in Database:**
| Fiscal Year | Rows | Status |
|-------------|------|--------|
| 2020 | 2,833 | Valid |
| 2021 | 2,480 | Valid |
| 2022 | 3,751 | Valid |
| 2023 | 12,385 | Valid |
| 2024 | 41,134 | Valid |
| 2025 | 49,204 | Valid |
| 2026 | 613 | **Future - Budgets/Forecasts** |
| 2030 | 4 | **Invalid** |
| 2045 | 7 | **Invalid** |

**Impact:** 2030/2045 data is clearly erroneous. 2026 data may be legitimate budget/forecast data.

---

## P2: Medium Priority Issues

### Issue 8: Missing Unit Information

**Scope:** 197,318 rows (42.7%) have NULL or empty unit fields.

**Distribution by Metric Type:**
| Metric | Empty Unit Records | Notes |
|--------|-------------------|-------|
| CAPEX | 9,002 | Largest contributor |
| EBITDA | 4,403 | Second largest |
| (various) | 183,913 | Distributed |

**Recommendation:** Infer units from metric type where possible (e.g., all EBITDA in EUR millions).

---

### Issue 9: Metric Name Inconsistencies

**Examples:**
| Variant 1 | Count | Variant 2 | Count |
|-----------|-------|-----------|-------|
| CAPEX | 9,689 | Capex | 3,188 |
| EBITDA | 6,393 | EBITDA IFRS | 3,627 |

**Impact:** Same metric split across multiple spellings requires synonym mapping (already implemented in `get_metric_synonyms()`).

---

## Code Pipeline Analysis

### Current Normalization Pipeline (6 Steps)

```
Step 1: Deduplicate points
Step 2: EBITDA pre-YTD normalization (if YTD data)
Step 3: YTD → Monthly conversion
Step 4: Unit normalization & outlier filtering
Step 5: Percentage bounds (for percentage metrics)
Step 6: Cost absolute value conversion
```

### Identified Issues in Pipeline

| Location | Issue | Severity |
|----------|-------|----------|
| `sql_extraction_query.py:121-123` | Inline kEUR→EUR threshold (>1000) | CRITICAL |
| `_normalization.py:26` | EBITDA threshold (10000) differs from SQL | CRITICAL |
| `sql_extraction_execution.py:90-93` | GROUP variations list may be incomplete | MEDIUM |
| Phase 3 entity fallback | Removes entity filtering for inverted data | LOW |

---

## Remediation Recommendations

### P0 Fixes (Immediate)

1. **Align Unit Conversion Thresholds**
   - Remove inline SQL conversion (lines 119-124 in `sql_extraction_query.py`)
   - Let Python post-processing handle all normalization
   - Single source of truth for threshold: 10,000

2. **Create Unit Normalization Mapping**
   - Centralized `UNIT_NORMALIZATION_MAP` for all unit variants
   - Normalize at ingestion time, not extraction time

3. **Audit Malformed Units**
   - Query: `WHERE unit ~ '[#@!()]' OR unit ~ '^[0-9-]+$'`
   - Set to NULL for re-processing or manual review

4. **Document Variable Cost Convention**
   - Negative values are by design (accounting outflows)
   - Confirm `convert_cost_to_absolute()` handles correctly

### P1 Fixes (This Sprint)

5. **Clean Entity Contamination**
   - Flag 489 rows for manual review
   - Update `entity_normalized = NULL` for contaminated rows

6. **Remove Invalid Fiscal Years**
   - Delete rows with fiscal_year IN (2030, 2045)
   - Flag 2026 as budget/forecast data

### P2 Fixes (Next Sprint)

7. **Infer Missing Units**
   - Create unit inference rules by metric type
   - Update 197k rows with NULL units

8. **Consolidate Metric Variants**
   - Extend `get_metric_synonyms()` mapping

---

## Verification Metrics

### Before (Current State)

| Metric | Value |
|--------|-------|
| EBITDA swing ratio | 28.7x+ |
| Missing units | 42.7% |
| Malformed units | ~1% |
| NULL values | 13.5% |
| Negative costs (expected) | 88.9% Variable Cost |

### Target (After Remediation)

| Metric | Target |
|--------|--------|
| EBITDA swing ratio | <5x |
| Missing units | <10% |
| Malformed units | 0% |
| NULL values | <5% |
| Negative costs | Converted to absolute |

---

## Appendix A: Audit Queries Used

```sql
-- Query 1: EBITDA quality summary by entity
SELECT entity_normalized, COUNT(*) as records, COUNT(DISTINCT unit) as unit_variants,
       SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) as negatives,
       MIN(value), MAX(value), AVG(value), STDDEV(value)
FROM financial_tables WHERE LOWER(metric) LIKE '%ebitda%'
GROUP BY entity_normalized ORDER BY records DESC;

-- Query 2: Unit distribution for key metrics
SELECT metric, unit, COUNT(*) as count, MIN(value), MAX(value)
FROM financial_tables WHERE metric IN ('EBITDA', 'EBITDA IFRS', 'Turnover', 'CAPEX', 'Variable Cost')
GROUP BY metric, unit ORDER BY metric, count DESC;

-- Query 3: Negative value analysis
SELECT metric, COUNT(*) as total, SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) as negatives,
       100.0 * SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) / COUNT(*) as pct_negative
FROM financial_tables WHERE metric IS NOT NULL GROUP BY metric
HAVING SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) > 10 ORDER BY pct_negative DESC;

-- Query 4: Entity contamination check
SELECT entity_normalized, COUNT(*) FROM financial_tables
WHERE entity_normalized LIKE '%CF%' OR entity_normalized LIKE '%interest%'
   OR entity_normalized LIKE '%Working Capital%' GROUP BY entity_normalized;

-- Query 5: Malformed unit detection
SELECT unit, COUNT(*) FROM financial_tables
WHERE unit ~ '[#@!]' OR unit ~ '^[0-9-]+$' OR unit ~ '^[A-Z][a-z]{2}-[0-9]{2}$'
GROUP BY unit ORDER BY count DESC;

-- Query 6: Period coverage gaps
SELECT fiscal_year, COUNT(DISTINCT SUBSTRING(column_name FROM 1 FOR 3)), COUNT(*)
FROM financial_tables WHERE fiscal_year >= 2020 GROUP BY fiscal_year;

-- Query 7: Scale consistency check
WITH stats AS (SELECT metric, entity_normalized, fiscal_year, AVG(value), STDDEV(value)
               FROM financial_tables WHERE value > 0 GROUP BY 1,2,3)
SELECT *, CASE WHEN stddev/avg_val > 2 THEN 'HIGH VARIANCE' ELSE 'OK' END
FROM stats WHERE metric IN ('EBITDA', 'EBITDA IFRS', 'Turnover');
```

---

## Appendix B: Files Analyzed

| File | Purpose |
|------|---------|
| `sql_extraction_query.py` | SQL query building, inline unit conversion |
| `sql_extraction_execution.py` | Entity filtering, fallback logic |
| `sql_extraction_normalization.py` | 6-step normalization pipeline |
| `sql_extraction_config.py` | Aggregation functions, metric synonyms |
| `_normalization.py` | EBITDA threshold, unit normalization |
| `_postprocessing.py` | Percentage bounds, cost conversion |

---

---

## Appendix C: Phase 4 Execution Guide

### Prerequisites
Ensure Phase 3 scripts have been run:
```bash
# Phase 3 (already completed)
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_unit_audit_columns.py
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_unit_standardization.py
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_unit_magnitude_inference.py
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_unit_context_inference.py
```

### Phase 4 Execution Order

```bash
# Phase 4A: Structural Cleanup (delete empty metrics, entity contamination)
# DRY RUN FIRST:
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_structural_cleanup.py --dry-run

# EXECUTE:
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_structural_cleanup.py

# Phase 4B: Ratio Metric Decomposition
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_ratio_decomposition.py --dry-run

POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_ratio_decomposition.py

# Phase 4C: Currency Metric Cleanup
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_currency_cleanup.py --dry-run

POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_currency_cleanup.py

# Phase 4D: EBITDA Scale Reconciliation
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_ebitda_scale.py --dry-run

POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_ebitda_scale.py

# Phase 4E: Forecasting Variable Preparation
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_forecasting_variables.py --dry-run

POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/fix_forecasting_variables.py

# FINAL VERIFICATION
POSTGRES_USER=raglite POSTGRES_PASSWORD=raglite POSTGRES_DB=raglite POSTGRES_PORT=5432 \
    uv run python scripts/verify_all_variables_quality.py --verbose
```

### Success Criteria (Phase 4)

| Metric | Before Phase 4 | Target |
|--------|----------------|--------|
| Empty metric rows | 83,090 (18%) | 0 |
| Entity contamination | 489 rows | 0 |
| Ratio unique units | 1,604 | <20 |
| Currency unique units | 317 | <10 |
| NULL units | 13% | <5% |
| EBITDA scale mixing | 828 rows | 0 |
| Forecasting vars ready | 4/11 | 8/11 |

### Rollback Procedure

If Phase 4 causes issues:
```sql
-- Backup tables are created automatically with timestamps
-- List backups:
SELECT table_name FROM information_schema.tables
WHERE table_name LIKE 'backup_%' ORDER BY table_name;

-- Restore example:
INSERT INTO financial_tables SELECT * FROM backup_empty_metrics_20260128_123456;
```

---

**Report Generated:** 2026-01-28 by Data Quality Audit Pipeline
