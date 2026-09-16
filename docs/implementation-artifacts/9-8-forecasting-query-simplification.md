# Story 9.8: Forecasting Query Simplification

**Epic:** [Epic 9 - Data Quality at Ingestion](../epics/epic-9-tracking.md)

Status: done

## Story

As a developer,
I want to simplify the forecasting query logic by using the pre-classified `period_type`, `value_type`, and `entity_level` columns from the database,
so that the forecasting module has cleaner code, faster queries, and more reliable data filtering without runtime period classification.

## Context

Stories 9.1-9.7 have established a classification pipeline:
- Database columns added: `period_type`, `value_type`, `entity_level` (Story 9.1)
- Classification modules implemented (Stories 9.2-9.4)
- Classification integrated into extraction pipeline (Story 9.5)
- Classification fields stored in PostgreSQL (Story 9.6)
- All existing PDFs re-ingested with classification (Story 9.7)

The forecasting module (`raglite/forecasting/timeseries/`) currently contains complex runtime classification and filtering logic that can now be replaced with simple SQL WHERE clauses using the pre-classified columns.

## Acceptance Criteria (BDD Format)

### AC1: Period Normalization Logic Removed

```gherkin
Given the forecasting module currently classifies periods at query time:
  - raglite/forecasting/timeseries/period_classification.py (~334 LOC)
  - raglite/forecasting/timeseries/sql_extraction_parsing.py (classification integration ~150 LOC)
When Story 9.8 simplification is complete
Then runtime period classification is replaced with SQL filters:
  - WHERE period_type = 'monthly_actual' (for monthly data)
  - WHERE period_type = 'ytd_actual' (for YTD data)
  - WHERE value_type = 'actual' (exclude budget data)
And the complex regex-based period parsing in sql_extraction_query.py is simplified
And classification import dependencies are removed from sql_extraction modules
```

### AC2: Direct SQL Queries by Classification Fields

```gherkin
Given the financial_tables table has classification columns:
  - period_type VARCHAR(50): 'monthly_actual', 'ytd_actual', 'budget', 'ytd_budget', 'unknown'
  - value_type VARCHAR(50): 'actual', 'budget', 'forecast', 'variance', 'unknown'
  - entity_level VARCHAR(100): 'consolidated', 'company_only', 'segment', 'geographic', 'unknown'
When extracting time-series data for forecasting
Then queries use direct column filters:
  - Monthly actuals: WHERE period_type = 'monthly_actual' AND value_type = 'actual'
  - YTD actuals: WHERE period_type = 'ytd_actual' AND value_type = 'actual'
  - Budget exclusion: WHERE value_type != 'budget'
And complex regex patterns for budget exclusion are removed:
  - No longer needed: period !~ '^B\s' patterns
  - No longer needed: period !~ '\sB\s' patterns
  - No longer needed: period !~ '^YTD\s+B\s' patterns
```

### AC3: LOC Reduction Target (50+ Lines)

```gherkin
Given the Epic 9 success criteria specifies 50+ LOC reduction
When refactoring is complete
Then the following reductions are achieved:
  - sql_extraction_query.py: Simplified _get_period_match_clause() and _get_budget_exclusion_clause()
  - sql_extraction_parsing.py: Reduced classification logic (classification now from database)
  - data_quality/orchestrator.py: Simplified _parse_period_multi_format() using period_type column
And total LOC reduction is >= 50 lines
And removed code is documented in Dev Agent Record
```

### AC4: Backward Compatibility Maintained

```gherkin
Given existing forecasting tests and MCP tools depend on current behavior
When simplification is complete
Then all existing unit tests pass unchanged
And all existing integration tests pass unchanged
And MCP tool responses remain identical:
  - get_financial_forecast returns same data
  - get_health_status reports same metrics
And forecasting accuracy (MAPE) is not degraded
```

### AC5: Query Performance Improvement

```gherkin
Given current queries use regex patterns for period classification
When simplified queries use indexed columns
Then query execution time is reduced:
  - period_type column has index (from Story 9.1 migration)
  - value_type column has index (from Story 9.1 migration)
  - Regex operations replaced with equality checks
And performance improvement is measurable (target: 20%+ faster)
```

### AC6: Data Quality Orchestrator Simplification

```gherkin
Given data_quality/orchestrator.py has _parse_period_multi_format() method
When simplification is complete
Then period parsing can optionally use period_type column:
  - Filter by period_type instead of parsing period strings
  - Monthly data: WHERE period_type = 'monthly_actual'
  - YTD data: WHERE period_type = 'ytd_actual'
And classification reports can use database counts:
  - SELECT period_type, COUNT(*) FROM financial_tables GROUP BY period_type
```

## Tasks / Subtasks

