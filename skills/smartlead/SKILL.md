# SKILL: Smartlead Cold-Outbound Platform

**Replaces:** Salesforge (dead — invalid API key as of 2026-05-06).
**Status:** ⚠️ API key NOT provisioned, plan NOT purchased — do NOT call until Pro tier active and `SMARTLEAD_API_KEY` set in env.
**Source:** Smartlead.ai REST API v1.
**Credentials Required:** `SMARTLEAD_API_KEY` (single key per workspace; created in dashboard → Settings → API Key Management).
**Cost gate:** Pro plan minimum for API access — **$94 USD/mo ≈ $145 AUD/mo** (LAW II). Base plan ($39 USD/mo) does NOT include API access.

---

## At-a-Glance (Anthropic tool-doc template — 6-vector hardened)

**What:** Drive cold-outbound campaigns: create campaign, push leads, monitor inbox warmup, receive webhook events for sends/opens/replies/bounces/unsubscribes. Smartlead handles SMTP, IP rotation, inbox rotation, and warmup; we own sequence orchestration on top.

**When to use:**
- Pushing prospects from `business_universe` into a sequenced outbound campaign (replaces direct Resend-from-script for cold).
- Configuring or auditing inbox warmup before any campaign that will exceed ~30 sends/day from a domain.
- Ingesting reply / bounce / unsubscribe events into our own pipeline (BU rows, suppression list, `dm_email_verified` ratchet).
- Reading per-campaign or per-account analytics for Closed-Loop Engine feedback.

**When NOT to use:**
- NOT for transactional or system mail (booking confirms, password resets, internal alerts) — that stays on Resend, Resend route is `src/api/routes/email.py`.
- NOT for one-off manual sends — use Resend or `scripts/campaign_sender.py --live`. Smartlead is for sequenced outbound only.
- NOT before the bounce-ratchet + RFC 8058 unsubscribe handlers are in production. Sending without those = burned `agencyxos.ai` domain.
- NOT during plan-unpurchased window (see Status above). 401 / 403 responses are wasted log noise.

**Caveats:**
- **Auth model:** API key as query parameter `?api_key=…`, NOT bearer header. Easy to leak in logs — always strip before logging URLs.
- **Webhook signing: HMAC-SHA256** with shared secret, `X-Smartlead-Signature` header. Confirmed via the 2026-05-06 deep-dive; previously marked UNVERIFIED. Fail-closed on missing signature OR missing secret.
- **Rate limits (confirmed 2026-05-06):** Standard tier 60 req/min + 1,000/hour + 10 burst/sec; **Pro tier 120 req/min + 3,000/hour + 20 burst/sec**; Enterprise custom. Limits apply ACROSS ALL endpoints combined (not per-endpoint). 429 returns include `retry_after` (seconds) plus headers `X-RateLimit-{Limit,Remaining,Reset}` and `Retry-After`. Default our client to **5 req/sec** with exponential backoff (`2^attempt + jitter`).
- **Campaign-create body schema is incomplete in public docs.** Required fields will need to be reverse-engineered from the dashboard or via support. Treat current params as best-effort.
- **AU deliverability not separately benchmarked by Smartlead.** Their warmup network is US/EU-heavy; expected but unverified that AU inboxes (Outlook AU, Gmail, ME) accept the same patterns. Validate with a 50-send Client Zero run before any volume.
- **Lead batch limit:** 400 leads per `add_leads` call. Larger batches must be chunked.

**Returns:**
- Add leads: `{ok: bool, added_count: int, skipped_count: int, skipped_leads: list[{email, reason}]}`.
- Warmup status: `{warmup_enabled: bool, sent_7d: int, opened_7d: int, replied_7d: int, bounced_7d: int, unsubscribed_7d: int}`.
- Send / per-lead status: derived from webhook stream, not a polling endpoint.
- Webhook event: `{event_type, timestamp_iso, campaign_id, campaign_name, lead: {email, first_name, last_name, company}, email_account, sequence_number, message_id}`.

---

## Input Parameter Constraints (Poka-Yoke)

