# SKILL: Pipedrive CRM Integration

**Purpose:** Sync Keiracom prospects + outreach state into agencies' Pipedrive CRMs. Read agency-side pipeline data back into BU/CIS for closed-loop scoring.
**Status:** ⚠️ API token NOT provisioned, integration NOT wired — do NOT call until per-tenant `PIPEDRIVE_API_TOKEN` provisioned per agency client.
**Source:** Pipedrive REST API **v2** (v1 sunset 2025-12 — do NOT use v1 endpoints).
**Credentials Required:** `PIPEDRIVE_API_TOKEN` (per-user, per-workspace; obtained from Settings → Personal preferences → API in the Pipedrive dashboard).
**Cost gate:** Pipedrive free trial 14 days. Paid plans **$14–$76 AUD/seat/month** (translated from USD $9–$49 — Pipedrive does not publish AUD-native pricing). API access included on all paid tiers (no API gating).

---

## At-a-Glance (Anthropic tool-doc template — 6-vector hardened)

**What:** Two-way sync between Keiracom Business Universe and a tenant agency's Pipedrive CRM. Keiracom pushes prospects (as Persons + Leads/Deals); Pipedrive pushes status changes (deal won/lost, activity logged, note added) back via webhooks. Closes the BU → outreach → reply → outcome loop for tenants who already use Pipedrive.

**Why Pipedrive first (vs HubSpot, ActiveCampaign, GoHighLevel):**
- Dominates the AU 2–10-person agency segment per 2026 research — largest installed base in our V0 ICP.
- Cheapest seat cost ($14–$76 AUD/user/mo) — fits agency-owner budget reality.
- Smallest build surface: clean REST + official Python SDK + lightweight webhook signing. Smaller than HubSpot, simpler than GHL.
- Free tier as wedge for tenants without a CRM today.
- v1 sunset Dec-2025 means we build v2-native — zero v1 technical debt.

**When to use:**
- A tenant agency wires their Pipedrive: bulk-push their existing pipeline into BU for ICP enrichment, then auto-create Persons/Leads in Pipedrive when Keiracom finds new prospects matching their ICP.
- Closed-loop reporting: pull "deals won" / "deals lost" by source = `keiracom-bu` and feed CIS feedback so the scoring engine learns from real outcomes.
- Activity sync: when our outbound logs an open/click/reply event, push a corresponding Activity to the matching Person in Pipedrive so the agency sees Keiracom-driven engagement in their workflow.

**When NOT to use:**
- NOT for tenants who use HubSpot, GHL, ActiveCampaign, or no CRM — separate skill or no-op.
- NOT for storing PII we don't want on Pipedrive's US-region servers (no AU data residency — see Caveats).
- NOT during the 14-day-trial-only window — calls work but the tenant churns out and orphans the integration. Gate on tenant having an active paid Pipedrive subscription.
- NOT before per-tenant `PIPEDRIVE_API_TOKEN` is verified live (call `GET /api/v2/users/me` with the token; non-200 = block all writes).

**Caveats:**
- **No AU data residency.** Pipedrive stores in US AWS regions. Document this in tenant onboarding; tenants with privacy-sensitive contracts must opt-in explicitly.
- **API v1 sunset Dec 2025 — DO NOT USE v1 endpoints.** Some search results reference v1; ignore. Use `https://{company-domain}.pipedrive.com/api/v2/` exclusively.
- **Channels API sunset Feb 2026.** If the agency uses Channels for lead inbox, our integration cannot rely on it post-sunset.
- **Per-user token model.** API tokens scope to a single user, not the workspace. Token-issuing user must have permissions for every Pipedrive resource we touch (Persons, Deals, Activities, Notes, Pipelines). Recommend the agency creates a dedicated `keiracom@{agency}.com.au` Pipedrive user with full admin rights for the integration.
- **No native BAS/GST integration.** Same gap as HubSpot/ActiveCampaign. AU agencies handle tax flow manually; our integration does NOT need to address this in v1.
- **Rate limits:** documented as **80 requests/2 seconds per token** (40 req/sec ceiling). Default our client to **10 req/sec** to leave headroom and survive bursts on shared tenant tokens. 429 responses → exponential backoff (1s → 2s → 4s, max 3 retries).
- **Webhook reliability lower than HubSpot.** Pipedrive webhooks have observed delivery delays of 5–60 seconds; build for eventual consistency, not real-time.

**Returns:**
- Person create/update: `{id: int, name, email_array, phone_array, org_id, owner_id, add_time, update_time}`.
- Deal create: `{id, title, value, currency, status, stage_id, person_id, org_id, pipeline_id, add_time}`.
- Activity create: `{id, type, subject, due_date, person_id, deal_id, done: bool}`.
- Webhook event: `{event, object, current: {…full object…}, previous: {…pre-change snapshot…}, user_id, company_id, timestamp}`.

