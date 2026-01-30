-- Migration: 006_elliot_realtime.sql
-- Description: Enable Supabase Realtime for Elliot monitoring tables
-- Created: 2025-02-05

-- Enable realtime for elliot_tasks
-- Note: Uses DO block to avoid errors if already added
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' 
        AND tablename = 'elliot_tasks'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE elliot_tasks;
    END IF;
END $$;

-- Enable realtime for elliot_signoff_queue
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' 
        AND tablename = 'elliot_signoff_queue'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE elliot_signoff_queue;
    END IF;
END $$;

-- Enable realtime for elliot_knowledge
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' 
        AND tablename = 'elliot_knowledge'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE elliot_knowledge;
    END IF;
END $$;

COMMENT ON TABLE elliot_tasks IS 'Tracks spawned agent tasks (REALTIME ENABLED)';
COMMENT ON TABLE elliot_signoff_queue IS 'Queue for knowledge sign-offs (REALTIME ENABLED)';
COMMENT ON TABLE elliot_knowledge IS 'Persistent knowledge base (REALTIME ENABLED)';