**Add leads to campaign:**
- `campaign_id: int` — required. Must be a valid campaign owned by the workspace; reject placeholder zero or negative.
- `leads: list[dict]` — required. Length **1 ≤ n ≤ 400**. Caller must chunk anything larger (chunk size 200 recommended for headroom).
- Each `lead` dict:
  - `email: str` — required. Must match `^[^@\s]+@[^@\s]+\.[^@\s]+$`. **AU enforcement:** if `au_only=True` (default), reject TLDs not in `{.com.au, .net.au, .org.au, .edu.au, .gov.au, .com}` (the bare `.com` is allowed because half of AU SMBs sit on it).
  - `first_name: str` — optional but strongly recommended. ≤40 chars. **Reject** if `None` AND the campaign template references `{{first_name}}` (template scan precedes API call).
  - `last_name: str` — optional. ≤40 chars.
  - `company: str` — optional. ≤200 chars.
  - `custom_fields: dict[str, str]` — optional. ≤200 keys per lead per Smartlead docs. Values must be strings (cast ints/UUIDs before send).
- **Pre-flight suppression check (REQUIRED):** every email must be checked against `public.global_suppression`, `public.domain_suppression`, and any campaign-scoped suppression list BEFORE the API call. Smartlead has its own suppression but ours is authoritative.
- **Pre-flight bounce-ratchet check (REQUIRED):** skip any email where `business_universe.dm_email_verified = false` regardless of confidence score.

**Warmup config:**
- `email_account_id: int` — required. The Smartlead-side email account, NOT our internal user/auth ID.
- `warmup_enabled: bool` — required.
- `total_warmup_per_day: int` — required when enabling. Conservative AU value: start at 20, ramp to 40 over 14 days. Hard cap 50 until reputation is established.
- `daily_rampup: bool` — required. **Always True** for new domains.
- `reply_rate_percentage: int` — optional. Range 30–60. Default 40.

**Never pass:**
- Raw user input as `email` without regex validation — will silently 422 a whole batch.
- `custom_fields` containing PII you don't want stored on Smartlead's servers.
- A `campaign_id` you didn't create in the same workspace (their isolation model is per-workspace, not per-key).

---

## Input Examples (covers edge cases)

**Add a single lead:**
```json
{
  "campaign_id": 12345,
  "leads": [{
    "email": "michael.chen@pymbledental.com.au",
    "first_name": "Michael",
    "last_name": "Chen",
    "company": "Pymble Dental",
    "custom_fields": {"suburb": "Pymble", "state": "NSW", "vertical": "dental"}
  }]
}
```

**Add a batch with one suppression-list hit (must be filtered out before send):**
```json
{
  "campaign_id": 12345,
  "leads": [
    {"email": "drsmith@example.com.au", "first_name": "Sam"},
    {"email": "unsub@example.com.au", "first_name": "Jo"}
  ]
}
```
Caller MUST: query `SELECT email FROM public.global_suppression WHERE email IN (...)` first; drop any matched emails; only the unmatched survivors go to Smartlead.

**Enable warmup on a fresh AU sender:**
```json
{
  "email_account_id": 7891,
  "warmup_enabled": true,
  "total_warmup_per_day": 20,
  "daily_rampup": true,
  "reply_rate_percentage": 40
}
```

---

## Response Trimming (what to persist, what to drop)

**Add-leads response — PERSIST:** `added_count`, `skipped_count`, full `skipped_leads` list with reasons (we need to know why Smartlead rejected — duplicate, blocked, malformed). **DROP:** any timing / latency fields; not load-bearing for our pipeline.

**Warmup-stats response — PERSIST:** `warmup_enabled`, the 7-day rollup counters (`sent_7d`, `opened_7d`, `replied_7d`, `bounced_7d`, `unsubscribed_7d`). **DROP:** per-day breakdown if returned (we recompute from our own webhook stream, single source of truth).

**Webhook event — PERSIST:** `event_type`, `timestamp`, `campaign_id`, `lead.email`, `sequence_number`, `message_id`. **DROP:** `email_account` ID (not useful downstream), `campaign_name` (we have it), redundant lead fields (`first_name`/`last_name` are already on BU).

Bloated webhooks fill `keiracom_admin.email_events` and slow downstream queries. Persist only fields cited in the closed-loop contract.

