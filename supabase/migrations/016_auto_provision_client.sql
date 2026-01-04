-- FILE: supabase/migrations/016_auto_provision_client.sql
-- PURPOSE: Auto-provision client and membership when new user signs up
-- PHASE: 17 (Launch Prerequisites)
-- TASK: AUTO-PROVISION
-- DEPENDENCIES: 002_clients_users_memberships.sql, 012_client_icp_profile.sql

-- ============================================
-- UPDATE: handle_new_user() to auto-provision
-- ============================================

-- Drop existing trigger first
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create enhanced function that provisions client + membership
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    v_client_id UUID;
    v_company_name TEXT;
    v_full_name TEXT;
BEGIN
    -- Extract metadata
    v_full_name := COALESCE(NEW.raw_user_meta_data->>'full_name', '');
    v_company_name := COALESCE(
        NEW.raw_user_meta_data->>'company_name',
        v_full_name || '''s Agency',
        'My Agency'
    );

    -- 1. Create user profile
    INSERT INTO users (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        v_full_name
    );

    -- 2. Create client (tenant) for this user
    INSERT INTO clients (
        name,
        tier,
        subscription_status,
        credits_remaining,
        default_permission_mode
    )
    VALUES (
        v_company_name,
        'ignition',           -- Default tier
        'trialing',           -- Start as trial
        1250,                 -- Ignition tier credits
        'co_pilot'            -- Default permission mode
    )
    RETURNING id INTO v_client_id;

    -- 3. Create owner membership (auto-accepted)
    INSERT INTO memberships (
        user_id,
        client_id,
        role,
        accepted_at
    )
    VALUES (
        NEW.id,
        v_client_id,
        'owner',
        NOW()
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Recreate trigger
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- ============================================
-- HELPER: Check if user needs onboarding
-- ============================================

CREATE OR REPLACE FUNCTION user_needs_onboarding(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_icp_confirmed TIMESTAMPTZ;
BEGIN
    -- Get the user's primary client's ICP status
    SELECT c.icp_confirmed_at INTO v_icp_confirmed
    FROM memberships m
    JOIN clients c ON c.id = m.client_id
    WHERE m.user_id = p_user_id
      AND m.role = 'owner'
      AND m.accepted_at IS NOT NULL
      AND m.deleted_at IS NULL
      AND c.deleted_at IS NULL
    ORDER BY m.created_at ASC
    LIMIT 1;

    -- If no ICP confirmed, needs onboarding
    RETURN v_icp_confirmed IS NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- RPC: Get onboarding status for current user
-- ============================================

CREATE OR REPLACE FUNCTION get_onboarding_status()
RETURNS TABLE (
    needs_onboarding BOOLEAN,
    client_id UUID,
    client_name TEXT,
    icp_confirmed_at TIMESTAMPTZ,
    website_url TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.icp_confirmed_at IS NULL AS needs_onboarding,
        c.id AS client_id,
        c.name AS client_name,
        c.icp_confirmed_at,
        c.website_url
    FROM memberships m
    JOIN clients c ON c.id = m.client_id
    WHERE m.user_id = auth.uid()
      AND m.role = 'owner'
      AND m.accepted_at IS NOT NULL
      AND m.deleted_at IS NULL
      AND c.deleted_at IS NULL
    ORDER BY m.created_at ASC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- GRANT EXECUTE to authenticated users
-- ============================================

GRANT EXECUTE ON FUNCTION get_onboarding_status() TO authenticated;
GRANT EXECUTE ON FUNCTION user_needs_onboarding(UUID) TO authenticated;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] handle_new_user() creates user + client + membership
-- [x] New users get 'owner' role with auto-accepted membership
-- [x] user_needs_onboarding() helper function
-- [x] get_onboarding_status() RPC for frontend
-- [x] Grants for authenticated users
