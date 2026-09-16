# Story 9.6: Storage Extension - Store Classification Fields

**Epic:** [Epic 9 - Data Quality at Ingestion](../epics/epic-9-tracking.md)

Status: done

## Story

As a data engineer,
I want the PostgreSQL table storage to persist the classification fields (period_type, value_type, entity_level) from enriched rows,
so that downstream queries can filter and group by classification without runtime computation, enabling simpler and faster forecasting queries.

## Acceptance Criteria (BDD Format)

### AC1: Classification Fields Included in INSERT Statement

```gherkin
Given the financial_tables table has classification columns (Story 9.1):
  - period_type VARCHAR(50)
  - value_type VARCHAR(50)
  - entity_level VARCHAR(100)
When store_tables_in_postgresql() receives rows with classification fields from Story 9.5
Then the INSERT statement includes all three classification columns
And classification values are extracted from row dict keys:
  - row.get("period_type") -> period_type column
  - row.get("value_type") -> value_type column
  - row.get("entity_level") -> entity_level column
And the column order in INSERT matches the VALUES tuple order
```

### AC2: Backward Compatibility for Rows Without Classification

```gherkin
Given existing code paths may produce rows without classification fields
When store_tables_in_postgresql() receives a row without period_type, value_type, or entity_level
Then NULL is inserted for missing classification fields (columns are nullable)
And existing rows (without classification) are stored successfully
And no errors are raised for missing classification fields
And backward compatibility is maintained for pre-Epic-9 code paths
```

### AC3: Classification Field Validation

```gherkin
Given classification fields use enum string values:
  - period_type: "monthly_actual", "ytd_actual", "budget", "ytd_budget", "unknown"
  - value_type: "actual", "budget", "forecast", "variance", "unknown"
  - entity_level: "consolidated", "company_only", "segment", "geographic", "unknown"
When a row is stored with classification fields
Then string values are stored exactly as provided (no transformation)
And VARCHAR column size accommodates all enum values (50/50/100 chars)
And storage does NOT validate enum membership (classifiers handle validation)
```

### AC4: Query Verification

```gherkin
Given rows are stored with classification fields
When querying financial_tables with classification filters:
  - SELECT * FROM financial_tables WHERE period_type = 'monthly_actual'
  - SELECT * FROM financial_tables WHERE value_type = 'actual'
  - SELECT * FROM financial_tables WHERE entity_level = 'company_only'
Then queries return correctly filtered results
And indexes (created in Story 9.1) provide efficient lookups
And combined filters work: WHERE period_type = 'monthly_actual' AND value_type = 'actual'
```

### AC5: Storage Metrics Include Classification

```gherkin
Given classification fields add storage overhead
When store_tables_in_postgresql() completes successfully
Then logging includes classification field presence:
  - rows_with_classification: count of rows with all 3 fields populated
  - rows_without_classification: count of rows with NULL classification
And metrics enable monitoring of classification coverage during migration
```

## Tasks / Subtasks

