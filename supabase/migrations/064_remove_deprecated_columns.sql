-- Migration: 064_remove_deprecated_columns.sql
-- Purpose: Remove deprecated Apollo column from lead_pool
-- Context: Apollo deprecated, replaced by Leadmagic in Siege Waterfall

-- Drop apollo_id column from lead_pool (deprecated service)
ALTER TABLE lead_pool DROP COLUMN IF EXISTS apollo_id;

-- Drop associated index if it exists
DROP INDEX IF EXISTS idx_pool_apollo_id;
