-- Migration 001: Backfill fiscal_year from period column
-- Created: 2025-11-28
-- Story: 5.0.1 - Fix Time-Series Period Extraction for Forecasting
-- Purpose: Populate fiscal_year column by parsing year from period (e.g., "Jan-25" → 2025)
--
-- Expected impact: ~300,000+ rows updated (89% of 344,316 rows with period populated)
-- Rollback: Set fiscal_year = NULL WHERE period IS NOT NULL (not recommended)

-- ============================================================================
-- Pre-migration verification
-- ============================================================================
-- Run this BEFORE the migration to see current state
SELECT
    COUNT(*) as total_rows,
    COUNT(CASE WHEN period IS NOT NULL THEN 1 END) as rows_with_period,
    COUNT(CASE WHEN fiscal_year IS NOT NULL THEN 1 END) as rows_with_fiscal_year_before,
    COUNT(CASE WHEN period IS NOT NULL AND fiscal_year IS NULL THEN 1 END) as rows_to_update
FROM financial_tables;

-- Expected output:
-- total_rows: 386,466
-- rows_with_period: 344,316
-- rows_with_fiscal_year_before: 14,022
-- rows_to_update: ~330,000

-- ============================================================================
-- Migration: Backfill fiscal_year from period
-- ============================================================================
-- Pattern explanation:
-- - period format: "Jan-25", "Feb-24", "Dec-23", etc.
-- - Regex: '.*-(\d{2})$' extracts the 2-digit year at the end
-- - Result: (regexp_match(period, '.*-(\d{2})$'))[1] returns "25", "24", "23"
-- - Convert to integer and add 2000 to get full year: 2000 + 25 = 2025

UPDATE financial_tables
SET fiscal_year = 2000 + (regexp_match(period, '.*-(\d{2})$'))[1]::int
WHERE period IS NOT NULL
  AND period ~ '-\d{2}$'        -- Only update rows with valid period format (ends with -XX)
  AND fiscal_year IS NULL;      -- Only update NULL fiscal_year to preserve any existing data

-- ============================================================================
-- Post-migration verification
-- ============================================================================
-- Run this AFTER the migration to verify success
SELECT
    COUNT(*) as total_rows,
    COUNT(CASE WHEN period IS NOT NULL THEN 1 END) as rows_with_period,
    COUNT(CASE WHEN fiscal_year IS NOT NULL THEN 1 END) as rows_with_fiscal_year_after,
    COUNT(CASE WHEN period IS NOT NULL AND fiscal_year IS NULL THEN 1 END) as rows_still_null
FROM financial_tables;

-- Expected output after migration:
-- total_rows: 386,466
-- rows_with_period: 344,316
-- rows_with_fiscal_year_after: ~320,000+ (was 14,022, should increase by ~300,000)
-- rows_still_null: ~24,000 (rows with invalid period format, e.g., quarterly values)

-- ============================================================================
-- Sample data verification
-- ============================================================================
-- Verify a few sample rows to ensure parsing worked correctly
SELECT
    period,
    fiscal_year,
    metric,
    value
FROM financial_tables
WHERE period IS NOT NULL AND fiscal_year IS NOT NULL
LIMIT 20;

-- ============================================================================
-- Rollback procedure (if needed)
-- ============================================================================
-- WARNING: This will DELETE all backfilled fiscal_year values
-- Only run if migration failed and you need to reset
--
-- UPDATE financial_tables
-- SET fiscal_year = NULL
-- WHERE period IS NOT NULL
--   AND period ~ '-\d{2}$'
--   AND fiscal_year = 2000 + (regexp_match(period, '.*-(\d{2})$'))[1]::int;
