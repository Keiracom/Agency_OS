# SKILL: Composio OAuth — Slack / Linear / GitHub day-1 agent access

**Purpose:** Provision OAuth tokens for Slack, Linear, and GitHub via Composio.dev so Dispatcher agents can read/write across all three on day-1 of a tenant onboarding. Single integration vendor (Composio) replaces three direct OAuth implementations.

**Status:** ⚠️ **Data layer only landed (migration `oauth_provider_tokens`).** Handler + routes ship in follow-up KEI once Dave-action prerequisites (below) complete. Do NOT call any `composio_oauth` function — none exist yet.

**Source:** Composio.dev REST API (https://docs.composio.dev/). Vendor docs pinned at the version that exists when the handler PR lands — record the docs URL + retrieval date in the handler-PR description.

**Cost gate:** Composio Free tier allows ~1k connected accounts/month, sufficient for early customer cohort. Growth tier required at ~10k+ active connections — current per-seat AUD pricing TBC in the handler-PR research pass (vendor pricing not stable at scope-time).

---

## Dave-action prerequisites (BLOCKS handler PR)

The handler + routes cannot be built without these one-time setup steps, all owned by Dave:

1. **Composio.dev account creation** — sign up Agency_OS-scout as the organisation owner.
2. **OAuth app registration on each provider** — three steps, all done from within the Composio dashboard:
   - Slack OAuth app (scopes: `channels:read`, `chat:write`, `users:read`, `team:read`).
   - Linear OAuth app (scopes: `read`, `write` over Issues, Comments, Projects).
   - GitHub OAuth app (scopes: `repo`, `read:org`, `read:user`).
3. **Issue Composio master API key** — store as env var `COMPOSIO_API_KEY` (production) and `COMPOSIO_API_KEY_DEV` (staging). Per-environment.
4. **Configure callback URL** in Composio's OAuth config: `https://api.keiracom.com/api/v1/composio/callback` (prod) and the equivalent staging host.
5. **Confirm `CUSTOMER_KEY_ENCRYPTION_KEY` is provisioned** in both prod + staging (already required by KEI-116 customer_api_keys; this skill reuses the same secret).

When all five are confirmed in `elliot_internal.api_keys_ledger`, the handler-PR is unblocked.

---

## At-a-Glance contract (for the follow-up handler PR)

**What:** Two-call OAuth flow brokered by Composio:
1. `POST /api/v1/composio/connect?provider=<slack|linear|github>` → returns `oauth_url` (Composio's hosted consent page) + CSRF `state`.
2. `GET /api/v1/composio/callback?state=<csrf>&composio_connection_id=<conn>` → exchanges `composio_connection_id` for `{access_token, refresh_token, expires_at}` via Composio's REST API, encrypts tokens with `pgp_sym_encrypt`, writes to `oauth_provider_tokens`, then 302s to `${frontend_url}/settings/integrations?provider=<p>&status=connected`.

**Why Composio (vs three direct integrations):**
- One vendor relationship vs three. One audit, one rotation policy, one rate-limit budget to monitor.
- Refresh-token lifecycle managed vendor-side — no per-provider refresh-cron in our codebase.
- Vendor takes liability for upstream OAuth-flow changes (Slack/Linear/GitHub all version their OAuth surfaces independently).

**When NOT to use:**
- NOT for end-user identity (Composio is for *bot* identities authorised by an end-user). For end-user signup use Supabase Auth (KEI-111A).
- NOT for storing customer-provided keys (those go through KEI-116 `customer_api_keys`).
- NOT if Composio.dev quota is exhausted — fail-fast in handler with a `503` and surface to `#ceo` via the existing alert path.
- NOT for any provider not in the {slack, linear, github} allowlist. The provider param is validated against a hard-coded set; widening requires a Dave-ratified KEI.

**Caveats:**
- **Composio API stability** is the single point of failure for three integrations. The handler-PR must include a `composio_health` check that runs on Dispatcher startup; failure-mode is "skip provider call, log to `interceptor_events`, surface in agent UI as 'connector temporarily unavailable'".
- **Token encryption is at-rest only.** Decrypted tokens live in process memory for the duration of a single agent action — no caching across requests. Mirror customer_api_keys handling for parity with KEI-116.
- **`composio_connection_id` is the source of truth on Composio's side.** Our `oauth_provider_tokens` row is the read-replica for our queries; if a user revokes from Composio's dashboard, Composio webhooks our `/composio/webhook` endpoint (to be added in handler-PR) and we soft-revoke the row.
- **Revocation cascade:** when a `dispatcher_customers` row is soft-deleted, all matching `oauth_provider_tokens` rows must be soft-revoked in the same transaction. Handler-PR adds that trigger.

**Returns (handler-PR shape, not in this scaffold):**
- `POST /connect`: `{oauth_url: str, state: str}`.
- `GET /callback`: `302` redirect to `${frontend_url}/settings/integrations?provider=<p>&status=connected`.
- `oauth_provider_tokens` row: `{id, tenant_id, provider, composio_connection_id, encrypted_access_token, encrypted_refresh_token, expires_at, created_at, revoked_at}`.

---

## What landed in this scaffold PR

- `supabase/migrations/20260519_kei124_oauth_provider_tokens.sql` — the durable data layer (table + two indexes + comments). Encrypted-at-rest via pgcrypto, mirrors KEI-116 customer_api_keys pattern.
- This skill doc — contract sketch + prerequisites checklist for the handler-PR.

## What ships in the follow-up KEI (bd-created post-merge)

- `src/auth/composio_oauth.py` — handler (start_oauth_flow + finalize_connection + store_tokens, ~150 LOC).
- `src/api/routes/composio.py` — POST /connect + GET /callback + (optional) POST /webhook (~150 LOC).
- `tests/auth/test_composio_oauth.py` + `tests/api/routes/test_composio.py` — vendor calls mocked.
- Settings additions for `COMPOSIO_API_KEY`, `COMPOSIO_BASE_URL`, `COMPOSIO_CALLBACK_URL`.
- Router registration in `src/api/main.py`.

The handler-PR cannot be opened until all five Dave-action prerequisites in the section above are recorded as live in `elliot_internal.api_keys_ledger`.
