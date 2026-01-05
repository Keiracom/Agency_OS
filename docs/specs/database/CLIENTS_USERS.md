# Database: Clients, Users, Memberships

**Migration:** `002_clients_users_memberships.sql`

---

## Clients Table

```sql
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    tier tier_type NOT NULL DEFAULT 'ignition',
    subscription_status subscription_status NOT NULL DEFAULT 'trialing',
    credits_remaining INTEGER NOT NULL DEFAULT 1250,
    credits_reset_at TIMESTAMPTZ,
    default_permission_mode permission_mode DEFAULT 'co_pilot',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    
    -- ICP Fields (Phase 11)
    website_url TEXT,
    company_description TEXT,
    services_offered TEXT[],
    years_in_business INTEGER,
    team_size INTEGER,
    value_proposition TEXT,
    default_offer TEXT,
    icp_industries TEXT[],
    icp_company_sizes TEXT[],
    icp_revenue_range TEXT,
    icp_locations TEXT[],
    icp_titles TEXT[],
    icp_pain_points TEXT[],
    als_weights JSONB DEFAULT '{}',
    als_learned_weights JSONB,
    als_weights_updated_at TIMESTAMPTZ,
    conversion_sample_count INTEGER DEFAULT 0,
    icp_extracted_at TIMESTAMPTZ,
    icp_extraction_source TEXT,
    icp_confirmed_at TIMESTAMPTZ,
    
    -- Platform Intelligence (Phase 20)
    data_sharing_consent BOOLEAN DEFAULT TRUE,
    data_sharing_consented_at TIMESTAMPTZ,
    
    -- Admin
    is_platform_admin BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete
);

CREATE INDEX idx_clients_subscription ON clients(subscription_status);
```

---

## Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger: Create user profile on auth signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO users (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();
```

---

## Memberships Table

```sql
CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    role membership_role NOT NULL DEFAULT 'member',
    invited_by UUID REFERENCES users(id),
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_membership UNIQUE (user_id, client_id)
);

CREATE INDEX idx_memberships_user ON memberships(user_id);
CREATE INDEX idx_memberships_client ON memberships(client_id);
```

---

## Membership Roles

| Role | Permissions |
|------|-------------|
| `owner` | Full access, billing, delete org |
| `admin` | Full access except billing |
| `member` | Create/edit campaigns, view leads |
| `viewer` | Read-only access |
