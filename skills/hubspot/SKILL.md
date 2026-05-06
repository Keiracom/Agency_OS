# SKILL: HubSpot CRM Integration

**Purpose:** Sync Keiracom prospects + outreach state into agencies' HubSpot CRMs (mid-size segment, 10–50 employees). Read agency-side pipeline data back into BU/CIS for closed-loop scoring. Second CRM connector after Pipedrive (#571).
**Status:** ⚠️ API token NOT provisioned, integration NOT wired — do NOT call until per-tenant `HUBSPOT_PRIVATE_APP_TOKEN` provisioned per agency client.
**Source:** HubSpot CRM API **2026 date-based versioning** (e.g. `2026-01-01`). Use the latest stable date version; 18-month support window per version.
**Credentials Required:** `HUBSPOT_PRIVATE_APP_TOKEN` (per-portal Private App access token; obtained from Settings → Integrations → Private Apps → Create private app, then assign scopes).
**Cost gate:** HubSpot Free CRM exists but is NOT useful for tenant integrations (limited API + no custom properties). **Professional plan minimum — $648 AUD/month** (translated from USD ~$418, with mandatory $5.7k AUD onboarding fee). Enterprise: $2,160 AUD/month + $10.08k onboarding. (LAW II — all AUD; USD × 1.55.)

---

## At-a-Glance (Anthropic tool-doc template — 6-vector hardened)

**What:** Two-way sync between Keiracom Business Universe and a tenant agency's HubSpot CRM. Keiracom pushes prospects (as Contacts → Deals); HubSpot pushes status changes (deal won/lost, contact engagement) back via webhooks. Closes the BU → outreach → reply → outcome loop for tenants on the Pro+ tier.

**Why HubSpot second (vs Pipedrive first, ActiveCampaign skipped, GHL deferred):**
- Mid-size AU agency segment (10–50 employees) anchors on HubSpot per 2026 research.
- Higher LTV deals than Pipedrive — bigger agencies, bigger marketing budgets, less price-sensitive.
- Stable date-based API versioning (2026 onwards) — predictable deprecation cadence vs Pipedrive's aggressive v1 sunset.
- Mature partner ecosystem in AU (RedPandas, Technix Infotech) — onboarding can route through certified partners when needed.
- Higher build cost than Pipedrive (more endpoints, custom property hash translation, association API), so #2 not #1.

**When to use:**
- Tenant agency wires their HubSpot: bulk-import existing pipeline into BU for ICP enrichment, then auto-create Contacts/Deals in HubSpot when Keiracom finds new prospects matching their ICP.
- Closed-loop reporting: pull Deals with `dealstage = closedwon` / `closedlost` and `dealsource = keiracom-bu` to feed CIS feedback so the scoring engine learns from real outcomes.
- Engagement sync: when our outbound logs an open/click/reply, push a corresponding Engagement (email log) to the matching Contact so the agency sees Keiracom-driven activity in their inbox/dashboard.

**When NOT to use:**
- NOT for tenants on Pipedrive, GHL, ActiveCampaign, or no CRM — separate skill or no-op.
- NOT for storing PII we don't want on HubSpot's US-region servers (no AU data residency — see Caveats).
- NOT before per-tenant `HUBSPOT_PRIVATE_APP_TOKEN` is verified live (call `GET /crm/v3/owners/me` with the token — non-200 = block all writes).
- NOT for tenants on HubSpot Free or Starter — API rate limits and missing custom-property support make production sync unreliable. Gate on Professional+.

**Caveats:**
- **No AU data residency.** HubSpot stores in US AWS regions. Document in tenant onboarding; tenants with privacy-sensitive contracts must opt-in explicitly.
- **API versioning is date-based from 2026.** Each version supported 18 months. Pin our client to a specific date version (e.g. `2026-01-01`) and watch the deprecation calendar quarterly.
- **v1 Contact Lists deprecated April 2026.** Use `crm/v3/lists` exclusively. Any v1 endpoint reference is a code smell.
- **Classic CRM cards sunset Oct 2026.** If we extend the integration with custom UI cards, use the new card framework, not Classic.
- **Custom-property hash translation required.** HubSpot exposes properties by their internal name (e.g. `bu_uuid_c`), not human label. Build a per-portal property cache (refresh weekly) so callers can use stable string keys.
- **Per-portal token model.** Private App tokens scope to a single HubSpot portal (account). Token-issuing user must have permissions for every object type we touch (Contacts, Companies, Deals, Engagements). Recommend the agency creates a `keiracom@{agency}.com.au` portal user with full admin rights for the integration.
- **Rate limits:** **100 requests / 10 seconds per Private App token** (10 req/sec sustained), with daily caps that vary by tier. Default our client to **5 req/sec** for headroom. 429 → exponential backoff (1s → 2s → 4s, max 3 retries) + respect `X-HubSpot-RateLimit-Daily-Remaining` header.
- **Webhook reliability is industry-standard with SLA backing** (better than Pipedrive). Still build for eventual consistency — observed delivery within 5 seconds typical, retries on 5xx for up to 24 hours.
- **No native BAS/GST integration.** Same gap as Pipedrive/ActiveCampaign. AU agencies handle tax flow manually; our integration does NOT need to address this in v1.

