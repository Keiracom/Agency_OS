# audit_discovery_elliot.md

**Author:** Elliottbot (callsign ELLIOT)
**Compiled:** 2026-05-07
**Worktree:** `/home/elliotbot/clawd/Agency_OS` (main branch)
**Format:** Phase 1 Discovery — facts and locations only.

---

## 1. Role and Ownership

I am Elliottbot, one of two peer CTO-tier agent bots on Agency OS (the other is Aiden). I orchestrate sub-agents and a clone (ATLAS), enforce the project's governance laws (LAW I-A through LAW XV-D), produce and review code via PRs, and write/verify Supabase memory state at session boundaries. I do not execute task work directly; I delegate to sub-agents (research-1, build-2/3, test-4, review-5, devops-6, architect-0, Explore) per LAW XI. My current owned scope this session has been the lead pipeline (Stages 1–11 in `cohort_runner.py`), enrichment vendor governance, AU compliance scoping, billing/Stripe scaffolding awareness, and SSOT alignment between `ARCHITECTURE.md` ↔ Drive Manual ↔ Supabase `ceo_memory`. Aiden owns the parallel reviewer role on shared files plus front-end / API / voice / SMS / LinkedIn / observability per the most recent split. Both bots dual-approve every PR before Max merges.

---

## 2. Single Source of Truth Locations

| Surface | Exact Location |
|---|---|
| Architecture canonical | `/home/elliotbot/clawd/Agency_OS/ARCHITECTURE.md` (in-repo) |
| Manual canonical (CEO SSOT) | Google Drive Doc ID `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho` |
| Manual mirror (in-repo) | `/home/elliotbot/clawd/Agency_OS/docs/MANUAL.md` |
| Governance rules | `/home/elliotbot/clawd/Agency_OS/docs/governance/CONSOLIDATED_RULES.md` (7 rules ratified 2026-05-01) |
| Architecture SSOT SOP | `/home/elliotbot/clawd/Agency_OS/docs/governance/SOP_ARCHITECTURE_SSOT.md` |
| Definition of Done | `/home/elliotbot/clawd/Agency_OS/DEFINITION_OF_DONE.md` |
| Project rules (Claude) | `/home/elliotbot/clawd/Agency_OS/CLAUDE.md` + `.claude/modules/_*.md` (10 modular files) |
| Global identity (user-level) | `/home/elliotbot/.claude/CLAUDE.md` |
| CEO directives + system state | Supabase `public.ceo_memory` (key-value) |
| My persistent memory | Supabase `elliot_internal.memories` (type: daily_log, core_fact, rule, decision, research) |
| Auto-memory feedback pins | `/home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/MEMORY.md` (index) + sibling `*.md` files |
| API key status ledger | Supabase `elliot_internal.api_keys_ledger` |
| Directive metrics | Supabase `public.cis_directive_metrics` |
| Identity callsign file | `/home/elliotbot/clawd/Agency_OS/IDENTITY.md` (currently empty in this worktree — flagged) |

---

## 3. Daily Tools / Platforms / Services

**Communication & Coordination**
- Telegram supergroup chat_id `-1003926592540` (sole human-facing channel for Dave + Max + peer bots; via `tg -g` script)
- Telegram listener log `/tmp/telegram-relay-elliot/`

**Compute / Hosting**
- Railway (Python services, Prefect worker)
- Vultr (separate VPS for some workers)
- Vercel (frontend)

**Data**
- Supabase Postgres (primary DB + auth + RLS)
- Upstash Redis (queue, inter-agent relay)

**Orchestration**
- Prefect (flow runs, deployments, scheduled work)

**Repository / CI**
- GitHub (`elliotbot/...` org, `elliot/...` and `aiden/...` branch prefixes)
- pre-commit (ruff hook)

**MCP Bridge** (`skills/mcp-bridge/scripts/mcp-bridge.js`) servers: supabase, redis, prefect, railway, prospeo, dataforseo, vercel, salesforge, vapi, telnyx, unipile, resend, memory, keiradrive, keiramail

