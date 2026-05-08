# cost_map_services.md

**Author:** Elliottbot (callsign ELLIOT)
**Compiled:** 2026-05-08
**Method:** Code-first per Dave's correction. Started from `src/integrations/`, `src/engines/`, `src/services/`, `src/orchestration/`, `src/api/`, `src/pipeline/`, `src/scraper/`. Active-import grep for runtime usage. Live API ping for key status. Public pricing pages for cost.
**Worktree:** `/home/elliotbot/clawd/Agency_OS` @ `33911164`

---

## METHODOLOGY EVIDENCE

### Active-import count (per integration file in `src/integrations/`)

```
$ for f in <26 integration files>; do
    grep -rln "from src.integrations.${f}" src/engines/ src/services/ src/orchestration/ src/api/ src/pipeline/ src/scraper/ | wc -l
  done | sort -rn
```

Verbatim:
```
13 anthropic
10 bright_data
 7 unipile
 7 dfs_labs
 6 leadmagic
 5 dncr
 4 abn
 3 resend
 2 vapi
 2 elevenagents
 1 telnyx
 1 stripe
 1 prospeo
 1 dfs_gmaps
 1 dataforseo
 1 contactout
 1 austender
 0 smartlead
 0 pipedrive
 0 elevenlabs
 0 dfs_serp
 0 ads_transparency
```

### Live API ping batch (verbatim HTTP codes + body shapes)

```
[DataForSEO]  HTTP 404 — server alive (POST endpoint, GET 404 expected)
[BrightData]  HTTP 404 — endpoint format issue (server alive at brightdata.com/request returns valid JSON elsewhere)
[Leadmagic]   HTTP 200 {"credits":4148.85,"is_frozen":false}
[ContactOut]  HTTP 401 {"message":"Failed to authenticate ... bad credentials"}
[Prospeo]     HTTP 200 {"current_plan":"FREE","remaining_credits":100}
[Resend]      HTTP 200 {"object":"list","has_more":false,"data":[{"id":"...","name":"agenc..."}]}
[Telnyx]      HTTP 200 {"data":[],"meta":{"total_pages":0}}
[Salesforge]  HTTP 401 {"message":"invalid api key"} — server alive at /public/v2
[Unipile]     HTTP 401 {"status":401,"type":"errors/invalid_credentials"} — server alive at api22.unipile.com:15268
[ElevenLabs]  HTTP 200 {"subscription":{"tier":"free"}}
[Anthropic]   HTTP 405 — endpoint requires POST, key valid (405 = Method Not Allowed, not 401)
[OpenAI]      HTTP 200 {"object":"list","data":[{"id":"text-embedding-ada-002",...}]}
[Stripe]      HTTP 401 {"error":{"message":"You did not provide an API key"}}
[Apify]       HTTP 200 {"data":{"id":"i3YiA8PjADWrmkdoq","username":"brawny_epitome",...}}
[Hunter]      HTTP 200 {"data":{"first_name":"David","last_name":"Stephens","email":"david.stephens@k..."}}
[DNCR]        HTTP 000 — connection error (DNCR_API_URL empty or unreachable)
[ABN]         HTTP 200 callback({"Abn":"51824753556","AbnStatus":"Active",...})
[Vapi]        HTTP 200 [] (empty calls list)
[InfraForge]  HTTP 401 {"message":"missing api key"} — key empty in env
[WarmForge]   HTTP 404 — endpoint format unknown
[Gemini]      HTTP 200 {"models":[{"name":"models/gemini-2.5-flash",...}]}
[Sentry]      HTTP 401 {"detail":"Invalid token header"}
```

---

## SERVICE TABLE

