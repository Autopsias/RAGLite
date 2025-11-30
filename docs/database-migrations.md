# Database Migrations

This document tracks all database schema changes and data migrations applied to RAGLite.

## Migration History

### Migration 001: Backfill fiscal_year from period Column

**Date:** 2025-11-28
**Story:** 5.0.1 - Fix Time-Series Period Extraction for Forecasting
**Type:** Data Migration (Backfill)
**Database:** PostgreSQL `financial_tables`

#### Purpose

Populate the `fiscal_year` column by parsing year values from the `period` column to enable time-series forecasting queries.

#### Problem Statement

During Epic 4 UAT testing, the `get_financial_forecast` MCP tool failed because time-series extraction could not find temporal metadata. The root cause was:
- The `fiscal_year` column was only 3.6% populated (14,022 rows)
- The `period` column was 89% populated (344,316 rows) with values like "Jan-25", "Feb-24"
- However, only ~36% of period values (124,644 rows) have parseable Mon-YY format
- The remaining 64% contain non-date values like "Var.", "YTD", "% LY", etc.

#### Migration Script

**File:** `scripts/migrations/001_backfill_fiscal_year.sql`

**Logic:**
```sql
UPDATE financial_tables
SET fiscal_year = 2000 + (regexp_match(period, '.*-(\d{2})$'))[1]::int
WHERE period IS NOT NULL
  AND period ~ '-\d{2}$'        -- Filter for valid Mon-YY format
  AND fiscal_year IS NULL;      -- Only update NULL values
```

**Regex Pattern:** `.*-(\d{2})$`
- Matches period values ending with a hyphen and 2 digits (e.g., "Jan-25", "Dec-24")
- Extracts the 2-digit year and adds 2000 to get full year
- Safely ignores rows with non-date period values ("Var.", "YTD", etc.)

#### Expected Impact

**Before Migration:**
- Total rows: 386,466
- Rows with period: 344,316 (89%)
- Rows with fiscal_year: 14,022 (3.6%)

**After Migration:**
- Total rows: 386,466 (unchanged)
- Rows with period: 344,316 (unchanged)
- Rows with fiscal_year: 138,666 (35.9%) - **increase of 124,644 rows**

**Note:** The migration updates only 36% of rows with period populated because 64% contain non-parseable values like "Var.", "YTD", "% LY", "Month", etc. This is expected and correct behavior.

#### Rollback Procedure

**WARNING:** Rollback will delete all backfilled fiscal_year values. Only use if migration failed.

```sql
UPDATE financial_tables
SET fiscal_year = NULL
WHERE period IS NOT NULL
  AND period ~ '-\d{2}$'
  AND fiscal_year = 2000 + (regexp_match(period, '.*-(\d{2})$'))[1]::int;
```

#### Verification

**Pre-migration check:**
```sql
SELECT
    COUNT(*) as total_rows,
    COUNT(CASE WHEN period IS NOT NULL THEN 1 END) as rows_with_period,
    COUNT(CASE WHEN fiscal_year IS NOT NULL THEN 1 END) as rows_with_fiscal_year
FROM financial_tables;
```

**Post-migration check:**
```sql
SELECT
    COUNT(*) as total_rows,
    COUNT(CASE WHEN period IS NOT NULL THEN 1 END) as rows_with_period,
    COUNT(CASE WHEN fiscal_year IS NOT NULL THEN 1 END) as rows_with_fiscal_year
FROM financial_tables;
```

**Sample data verification:**
```sql
SELECT period, fiscal_year, metric, value
FROM financial_tables
WHERE period IS NOT NULL AND fiscal_year IS NOT NULL
LIMIT 20;
```

#### Execution Notes

**Environment:** Production database (port 5432)
**Execution date:** 2025-11-28 20:10:04 UTC
**Execution time:** <2 seconds
**Backup created:** backups/pre-migration-001-20251128-201004.backup (7.6MB)
**Rows affected:** 124,644 rows updated
**Status:** ✅ COMPLETED

**Results:**
- Before: 14,022 rows with fiscal_year (3.6%)
- After: 138,666 rows with fiscal_year (35.9%)
- Increase: 124,644 rows (+988%)

**Verification:**
- Sample data shows correct extraction: "YTD 2025" → 2025, "FY 2024" → 2024, "Real 2023" → 2023
- All updates wrapped in transaction and committed successfully
- No errors during execution

#### Related Changes

- New function: `extract_timeseries_from_sql()` in `raglite/forecasting/timeseries_extract.py`
- Modified MCP tool: `get_financial_forecast()` in `raglite/main.py`
- Integration tests: `tests/integration/test_forecast_query_integration.py`

#### References

- Story file: `docs/stories/5-0-1-fix-timeseries-period-extraction.md`
- Epic 4 UAT bug: BUG-E4-001
- Database schema: PostgreSQL `financial_tables` table (Story 2.6)
- Database safety: Story 4.0.7 database operation modes

---

## Migration Conventions

### File Naming

Format: `NNN_description.sql` where NNN is a 3-digit sequence number

Examples:
- `001_backfill_fiscal_year.sql`
- `002_add_document_category_column.sql`

### Migration Script Structure

All migration scripts should include:

1. **Header comment block**
   - Migration number
   - Creation date
   - Story reference
   - Purpose
   - Expected impact

2. **Pre-migration verification** (SELECT queries to check current state)

3. **Migration logic** (UPDATE/INSERT/ALTER statements with comments)

4. **Post-migration verification** (SELECT queries to validate success)

5. **Rollback procedure** (commented out, with WARNING)

### Execution Safety

**CRITICAL:** All production database migrations MUST follow Story 4.0.7 database safety protocols:

1. **Test first:** Run migration in transaction with ROLLBACK on development/test database
2. **Backup:** Run `pg_dump` before applying to production
3. **Transaction:** Wrap UPDATE/INSERT in BEGIN/COMMIT block
4. **Verification:** Run post-migration checks to confirm success
5. **Documentation:** Update this file with execution notes (date, time, rows affected, status)

### Database Operation Modes

- **TEST mode** (port 5433): Safe for testing migrations, can delete data
- **PRODUCTION mode** (port 5432): Requires `SafetyGuard` validation, backups mandatory
- **DEPLOY mode:** Use `scripts/deploy-to-production.py` for schema changes requiring `--force-data-loss` flag

---

## Future Migrations

*Migrations to be added as they are created*