**Sub-Agents** (Anthropic Agent SDK via Claude Code Agent tool):
architect-0 (Opus), research-1 (Haiku), build-2 (Sonnet), build-3 (Sonnet), test-4 (Haiku), review-5 (Sonnet), devops-6 (Haiku), Explore (Haiku), plus ~30 named auditor and Fix-NN agents

**Clone (parallel worker)**
- ATLAS — workspace `/home/elliotbot/clawd/Agency_OS-atlas/`, tmux session `atlas`, inbox `/tmp/telegram-relay-atlas/inbox/`, outbox `/tmp/telegram-relay-atlas/outbox/`, service `atlas-inbox-watcher`, dispatch via signed JSON or unsigned (HMAC optional)

---

## 4. Reporting Structure

```
Dave (CEO, ultimate decision-maker)
  └── Max (COO proxy, Tier 0 authority delegated by Dave)
        ├── Elliot (peer bot — me)
        │     └── ATLAS (clone, parallel work)
        │     └── sub-agents (spawned per task: research-1, build-2/3, test-4, review-5, devops-6, architect-0, Explore, fixers, auditors)
        └── Aiden (peer bot — equal-authority peer to me)
              └── ORION (clone, parallel work)
              └── sub-agents (same agent registry)
```

I report to Dave (currently relayed via Max). I have no direct human reports. ATLAS and sub-agents report to me. Aiden reports to Dave parallel to me; Aiden and I cross-review every PR (dual-approval rule). Max can merge after dual-bot approval without Dave's per-PR sign-off.

---

## 5. Repository Directory Tree (Top 2 Levels)

```
Agency_OS/
├── agency-os-html/
├── agency-os-prototype/        (app, components, data, lib)
├── agents/                     (builder, fixer, prompts, qa)
├── alembic/                    (versions)
├── app-data/
├── builds/
├── campaigns/
├── canvas/
├── .claude/                    (agents, commands, hooks, modules, skills)
├── .clawdbot/
├── .clawdhub/
├── competitive/                (screenshots)
├── config/
├── data/
├── docs/                       (advice, architecture, archive, audits, clones, drafts,
│                                e2e, finance, governance, integrations, landing-variants,
│                                legal, manuals, marketing, ops, phases, pitch, postmortems,
│                                progress, research, roadmap, specs, strategy, voice)
├── frontend/                   (app, components, contexts, data, hooks, landing, lib,
│                                mocks, public, scripts, src, types, .vercel)
├── .githooks/                  (post-commit)
├── .github/                    (workflows)
├── governance/                 (memory)
├── hooks/                      (context-warning, session-supabase)
├── infra/                      (coo, observability, opa, phoenix, relay, restate)
├── landing-page-analysis/      (animation-frames)
├── logs/
├── maya-concepts/
├── mcp-servers/                (dataforseo, gmail, memory, prefect, prospeo, railway,
│                                resend, salesforge, telegram, telnyx, unipile, vapi, vercel)
├── memory/                     (decisions, leadmagic-trial)
├── migrations/
├── projects/                   (elliot-pwa)
├── prompts/
├── research/                   (d1_2_audit, d1_4_reaudit, d1_8_2_extraction, d1_8_3_synthesis,
│                                d2_audit, d2_cascade)
├── scripts/                    (output)
├── skills/                     (agents, asic-new-co, austender, callback-poller, campaign,
│                                conversion, crm, dataforseo, decomposer, drive-manual,
│                                frontend, hubspot, leadmagic, linkedin, mcp-bridge,
│                                pipedrive, pr-tool, seek, smartlead, superpowers, testing,
│                                three-store-save)
├── SKILLS/                     (uppercase variant — coexists with skills/)
├── src/                        (agents, api, clients, common, config, coo_bot, data,
│                                detectors, engines, enrichment, evo, fixtures, governance,
│                                integrations, intelligence, memory, models, observability,
│                                orchestration, outreach, pipeline, prefect_utils, prompts,
│                                relay, scraper, security, services, telegram_bot, utils, voice)
├── supabase/                   (functions, migrations, seeds, .temp)
└── tests/                      (api, ci_guards, config, coo_bot, e2e, enrichment, fixtures,
                                 governance, integration, integrations, intelligence, live,
                                 memory, migrations, observability, orchestration, outreach,
                                 pipeline, scripts, security, telegram_bot, test_api,
                                 test_clients, test_detectors, test_engines, test_flows,
                                 test_integrations, test_intelligence, test_pipeline,
                                 test_services, test_skills, unit)
```