**Returns:**
- Contact create/update: `{id: str, properties: {firstname, lastname, email, phone, company, ...}, createdAt, updatedAt}`.
- Deal create: `{id: str, properties: {dealname, amount, dealstage, pipeline, hubspot_owner_id, ...}, associations: {contacts, companies}}`.
- Engagement create: `{id: str, type: 'EMAIL'|'CALL'|'NOTE', subject, body, hs_timestamp}`.
- Webhook event: `{eventId, subscriptionType, portalId, occurredAt, objectId, propertyName, propertyValue, changeSource}`.

---

## Input Parameter Constraints (Poka-Yoke)

**Create / update Contact:**
- `email: str` — required and the primary identity key. Must match `^[^@\s]+@[^@\s]+\.[^@\s]+$`. **AU enforcement:** if `au_only=True` (default), reject TLDs not in `{.com.au, .net.au, .org.au, .edu.au, .gov.au, .com}`.
- `firstname: str` — strongly recommended. ≤ 60 chars. **Reject** if `None` AND the campaign template references `{{firstname}}` (template scan precedes API call).
- `lastname: str` — optional. ≤ 60 chars.
- `phone: str` — optional. Normalised to E.164 with `+61` prefix. Reject anything not matching `^\+61\d{9}$` unless caller passes `au_only=False`.
- `company: str` — optional. ≤ 200 chars. (Will become `associatedcompanyid` if a matching Company exists; otherwise pass as a property.)
- `lifecyclestage: str` — optional. Must be one of `subscriber`, `lead`, `marketingqualifiedlead`, `salesqualifiedlead`, `opportunity`, `customer`, `evangelist`, `other`. Default `lead` for Keiracom-sourced.
- `properties: dict[str, str]` — optional. Keys are HubSpot internal names (e.g. `bu_uuid_c`), NOT human labels. Caller must pre-translate via the property cache (see `/crm/v3/properties/contacts`).

**Create Deal:**
- `dealname: str` — required. ≤ 255 chars. Convention: `"{display_name} — {service}"` (e.g. `"Pymble Dental — SEO retainer"`).
- `amount: int | float` — required. **AUD only** (LAW II). Pass as a number; HubSpot stores as string but our wrapper handles conversion.
- `currency: "AUD"` — hardcoded. Reject any other currency at the wrapper level. Tenant portal must have AUD configured as a multi-currency option.
- `dealstage: str` — required. Maps to the agency's pipeline stage (e.g. `appointmentscheduled`, `qualifiedtobuy`). Tenant config declares which stage corresponds to "Keiracom-sourced new lead".
- `pipeline: str` — required. Tenant config maps which pipeline new Keiracom deals enter (default `default`).
- `hubspot_owner_id: int` — required. The HubSpot user who owns the deal. Default to `tenant.keiracom_hubspot_owner_id`.

**Webhook handler (inbound):**
- Verify signature header before reading body (see Webhook Signing).
- `subscriptionType: str` — must match HubSpot's documented event matrix (e.g. `contact.creation`, `deal.propertyChange`, `contact.deletion`).
- Idempotency: dedupe by `(eventId, occurredAt)` before any side-effect insert.

**Never pass:**
- USD or other-currency `amount` — rejected by wrapper (LAW II).
- Raw user input as `properties` keys — must be pre-translated to HubSpot internal names.
- A `vid` from a different tenant's portal — HubSpot returns 404 silently; build a tenant-id assertion at wrapper level.
- v1 Contact Lists endpoints — sunset April 2026; raise `RuntimeError` if any caller path hits them.

---

## Input Examples (covers edge cases)

**Create a Contact from a BU row:**
```json
{
  "properties": {
    "email": "michael.chen@pymbledental.com.au",
    "firstname": "Michael",
    "lastname": "Chen",
    "phone": "+61412345678",
    "company": "Pymble Dental",
    "lifecyclestage": "lead",
    "bu_uuid_c": "BU-uuid-here",
    "vertical_c": "dental"
  }
}
```