---

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/campaigns/create` | POST | Create a campaign. Returns `campaign_id`. Body schema partly undocumented. |
| `/campaigns/{campaign_id}/leads` | POST | Add ≤400 leads to a campaign. |
| `/campaigns/{campaign_id}` | GET | Read campaign config + status. |
| `/campaigns/{campaign_id}/sequences` | POST | Push email sequence steps (subject + body per step). |
| `/email-accounts/{email_account_id}/warmup-stats` | GET | 7-day warmup metrics for one sending account. |
| `/email-accounts/{email_account_id}/warmup` | POST | Enable / configure warmup. |
| Webhook receiver | POST (inbound) | Smartlead → us. Subscribe per-event-type in dashboard. |

**Base URL:** `https://server.smartlead.ai/api/v1`
**Auth:** append `?api_key={SMARTLEAD_API_KEY}` to every request — never put it in a header or in the body.

---

## Webhook Events

| Event | Triggers BU update? | Our handler action |
|---|---|---|
| `EMAIL_SENT` | No | Insert into `keiracom_admin.email_events` for analytics. |
| `EMAIL_OPENED` | No | Same — analytics only. |
| `EMAIL_CLICKED` | No | Analytics; tag prospect as "warm" if N≥2. |
| `EMAIL_REPLIED` | Yes — set `business_universe.last_reply_at` | Route reply to Slack #replies via classifier; pause sequence for that lead. |
| `EMAIL_BOUNCED` (hard) | Yes — set `dm_email_verified=false`, `dm_email_confidence=0` | Bounce-ratchet. Insert into `keiracom_admin.email_events`. |
| `EMAIL_BOUNCED` (soft) | No | Retry policy is Smartlead's — just log. |
| `LEAD_UNSUBSCRIBED` | Yes — insert into `public.global_suppression` (source='smartlead-unsub') | Compliance critical. |
| `LEAD_CATEGORY_UPDATED` | No | Optional — Smartlead's reply-classifier output, can feed CIS. |

**Idempotency:** dedupe by `(message_id, event_type)` before insert. Smartlead retries failed webhooks at 1m / 5m / 30m, so duplicate deliveries are normal.

**Required response:** HTTP 200 within 30s. Anything else triggers retry.

---

## Webhook Signing — HMAC-SHA256 (confirmed 2026-05-06)

Confirmed via Smartlead docs and verified on the 2026-05-06 deep-dive:

1. Header: `X-Smartlead-Signature: <hmac>`
2. Algorithm: **HMAC-SHA256** with shared secret
3. Payload: raw request body bytes
4. Secret: configured per-webhook subscription in the Smartlead dashboard (NOT the `SMARTLEAD_API_KEY`)
5. Idempotency: dedupe at the receiver on `(lead_id, event, timestamp)` — Smartlead does NOT issue a formal idempotency token. Retry policy: 1m → 5m → 15m → 1h → 6h (5 retries, then auto-disable).

**Subscription levels:** User-wide, Client-level, or Campaign-level. Recommend Client-level so a tenant's webhooks all point at the same Keiracom receiver URL.

**Receiver implementation:** mirror the Resend/Svix HMAC pattern in `src/integrations/resend_client.py` — fail-closed on missing header, fail-closed on missing secret, constant-time compare, log header presence (not content) on rejection. The verify pattern from PR #557 / #566 is directly applicable.

---

## Error Handling (Category → Action mapping)

| HTTP | Category | Action |
|---|---|---|
| 200 | success | Persist trimmed response (see Response Trimming). |
| 400 | caller_error | Validate against Input Parameter Constraints; do NOT retry. |
| 401 | config_error | Missing / wrong `SMARTLEAD_API_KEY`. Route to devops-6. |
| 402 / 403 | budget / plan | Pro plan not active. Escalate to Dave (budget decision). Do NOT keep hitting endpoint. |
| 422 | validation | Inspect `skipped_leads` reasons; fix upstream data; do NOT retry the same payload. |
| 429 | transient | Exponential backoff 1s → 2s → 4s, max 3 attempts, then escalate. |
| 5xx | transient | Retry once after 5s. If still failing, escalate to devops-6. |
| webhook signature mismatch | security | Reject with 401. Log header + first 64 bytes of body for audit. Never silently drop. |

---

## Rate Limiting

- Public docs do NOT specify per-second / per-minute limits.
- Empirical: 429 observed under sustained 10 req/sec. Default to **2 req/sec** for batch operations, **1 req/sec** for warmup config (low-frequency anyway).
- Always `await asyncio.sleep(0.5)` between calls in a batch loop unless you have a hard deadline.

---

## Integration Points

