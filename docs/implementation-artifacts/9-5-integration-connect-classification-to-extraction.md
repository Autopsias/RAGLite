# Story 9.5: Integration - Connect Classification to Extraction

Status: done

## Story

As a data engineer,
I want the classification modules (period_type, value_type, entity_level) to be automatically invoked during table extraction,
so that every extracted row includes classification fields before storage, enabling simplified downstream queries.

## Acceptance Criteria (BDD Format)

### AC1: Classification Hook in Extraction Pipeline

```gherkin
Given the table extraction produces raw rows with entity, metric, period fields
When extract_table_data_adaptive() completes extraction
Then each row is automatically enriched with classification fields:
  - period_type: from classify_period()
  - value_type: from classify_value_type()
  - entity_level: from classify_entity_level()
And classification runs synchronously after row extraction (before unit inference)
And classification adds <20% overhead to extraction time (per Epic 9 AC4)
```

### AC2: Classification Field Population

```gherkin
Given a table row with period="Dec-24", entity="Portugal Cement", metric="Variable Costs"
When classification is applied during extraction
Then the row includes:
  - period_type="monthly_actual" (from period classifier)
  - value_type="actual" (from value type classifier)
  - entity_level="company_only" (from entity level classifier)
And all three fields are populated for every extracted row
And UNKNOWN is used when classification cannot determine type (no NULLs)
```

### AC3: Classification Report Generation

```gherkin
Given a document is being ingested with multiple tables
When all tables are extracted and classified
Then a ClassificationSummary is generated with:
  - period_type_breakdown: counts by PeriodType enum
  - value_type_breakdown: counts by ValueType enum
  - entity_level_breakdown: counts by EntityLevel enum
  - total_rows_classified: count of all rows
  - classification_duration_ms: time spent on classification
And the summary is logged at INFO level for audit trail
And classification reports enable quality monitoring without database queries
```

### AC4: Performance Constraint

```gherkin
Given a document with 100+ table rows
When classification is applied during extraction
Then total classification time is <100ms for 1000 rows
And extraction+classification overhead is <20% vs extraction-only baseline
And memory usage remains O(n) where n is batch size
And batch processing is used for efficiency (classify_*_batch functions)
```

### AC5: Row Dict Schema Extension

```gherkin
Given the current row dict schema from extract_table_data_adaptive:
  {entity, metric, period, fiscal_year, value, unit, ...}
When classification integration is complete
Then row dict includes additional fields:
  - period_type: str (PeriodType.value)
  - value_type: str (ValueType.value)
  - entity_level: str (EntityLevel.value)
And existing fields remain unchanged (backward compatible)
And new fields use string values (not enum objects) for JSON serialization
```

### AC6: Integration with Existing Classifiers

```gherkin
Given the classification modules from Stories 9.2, 9.3, 9.4 exist:
  - raglite/ingestion/classification/period_classifier.py
  - raglite/ingestion/classification/value_type_classifier.py
  - raglite/ingestion/classification/entity_level_classifier.py
When Story 9.5 integration is implemented
Then it uses the existing classify_*() and classify_*_batch() functions
And it does NOT duplicate classification logic
And it coordinates period_type and value_type (BUDGET period_type -> BUDGET value_type)
```

## Tasks / Subtasks