**Create a Deal for a Keiracom-sourced lead:**
```json
{
  "properties": {
    "dealname": "Pymble Dental — SEO retainer",
    "amount": 3000,
    "currency": "AUD",
    "dealstage": "appointmentscheduled",
    "pipeline": "default",
    "hubspot_owner_id": 891234
  },
  "associations": [
    {"to": {"id": "1729"}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]}
  ]
}
```

**Webhook payload — deal property change (incoming):**
```json
{
  "eventId": 12345678,
  "subscriptionType": "deal.propertyChange",
  "portalId": 88812,
  "occurredAt": 1714989060000,
  "objectId": 1729,
  "propertyName": "dealstage",
  "propertyValue": "closedwon",
  "changeSource": "CRM_UI"
}
```
Handler reads the stage transition (`appointmentscheduled` → `closedwon`) → posts CIS feedback row → BU `last_outcome = won`.

---

## Response Trimming (what to persist, what to drop)

**Contact create/update — PERSIST:** `id`, `properties.email`, `properties.firstname`, `properties.lastname`, `properties.phone`, `properties.company`, `properties.lifecyclestage`, `createdAt`, `updatedAt`. **DROP:** `hs_calculated_*`, `notes_last_*`, `num_associated_deals`, `recent_conversion_*` — re-derived from our own pipeline data.

**Deal create — PERSIST:** `id`, `properties.dealname`, `properties.amount`, `properties.dealstage`, `properties.pipeline`, `properties.hubspot_owner_id`, `properties.closedate`, `createdAt`, `updatedAt`. **DROP:** `hs_acv`, `hs_arr`, `hs_mrr`, `hs_projected_amount` — agency-side analytics, not load-bearing for our pipeline.

**Webhook event — PERSIST:** `eventId`, `subscriptionType`, `portalId`, `objectId`, `propertyName`, `propertyValue`, `occurredAt`. **DROP:** `changeSource`, `attemptNumber` — log only at DEBUG.

---

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/crm/v3/owners/me` | GET | Verify token + get tenant user identity. Use during onboarding, not per-call. |
| `/crm/v3/objects/contacts` | POST | Create Contact. |
| `/crm/v3/objects/contacts/{id}` | GET / PATCH / DELETE | Read / update / archive Contact. |
| `/crm/v3/objects/contacts/search` | POST | Find existing Contact by email or property (dedupe before create). |
| `/crm/v3/objects/deals` | POST | Create Deal. |
| `/crm/v3/objects/deals/{id}` | GET / PATCH | Read / update Deal. |
| `/crm/v3/objects/deals/{id}/associations/contacts/{contactId}/{type}` | PUT | Associate Deal ↔ Contact. |
| `/crm/v3/objects/companies` | POST / GET | Manage Companies. |
| `/crm/v3/properties/contacts` | GET | Look up custom-property internal names (cache per portal; refresh weekly). |
| `/crm/v3/lists` | POST / GET | Static + dynamic list management (NOT v1 Contact Lists — sunset April 2026). |
| `/crm/v3/objects/engagements` | POST | Log Engagement (email/call/note) against a Contact/Deal. |
| `/webhooks/v1/{appId}/subscriptions` | POST / GET | Manage outbound webhook subscriptions. |

**Base URL:** `https://api.hubapi.com`
**Auth:** `Authorization: Bearer {HUBSPOT_PRIVATE_APP_TOKEN}` header. NOT a query parameter.
**API version pin:** include `Date: 2026-01-01` (or current pinned date) in headers when targeting a specific version of date-based endpoints.

---

## Webhook Events We Subscribe To

| Event | Triggers BU update? | Handler action |
|---|---|---|
| `contact.creation` | No (Keiracom created it) | Skip — origin was Keiracom; persist HubSpot `vid` ↔ `bu_id` mapping. |
| `contact.propertyChange` (email) | Conditional | If email changed, sync corrected value back to BU. |
| `contact.deletion` | Yes — set `business_universe.crm_deleted_at` | Flag in BU; do not push again to this tenant. |
| `deal.creation` | No (Keiracom created) | Persist `deal_id` ↔ `bu_id` mapping. |
| `deal.propertyChange` (dealstage → closedwon) | Yes — `last_outcome = won`, CIS feedback row | Closed-loop signal — high value. |
| `deal.propertyChange` (dealstage → closedlost) | Yes — `last_outcome = lost`, CIS feedback row, capture `closed_lost_reason` | Closed-loop signal — high value. |
| `contact.propertyChange` (lifecyclestage → customer) | Yes — `last_outcome = customer` | Late conversion signal. |

