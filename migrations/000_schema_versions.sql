-- Migration: 000_schema_versions
-- Story: 4.0.7 - Three-Mode Database Operation System
-- Purpose: Track schema versions for safe production deployments
-- Created: 2025-11-27

-- Schema version tracking table
-- Used by deploy-to-production.py to track which migrations have been applied
CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by TEXT,
    checksum TEXT
);

-- Insert this migration
INSERT INTO schema_versions (version, name, applied_by)
VALUES (0, '000_schema_versions', 'init')
ON CONFLICT (version) DO NOTHING;

-- Comment: Future migrations should:
-- 1. Be named with incrementing numbers: 001_add_feature.sql, 002_update_index.sql
-- 2. Insert their version into schema_versions at the end
-- 3. Be idempotent (safe to run multiple times)
-- 4. Never delete production data without explicit --force-data-loss flag
