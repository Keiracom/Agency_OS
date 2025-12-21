-- FILE: supabase/migrations/008_audit_logs.sql
-- PURPOSE: System audit trail for compliance and debugging
-- PHASE: 1 (Foundation + DevOps)
-- TASK: DB-009
-- DEPENDENCIES: 007_webhook_configs.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly

-- ============================================
-- AUDIT LOGS
-- ============================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Who performed the action
    user_id UUID REFERENCES users(id),
    client_id UUID REFERENCES clients(id),

    -- What action was performed
    action audit_action NOT NULL,
    resource_type TEXT NOT NULL,         -- campaigns, leads, users, etc.
    resource_id UUID,                    -- ID of affected resource

    -- Details of the change
    old_values JSONB,                    -- Previous state
    new_values JSONB,                    -- New state
    changes JSONB,                       -- Diff of changes

    -- Context
    ip_address INET,
    user_agent TEXT,
    request_id TEXT,                     -- For tracing

    -- Additional metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- Primary lookups
CREATE INDEX idx_audit_logs_client ON audit_logs(client_id, created_at DESC)
    WHERE client_id IS NOT NULL;
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC)
    WHERE user_id IS NOT NULL;

-- Resource-specific queries
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- Action filtering
CREATE INDEX idx_audit_logs_action ON audit_logs(action, created_at DESC);

-- Time-based queries
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- Request tracing
CREATE INDEX idx_audit_logs_request ON audit_logs(request_id)
    WHERE request_id IS NOT NULL;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Create audit log entry
CREATE OR REPLACE FUNCTION create_audit_log(
    p_user_id UUID,
    p_client_id UUID,
    p_action audit_action,
    p_resource_type TEXT,
    p_resource_id UUID DEFAULT NULL,
    p_old_values JSONB DEFAULT NULL,
    p_new_values JSONB DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
    v_changes JSONB;
BEGIN
    -- Calculate changes if both old and new values provided
    IF p_old_values IS NOT NULL AND p_new_values IS NOT NULL THEN
        SELECT jsonb_object_agg(key, value)
        INTO v_changes
        FROM (
            SELECT key, jsonb_build_object(
                'old', p_old_values->key,
                'new', p_new_values->key
            ) as value
            FROM jsonb_each(p_new_values)
            WHERE p_old_values->key IS DISTINCT FROM p_new_values->key
        ) t;
    END IF;

    INSERT INTO audit_logs (
        user_id, client_id, action,
        resource_type, resource_id,
        old_values, new_values, changes,
        metadata
    ) VALUES (
        p_user_id, p_client_id, p_action,
        p_resource_type, p_resource_id,
        p_old_values, p_new_values, v_changes,
        p_metadata
    )
    RETURNING id INTO v_log_id;

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- Get audit history for a resource
CREATE OR REPLACE FUNCTION get_audit_history(
    p_resource_type TEXT,
    p_resource_id UUID,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    action audit_action,
    changes JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ
) AS $$
    SELECT
        al.id,
        al.user_id,
        al.action,
        al.changes,
        al.metadata,
        al.created_at
    FROM audit_logs al
    WHERE al.resource_type = p_resource_type
    AND al.resource_id = p_resource_id
    ORDER BY al.created_at DESC
    LIMIT p_limit;
$$ LANGUAGE sql STABLE;

-- ============================================
-- AUTO-AUDIT TRIGGERS
-- ============================================

-- Generic audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    v_action audit_action;
    v_old_values JSONB;
    v_new_values JSONB;
    v_user_id UUID;
    v_client_id UUID;
BEGIN
    -- Determine action type
    IF TG_OP = 'INSERT' THEN
        v_action := 'create';
        v_new_values := to_jsonb(NEW);
        v_old_values := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        v_action := 'update';
        v_old_values := to_jsonb(OLD);
        v_new_values := to_jsonb(NEW);
    ELSIF TG_OP = 'DELETE' THEN
        v_action := 'delete';
        v_old_values := to_jsonb(OLD);
        v_new_values := NULL;
    END IF;

    -- Try to get user_id from current session
    BEGIN
        v_user_id := auth.uid();
    EXCEPTION WHEN OTHERS THEN
        v_user_id := NULL;
    END;

    -- Try to get client_id from the record
    IF v_new_values ? 'client_id' THEN
        v_client_id := (v_new_values->>'client_id')::UUID;
    ELSIF v_old_values ? 'client_id' THEN
        v_client_id := (v_old_values->>'client_id')::UUID;
    END IF;

    -- Create audit log
    PERFORM create_audit_log(
        v_user_id,
        v_client_id,
        v_action,
        TG_TABLE_NAME,
        CASE
            WHEN TG_OP = 'DELETE' THEN (OLD.id)::UUID
            ELSE (NEW.id)::UUID
        END,
        v_old_values,
        v_new_values
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit triggers to key tables
-- Note: Enable these selectively to avoid performance impact

-- Campaigns audit
CREATE TRIGGER campaigns_audit
    AFTER INSERT OR UPDATE OR DELETE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Clients audit
CREATE TRIGGER clients_audit
    AFTER INSERT OR UPDATE OR DELETE ON clients
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Memberships audit (for access control changes)
CREATE TRIGGER memberships_audit
    AFTER INSERT OR UPDATE OR DELETE ON memberships
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- ============================================
-- RETENTION POLICY
-- ============================================

-- Function to clean old audit logs (run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(
    p_retention_days INTEGER DEFAULT 365
)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    DELETE FROM audit_logs
    WHERE created_at < NOW() - (p_retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] audit_logs table with all required fields
-- [x] Proper indexes for common queries
-- [x] create_audit_log() function
-- [x] get_audit_history() function
-- [x] Auto-audit triggers for key tables
-- [x] cleanup_old_audit_logs() for retention
-- [x] Changes diff calculation
-- [x] Request ID for tracing
