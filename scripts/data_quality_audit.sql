-- ============================================================================
-- RAGLite Data Quality Audit SQL Scripts
-- Date: 2026-01-27
-- Purpose: Audit and cleanup data quality issues in financial_tables
-- ============================================================================

-- ============================================================================
-- SECTION 1: AUDIT QUERIES (Read-Only)
-- ============================================================================

-- 1.1 Summary Statistics
SELECT 'Summary Statistics' as section;
SELECT
    COUNT(*) as total_rows,
    SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END) as null_values,
    SUM(CASE WHEN unit IS NULL OR unit = '' THEN 1 ELSE 0 END) as missing_units,
    SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) as negatives,
    COUNT(DISTINCT unit) as unique_units,
    COUNT(DISTINCT metric) as unique_metrics,
    COUNT(DISTINCT entity_normalized) as unique_entities
FROM financial_tables;

-- 1.2 EBITDA Quality by Entity
SELECT 'EBITDA Quality by Entity' as section;
SELECT
    entity_normalized,
    COUNT(*) as records,
    COUNT(DISTINCT unit) as unit_variants,
    SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) as negatives,
    ROUND(MIN(value)::numeric, 2) as min_val,
    ROUND(MAX(value)::numeric, 2) as max_val,
    ROUND(AVG(value)::numeric, 2) as avg_val
FROM financial_tables
WHERE LOWER(metric) LIKE '%ebitda%'
GROUP BY entity_normalized
ORDER BY records DESC
LIMIT 20;

-- 1.3 Unit Distribution for Key Metrics
SELECT 'Unit Distribution for Key Metrics' as section;
SELECT
    metric,
    unit,
    COUNT(*) as count,
    ROUND(MIN(value)::numeric, 2) as min_val,
    ROUND(MAX(value)::numeric, 2) as max_val
FROM financial_tables
WHERE metric IN ('EBITDA', 'EBITDA IFRS', 'Turnover', 'Revenue', 'CAPEX', 'Variable Cost')
GROUP BY metric, unit
ORDER BY metric, count DESC
LIMIT 50;

-- 1.4 Negative Value Analysis
SELECT 'Negative Value Analysis' as section;
SELECT
    metric,
    COUNT(*) as total,
    SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) as negatives,
    ROUND(100.0 * SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as pct_negative
FROM financial_tables
WHERE metric IS NOT NULL
GROUP BY metric
HAVING SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) > 10
ORDER BY pct_negative DESC
LIMIT 20;

-- 1.5 Entity Contamination Check
SELECT 'Entity Contamination Check' as section;
SELECT entity_normalized, COUNT(*) as rows
FROM financial_tables
WHERE entity_normalized LIKE '%CF%'
   OR entity_normalized LIKE '%interest%'
   OR entity_normalized LIKE '%Working Capital%'
   OR entity_normalized LIKE '%expense%'
GROUP BY entity_normalized
ORDER BY rows DESC;

-- 1.6 Malformed Unit Detection
SELECT 'Malformed Unit Detection' as section;
SELECT unit, COUNT(*) as count
FROM financial_tables
WHERE unit ~ '[#@!()]'
   OR unit ~ '^-?[0-9]+\.?[0-9]*$'
   OR unit ~ '^[A-Z][a-z]{2}-[0-9]{2}$'
GROUP BY unit
ORDER BY count DESC
LIMIT 30;

-- 1.7 Fiscal Year Distribution
SELECT 'Fiscal Year Distribution' as section;
SELECT
    fiscal_year,
    COUNT(*) as rows,
    CASE
        WHEN fiscal_year > 2025 THEN 'FUTURE/INVALID'
        WHEN fiscal_year < 2020 THEN 'HISTORICAL'
        ELSE 'VALID'
    END as status
FROM financial_tables
WHERE fiscal_year IS NOT NULL
GROUP BY fiscal_year
ORDER BY fiscal_year;

-- ============================================================================
-- SECTION 2: ENTITY CONTAMINATION CLEANUP
-- ============================================================================