**Idempotency:** dedupe by `(eventId, occurredAt)` before any side-effect. HubSpot may redeliver events for up to 24 hours on receiver failure.

**Required response:** HTTP 200 within 5s. Anything else triggers retry.

---

## Webhook Signing

HubSpot uses **HMAC-SHA256** over a canonical request string (NOT raw body). Header is `X-HubSpot-Signature-v3`.

Canonical string format:
```
{HTTP_METHOD}{REQUEST_URI}{REQUEST_BODY}{TIMESTAMP}
```
Where:
- `HTTP_METHOD` = `POST` (always uppercase)
- `REQUEST_URI` = full URL including query string
- `REQUEST_BODY` = raw body bytes
- `TIMESTAMP` = `X-HubSpot-Request-Timestamp` header value (millis since epoch)

Verification:
1. Read `X-HubSpot-Signature-v3` and `X-HubSpot-Request-Timestamp` headers.
2. Reject if either header is missing (fail-closed, return 401).
3. Reject if `now - timestamp > 5 minutes` (replay protection).
4. Compute `HMAC-SHA256(client_secret, canonical_string).base64()`.
5. Constant-time compare against header value (`hmac.compare_digest`).

**This is stronger than Pipedrive's HTTP Basic auth** — payload integrity AND timestamp replay protection. Mirror the existing `verify_webhook_signature` pattern from `src/integrations/resend_client.py` (Svix-spec).

Secret source: per-tenant `tenant_config.hubspot_webhook_client_secret` (encrypted at rest), set when the Private App is created in the tenant's HubSpot portal.

---

## Error Handling (Category → Action mapping)

| HTTP | Category | Action |
|---|---|---|
| 200 / 201 / 204 | success | Persist trimmed response. |
| 400 | caller_error | Validate against Input Parameter Constraints; do NOT retry. |
| 401 | config_error | Token invalid/revoked. Disable tenant integration; alert via Slack. |
| 403 | permission_error | Token lacks scope (e.g. `crm.objects.deals.write`). Re-issue token with required scopes. |
| 404 | not_found | Tenant deleted the Contact/Deal — mark `crm_deleted_at` in BU; do NOT recreate. |
| 409 | conflict | Duplicate (email already exists). Search-first-then-create flow handles this; if it fires, fall back to GET-by-email + PATCH. |
| 410 | sunset | Endpoint deprecated (likely v1 Contact Lists). Log governance debt and route to devops-6. |
| 429 | rate_limit | Exponential backoff 1s → 2s → 4s, max 3 retries. Respect `Retry-After` header if present. |
| 5xx | transient | Retry once after 5s. If still failing, escalate to devops-6. |
| webhook signature mismatch | security | Reject with 401. Log header presence (not content) for audit. |

---

## Rate Limiting

- Documented ceiling: **100 requests / 10 seconds** per Private App token (sustained 10 req/sec).
- Daily caps vary by tier:
  - Professional: 250,000 requests/day
  - Enterprise: 500,000 requests/day
- Default our client to **5 req/sec** for headroom; allow burst-to-15 with leaky bucket.
- Bulk operations (initial portal import for new tenant): use `/crm/v3/objects/contacts/search` to dedupe before write; cap at 3 req/sec to be courteous.
- Watch the `X-HubSpot-RateLimit-Daily-Remaining` response header — pause integration if remaining < 10% of daily cap.

---

## Integration Points

