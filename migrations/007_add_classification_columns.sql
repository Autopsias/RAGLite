-- Migration 007: Add Classification Columns
-- Foundation for Epic 9: Data Quality at Ingestion
-- Adds classification columns to financial_tables for period, value, and entity classification

-- Add period_type column (stores PeriodType enum values)
ALTER TABLE financial_tables
ADD COLUMN IF NOT EXISTS period_type VARCHAR(50);

COMMENT ON COLUMN financial_tables.period_type IS
'Period classification: monthly_actual, ytd_actual, budget, ytd_budget, unknown';

-- Add value_type column (stores ValueType enum values - Story 9.3)
ALTER TABLE financial_tables
ADD COLUMN IF NOT EXISTS value_type VARCHAR(50);

COMMENT ON COLUMN financial_tables.value_type IS
'Value type classification: actual, budget, forecast, variance';

-- Add entity_level column (stores entity hierarchy level - Story 9.4)
ALTER TABLE financial_tables
ADD COLUMN IF NOT EXISTS entity_level VARCHAR(100);

COMMENT ON COLUMN financial_tables.entity_level IS
'Entity hierarchy level: group, country, business_unit, product_line';

-- Create indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_period_type ON financial_tables(period_type);
CREATE INDEX IF NOT EXISTS idx_value_type ON financial_tables(value_type);
CREATE INDEX IF NOT EXISTS idx_entity_level ON financial_tables(entity_level);

-- Verification queries
-- Check columns exist:
-- SELECT column_name, data_type, character_maximum_length, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'financial_tables'
--   AND column_name IN ('period_type', 'value_type', 'entity_level');

-- Check indexes exist:
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'financial_tables'
--   AND indexname IN ('idx_period_type', 'idx_value_type', 'idx_entity_level');
