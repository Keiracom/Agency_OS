-- =============================================================================
-- KEI-116 — Customer API Key Encryption-at-Rest (Part 17.6)
-- =============================================================================
-- Design rationale:
--   Plaintext API keys are NEVER stored. Each row stores:
--     • encrypted_key (BYTEA) — pgp_sym_encrypt ciphertext using the
--       CUSTOMER_KEY_ENCRYPTION_KEY env secret (AES-256 via pgcrypto).
--     • lookup_hash (TEXT)  — SHA-256(plaintext) hex stored as a 64-char
--       column, enabling O(1) existence checks and dedup without decrypting
--       all rows. Hash is non-reversible; attacker with DB read cannot
--       recover plaintext from this column alone.
--   Rotation: old row is soft-revoked (revoked_at SET) and a new row is
--   inserted; both share the same (customer_id, provider) pair. The partial
--   indexes exclude revoked rows so duplicates are blocked only for active
--   keys, while allowing historical chain: revoked → active.
--   pgcrypto extension must already exist (confirmed: YES).
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.customer_api_keys (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id  UUID         NOT NULL,
    -- provider = vendor name: 'anthropic', 'openai', 'google', etc.
    -- No FK on customers — table may not exist at migration time; enforced
    -- at application layer.
    provider     TEXT         NOT NULL,
    -- AES-256 ciphertext produced by pgp_sym_encrypt(plaintext, master_key).
    encrypted_key BYTEA       NOT NULL,
    -- SHA-256 hex of the plaintext key (64 chars). Used for O(1) lookup
    -- without decryption. Non-reversible; safe to index.
    lookup_hash  TEXT         NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    -- Set by rotate() on the incoming new row to record when rotation happened.
    rotated_at   TIMESTAMPTZ,
    -- Set by revoke() or rotate() on the outgoing old row.
    revoked_at   TIMESTAMPTZ
);

-- Partial unique index: lookup_hash must be unique among ACTIVE (non-revoked)
-- rows. Revoked rows are excluded so a rotated key can re-use the hash slot
-- once the new key is in (different hash). Two active rows for the same
-- plaintext key are blocked, which catches accidental double-store.
CREATE UNIQUE INDEX IF NOT EXISTS customer_api_keys_lookup_hash_idx
    ON public.customer_api_keys (lookup_hash)
    WHERE revoked_at IS NULL;

-- Composite index for provider-keyed lookups by customer (e.g. "give me the
-- current anthropic key for customer X"). Active rows only.
CREATE INDEX IF NOT EXISTS customer_api_keys_customer_provider_idx
    ON public.customer_api_keys (customer_id, provider)
    WHERE revoked_at IS NULL;
