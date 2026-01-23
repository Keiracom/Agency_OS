-- ============================================
-- Migration: 050_emergency_pause.sql
-- Purpose: Add pause tracking fields to campaigns and clients
-- Phase H: Item 43 - Emergency Pause Button
-- Date: 2026-01-23
-- ============================================

-- ============================================
-- CAMPAIGNS TABLE: Add pause tracking
-- ============================================

-- paused_at: When the campaign was paused (NULL = not paused)
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ;

-- pause_reason: Why the campaign was paused (optional)
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS pause_reason TEXT;

-- paused_by_user_id: Who initiated the pause
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS paused_by_user_id UUID REFERENCES users(id);

-- Index for finding paused campaigns efficiently
CREATE INDEX IF NOT EXISTS idx_campaigns_paused_at
ON campaigns(client_id, paused_at)
WHERE paused_at IS NOT NULL;

-- ============================================
-- CLIENTS TABLE: Add emergency pause tracking
-- ============================================

-- paused_at: When client paused ALL outreach (NULL = not paused)
ALTER TABLE clients ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ;

-- pause_reason: Why the client paused all outreach
ALTER TABLE clients ADD COLUMN IF NOT EXISTS pause_reason TEXT;

-- paused_by_user_id: Who initiated the emergency pause
ALTER TABLE clients ADD COLUMN IF NOT EXISTS paused_by_user_id UUID REFERENCES users(id);

-- Index for finding clients with emergency pause
CREATE INDEX IF NOT EXISTS idx_clients_paused_at
ON clients(paused_at)
WHERE paused_at IS NOT NULL;

-- ============================================
-- COMMENTS for documentation
-- ============================================

COMMENT ON COLUMN campaigns.paused_at IS 'Timestamp when campaign was paused. NULL means not paused.';
COMMENT ON COLUMN campaigns.pause_reason IS 'Optional reason for pausing the campaign.';
COMMENT ON COLUMN campaigns.paused_by_user_id IS 'User who initiated the pause action.';

COMMENT ON COLUMN clients.paused_at IS 'Emergency pause timestamp. When set, ALL outreach for this client stops.';
COMMENT ON COLUMN clients.pause_reason IS 'Reason for emergency pause (e.g., "Content issue", "Client request").';
COMMENT ON COLUMN clients.paused_by_user_id IS 'User who initiated the emergency pause.';

-- ============================================
-- VERIFICATION
-- ============================================
-- Run: SELECT column_name, data_type FROM information_schema.columns
--      WHERE table_name = 'campaigns' AND column_name LIKE 'pause%';
-- Run: SELECT column_name, data_type FROM information_schema.columns
--      WHERE table_name = 'clients' AND column_name LIKE 'pause%';
