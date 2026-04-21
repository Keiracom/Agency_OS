-- Add critic columns to dm_messages for critic/writer architecture
ALTER TABLE dm_messages ADD COLUMN IF NOT EXISTS critic_score INTEGER;
ALTER TABLE dm_messages ADD COLUMN IF NOT EXISTS critic_feedback TEXT;
ALTER TABLE dm_messages ADD COLUMN IF NOT EXISTS needs_review BOOLEAN DEFAULT FALSE;