| File | Usage |
|---|---|
| `src/integrations/hubspot_client.py` | TBD — main client implementation. Mirror `src/integrations/pipedrive_client.py` (#575) and `src/integrations/resend_client.py` (single class/module, methods per endpoint, dedupe + suppression-aware writes, `verify_webhook_signature_v3()` helper). |
| `src/api/routes/hubspot.py` | TBD — webhook receiver mounted at `/api/hubspot/webhook`. Per-tenant signature verification with replay protection. |
| `src/engines/crm_sync.py` | Existing (Pipedrive scope) — extend with HubSpot dispatcher; route per `tenant_config.crm_provider`. |
| `src/models/tenant_config.py` | TBD — extend with `hubspot_portal_id`, `hubspot_private_app_token` (encrypted), `hubspot_webhook_client_secret` (encrypted), `hubspot_owner_user_id`, `hubspot_pipeline`, `hubspot_dealstage_keiracom_lead` columns. |

**LAW XII:** direct calls to `src/integrations/hubspot_client.py` outside skill execution are forbidden. The skill is the canonical interface.
**LAW XIII:** any change to HubSpot call patterns updates this SKILL.md in the same PR.

---

## Governance

- **LAW II:** all Deal `amount`s in AUD. Wrapper rejects non-AUD currency at validation. Tenant portal must have AUD as a configured currency.
- **LAW VI:** prefer this skill > MCP > exec. There is currently NO HubSpot MCP server, so all calls go through `src/integrations/hubspot_client.py` and are wrapped by this skill.
- **LAW XII / XIII:** see Integration Points above.
- **CEO Directive (2026-05-06):** HubSpot is the SECOND CRM integration after Pipedrive (mid-size 10–50 employee segment). ActiveCampaign skipped (no AU presence); GoHighLevel deferred until AU share crosses 15%.

---

## Pending Verification (DO NOT SKIP BEFORE FIRST PRODUCTION USE)

1. **Webhook signature v3 implementation** — confirm canonical string format `{METHOD}{URI}{BODY}{TIMESTAMP}` matches HubSpot's actual hash; observe the first 5 production webhooks to verify.
2. **Date version pin** — confirm `2026-01-01` (or current latest) is the right pin; review HubSpot deprecation calendar and update quarterly.
3. **Custom-property name cache** — build per-portal cache via `/crm/v3/properties/contacts` and `/crm/v3/properties/deals`. Refresh weekly. Without this, custom-field writes fail with cryptic 400s.
4. **AUD multi-currency configuration** — verify the tenant portal has AUD enabled. HubSpot won't accept Deal `amount` in AUD if AUD isn't a configured portal currency.
5. **Daily rate-limit ceiling under load** — empirical test against Professional tier (250k/day cap) before any tenant onboards bulk-volume. Pause integration when daily-remaining < 10%.
6. **AU partner relationship** — RedPandas / Technix Infotech are the established AU HubSpot partners. Decide whether we route Pro+ tenant onboarding through them (revenue share) or self-serve.

---

## Migration Notes (from "no CRM" or other CRMs)

- **From "no CRM"**: tenant signs up for HubSpot Free, but Free CRM has no API custom-property support. Gate writes on Professional+ subscription. Onboarding lead-time is 2–4 weeks (HubSpot mandatory $5.7k onboarding).
- **From Pipedrive (#571 skill)**: tenant migrating between CRMs is out-of-scope for this skill. Plan a separate migration tool that reads Pipedrive Persons + Deals and writes to HubSpot Contacts + Deals. Both skills can run in parallel during transition.
- **From ActiveCampaign / GHL**: out of scope. Note in tenant config so we route them to the right (future) integration skill.
- **From Salesforce**: out of scope. Higher up-market — separate integration when we build it.

---

## Template Checklist (mirrors leadmagic / smartlead / pipedrive)

- [x] **At-a-Glance block** with What / Why / When to use / When NOT to use / Caveats / Returns
- [x] **Input Parameter Constraints** with regex, length limits, AU enforcement, poka-yoke
- [x] **Input Examples** ≥3 cases including edge cases (Contact, Deal, webhook payload)
- [x] **Response Trimming** PERSIST vs DROP per response type
- [x] **API Endpoints table** with method + purpose
- [x] **Webhook Events** matrix with BU update semantics
- [x] **Error Handling** table HTTP → category → action
- [x] **LAW XII governance note** — skill is canonical interface
- [x] **Pending Verification** section — every assumption that must be closed before production

---

## Why this skill exists (and why HubSpot is #2, not #1)

Per the AU agency CRM research (2026-05-06 — see TG group + PR #571 reasoning):

| Segment | Anchor CRM | Build priority |
|---|---|---|
| Solo consultants (1 person) | Free tier (HubSpot Free, Freshsales, Zoho) | Skip — no paid LTV |
| Small agencies (2–10) | **Pipedrive** | **#1 (#571 — shipped)** |
| Mid-size agencies (10–50) | **HubSpot** | **#2 (this skill)** |
| Large agencies (50+) | Salesforce / HubSpot Enterprise | Defer — too few in AU |

HubSpot ships as #2 because:
1. **Higher LTV** per tenant (Pro+ deals are 3–5× Pipedrive ARPU) — but smaller addressable AU market.
2. **Higher build cost** — more endpoints, custom-property hash translation, association API, signature-v3 verification.
3. **Slower tenant onboarding** — mandatory $5.7k AUD onboarding fee adds 2–4 weeks lead time.

Building Pipedrive first reaches the largest segment fastest and proves the integration pattern. HubSpot follows once we have a tenant ready to upgrade or a mid-size agency joins.

Two notable differentiators we may exploit later (NOT in v1 scope):
1. **AU data residency** — no major CRM offers it. Building a Keiracom-side mirror with AU storage is a future moat.
2. **Xero/MYOB sync** — no CRM has BAS/GST integration. A future Keiracom→Xero sync is a wedge.
