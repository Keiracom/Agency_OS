-- F2.1: evo_flow_callbacks table
-- Stores Prefect flow completion callbacks written by src/prefect_utils/callback_writer.py
-- Polled by src/evo/callback_poller.py for Telegram alerts.

CREATE TABLE IF NOT EXISTS public.evo_flow_callbacks (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_name      TEXT        NOT NULL,
    flow_run_id    TEXT,
    deployment_id  TEXT,
    status         TEXT        NOT NULL CHECK (status IN ('completed', 'failed', 'crashed')),
    result_summary JSONB,
    consumed_at    TIMESTAMPTZ,
    consumed_by    TEXT,
    created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_efc_flow_name   ON public.evo_flow_callbacks(flow_name);
CREATE INDEX IF NOT EXISTS idx_efc_status      ON public.evo_flow_callbacks(status);
CREATE INDEX IF NOT EXISTS idx_efc_consumed_at ON public.evo_flow_callbacks(consumed_at);

COMMENT ON TABLE public.evo_flow_callbacks IS
    'Prefect flow completion callbacks. Written by callback_writer.py, polled by callback_poller.py. F2.1.';