- [ ] Task 1: Create classification integration module (AC: #1, #5, #6)
  - [ ] 1.1: Create `raglite/ingestion/classification/integration.py` module
  - [ ] 1.2: Implement `classify_row(row: dict) -> dict` function that adds classification fields
  - [ ] 1.3: Implement `classify_rows_batch(rows: list[dict]) -> list[dict]` for batch processing
  - [ ] 1.4: Ensure coordination between period_type and value_type classifiers
  - [ ] 1.5: Export functions from `__init__.py`

- [ ] Task 2: Hook classification into extraction pipeline (AC: #1, #2)
  - [ ] 2.1: Modify `raglite/ingestion/adaptive_table/core/api.py` to call classification
  - [ ] 2.2: Call classification after row extraction, before unit inference
  - [ ] 2.3: Ensure all rows have classification fields (no NULLs, use UNKNOWN)
  - [ ] 2.4: Pass extracted row data to classifiers (period, entity fields)

- [ ] Task 3: Implement classification summary generation (AC: #3)
  - [ ] 3.1: Create `ClassificationSummary` dataclass in models.py
  - [ ] 3.2: Implement `generate_classification_summary(rows: list[dict]) -> ClassificationSummary`
  - [ ] 3.3: Log summary at INFO level after each document extraction
  - [ ] 3.4: Include timing metrics (classification_duration_ms)

- [ ] Task 4: Performance optimization (AC: #4)
  - [ ] 4.1: Use batch classification functions for efficiency
  - [ ] 4.2: Add performance benchmark test (1000 rows < 100ms)
  - [ ] 4.3: Profile classification to ensure <20% overhead
  - [ ] 4.4: Document performance characteristics in module docstring

- [ ] Task 5: Unit tests (AC: #1, #2, #3, #4, #5)
  - [ ] 5.1: Create `tests/unit/ingestion/classification/test_integration.py`
  - [ ] 5.2: Test single row classification with all fields populated
  - [ ] 5.3: Test batch classification with mixed period/value/entity types
  - [ ] 5.4: Test UNKNOWN fallback when classification fails
  - [ ] 5.5: Test classification summary generation with expected breakdowns
  - [ ] 5.6: Test performance constraint (1000 rows < 100ms)
  - [ ] 5.7: Ensure 95%+ test coverage per Epic 9 requirements

- [ ] Task 6: Integration tests (AC: #1, #2, #6)
  - [ ] 6.1: Add integration test in `tests/integration/ingestion/test_classification_integration.py`
  - [ ] 6.2: Test end-to-end: extraction -> classification -> row enrichment
  - [ ] 6.3: Verify classification fields present in extracted rows
  - [ ] 6.4: Test with sample PDF from production data

## Dev Notes

### Integration Module Design

The integration module coordinates all three classifiers:

```python
# raglite/ingestion/classification/integration.py

from raglite.ingestion.classification import (
    classify_period,
    classify_value_type,
    classify_entity_level,
    ClassifiedPeriod,
    ClassifiedValueType,
    ClassifiedEntityLevel,
    PeriodType,
    ValueType,
    EntityLevel,
)

def classify_row(row: dict[str, Any]) -> dict[str, Any]:
    """Enrich a table row with classification fields.

    Args:
        row: Table row dict with entity, metric, period fields

    Returns:
        Row dict with added period_type, value_type, entity_level fields
    """
    # Get input values (handle None gracefully)
    period = row.get("period", "") or ""
    entity = row.get("entity", "") or ""

    # Classify period type
    period_result: ClassifiedPeriod = classify_period(period)
    period_type = period_result.period_type

    # Classify value type (uses period_type for coordination)
    value_result: ClassifiedValueType = classify_value_type(
        period=period,
        period_type=period_type
    )

    # Classify entity level
    entity_result: ClassifiedEntityLevel = classify_entity_level(entity)

    # Return enriched row (use enum .value for JSON serialization)
    return {
        **row,
        "period_type": period_type.value,
        "value_type": value_result.value_type.value,
        "entity_level": entity_result.entity_level.value,
    }
```

### Extraction Pipeline Hook Location

Classification should be called in `extract_table_data_adaptive()` after row extraction but before unit inference:

```python
# In raglite/ingestion/adaptive_table/core/api.py

async def extract_table_data_adaptive(...) -> list[dict[str, Any]]:
    # ... existing layout detection and extraction ...

    # Extract based on detected layout
    rows = _extract_table_by_layout(...)

    # NEW: Apply classification to all rows (Story 9.5)
    from raglite.ingestion.classification.integration import classify_rows_batch
    rows = classify_rows_batch(rows)

    # Existing: Apply async context-aware unit inference
    rows = await _apply_context_aware_unit_inference_async(...)

    return rows
```

### Classification Summary Dataclass

```python
@dataclass
class ClassificationSummary:
    """Summary of classification results for a document."""

    total_rows: int
    classification_duration_ms: int

    # Period type breakdown
    period_monthly_actual: int
    period_ytd_actual: int
    period_budget: int
    period_ytd_budget: int
    period_unknown: int

    # Value type breakdown
    value_actual: int
    value_budget: int
    value_forecast: int
    value_variance: int
    value_unknown: int

    # Entity level breakdown
    entity_consolidated: int
    entity_company_only: int
    entity_segment: int
    entity_geographic: int
    entity_unknown: int
```

### Row Dict Schema (Before/After)

**Before (current):**
```python
{
    "entity": "Portugal Cement",
    "metric": "Variable Costs",
    "period": "Dec-24",
    "fiscal_year": 2024,
    "value": 23.5,
    "unit": "EUR/ton",
    "page_number": 12,
    "table_index": 0,
    "table_caption": "Performance Summary",
    "row_index": 5,
    "column_name": "Dec-24",
    "chunk_text": "...",
    "document_id": "2024-12-performance-review"
}
```

**After (with classification):**
```python
{
    "entity": "Portugal Cement",
    "metric": "Variable Costs",
    "period": "Dec-24",
    "fiscal_year": 2024,
    "value": 23.5,
    "unit": "EUR/ton",
    "page_number": 12,
    "table_index": 0,
    "table_caption": "Performance Summary",
    "row_index": 5,
    "column_name": "Dec-24",
    "chunk_text": "...",
    "document_id": "2024-12-performance-review",
    # NEW FIELDS (Story 9.5)
    "period_type": "monthly_actual",
    "value_type": "actual",
    "entity_level": "company_only"
}
```

### Performance Budget

Per Epic 9 AC4: Ingestion time increase <20%

| Operation | Current | With Classification | Overhead |
|-----------|---------|---------------------|----------|
| Row extraction | ~50ms/table | ~50ms/table | 0% |
| Classification | N/A | ~10ms/100 rows | New |
| Unit inference | ~200ms/table | ~200ms/table | 0% |
| **Total** | ~250ms/table | ~260ms/table | **~4%** |

Classification is very fast (regex + lookups) and adds minimal overhead.

### File Size Constraints

Per `.claude/rules/file-size-limits.md`:
- Target: 100-250 LOC per file
- `integration.py` should be ~150 LOC (classify_row, classify_rows_batch, summary generation)

### Test Organization

- Unit tests: `tests/unit/ingestion/classification/test_integration.py`
- Integration tests: `tests/integration/ingestion/test_classification_integration.py` (extend existing)
- Performance tests: Include in unit tests with timing assertions

### Downstream Impact

Story 9.6 (Storage Extension) will:
- Read the new classification fields from row dicts
- Insert into PostgreSQL `financial_tables` columns (added in Story 9.1)

Story 9.8 (Forecasting Query Simplification) will:
- Query by `period_type` directly: `WHERE period_type = 'monthly_actual'`
- Remove period normalization logic from forecasting module

### References

- [Source: raglite/ingestion/classification/] - Classification modules (Stories 9.2-9.4)
- [Source: raglite/ingestion/adaptive_table/core/api.py] - Extraction entry point
- [Source: docs/epics/epic-9-tracking.md] - Epic requirements (<20% overhead)
- [Source: .claude/rules/testing.md] - Test marker requirements
- [Source: .claude/rules/file-size-limits.md] - 500 LOC hard limit

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
