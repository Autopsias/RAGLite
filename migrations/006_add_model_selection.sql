-- Migration 006: Add model_selection table for caching model selection results
-- Story 7b-4: Model Selection Cache in PostgreSQL
--
-- This migration creates the model_selection table to cache per-variable
-- model selection results from cross-validation, avoiding redundant CV runs.
--
-- AC-7b.4.1: Table with columns for best model, MAPE/MASE, regressors
-- AC-7b.4.6: Idempotent migration (CREATE IF NOT EXISTS)

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

-- Index on variable_name for fast lookups (AC-7b.4.3: <100ms query)
CREATE INDEX IF NOT EXISTS idx_model_selection_variable ON model_selection(variable_name);

-- Index on expires_at for efficient TTL cleanup (AC-7b.4.5)
CREATE INDEX IF NOT EXISTS idx_model_selection_expires ON model_selection(expires_at);
