# Story 7b-4: Model Selection Cache in PostgreSQL

Status: Drafted

## Story Header

- **Epic:** 7b - Intelligent Model Selection Framework
- **Priority:** P0
- **Effort:** 1 day
- **Status:** drafted
- **Dependencies:** 7b-3 (Per-Variable Model Selection via Cross-Validation) - provides ModelSelectionResult

## User Story

As a forecasting system,
I want to cache model selection results in PostgreSQL with efficient lookups,
so that MCP query-time forecast generation can quickly retrieve the optimal model without re-running cross-validation.

## Background

Story 7b-3 implements per-variable model selection via cross-validation, producing `ModelSelectionResult` dataclass instances. This story caches those results in PostgreSQL to enable:
1. Fast (<100ms) lookup during MCP query execution
2. 7-day TTL with automatic expiration to ensure freshness
3. Manual invalidation for forced refresh scenarios

## Acceptance Criteria

### AC-7b.4.1: New `model_selection` PostgreSQL table

**Given** the RAGLite database is running on PostgreSQL
**When** the migration script `006_add_model_selection.sql` is applied
**Then** a new `model_selection` table exists with the following columns:
  - `id`: SERIAL PRIMARY KEY
  - `variable_name`: VARCHAR(100) NOT NULL UNIQUE
  - `best_model`: VARCHAR(50) NOT NULL
  - `best_mape`: NUMERIC(8,4) NOT NULL
  - `best_mase`: NUMERIC(8,4)
  - `use_regressors`: BOOLEAN DEFAULT FALSE
  - `regressor_list`: JSONB
  - `candidate_results`: JSONB
  - `data_characteristics`: JSONB
  - `selected_at`: TIMESTAMP DEFAULT NOW()
  - `expires_at`: TIMESTAMP NOT NULL

**And** appropriate indexes are created:
  - `idx_model_selection_variable` on `variable_name`
  - `idx_model_selection_expires` on `expires_at`

**Verification:**
- Migration script applies without errors
- Table structure matches specification
- Indexes are created and visible in `\di`

### AC-7b.4.2: Store best_model, regressors, MAPE, MASE per variable

**Given** a `ModelSelectionResult` from Story 7b-3 is available
**When** `cache_model_selection(result: ModelSelectionResult)` is called
**Then** the result is stored in the `model_selection` table with:
  - `variable_name`: From `result.variable_name`
  - `best_model`: From `result.best_model`
  - `best_mape`: From `result.best_mape`
  - `best_mase`: From `result.best_mase`
  - `use_regressors`: From `result.best_with_regressors`
  - `regressor_list`: JSON array from `result.best_regressor_set`
  - `candidate_results`: JSON serialization of `result.candidate_results`
  - `data_characteristics`: JSON serialization of `result.data_characteristics`
  - `selected_at`: Current timestamp
  - `expires_at`: Current timestamp + 7 days

**And** if a record for the variable already exists, it is replaced (upsert behavior)

**Verification:**
- Record is inserted/updated in database
- All fields correctly populated
- Upsert works for re-running model selection

### AC-7b.4.3: `get_cached_model_selection()` with <100ms lookup

**Given** a cached model selection exists for variable "ebitda"
**When** `get_cached_model_selection("ebitda")` is called
**Then** the function returns a `CachedModelSelection` object within 100ms containing:
  - `variable_name`: "ebitda"
  - `best_model`: The cached best model name
  - `best_mape`: The cached MAPE score
  - `best_mase`: The cached MASE score
  - `use_regressors`: Boolean flag
  - `regressor_list`: List of regressor names
  - `is_expired`: False (if within TTL)
  - `selected_at`: Original selection timestamp
  - `expires_at`: Expiration timestamp

**And** if no cached result exists, returns `None`

**And** if cached result is expired (past `expires_at`), returns result with `is_expired=True`

**Verification:**
- Performance test confirms <100ms lookup time
- Returns None for uncached variables
- Correctly identifies expired entries

### AC-7b.4.4: `invalidate_model_selection()` for manual refresh

**Given** a cached model selection exists for variable "ebitda"
**When** `invalidate_model_selection("ebitda")` is called
**Then** the cache entry for "ebitda" is deleted from the `model_selection` table

**And** when `invalidate_model_selection(None)` or `invalidate_all_model_selections()` is called
**Then** all cache entries are deleted

**Verification:**
- Single variable invalidation works
- All-variable invalidation works
- Subsequent lookup returns None after invalidation

