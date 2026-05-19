-- =============================================================================
-- KEI-124 — Composio OAuth provider tokens (data layer)
-- =============================================================================
-- Stores per-tenant OAuth tokens minted by Composio.dev for day-1 Slack, Linear,
-- and GitHub agent access. This migration is the durable data layer landed
-- ahead of the handler + routes (follow-up KEI) so that vendor onboarding can
-- proceed in parallel with implementation review.
--
-- Design rationale:
--   • Tokens are encrypted at rest with pgcrypto (mirrors customer_api_keys
--     pattern at KEI-116). The encryption secret is the same env var
--     CUSTOMER_KEY_ENCRYPTION_KEY — one secret per environment, no per-table
--     proliferation. Decryption only happens at the auth-service boundary,
--     never in long-lived application memory.
--   • composio_connection_id is the Composio.dev connected-account ID — the
--     primary key on their side. Stored so we can re-fetch / revoke via the
--     Composio API without re-running OAuth from the user.
--   • Provider list is intentionally TEXT (not an enum) at this stage; the
--     handler validates against an allowlist of {'slack','linear','github'}.
--     Tighten to a Postgres enum in a sub-KEI once the three providers are
--     wired and stable.
--   • Soft revocation only — historical tokens stay queryable for incident
--     forensics (e.g. "did this agent action use a token revoked at time X?")
--     and partial unique indexes ensure only one ACTIVE token per
--     (tenant, provider) pair.
--   • No FK on tenant_id at this migration — public.dispatcher_customers FK
--     is added in a sub-KEI alongside RLS policies (KEI-111E pattern). Keeps
--     this migration replayable in dev environments that haven't run KEI-111
--     yet.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.oauth_provider_tokens (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    -- One of: 'slack' | 'linear' | 'github'. Validated at the application
    -- layer; widen to an enum in a sub-KEI once the providers stabilise.
    provider                TEXT         NOT NULL,
    -- Composio.dev's connected-account identifier. Used to refresh / revoke
    -- through their API without re-running OAuth from the end user.
    composio_connection_id  TEXT         NOT NULL,
    -- AES-256 ciphertext via pgp_sym_encrypt(plaintext, CUSTOMER_KEY_ENCRYPTION_KEY).
    encrypted_access_token  BYTEA        NOT NULL,
    -- Nullable: some providers (e.g. GitHub OAuth apps) don't issue refresh
    -- tokens. Composio handles re-auth transparently when null.
    encrypted_refresh_token BYTEA,
    -- Wall-clock expiry of the access_token. NULL means "long-lived / managed
    -- by Composio" — handler treats null expires_at as never-expiring at the
    -- AOS layer and defers to Composio's own refresh logic.
    expires_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    -- Set when the user disconnects or admin revokes; row stays for audit.
    revoked_at              TIMESTAMPTZ
);

-- Active-only unique constraint: at most one live token per (tenant, provider).
-- Revoked rows excluded so disconnect → reconnect doesn't violate uniqueness
-- while still blocking double-store of an active token.
CREATE UNIQUE INDEX IF NOT EXISTS oauth_provider_tokens_tenant_provider_active_idx
    ON public.oauth_provider_tokens (tenant_id, provider)
    WHERE revoked_at IS NULL;

-- Lookup by composio_connection_id for webhook-driven token refresh /
-- revocation events from Composio's side.
CREATE INDEX IF NOT EXISTS oauth_provider_tokens_composio_connection_id_idx
    ON public.oauth_provider_tokens (composio_connection_id);

COMMENT ON TABLE public.oauth_provider_tokens IS
    'KEI-124: per-tenant OAuth tokens minted via Composio.dev for Slack / Linear / GitHub day-1 agent access. Encrypted at rest with pgcrypto. Handler + routes ship in follow-up KEI.';
COMMENT ON COLUMN public.oauth_provider_tokens.composio_connection_id IS
    'KEI-124: Composio.dev connected-account ID. Used to refresh or revoke without re-running user-facing OAuth.';
COMMENT ON COLUMN public.oauth_provider_tokens.encrypted_access_token IS
    'KEI-124: pgp_sym_encrypt(access_token, CUSTOMER_KEY_ENCRYPTION_KEY). Same env secret as KEI-116 customer_api_keys.';
COMMENT ON COLUMN public.oauth_provider_tokens.encrypted_refresh_token IS
    'KEI-124: nullable — some providers (GitHub OAuth apps) do not issue refresh tokens. Composio handles re-auth when null.';
COMMENT ON COLUMN public.oauth_provider_tokens.expires_at IS
    'KEI-124: nullable; null means "managed by Composio side", AOS layer treats as never-expiring locally.';
COMMENT ON COLUMN public.oauth_provider_tokens.revoked_at IS
    'KEI-124: soft revoke; row survives for audit. Partial unique index excludes revoked rows so reconnect is allowed.';
