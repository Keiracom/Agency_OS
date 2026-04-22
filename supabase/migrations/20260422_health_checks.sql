CREATE TABLE IF NOT EXISTS public.health_checks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    signal_type TEXT NOT NULL,  -- 'flow_failure', 'service_down', 'key_expired', 'test_fail', 'worker_stale'
    tier INTEGER NOT NULL,      -- 1, 2, or 3
    severity TEXT NOT NULL DEFAULT 'MEDIUM',  -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'detected',  -- 'detected', 'fixing', 'fixed', 'watching', 'escalated', 'resolved'
    fix_pr_url TEXT,
    locked_by TEXT,             -- T1 fix ID for concurrency lock
    locked_at TIMESTAMPTZ,
    escalated_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_health_checks_status ON public.health_checks (status);
CREATE INDEX IF NOT EXISTS idx_health_checks_tier ON public.health_checks (tier);