-- 2.1 Create audit table for entity contamination
-- Uncomment to execute
/*
CREATE TABLE IF NOT EXISTS entity_contamination_audit AS
SELECT
    id,
    document_id,
    metric,
    entity_normalized,
    column_name,
    fiscal_year,
    value,
    unit,
    NOW() as audit_date
FROM financial_tables
WHERE entity_normalized IN (
    'CF from Operations',
    'Net interest expenses',
    'De(in)crease Trade Working Capital',
    'CF from Operating Activities',
    'Other Working Capital Variances',
    'Trade Working Capital'
)
OR entity_normalized LIKE '%interest%'
OR entity_normalized LIKE '%expense%'
OR (entity_normalized LIKE '%Working Capital%' AND entity_normalized NOT LIKE '%Trade Working Capital/Turnover%');
*/

-- 2.2 Count contaminated rows
SELECT 'Entity Contamination Count' as section;
SELECT COUNT(*) as contaminated_rows
FROM financial_tables
WHERE entity_normalized IN (
    'CF from Operations',
    'Net interest expenses',
    'De(in)crease Trade Working Capital',
    'CF from Operating Activities',
    'Other Working Capital Variances',
    'Trade Working Capital'
);

-- 2.3 Option A: Set entity to NULL (preserve data, remove from aggregations)
-- Uncomment to execute
/*
UPDATE financial_tables
SET entity_normalized = NULL
WHERE entity_normalized IN (
    'CF from Operations',
    'Net interest expenses',
    'De(in)crease Trade Working Capital',
    'CF from Operating Activities',
    'Other Working Capital Variances',
    'Trade Working Capital'
);
*/

-- ============================================================================
-- SECTION 3: MALFORMED UNIT CLEANUP
-- ============================================================================

-- 3.1 Audit malformed units
SELECT 'Malformed Units Summary' as section;
SELECT
    CASE
        WHEN unit ~ '[#@!()]' THEN 'SYMBOL_CORRUPTION'
        WHEN unit ~ '^-?[0-9]+\.?[0-9]*$' THEN 'NUMERIC_IN_UNIT'
        WHEN unit ~ '^[A-Z][a-z]{2}-[0-9]{2}$' THEN 'PERIOD_IN_UNIT'
        ELSE 'OTHER'
    END as corruption_type,
    COUNT(*) as count
FROM financial_tables
WHERE unit ~ '[#@!()]'
   OR unit ~ '^-?[0-9]+\.?[0-9]*$'
   OR unit ~ '^[A-Z][a-z]{2}-[0-9]{2}$'
GROUP BY 1
ORDER BY count DESC;

-- 3.2 Set malformed units to NULL (for later inference)
-- Uncomment to execute
/*
UPDATE financial_tables
SET unit = NULL
WHERE unit ~ '[#@!()]'
   OR unit ~ '^-?[0-9]+\.?[0-9]*$'
   OR unit ~ '^[A-Z][a-z]{2}-[0-9]{2}$';
*/

-- ============================================================================
-- SECTION 4: INVALID FISCAL YEAR CLEANUP
-- ============================================================================

-- 4.1 Audit invalid fiscal years
SELECT 'Invalid Fiscal Years' as section;
SELECT fiscal_year, COUNT(*) as rows
FROM financial_tables
WHERE fiscal_year > 2026 OR fiscal_year < 2015
GROUP BY fiscal_year
ORDER BY fiscal_year;

-- 4.2 Delete clearly invalid rows (2030, 2045)
-- Uncomment to execute
/*
DELETE FROM financial_tables
WHERE fiscal_year IN (2030, 2045);
*/

-- ============================================================================
-- SECTION 5: UNIT NORMALIZATION MAPPING
-- ============================================================================

