-- KEI-100 / Linear KEI-73 — T0.2 LiteLLM governance_tier alias resolution cache
-- 24h TTL. Reader skips rows where expires_at < now().
-- Populated by: scripts/litellm_boot_check.py (boot-time) + interceptor (per-call).

CREATE TABLE IF NOT EXISTS public.litellm_alias_cache (
  alias              text PRIMARY KEY,
  resolved_model     text NOT NULL,
  resolved_provider  text NOT NULL,
  api_key_ref        text,
  cached_at          timestamptz NOT NULL DEFAULT now(),
  expires_at         timestamptz NOT NULL DEFAULT (now() + interval '24 hours')
);

CREATE INDEX IF NOT EXISTS litellm_alias_cache_expires_at_idx
  ON public.litellm_alias_cache (expires_at);

CREATE INDEX IF NOT EXISTS litellm_alias_cache_provider_idx
  ON public.litellm_alias_cache (resolved_provider);

COMMENT ON TABLE public.litellm_alias_cache IS
  'KEI-100 T0.2: LiteLLM governance_tier alias resolution cache. 24h TTL. Reader filters expires_at >= now().';
COMMENT ON COLUMN public.litellm_alias_cache.alias IS
  'governance_tier_fast | governance_tier_premium (or _unavailable suffix for degraded providers)';
COMMENT ON COLUMN public.litellm_alias_cache.api_key_ref IS
  'env var name (ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY) — never the secret itself';
