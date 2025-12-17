-- Migration 005: Add entity normalization for data quality improvements
-- Issue: Entity contamination in forecasting data (14.4x for EBITDA, 560x for variable_cost)
-- Root Cause: ILIKE '%entity%' patterns match too many variations
-- Fix: Add entity_mappings lookup table and entity_normalized column
--
-- Created: 2025-12-16
-- Story: 6.28 - Data Quality Fixes

-- Step 1: Create entity mappings lookup table
-- This stores the mapping from raw entity variations to canonical forms
CREATE TABLE IF NOT EXISTS entity_mappings (
    id SERIAL PRIMARY KEY,
    raw_entity VARCHAR(255) UNIQUE NOT NULL,
    canonical_entity VARCHAR(100) NOT NULL,
    match_type VARCHAR(20) DEFAULT 'exact',  -- exact, fuzzy, manual
    created_at TIMESTAMP DEFAULT NOW()
);

-- Step 2: Populate entity mappings from known patterns
-- These mappings match entity_normalizer.py ENTITY_CANONICAL_MAP
INSERT INTO entity_mappings (raw_entity, canonical_entity, match_type) VALUES
-- Group/Consolidated variations
('GROUP', 'Group', 'exact'),
('Conso', 'Group', 'exact'),
('CONSO', 'Group', 'exact'),
('Consolidated', 'Group', 'exact'),
('Group Total', 'Group', 'exact'),
('Secil GROUP', 'Group', 'exact'),
('Secil Group', 'Group', 'exact'),
('SECIL GROUP', 'Group', 'exact'),
('Total Group', 'Group', 'exact'),
('Total', 'Group', 'exact'),
('TOTAL', 'Group', 'exact'),
('Groupe', 'Group', 'exact'),
('Consolidado', 'Group', 'exact'),
-- Portugal variations
('Portugal', 'Portugal', 'exact'),
('PT', 'Portugal', 'exact'),
('Portugal Cement', 'Portugal', 'exact'),
('Cimento de Portugal', 'Portugal', 'exact'),
('Secil Portugal', 'Portugal', 'exact'),
('SECIL Portugal', 'Portugal', 'exact'),
('Secil PT', 'Portugal', 'exact'),
('Port.', 'Portugal', 'exact'),
('Portug.', 'Portugal', 'exact'),
('PORTUGAL', 'Portugal', 'exact'),
-- Brazil variations
('Brazil', 'Brazil', 'exact'),
('BR', 'Brazil', 'exact'),
('Brasil', 'Brazil', 'exact'),
('Brazil Cement', 'Brazil', 'exact'),
('BRAZIL', 'Brazil', 'exact'),
('Secil Brazil', 'Brazil', 'exact'),
('Secil Brasil', 'Brazil', 'exact'),
-- Tunisia variations
('Tunisia', 'Tunisia', 'exact'),
('TN', 'Tunisia', 'exact'),
('Tunisie', 'Tunisia', 'exact'),
('Tunisia Cement', 'Tunisia', 'exact'),
('TUNISIA', 'Tunisia', 'exact'),
('Secil Tunisia', 'Tunisia', 'exact'),
('Secil Tunisie', 'Tunisia', 'exact'),
('Tunísia', 'Tunisia', 'exact'),
-- Lebanon variations
('Lebanon', 'Lebanon', 'exact'),
('LB', 'Lebanon', 'exact'),
('Liban', 'Lebanon', 'exact'),
('Lebanon Cement', 'Lebanon', 'exact'),
('LEBANON', 'Lebanon', 'exact'),
('Secil Lebanon', 'Lebanon', 'exact'),
('Secil Liban', 'Lebanon', 'exact'),
('Líbano', 'Lebanon', 'exact'),
-- Angola variations
('Angola', 'Angola', 'exact'),
('AO', 'Angola', 'exact'),
('Angola Cement', 'Angola', 'exact'),
('ANGOLA', 'Angola', 'exact'),
('Secil Angola', 'Angola', 'exact'),
-- Cape Verde variations
('Cape Verde', 'Cape Verde', 'exact'),
('CV', 'Cape Verde', 'exact'),
('Cabo Verde', 'Cape Verde', 'exact'),
('Cape Verde Cement', 'Cape Verde', 'exact'),
('CAPE VERDE', 'Cape Verde', 'exact'),
('Secil Cape Verde', 'Cape Verde', 'exact'),
-- Ready-Mix variations
('Ready-Mix', 'Ready-Mix', 'exact'),
('RMC', 'Ready-Mix', 'exact'),
('Betão Pronto', 'Ready-Mix', 'exact'),
('Concrete', 'Ready-Mix', 'exact'),
('Ready Mix', 'Ready-Mix', 'exact'),
('READY-MIX', 'Ready-Mix', 'exact'),
-- Cement variations
('Cement Unit', 'Cement', 'exact'),
('Cement', 'Cement', 'exact'),
('CEMENT', 'Cement', 'exact'),
('Cimento', 'Cement', 'exact'),
-- Trading variations
('Trading', 'Trading', 'exact'),
('TRADING', 'Trading', 'exact'),
('Secil Trading', 'Trading', 'exact'),
('Cimpor Trading', 'Trading', 'exact'),
-- Parent company variations
('CIMPOR', 'Cimpor', 'exact'),
('Cimpor', 'Cimpor', 'exact'),
('InterCement', 'InterCement', 'exact'),
('Intercement', 'InterCement', 'exact'),
('INTERCIMENT', 'InterCement', 'exact'),
('Secil', 'Secil', 'exact'),
('SECIL', 'Secil', 'exact')
ON CONFLICT (raw_entity) DO NOTHING;

-- Step 3: Add entity_normalized column to financial_tables
ALTER TABLE financial_tables
ADD COLUMN IF NOT EXISTS entity_normalized VARCHAR(100);

-- Step 4: Create index for fast lookups on entity_normalized
CREATE INDEX IF NOT EXISTS idx_entity_normalized
ON financial_tables(entity_normalized);

-- Step 5: Create index on entity_mappings for fast joins
CREATE INDEX IF NOT EXISTS idx_entity_mappings_raw
ON entity_mappings(raw_entity);

CREATE INDEX IF NOT EXISTS idx_entity_mappings_canonical
ON entity_mappings(canonical_entity);

-- Verification queries:
-- SELECT COUNT(*) FROM entity_mappings;  -- Should be ~90 rows
-- SELECT canonical_entity, COUNT(*) FROM entity_mappings GROUP BY canonical_entity ORDER BY COUNT(*) DESC;

-- Note: Run scripts/backfill_entity_normalized.py after this migration
-- to populate the entity_normalized column with values
