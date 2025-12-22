-- Migration: 011_fix_user_insert_policy.sql
-- Purpose: Allow trigger/auth to insert new users during signup
-- Issue: RLS blocking handle_new_user() trigger insert

-- Allow users to be inserted during signup (when auth.uid() matches the new user id)
CREATE POLICY users_insert_on_signup ON users
    FOR INSERT
    WITH CHECK (id = auth.uid());
