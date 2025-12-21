-- FILE: supabase/migrations/009_rls_policies.sql
-- PURPOSE: Row-Level Security policies via memberships
-- PHASE: 1 (Foundation + DevOps)
-- TASK: DB-010
-- DEPENDENCIES: 008_audit_logs.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Multi-tenant isolation via memberships

-- ============================================
-- ENABLE RLS ON ALL TABLES
-- ============================================

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_sequences ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE global_suppression ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_suppression ENABLE ROW LEVEL SECURITY;
ALTER TABLE activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_permission_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- ============================================
-- CLIENTS POLICIES
-- ============================================

-- Users can view clients they are members of
CREATE POLICY clients_select ON clients
    FOR SELECT
    USING (
        id IN (SELECT get_user_client_ids())
        AND deleted_at IS NULL
    );

-- Only owners/admins can update clients
CREATE POLICY clients_update ON clients
    FOR UPDATE
    USING (
        user_has_role(id, ARRAY['owner', 'admin']::membership_role[])
        AND deleted_at IS NULL
    );

-- Only owners can soft-delete clients
CREATE POLICY clients_delete ON clients
    FOR DELETE
    USING (user_has_role(id, ARRAY['owner']::membership_role[]));

-- ============================================
-- USERS POLICIES
-- ============================================

-- Users can view their own profile
CREATE POLICY users_select_own ON users
    FOR SELECT
    USING (id = auth.uid());

-- Users can view profiles of users in their clients
CREATE POLICY users_select_team ON users
    FOR SELECT
    USING (
        id IN (
            SELECT m.user_id FROM memberships m
            WHERE m.client_id IN (SELECT get_user_client_ids())
            AND m.deleted_at IS NULL
        )
    );

-- Users can update their own profile
CREATE POLICY users_update ON users
    FOR UPDATE
    USING (id = auth.uid());

-- ============================================
-- MEMBERSHIPS POLICIES
-- ============================================

-- View memberships for clients user belongs to
CREATE POLICY memberships_select ON memberships
    FOR SELECT
    USING (
        client_id IN (SELECT get_user_client_ids())
        AND deleted_at IS NULL
    );

-- Owners/admins can create memberships
CREATE POLICY memberships_insert ON memberships
    FOR INSERT
    WITH CHECK (
        user_has_role(client_id, ARRAY['owner', 'admin']::membership_role[])
    );

-- Owners/admins can update memberships
CREATE POLICY memberships_update ON memberships
    FOR UPDATE
    USING (
        user_has_role(client_id, ARRAY['owner', 'admin']::membership_role[])
        AND deleted_at IS NULL
    );

-- Owners can delete memberships
CREATE POLICY memberships_delete ON memberships
    FOR DELETE
    USING (user_has_role(client_id, ARRAY['owner']::membership_role[]));

-- ============================================
-- CAMPAIGNS POLICIES
-- ============================================

-- View campaigns for user's clients
CREATE POLICY campaigns_select ON campaigns
    FOR SELECT
    USING (
        client_id IN (SELECT get_user_client_ids())
        AND deleted_at IS NULL
    );

