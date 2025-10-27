-- Migration 002: Create financial_tables schema
-- Story 2.13: SQL Table Search (Phase 2A-REVISED)
-- Created: 2025-10-26
-- Purpose: Store extracted financial tables in structured SQL format for exact matching queries

CREATE TABLE IF NOT EXISTS financial_tables (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Document metadata
    document_id VARCHAR(255) NOT NULL,
    page_number INT NOT NULL,
    table_index INT NOT NULL,
    table_caption TEXT,

    -- Structured columns for querying
    entity VARCHAR(255),           -- e.g., "Portugal Cement", "Spain Ready-Mix"
    metric VARCHAR(255),            -- e.g., "variable costs", "thermal energy"
    period VARCHAR(100),            -- e.g., "Aug-25 YTD", "Q2 2025"
    fiscal_year INT,                -- e.g., 2025
    value DECIMAL(15,2),            -- Numeric value
    unit VARCHAR(50),               -- e.g., "EUR/ton", "GJ/ton"

    -- Additional metadata
    row_index INT,
    column_name VARCHAR(255),
    section_type VARCHAR(100) DEFAULT 'Table',
    created_at TIMESTAMP DEFAULT NOW(),

    -- Full context for attribution and fallback
    chunk_text TEXT                 -- Original table chunk text for context
);

-- Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_entity ON financial_tables(entity);
CREATE INDEX IF NOT EXISTS idx_metric ON financial_tables(metric);
CREATE INDEX IF NOT EXISTS idx_period ON financial_tables(period);
CREATE INDEX IF NOT EXISTS idx_fiscal_year ON financial_tables(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_document_page ON financial_tables(document_id, page_number);

-- Comments for documentation
COMMENT ON TABLE financial_tables IS 'Financial table data extracted from PDF documents for SQL-based exact matching queries';
COMMENT ON COLUMN financial_tables.entity IS 'Company, division, or business unit name';
COMMENT ON COLUMN financial_tables.metric IS 'Cost type, production metric, or financial measure';
COMMENT ON COLUMN financial_tables.period IS 'Time period (e.g., "Aug-25 YTD", "Q2 2025")';
COMMENT ON COLUMN financial_tables.value IS 'Numeric value from table cell';
COMMENT ON COLUMN financial_tables.unit IS 'Unit of measurement (e.g., "EUR/ton", "GJ/ton")';
COMMENT ON COLUMN financial_tables.chunk_text IS 'Full table context for attribution and synthesis';