Note: `tests/` and `tests/test_*` coexist (legacy structure not yet consolidated). `skills/` and `SKILLS/` coexist (case duplication).

---

## 6. Governing Files (Names + Paths)

**Architecture / SSOT**
- `/home/elliotbot/clawd/Agency_OS/ARCHITECTURE.md` — canonical pipeline, stages, vendors
- `/home/elliotbot/clawd/Agency_OS/docs/MANUAL.md` — Manual mirror (CEO SSOT lives in Drive)
- `/home/elliotbot/clawd/Agency_OS/AGENCY_OS_STRATEGY.md`
- `/home/elliotbot/clawd/Agency_OS/AGENTS.md`

**Governance**
- `/home/elliotbot/clawd/Agency_OS/docs/governance/CONSOLIDATED_RULES.md` — 7 ratified rules (2026-05-01)
- `/home/elliotbot/clawd/Agency_OS/docs/governance/SOP_ARCHITECTURE_SSOT.md`
- `/home/elliotbot/clawd/Agency_OS/governance/SOUL.md`
- `/home/elliotbot/clawd/Agency_OS/governance/ENFORCE.md`
- `/home/elliotbot/clawd/Agency_OS/governance/MEMORY.md` (deprecated for new writes)
- `/home/elliotbot/clawd/Agency_OS/governance/HANDOFF-clawd.md`
- `/home/elliotbot/clawd/Agency_OS/governance/research1-standing-brief.md`
- `/home/elliotbot/clawd/Agency_OS/governance/TOOLS.md`
- `/home/elliotbot/clawd/Agency_OS/ENFORCE.md` (root-level mirror)
- `/home/elliotbot/clawd/Agency_OS/HANDOFF.md` (root-level)

**Definition of Done / Process**
- `/home/elliotbot/clawd/Agency_OS/DEFINITION_OF_DONE.md`
- `/home/elliotbot/clawd/Agency_OS/CLAUDE.md` — project worktree config
- `/home/elliotbot/clawd/Agency_OS/.claude/modules/` — 10 modular project rule files (`_project_overview.md`, `_law_step0.md`, `_session_start.md`, `_law_clean_tree.md`, `_law_architecture_first.md`, `_mcp_bridge.md`, `_governance_rules.md`, `_dead_references.md`, `_enrichment_path.md`, `_directive_format.md`, `_session_end.md`)
- `/home/elliotbot/.claude/CLAUDE.md` — global identity (Elliottbot CTO config)

**Bootstrap / Deployment**
- `/home/elliotbot/clawd/Agency_OS/BOOTSTRAP.md`
- `/home/elliotbot/clawd/Agency_OS/DEPLOYMENT.md`
- `/home/elliotbot/clawd/Agency_OS/DEPLOYMENT_ISSUES.md`
- `/home/elliotbot/clawd/Agency_OS/AUTONOMOUS_EXECUTION_PLAN.md`
- `/home/elliotbot/clawd/Agency_OS/docker-compose.yml`
- `/home/elliotbot/clawd/Agency_OS/.github/workflows/` — CI definitions

**Project / Misc**
- `/home/elliotbot/clawd/Agency_OS/README.md`
- `/home/elliotbot/clawd/Agency_OS/IDENTITY.md` — empty in this worktree (flagged)
- `/home/elliotbot/clawd/Agency_OS/CEO_QUESTIONS.md`
- `/home/elliotbot/clawd/Agency_OS/DAVE_INPUT_FORM.md`
- `/home/elliotbot/clawd/Agency_OS/FILE_TREE.md`
- 40+ additional `*.md` audit/report files at repo root (legacy)

**Hooks**
- `/home/elliotbot/clawd/Agency_OS/.githooks/post-commit`
- `/home/elliotbot/clawd/Agency_OS/.claude/hooks/inbox_check_hook.sh`, `recorder_hook.sh`, `stop_relay_hook.sh`
- `/home/elliotbot/clawd/Agency_OS/scripts/ssot_drift_check.sh` — wired to SessionStart:clear