| File | Usage |
|---|---|
| `src/integrations/smartlead_client.py` | TBD — main client implementation. Mirror `src/integrations/resend_client.py` structure (single class, methods per endpoint, `verify_webhook_signature()` helper). |
| `src/api/routes/smartlead.py` | TBD — webhook receiver route, mounted under `/api/smartlead/webhook`. Mirror `src/api/routes/email.py` HMAC-verify pattern. |
| `src/pipeline/campaign_orchestrator.py` | TBD — push BU prospects into a campaign, manage sequence steps. |
| `scripts/campaign_sender.py` | Out of scope — that script uses Resend MCP for individual sends, not Smartlead campaigns. |

**LAW XII:** direct calls to `src/integrations/smartlead_client.py` outside skill execution are forbidden. The skill is the canonical interface.
**LAW XIII:** any change to Smartlead call patterns updates this SKILL.md in the same PR.

---

## Governance

- **LAW II:** all Smartlead costs logged in AUD (subscription is flat-rate so primarily a `$145 AUD/mo` line item, not per-call).
- **LAW VI (updated 2026-05-06):** prefer this skill > MCP > exec. **Smartlead MCP server now wired** (PR #579) — `mcp-bridge call smartlead <tool>` is the canonical operational dispatch path for the 75 endpoints / 116 tools NOT explicitly listed in this skill. Direct Python client (`src/integrations/smartlead_client.py`) is **deferred** unless evidence shows MCP is insufficient (saves ~500 lines per ELLIOT's audit). The skill stays canonical for the strategic-tool subset documented above; MCP handles the long tail.
- **LAW XII / XIII:** see Integration Points above.
- **CEO Directive (2026-05-06):** Smartlead is the canonical replacement for Salesforge. Salesforge integration code (if any survives) is dead-on-import — do not extend, do not reference.
- **Pre-revenue reality (per memory `feedback_pre_revenue_reality`):** zero clients today. Subscription cost is real money out — confirm with Dave before activating Pro plan.

---

## Pending Verification (DO NOT SKIP BEFORE FIRST PRODUCTION USE)

1. ✅ **Webhook signing algorithm** — RESOLVED 2026-05-06: HMAC-SHA256, `X-Smartlead-Signature` header, per-subscription secret. See "Webhook Signing" section above.
2. ✅ **Rate-limit ceiling** — RESOLVED 2026-05-06: Pro 120/min + 3,000/hour + 20 burst/sec. See Caveats.
3. **Campaign-create full body schema** — request from support or reverse-engineer from dashboard.
4. **List-campaigns endpoint** — not in current public docs; needed for UI / admin tooling.
5. **AU deliverability** — run a 50-send Client Zero campaign through a Smartlead-managed AU SMTP and measure inbox-placement before any real volume. **No documented AU warmup partners** — confirmed gap.
6. **SmartSenders programmatic seat purchase** — `auto-generate-mailboxes` and `bulk-create-accounts` API endpoints exist, but SmartSenders new-seat purchase from partners (Zapmail, InfraInbox, Mailreef) appears UI-driven. Confirm via partner support whether programmatic purchase is exposed.
7. ✅ **Warmup config via API** — RESOLVED 2026-05-06 (corrected from prior "not documented" claim): endpoints DO exist per ELLIOT's MCP-server source audit — `PUT /email-accounts/{id}/warmup-settings` (configure), `GET /email-accounts/{id}/warmup-status` (read), `GET /email-accounts/{id}/health-metrics` (deliverability metrics). All three available programmatically.
8. ✅ **Hidden API surface audit** — RESOLVED 2026-05-06: ELLIOT cloned LeadMagic's `smartlead-mcp-server` repo, verified **116 `registerTool()` calls backed by 75 unique API endpoints** (vs ~28 in this skill prior to update). LAW VI dispatch path: route operational tools via the MCP server (`mcp-bridge call smartlead <tool>`); skill remains the canonical contract. See Build Recommendation below.

---

## Operational Mechanics (added 2026-05-06)

### Warmup
- **Per-mailbox**, not per-domain. Each inbox has its own ramp curve.
- Default ramp: **5–10 sends/day week 1 → 20–30/day week 2 → 150–200/day week 4**, minimum 3–4 weeks before full-volume sending.
- Reply-rate targets: ~30% during warmup, escalates to ~70% during live campaigns, ~20–30% steady-state post-campaign.
- Smart-Adjusting Algorithm auto-pauses on bounce spikes / spam complaints / invalid-inbox status; resumes healthy domains automatically.
- AU warmup partners NOT separately documented — flagged as deliverability gap (see Pending Verification #5).

### DNS setup
- **SPF:** `v=spf1 include:_spf.smartlead.ai ~all`
- **DKIM:** auto-generated CNAME, pushed by Smartlead
- **DMARC:** start `p=none` for 2–4 weeks → `p=quarantine`
- Verification instant via Cloudflare-API integration.
- Multi-domain supported (5+ sending domains per account, each with own DNS).
- Custom tracking domain (CNAME) recommended but not required.
- Bounce/return-path defaults to primary domain, not separate.
- AU TLDs (.com.au, .net.au) treated as standard — no documented gotchas.

### Mailbox provisioning + SmartSenders
- **Existing mailboxes:** Google Workspace IMAP/SMTP, Office 365 SMTP (`smtp.office365.com:587` with SMTP AUTH enabled in Exchange Admin Center), custom IMAP/SMTP. Flow is UI-driven.
- **SmartSenders RESALE:** Smartlead resells pre-warmed mailboxes via partners — Zapmail, InfraInbox, Mailreef — at approximately **$5–15 AUD/seat/month** (pricing partner-dependent, not publicly published). Pre-warmed seats can skip the 3–4 week warmup runway entirely (Dave-decision: spend vs. time tradeoff).
- **Daily send cap per mailbox:** 50–200 (safe range); warmup counts toward daily cap.
- **Reply-side:** Smartlead polls IMAP for replies (Gmail / Office365 API integration); webhook-only delivery NOT documented.
- **Dedicated IPs:** available via partner SMTP providers (Mailreef et al.); pricing not documented.

### Email pool rotation
- **Campaign-scoped weighted round-robin.** Operator can assign weights.
- **Health-aware:** mailboxes with bounces or paused warmup auto-skipped from rotation.
- **Per-prospect threading PRESERVED:** prospect 1's step 1 + step 2 always come from the SAME mailbox in the pool (preserves reply threading and deliverability). Different prospects can come from different mailboxes within the same campaign.
- Bad accounts removed immediately on bounce/complaint signal.

### Programmatic provisioning matrix (API vs UI)
| Action | API | UI-only |
|---|---|---|
| `auto-generate-mailboxes` | ✅ | — |
| `bulk-create-accounts` | ✅ | — |
| `verify-domain` (DNS) | ✅ | — |
| Domain purchase via Namecheap integration | ✅ | — |
| SmartSenders new-seat purchase from partners | ⚠️ partial | likely partner UI |
| Warmup config — `PUT /email-accounts/{id}/warmup-settings` | ✅ | — |
| Warmup status — `GET /email-accounts/{id}/warmup-status` | ✅ | — |
| Warmup health metrics — `GET /email-accounts/{id}/health-metrics` | ✅ | — |
| Routing tools NOT in this skill (≈47 more) | ✅ via `mcp-bridge call smartlead` | — |

---

## Migration Notes (from Salesforge)

| Salesforge concept | Smartlead concept | Notes |
|---|---|---|
| Workspace | Workspace | Same. One per Keiracom client account when multi-tenant lands. |
| Sequence | Campaign + sequences endpoint | Sequence steps live under `/campaigns/{id}/sequences`. |
| Sender pool | Email accounts | Add each sending inbox as a separate email account; warmup configured per-account. |
| Lead | Lead | Field shape is similar; `custom_fields` is the merge-tag store. |
| Reply webhook | `EMAIL_REPLIED` event | Same semantics; signature verification differs (see Webhook Signing). |
| Salesforge unsubscribe | `LEAD_UNSUBSCRIBED` event | Both must funnel into our `public.global_suppression`. |

---

## Template Checklist (for hardening other skills)

- [x] **At-a-Glance block** with What / When to use / When NOT to use / Caveats / Returns
- [x] **Input Parameter Constraints** section with regex patterns, length limits, AU enforcement, poka-yoke rejection rules
- [x] **Input Examples** with ≥3 cases including at least one edge case
- [x] **Response Trimming** section naming which fields to PERSIST vs DROP
- [x] **Error Handling table** with HTTP code + category + action routing
- [x] **LAW XII governance note** — skill is the canonical interface; direct integration calls forbidden
- [x] **Pending Verification** section listing every public-docs gap that must be closed before production use
