-- Migration 004: Change document_id from UUID to TEXT for filename storage
-- Issue: EXC-006 Async ingestion metadata attribution failure
-- Root Cause: document_id column is UUID but code stores filenames (TEXT)
-- Fix: Convert document_id columns to TEXT in both tables
--
-- Created: 2025-11-23
-- Related Commit: 0198483 fix(database): change document_id from UUID to TEXT for filename storage

-- Step 1: Drop foreign key constraints if any exist
-- (None currently defined, but good practice to check)

-- Step 2: Change financial_chunks.document_id from UUID to TEXT
ALTER TABLE financial_chunks
ALTER COLUMN document_id TYPE TEXT USING document_id::TEXT;

-- Step 3: Change financial_tables.document_id from UUID to TEXT (already VARCHAR, verify)
-- financial_tables.document_id is already VARCHAR(255), no change needed
-- Verify with: SELECT data_type FROM information_schema.columns WHERE table_name = 'financial_tables' AND column_name = 'document_id';

-- Step 4: Update indexes to use TEXT type
-- Indexes automatically handle type changes, no action needed

-- Verification query:
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name IN ('financial_chunks', 'financial_tables')
-- AND column_name = 'document_id';
