-- _live_roundtrip_probe.sql — invoked by postgres_self_hosted_live_roundtrip.sh.
--
-- LIVE read+write proof of the self-hosted (Vultr VPS) Postgres. Performs a
-- REAL durable write of a unique sentinel token (passed as :token), reads it
-- back, asserts equality FROM the live server, prints server identity, then
-- deletes the sentinel so the proof is idempotent and re-runnable.
--
-- This is intentionally NOT wrapped in a rollback: a rollback would prove
-- only that a transaction can open, not that the instance durably persists a
-- committed row. The DELETE at the end restores a clean state.
--
-- ON_ERROR_STOP=1 is set by the wrapper: any failure (connect, write, read)
-- aborts with non-zero exit, which the wrapper treats as proof failure.

\set QUIET on

-- Durable liveness table on the self-hosted instance (created once).
CREATE TABLE IF NOT EXISTS public.gate_proof_liveness (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token      text NOT NULL,
    written_at timestamptz NOT NULL DEFAULT now()
);

-- Expose the token to plpgsql (the DO block below reads it via current_setting).
SET myapp.tok = :'token';

-- Real durable write (committed — psql autocommits each statement).
INSERT INTO public.gate_proof_liveness (token) VALUES (:'token');

-- Server identity — proves which live instance answered.
SELECT 'current_database=' || current_database() AS db;
SELECT 'server_addr=' || COALESCE(host(inet_server_addr()), 'local') AS addr;
SELECT 'server_version=' || current_setting('server_version') AS ver;

-- Read the sentinel back and assert it round-tripped from the live DB.
SELECT CASE
         WHEN count(*) = 1 THEN 'sentinel_readback_match=true'
         ELSE 'sentinel_readback_match=false'
       END AS readback
FROM public.gate_proof_liveness
WHERE token = :'token';

-- Hard assert: abort (non-zero exit via ON_ERROR_STOP) if the row is absent.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.gate_proof_liveness
        WHERE token = current_setting('myapp.tok', true)
    ) THEN
        RAISE EXCEPTION 'live readback failed: sentinel token not found on live server';
    END IF;
END $$;

-- Idempotent cleanup — remove this run's sentinel.
DELETE FROM public.gate_proof_liveness WHERE token = :'token';