---

## 7. Test Baseline

Run: `pytest tests/` from `/home/elliotbot/clawd/Agency_OS/` on branch `elliot/docs-enrichment-ref-sweep` at HEAD `33911164` on 2026-05-07.

- **Collected:** 3480 tests (4 deselected per pytest config)
- **First failure observed:** `tests/integrations/test_dncr_client.py::TestHappyPathRegistered::test_registered_true` (run with `-x` exited at 362 passed / 1 failed / 4 deselected after 53.25s)
- **Full pass/fail/skip totals:** unknown — second run (without `-x`, excluding `tests/live` and `tests/e2e`) hit my 180s timeout before completion within the 30-minute audit budget
- **Warnings:** 57 (httpx DeprecationWarning, asyncio event loop, supabase timeout/verify deprecations, pydantic datetime.utcnow)
- **Test directory layout duplication noted:** `tests/api/` vs `tests/test_api/`, `tests/integrations/` vs `tests/test_integrations/` — both exist concurrently

Per Manual entry referenced earlier in session: "2152 passed, 0 failed, 28 skipped" (date of that baseline not re-verified in this audit).

---

## 8. Databases

### Supabase Project (sole production database)

- **Project ID:** `jatzvazlbusedwsnqxzr`
- **Project name:** `agency-os-prod`
- **Organization slug:** `jzgvxdbaunqnbxpttsut`
- **Region:** `ap-southeast-1` (Singapore)
- **Postgres version:** 17.6.1.063 (engine 17, GA)
- **Host:** `db.jatzvazlbusedwsnqxzr.supabase.co`
- **Status:** ACTIVE_HEALTHY
- **Created:** 2025-12-19

### Schemas + Tables (every table queried via information_schema)

**`auth` (23 tables — Supabase managed):**
audit_log_entries, custom_oauth_providers, flow_state, identities, instances, mfa_amr_claims, mfa_challenges, mfa_factors, oauth_authorizations, oauth_client_states, oauth_clients, oauth_consents, one_time_tokens, refresh_tokens, saml_providers, saml_relay_states, schema_migrations, sessions, sso_domains, sso_providers, users, webauthn_challenges, webauthn_credentials

**`elliot_internal` (4 tables):**
api_keys_ledger, memories, prefect_logs, state

**`extensions` (2):** pg_stat_statements, pg_stat_statements_info

**`finops_demo` (4):** accounts, daily_performance, holdings, transactions

**`keiracom_admin` (21):**
agent_budget_limits, agent_status_observations, api_keys_due_for_rotation, api_keys_inventory, approval_queue, bank_balance_snapshots, client_emails, cost_observations, dashboard_messages, dave_corrections, deploy_observations, email_events, kill_switch_state, monthly_burn, outreach_funnel_stats, pr_activity, pr_observations, runway_estimate, session_health, session_health_current, subscription_recurring, task_queue, task_queue_active

**`outreach` (1):** sends

