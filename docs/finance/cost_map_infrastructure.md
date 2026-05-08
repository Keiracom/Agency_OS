# cost_map_infrastructure.md — Agency OS Infrastructure Cost Map

**To: Dave (CEO), via Max (COO)**
**From: Aiden**
**Compiled: 2026-05-08**
**Method:** Code-first → public pricing pages → AUD conversion at 1.55 (LAW II). No portal-access claims. No estimates where verification is possible.

---

## METHODOLOGY

1. Read deployment configs (`railway.toml`, `vercel.json`, `frontend/vercel.json`)
2. Probe Vercel team via MCP (project list + region mapping)
3. Ping every LLM/infra API key from `.env` (HTTP 200/401/404 = key status)
4. Cross-reference public pricing pages
5. Convert USD → AUD at 1.55

**Verified live (HTTP 200 ping today):** Anthropic API, OpenAI, OpenRouter, Groq, Gemini, GitHub, Cloudflare, Namecheap. All 7 keys live.

---

## CONFIRMED INFRASTRUCTURE — ACTIVE

| Platform | Tier | What it runs | Verified Status | USD/mo | AUD/mo | Downgrade? |
|---|---|---|---|---|---|---|
| **Supabase** | Pro | PostgreSQL DB (jatzvazlbusedwsnqxzr, 212 tables, ap-southeast-1 Singapore) + Auth + Edge functions | Max V1 confirmed $38.75 AUD/mo from billing portal | $25 | **$38.75** | NO — RLS/multi-tenancy needs Pro |
| **Railway** | usage-based | 9 services in `agency-os` project: agency-os (FastAPI 2GB), prefect-server (1GB), prefect-worker (4GB), prefect-postgres, restate-py-service, restate-server, reacher, opa-gatekeeper, auditor-phoenix | Max V1 confirmed ~$31 AUD/mo base. Total likely materially higher; needs Railway dashboard read for accurate. | varies | **~$31 base** | Possibly: prune restate-py-service + auditor-phoenix if not in Phase 1 critical path |
| **Vercel** | Pro (inferred) | 3 production projects: frontend (Next.js, syd1) → app.agencyxos.ai · agencyxos-marketing → agencyxos.ai · admin-dashboard → admin.agencyxos.ai. 20+ total projects. Team `dvidstephens-2724's projects`. | Custom domains across 3 deployments = Pro tier required. Hobby tier blocks team + custom domains. | $20/seat | **$31** | NO — multiple custom domains require Pro |
| **Anthropic Max 20x** | Subscription | Claude Code + sub-agents for engineering/audit/research | Per Dave. Pricing confirmed via Anthropic public announcement (Aug 2025). | $200 | **$310** | YES if engineering velocity drops — Max 5x = $100 USD |
| **GitHub** | Free | Public repo Keiracom/Agency_OS, Actions CI | API ping HTTP 200, repo accessible | $0 | **$0** | n/a |
| **Cloudflare** | Free | DNS zones for keiracom + agencyxos | Account ID + 2 zones in env, API ping HTTP 200 | $0 | **$0** | n/a — Free tier sufficient |
| **Namecheap** | per-domain | Domain registrations (agencyxos.ai etc.) | API ping HTTP 200, key valid | ~$1/mo | **~$1.55** | n/a — base cost minimal |
| **CONFIRMED MONTHLY SUBTOTAL** | | | | | **~$412.30 AUD** | |

---

## VARIABLE COST — LLM API USAGE (UNVERIFIED MEASURED)

| Provider | Key Status | Used By | Pricing | Measured Spend |
|---|---|---|---|---|
| **Anthropic API** (separate from Max subscription) | HTTP 200 | Pipeline AI calls (Sonnet/Opus/Haiku via SDK) | per-token: Sonnet input $3/M tokens, output $15/M | **UNVERIFIED** |
| **OpenAI API** | HTTP 200 | Reply analysis fallback | per-token | **UNVERIFIED** |
| **OpenRouter API** | HTTP 200 | Multi-model fallback | per-token at provider rate + 5% | **UNVERIFIED** |
| **Groq API** | HTTP 200 | Fast inference fallback (Llama 3.3) | free tier ~14k requests/day | **UNVERIFIED** |
| **Gemini API** | HTTP 200 | Google AI fallback | free tier 1.5M tokens/day | **UNVERIFIED** |

**Why UNVERIFIED:** per Elliot V3b primary-source query, `sdk_usage_log` table has 0 rows. The cost-instrumentation infrastructure exists in schema but has never written from any of the 456 organic pipeline runs. Cannot give a measured number without burning the same trust problem as Max's `subscription_recurring` table.

**[PROPOSE:] Phase 1 cost-instrumentation task** (Elliot E1+ adjunct, ~2-3hr): wire `sdk_usage_log` writes into stage executors so the next pipeline run produces measurable cost-per-prospect data. Same memory pin as Elliot V3b. Until then: pay-per-token costs are CALCULABLE per call but TOTAL not MEASURED.

