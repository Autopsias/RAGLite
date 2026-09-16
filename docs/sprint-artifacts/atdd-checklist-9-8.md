# ATDD Checklist - Story 9.8: Forecasting Query Simplification

**Generated:** 2026-02-01
**Status:** RED (Tests created, not implemented)
**Story:** [9-8-forecasting-query-simplification.md](../implementation-artifacts/9-8-forecasting-query-simplification.md)

## Test Summary

| AC | Test Count | Priority | Status |
|----|------------|----------|--------|
| AC1 | 8 | P0/P1 | RED |
| AC2 | 11 | P0/P1 | RED |
| AC3 | 10 | P1/P2 | RED |
| AC4 | 11 | P0/P1 | RED |
| AC5 | 8 | P0/P1/P2 | RED |
| AC6 | 10 | P1/P2 | RED |
| **Total** | **58** | - | **RED** |

## Acceptance Criteria Coverage

### AC1: Period Normalization Logic Removed (8 tests)

- [ ] TEST-AC-9.8.1.1 [P0]: SQL queries use period_type column filter
- [ ] TEST-AC-9.8.1.2 [P0]: SQL queries use value_type column filter
- [ ] TEST-AC-9.8.1.3 [P0]: YTD queries use period_type column filter
- [ ] TEST-AC-9.8.1.4 [P1]: Classification imports removed from sql_extraction modules
- [ ] TEST-AC-9.8.1.5 [P1]: Complex regex period matching is replaced
- [ ] TEST-AC-9.8.1.6 [P0]: Query does not use budget exclusion regex
- [ ] TEST-AC-9.8.1.7 [P1]: _get_period_match_clause() is simplified
- [ ] TEST-AC-9.8.1.8 [P1]: _get_budget_exclusion_clause() removed or simplified

### AC2: Direct SQL Queries by Classification Fields (11 tests)

- [ ] TEST-AC-9.8.2.1 [P0]: Monthly actuals query uses period_type filter
- [ ] TEST-AC-9.8.2.2 [P0]: Monthly actuals query uses value_type filter
- [ ] TEST-AC-9.8.2.3 [P0]: Combined filter for monthly actuals
- [ ] TEST-AC-9.8.2.4 [P0]: YTD actuals query uses period_type filter
- [ ] TEST-AC-9.8.2.5 [P0]: YTD actuals query uses value_type filter
- [ ] TEST-AC-9.8.2.6 [P0]: Combined filter for YTD actuals
- [ ] TEST-AC-9.8.2.7 [P0]: Budget exclusion uses column, not regex
- [ ] TEST-AC-9.8.2.8 [P1]: No pattern '^B\\s' regex in query
- [ ] TEST-AC-9.8.2.9 [P1]: No YTD budget regex pattern
- [ ] TEST-AC-9.8.2.10 [P0]: Query references period_type column
- [ ] TEST-AC-9.8.2.11 [P0]: Query references value_type column

### AC3: LOC Reduction Target (50+ Lines) (10 tests)

- [ ] TEST-AC-9.8.3.1 [P1]: Total LOC reduction >= 50 lines achieved
- [ ] TEST-AC-9.8.3.2 [P1]: sql_extraction_query.py LOC reduced
- [ ] TEST-AC-9.8.3.3 [P1]: _get_period_match_clause() function simplified
- [ ] TEST-AC-9.8.3.4 [P1]: _get_budget_exclusion_clause() simplified or removed
- [ ] TEST-AC-9.8.3.5 [P1]: sql_extraction_parsing.py LOC reduced
- [ ] TEST-AC-9.8.3.6 [P1]: Runtime classification calls removed
- [ ] TEST-AC-9.8.3.7 [P1]: generate_classification_report() calls removed
- [ ] TEST-AC-9.8.3.8 [P1]: orchestrator.py LOC reduced
- [ ] TEST-AC-9.8.3.9 [P1]: _parse_period_multi_format() can use period_type
- [ ] TEST-AC-9.8.3.10 [P2]: Removed code documented in Dev Agent Record

### AC4: Backward Compatibility Maintained (11 tests)

- [ ] TEST-AC-9.8.4.1 [P0]: Existing unit tests pass
- [ ] TEST-AC-9.8.4.2 [P0]: sql_extraction_query tests pass
- [ ] TEST-AC-9.8.4.3 [P0]: Existing integration tests pass
- [ ] TEST-AC-9.8.4.4 [P0]: Forecasting integration tests pass
- [ ] TEST-AC-9.8.4.5 [P0]: get_financial_forecast returns same data
- [ ] TEST-AC-9.8.4.6 [P0]: get_health_status reports same metrics
- [ ] TEST-AC-9.8.4.7 [P1]: Forecast response structure unchanged
- [ ] TEST-AC-9.8.4.8 [P0]: MAPE (Mean Absolute Percentage Error) not degraded
- [ ] TEST-AC-9.8.4.9 [P1]: Forecast values unchanged for known input
- [ ] TEST-AC-9.8.4.10 [P1]: Handles NULL period_type gracefully
- [ ] TEST-AC-9.8.4.11 [P1]: Handles NULL value_type gracefully

