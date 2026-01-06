-- Migration: 030_customer_import.sql
-- Phase: 24F - Customer Import & Platform Intelligence
-- Purpose: Import customers, manage suppression, aggregate buyer signals

-- ============================================================================
-- CLIENT CUSTOMERS (Private - per-client)
-- ============================================================================

-- Client's existing customers for suppression and social proof
CREATE TABLE IF NOT EXISTS client_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Company identification
    company_name TEXT NOT NULL,
    domain TEXT,  -- Extracted from email or provided (for matching)
    industry TEXT,
    employee_count_range TEXT,

    -- Primary contact (optional)
    contact_email TEXT,
    contact_name TEXT,
    contact_title TEXT,

    -- Customer data
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'churned', 'prospect')),
    customer_since DATE,
    churned_at DATE,
    deal_value DECIMAL(12,2),

    -- Social proof settings
    can_use_as_reference BOOLEAN DEFAULT false,
    case_study_url TEXT,
    testimonial TEXT,
    logo_approved BOOLEAN DEFAULT false,

    -- Import metadata
    source TEXT NOT NULL CHECK (source IN ('hubspot', 'pipedrive', 'close', 'csv', 'manual')),
    crm_id TEXT,  -- ID in their CRM
    imported_at TIMESTAMPTZ DEFAULT NOW(),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- One customer per domain per client
    UNIQUE (client_id, domain)
);

-- ============================================================================
-- SUPPRESSION LIST (Per-client domain blocking)
-- ============================================================================

-- Domain-level blocking for existing customers, competitors, etc.
CREATE TABLE IF NOT EXISTS suppression_list (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- What to block (domain is primary, email for edge cases)
    domain TEXT,
    email TEXT,
    company_name TEXT,  -- Fuzzy match fallback

    -- Why suppressed
    reason TEXT NOT NULL CHECK (reason IN (
        'existing_customer',
        'past_customer',
        'competitor',
        'do_not_contact',
        'unsubscribed',
        'bounced',
        'other'
    )),

    -- Reference
    source TEXT NOT NULL CHECK (source IN (
        'crm_import',
        'csv_import',
        'manual',
        'bounce',
        'unsubscribe',
        'closer_engine'
    )),
    customer_id UUID REFERENCES client_customers(id) ON DELETE SET NULL,

    -- Metadata
    notes TEXT,
    expires_at TIMESTAMPTZ,  -- Some suppressions might expire

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- One domain per client
    UNIQUE (client_id, domain)
);

-- Additional index for email lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_suppression_email_client
    ON suppression_list(client_id, email)
    WHERE email IS NOT NULL;

-- ============================================================================
-- PLATFORM BUYER SIGNALS (Aggregated, anonymized - platform-wide)
-- ============================================================================

-- Aggregated buyer intelligence from all clients
CREATE TABLE IF NOT EXISTS platform_buyer_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company identification (NO client reference - anonymized)
    domain TEXT NOT NULL UNIQUE,
    company_name TEXT,
    industry TEXT,
    employee_count_range TEXT,

    -- Aggregated signals
    times_bought INTEGER DEFAULT 1,  -- How many times this company bought from ANY client
    total_value DECIMAL(12,2),
    avg_deal_value DECIMAL(12,2),
    services_bought TEXT[],  -- ['seo', 'web_design', 'ppc'] - anonymized service types

    -- For lead scoring
    buyer_score INTEGER DEFAULT 50 CHECK (buyer_score >= 0 AND buyer_score <= 100),

    -- Timestamps
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_converted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Client customers indexes
CREATE INDEX IF NOT EXISTS idx_client_customers_domain
    ON client_customers(domain)
    WHERE domain IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_client_customers_client
    ON client_customers(client_id);
CREATE INDEX IF NOT EXISTS idx_client_customers_status
    ON client_customers(status);
CREATE INDEX IF NOT EXISTS idx_client_customers_referenceable
    ON client_customers(client_id, can_use_as_reference)
    WHERE can_use_as_reference = true;

-- Suppression list indexes
CREATE INDEX IF NOT EXISTS idx_suppression_domain
    ON suppression_list(domain)
    WHERE domain IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_suppression_client
    ON suppression_list(client_id);
CREATE INDEX IF NOT EXISTS idx_suppression_reason
    ON suppression_list(reason);

-- Platform buyer signals indexes
CREATE INDEX IF NOT EXISTS idx_platform_buyers_domain
    ON platform_buyer_signals(domain);
CREATE INDEX IF NOT EXISTS idx_platform_buyers_score
    ON platform_buyer_signals(buyer_score DESC);
CREATE INDEX IF NOT EXISTS idx_platform_buyers_industry
    ON platform_buyer_signals(industry)
    WHERE industry IS NOT NULL;

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE client_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppression_list ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_buyer_signals ENABLE ROW LEVEL SECURITY;