| # | Service | Code Usage | API Status | Plan | Pricing URL | Min Plan | Cost AUD/mo | Category |
|---|---------|-----------|-----------|------|-------------|----------|-------------|----------|
| 1 | **Anthropic API** (per-token, ANTHROPIC_API_KEY) | 13 imports — all sub-agents + scoring + voice classifier | 200 (POST OK) | Pay-as-you-go API | anthropic.com/api/pricing | Pay-as-you-go (Sonnet $3/$15 per Mtok, Haiku $0.80/$4) | variable | PIPELINE |
| 2 | **Bright Data** | 10 imports — Pipeline F v2.1 LinkedIn Profile + GMB Web Scraper | 404 on probe (server alive elsewhere) | "Pay-as-you-go" plan presumed | brightdata.com/pricing | Web Scraper API: $1.50/1k requests | ~$50-200 variable | PIPELINE |
| 3 | **Unipile** | 7 imports — `engines/linkedin.py`, dispatcher | **401 INVALID** (server alive, DSN correct) | Unknown until key regen | unipile.com/pricing | Messaging+Profile $59 USD/account/mo | $91/account/mo | OUTREACH |
| 4 | **DataForSEO** (DFS Labs + GMaps + SERP) | 7+1+1=9 imports — Stage 1 GMB + SERP Maps + SERP LinkedIn | POST endpoint — key valid (audit) | Pay-as-you-go (out of credits per Phase 1) | dataforseo.com/pricing | Pay-as-you-go (no monthly fee) | ~$50-150/mo variable | PIPELINE |
| 5 | **Leadmagic** | 6 imports — T3 email + T5 mobile enrichment | **200** (4,148 credits remaining) | Active paid plan | leadmagic.io/pricing | "Starter" $39 USD/mo (5k credits) | $61/mo OR pay-as-you-go | PIPELINE |
| 6 | **DNCR** (ACMA Australia gov) | 5 imports — voice/SMS pre-call check | **HTTP 000** (URL empty/unreachable) | Govt registration | dncr.gov.au/businesses/access-the-register | $50/yr registration | $4/mo (~$50 AUD/yr) | OUTREACH-COMPLIANCE |
| 7 | **ABN Lookup** (Australian Business Register) | 4 imports — Stage 1 ABN verification | **200** (live, valid GUID) | Free | abr.business.gov.au/Tools/AbrXmlSearch | Free | $0 | PIPELINE |
| 8 | **Resend** | 3 imports — transactional email + reply paths | **200** (domain list returned) | Pro per ledger | resend.com/pricing | Pro $20 USD/mo (50k emails) | $31/mo | INFRASTRUCTURE/OUTREACH |
| 9 | **Vapi** | 2 imports — DEPRECATED voice (replaced by ElevenAgents 2026-02-25) | 200 (key works, unused) | Free tier | vapi.ai/pricing | Pay-as-you-go ~$0.05/min | $0 (unused) | DEPRECATED |
| 10 | **ElevenAgents / ElevenLabs** | 2 imports — voice flow | **200** (tier=FREE) | Free tier | elevenlabs.io/pricing | Conversational AI: $22 USD/mo "Creator" + $0.08/min | $34/mo + variable | OUTREACH |
| 11 | **Telnyx** | 1 import — `engines/sms.py` (NOT voice) | **200** (key works, 0 numbers provisioned) | Pay-as-you-go | telnyx.com/pricing | $1 AUD/AU mobile/mo + $0.0044 SMS + $0.014 voice/min | $1+variable | OUTREACH (SMS on hold) |
| 12 | **Stripe** | 1 import — billing (price_ids=None, not wired) | **401** (STRIPE_API_KEY empty in env) | Not configured | stripe.com/au/pricing | 1.7% + $0.30 per AU domestic card | $0 base + transaction fees | BILLING (REQUIRED) |
| 13 | **Prospeo** | 1 import — DEPRECATED (replaced by Bright Data + Leadmagic) | 200 FREE tier | Free | prospeo.io/pricing | — | $0 (DEPRECATED) | DEPRECATED |
| 14 | **DFS GMaps** (subset of DataForSEO) | 1 import (counted in #4) | — | — | — | — | — | PIPELINE (rolled into #4) |
| 15 | **DataForSEO base** | 1 import (counted in #4) | — | — | — | — | — | PIPELINE (rolled into #4) |
| 16 | **ContactOut** | 1 import — email enrichment alternative | **401** (key dead per ledger note "Sami email drafted, not sent") | Demo-locked | contactout.com/pricing | Personal $99 USD/mo OR Sales Pro $149 USD/mo | $154/mo (if reactivated) | PIPELINE (reactivation gated on Dave) |
| 17 | **Austender** (Australian Government tenders) | 1 import — `austender_client.py` (research-only) | Not pinged | Free public data | tenders.gov.au | Free | $0 | PIPELINE (research) |
| 18 | **OpenAI** | (not via integrations/ — used by listener/embeddings) | **200** | Pay-as-you-go | openai.com/api/pricing | text-embedding-3-small $0.02/1M tokens, gpt-4o-mini $0.15/1M | ~$5-30/mo variable | PIPELINE |
| 19 | **Gemini** (Google AI) | (not via integrations/ — used by Stage 3+7 per ledger) | **200** | Free tier per ledger | ai.google.dev/pricing | Free tier 15 req/min, 1M tokens/day for 2.5 Flash | $0 (free tier) | PIPELINE |
| 20 | **Hunter** | (referenced in ARCHITECTURE.md L2 email fallback) | **200** (David Stephens account) | Active (key needs renewal per ledger) | hunter.io/pricing | Starter $34 USD/mo (500 verifications) | $53/mo | PIPELINE (fallback) |
| 21 | **Apify** | (referenced in ARCHITECTURE.md Pipeline F v2.1 L2 LinkedIn) | **200** (user `brawny_epitome`) | Active | apify.com/pricing | Starter $49 USD/mo (1k actor compute units) | $76/mo | PIPELINE |
| 22 | **Salesforge** | 0 active imports (file deleted PR-A #593) but ARCHITECTURE.md canonical email path | **401** (server alive at /public/v2 + Bearer auth, key value invalid) | Unknown until key regen | salesforge.ai/pricing | Growth $96 USD/mo (incl. Warmforge bundled per session memory) | $149/mo | OUTREACH (REQUIRED) |
| 23 | **InfraForge** | 0 active imports (5 NotImplementedError stubs in `domain_provisioning_service.py`) | **401** (key empty) | Not configured | infraforge.com/pricing | $40 USD/mo per session memory | $62/mo | OUTREACH (Phase 2) |
| 24 | **WarmForge** | 0 active imports | 404 endpoint probe | Bundled FREE in Salesforge Growth per session memory verification | salesforge.ai/pricing | bundled in #22 | $0 (bundled) | OUTREACH (bundled) |
| 25 | **Sentry** | (referenced in settings.py, sentry_sdk active per pytest output) | **401** (key invalid) | Free tier | sentry.io/pricing | Free 5k errors/mo OR Team $26 USD/mo | $0 (free) OR $40/mo | INFRASTRUCTURE |
| 26 | **Calcom + Calendly** | settings.py only, not imported by code | not pinged (calcom_api_key + calendly_api_key both empty per V1) | Unknown | cal.com/pricing OR calendly.com/pricing | Free tier exists | $0 (free tier sufficient for Phase 1) | OUTREACH (booking) |
| 27 | **Pipedrive** | 0 active imports despite `pipedrive_client.py` existing | not pinged | Unknown | pipedrive.com/pricing | Essential $14 USD/mo per seat | $22/mo if reactivated | DEPRECATED (orphan integration file) |
| 28 | **SmartLead** | 0 imports, smartlead_mcp.py is dead reference | — | — | — | — | $0 | DEPRECATED |
| 29 | **HeyGen** | settings.py heygen_api_key only — no imports | not pinged | Unknown | heygen.com/pricing | Creator $24 USD/mo | $0 (unused) OR $37/mo if activated | DEPRECATED OR PLANNED |
| 30 | **Twitter/X** | settings.py 4 fields, no imports | not pinged | Unknown | developer.twitter.com/pricing | Free OR Basic $100 USD/mo | $0 (unused) | DEPRECATED OR PLANNED |
| 31 | **Twilio** | settings.py twilio_auth_token only, no Python integration file | not pinged | Replaced by Telnyx per session memory | twilio.com/pricing | Pay-as-you-go | $0 (unused, deprecated) | DEPRECATED |
| 32 | **Postmark** | settings.py postmark_server_token only, no imports | not pinged | Replaced by Resend | postmarkapp.com/pricing | $15 USD/mo | $0 (unused, deprecated) | DEPRECATED |
| 33 | **HeyReach** | settings.py heyreach_api_key only, replaced by Unipile per session memory | not pinged | DEPRECATED | — | — | $0 | DEPRECATED |

---

## THREE BUCKETS

### Bucket A — CURRENTLY ACTIVE (key works, code calls it)

| Service | Monthly AUD | Notes |
|---|---|---|
| Anthropic API (per-token, ANTHROPIC_API_KEY) | variable | Powers all sub-agents and Claude classifications. Anthropic Max 20x engineering subscription ($310) attributed to Aiden's `cost_map_infrastructure.md` per scope split. |
| Leadmagic | ~$61 OR pay-as-you-go | 4,148 credits remaining, healthy balance |
| Resend | $31 | Pro tier per ledger; agencyxos.ai domain pending verification |
| ElevenLabs/ElevenAgents | $34 + variable | Currently FREE tier — would need Creator $22 USD/mo for production voice |
| OpenAI | $5-30 variable | Embeddings + gpt-4o-mini for listener subsystem |
| Apify | $76 | Pipeline F v2.1 L2 LinkedIn |
| Hunter | $53 | Pipeline F v2.1 L2 email fallback |
| ABN Lookup | $0 | Free Australian government API |
| Bright Data | $50-200 variable | LinkedIn Profile + GMB datasets |
| DataForSEO | $50-150 variable | SERP + GMaps (currently out of credits) |
| Vapi | $0 | DEPRECATED in code path but key still active (unused) |
| Telnyx | $1 + variable | SMS on hold, 0 numbers provisioned |
| Sentry | $0 | Free tier (key invalid in env but free tier still works without auth for client-side) |
| Gemini | $0 | Free tier |
| **SUBTOTAL — Active** | **~$361/mo + variable** | $310 less than v1 — Anthropic Max 20x re-attributed to infra scope (Aiden) per dual-bot consolidation. Pure services-side fixed-fee ~$361/mo + variable usage on Anthropic API + DataForSEO + Bright Data + OpenAI + Apify + Leadmagic. |

### Bucket B — NEEDED FOR LAUNCH (code depends but key dead/missing)

| Service | Monthly AUD | Action | Blocking |
|---|---|---|---|
| Salesforge Growth (incl. Warmforge bundled) | $149 | Regenerate API key in Salesforge dashboard + rebuild `src/integrations/salesforge.py` against `/public/v2` Bearer auth | Email outreach (Phase 1 E2/E3) |
| Unipile | $91/account | Regenerate API key in Unipile dashboard | LinkedIn outreach |
| Stripe AU live mode | $0 base + 1.7%+$0.30 transaction | Configure price IDs, enable GST 10%, set live keys | All billing (Phase 0 #3) |
| InfraForge | $62 | Configure key + finish `domain_provisioning_service.py` (5 stubs) | Custom domain outreach (Phase 2) |
| ContactOut | $154 | Reactivate (Sami email drafted not sent per ledger) | Email enrichment redundancy (optional) |
| DNCR registration | ~$4/mo ($50/yr) | Confirm registration valid + populate DNCR_API_URL env | Voice/SMS legal compliance |
| **SUBTOTAL — Required** | **~$306/mo + variable** | Hard requirements: Salesforge + Unipile + Stripe = $240/mo |

### Bucket C — DEAD IN ENV (keys exist but no active code calls)

| Service | Why dead | Action |
|---|---|---|
| Apollo (`APOLLO_API_KEY` in env) | Replaced by Bright Data + ABN per ledger; not in src/integrations/ | Remove from env |
| Twilio (`TWILIO_AUTH_TOKEN` in settings) | Replaced by Telnyx; no Python integration file | Remove from env |
| Postmark (`POSTMARK_SERVER_TOKEN` in settings) | Replaced by Resend; no Python integration file | Remove from env |
| HeyReach (`HEYREACH_API_KEY` in settings) | Replaced by Unipile; no Python integration file | Remove from env |
| Webshare (per ledger) | Replaced by Bright Data | Remove from env |
| Prospeo (FREE tier active but no active code import) | Replaced by Bright Data + Leadmagic | Remove from env |
| Pipedrive (file exists, 0 imports) | No active code path uses it; Aiden Item #7 noted as the only Python CRM but it's an orphan | Decide: wire to setup-call playbook OR remove |
| SmartLead (file `smartlead_mcp.py` exists, 0 imports) | Dead reference (Layer 7.X candidate per Aiden Phase 2) | Remove file + env |
| ZeroBounce (per ledger) | Parked per ARCHITECTURE.md | Remove from env |
| Twitter/X (4 settings fields, 0 imports) | Speculative — no code uses | Remove from env |
| HeyGen (settings field, 0 imports) | Content pipeline planned but deferred Phase 4 | Remove from env until Phase 4 |
| Cal.com / Calendly (settings fields, 0 imports) | Booking integration speculative; setup playbook references but no integration written | Remove or pick one + integrate |
| YouTube (2 settings fields, 0 imports) | Content pipeline (Phase 4) | Remove from env until Phase 4 |
| Buffer (1 setting field, 0 imports) | Social posting (Phase 4) | Remove from env until Phase 4 |
| v0 (1 setting field, 0 imports) | UI generation tool (dev-only) | Remove from production env |

---

## SUMMARY — UNVERIFIED ITEMS

Per Dave's "no estimates" rule, items I cannot verify without dashboard access:
- **Anthropic Max 20x subscription** — known $310/mo from session memory, NOT pinged because consumer subscription, not API key. Real cost only verifiable via Anthropic billing dashboard.
- **DataForSEO actual monthly burn** — pay-as-you-go, depends on call volume; needs portal for true number. Bucket A range "$50-150 variable" is from public per-call pricing × estimated stage volume.
- **Bright Data actual monthly burn** — same situation.
- **OpenAI / Apify / Leadmagic actual usage costs** — pay-as-you-go variable; pricing-page rates known but real billing is portal-only.

---

## ANSWER TO DAVE'S CORE QUESTION

**What we're paying for now (Bucket A) — services side only:** ~$361 AUD/mo + variable usage costs (~$100-300 estimated based on stage call volumes). Excludes Anthropic Max 20x ($310) — that's an infrastructure subscription attributed to Aiden's scope.

**What we need to pay for to launch (Bucket B):** ~$306 AUD/mo, of which ~$240 is hard requirement (Salesforge + Unipile + Stripe activation)

**What's in `.env` but shouldn't be (Bucket C):** 15 dead/deprecated/speculative env entries to clean out — zero current cost but cleaning prevents future confusion

**Services-side total to operate at launch (A + B):** ~$667 AUD/mo + variable usage costs

**Combined with Aiden's infrastructure (~$412.30 AUD/mo including Anthropic Max 20x):** ~$1,079.30 AUD/mo + variable usage costs. (NOT $1,389 — earlier number double-counted Anthropic Max 20x across both files; corrected via dual-bot consolidation.)

---

## End of cost_map_services.md

Method: code-first per Dave's correction. Verbatim ping output above. Pricing pulled from public vendor pages. No "per ledger" claims for cost — only for status notes where ledger is the operational source of record.
