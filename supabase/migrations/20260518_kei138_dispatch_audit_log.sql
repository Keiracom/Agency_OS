-- KEI-138 — Dispatch HMAC audit log.
--
-- Captures one row per dispatch-queue pop in src/relay/relay_consumer.py.
-- Used for:
--   1. Signed-vs-unsigned dispatch metrics (aggregate on hmac_status).
--   2. Rotation validation — count rows where secret_index=1 (signed with PREV).
--   3. Tamper detection forensics.
--
-- Plaintext payload body is NOT stored. Only the canonical SHA-256 hash
-- (excluding the hmac field) is recorded; payload content can include
-- dispatch briefs which may contain sensitive context.
--
-- Indexed for the two hot query paths:
--   - WHERE created_at >= NOW() - INTERVAL '1 hour' GROUP BY hmac_status
--   - WHERE hmac_status = 'signed_invalid' ORDER BY created_at DESC

CREATE TABLE IF NOT EXISTS public.dispatch_audit_log (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    queue          text NOT NULL,
    target         text NOT NULL,
    hmac_status    text NOT NULL CHECK (hmac_status IN (
                       'signed_verified',
                       'signed_invalid',
                       'unsigned',
                       'no_secret'
                   )),
    secret_index   smallint NOT NULL DEFAULT -1,
    payload_hash   text NOT NULL,
    reason         text,
    created_at     timestamp with time zone NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS dispatch_audit_log_created_at_status_idx
    ON public.dispatch_audit_log (created_at DESC, hmac_status);

CREATE INDEX IF NOT EXISTS dispatch_audit_log_invalid_idx
    ON public.dispatch_audit_log (created_at DESC)
    WHERE hmac_status = 'signed_invalid';

COMMENT ON TABLE public.dispatch_audit_log IS
    'KEI-138 — one row per dispatch queue pop. Stores hmac outcome + canonical payload hash. Payload body is NOT persisted.';

COMMENT ON COLUMN public.dispatch_audit_log.secret_index IS
    '0 = signed with current INBOX_HMAC_SECRET; 1 = signed with INBOX_HMAC_SECRET_PREV (rotation window still active); -1 = not applicable (unsigned / no_secret / signed_invalid).';