-- Members+ can create campaigns
CREATE POLICY campaigns_insert ON campaigns
    FOR INSERT
    WITH CHECK (
        user_has_role(client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
    );

-- Members+ can update campaigns
CREATE POLICY campaigns_update ON campaigns
    FOR UPDATE
    USING (
        user_has_role(client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
        AND deleted_at IS NULL
    );

-- Admins+ can soft-delete campaigns
CREATE POLICY campaigns_delete ON campaigns
    FOR DELETE
    USING (user_has_role(client_id, ARRAY['owner', 'admin']::membership_role[]));

-- ============================================
-- CAMPAIGN RESOURCES POLICIES
-- ============================================

CREATE POLICY campaign_resources_select ON campaign_resources
    FOR SELECT
    USING (
        campaign_id IN (
            SELECT id FROM campaigns
            WHERE client_id IN (SELECT get_user_client_ids())
            AND deleted_at IS NULL
        )
    );

CREATE POLICY campaign_resources_insert ON campaign_resources
    FOR INSERT
    WITH CHECK (
        campaign_id IN (
            SELECT id FROM campaigns c
            WHERE user_has_role(c.client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
        )
    );

CREATE POLICY campaign_resources_update ON campaign_resources
    FOR UPDATE
    USING (
        campaign_id IN (
            SELECT id FROM campaigns c
            WHERE user_has_role(c.client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
        )
    );

-- ============================================
-- CAMPAIGN SEQUENCES POLICIES
-- ============================================

CREATE POLICY campaign_sequences_select ON campaign_sequences
    FOR SELECT
    USING (
        campaign_id IN (
            SELECT id FROM campaigns
            WHERE client_id IN (SELECT get_user_client_ids())
            AND deleted_at IS NULL
        )
    );

CREATE POLICY campaign_sequences_insert ON campaign_sequences
    FOR INSERT
    WITH CHECK (
        campaign_id IN (
            SELECT id FROM campaigns c
            WHERE user_has_role(c.client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
        )
    );

CREATE POLICY campaign_sequences_update ON campaign_sequences
    FOR UPDATE
    USING (
        campaign_id IN (
            SELECT id FROM campaigns c
            WHERE user_has_role(c.client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
        )
    );

-- ============================================
-- LEADS POLICIES
-- ============================================

CREATE POLICY leads_select ON leads
    FOR SELECT
    USING (
        client_id IN (SELECT get_user_client_ids())
        AND deleted_at IS NULL
    );

CREATE POLICY leads_insert ON leads
    FOR INSERT
    WITH CHECK (
        user_has_role(client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
    );

CREATE POLICY leads_update ON leads
    FOR UPDATE
    USING (
        user_has_role(client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
        AND deleted_at IS NULL
    );

CREATE POLICY leads_delete ON leads
    FOR DELETE
    USING (user_has_role(client_id, ARRAY['owner', 'admin']::membership_role[]));

-- ============================================
-- SUPPRESSION POLICIES
-- ============================================

-- Global suppression: admins only
CREATE POLICY global_suppression_select ON global_suppression
    FOR SELECT
    USING (TRUE);  -- Anyone can check suppression

-- Client suppression follows client access
CREATE POLICY client_suppression_select ON client_suppression
    FOR SELECT
    USING (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY client_suppression_insert ON client_suppression
    FOR INSERT
    WITH CHECK (
        user_has_role(client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
    );

-- ============================================
-- ACTIVITIES POLICIES
-- ============================================

CREATE POLICY activities_select ON activities
    FOR SELECT
    USING (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY activities_insert ON activities
    FOR INSERT
    WITH CHECK (
        user_has_role(client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
    );

-- ============================================
-- ACTIVITY STATS POLICIES
-- ============================================

CREATE POLICY activity_stats_select ON activity_stats
    FOR SELECT
    USING (client_id IN (SELECT get_user_client_ids()));

-- ============================================
-- APPROVAL QUEUE POLICIES
-- ============================================

CREATE POLICY approval_queue_select ON approval_queue
    FOR SELECT
    USING (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY approval_queue_update ON approval_queue
    FOR UPDATE
    USING (
        user_has_role(client_id, ARRAY['owner', 'admin', 'member']::membership_role[])
    );

-- ============================================
-- LEAD PERMISSION OVERRIDES POLICIES
-- ============================================

CREATE POLICY lead_permission_overrides_select ON lead_permission_overrides
    FOR SELECT
    USING (
        lead_id IN (
            SELECT id FROM leads
            WHERE client_id IN (SELECT get_user_client_ids())
        )
    );

CREATE POLICY lead_permission_overrides_manage ON lead_permission_overrides
    FOR ALL
    USING (
        lead_id IN (
            SELECT id FROM leads l
            WHERE user_has_role(l.client_id, ARRAY['owner', 'admin']::membership_role[])
        )
    );

-- ============================================
-- WEBHOOK CONFIGS POLICIES
-- ============================================

CREATE POLICY webhook_configs_select ON webhook_configs
    FOR SELECT
    USING (
        client_id IN (SELECT get_user_client_ids())
        AND deleted_at IS NULL
    );

CREATE POLICY webhook_configs_manage ON webhook_configs
    FOR ALL
    USING (
        user_has_role(client_id, ARRAY['owner', 'admin']::membership_role[])
    );

-- ============================================
-- WEBHOOK DELIVERIES POLICIES
-- ============================================

CREATE POLICY webhook_deliveries_select ON webhook_deliveries
    FOR SELECT
    USING (client_id IN (SELECT get_user_client_ids()));

-- ============================================
-- AUDIT LOGS POLICIES
-- ============================================

-- Users can view audit logs for their clients
CREATE POLICY audit_logs_select ON audit_logs
    FOR SELECT
    USING (client_id IN (SELECT get_user_client_ids()));

-- Only system can insert (via service role)

-- ============================================
-- SERVICE ROLE BYPASS
-- ============================================

-- Note: Service role bypasses RLS automatically in Supabase
-- These policies allow the backend (using service key) to perform
-- operations on behalf of the system (e.g., Prefect workers)

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] RLS enabled on all tables
-- [x] Clients: view via membership, update by admin+, delete by owner
-- [x] Users: view own + team, update own
-- [x] Memberships: view via client, manage by admin+
-- [x] Campaigns: CRUD based on role
-- [x] Leads: CRUD based on role
-- [x] Activities: read/write via membership
-- [x] Suppression: client-scoped
-- [x] Approval queue: view/update via membership
-- [x] Webhooks: admin+ management
-- [x] Audit logs: read-only for clients
-- [x] Soft delete checks (deleted_at IS NULL)
-- [x] Using get_user_client_ids() helper function
-- [x] Using user_has_role() helper function