-- 5.1 Create unit normalization lookup table
-- Uncomment to execute
/*
CREATE TABLE IF NOT EXISTS unit_normalization_map (
    raw_unit VARCHAR(100) PRIMARY KEY,
    normalized_unit VARCHAR(20),
    multiplier DECIMAL(20, 6),
    notes TEXT
);

INSERT INTO unit_normalization_map (raw_unit, normalized_unit, multiplier, notes) VALUES
-- Standard EUR variants
('EUR', 'EUR', 1.0, 'Base currency'),
('€', 'EUR', 1.0, 'Symbol variant'),
('Euro', 'EUR', 1.0, 'Text variant'),

-- Thousands
('K EUR', 'EUR', 1000.0, 'Thousands'),
('KEUR', 'EUR', 1000.0, 'Thousands compact'),
('kEUR', 'EUR', 1000.0, 'Thousands lowercase'),
('1000 EUR', 'EUR', 1000.0, 'Explicit thousands'),

-- Millions
('M EUR', 'EUR', 1000000.0, 'Millions'),
('MEUR', 'EUR', 1000000.0, 'Millions compact'),
('Meur', 'EUR', 1000000.0, 'Millions mixed case'),
('M€', 'EUR', 1000000.0, 'Millions symbol'),

-- Percentages (no conversion)
('%', 'PCT', 1.0, 'Percentage'),
('pp', 'PP', 1.0, 'Percentage points'),
('% LY', 'PCT_LY', 1.0, 'Percent vs last year'),

-- Volume units (no conversion)
('kton', 'KTON', 1.0, 'Kilotons'),
('km3', 'KM3', 1.0, 'Cubic kilometers'),
('Eur/ton', 'EUR_TON', 1.0, 'Euro per ton'),
('Eur/m3', 'EUR_M3', 1.0, 'Euro per cubic meter')

ON CONFLICT (raw_unit) DO NOTHING;
*/

-- 5.2 List all EUR-related units for verification
SELECT 'EUR-related Units' as section;
SELECT unit, COUNT(*) as count
FROM financial_tables
WHERE LOWER(unit) LIKE '%eur%' OR unit IN ('€', 'M€')
GROUP BY unit
ORDER BY count DESC;

-- ============================================================================
-- SECTION 6: VERIFICATION QUERIES
-- ============================================================================

-- 6.1 Post-cleanup summary
SELECT 'Post-Cleanup Summary' as section;
SELECT
    'EBITDA' as metric,
    COUNT(*) as total_rows,
    COUNT(DISTINCT unit) as unique_units,
    SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) as negatives,
    ROUND(CASE WHEN MAX(value) > 0 AND MIN(CASE WHEN value > 0 THEN value END) > 0
          THEN MAX(value) / MIN(CASE WHEN value > 0 THEN value END)
          ELSE 0 END::numeric, 1) as swing_ratio
FROM financial_tables
WHERE LOWER(metric) LIKE '%ebitda%'
  AND entity_normalized = 'Group';

-- 6.2 Quality metrics tracking
SELECT 'Quality Metrics' as section;
SELECT
    ROUND(100.0 * SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as pct_null_values,
    ROUND(100.0 * SUM(CASE WHEN unit IS NULL OR unit = '' THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as pct_missing_units,
    ROUND(100.0 * SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as pct_negative,
    ROUND(100.0 * SUM(CASE WHEN unit ~ '[#@!()]' OR unit ~ '^[0-9-]+$' THEN 1 ELSE 0 END) / COUNT(*)::numeric, 2) as pct_malformed_units
FROM financial_tables;

-- ============================================================================
-- SECTION 7: VARIABLE COST SIGN CONVENTION AUDIT
-- ============================================================================

-- 7.1 Variable Cost sign distribution by entity
SELECT 'Variable Cost Sign Convention' as section;
SELECT
    entity_normalized,
    COUNT(*) as total,
    SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) as negatives,
    SUM(CASE WHEN value >= 0 THEN 1 ELSE 0 END) as positives,
    CASE
        WHEN SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) > 0.9 THEN 'CONSISTENT_NEGATIVE'
        WHEN SUM(CASE WHEN value >= 0 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) > 0.9 THEN 'CONSISTENT_POSITIVE'
        ELSE 'MIXED'
    END as pattern
FROM financial_tables
WHERE LOWER(metric) LIKE '%variable%cost%'
GROUP BY entity_normalized
ORDER BY total DESC
LIMIT 20;

-- ============================================================================
-- END OF AUDIT SCRIPT
-- ============================================================================
