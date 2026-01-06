-- FILE: supabase/migrations/017_fix_trigger_schema.sql
-- PURPOSE: Fix handle_new_user trigger to use explicit schema qualification
-- ISSUE: When triggered from auth.users insert, unqualified table names may resolve
--        to auth schema instead of public schema, causing "column not found" errors

CREATE OR REPLACE FUNCTION public.handle_new_user()
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

    -- 1. Create user profile (EXPLICIT public schema)
    INSERT INTO public.users (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        v_full_name
    );

    -- 2. Create client (tenant) for this user (EXPLICIT public schema)
    INSERT INTO public.clients (
        name,
        tier,
        subscription_status,
        credits_remaining,
        default_permission_mode
    )
    VALUES (
        v_company_name,
        'ignition',
        'trialing',
        1250,
        'co_pilot'
    )
    RETURNING id INTO v_client_id;

    -- 3. Create owner membership (EXPLICIT public schema)
    INSERT INTO public.memberships (
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
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

-- Ensure trigger exists and points to updated function
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