### AC-7b.4.5: 7-day TTL with automatic expiration

**Given** a model selection result is cached for variable "revenue"
**When** the cache entry is created
**Then** `expires_at` is set to `selected_at + 7 days`

**And** when querying expired entries, `is_expired=True` is returned

**And** an optional cleanup function `cleanup_expired_model_selections()` removes all entries where `expires_at < NOW()`

**Verification:**
- TTL is correctly set to 7 days
- Expired entries are flagged correctly
- Cleanup function removes expired entries

### AC-7b.4.6: Migration script

**Given** the RAGLite PostgreSQL database is running
**When** the migration script `migrations/006_add_model_selection.sql` is executed
**Then** the `model_selection` table and indexes are created successfully
**And** the migration is idempotent (can be run multiple times without error)

**Verification:**
- Migration runs on fresh database
- Migration runs on existing database without errors
- Schema matches specification

## Technical Specification

### Database Schema

```sql
-- migrations/006_add_model_selection.sql

CREATE TABLE IF NOT EXISTS model_selection (
    id SERIAL PRIMARY KEY,
    variable_name VARCHAR(100) NOT NULL UNIQUE,
    best_model VARCHAR(50) NOT NULL,
    best_mape NUMERIC(8,4) NOT NULL,
    best_mase NUMERIC(8,4),
    use_regressors BOOLEAN DEFAULT FALSE,
    regressor_list JSONB,
    candidate_results JSONB,
    data_characteristics JSONB,
    selected_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_model_selection_variable ON model_selection(variable_name);
CREATE INDEX IF NOT EXISTS idx_model_selection_expires ON model_selection(expires_at);
```

### ORM Model

```python
# In raglite/external_data/orm_models.py

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB

class ModelSelection(Base):
    """ORM model for cached model selection results."""

    __tablename__ = "model_selection"

    id = Column(Integer, primary_key=True)
    variable_name = Column(String(100), nullable=False, unique=True, index=True)
    best_model = Column(String(50), nullable=False)
    best_mape = Column(Numeric(8, 4), nullable=False)
    best_mase = Column(Numeric(8, 4))
    use_regressors = Column(Boolean, default=False)
    regressor_list = Column(JSONB)
    candidate_results = Column(JSONB)
    data_characteristics = Column(JSONB)
    selected_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
```

### Cache Methods

```python
# In raglite/external_data/storage.py

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

MODEL_SELECTION_TTL_DAYS = 7


@dataclass
class CachedModelSelection:
    """Cached model selection result for MCP query-time lookup."""

    variable_name: str
    best_model: str
    best_mape: float
    best_mase: float
    use_regressors: bool
    regressor_list: list[str]
    candidate_results: dict | None
    data_characteristics: dict | None
    selected_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


async def cache_model_selection(result: ModelSelectionResult) -> None:
    """Cache model selection result in PostgreSQL.

    Performs upsert - replaces existing entry if present.

    Args:
        result: ModelSelectionResult from Story 7b-3
    """
    # Implementation: Insert or update model_selection table
    ...


async def get_cached_model_selection(variable_name: str) -> Optional[CachedModelSelection]:
    """Retrieve cached model selection for variable.

    Args:
        variable_name: Name of the variable to look up

    Returns:
        CachedModelSelection if found, None otherwise
    """
    # Implementation: Query model_selection table by variable_name
    ...


async def invalidate_model_selection(variable_name: str | None = None) -> int:
    """Invalidate cached model selection(s).

    Args:
        variable_name: Variable to invalidate, or None for all

    Returns:
        Number of entries deleted
    """
    # Implementation: Delete from model_selection table
    ...


async def cleanup_expired_model_selections() -> int:
    """Remove all expired model selection cache entries.

    Returns:
        Number of entries deleted
    """
    # Implementation: DELETE WHERE expires_at < NOW()
    ...
```

### Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| migrations/006_add_model_selection.sql | Create | +20 |
| raglite/external_data/orm_models.py | Add ModelSelection ORM | +40 |
| raglite/external_data/storage.py | Add cache methods | +100 |
| tests/unit/test_model_selection_cache.py | Create unit tests | +150 |
| tests/integration/test_model_selection_cache.py | Create integration tests | +100 |

## Tasks

- [ ] Task 1: Create migration script (AC-7b.4.1, AC-7b.4.6)
  - [ ] 1.1 Create `migrations/006_add_model_selection.sql`
  - [ ] 1.2 Define table schema with all required columns
  - [ ] 1.3 Add indexes for variable_name and expires_at
  - [ ] 1.4 Test migration on fresh and existing databases

