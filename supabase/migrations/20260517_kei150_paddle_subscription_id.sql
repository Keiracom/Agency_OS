-- KEI-150: Add paddle_subscription_id to public.customers
-- Paddle MoR account scaffold — nullable text column, safe to run multiple times.

ALTER TABLE public.customers
  ADD COLUMN IF NOT EXISTS paddle_subscription_id TEXT;

COMMENT ON COLUMN public.customers.paddle_subscription_id IS
  'Paddle subscription ID assigned by Paddle MoR on first successful payment (KEI-150).';
