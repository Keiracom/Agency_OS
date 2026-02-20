-- FILE: supabase/seeds/058_bloomberg_dashboard_test_data.sql
-- PURPOSE: Seed test data for Bloomberg Terminal dashboard (Directive #052 Part I)
-- DATE: 2026-02-19
-- 
-- This seeds data for all 6 panels:
-- 1. Campaign Health - ALS distribution
-- 2. Personalisation Intelligence - Enrichment data
-- 3. Outreach Performance - Sequences, replies, meetings
-- 4. Alert Centre - Active alerts, review queues
-- 5. Deliverability - Domain warmup status
-- 6. Discovery Loop - Discarded leads, quota status

-- ============================================
-- TEST CLIENT
-- ============================================

-- Insert test client if not exists
INSERT INTO clients (id, name, company_name, status, created_at)
VALUES (
    'test-client-001'::uuid,
    'Test Agency',
    'Test Agency Pty Ltd',
    'active',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- PANEL 1: CAMPAIGN HEALTH TEST DATA
-- ============================================

-- Insert leads with ALS tiers for distribution
INSERT INTO lead_pool (id, client_id, email, first_name, last_name, als_score, als_tier, pool_status, created_at)
VALUES
    -- Hot leads (25%)
    (gen_random_uuid(), 'test-client-001'::uuid, 'hot1@test.com', 'Sarah', 'Chen', 92, 'hot', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'hot2@test.com', 'Mike', 'Johnson', 89, 'hot', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'hot3@test.com', 'Lisa', 'Park', 87, 'hot', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'hot4@test.com', 'James', 'Wilson', 85, 'hot', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'hot5@test.com', 'Emma', 'Davis', 86, 'hot', 'assigned', NOW()),
    
    -- Warm leads (35%)
    (gen_random_uuid(), 'test-client-001'::uuid, 'warm1@test.com', 'David', 'Lee', 78, 'warm', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'warm2@test.com', 'Rachel', 'Ng', 72, 'warm', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'warm3@test.com', 'Tom', 'Brown', 68, 'warm', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'warm4@test.com', 'Amy', 'Taylor', 75, 'warm', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'warm5@test.com', 'Chris', 'Martin', 70, 'warm', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'warm6@test.com', 'Nina', 'Garcia', 73, 'warm', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'warm7@test.com', 'Jack', 'Smith', 69, 'warm', 'assigned', NOW()),
    
    -- Cool leads (25%)
    (gen_random_uuid(), 'test-client-001'::uuid, 'cool1@test.com', 'Alex', 'Turner', 55, 'cool', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'cool2@test.com', 'Maya', 'Patel', 48, 'cool', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'cool3@test.com', 'Ryan', 'Clark', 52, 'cool', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'cool4@test.com', 'Sophie', 'White', 45, 'cool', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'cool5@test.com', 'Ben', 'Harris', 50, 'cool', 'assigned', NOW()),
    
    -- Cold leads (15%)
    (gen_random_uuid(), 'test-client-001'::uuid, 'cold1@test.com', 'Kevin', 'Moore', 32, 'cold', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'cold2@test.com', 'Laura', 'Young', 28, 'cold', 'assigned', NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'cold3@test.com', 'Dan', 'Scott', 25, 'cold', 'assigned', NOW())
ON CONFLICT DO NOTHING;

-- Campaign quota status
INSERT INTO campaign_quota_status (id, campaign_id, client_id, target_lead_count, current_qualified_count, discovery_loops_run)
VALUES (
    gen_random_uuid(),
    gen_random_uuid(),
    'test-client-001'::uuid,
    100,
    65,
    2
) ON CONFLICT DO NOTHING;

-- ============================================
-- PANEL 2: PERSONALISATION INTELLIGENCE
-- ============================================

-- Update lead_pool with enrichment data
UPDATE lead_pool
SET 
    enrichment_lineage = '[
        {"step": 1, "source": "ai_ark", "timestamp": "2026-02-19T10:00:00Z", "data_added": ["email", "title"]},
        {"step": 2, "source": "hunter_io", "timestamp": "2026-02-19T10:00:01Z", "verification": "valid"}
    ]'::jsonb,
    intent_signals = '{
        "linkedin_posts": true,
        "recent_post_topic": "AI automation in sales",
        "company_news": "Series A funding"
    }'::jsonb
