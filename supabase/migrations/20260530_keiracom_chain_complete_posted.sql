-- ============================================================================
-- 20260530_keiracom_chain_complete_posted.sql
--
-- Durable dedup ledger for v1_chain_orchestrator chain-complete posts.
-- Replaces an in-process flag (lost on dispatcher restart) that allowed a
-- triplicate / duplicate #ceo post on NATS redeliver after restart.
--
-- task: Agency_OS-wdcw (Pre-Phase-1 hygiene, Dave-authorised).
--
-- USAGE
--   The orchestrator's _post_chain_complete attempts INSERT ON CONFLICT DO
--   NOTHING RETURNING chain_id. If RETURNING returns the row, this is the
--   FIRST post for the chain — proceed with the HTTP POST to
--   /dispatcher/chain_complete. If RETURNING is empty, a concurrent / prior
--   process already claimed → SKIP the HTTP POST. Atomic by Postgres MVCC,
--   correct under restart + concurrent consumers.
--
-- KEI-87 convention: SET LOCAL agency_os.callsign = 'dave' per the
-- established migration pattern for public-schema DDL.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE IF NOT EXISTS public.keiracom_chain_complete_posted (
    chain_id   TEXT         PRIMARY KEY,
    posted_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.keiracom_chain_complete_posted IS
    'Agency_OS-wdcw — durable dedup ledger for v1_chain_orchestrator chain-'
    'complete posts. One row per chain_id that has been notified to #ceo. '
    'Survives dispatcher restart; replaces the in-process complete_posted '
    'flag (lost on restart, allowed dup posts on NATS redeliver).';
