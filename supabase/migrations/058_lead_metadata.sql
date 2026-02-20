-- Migration: 058_lead_metadata.sql
-- Purpose: Add metadata JSONB column to leads table for intent handler storage
-- Created: 2025-02-19

-- Add metadata JSONB column (nullable, default {})
ALTER TABLE leads ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::JSONB;

-- Add comment for documentation
COMMENT ON COLUMN leads.metadata IS 'Generic metadata storage for intent handlers (meeting_requested_at, referral info, admin review flags, etc.)';

-- Create index for metadata queries (GIN index for JSONB)
CREATE INDEX IF NOT EXISTS idx_leads_metadata ON leads USING GIN (metadata);