---

## DAVE-MENTIONED, CODEBASE-EVIDENCE-MISSING

| Platform | Why Dave mentioned | Code-base evidence | Verdict |
|---|---|---|---|
| **Vultr** | Listed in directive as known infrastructure platform | `grep -rE "vultr\|VULTR" .env src/ scripts/` returns ZERO hits. Not in railway.toml, vercel.json, frontend/vercel.json. No systemd unit named *vultr*. | **NO EVIDENCE in codebase.** Possibly a personal dev workstation (not deploy infra) OR a deprecated/never-onboarded provider. Flag for Dave to clarify. |

---

## DOWNGRADE ANALYSIS

**Cannot downgrade (load-bearing for product):**
- Supabase Pro — RLS, multi-tenant isolation, 212 tables → Pro is minimum
- Vercel Pro — 3 custom domains (agencyxos.ai, app.agencyxos.ai, admin.agencyxos.ai) → Pro is minimum
- Anthropic Max 20x — engineering velocity (193 directives in 56 days, 3.4/day per Elliot) — downgrade to Max 5x ($100 USD) feasible IF directive cadence drops post-Phase-1, but engineering is the throughput-bound resource right now

**Could downgrade (verify usage):**
- Railway: services like `restate-py-service` and `auditor-phoenix` are not in Phase 1 critical path — pruning could reduce base ~$10-15 USD/mo
- Anthropic API: free if Max-20x covers all internal traffic (sub-agents go through Claude Code, not API). Verify whether ANTHROPIC_API_KEY-using pipeline calls can route through Claude Code instead.

**Already at floor (no downgrade possible):**
- GitHub Free, Cloudflare Free, Namecheap per-domain

---

## PHASE 0 ENV-CLEANUP RECOMMENDATIONS

Per Dave's locked plan Phase 0 item 7 (clean dead env vars):

| Env Key | Status | Action |
|---|---|---|
| `VULTR_*` | Not present in .env (verified grep) | n/a — no cleanup needed |
| `OPENAI_API_KEY` | HTTP 200 (live) | Keep — used as Anthropic fallback |
| `OPENROUTER_API_KEY` | HTTP 200 (live) | Keep — multi-model fallback |
| `GROQ_API_KEY` | HTTP 200 (live) | Keep — free-tier fast-inference |
| `GEMINI_API_KEY` + `GEMINI_API_KEY_BACKUP` | HTTP 200 (both live) | Consolidate — only one needed unless intentional rotation |
| `NAMECHEAP_*` | HTTP 200 | Keep — domain registrar for agencyxos.ai |
| `CLOUDFLARE_*` | HTTP 200 | Keep — DNS for both zones |

---

## SUMMARY FOR MAX CONSOLIDATION

**Current confirmed infrastructure spend (monthly):** **~$412.30 AUD**

Decomposition:
- Supabase Pro: $38.75 AUD
- Railway base: ~$31 AUD (per Max V1; total may be higher pending dashboard verify)
- Vercel Pro: $31 AUD
- Anthropic Max 20x: $310 AUD (engineering subscription — separate budget category)
- GitHub: $0
- Cloudflare: $0
- Namecheap: ~$1.55 AUD/mo

**Variable LLM API usage on top:** UNVERIFIED until `sdk_usage_log` instrumentation lands in Phase 1.

**Pure-product floor (excluding Anthropic Max 20x as it's an engineering cost):** **~$102.30 AUD/mo**

**Required for launch (additions):** Stripe AU live mode (no monthly fee, % of GMV); Resend domain verification (Resend Pro $20 USD = $31 AUD/mo if needed for transactional volume; free tier covers 3,000 emails/mo).

---

## VERIFICATION TRAIL

```bash
# Railway projects (MCP)
$ node skills/mcp-bridge/scripts/mcp-bridge.js call railway list_projects | grep '"name"'
"agency-os", "prefect-postgres", "restate-py-service", "reacher", "opa-gatekeeper",
"agency-os", "auditor-phoenix", "prefect-server", "restate-server", "prefect-worker"
9 services in agency-os project

# Vercel team (MCP)
$ list_teams → team_IAEoUP4Fta5U2uuER7d8VGDm "dvidstephens-2724's projects"

# Supabase
project_ref=jatzvazlbusedwsnqxzr (per CLAUDE.md), Pro plan (per Max V1)

# Live API pings (HTTP 200 = key valid + service responding)
Anthropic: 200 | OpenAI: 200 | OpenRouter: 200 | Groq: 200 | Gemini: 200
GitHub: 200 | Cloudflare: 200 | Namecheap: 200

# Vultr negative grep (no evidence in codebase)
$ grep -rE "vultr|VULTR" .env src/ scripts/ → 0 hits
```