- [ ] Task 2: Add ORM model to orm_models.py (AC-7b.4.1, AC-7b.4.2)
  - [ ] 2.1 Add imports for JSONB, DateTime, func
  - [ ] 2.2 Create ModelSelection class with SQLAlchemy columns
  - [ ] 2.3 Add table indexes via Column parameters or __table_args__
  - [ ] 2.4 Verify ORM matches migration schema

- [ ] Task 3: Create CachedModelSelection dataclass (AC-7b.4.3)
  - [ ] 3.1 Define CachedModelSelection in storage.py
  - [ ] 3.2 Add is_expired property
  - [ ] 3.3 Add docstrings and type hints

- [ ] Task 4: Implement cache_model_selection() (AC-7b.4.2, AC-7b.4.5)
  - [ ] 4.1 Add function signature and docstring
  - [ ] 4.2 Calculate expires_at as selected_at + 7 days
  - [ ] 4.3 Serialize data_characteristics to JSON
  - [ ] 4.4 Implement upsert logic (INSERT ON CONFLICT UPDATE)
  - [ ] 4.5 Add structured logging

- [ ] Task 5: Implement get_cached_model_selection() (AC-7b.4.3)
  - [ ] 5.1 Add function signature and docstring
  - [ ] 5.2 Query by variable_name
  - [ ] 5.3 Return None if not found
  - [ ] 5.4 Convert ORM object to CachedModelSelection dataclass
  - [ ] 5.5 Ensure <100ms performance (indexed query)

- [ ] Task 6: Implement invalidate_model_selection() (AC-7b.4.4)
  - [ ] 6.1 Add function signature and docstring
  - [ ] 6.2 Handle single variable deletion
  - [ ] 6.3 Handle all-variable deletion (variable_name=None)
  - [ ] 6.4 Return count of deleted entries

- [ ] Task 7: Implement cleanup_expired_model_selections() (AC-7b.4.5)
  - [ ] 7.1 Add function signature and docstring
  - [ ] 7.2 Delete where expires_at < NOW()
  - [ ] 7.3 Return count of deleted entries

- [ ] Task 8: Write unit tests (AC-7b.4.2, AC-7b.4.3, AC-7b.4.4, AC-7b.4.5)
  - [ ] 8.1 Create tests/unit/test_model_selection_cache.py
  - [ ] 8.2 Test CachedModelSelection dataclass and is_expired
  - [ ] 8.3 Mock database calls for cache methods
  - [ ] 8.4 Test TTL calculation logic

- [ ] Task 9: Write integration tests (AC-7b.4.1, AC-7b.4.3, AC-7b.4.6)
  - [ ] 9.1 Create tests/integration/test_model_selection_cache.py
  - [ ] 9.2 Test migration applies correctly
  - [ ] 9.3 Test cache_model_selection with real database
  - [ ] 9.4 Test get_cached_model_selection with real database
  - [ ] 9.5 Test invalidate_model_selection with real database
  - [ ] 9.6 Performance test for <100ms lookup

- [ ] Task 10: Validation (MANDATORY)
  - [ ] 10.1 Run unit tests: `uv run pytest tests/unit/test_model_selection_cache.py -v`
  - [ ] 10.2 Run integration tests: `uv run pytest tests/integration/test_model_selection_cache.py -v`
  - [ ] 10.3 Apply migration to test database
  - [ ] 10.4 Verify <100ms lookup performance
  - [ ] 10.5 Test upsert behavior with repeated caching

## Dev Notes

### Architecture References

