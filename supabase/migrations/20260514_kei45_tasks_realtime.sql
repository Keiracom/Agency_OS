-- KEI-45 Phase A Component 1 — enable Supabase Realtime on public.tasks
--
-- Per Dave architecture ratified ts ~1778733600 + Elliot dispatch ts ~1778739100:
-- agents subscribe to Realtime postgres_changes on tasks table; on INSERT/UPDATE
-- they receive the event instantly + run their personalised bd ready + atomic
-- claim cycle. Replaces poll-every-N-seconds idle daemon as primary mechanism.
--
-- Component 6 idle daemon remains as 15-min ceiling fallback for dead-subscription
-- recovery only (KEI-63 polling-loop already handles agent-level idle detection;
-- this is for Realtime-channel-died case).
--
-- Subscriber pattern (agent code, post-Phase-A wiring KEI-22 / KEI-51):
--     supabase.channel('tasks-events')
--       .on('postgres_changes',
--           {event: '*', schema: 'public', table: 'tasks'},
--           (payload) => run_bd_ready_and_claim_cycle(payload))
--       .subscribe();
--
-- Migration is idempotent: ALTER PUBLICATION ADD TABLE is a no-op if already present.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime' AND tablename = 'tasks'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.tasks;
    END IF;
END $$;

-- Optional richer-event-shape trigger.
-- Default Realtime postgres_changes gives row-level INSERT/UPDATE/DELETE payloads.
-- This trigger publishes a derived 'task-event' Notify channel with semantic event
-- types (new_available / claimed / completed / unclaimed) for agents that prefer
-- semantic events over raw row diffs.
-- Subscribers use pg_notify('task-event', payload).

CREATE OR REPLACE FUNCTION public.kei45_emit_task_event() RETURNS trigger
LANGUAGE plpgsql AS $func$
DECLARE
    event_type  text;
    payload     jsonb;
    status_available CONSTANT text := 'available';
BEGIN
    IF TG_OP = 'INSERT' AND NEW.status = status_available THEN
        event_type := 'new_available';
    ELSIF TG_OP = 'UPDATE' AND OLD.status = status_available AND NEW.status = 'active' THEN
        event_type := 'claimed';
    ELSIF TG_OP = 'UPDATE' AND OLD.status = 'active' AND NEW.status = 'done' THEN
        event_type := 'completed';
    ELSIF TG_OP = 'UPDATE' AND OLD.status = 'active' AND NEW.status = status_available THEN
        event_type := 'unclaimed';
    ELSE
        event_type := 'other';
    END IF;

    payload := jsonb_build_object(
        'event_type', event_type,
        'id',         NEW.id,
        'title',      NEW.title,
        'status',     NEW.status,
        'priority',   NEW.priority,
        'claimed_by', NEW.claimed_by,
        'tags',       NEW.tags,
        'op',         TG_OP,
        'at',         now()
    );

    PERFORM pg_notify('task_event', payload::text);
    RETURN NEW;
END
$func$;

DROP TRIGGER IF EXISTS kei45_task_event_trigger ON public.tasks;

CREATE TRIGGER kei45_task_event_trigger
AFTER INSERT OR UPDATE ON public.tasks
FOR EACH ROW EXECUTE FUNCTION public.kei45_emit_task_event();