WHERE client_id = 'test-client-001'::uuid
AND als_tier = 'hot';

UPDATE lead_pool
SET 
    enrichment_lineage = '[
        {"step": 1, "source": "ai_ark", "timestamp": "2026-02-19T10:00:00Z", "data_added": ["email"]}
    ]'::jsonb,
    intent_signals = '{
        "linkedin_posts": true,
        "x_posts": false
    }'::jsonb
WHERE client_id = 'test-client-001'::uuid
AND als_tier = 'warm';

-- ============================================
-- PANEL 3: OUTREACH PERFORMANCE
-- ============================================

-- Create test leads for sequence tracking
INSERT INTO leads (id, client_id, email, first_name, last_name, status, current_sequence_step, created_at)
VALUES
    (gen_random_uuid(), 'test-client-001'::uuid, 'seq1@test.com', 'Sarah', 'Chen', 'in_sequence', 2, NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'seq2@test.com', 'Mike', 'Johnson', 'in_sequence', 1, NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'seq3@test.com', 'Lisa', 'Park', 'in_sequence', 3, NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'seq4@test.com', 'James', 'Wilson', 'in_sequence', 1, NOW()),
    (gen_random_uuid(), 'test-client-001'::uuid, 'seq5@test.com', 'Emma', 'Davis', 'in_sequence', 2, NOW())
ON CONFLICT DO NOTHING;

-- Reply intents
INSERT INTO lead_replies (id, lead_id, client_id, channel, direction, content, intent, intent_confidence, created_at)
SELECT 
    gen_random_uuid(),
    (SELECT id FROM leads WHERE client_id = 'test-client-001'::uuid LIMIT 1),
    'test-client-001'::uuid,
    'email',
    'inbound',
    'Sample reply content',
    intent_val,
    0.95,
    NOW() - (random() * INTERVAL '30 days')
FROM unnest(ARRAY[
    'meeting_request', 'meeting_request', 'meeting_request',
    'interested', 'interested', 'interested', 'interested',
    'not_interested', 'not_interested',
    'question', 'question',
    'out_of_office'
]) AS intent_val
ON CONFLICT DO NOTHING;

-- Meetings booked this month
INSERT INTO meetings (id, client_id, lead_id, booked_at, scheduled_at, meeting_type, showed_up)
SELECT
    gen_random_uuid(),
    'test-client-001'::uuid,
    (SELECT id FROM leads WHERE client_id = 'test-client-001'::uuid LIMIT 1),
    DATE_TRUNC('month', NOW()) + (generate_series || ' days')::INTERVAL,
    DATE_TRUNC('month', NOW()) + ((generate_series + 1) || ' days')::INTERVAL,
    'discovery',
    TRUE
FROM generate_series(1, 14)
ON CONFLICT DO NOTHING;

-- ============================================
-- PANEL 4: ALERT CENTRE
-- ============================================