- [Source: docs/prd/epic-7-intelligent-model-selection.md#Story 7.4]
- [Source: docs/architecture/5-technology-stack-definitive.md]
- [Source: raglite/external_data/orm_models.py] - Existing ORM patterns
- [Source: raglite/external_data/storage.py] - Existing storage methods
- [Source: raglite/forecasting/model_selection.py] - Story 7b-3 ModelSelectionResult

### Existing Patterns to Follow

**ORM Model Pattern (orm_models.py):**
```python
class ExternalDataRecord(Base):
    __tablename__ = "external_data"

    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False, index=True)
    value = Column(Float, nullable=False)
    # ... etc
```

**Async Storage Pattern (storage.py):**
```python
async def store_external_data(data: ExternalDataInput) -> int:
    """Store external data in PostgreSQL."""
    async with get_async_session() as session:
        record = ExternalDataRecord(...)
        session.add(record)
        await session.commit()
        return record.id
```

### Key Technical Details

1. **Upsert Strategy:**
   - Use PostgreSQL's `INSERT ... ON CONFLICT (variable_name) DO UPDATE`
   - SQLAlchemy: `insert(...).on_conflict_do_update()`

2. **Performance Optimization:**
   - Index on `variable_name` ensures <100ms lookup
   - JSONB for flexible storage of complex nested objects
   - Avoid loading candidate_results unless needed (optional lazy load)

3. **TTL Implementation:**
   - Calculate `expires_at = selected_at + timedelta(days=7)`
   - Check `is_expired` property on read
   - Cleanup job can run periodically or on-demand

4. **Data Characteristics Serialization:**
   - `DataCharacteristics` from Story 7b-2 is a dataclass
   - Use `dataclasses.asdict()` for JSON serialization
   - Handle None values gracefully

### Database Ports

- **Production:** PostgreSQL port 5432
- **Test:** PostgreSQL port 5433
- Tests MUST use test database (port 5433) per database-safety.md

### Performance Budget

| Operation | Target Time |
|-----------|-------------|
| get_cached_model_selection() | <100ms |
| cache_model_selection() | <500ms |
| invalidate_model_selection() | <200ms |
| cleanup_expired_model_selections() | <1s |

### NFRs

- **Query Time:** <100ms for cache lookup (indexed)
- **Availability:** Cache miss should not block forecasting (fallback to Prophet)
- **Test Coverage:** 80%+ for new code
- **Data Integrity:** UNIQUE constraint on variable_name prevents duplicates

## Testing Requirements

### Unit Tests (tests/unit/test_model_selection_cache.py)

- Test CachedModelSelection dataclass creation
- Test is_expired property with various timestamps
- Test TTL calculation (7 days from selected_at)
- Mock database interactions for cache methods
- Test JSON serialization of data_characteristics

### Integration Tests (tests/integration/test_model_selection_cache.py)

- Test migration applies to test database (port 5433)
- Test cache_model_selection() stores correctly
- Test get_cached_model_selection() retrieves correctly
- Test upsert behavior (update existing entry)
- Test invalidate_model_selection() for single and all
- Test cleanup_expired_model_selections()
- Performance test: lookup < 100ms

### Validation Checklist

```bash
# Apply migration to test database
docker exec raglite-postgresql-test psql -U raglite -d raglite -f migrations/006_add_model_selection.sql

# Unit tests
uv run pytest tests/unit/test_model_selection_cache.py -v

# Integration tests (uses port 5433)
APP_ENV=test uv run pytest tests/integration/test_model_selection_cache.py -v

# Performance test
uv run pytest tests/integration/test_model_selection_cache.py -v -k "performance"

# Verify table created
docker exec raglite-postgresql-test psql -U raglite -d raglite -c "\d model_selection"

# Verify indexes created
docker exec raglite-postgresql-test psql -U raglite -d raglite -c "\di idx_model_selection*"
```

## Definition of Done

- [ ] All 6 acceptance criteria verified with passing tests
- [ ] Migration script creates table and indexes
- [ ] ORM model matches schema
- [ ] All cache methods implemented and tested
- [ ] Unit tests passing with 80%+ coverage on new code
- [ ] Integration tests passing on test database
- [ ] Performance test confirms <100ms lookup
- [ ] Code follows existing orm_models.py and storage.py patterns
- [ ] Docstrings added to all public functions
- [ ] Ready for Story 7b-5 (Slash Commands) and Story 7b-6 (MCP Integration)

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

(To be filled during implementation)

### Debug Log References

N/A

### Completion Notes List

(To be filled during implementation)

### File List

**To Create:**
- `migrations/006_add_model_selection.sql` - Database migration
- `tests/unit/test_model_selection_cache.py` - Unit tests
- `tests/integration/test_model_selection_cache.py` - Integration tests

**To Modify:**
- `raglite/external_data/orm_models.py` - Add ModelSelection ORM model
- `raglite/external_data/storage.py` - Add cache methods

**To Reference:**
- `raglite/forecasting/model_selection.py` - Story 7b-3 ModelSelectionResult
- `raglite/forecasting/data_analyzer.py` - Story 7b-2 DataCharacteristics

### Change Log

- 2025-12-21: Story drafted with all 6 acceptance criteria in BDD format
