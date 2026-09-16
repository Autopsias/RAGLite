# Story 9.1: Schema Migration - Add Classification Columns

Epic: 9
Status: done
Estimate: 0.5 days

## Story

As a data engineer,
I want to add classification columns to the financial_tables schema,
so that downstream forecasting queries can filter by period_type, value_type, and entity_level without complex normalization logic.

## Acceptance Criteria (BDD Format)

### AC1: period_type Column Addition

```gherkin
Given the financial_tables table exists in PostgreSQL
When Migration 007 is applied
Then a new column period_type VARCHAR(50) is added
And the column is nullable for backward compatibility
And an index idx_period_type is created on the column
```

### AC2: value_type Column Addition

```gherkin
Given the financial_tables table exists in PostgreSQL
When Migration 007 is applied
Then a new column value_type VARCHAR(50) is added
And the column is nullable for backward compatibility
And an index idx_value_type is created on the column
```

### AC3: entity_level Column Addition

```gherkin
Given the financial_tables table exists in PostgreSQL
When Migration 007 is applied
Then a new column entity_level VARCHAR(100) is added
And the column is nullable for backward compatibility
And an index idx_entity_level is created on the column
```

### AC4: Migration Script Idempotency

```gherkin
Given Migration 007 exists in migrations/
When the migration is run multiple times
Then it succeeds without errors (IF NOT EXISTS guards)
And no duplicate columns or indexes are created
```

### AC5: Verification Script

```gherkin
Given Migration 007 has been applied
When running the verification script
Then it confirms all three columns exist
And it confirms all three indexes exist
And it reports the migration status as SUCCESS
```

## Tasks / Subtasks

- [ ] Task 1: Create migration file (AC: AC1.1, AC2.1, AC3.1, AC4.1)
  - [ ] 1.1: Create `migrations/007_add_classification_columns.sql` (AC: AC1.1, AC2.1, AC3.1)
  - [ ] 1.2: Add ALTER TABLE statements with IF NOT EXISTS guards (AC: AC4.1)
  - [ ] 1.3: Add CREATE INDEX statements for all three columns (AC: AC1.1, AC2.1, AC3.1)
  - [ ] 1.4: Add COMMENT statements documenting column purpose (AC: AC1.1, AC2.1, AC3.1)

- [ ] Task 2: Create Python migration runner (AC: AC4.1, AC5.1)
  - [ ] 2.1: Create `migrations/007_add_classification_columns.py` (AC: AC5.1)
  - [ ] 2.2: Implement apply_migration() following 001_apply_schema.py pattern (AC: AC4.1)
  - [ ] 2.3: Add verification checks for column/index existence (AC: AC5.1)
  - [ ] 2.4: Add rollback instructions in comments (AC: AC4.1)

- [ ] Task 3: Unit tests (AC: AC1.1, AC2.1, AC3.1, AC4.1)
  - [ ] 3.1: Create `tests/unit/migrations/test_007_classification_columns.py` (AC: AC1.1, AC2.1, AC3.1)
  - [ ] 3.2: Test migration creates columns correctly (AC: AC1.1, AC2.1, AC3.1)
  - [ ] 3.3: Test migration is idempotent (runs twice without error) (AC: AC4.1)
  - [ ] 3.4: Test verification logic (AC: AC5.1)
  - [ ] 3.5: Ensure test coverage meets 80%+ threshold per quality-gates.md

- [ ] Task 4: Integration test (AC: AC5.1)
  - [ ] 4.1: Add integration test verifying columns exist after migration (AC: AC5.1)
  - [ ] 4.2: Test INSERT with classification fields works (AC: AC1.1, AC2.1, AC3.1)
  - [ ] 4.3: Ensure integration test coverage meets 80%+ threshold per quality-gates.md

## Dev Notes

### Database Schema Extension

Current `financial_tables` schema (from `migrations/002_create_financial_tables.sql`):

| Column | Type | Purpose |
|--------|------|---------|
| document_id | VARCHAR(255) | Source document reference |
| page_number | INT | Source page |
| table_index | INT | Table number on page |
| entity | VARCHAR(255) | Raw entity name |
| entity_normalized | VARCHAR(255) | Normalized entity (from Migration 001) |
| metric | VARCHAR(255) | Financial metric type |
| period | VARCHAR(100) | Period string (raw) |
| fiscal_year | INT | Extracted fiscal year |
| value | DECIMAL(15,2) | Numeric value |
| unit | VARCHAR(50) | Unit of measurement |

**New columns to add:**

| Column | Type | Purpose | Example Values |
|--------|------|---------|----------------|
| period_type | VARCHAR(50) | Classification from PeriodType enum | "monthly_actual", "ytd_actual", "budget", "unknown" |
| value_type | VARCHAR(50) | Data value classification (Story 9.3) | "actual", "budget", "forecast", "variance" |
| entity_level | VARCHAR(100) | Organizational hierarchy level (Story 9.4) | "group", "country", "business_unit", "product_line" |

### Foundation Code Available

From commit `58fbc9e`, the following exists in `raglite/forecasting/timeseries/period_classification.py`:
- `PeriodType` enum with 5 values: MONTHLY_ACTUAL, YTD_ACTUAL, BUDGET, YTD_BUDGET, UNKNOWN (lines 10-16)
- `classify_period()` function for classifying period strings (lines 19-76)
- `ClassificationReport` dataclass for reporting (lines 79-87)

### Migration Pattern Reference

Follow the pattern from `migrations/001_apply_schema.py`:
1. Use `get_postgresql_connection()` from `raglite.shared.clients` (line 8)
2. Use `SafetyGuard` for production protection (lines 13-16)
3. Include verification steps after each ALTER (lines 40-50)
4. Use structured logging with `get_logger(__name__)` (line 10)

**Architecture Reference:**
- [Source: docs/architecture/database-operation-modes.md] - Three-mode database operation system (Mode 3: PRODUCTION DEPLOY for schema migrations)
- Migration deployments require `scripts/deploy-to-production.py --deploy-production` with typed confirmation
- SafetyGuard implementation ensures test fixtures validate test environment before destructive operations
- All migrations must support idempotency via IF NOT EXISTS guards per Section "Rule 2: Production Deletion Requires Explicit Consent"

### Testing Standards

- Unit tests in `tests/unit/migrations/`
- Use pytest fixtures for database setup/teardown
- Mock `get_postgresql_connection()` for unit tests
- Integration tests require `APP_ENV=test` and test database ports (5433)

### Project Structure Notes

- Migration files: `migrations/007_add_classification_columns.sql` and `.py`
- Test files: `tests/unit/migrations/test_007_classification_columns.py`
- Follows existing migration numbering (001-006 already exist)

### References

- [Source: migrations/002_create_financial_tables.sql] - Current schema
- [Source: migrations/001_apply_schema.py] - Migration pattern to follow
- [Source: raglite/forecasting/timeseries/period_classification.py] - PeriodType enum
- [Source: docs/epics/epic-9-tracking.md] - Epic requirements
- [Source: .claude/rules/database-safety.md] - Production protection rules

## Dev Agent Record

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

(No debug logs - story completed without debugging required)

### Completion Notes List

(Story completed successfully on first iteration with comprehensive test coverage)

### File List

- `migrations/007_add_classification_columns.sql`
- `migrations/migration_007_add_classification_columns.py`
- `tests/unit/migrations/test_007_classification_columns.py`
- `tests/integration/test_007_migration_integration.py`
