-- Migration: Founding Member Tracking
-- Created: 2026-02-07
-- Purpose: Track 20 founding member spots with benefits

CREATE TABLE IF NOT EXISTS founding_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id),
    email TEXT NOT NULL UNIQUE,
    company_name TEXT,
    spot_number INTEGER NOT NULL UNIQUE CHECK (spot_number >= 1 AND spot_number <= 20),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'reserved' CHECK (status IN ('reserved', 'active', 'churned', 'expired')),
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    benefits JSONB DEFAULT '{
        "lifetime_discount_percent": 40,
        "priority_support": true,
        "early_feature_access": true,
        "founding_badge": true,
        "locked_price": true
    }'::jsonb,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Waitlist for after 20 spots filled
CREATE TABLE IF NOT EXISTS founding_waitlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    company_name TEXT,
    position INTEGER NOT NULL,
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_founding_members_email ON founding_members(email);
CREATE INDEX idx_founding_members_status ON founding_members(status);
CREATE INDEX idx_founding_waitlist_position ON founding_waitlist(position);

-- Function to get next available spot
CREATE OR REPLACE FUNCTION get_next_founding_spot()
RETURNS INTEGER AS $$
DECLARE
    next_spot INTEGER;
BEGIN
    SELECT MIN(s.spot) INTO next_spot
    FROM generate_series(1, 20) AS s(spot)
    WHERE s.spot NOT IN (SELECT spot_number FROM founding_members);
    RETURN next_spot;
END;
$$ LANGUAGE plpgsql;

-- Function to get remaining spots count
CREATE OR REPLACE FUNCTION get_remaining_founding_spots()
RETURNS INTEGER AS $$
BEGIN
    RETURN 20 - (SELECT COUNT(*) FROM founding_members WHERE status IN ('reserved', 'active'));
END;
$$ LANGUAGE plpgsql;

-- View: Founding spots status for landing page
CREATE OR REPLACE VIEW founding_spots_status AS
SELECT 
    20 as total_spots,
    (SELECT COUNT(*) FROM founding_members WHERE status IN ('reserved', 'active')) as spots_taken,
    get_remaining_founding_spots() as spots_remaining,
    (SELECT COUNT(*) FROM founding_waitlist) as waitlist_count,
    CASE 
        WHEN get_remaining_founding_spots() = 0 THEN true 
        ELSE false 
    END as is_full;

-- Auto-position waitlist entries
CREATE OR REPLACE FUNCTION set_waitlist_position()
RETURNS TRIGGER AS $$
BEGIN
    NEW.position := COALESCE((SELECT MAX(position) FROM founding_waitlist), 0) + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_waitlist_position
    BEFORE INSERT ON founding_waitlist
    FOR EACH ROW
    EXECUTE FUNCTION set_waitlist_position();

-- Trigger to update timestamp
CREATE TRIGGER trigger_founding_members_updated
    BEFORE UPDATE ON founding_members
    FOR EACH ROW
    EXECUTE FUNCTION update_sales_pipeline_timestamp();

-- RLS
ALTER TABLE founding_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE founding_waitlist ENABLE ROW LEVEL SECURITY;

-- Comments
COMMENT ON TABLE founding_members IS '20 founding member spots with 40% lifetime discount';
COMMENT ON COLUMN founding_members.benefits IS 'JSON benefits locked at signup time';