### AC5: Query Performance Improvement (8 tests)

- [ ] TEST-AC-9.8.5.1 [P1]: Query execution is 20%+ faster
- [ ] TEST-AC-9.8.5.2 [P1]: period_type column index is used
- [ ] TEST-AC-9.8.5.3 [P1]: value_type column index is used
- [ ] TEST-AC-9.8.5.4 [P0]: No regex operations in simplified query
- [ ] TEST-AC-9.8.5.5 [P1]: Equality check performs better than regex
- [ ] TEST-AC-9.8.5.6 [P1]: Budget exclusion with equality faster than regex
- [ ] TEST-AC-9.8.5.7 [P1]: Performance improvement can be benchmarked
- [ ] TEST-AC-9.8.5.8 [P2]: Performance improvement is documented

### AC6: Data Quality Orchestrator Simplification (10 tests)

- [ ] TEST-AC-9.8.6.1 [P1]: Period parsing can use period_type column
- [ ] TEST-AC-9.8.6.2 [P1]: Monthly data can be filtered by period_type
- [ ] TEST-AC-9.8.6.3 [P1]: YTD data can be filtered by period_type
- [ ] TEST-AC-9.8.6.4 [P1]: Classification counts can be retrieved from database
- [ ] TEST-AC-9.8.6.5 [P1]: Period type distribution is available
- [ ] TEST-AC-9.8.6.6 [P1]: Value type distribution is available
- [ ] TEST-AC-9.8.6.7 [P1]: _fetch_secil_data() uses period_type column
- [ ] TEST-AC-9.8.6.8 [P1]: Optional method for classification stats from DB
- [ ] TEST-AC-9.8.6.9 [P1]: Existing orchestrator methods continue to work
- [ ] TEST-AC-9.8.6.10 [P2]: _parse_period_multi_format() still works

## Test Files

| File | Tests | ACs Covered |
|------|-------|-------------|
| `test_ac1_period_normalization_removed.py` | 8 | AC1 |
| `test_ac2_direct_sql_queries.py` | 11 | AC2 |
| `test_ac3_loc_reduction.py` | 10 | AC3 |
| `test_ac4_backward_compatibility.py` | 11 | AC4 |
| `test_ac5_query_performance.py` | 8 | AC5 |
| `test_ac6_orchestrator_simplification.py` | 10 | AC6 |

## Priority Distribution

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 23 | Critical - Core functionality, must pass |
| P1 | 32 | Important - Quality improvements |
| P2 | 3 | Nice-to-have - Documentation, edge cases |

## Implementation Notes

### Key Behavior Assertions

1. **Query Structure**: Queries must use `period_type` and `value_type` columns, not regex
2. **LOC Target**: Combined reduction >= 50 lines across modified files
3. **Performance**: 20%+ improvement in query execution time
4. **Compatibility**: All existing tests must pass, MCP responses unchanged

### Files Under Test

| File | Purpose |
|------|---------|
| `raglite/forecasting/timeseries/sql_extraction_query.py` | Query building |
| `raglite/forecasting/timeseries/sql_extraction_parsing.py` | Row parsing |
| `raglite/forecasting/data_quality/orchestrator.py` | Data quality |

### Expected Query Transformation

**Before (regex-based):**
```sql
WHERE period ~ '^[A-Za-z]{3}-[0-9]{2,4}$'
  AND period !~ '^B\s'
  AND period !~ '\sB\s'
```

**After (column-based):**
```sql
WHERE period_type = 'monthly_actual'
  AND value_type = 'actual'
```

## Running Tests

```bash
# Run all Story 9.8 acceptance tests
uv run pytest tests/acceptance/story_9_8/ -v

# Run only P0 (critical) tests
uv run pytest tests/acceptance/story_9_8/ -v -m p0

# Run specific AC tests
uv run pytest tests/acceptance/story_9_8/test_ac1_period_normalization_removed.py -v
```

## Completion Criteria

- [ ] All 58 tests pass (currently all RED)
- [ ] LOC reduction >= 50 lines verified
- [ ] Performance improvement >= 20% measured
- [ ] All existing unit/integration tests still pass
- [ ] MCP tool responses unchanged
- [ ] MAPE accuracy not degraded
