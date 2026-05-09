-- Migration: 20260509_sdk_usage_log_rls_policies.sql
-- Purpose: Add the two RLS policies to sdk_usage_log that 018_sdk_usage_log.sql
--          intended but never landed in prod. Discovered while building E1 R3
--          (PR #649) — pg_policies showed sdk_usage_log has RLS enabled but
--          ZERO policies, so authenticated PostgREST clients can read nothing
--          (only the service_role bypass works).
--
--          Original 018 migration referenced `client_memberships` — a table
--          that does not exist in prod schema. Canonical name is `memberships`
--          (verified 2026-05-09: columns user_id, client_id, deleted_at all
--          present). This migration uses the correct table name.
--
--          Idempotent: DROP IF EXISTS first so the migration is safe to re-run
--          and survives any future divergence between dev and prod state.
-- Created: 2026-05-09

-- Pre-flight: ensure RLS is enabled (no-op if already on)
ALTER TABLE sdk_usage_log ENABLE ROW LEVEL SECURITY;

-- Drop any prior versions of these named policies before recreating, so the
-- migration is idempotent even if a half-applied attempt left fragments behind.
DROP POLICY IF EXISTS sdk_usage_platform_admin ON sdk_usage_log;
DROP POLICY IF EXISTS sdk_usage_client_member ON sdk_usage_log;

-- Platform admins see all SDK usage (full CRUD)
CREATE POLICY sdk_usage_platform_admin ON sdk_usage_log
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid()
            AND u.is_platform_admin = true
        )
    );

-- Client members see their own client's SDK usage (read-only)
CREATE POLICY sdk_usage_client_member ON sdk_usage_log
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM memberships m
            WHERE m.user_id = auth.uid()
            AND m.client_id = sdk_usage_log.client_id
            AND m.deleted_at IS NULL
        )
    );

COMMENT ON POLICY sdk_usage_platform_admin ON sdk_usage_log IS
    'Platform admins (users.is_platform_admin = true) can do anything. Established 2026-05-09 — original 018_sdk_usage_log.sql policy never landed in prod.';
COMMENT ON POLICY sdk_usage_client_member ON sdk_usage_log IS
    'Client members (via memberships) can SELECT their own client rows. Established 2026-05-09 with correct memberships table reference (018 referenced non-existent client_memberships).';