- [ ] Task 1: Update _prepare_table_records to include classification fields (AC: #1, #2)
  - [ ] 1.1: Add period_type, value_type, entity_level to record tuple
  - [ ] 1.2: Use row.get() with None default for backward compatibility
  - [ ] 1.3: Update tuple field order documentation

- [ ] Task 2: Update INSERT statement in _insert_records_in_batches (AC: #1)
  - [ ] 2.1: Add period_type, value_type, entity_level to column list
  - [ ] 2.2: Ensure VALUES placeholder count matches column count
  - [ ] 2.3: Maintain existing column order, append classification at end

- [ ] Task 3: Add classification coverage logging (AC: #5)
  - [ ] 3.1: Count rows with all classification fields populated
  - [ ] 3.2: Count rows with NULL classification (backward compat)
  - [ ] 3.3: Add metrics to _log_storage_success extra fields

- [ ] Task 4: Unit tests (AC: #1, #2, #3)
  - [ ] 4.1: Test storage with classification fields populated
  - [ ] 4.2: Test storage without classification fields (backward compat)
  - [ ] 4.3: Test storage with partial classification (some fields NULL)
  - [ ] 4.4: Test record tuple structure matches INSERT column order

- [ ] Task 5: Integration tests (AC: #4)
  - [ ] 5.1: Test end-to-end: extraction -> classification -> storage -> query
  - [ ] 5.2: Verify queries by period_type return correct rows
  - [ ] 5.3: Verify queries by value_type return correct rows
  - [ ] 5.4: Verify queries by entity_level return correct rows
  - [ ] 5.5: Test combined filter queries

## Dev Notes

### Architecture Reference

**Module Location:** `raglite/ingestion/storage/table_store.py`

Per Architecture Section 6 (Reference Implementation), the storage layer follows the pattern:
- Direct SDK usage (psycopg2) without custom wrappers
- Batch insertion via `psycopg2.extras.execute_values()`
- Structured logging with `extra={}` for metrics
- Pydantic models for type safety (StorageMetrics)

**Key Functions:**
- `store_tables_in_postgresql()` - Main entry point
- `_prepare_table_records()` - Row dict -> tuple transformation
- `_insert_records_in_batches()` - Batch INSERT execution
- `_log_storage_success()` - Metrics logging

### Current INSERT Statement (table_store.py line 120-128)

```python
execute_values(
    cursor,
    """
    INSERT INTO financial_tables (
        document_id, page_number, table_index, table_caption,
        entity, metric, period, fiscal_year, value, unit,
        row_index, column_name, chunk_text
    ) VALUES %s
    """,
    batch_records,
)
```

### Updated INSERT Statement (Story 9.6)

```python
execute_values(
    cursor,
    """
    INSERT INTO financial_tables (
        document_id, page_number, table_index, table_caption,
        entity, metric, period, fiscal_year, value, unit,
        row_index, column_name, chunk_text,
        period_type, value_type, entity_level
    ) VALUES %s
    """,
    batch_records,
)
```

### Record Tuple Update (_prepare_table_records)

```python
# Current record tuple (13 fields):
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

# Updated record tuple (16 fields):
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
    # NEW: Classification fields (Story 9.6)
    row.get("period_type"),      # None if not classified
    row.get("value_type"),       # None if not classified
    row.get("entity_level"),     # None if not classified
)
```

### Classification Coverage Logging

```python
# In _log_storage_success or new helper:
rows_with_classification = sum(
    1 for row in valid_rows
    if row.get("period_type") and row.get("value_type") and row.get("entity_level")
)
rows_without_classification = len(valid_rows) - rows_with_classification

logger.info(
    "PostgreSQL table storage complete",
    extra={
        # ... existing metrics ...
        "rows_with_classification": rows_with_classification,
        "rows_without_classification": rows_without_classification,
        "classification_coverage_pct": round(
            100 * rows_with_classification / len(valid_rows), 1
        ) if valid_rows else 0,
    },
)
```

### Data Flow (End-to-End)

```
PDF Extraction (Docling)
    -> Row Dict {entity, metric, period, value, ...}
    -> Story 9.5: classify_rows_batch()
    -> Enriched Row Dict {entity, metric, period, value, ..., period_type, value_type, entity_level}
    -> Story 9.6: store_tables_in_postgresql()
    -> PostgreSQL INSERT with all 16 columns
    -> financial_tables table with classification fields populated
```

### Query Examples (Story 9.8 will use these)

```sql
-- Get monthly actuals for forecasting
SELECT entity, metric, period, value
FROM financial_tables
WHERE period_type = 'monthly_actual'
  AND value_type = 'actual'
ORDER BY entity, metric, period;

-- Get budget data for variance analysis
SELECT entity, metric, period, value
FROM financial_tables
WHERE value_type = 'budget';

-- Get consolidated-only rows (exclude segment/geographic breakdown)
SELECT DISTINCT entity
FROM financial_tables
WHERE entity_level = 'consolidated';
```

### File Modification

**Target file:** `raglite/ingestion/storage/table_store.py`

Changes:
1. `_prepare_table_records()`: Add 3 fields to record tuple
2. `_insert_records_in_batches()`: Add 3 columns to INSERT
3. `_log_storage_success()`: Add classification coverage metrics
4. Add helper function `_count_classification_coverage()` if needed

**Estimated LOC change:** +15 lines (well within 500 LOC limit)

### Test Files

- Unit: `tests/unit/ingestion/storage/test_table_store_classification.py`
- Integration: `tests/integration/ingestion/test_storage_classification.py`

### Dependencies

- **Requires:** Story 9.1 (schema migration) - columns must exist
- **Requires:** Story 9.5 (classification integration) - rows have classification fields
- **Enables:** Story 9.7 (re-ingestion) - re-process existing PDFs
- **Enables:** Story 9.8 (forecasting query simplification) - query by classification

### References

- [Source: raglite/ingestion/storage/table_store.py] - Current storage implementation
- [Source: migrations/migration_007_add_classification_columns.py] - Schema migration
- [Source: raglite/ingestion/classification/integration.py] - Classification enrichment
- [Source: docs/epics/epic-9-tracking.md] - Epic requirements
- [Source: .claude/rules/database-safety.md] - Database operation safety

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
