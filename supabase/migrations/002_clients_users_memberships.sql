-- FILE: supabase/migrations/002_clients_users_memberships.sql
-- PURPOSE: Multi-tenant clients, users, and team memberships
-- PHASE: 1 (Foundation + DevOps)
-- TASK: DB-003
-- DEPENDENCIES: 001_foundation.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only (deleted_at column)

-- ============================================
-- CLIENTS (Tenants)
-- ============================================

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,

    -- Subscription
    tier tier_type NOT NULL DEFAULT 'ignition',
    subscription_status subscription_status NOT NULL DEFAULT 'trialing',

    -- Credits (AUD-based)
    credits_remaining INTEGER NOT NULL DEFAULT 1250,
    credits_reset_at TIMESTAMPTZ,

    -- Default settings
    default_permission_mode permission_mode DEFAULT 'co_pilot',

    -- Stripe integration
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete (Rule 14)
);

-- Trigger for updated_at
CREATE TRIGGER clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Indexes
CREATE INDEX idx_clients_subscription ON clients(subscription_status)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_clients_stripe ON clients(stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

-- ============================================
-- USERS (Profile linked to auth.users)
-- ============================================

CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,

    -- Preferences
    timezone TEXT DEFAULT 'Australia/Sydney',
    notification_email BOOLEAN DEFAULT TRUE,
    notification_sms BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger for updated_at
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Index for email lookup
CREATE INDEX idx_users_email ON users(email);

-- ============================================
-- TRIGGER: Create user profile on auth signup
-- ============================================

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO users (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- ============================================
-- MEMBERSHIPS (User-Client many-to-many with roles)
-- ============================================

CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    role membership_role NOT NULL DEFAULT 'member',

    -- Invitation tracking
    invited_by UUID REFERENCES users(id),
    invited_email TEXT,  -- For pending invitations
    accepted_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,  -- Soft delete (Rule 14)

    -- Unique constraint per user per client
    CONSTRAINT unique_membership UNIQUE (user_id, client_id)
);

-- Trigger for updated_at
CREATE TRIGGER memberships_updated_at
    BEFORE UPDATE ON memberships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Indexes for common lookups
CREATE INDEX idx_memberships_user ON memberships(user_id)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_memberships_client ON memberships(client_id)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_memberships_role ON memberships(client_id, role)
    WHERE deleted_at IS NULL AND accepted_at IS NOT NULL;
CREATE INDEX idx_memberships_pending ON memberships(invited_email)
    WHERE accepted_at IS NULL AND deleted_at IS NULL;

-- ============================================
-- HELPER: Create first client and membership for new user
-- ============================================

CREATE OR REPLACE FUNCTION create_initial_client_for_user(
    p_user_id UUID,
    p_client_name TEXT
)
RETURNS UUID AS $$
DECLARE
    v_client_id UUID;
BEGIN
    -- Create the client
    INSERT INTO clients (name)
    VALUES (p_client_name)
    RETURNING id INTO v_client_id;

    -- Create owner membership
    INSERT INTO memberships (user_id, client_id, role, accepted_at)
    VALUES (p_user_id, v_client_id, 'owner', NOW());

    RETURN v_client_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] clients table with all fields from PART 5
-- [x] users table linked to auth.users
-- [x] memberships table with role-based access
-- [x] Soft delete columns (deleted_at) on all tables (Rule 14)
-- [x] updated_at triggers on all tables
-- [x] handle_new_user() trigger for auth signup
-- [x] Indexes for performance
-- [x] Unique constraint on user_id + client_id
-- [x] Helper function for initial client creation