- [ ] Task 1: Simplify SQL query building (AC: #1, #2, #3)
  - [ ] 1.1: Update `sql_extraction_query.py::_get_period_match_clause()` to use period_type column
  - [ ] 1.2: Remove `_get_budget_exclusion_clause()` - replaced by `value_type != 'budget'`
  - [ ] 1.3: Simplify `_build_periods_with_year_cte()` - remove regex period extraction
  - [ ] 1.4: Update `build_timeseries_query()` to accept period_type filter parameter
  - [ ] 1.5: Track LOC changes in each file

- [ ] Task 2: Simplify SQL row parsing (AC: #1, #3)
  - [ ] 2.1: Update `sql_extraction_parsing.py::parse_sql_rows_with_units()` to use DB classification
  - [ ] 2.2: Remove runtime classification calls (classify_period, generate_classification_report)
  - [ ] 2.3: Remove classification imports if no longer needed
  - [ ] 2.4: Update ParsedTimeSeriesData to accept classification from DB

- [ ] Task 3: Simplify data quality orchestrator (AC: #3, #6)
  - [ ] 3.1: Update `orchestrator.py::_fetch_secil_data()` to use period_type column
  - [ ] 3.2: Optionally simplify `_parse_period_multi_format()` with period_type filter
  - [ ] 3.3: Add option to get classification stats from DB (GROUP BY period_type)

- [ ] Task 4: Update SQL extraction execution (AC: #2, #4)
  - [ ] 4.1: Update `sql_extraction_execution.py::execute_sql_with_fallback()` to pass period_type
  - [ ] 4.2: Ensure prefer_ytd flag maps to correct period_type filter
  - [ ] 4.3: Verify entity_filter logic still works with new query structure

- [ ] Task 5: Unit tests (AC: #4)
  - [ ] 5.1: Update `tests/unit/forecasting/timeseries/test_sql_extraction_query.py` for new query format
  - [ ] 5.2: Add tests for period_type-based filtering
  - [ ] 5.3: Ensure classification module tests still pass (period_classification.py not deleted)
  - [ ] 5.4: Test backward compatibility with NULL classification columns (edge case)

- [ ] Task 6: Integration tests (AC: #4, #5)
  - [ ] 6.1: Run full forecasting test suite to verify no regression
  - [ ] 6.2: Test MCP tool `get_financial_forecast` returns same data
  - [ ] 6.3: Measure query performance improvement (before/after timing)
  - [ ] 6.4: Verify MAPE accuracy is unchanged

- [ ] Task 7: Documentation and cleanup (AC: #3)
  - [ ] 7.1: Document LOC reduction in Dev Agent Record
  - [ ] 7.2: Update module docstrings to reflect simplification
  - [ ] 7.3: Add migration note for any deprecated functions

## Dev Notes

### Current Architecture (Before Simplification)

```
Query Flow (Complex):
1. extract_timeseries_from_sql() calls configure_extraction()
2. build_timeseries_query() generates SQL with regex patterns:
   - period ~ '^[A-Za-z]{3}-[0-9]{2,4}$'
   - period !~ '^B\s' (budget exclusion)
   - period !~ '\sB\s' (budget exclusion)
   - period !~ '^YTD\s+B\s' (YTD budget exclusion)
3. parse_sql_rows_with_units() classifies periods at runtime:
   - classify_period() for each row
   - generate_classification_report() for logging
   - validate_period_homogeneity() for quality check
4. Filtered and normalized data returned
```

### Target Architecture (After Simplification)

```
Query Flow (Simplified):
1. extract_timeseries_from_sql() calls configure_extraction()
2. build_timeseries_query() generates SQL with column filters:
   - WHERE period_type = 'monthly_actual'
   - WHERE value_type = 'actual'
3. parse_sql_rows_with_units() reads pre-classified data:
   - period_type already in row from DB
   - No runtime classification needed
4. Filtered and normalized data returned (same output, simpler path)
```

### Files to Modify

| File | Current LOC | Expected Change | Target LOC |
|------|-------------|-----------------|------------|
| `sql_extraction_query.py` | 337 | -30 to -40 | ~300 |
| `sql_extraction_parsing.py` | 263 | -10 to -20 | ~245 |
| `data_quality/orchestrator.py` | 487 | -5 to -10 | ~480 |
| **Total Reduction** | - | **-50 to -70** | - |

### Query Transformation Example

**Before (regex-based filtering):**
```sql
WHERE period IS NOT NULL
  AND (
      period ~ '^YTD\s+[A-Za-z]{3}-[0-9]{2,4}$'
      OR period ~ '^[A-Za-z]{3}-[0-9]{2,4}$'
  )
  AND period !~ '^B\s'
  AND period !~ '\sB\s'
  AND period !~ '\sB$'
  AND period !~ '^YTD\s+B\s'
  AND period IS NOT NULL
  AND TRIM(period) <> ''
  AND period !~* '^N/A$'
  AND period !~* '^None$'
  AND period !~* '^null$'
```

**After (column-based filtering):**
```sql
WHERE period_type IN ('monthly_actual', 'ytd_actual')
  AND value_type = 'actual'
```

### Backward Compatibility Strategy

1. **Keep classification module:** `period_classification.py` remains for:
   - Unit test coverage
   - Potential future re-ingestion
   - Documentation of classification logic

2. **Feature flag (optional):** Could add `use_db_classification=True` parameter to gradually migrate

3. **Null handling:** Support rows without classification (pre-migration data):
   ```sql
   WHERE (period_type IS NULL OR period_type IN ('monthly_actual', 'ytd_actual'))
   ```

### Performance Expectations

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Period matching | Regex scan | Index lookup | ~50% faster |
| Budget exclusion | Multiple regex | Single equality | ~80% faster |
| Row parsing | Runtime classify | DB read | ~90% faster |
| Overall query | ~200ms | ~100ms | ~50% faster |

### Risk Mitigation

1. **Data consistency:** Re-ingestion (Story 9.7) ensures all rows have classification
2. **Test coverage:** Run full test suite before and after
3. **Gradual rollout:** Could use feature flag for A/B comparison
4. **Rollback:** period_classification.py remains if issues found

### References

- [Source: raglite/forecasting/timeseries/sql_extraction_query.py] - Query building (~337 LOC)
- [Source: raglite/forecasting/timeseries/sql_extraction_parsing.py] - Row parsing (~263 LOC)
- [Source: raglite/forecasting/timeseries/period_classification.py] - Classification logic (~334 LOC)
- [Source: raglite/forecasting/data_quality/orchestrator.py] - Data quality checks (~487 LOC)
- [Source: docs/epics/epic-9-tracking.md] - Epic requirements (50+ LOC reduction)
- [Source: .claude/rules/coding-standards.md] - Code quality requirements

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