---

## Input Parameter Constraints (Poka-Yoke)

**Create / update Person:**
- `name: str` — required. ≤120 chars (Pipedrive's hard limit). Reject empty / whitespace-only.
- `email: list[dict]` — required when populating from BU. Each entry `{"value": "<email>", "primary": bool, "label": "work"|"home"|"other"}`. Validate `value` against `^[^@\s]+@[^@\s]+\.[^@\s]+$`.
- `phone: list[dict]` — optional. Same shape. AU enforcement: phone numbers normalised to E.164 with `+61` prefix; reject anything not matching `^\+61\d{9}$` unless caller passes `au_only=False`.
- `org_id: int | None` — optional. Must be an existing Pipedrive Organization (call `/api/v2/organizations/{id}` to verify before set).
- `owner_id: int` — required for write. Maps to a Pipedrive user. Default to the tenant's `keiracom_pipedrive_user_id` from tenant config.
- `custom_fields: dict[str, str]` — optional. Field keys are Pipedrive's hash-suffixed names (e.g. `5b...c4`), NOT human-readable labels. Caller must pre-translate via `/api/v2/personFields`.

**Create Deal:**
- `title: str` — required. ≤255 chars. Convention: `"{display_name} — {service}"` (e.g. `"Pymble Dental — SEO retainer"`).
- `value: int | float` — required. **AUD only** (LAW II). Cents not supported by Pipedrive — pass whole-AUD integers.
- `currency: "AUD"` — hardcoded. Reject any other currency at the wrapper level.
- `stage_id: int` — required. Maps to the agency's pipeline stage. Tenant config must declare which stage_id corresponds to "Keiracom-sourced new lead".
- `person_id: int` — required. Must exist (created from BU first).
- `pipeline_id: int` — required. Tenant config maps which pipeline new Keiracom deals enter.

**Webhook handler (inbound):**
- Verify signature header before reading body (see Webhook Signing).
- `event: str` — must match `{action}.{object}` from the documented event matrix (e.g. `added.deal`, `updated.person`, `deleted.activity`, `merged.organization`).
- Idempotency: dedupe by `(event, object.id, current.update_time)` before any side-effect insert.

**Never pass:**
- USD or other-currency `value` — rejected by wrapper (LAW II).
- Raw user input as `custom_fields` keys — must be pre-translated to Pipedrive hashes.
- A `person_id` from a different tenant's workspace — Pipedrive API will silently 404; build a tenant-id assertion at wrapper level.

---

## Input Examples (covers edge cases)

**Create a Person from a BU row:**
```json
{
  "name": "Michael Chen",
  "email": [{"value": "michael.chen@pymbledental.com.au", "primary": true, "label": "work"}],
  "phone": [{"value": "+61412345678", "primary": true, "label": "work"}],
  "owner_id": 891234,
  "custom_fields": {
    "5b3e91...c4ff": "BU-uuid-here",
    "8a2c11...d8e0": "dental"
  }
}
```

**Create a Deal for a Keiracom-sourced lead:**
```json
{
  "title": "Pymble Dental — SEO retainer",
  "value": 3000,
  "currency": "AUD",
  "stage_id": 12,
  "person_id": 1729,
  "pipeline_id": 3
}
```

**Webhook payload — deal status update (incoming):**
```json
{
  "event": "updated.deal",
  "object": "deal",
  "current": {"id": 1729, "status": "won", "value": 3000, "currency": "AUD", "stage_id": 18},
  "previous": {"id": 1729, "status": "open", "stage_id": 12},
  "user_id": 891234,
  "company_id": 88812,
  "timestamp": "2026-05-06T09:31:00Z"
}
```
Handler reads the `status` transition (open → won) → posts CIS feedback row → BU `last_outcome = won`.

---

## Response Trimming (what to persist, what to drop)

**Person create/update — PERSIST:** `id`, `name`, all `email[*].value`, all `phone[*].value`, `org_id`, `owner_id`, `add_time`, `update_time`. **DROP:** `picture_id`, `next_activity_*`, `last_activity_*`, `won_deals_count`, `lost_deals_count` — re-derived from our own pipeline data.

**Deal create — PERSIST:** `id`, `title`, `value`, `currency`, `status`, `stage_id`, `person_id`, `pipeline_id`, `add_time`, `update_time`. **DROP:** `expected_close_date`, `probability`, `formatted_value` — agency-side noise.

**Webhook event — PERSIST:** `event`, `object`, `current.id`, `current.status`, `current.update_time`, `previous.status` (for transition detection). **DROP:** full `current`/`previous` payloads beyond the fields cited — webhook table fills fast.

---

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v2/users/me` | GET | Verify token + get tenant user identity. Use during onboarding, not per-call. |
| `/api/v2/persons` | POST | Create Person. |
| `/api/v2/persons/{id}` | PATCH / GET / DELETE | Update / read / delete Person. |
| `/api/v2/persons/search?term=...` | GET | Find existing Person by email or name (dedupe before create). |
| `/api/v2/deals` | POST | Create Deal. |
| `/api/v2/deals/{id}` | PATCH / GET | Update / read Deal. |
| `/api/v2/leads` | POST | Create Lead (pre-Deal qualified prospect). |
| `/api/v2/activities` | POST | Log activity (call, email, meeting, task) against a Person/Deal. |
| `/api/v2/notes` | POST | Add a free-text note to a Person/Deal. |
| `/api/v2/organizations` | POST / GET | Manage Organisations. |
| `/api/v2/personFields` | GET | Look up custom-field hash keys (cache per tenant; refresh weekly). |
| `/api/v2/webhooks` | POST / GET / DELETE | Manage outbound webhooks. |

**Base URL:** `https://{company-domain}.pipedrive.com/api/v2/` — `company-domain` is per-tenant and stored in tenant config.
**Auth:** `?api_token=…` query parameter OR `x-api-token` header. Prefer header (less log leak risk).

---

## Webhook Events We Subscribe To

| Event | Triggers BU update? | Handler action |
|---|---|---|
| `added.person` | No (we created it) | Skip — origin was Keiracom. |
| `updated.person` | Conditional | If `email` or `phone` changed, sync back to BU (agency may have corrected our data). |
| `deleted.person` | Yes — set `business_universe.crm_deleted_at` | Flag in BU; do not push again to this tenant. |
| `added.deal` | No (Keiracom created) | Persist `deal_id` ↔ `bu_id` mapping. |
| `updated.deal` (status: open → won) | Yes — `last_outcome = won`, CIS feedback row | Closed-loop signal — high value. |
| `updated.deal` (status: open → lost) | Yes — `last_outcome = lost`, CIS feedback row, capture `lost_reason_id` | Closed-loop signal — high value. |
| `added.activity` (Keiracom-sourced reply) | No | Already in our own event log. |

**Idempotency:** dedupe by `(event, object.id, current.update_time)` before any side-effect. Pipedrive may redeliver the same event up to 3 times.

**Required response:** HTTP 200 within 10s. Anything else → Pipedrive retries up to 3x with backoff.

---

## Webhook Signing

Pipedrive supports HTTP Basic Auth for outbound webhooks (no HMAC by default). To verify authenticity:

1. When creating a webhook subscription via `POST /api/v2/webhooks`, set `http_auth_user` and `http_auth_password` to a per-tenant random secret.
2. Pipedrive includes those as `Authorization: Basic <base64(user:password)>` on every webhook delivery.
3. Our handler at `/api/pipedrive/webhook` verifies the Basic header against the per-tenant stored secret.
4. Reject any webhook without valid Basic auth as 401.

**This is weaker than HMAC-over-body (no payload integrity check)** — secret leak = full webhook spoof. Mitigations:
- Store the per-tenant secret in `tenant_config.pipedrive_webhook_secret` encrypted at rest.
- Rotate secrets quarterly.
- Reject webhooks where `company_id` does not match the authenticated tenant's `company_id` — extra defence.

---

## Error Handling (Category → Action mapping)

| HTTP | Category | Action |
|---|---|---|
| 200 / 201 | success | Persist trimmed response. |
| 400 | caller_error | Validate against Input Parameter Constraints; do NOT retry. |
| 401 | config_error | Token invalid/revoked. Disable tenant integration; alert via Slack. |
| 402 | budget | Tenant on free trial that lapsed, or hit a feature gate. Pause integration; flag tenant for billing follow-up. |
| 404 | not_found | Tenant deleted the Person/Deal — mark `crm_deleted_at` in BU; do NOT recreate. |
| 410 | sunset | Endpoint is v1 — escape hatch in code; should never fire if the wrapper is correct. Log governance debt and route to devops-6. |
| 429 | rate_limit | Exponential backoff 1s → 2s → 4s, max 3 retries. After 3, queue for off-peak retry. |
| 5xx | transient | Retry once after 5s. If still failing, escalate to devops-6. |
| webhook 401 | security | Reject with 401. Log Authorization header presence (not content) for audit. |

---

## Rate Limiting

- Documented ceiling: **80 requests / 2 seconds** per API token (= 40 req/sec).
- Default our client to **10 req/sec** for headroom; allow burst-to-30 with a leaky bucket if backlog requires.
- Bulk operations (e.g. initial pipeline import for a new tenant): use `personFields`+`/persons/search` to dedupe before write; use 5 req/sec to be courteous.

---

## Integration Points

| File | Usage |
|---|---|
| `src/integrations/pipedrive_client.py` | TBD — main client implementation. Mirror `src/integrations/resend_client.py` pattern (single class, methods per endpoint, dedupe + suppression-aware writes, `verify_webhook_basic_auth()` helper). |
| `src/api/routes/pipedrive.py` | TBD — webhook receiver mounted at `/api/pipedrive/webhook`. Per-tenant Basic-auth verification. |
| `src/engines/crm_sync.py` | TBD — orchestrator for BU → Pipedrive Person/Deal pushes; subscribed to BU change events. |
| `src/models/tenant_config.py` | TBD — per-tenant `pipedrive_company_domain`, `pipedrive_api_token` (encrypted), `pipedrive_owner_user_id`, `pipedrive_pipeline_id`, `pipedrive_webhook_secret` columns. |

**LAW XII:** direct calls to `src/integrations/pipedrive_client.py` outside skill execution are forbidden. The skill is the canonical interface.
**LAW XIII:** any change to Pipedrive call patterns updates this SKILL.md in the same PR.

---

## Governance

- **LAW II:** all Deal `value`s in AUD. Wrapper rejects non-AUD currency at the validation layer.
- **LAW VI:** prefer this skill > MCP > exec. There is currently NO Pipedrive MCP server, so all calls go through `src/integrations/pipedrive_client.py` and are wrapped by this skill.
- **LAW XII / XIII:** see Integration Points above.
- **CEO Directive (2026-05-06):** Pipedrive selected as the FIRST CRM integration based on AU agency 2–10-person segment dominance. HubSpot is #2 build priority; ActiveCampaign skipped (no AU presence); GoHighLevel deferred until AU share crosses 15%.

---

## Pending Verification (DO NOT SKIP BEFORE FIRST PRODUCTION USE)

1. **Webhook Basic-auth implementation** — confirm Pipedrive sends the `Authorization: Basic <…>` header exactly as documented; observe the first 5 deliveries to verify before enabling write-back from webhooks.
2. **Custom-field hash translation** — build a per-tenant cache of `personFields` / `dealFields` mapping human labels → hash keys. Refresh weekly or on 400 from a write.
3. **Rate-limit ceiling under burst** — empirical test: send 200 Person creates in 5 seconds, observe 429 frequency, tune client default down if needed.
4. **AU-specific test tenant** — spin up a Pipedrive trial account from an AU IP; verify pricing displays in some currency (likely USD with no local conversion) and document for tenant onboarding flow.
5. **Channels API sunset Feb 2026** — confirm we do not depend on Channels in any code path before Feb 2026.

---

## Migration Notes (from "no CRM" or other CRMs)

- **From "no CRM"**: most cost-effective onboarding. Tenant signs up for Pipedrive free trial, we create their initial pipeline + custom fields via API, push their existing BU prospects in. **Risk:** 14-day trial expiry — gate writes on paid status.
- **From HubSpot:** out of scope for this skill. Plan a separate `skills/hubspot/` skill for #2 priority. Some tenants may run both during transition; our integration should be Pipedrive-side only.
- **From ActiveCampaign / GHL:** out of scope. Note in tenant config so we route them to the right (future) integration skill.

---

## Template Checklist (mirrors leadmagic / smartlead)

- [x] **At-a-Glance block** with What / Why / When to use / When NOT to use / Caveats / Returns
- [x] **Input Parameter Constraints** with regex, length limits, AU enforcement, poka-yoke
- [x] **Input Examples** ≥3 cases including edge cases (Person, Deal, webhook payload)
- [x] **Response Trimming** PERSIST vs DROP per response type
- [x] **API Endpoints table** with method + purpose
- [x] **Webhook Events** matrix with BU update semantics
- [x] **Error Handling** table HTTP → category → action
- [x] **LAW XII governance note** — skill is canonical interface
- [x] **Pending Verification** section — every assumption that must be closed before production

---

## Why this skill exists

Per the AU agency CRM research (2026-05-06) summarised in TG: Pipedrive owns the 2–10-person AU agency segment that is our V0 ICP. Building this integration first reaches the largest reachable customer surface for the smallest dev cost. HubSpot integration follows when we move upmarket; GHL integration is contingent on AU share crossing a threshold that may not happen for 12–18 months.

Two notable differentiators we may exploit later (NOT in v1 scope):
1. **AU data residency** — no major CRM offers it. Building a Keiracom-side mirror of Pipedrive data with AU storage is a future moat.
2. **Xero/MYOB sync** — no CRM has BAS/GST integration. A future Keiracom→Xero sync is a wedge.
