-- Migration: 010_stripe_billing.sql
-- Purpose: Add Stripe billing fields to clients table for deposit + subscription tracking
-- Step: 8/8 Build Sequence
-- Created: 2026-02-23

-- ============================================================================
-- Add Stripe billing columns to clients table
-- ============================================================================

-- deposit_paid: Set to true when $500 AUD founding deposit is confirmed via webhook
ALTER TABLE clients ADD COLUMN IF NOT EXISTS deposit_paid BOOLEAN DEFAULT FALSE;

-- subscription_activated_at: Set when first campaign is APPROVED and subscription starts
ALTER TABLE clients ADD COLUMN IF NOT EXISTS subscription_activated_at TIMESTAMPTZ;

-- Create index for fast lookup of founding members who paid deposit
CREATE INDEX IF NOT EXISTS idx_clients_deposit_paid ON clients(deposit_paid) WHERE deposit_paid = true;

-- ============================================================================
-- Create founding_spots view for landing page counter
-- Uses clients.deposit_paid = true to count claimed spots (not founding_members table)
-- ============================================================================

-- Drop existing view if it exists
DROP VIEW IF EXISTS founding_spots CASCADE;

-- Create materialized view for performance (refresh on deposit confirmation)
CREATE MATERIALIZED VIEW IF NOT EXISTS founding_spots AS
SELECT 
    1 AS id,
    20 AS total_spots,
    COALESCE((SELECT COUNT(*) FROM clients WHERE deposit_paid = true AND deleted_at IS NULL), 0)::INTEGER AS spots_taken
WITH DATA;

-- Create unique index for concurrent refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_founding_spots_id ON founding_spots(id);

-- Function to refresh founding spots view (called after deposit webhook)
CREATE OR REPLACE FUNCTION refresh_founding_spots()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY founding_spots;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-refresh on client deposit changes
DROP TRIGGER IF EXISTS trigger_refresh_founding_spots ON clients;
CREATE TRIGGER trigger_refresh_founding_spots
    AFTER INSERT OR UPDATE OF deposit_paid ON clients
    FOR EACH STATEMENT
    EXECUTE FUNCTION refresh_founding_spots();

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON COLUMN clients.deposit_paid IS 'True when $500 AUD founding deposit is confirmed via Stripe webhook';
COMMENT ON COLUMN clients.subscription_activated_at IS 'Timestamp when subscription was activated (first campaign APPROVED)';
COMMENT ON MATERIALIZED VIEW founding_spots IS 'Live count of founding spots claimed vs total for landing page display';

-- ============================================================================
-- Verification
-- ============================================================================
-- Verify columns exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'clients' AND column_name = 'deposit_paid') THEN
        RAISE EXCEPTION 'deposit_paid column not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'clients' AND column_name = 'subscription_activated_at') THEN
        RAISE EXCEPTION 'subscription_activated_at column not created';
    END IF;
END $$;