**`public` (~119 tables — primary application schema):**
_archive_lead_pool_mar25, _archive_leads_mar25, ab_test_variants, ab_tests, abn_registry, activities, activity_stats, admin_notifications, agency_communication_profile, agency_exclusion_list, agency_service_profile, agent_comms, agent_memories, api_rate_limits, approval_queue, audit_logs, business_decision_makers, business_reviews, business_universe, campaign_discovery_log, campaign_lead_messages, campaign_leads, campaign_resources, campaign_sends, campaign_sequences, campaign_suggestion_history, campaign_suggestions, campaigns, ceo_memory, ceo_memory_archive, cis_adjustment_log, cis_agency_learnings, cis_agency_pool_config, cis_agent_metrics, cis_als_tier_conversions, cis_ceo_corrections, cis_channel_performance, cis_directive_metrics, cis_global_learning_pool, cis_improvement_log, cis_message_patterns, cis_outreach_outcomes, cis_reply_classifications, cis_run_log, client_crm_configs, client_customers, client_dashboard_flags, client_intelligence, client_linkedin_credentials, client_personas, client_portfolio, client_projects, client_resources, client_suppression, clients, conversation_threads, conversion_pattern_history, conversion_patterns, coordinator_claims, crm_push_log, crm_sync_log, deal_stage_history, deals, demo_bookings, digest_logs, discarded_leads, discovery_queries, discovery_results, dm_messages, domain_suppression, domain_warmup_status, elliot_knowledge, elliot_knowledge_relevant, elliot_session_state, elliot_signoff_queue, elliot_status, elliot_tasks, email_events, email_templates, enrichment_diagnostic, enrichment_raw_responses, evo_auth_requests, evo_flow_callbacks, evo_task_queue, evo_task_results, founding_members, founding_spots_status, founding_waitlist, frozen_artifacts, global_suppression, gmb_pilot_results, gmb_vendor_test, gmb_vendor_test_dfs, gmb_vendor_test_dfs_biz, gmb_vendor_test_dfs_v2, governance_events, health_checks, human_review_queue, icp_extraction_jobs, icp_refinement_log, industry_keywords, lead_agency_suppression, lead_assignments, lead_lineage_log, lead_outreach_history, lead_permission_overrides, lead_pool, lead_signal_changes, lead_social_posts, lead_tags, leads, linkedin_account_daily_state, linkedin_action_queue, linkedin_connections, linkedin_seats, location_suburbs, meetings, memberships, outreach_telemetry, personas, platform_buyer_signals, platform_timing_signals, replies, resource_pool, revenue_attribution, sales_pipeline, sales_pipeline_history, sales_pipeline_summary, scheduled_touches, scraper_health_log, sdk_usage_log, signal_configurations, suppression_list, telegram_sessions, thread_messages, tier_registry, trading_names, unipile_accounts, upcoming_demos, users, v_client_assignment_stats, v_client_lead_stats, v_lead_pool_stats, voice_call_context, voice_calls, waitlist, webhook_configs, webhook_deliveries

**`rag_demo` (1):** chunks

**`realtime` (10 — Supabase managed):** messages + 7 daily partitions, schema_migrations, subscription

**`storage` (8 — Supabase managed):** buckets, buckets_analytics, buckets_vectors, migrations, objects, s3_multipart_uploads, s3_multipart_uploads_parts, vector_indexes

**`supabase_migrations` (1):** schema_migrations

**`vault` (2):** decrypted_secrets, secrets

**Total:** ~196 tables across 12 schemas (auth/realtime/storage/vault are Supabase managed; application schemas are `public`, `elliot_internal`, `keiracom_admin`, `outreach`, `finops_demo`, `rag_demo`).

---

## 9. External APIs / Services

Source: Supabase `elliot_internal.api_keys_ledger` (canonical key status table) + ARCHITECTURE.md §4. As of last verification 2026-04-21.

### LIVE (verified key)
| Service | Env Var | Last Verified | Purpose |
|---|---|---|---|
| ABR | ABN_LOOKUP_GUID | 2026-04-16 | T1 Australian Business Register lookup (free) |
| Anthropic | ANTHROPIC_API_KEY | 2026-04-21 | Claude (Haiku/Sonnet/Opus) sub-agents |
| Apify | APIFY_API_TOKEN | 2026-04-15 | Pipeline F v2.1 L2 LinkedIn (`harvestapi/linkedin-profile-scraper`) + Stage 9 Facebook social |
| Bright Data | BRIGHTDATA_API_KEY | 2026-04-16 | T1.5/T2/T-DM1/2/3/4 — LinkedIn Profile (`gd_l1viktl72bvl7bjuj0`) + GMB Web Scraper (`gd_m8ebnr0q2qlklc02fz`) |
| ClickSend | CLICKSEND_API_KEY | unknown date | SMS (status: live in ledger, action item pending) |
| ContactOut | CONTACTOUT_API_KEY | 2026-04-20 | Email enrichment (demo-locked; credit purchase blocked) |
| DataForSEO | DATAFORSEO_LOGIN + _PASSWORD | 2026-04-16 | T0 GMB / T1.5a SERP Maps / T1.5b SERP LinkedIn / T-DM0 |
| Gemini | GEMINI_API_KEY | 2026-04-21 | Stages 3 + 7 (DM ID + voice). **Dave action: NOT in Railway/Vultr env — stages will fail.** |
| Hunter | HUNTER_API_KEY | 2026-04-21 | Pipeline F v2.1 L2 email fallback (score ≥70). Renewal pending |
| InfraForge | INFRAFORGE_API_KEY | unknown | Domain provisioning (alternative path) |
| Leadmagic | LEADMAGIC_API_KEY | 2026-04-20 | T3 email ($0.015) + T5 mobile ($0.077) |
| OpenAI | OPENAI_API_KEY | 2026-04-21 | Listener subsystem embeddings + gpt-4o-mini |
| Prefect | PREFECT_API_KEY + _URL | 2026-04-21 | Orchestration |
| Railway | RAILWAY_TOKEN | 2026-04-21 | Compute control plane |
| Redis | UPSTASH_REDIS_REST_TOKEN | 2026-04-21 | Queue / inter-agent relay |
| Resend | RESEND_API_KEY | 2026-04-21 | Transactional email (agencyxos.ai domain verification failed) |
| Supabase | DATABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY, SUPABASE_URL, SUPABASE_ACCESS_TOKEN, SUPABASE_JWT_SECRET | 2026-04-21 | DB + auth + RLS |
| Telegram | TELEGRAM_TOKEN | 2026-04-21 | Group chat + bot identity. **Dave action: add to Railway prefect-worker for on_failure_hook alerts.** |
| Twilio | TWILIO_AUTH_TOKEN | unknown | SMS (status live in ledger; not currently active in pipeline) |
| WarmForge | WARMFORGE_API_KEY | unknown | Email warmup (bundled with Salesforge Growth) |

