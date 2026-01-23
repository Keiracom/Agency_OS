-- Migration: 052_soft_delete_suppression_customers.sql
-- Purpose: Add soft delete support to suppression_list and client_customers tables
-- Fixes: Rule 14 violation - hard deletes in suppression_service.py and customer_import_service.py

-- ============================================================================
-- ADD DELETED_AT COLUMNS
-- ============================================================================

-- Add deleted_at to suppression_list
ALTER TABLE suppression_list
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

-- Add deleted_at to client_customers
ALTER TABLE client_customers
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

-- ============================================================================
-- UPDATE INDEXES TO EXCLUDE SOFT-DELETED ROWS
-- ============================================================================

-- Drop and recreate suppression indexes with soft delete filter
DROP INDEX IF EXISTS idx_suppression_domain;
CREATE INDEX idx_suppression_domain
    ON suppression_list(domain)
    WHERE domain IS NOT NULL AND deleted_at IS NULL;

DROP INDEX IF EXISTS idx_suppression_client;
CREATE INDEX idx_suppression_client
    ON suppression_list(client_id)
    WHERE deleted_at IS NULL;

DROP INDEX IF EXISTS idx_suppression_reason;
CREATE INDEX idx_suppression_reason
    ON suppression_list(reason)
    WHERE deleted_at IS NULL;

DROP INDEX IF EXISTS idx_suppression_email_client;
CREATE UNIQUE INDEX idx_suppression_email_client
    ON suppression_list(client_id, email)
    WHERE email IS NOT NULL AND deleted_at IS NULL;

-- Drop and recreate client_customers indexes with soft delete filter
DROP INDEX IF EXISTS idx_client_customers_domain;
CREATE INDEX idx_client_customers_domain
    ON client_customers(domain)
    WHERE domain IS NOT NULL AND deleted_at IS NULL;

DROP INDEX IF EXISTS idx_client_customers_client;
CREATE INDEX idx_client_customers_client
    ON client_customers(client_id)
    WHERE deleted_at IS NULL;

DROP INDEX IF EXISTS idx_client_customers_status;
CREATE INDEX idx_client_customers_status
    ON client_customers(status)
    WHERE deleted_at IS NULL;

DROP INDEX IF EXISTS idx_client_customers_referenceable;
CREATE INDEX idx_client_customers_referenceable
    ON client_customers(client_id, can_use_as_reference)
    WHERE can_use_as_reference = true AND deleted_at IS NULL;

-- ============================================================================
-- UPDATE UNIQUE CONSTRAINTS
-- ============================================================================

-- Update suppression_list unique constraint to allow re-adding soft-deleted entries
-- Drop existing constraint and recreate with partial index
ALTER TABLE suppression_list DROP CONSTRAINT IF EXISTS suppression_list_client_id_domain_key;
CREATE UNIQUE INDEX idx_suppression_list_client_domain_unique
    ON suppression_list(client_id, domain)
    WHERE deleted_at IS NULL;

-- Update client_customers unique constraint
ALTER TABLE client_customers DROP CONSTRAINT IF EXISTS client_customers_client_id_domain_key;
CREATE UNIQUE INDEX idx_client_customers_client_domain_unique
    ON client_customers(client_id, domain)
    WHERE deleted_at IS NULL;

-- ============================================================================
-- UPDATE is_suppressed FUNCTION TO CHECK deleted_at
-- ============================================================================

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

    -- Check domain-level suppression first (excluding soft-deleted)
    IF v_domain IS NOT NULL THEN
        SELECT s.reason INTO v_suppression
        FROM suppression_list s
        WHERE s.client_id = p_client_id
        AND s.domain = v_domain
        AND s.deleted_at IS NULL  -- Soft delete check
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

    -- Check email-level suppression (excluding soft-deleted)
    IF p_email IS NOT NULL THEN
        SELECT s.reason INTO v_suppression
        FROM suppression_list s
        WHERE s.client_id = p_client_id
        AND s.email = LOWER(p_email)
        AND s.deleted_at IS NULL  -- Soft delete check
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

-- ============================================================================
-- UPDATE get_customer_import_stats FUNCTION
-- ============================================================================

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
        (SELECT COUNT(*) FROM client_customers WHERE client_id = p_client_id AND deleted_at IS NULL)::BIGINT,
        (SELECT COUNT(*) FROM client_customers WHERE client_id = p_client_id AND status = 'active' AND deleted_at IS NULL)::BIGINT,
        (SELECT COUNT(*) FROM client_customers WHERE client_id = p_client_id AND status = 'churned' AND deleted_at IS NULL)::BIGINT,
        (SELECT COUNT(*) FROM suppression_list WHERE client_id = p_client_id AND deleted_at IS NULL)::BIGINT,
        (SELECT COUNT(*) FROM client_customers WHERE client_id = p_client_id AND can_use_as_reference = true AND deleted_at IS NULL)::BIGINT,
        (SELECT COALESCE(SUM(deal_value), 0) FROM client_customers WHERE client_id = p_client_id AND deleted_at IS NULL)::DECIMAL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON COLUMN suppression_list.deleted_at IS 'Soft delete timestamp (Rule 14)';
COMMENT ON COLUMN client_customers.deleted_at IS 'Soft delete timestamp (Rule 14)';

-- ============================================================================
-- VERIFICATION CHECKLIST
-- ============================================================================
-- [x] Added deleted_at to suppression_list
-- [x] Added deleted_at to client_customers
-- [x] Updated indexes with soft delete filter
-- [x] Updated unique constraints as partial indexes
-- [x] Updated is_suppressed function
-- [x] Updated get_customer_import_stats function