-- Client customers policies (private per-client)
CREATE POLICY "Clients can view own customers"
    ON client_customers FOR SELECT
    USING (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

CREATE POLICY "Clients can insert own customers"
    ON client_customers FOR INSERT
    WITH CHECK (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

CREATE POLICY "Clients can update own customers"
    ON client_customers FOR UPDATE
    USING (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

CREATE POLICY "Clients can delete own customers"
    ON client_customers FOR DELETE
    USING (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

-- Suppression list policies (private per-client)
CREATE POLICY "Clients can view own suppression list"
    ON suppression_list FOR SELECT
    USING (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

CREATE POLICY "Clients can insert own suppression"
    ON suppression_list FOR INSERT
    WITH CHECK (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

CREATE POLICY "Clients can delete own suppression"
    ON suppression_list FOR DELETE
    USING (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

-- Platform buyer signals (public read for scoring, service-write for updates)
CREATE POLICY "All authenticated users can read buyer signals"
    ON platform_buyer_signals FOR SELECT
    USING (auth.role() = 'authenticated');

CREATE POLICY "Service role can manage buyer signals"
    ON platform_buyer_signals FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Platform admins can view all customers (for support)
CREATE POLICY "Platform admins can view all customers"
    ON client_customers FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.is_platform_admin = true
        )
    );

-- Platform admins can view all suppression
CREATE POLICY "Platform admins can view all suppression"
    ON suppression_list FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.is_platform_admin = true
        )
    );

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update updated_at for client_customers
CREATE TRIGGER update_client_customers_updated_at
    BEFORE UPDATE ON client_customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at for platform_buyer_signals
CREATE TRIGGER update_platform_buyer_signals_updated_at
    BEFORE UPDATE ON platform_buyer_signals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Extract domain from email address
CREATE OR REPLACE FUNCTION extract_domain_from_email(email TEXT)
RETURNS TEXT AS $$
BEGIN
    IF email IS NULL OR email = '' THEN
        RETURN NULL;
    END IF;
    -- Extract everything after the @ sign
    RETURN LOWER(SPLIT_PART(email, '@', 2));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Check if a domain/email is suppressed for a client
CREATE OR REPLACE FUNCTION is_suppressed(
    p_client_id UUID,
    p_email TEXT DEFAULT NULL,
    p_domain TEXT DEFAULT NULL
)
RETURNS TABLE (
    suppressed BOOLEAN,
    reason TEXT,
    details TEXT
) AS $$
DECLARE
    v_domain TEXT;
    v_suppression RECORD;
BEGIN
    -- Extract domain from email if not provided
    v_domain := COALESCE(p_domain, extract_domain_from_email(p_email));

    -- Check domain-level suppression first
    IF v_domain IS NOT NULL THEN
        SELECT s.reason INTO v_suppression
        FROM suppression_list s
        WHERE s.client_id = p_client_id
        AND s.domain = v_domain
        AND (s.expires_at IS NULL OR s.expires_at > NOW())
        LIMIT 1;

        IF FOUND THEN
            RETURN QUERY SELECT
                true::BOOLEAN,
                v_suppression.reason,
                format('Domain %s is suppressed: %s', v_domain, v_suppression.reason);
            RETURN;
        END IF;
    END IF;

    -- Check email-level suppression
    IF p_email IS NOT NULL THEN
        SELECT s.reason INTO v_suppression
        FROM suppression_list s
        WHERE s.client_id = p_client_id
        AND s.email = LOWER(p_email)
        AND (s.expires_at IS NULL OR s.expires_at > NOW())
        LIMIT 1;

        IF FOUND THEN
            RETURN QUERY SELECT
                true::BOOLEAN,
                v_suppression.reason,
                format('Email %s is suppressed: %s', p_email, v_suppression.reason);
            RETURN;
        END IF;
    END IF;

    -- Not suppressed
    RETURN QUERY SELECT false::BOOLEAN, NULL::TEXT, NULL::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get buyer signal boost for scoring
CREATE OR REPLACE FUNCTION get_buyer_score_boost(p_domain TEXT)
RETURNS INTEGER AS $$
DECLARE
    v_buyer_score INTEGER;
BEGIN
    SELECT buyer_score INTO v_buyer_score
    FROM platform_buyer_signals
    WHERE domain = LOWER(p_domain);

    IF NOT FOUND THEN
        RETURN 0;  -- No boost for unknown company
    END IF;

    -- Convert buyer_score (0-100) to boost points (max 15)
    RETURN LEAST(FLOOR(v_buyer_score * 0.15), 15);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Update or create platform buyer signal
CREATE OR REPLACE FUNCTION upsert_buyer_signal(
    p_domain TEXT,
    p_company_name TEXT DEFAULT NULL,
    p_industry TEXT DEFAULT NULL,
    p_deal_value DECIMAL DEFAULT NULL,
    p_service_type TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_signal_id UUID;
    v_times_bought INTEGER;
    v_total_value DECIMAL;
    v_services TEXT[];
    v_buyer_score INTEGER;
BEGIN
    -- Try to find existing signal
    SELECT id, times_bought, total_value, services_bought
    INTO v_signal_id, v_times_bought, v_total_value, v_services
    FROM platform_buyer_signals
    WHERE domain = LOWER(p_domain);

    IF FOUND THEN
        -- Update existing signal
        v_times_bought := v_times_bought + 1;
        v_total_value := COALESCE(v_total_value, 0) + COALESCE(p_deal_value, 0);

        -- Add service type if new
        IF p_service_type IS NOT NULL AND NOT (p_service_type = ANY(COALESCE(v_services, ARRAY[]::TEXT[]))) THEN
            v_services := ARRAY_APPEND(COALESCE(v_services, ARRAY[]::TEXT[]), p_service_type);
        END IF;

        -- Calculate new buyer score
        v_buyer_score := 50;  -- Base
        IF v_times_bought >= 3 THEN
            v_buyer_score := v_buyer_score + 30;
        ELSIF v_times_bought >= 2 THEN
            v_buyer_score := v_buyer_score + 20;
        ELSE
            v_buyer_score := v_buyer_score + 10;
        END IF;

        IF array_length(v_services, 1) >= 2 THEN
            v_buyer_score := v_buyer_score + 10;
        END IF;

        IF COALESCE(v_total_value / v_times_bought, 0) >= 5000 THEN
            v_buyer_score := v_buyer_score + 10;
        END IF;

        v_buyer_score := LEAST(v_buyer_score, 100);

        UPDATE platform_buyer_signals
        SET times_bought = v_times_bought,
            total_value = v_total_value,
            avg_deal_value = v_total_value / v_times_bought,
            services_bought = v_services,
            buyer_score = v_buyer_score,
            last_converted_at = NOW(),
            updated_at = NOW(),
            company_name = COALESCE(company_name, p_company_name),
            industry = COALESCE(industry, p_industry)
        WHERE id = v_signal_id
        RETURNING id INTO v_signal_id;
    ELSE
        -- Create new signal
        v_buyer_score := 60;  -- Default "known buyer" boost

        INSERT INTO platform_buyer_signals (
            domain, company_name, industry, times_bought,
            total_value, avg_deal_value, services_bought,
            buyer_score, last_converted_at
        ) VALUES (
            LOWER(p_domain), p_company_name, p_industry, 1,
            p_deal_value, p_deal_value,
            CASE WHEN p_service_type IS NOT NULL THEN ARRAY[p_service_type] ELSE ARRAY[]::TEXT[] END,
            v_buyer_score, NOW()
        )
        RETURNING id INTO v_signal_id;
    END IF;

    RETURN v_signal_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get customer import stats for a client
CREATE OR REPLACE FUNCTION get_customer_import_stats(p_client_id UUID)
RETURNS TABLE (
    total_customers BIGINT,
    active_customers BIGINT,
    churned_customers BIGINT,
    suppressed_domains BIGINT,
    referenceable_customers BIGINT,
    total_deal_value DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM client_customers WHERE client_id = p_client_id)::BIGINT,
        (SELECT COUNT(*) FROM client_customers WHERE client_id = p_client_id AND status = 'active')::BIGINT,
        (SELECT COUNT(*) FROM client_customers WHERE client_id = p_client_id AND status = 'churned')::BIGINT,
        (SELECT COUNT(*) FROM suppression_list WHERE client_id = p_client_id)::BIGINT,
        (SELECT COUNT(*) FROM client_customers WHERE client_id = p_client_id AND can_use_as_reference = true)::BIGINT,
        (SELECT COALESCE(SUM(deal_value), 0) FROM client_customers WHERE client_id = p_client_id)::DECIMAL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE client_customers IS 'Client existing customers - for suppression and social proof';
COMMENT ON TABLE suppression_list IS 'Domain/email-level blocking per client';
COMMENT ON TABLE platform_buyer_signals IS 'Aggregated anonymized buyer intelligence for lead scoring';

COMMENT ON COLUMN client_customers.can_use_as_reference IS 'Client has approved using this customer as a reference in outreach';
COMMENT ON COLUMN client_customers.logo_approved IS 'Client has approved showing customer logo';
COMMENT ON COLUMN suppression_list.expires_at IS 'Optional expiration for temporary suppressions';
COMMENT ON COLUMN platform_buyer_signals.times_bought IS 'Number of times this company bought from ANY client (aggregated)';
COMMENT ON COLUMN platform_buyer_signals.buyer_score IS 'Score 0-100 indicating likelihood to buy agency services';
