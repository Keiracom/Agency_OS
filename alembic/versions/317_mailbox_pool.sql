-- Mailbox pool for MailboxRotator (PHASE-2-SLICE-5 Track A)
CREATE TABLE IF NOT EXISTS mailbox_pool (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mailbox_id TEXT NOT NULL UNIQUE,
    client_id UUID NOT NULL,
    channel TEXT NOT NULL DEFAULT 'email',
    last_send_at TIMESTAMPTZ,
    daily_count INTEGER NOT NULL DEFAULT 0,
    warming_day INTEGER,
    healthy BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mailbox_pool_client_channel ON mailbox_pool (client_id, channel);
CREATE INDEX IF NOT EXISTS idx_mailbox_pool_lru ON mailbox_pool (last_send_at);