-- Active alerts
INSERT INTO admin_notifications (id, client_id, notification_type, title, message, severity, status, created_at)
VALUES
    (gen_random_uuid(), 'test-client-001'::uuid, 'bright_data_error', 'Bright Data API Error', 'Rate limit exceeded for scraping operations', 'high', 'pending', NOW() - INTERVAL '2 hours'),
    (gen_random_uuid(), 'test-client-001'::uuid, 'warmup_health_low', 'Domain Health Warning', 'agency-mail.com health score dropped below 70%', 'medium', 'pending', NOW() - INTERVAL '4 hours'),
    (gen_random_uuid(), 'test-client-001'::uuid, 'hot_warm_ratio_low', 'Campaign Quality Alert', 'Hot+Warm ratio at 18%, below 20% threshold', 'high', 'pending', NOW() - INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

-- Human review queue
INSERT INTO human_review_queue (id, client_id, lead_id, review_type, priority, status, data, created_at)
SELECT
    gen_random_uuid(),
    'test-client-001'::uuid,
    (SELECT id FROM leads WHERE client_id = 'test-client-001'::uuid LIMIT 1),
    review_type,
    priority,
    'pending',
    '{}'::jsonb,
    NOW()
FROM (VALUES 
    ('reply_classification', 'high'),
    ('reply_classification', 'medium'),
    ('content_qa', 'low')
) AS v(review_type, priority)
ON CONFLICT DO NOTHING;

-- Complaint queue (angry replies)
INSERT INTO lead_replies (id, lead_id, client_id, channel, direction, content, intent, admin_review_required, created_at)
SELECT
    gen_random_uuid(),
    (SELECT id FROM leads WHERE client_id = 'test-client-001'::uuid LIMIT 1),
    'test-client-001'::uuid,
    'email',
    'inbound',
    'Please remove me from your list immediately!',
    'angry_or_complaint',
    TRUE,
    NOW() - INTERVAL '3 hours'
WHERE NOT EXISTS (
    SELECT 1 FROM lead_replies 
    WHERE client_id = 'test-client-001'::uuid 
    AND intent = 'angry_or_complaint'
);

-- ============================================
-- PANEL 5: DELIVERABILITY
-- ============================================

INSERT INTO domain_warmup_status (id, client_id, domain, provider, warmup_stage, daily_send_limit, current_send_count, health_score, warmup_started_at)
VALUES
    (gen_random_uuid(), 'test-client-001'::uuid, 'agency-mail.com', 'warmforge', 'stable', 150, 87, 92, NOW() - INTERVAL '30 days'),
    (gen_random_uuid(), 'test-client-001'::uuid, 'outreach-pro.io', 'warmforge', 'ramping', 75, 45, 78, NOW() - INTERVAL '14 days'),
    (gen_random_uuid(), 'test-client-001'::uuid, 'sales-connect.com', 'mailforge', 'ramping', 50, 28, 65, NOW() - INTERVAL '7 days'),
    (gen_random_uuid(), 'test-client-001'::uuid, 'new-domain.co', 'warmforge', 'ramping', 25, 12, 55, NOW() - INTERVAL '3 days')
ON CONFLICT (client_id, domain) DO UPDATE SET
    warmup_stage = EXCLUDED.warmup_stage,
    daily_send_limit = EXCLUDED.daily_send_limit,
    current_send_count = EXCLUDED.current_send_count,
    health_score = EXCLUDED.health_score;

-- ============================================
-- PANEL 6: DISCOVERY LOOP
-- ============================================

-- Discarded leads by gate
INSERT INTO discarded_leads (id, lead_id, client_id, discard_gate, discard_reason, als_at_discard, discarded_at)
SELECT
    gen_random_uuid(),
    (SELECT id FROM lead_pool WHERE client_id = 'test-client-001'::uuid LIMIT 1),
    'test-client-001'::uuid,
    gate,
    reason,
    30,
    NOW() - (random() * INTERVAL '7 days')
FROM (VALUES
    -- Gate 1 discards (data quality)
    (1, 'missing_email'),
    (1, 'missing_email'),
    (1, 'invalid_domain'),
    (1, 'missing_company'),
    (1, 'incomplete_profile'),
    
    -- Gate 2 discards (authority)
    (2, 'low_authority_score'),
    (2, 'low_authority_score'),
    (2, 'non_decision_maker'),
    
    -- Gate 3 discards (company fit)
    (3, 'company_too_small'),
    (3, 'wrong_industry'),
    (3, 'company_too_small')
) AS v(gate, reason)
ON CONFLICT DO NOTHING;

-- ============================================
-- VERIFICATION
-- ============================================

DO $$
DECLARE
    v_lead_count INTEGER;
    v_domain_count INTEGER;
    v_alert_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_lead_count FROM lead_pool WHERE client_id = 'test-client-001'::uuid;
    SELECT COUNT(*) INTO v_domain_count FROM domain_warmup_status WHERE client_id = 'test-client-001'::uuid;
    SELECT COUNT(*) INTO v_alert_count FROM admin_notifications WHERE client_id = 'test-client-001'::uuid;
    
    RAISE NOTICE '✅ Bloomberg Dashboard Test Data Seeded';
    RAISE NOTICE '   - Lead Pool: % records', v_lead_count;
    RAISE NOTICE '   - Domains: % records', v_domain_count;
    RAISE NOTICE '   - Alerts: % records', v_alert_count;
END $$;
