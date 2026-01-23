-- ============================================
-- Migration: 053_campaign_resource_fk.sql
-- Purpose: Add client_resource_id FK to campaign_resources for auto-inheritance tracking
-- Gap Reference: TODO.md #10
-- ============================================

-- Add client_resource_id column to campaign_resources
-- This tracks which client_resource was inherited when the campaign was created
ALTER TABLE campaign_resources
ADD COLUMN IF NOT EXISTS client_resource_id UUID REFERENCES client_resources(id) ON DELETE SET NULL;

-- Add index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_campaign_resources_client_resource_id
ON campaign_resources(client_resource_id);

-- Add comment explaining the purpose
COMMENT ON COLUMN campaign_resources.client_resource_id IS 'Source client resource if auto-inherited from client level';

-- ============================================
-- VERIFICATION
-- ============================================
-- After running:
-- 1. Check column exists: \d campaign_resources
-- 2. Check FK constraint: \d campaign_resources
-- 3. Check index exists: \di idx_campaign_resources_client_resource_id
