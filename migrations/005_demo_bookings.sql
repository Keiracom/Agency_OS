-- Migration: Demo Bookings Table
-- Created: 2026-02-07
-- Purpose: Store demo booking events from Cal.com/Calendly

CREATE TABLE IF NOT EXISTS demo_bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id TEXT UNIQUE NOT NULL,
    provider TEXT NOT NULL CHECK (provider IN ('cal.com', 'calendly')),
    lead_id UUID REFERENCES leads(id),
    attendee_email TEXT NOT NULL,
    attendee_name TEXT,
    scheduled_time TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    meeting_url TEXT,
    location TEXT,
    status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled', 'no_show')),
    notes TEXT,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_demo_bookings_email ON demo_bookings(attendee_email);
CREATE INDEX idx_demo_bookings_scheduled ON demo_bookings(scheduled_time);
CREATE INDEX idx_demo_bookings_status ON demo_bookings(status);
CREATE INDEX idx_demo_bookings_lead ON demo_bookings(lead_id);

-- Auto-update timestamp trigger
CREATE TRIGGER trigger_demo_bookings_updated
    BEFORE UPDATE ON demo_bookings
    FOR EACH ROW
    EXECUTE FUNCTION update_sales_pipeline_timestamp();

-- RLS
ALTER TABLE demo_bookings ENABLE ROW LEVEL SECURITY;

-- View: Upcoming demos
CREATE OR REPLACE VIEW upcoming_demos AS
SELECT 
    db.id,
    db.attendee_email,
    db.attendee_name,
    db.scheduled_time,
    db.duration_minutes,
    db.meeting_url,
    db.provider,
    l.company_name,
    sp.deal_value_aud
FROM demo_bookings db
LEFT JOIN leads l ON db.lead_id = l.id
LEFT JOIN sales_pipeline sp ON db.lead_id = sp.lead_id
WHERE db.status = 'scheduled'
  AND db.scheduled_time > NOW()
ORDER BY db.scheduled_time;

COMMENT ON TABLE demo_bookings IS 'Demo booking events from Cal.com or Calendly webhooks';