### DEAD / 401 (key invalid or unauthorized)
| Service | Env Var | Status | Dave Action |
|---|---|---|---|
| **Salesforge** | SALESFORGE_API_KEY | dead_401 | "Add to Railway if outreach runs on Railway. Currently Vultr-only." (BLOCKER for outreach launch — code in `src/integrations/salesforge.py` was deleted PR-A #593, must be recreated) |
| **Unipile** | UNIPILE_API_KEY | dead_401 | "Add to Railway if LinkedIn outreach runs on Railway." |

### DEPRECATED (do not use — replacements active)
| Service | Env Var | Replacement |
|---|---|---|
| Apollo | APOLLO_API_KEY | Bright Data + BU JOIN |
| Prospeo | PROSPEO_API_KEY | Removed per LAW XIII |
| Vapi | VAPI_API_KEY | Replaced by ElevenAgents (per Manual; legacy code paths still exist) |
| Webshare | WEBSHARE_API_KEY | Bright Data |
| ZeroBounce | ZEROBOUNCE_API_KEY | Parked (Leadmagic for email verify) |

### UNKNOWN STATUS (key may or may not exist)
| Service | Env Var | Notes |
|---|---|---|
| Cal.com | CAL_API_KEY | unknown |
| Calendly | CALENDLY_API_KEY | unknown |
| ElevenLabs | ELEVENLABS_API_KEY | unknown — used by `src/integrations/elevenlabs.py` |
| Groq | GROQ_API_KEY | unknown |
| HeyGen | HEYGEN_API_KEY | unknown |
| Spider | SPIDER_API_KEY | unknown |
| **Stripe** | STRIPE_SECRET_KEY | unknown — **CRITICAL: not configured anywhere; blocks billing + onboarding + revenue path** |
| Telegram (alt) | TELEGRAM_BOT_TOKEN | unknown (separate from TELEGRAM_TOKEN above) |
| Telnyx | TELNYX_API_KEY | unknown — SMS on hold until post-launch |

### Vendors referenced in ARCHITECTURE.md but not in ledger
| Service | Notes |
|---|---|
| ElevenAgents (Voice AI Alex) | Active per ARCHITECTURE.md; key not tracked in `api_keys_ledger` |
| Jina AI Reader | Free, no key required |
| Forager | 404 (per session memory) |
| Reacher | Port 25 blocked on Railway/Vultr — not in active path |
| Adzuna | Sandbox per ARCHITECTURE.md §12 (not currently called) |
| Primeforge | Pre-warmed mailboxes — vendor-claimed pending API verification |

---

## End of audit_discovery_elliot.md

Facts and locations only per Dave's spec. No summaries, no opinions, no recommendations.
