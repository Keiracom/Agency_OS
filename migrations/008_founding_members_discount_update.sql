-- Migration: Update Founding Member Discount from 40% to 50%
-- Created: 2026-02-12
-- Purpose: CEO Directive #008 - Increase founding member discount
-- Author: Elliot

-- =============================================================================
-- IMPORTANT: This migration updates the DEFAULT discount for new founding members
-- Existing members keep their locked-in benefits (no retroactive changes)
-- =============================================================================

-- Step 1: Update the DEFAULT for new founding members
ALTER TABLE founding_members 
ALTER COLUMN benefits 
SET DEFAULT '{
    "lifetime_discount_percent": 50,
    "priority_support": true,
    "early_feature_access": true,
    "founding_badge": true,
    "locked_price": true
}'::jsonb;

-- Step 2: Update the table comment to reflect new discount
COMMENT ON TABLE founding_members IS '20 founding member spots with 50% lifetime discount (updated CEO Directive #008)';

-- Step 3: Log the change for audit trail
INSERT INTO governance_log (
    event_type,
    event_description,
    directive_reference,
    created_by,
    created_at
) VALUES (
    'PRICING_CHANGE',
    'Founding member discount updated from 40% to 50% for new members. Existing members retain their locked benefits.',
    'CEO Directive #008',
    'migration',
    NOW()
) ON CONFLICT DO NOTHING;

-- =============================================================================
-- VERIFICATION QUERY (run after migration)
-- =============================================================================
-- SELECT 
--     benefits->>'lifetime_discount_percent' as new_default_discount,
--     COUNT(*) as existing_member_count
-- FROM founding_members
-- GROUP BY benefits->>'lifetime_discount_percent';
-- 
-- Expected: new members get 50%, existing members retain whatever they had

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================
-- ALTER TABLE founding_members 
-- ALTER COLUMN benefits 
-- SET DEFAULT '{
--     "lifetime_discount_percent": 40,
--     "priority_support": true,
--     "early_feature_access": true,
--     "founding_badge": true,
--     "locked_price": true
-- }'::jsonb;
--
-- COMMENT ON TABLE founding_members IS '20 founding member spots with 40% lifetime discount';
