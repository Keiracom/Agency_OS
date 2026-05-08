# audit_discovery_aiden.md

**Submitted:** 2026-05-07
**Author:** Aiden
**Workspace:** /home/elliotbot/clawd/Agency_OS-aiden/
**Branch:** aiden/scaffold (session branch, does not merge to main)

---

## 1. Role + ownership (one paragraph)

Aiden is one of two AI engineering bots running parallel to Elliot under Max-COO and Dave-CEO. I take build directives, do code-level engineering work (PR authoring, refactors, cleanups, tests, audits), peer-review Elliot's PRs (dual-approval rule applies), and dispatch heavy or long-running work to my clone ORION. Recent ownership in this session: Layer 6 SSOT drift detector (PR #606), onboarding-flow spec PR #609 + amendments, leadmagic mock-mode production guardrail (PR #610), Layer 7 SSOT cleanup peer-review (PR #611), audit on voice/LinkedIn/frontend/ops scope. I do not own product/strategy decisions — those route via Dave through Max.

---

## 2. Single source of truth (SSOT) for my work

| Surface | Location | Purpose |
|---|---|---|
| Operational architecture canon | `/home/elliotbot/clawd/Agency_OS-aiden/ARCHITECTURE.md` (also at top-level of repo) | Pipeline, vendors, tiers, deprecated items, scoring, validation rules, env vars, security, glossary, roadmap |
| CEO-facing mirror | Google Doc ID `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho` (Drive Manual) | CEO-facing state mirror of architecture |
| Process / governance | `docs/governance/SOP_ARCHITECTURE_SSOT.md` (ratified PR #606), `docs/governance/CONSOLIDATED_RULES.md` (7 rules ratified 2026-05-01) | SSOT discipline + consolidated rules |
| Identity | `/home/elliotbot/clawd/Agency_OS-aiden/IDENTITY.md` | Callsign canonical (LAW XVII) |
| Session memory (callsign-scoped) | `public.agent_memories` table in Supabase, filtered `WHERE callsign = 'aiden'` | Day-to-day session memory |
| Long-term feedback memory | `/home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/` (37 files indexed in `MEMORY.md`) | Cross-session feedback rules |
| CEO state | `public.ceo_memory` table in Supabase | Dave-facing state, directive counter, blockers |
| Specs (PR-merged) | `docs/specs/` (currently `onboarding_email_provisioning.md`) | Ratified design specifications |
| Inbox/outbox relay | `/tmp/telegram-relay-aiden/inbox/` and `/outbox/` | Telegram cross-post + clone dispatch |

---

## 3. Tools, platforms, services I interact with daily

| Tool | Purpose |
|---|---|
| `tg` CLI (group + DM modes) | Telegram cross-bot communication via group chat -1003926592540 |
| Bash | Filesystem inspection, grep, find, ruff, pytest |
| `git` + `gh` CLI | Branch/commit/push/PR operations on Keiracom/Agency_OS |
| Read / Edit / Write tools | File-level editing in conversation |
| Task tool (sub-agent dispatch) | research-1, build-2, build-3, test-4, review-5, devops-6, architect-0, Explore, Plan, general-purpose |
| MCP bridge (`/home/elliotbot/clawd/skills/mcp-bridge/scripts/mcp-bridge.js`) | Wraps 13+ MCP servers: supabase, redis, prefect, railway, prospeo, dataforseo, vercel, salesforge, vapi, telnyx, unipile, resend, memory |
| `mcp__keiradrive__keiradrive_search_doc` (loadable via ToolSearch) | Read CEO Drive Manual |
| `WebFetch` (loadable via ToolSearch) | Verify vendor pricing pages, JS-rendered content |
| Python 3 + pytest | Run tests, ruff format/check, manual verification |
| Supabase via MCP | Query agent_memories, ceo_memory, business_universe, lead_pool etc. |
| Clone dispatch (file-based) | Write JSON to `/tmp/telegram-relay-orion/inbox/` to dispatch ORION |

---

## 4. Reporting chain

```
Dave (CEO)
  └─ Max (COO, Dave-proxy in TG group, Tier-0 authority)
       ├─ Elliot (peer bot)
       │    └─ ATLAS (Elliot's clone, /home/elliotbot/clawd/Agency_OS-atlas/)
       └─ Aiden (this bot)
            └─ ORION (Aiden's clone, /home/elliotbot/clawd/Agency_OS-orion/)
```

**Up:** Dave (via Max). **Sideways:** Elliot (peer, dual-approval reciprocal). **Down:** ORION (clone, dispatched via inbox JSON). **Sub-agents (transient):** Task-tool spawns (research-1, build-2, etc.) — dispatched per work item, not persistent.

**Other clones in environment:** Scout (research clone for Elliot, `/home/elliotbot/clawd/Agency_OS-scout/`). Sometimes Atlas/Scout dispatched for parallel work.

---

## 5. Repository directory tree (top 2 levels)

**Top-level (`/home/elliotbot/clawd/Agency_OS-aiden/`):**
```
agency-os-html/          agency-os-prototype/    agents/
alembic/                 app-data/               builds/
campaigns/               canvas/                 competitive/
config/                  data/                   docs/
frontend/                governance/             hooks/
infra/                   landing-page-analysis/  maya-concepts/
mcp-servers/             memory/                 migrations/
projects/                prompts/                research/
scripts/                 skills/                 SKILLS/
src/                     .claude/                .git/
tests/                   tasks/
```

**Top-level files of note:** `ARCHITECTURE.md`, `CLAUDE.md`, `IDENTITY.md`, `AGENTS.md`, `MEMORY.md`, `SECURITY.md`, plus many `*_REPORT.md`, `*_PLAN.md`, audit docs.

**`src/` (2nd level) — backend Python:**
```
src/agent_coord/    src/agents/        src/api/         src/clients/
src/clone_dispatch.py  src/config/    src/coo_bot/     src/data/
src/detectors/      src/engines/       src/exceptions.py  src/integrations/
src/intelligence/   src/middleware/    src/models/       src/observability/
src/orchestration/  src/outreach/      src/pipeline/     src/services/
src/skills/         src/sso/           src/telegram_bot/  src/utils/
src/voice/          src/main.py
```

**`frontend/` (2nd level) — Next.js:**
```
frontend/app/        frontend/components/   frontend/contexts/
frontend/data/       frontend/hooks/        frontend/landing/
frontend/lib/        frontend/middleware.ts frontend/mocks/
frontend/public/     frontend/scripts/      frontend/sentry.client.config.ts
```

**`docs/` (2nd level) — documentation:**
```
docs/advice/         docs/architecture/   docs/archive/        docs/audits/
docs/clones/         docs/drafts/         docs/e2e/            docs/finance/
docs/governance/     docs/integrations/   docs/landing-variants/
docs/legal/          docs/manuals/        docs/marketing/      docs/ops/
docs/phases/         docs/pitch/          docs/postmortems/    docs/progress/
docs/research/       docs/roadmap/        docs/specs/          docs/strategy/
docs/voice/          docs/MANUAL.md       docs/project_structure.md
```

---

## 6. Governing files

| File | Purpose |
|---|---|
| `/home/elliotbot/clawd/Agency_OS-aiden/ARCHITECTURE.md` | Locked system architecture (586 lines, 14 sections incl. Security/Glossary/Roadmap added in PR #608). Authority: CEO. Do not modify without explicit CEO directive. |
| `/home/elliotbot/clawd/Agency_OS-aiden/CLAUDE.md` (43 lines, modular) | Project-config + auto-loaded module imports (`@.claude/modules/_*.md`) |
| `/home/elliotbot/clawd/Agency_OS-aiden/IDENTITY.md` | Callsign source-of-truth (LAW XVII) |
| `/home/elliotbot/clawd/Agency_OS-aiden/AGENTS.md` | Agent registry / role assignments |
| `/home/elliotbot/clawd/Agency_OS-aiden/.claude/modules/` | 11 module files (process, laws, session start/end, governance rules) — pointer modules per Layer 1 SSOT alignment (PR #603) |
| `/home/elliotbot/clawd/Agency_OS-aiden/docs/governance/CONSOLIDATED_RULES.md` | 7 ratified rules (2026-05-01) — VERIFY / COORDINATE / APPROVE / ORCHESTRATE / COMMUNICATE / GOVERN / BUSINESS |
| `/home/elliotbot/clawd/Agency_OS-aiden/docs/governance/SOP_ARCHITECTURE_SSOT.md` | SOP for Architecture SSOT discipline (ACTIVE 2026-05-07, PR #606) |
| `/home/elliotbot/clawd/Agency_OS-aiden/scripts/ssot_drift_check.sh` | Layer 6 drift detector (fires on `SessionStart:clear` per PR #607) |
| `/home/elliotbot/clawd/Agency_OS-aiden/.claude/settings.json` | Hook configuration including ssot_drift_check.sh wiring |
| `/home/elliotbot/clawd/Agency_OS-aiden/SECURITY.md` | Top-level security doc (existence verified, content not audited for this report) |
| `/home/elliotbot/clawd/Agency_OS-aiden/docs/MANUAL.md` | Human-readable manual (in-repo mirror; canonical-source disambiguation vs Drive Manual is a queued Dave question) |
| `/home/elliotbot/.claude/CLAUDE.md` (user-global, outside repo) | Elliottbot-as-CTO global identity instructions |
| `/home/elliotbot/clawd/CLAUDE.md` (parent-dir, project-root) | Project-root CLAUDE.md (in-repo file at repo root) |

---

## 7. Test baseline

```
$ python3 -m pytest --collect-only -q
3489/3493 tests collected (4 deselected) in 14.83s
```

- **Collected:** 3,489
- **Deselected:** 4
- **Total in test suite:** 3,493
- **Failing:** unknown — running full suite past collection-only is multi-minute work; baseline collection success is the data point reported here

**Test directory structure (top of `tests/`):**
```
tests/api/          tests/clones/         tests/coo_bot/       tests/dashboards/
tests/e2e/          tests/engines/        tests/integrations/  tests/intelligence/
tests/orchestration/ tests/outreach/      tests/pipeline/      tests/services/
tests/test_integrations/ tests/voice/    tests/test_*.py (~100s of files)
```

Markers in pytest.ini: `live` (real API calls, deselected by default), `integration`, `e2e`. Default `pytest -m "not live"` pattern covers offline tests; `pytest -m live` opts into real-API smoke tests added in PR #602.

---

## 8. Databases

**Supabase project:**
- **Project ID:** `jatzvazlbusedwsnqxzr` (sole project per CLAUDE.md §Supabase)
- **Region:** unknown — not exposed in CLAUDE.md or accessible env vars; would require direct Supabase dashboard access

**Schemas + table counts:**

### Schema: `elliot_internal` (4 tables)

```
api_keys_ledger      memories      prefect_logs      state
```

### Schema: `public` (141 tables)

```
_archive_lead_pool_mar25       _archive_leads_mar25            ab_test_variants
ab_tests                       abn_registry                    activities
activity_stats                 admin_notifications             agency_communication_profile
agency_exclusion_list          agency_service_profile          agent_comms
agent_memories                 api_rate_limits                 approval_queue
audit_logs                     business_decision_makers        business_reviews
business_universe              campaign_discovery_log          campaign_lead_messages
campaign_leads                 campaign_resources              campaign_sends
campaign_sequences             campaign_suggestion_history     campaign_suggestions
campaigns                      ceo_memory                      ceo_memory_archive
cis_adjustment_log             cis_agency_learnings            cis_agency_pool_config
cis_agent_metrics              cis_als_tier_conversions        cis_ceo_corrections
cis_channel_performance        cis_directive_metrics           cis_global_learning_pool
cis_improvement_log            cis_message_patterns            cis_outreach_outcomes
cis_reply_classifications      cis_run_log                     client_crm_configs
client_customers               client_dashboard_flags          client_intelligence
client_linkedin_credentials    client_personas                 client_portfolio
client_projects                client_resources                client_suppression
clients                        conversation_threads            conversion_pattern_history
conversion_patterns            coordinator_claims              crm_push_log
crm_sync_log                   deal_stage_history              deals
demo_bookings                  digest_logs                     discarded_leads
discovery_queries              discovery_results               dm_messages
domain_suppression             domain_warmup_status            elliot_knowledge
elliot_session_state           elliot_signoff_queue            elliot_status
elliot_tasks                   email_events                    email_templates
enrichment_diagnostic          enrichment_raw_responses        evo_auth_requests
evo_flow_callbacks             evo_task_queue                  evo_task_results
founding_members               founding_waitlist               frozen_artifacts
global_suppression             gmb_pilot_results               gmb_vendor_test
gmb_vendor_test_dfs            gmb_vendor_test_dfs_biz         gmb_vendor_test_dfs_v2
governance_events              health_checks                   human_review_queue
icp_extraction_jobs            icp_refinement_log              industry_keywords
lead_agency_suppression        lead_assignments                lead_lineage_log
lead_outreach_history          lead_permission_overrides       lead_pool
lead_signal_changes            lead_social_posts               lead_tags
leads                          linkedin_account_daily_state    linkedin_action_queue
linkedin_connections           linkedin_seats                  location_suburbs
meetings                       memberships                     outreach_telemetry
personas                       platform_buyer_signals          platform_timing_signals
replies                        resource_pool                   revenue_attribution
sales_pipeline                 sales_pipeline_history          scheduled_touches
scraper_health_log             sdk_usage_log                   signal_configurations
suppression_list               telegram_sessions               thread_messages
tier_registry                  trading_names                   unipile_accounts
users                          voice_call_context              voice_calls
waitlist                       webhook_configs                 webhook_deliveries
```

**Total: 145 tables across 2 schemas.**

Note: 157 migrations exist in `alembic/versions/` per Max's audit. Schema may have additional schemas not queried (e.g., `auth.*` Supabase-managed).

---

## 9. External APIs and services

Per `ARCHITECTURE.md` §SECTION 4 — LIVE VENDORS:

| Vendor | Purpose | Active status | API key status |
|---|---|---|---|
| **DataForSEO** | T0 multi-category discovery, T-DM0 ad spend + DM signals | ACTIVE | env vars `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` present in `~/.config/agency-os/.env` (not verified working in this audit) |
| **Bright Data** | T2 GMB backfill (gd_m8ebnr0q2qlklc02fz), T1.5 LinkedIn Company, T-DM2 LinkedIn Profile, generic web scrape | ACTIVE | `BRIGHTDATA_API_KEY` present, verified working in PR #602 live-smoke (BD GMB + BD LinkedIn URL-input) |
| **ABR (data.gov.au)** | ABN + trading name lookup | ACTIVE | `ABN_LOOKUP_GUID` present, verified working in PR #602 live-smoke |
| **Leadmagic** | Email + mobile enrichment | ACTIVE | `LEADMAGIC_API_KEY` present, status unknown without re-verification |
| **Jina AI Reader** | Web scrape (Tier 2 scraper waterfall) | ACTIVE | No API key required (free tier) |
| **Anthropic API** | Claude Haiku/Sonnet/Opus | ACTIVE | `ANTHROPIC_API_KEY` present |
| **Salesforge** | Email outreach | **BROKEN — API key returns 401** per Max audit; `salesforge` MCP server config in settings.json but `src/integrations/salesforge.py` does not exist |
| **Unipile** | LinkedIn outreach (connections, DMs) | ACTIVE | env var present in `.env`, `src/integrations/unipile.py` 25.7KB substantive |
| **ElevenAgents** | Voice AI persona (Alex) | ACTIVE | env vars `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` present, `src/integrations/elevenagents_client.py` 22.4KB substantive |
| **Telnyx** | SMS outreach + voice PSTN | ACTIVE (code), UNTESTED LIVE | `src/integrations/telnyx_client.py` 17.7KB substantive; per Max audit "untested live" |

**Other vendor env vars present in `.env` (per `grep -oE "^[A-Z_]+="`):**
APIFY_API_TOKEN, APOLLO_API_KEY, BRAVE_API_KEY, CLICKSEND_API_KEY+USERNAME, CLOUDFLARE_ACCOUNT_ID+API_TOKEN+ZONE_AGENCYXOS+ZONE_KEIRACOM, CONTACTOUT_API_KEY, COO_BOT_TOKEN, CREDENTIAL_ENCRYPTION_KEY, CSB_API_KEY, DATABASE_URL+DATABASE_URL_MIGRATIONS, EXPO_TOKEN, GEMINI_API_KEY+GEMINI_API_KEY_BACKUP. Many of these reference vendors deprecated or pending — see ARCHITECTURE.md §3 DEPRECATED VENDORS for canonical deprecation list.

**Vendor key status canonical reference:**
`elliot_internal.api_keys_ledger` table exists per discovery in this audit but column schema not queried (column-name lookup failed in MCP shell escape during this audit). Per memory pin `api_key_lookup_sop`: query this table before assuming any key works.

**Deprecated per ARCHITECTURE.md §3 (not active):**
Clay, Hunter.io (except L2 fallback), Kaspr, Proxycurl, Apollo (deprecated for enrichment), Apify (deprecated for GMB; some narrow exceptions), Webshare, SERP API, Direct mail, ZeroBounce, Lemlist, SmartLead.

---

## End of report
