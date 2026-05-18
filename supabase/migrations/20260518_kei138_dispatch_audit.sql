-- KEI-138 (Agency_OS-y52ohx) — dispatch HMAC audit log + signature metrics view.
--
-- WHY
--   No machine-readable trail exists for who signed / who verified inbox
--   dispatches. Rotation, incident triage, and "signed vs unsigned" telemetry
--   all required reading logs by hand. This table closes that gap.
--
-- WHO WRITES
--   - scripts/sign_dispatch.py            on every signed write     (action=sign)
--   - src/relay/relay_consumer.py         on every verify attempt   (action=verify)
--   - src/security/inbox_hmac.audit()     direct callers            (action=sign|verify)
--
-- WHAT IS PRIVATE
--   `secret_fingerprint` is the first 12 hex chars of SHA-256(secret) — it
--   identifies which key was used WITHOUT revealing the key itself. Safe to
--   log + display in dashboards.
--
-- HOW THIS POWERS ROTATION
--   During a rotation window two secrets are valid (INBOX_HMAC_SECRET +
--   INBOX_HMAC_SECRET_PREVIOUS). The fingerprint column lets ops verify
--   "no production dispatch is still signing with the OLD secret" before
--   decommissioning it — query `dispatch_signature_metrics` filtered by
--   `secret_fingerprint = '<old-fp>'` and confirm count=0 over the last 24h.

CREATE TABLE IF NOT EXISTS public.dispatch_audit (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ts                  timestamptz NOT NULL DEFAULT NOW(),
    action              text NOT NULL CHECK (action IN ('sign', 'verify')),
    result              text NOT NULL CHECK (result IN ('ok', 'mismatch', 'unsigned', 'no_secret', 'error')),
    payload_id          text,
    target              text,
    actor               text,
    secret_fingerprint  text,
    file_path           text,
    reason              text
);

COMMENT ON TABLE public.dispatch_audit IS
    'KEI-138 — audit trail of every inbox HMAC sign + verify. secret_fingerprint = SHA-256(secret)[:12] — safe to log.';

CREATE INDEX IF NOT EXISTS dispatch_audit_ts_idx
    ON public.dispatch_audit (ts DESC);

CREATE INDEX IF NOT EXISTS dispatch_audit_result_idx
    ON public.dispatch_audit (result);

CREATE INDEX IF NOT EXISTS dispatch_audit_action_target_idx
    ON public.dispatch_audit (action, target);

-- Signed-vs-unsigned dispatch metrics (signature posture over time).
-- Per-hour rollup of verify outcomes by target + secret fingerprint.
CREATE OR REPLACE VIEW public.dispatch_signature_metrics AS
SELECT
    DATE_TRUNC('hour', ts)             AS hour,
    target,
    result,
    secret_fingerprint,
    COUNT(*)                           AS dispatches
FROM public.dispatch_audit
WHERE action = 'verify'
GROUP BY DATE_TRUNC('hour', ts), target, result, secret_fingerprint
ORDER BY hour DESC;

COMMENT ON VIEW public.dispatch_signature_metrics IS
    'KEI-138 — hourly rollup of verify outcomes. Query secret_fingerprint to confirm rotation is complete (old fp count = 0).';
