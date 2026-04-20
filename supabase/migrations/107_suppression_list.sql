CREATE TABLE IF NOT EXISTS public.suppression_list (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL,
  suppressed_at timestamptz NOT NULL DEFAULT now(),
  reason text NOT NULL,
  channel text NOT NULL DEFAULT 'all',
  source text NOT NULL DEFAULT 'system',
  UNIQUE(email, channel)
);
CREATE INDEX IF NOT EXISTS suppression_list_email_idx ON public.suppression_list (email);
CREATE INDEX IF NOT EXISTS suppression_list_reason_idx ON public.suppression_list (reason);
