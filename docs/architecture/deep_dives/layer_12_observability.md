# Layer 12 — Observability (deep-dive)

**Layer owner:** scout (this dive — Better Stack + metrics dashboard + alert routing slice) joint with Atlas (other observability slice — TBD per Atlas's own deep-dive).
**Dispatched by:** elliot, KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500.
**Date:** 2026-05-25.
**Cross-cites:** my earlier CI/CD gap audit (PR #1125 — rollback runbook gap), Phase A4 Go Sidecar work (PR #1144 — secret-scan posture), MAL V1 trace composition (PR #1134).

---

## Notes — canonical-key query gate (per `_orchestrator.md` audit-dispatch checklist 2026-05-24)

**Queried `ceo:cache_framework_canonical`** (updated 2026-05-25 21:59:49Z). Verbatim payload:

```
layer_1_anthropic_prompt_cache: {content: structurally stable per-domain content, multiplier: 0.10x input cost}
layer_2_uncached:               {content: per-call dynamic content,           multiplier: 1.0x}
valkey_semantic_cache:          layered on top for repetitive query hits
history_beyond_active_window:   stored in Hindsight for queryable recall, NOT held in active context
per_tier_multipliers_proposal:  sandbox 0.5x | solo 1.0x | pro 1.5x | team 2.0x | enterprise custom
tier_multipliers_status:        PROPOSAL — pressure-test in Phase 2
implementation_status:          Cat 4 cost.cache_discipline RATIFIED-CEO placement; Cat 20 Layer 11 deep-dive produces implementation spec
```

**Queried `ceo:keiracom_architecture_v2_locked` + V2 inventory** (`/home/elliotbot/clawd/Agency_OS/docs/architecture/keiracom_architecture_v2_inventory.md`). Verbatim relevant rows:

- **`infra.observability`** (line 207): "Observability + monitoring layer — Better Stack (already in fleet env vars) + per-layer /health checks. V1 scoped. Owner: Aiden (review/governance) + engineer-tier TBD (implementation). Depends on: temp.middleware (audit events flow here per inline_at_chokepoint item 5) + nats.fleet_inter_agent (NATS health observed) + mem.engine (Hindsight health observed)." **LOOSE V1-required.**
- **`cost.metering_pipeline`** (line 73): "Log-based per-tenant LLM metering pipeline (V1 captures token-counts only; cost $AUD translation deferred to P3)." **RATIFIED-CEO.** PR #1137.
- **`cost.dashboard`** (line 80): "Cost dashboard (admin-dashboard panel, not standalone) per-tenant + per-callsign + per-agent-role." **LOOSE.** PR #1139 scoping.
- **`cost.governance_attribution`** (line 78): "Governance-decision cost-attribution (PR-review + canonical-key query + audit-dispatch)." **LOOSE.**
- **`mem.wrap.trace`** (line 55): "Trace composition: OTel + tenant log + Reflect citations → audit-trail shape (HIPAA/legal/accounting)." **RATIFIED-CEO.** PR #1134.
- **`temp.inline.audit`** (line 97): "Audit trail emission — INLINE." **RATIFIED-CEO.**
- **`infra.backup_dr`** (line 211): "MOVED FROM V1 HARD GATE TO V1.x FEATURE." V1 ships Supabase PITR Pro tier (7-day point-in-time recovery; ~$39 AUD/mo) + multi-region cloud failover. **LOOSE V1.x.**
- **`infra.cicd`** (line ~210): "rollbacks UNKNOWN — Phase 2 sub-item." Audited by me 2026-05-23 (PR #1125): rollback runbook **missing**, only DB-restore runbooks (Postgres KEI-126, Weaviate KEI-60) exist; code-deploy rollback path = manual `git revert` + ~5-7min wait, OR two-dashboard split-brain manual clicks.
- **`cust.dashboard_spec`** (line 180): "Dashboard spec — docs/specs/AGENT_DASHBOARD_SPEC.md exists but **stale** (Agency OS calibration; refers to Maya/Researcher/Builder/Auditor not current fleet)." **LOOSE.**

---

## §1 — Designed (architecture spec exists?)

**Yes — at the layer-row level, no — at the implementation-spec level.**

The V2 inventory names this layer (`infra.observability` LOOSE V1-required) and its three direct dependencies (`temp.middleware` audit-event source, `nats.fleet_inter_agent` health observed, `mem.engine` Hindsight health observed). Vendor decision is locked: **Better Stack** for uptime monitors + heartbeats + alert routing.

What is **not** spec'd yet:
- Concrete metrics catalogue (what gets emitted, at what cadence, with what cardinality).
- Dashboard layout (no current canonical doc; `AGENT_DASHBOARD_SPEC.md` is stale per `cust.dashboard_spec`).
- Alert SLO thresholds (no per-metric "page Dave if X > Y for Z minutes" matrix).
- Retention policy for emitted metrics (cost vs forensic-window trade-off).
- Cross-tenant aggregation pattern for governance audit-trail roll-up (NATS `cross_tenant_aggregation` LOOSE per line 110).

**Honest:** the layer has an *architectural placement* but no *implementation contract*. Engineer-tier owns producing that during the V1 build phase.

---

## §2 — Built (implementation done?)

**Partial. Better Stack scaffolding exists; alert routing IS wired; metrics dashboard does NOT exist; metering IS wired.**

Concrete shipped pieces:

| Component | State | Source |
|---|---|---|
| Better Stack API key + env vars | ✅ wired | fleet env vars per `infra.observability` row |
| Heartbeat bootstrap (5 named) | ✅ created | `scripts/orchestrator/betterstack_setup.py` |
| Uptime monitors | ✅ 3 created | `scripts/orchestrator/betterstack_uptime_monitors.py` |
| BS-webhook receiver creating Linear KEI per incident | ✅ shipped | `src/api/webhooks/betterstack.py` |
| Severity-routing P0→#ceo / P1→#execution / OTHER→#alerts | ✅ shipped | `src/api/webhooks/betterstack_severity_router.py` (KEI-20) |
| Runbook for operator-gated Slack OAuth + policy wiring | ✅ shipped | `docs/runbooks/betterstack-slack-routing.md` |
| FastAPI `/health` `/liveness` `/readiness` endpoints | ✅ shipped | `src/api/routes/health.py` |
| Public status page | ✅ shipped | `scripts/orchestrator/betterstack_status_page.py` (PR-D, merged) |
| Per-tenant LLM token metering (log-based) | ✅ shipped | PR #1137 (`cost.metering_pipeline`) |
| Trace composition (OTel + tenant log + Reflect) | ✅ shipped | PR #1134 (`mem.wrap.trace`) |

Concrete missing pieces:

| Component | State | Why |
|---|---|---|
| Cost dashboard panel | ❌ not built | `cost.dashboard` LOOSE; PR #1139 scoping only |
| Governance cost-attribution surface | ❌ not built | `cost.governance_attribution` LOOSE |
| Customer-tier dashboard | ❌ stale spec | `cust.dashboard_spec` LOOSE; AGENT_DASHBOARD_SPEC.md refers to retired Agency-OS fleet |
| Code-deploy rollback metric/alert | ❌ not built | cross-cite my CI/CD audit PR #1125 — rollback runbook missing entirely |
| Heartbeat-recovery routing to `#execution` | ⚠️ blocked | Better Stack API limitation: `expiration_policy_id` not exposed on heartbeats (runbook §"Heartbeat-recovery routing limitation") |
| Per-agent-role cost panel | ❌ not built | needed for `cost.dashboard` per-callsign + per-agent-role slice |
| Compliance audit-trail retention surface | ❌ not built | needed for `mem.wrap.trace` HIPAA/legal/accounting downstream |

---

## §3 — Measured (production data exists OR honestly stated no-data-yet)

**Empirical state, queried live via Better Stack MCP 2026-05-25:**

**Monitors:**
```
ID      | Name            | URL                                              | Status     | Last Checked
4400037 | agencyxos.ai    | https://agencyxos.ai                             | 🟢 Up      | 2026-05-25 21:58:38Z
4400118 | supabase-rest   | https://jatzvazlbusedwsnqxzr.supabase.co/rest/v1/| ⏸️ Paused  | 2026-05-15 12:57:27Z
4400119 | railway-prefect | https://prefect.keiracom.app/api/health          | ⏸️ Paused  | 2026-05-15 12:54:50Z
```

**Heartbeats:**
```
ID     | Name                 | Status  | Period | Grace | Created
459824 | elliot-polling-loop  | 🔴 Down  | 1m     | 1m    | 2026-05-12 12:32:14Z
459825 | cognee-phase1-ingest | 🔴 Down  | 10m    | 5m    | 2026-05-12 12:32:14Z
459826 | prefect-pipeline     | pending | 10m    | 5m    | 2026-05-12 12:32:14Z
459827 | central-listener     | pending | 5m     | 2m    | 2026-05-12 12:32:15Z
459828 | agency-os-discovery  | pending | 30m    | 10m   | 2026-05-12 12:32:15Z
```

**Honest read:**
- **3 monitors total:** 1 active (status-page check on `agencyxos.ai`), 2 paused for 10+ days. **No monitor is actually probing application code.**
- **5 heartbeats total:** 0 green, 2 down, 3 pending. The heartbeat infrastructure was bootstrapped 2026-05-12 but the caller-side `curl` integrations were never wired into the actual jobs. `cognee-phase1-ingest` is stale because Cognee was retired (`mem.cognee_retired` lock).
- **Net:** the observability scaffolding is shipped, but the **scaffolding is not yet observing**. This is the dominant V1-blocker risk in this layer.

**What we don't measure yet:**
- Per-tenant LLM token spend at-a-glance (data exists in `cost.metering_pipeline` log stream; no dashboard reads it).
- Per-callsign cost burn-rate.
- API request latency p50/p95/p99 per endpoint.
- NATS message throughput / dead-letter rate.
- Hindsight retrieval latency / index-write lag.
- Deploy success rate over time (CI/CD audit found 15/15 success on last 15 main runs, but no time-series surface).
- Rollback-to-good-deploy MTTR (no rollback path measured because no rollback runbook exists).

**Cross-cite — CI/CD audit (PR #1125):** the deploy-failure `notify-failure` job in `ci.yml:325-335` is a no-op `echo` placeholder. CI failures emit ZERO observability signal. This is a Layer 12 + Layer infra.cicd joint gap.

---

## §4 — Token budget / cost behaviour at this layer

**Observability layer emits ~zero LLM tokens.** Better Stack probes, heartbeats, FastAPI health endpoints, Slack webhook posts — all mechanical HTTP. No LLM in the hot path.

**Observability layer OBSERVES the token budget for other layers** — that's the `cost.metering_pipeline` + `cost.dashboard` cluster:
- `cost.metering_pipeline` (PR #1137): captures token-counts from LLM request logs per tenant. V1 = token-counts only.
- `$AUD translation deferred to P3` (`cost.metering.provider_billing_api` line 76): per-model-per-tenant $AUD upgrade. **Decision rationale per Dave ratify on PR #1128 §5: ship token-counts first, attach $AUD post-first-paying-customer.**
- `cost.governance_attribution` LOOSE: governance-decision cost (PR-review + canonical-key query + audit-dispatch) — separate cost stream from customer-facing LLM spend.

**Better Stack pricing:** free tier covers 10 monitors + 5 heartbeats. We're at 3 monitors + 5 heartbeats — under free tier. Paid tier needed when fleet expands to >10 services with health endpoints. **No upgrade needed pre-V1.**

**Slack-relay (alert delivery) cost:** ~zero per post; rate-limited by Slack itself, not by us.

**Net layer-cost answer:** observability is a fixed-overhead layer at infrastructure cost (Better Stack subscription + small CPU footprint for FastAPI health routes + webhook handler), not a variable-cost layer that scales with tenant LLM spend.

---

## §5 — Cache strategy applicable

Per `ceo:cache_framework_canonical`, mapped to this layer's data flows:

| Sub-flow | Applicable layer | Reasoning |
|---|---|---|
| Better Stack synthetic probes | **No cache** | Probes are explicit "is the live thing alive?" — caching would defeat the purpose. |
| `/health` `/liveness` `/readiness` route returns | **Layer 2 (uncached, 1.0x)** | Per-call dynamic content (component status snapshot). Anthropic prompt cache N/A — no LLM. |
| LLM-metering log ingest (cost.metering_pipeline) | **No cache** | Write-heavy, append-only stream. Caching breaks accounting. |
| Dashboard reads — last-1h, last-24h, last-7d cost summaries | **Valkey semantic cache fit** | Repeat query hits on bounded time-windows; perfect Valkey target. Engineer-tier should TTL on the window boundary (don't cache "last 24h" longer than 1 min). |
| Audit-trail recall ("what did agent X do 90 days ago?") | **Hindsight beyond active window** | mem.wrap.trace already composes OTel + tenant log; long-tail recall belongs in Hindsight per the canonical key. |
| Layer 1 Anthropic prompt cache (0.10x) | **N/A for observability** | Observability doesn't call Anthropic. |

**Caveat — pressure-test signal:** the framework's tier multipliers (0.5x→2.0x) describe customer-facing cost behaviour, not infrastructure-fixed costs. Observability's cost shape is fixed-per-fleet, not per-tier. Pressure-test framing in §7.

---

## §6 — LOOSE items / open questions

1. **No heartbeat is currently green** (§3). Engineer-tier item 1: wire the heartbeat `curl` calls into the jobs the heartbeat names imply, then verify all 5 go green. Some heartbeats are also stale (cognee-phase1-ingest; Cognee retired per `mem.cognee_retired`) — these should be deleted, not "fixed".
2. **No application-code monitor** (§3). Only `agencyxos.ai` status-page is monitored; `railway-prefect` + `supabase-rest` paused for 10+ days. Engineer-tier: identify the actual application endpoints that *should* be monitored at V1 launch.
3. **Heartbeat-recovery routing limitation** (`docs/runbooks/betterstack-slack-routing.md` §"Heartbeat-recovery routing limitation"): Better Stack API doesn't expose `expiration_policy_id` on heartbeats, so heartbeat recoveries land in `#ceo` not `#execution`. Track BS API release notes; engineer-tier patches when BS exposes the field.
4. **Cost dashboard surface not built** (`cost.dashboard` LOOSE). Per-tenant + per-callsign + per-agent-role breakdown is needed for `crit4.cost_aware` V1-launch placement.
5. **Customer dashboard spec stale** (`cust.dashboard_spec` LOOSE). `docs/specs/AGENT_DASHBOARD_SPEC.md` refers to retired Agency-OS fleet — needs refresh for Keiracom V2 architecture (Keira persona + 5-tab nav per `ux.nav.*` rows).
6. **Code-deploy rollback observability gap** — cross-cite my CI/CD audit (PR #1125). No rollback runbook + no rollback metric. Layer 12 needs a "deploy success rate over rolling 24h" panel + a fire-when-failed-twice alert.
7. **Compliance audit-trail retention not surfaced.** `mem.wrap.trace` PR #1134 composes the trace; nothing currently surfaces "retention compliance OK / breach" for HIPAA/legal/accounting downstream verticals.
8. **Backup-DR posture not observed.** Per `infra.backup_dr`, V1 ships Supabase PITR (7-day window) + multi-region failover. Layer 12 needs: PITR window-age metric, failover-region-health metric, last-successful-restore-drill timestamp. Without this, "what happens if your servers die?" has no observability signal.
9. **No SLO matrix defined.** Per-metric thresholds for "alert" vs "page" vs "log only" — needs Aiden + Elliot decision pass.
10. **`notify-failure` no-op echo in `ci.yml`** (CI/CD audit finding). CI failures emit zero signal. Wire to NATS `keiracom.elliot.inbox` (consistent with existing pattern) or to Better Stack heartbeat failure semantic.

---

## §7 — Per-tier behaviour variation (proposal pressure-test)

The cache-framework canonical proposes tier multipliers (Sandbox 0.5x / Solo 1.0x / Pro 1.5x / Team 2.0x / Enterprise custom) — **status: PROPOSAL, pressure-test in Phase 2.** Applied honestly to this layer:

**Backend observability (what gets monitored)** — should be **uniform across all tiers**. Same monitor cadence, same heartbeats, same severity routing. A Solo tenant's failure mode is no less critical to Keiracom's reliability than an Enterprise tenant's. The tier multiplier does NOT cleanly apply here. **Pressure-test verdict: REJECT tier-variation for backend observability.**

**Customer-facing dashboard surface (what the tenant SEES of their own metrics)** — tier-multiplier framing IS load-bearing here:

| Tier | Dashboard surface | Rationale |
|---|---|---|
| Sandbox (0.5x) | Lightweight — last-7d token count + most-recent-error link. No real-time alerts to the customer. Read-only. | Trial / evaluation only; minimal surface keeps onboarding fast. |
| Solo (1.0x) | Standard — 24h + 7d cost panels, agent-run history, BYOK usage; admin self-can-paginate. Daily digest email. | Baseline V1-launch customer surface. |
| Pro (1.5x) | Enriched — adds per-project breakdown, real-time critical alerts to customer Slack/email, exportable CSV. | Justifies the price gap vs Solo. |
| Team (2.0x) | + per-user attribution, per-chat-slot attribution (`tier.team` 2 chats), team admin SSO logs | Multi-user surface only meaningful from Team tier up. |
| Enterprise (custom) | + custom SLA dashboards, white-glove ops, audit-trail export to customer's own SIEM | Custom contract surface. |

**Pressure-test verdict on customer-surface multipliers: HOLDS as a UX-feature-budget framing**, not as a cost-of-observation framing. The cost-multiplier framing applies cleanly to *what the customer is paying for visibility of their own work* — not to *what observability costs us to deliver*.

**Open question for deliberation:** is "observability surface tier" actually a useful product axis, or is it a free differentiator that costs us little to ship and avoids tier-gating ill-will? **Recommend Elliot impl-feasibility + Aiden architecture lens before committing tier-gated dashboards.**

---

## §8 — Per-agent-type variation where applicable

**Internal fleet observability** (the bots talking to each other) — per-agent variation is meaningful because the agent roles have different call shapes:

| Agent role | Call shape | Observability axis that matters |
|---|---|---|
| Worker callsigns (Atlas / Orion / Nova) | High-volume LLM calls, PR-creation bursts | Rate metrics + per-PR cost; aggregated dashboards |
| Deliberator callsigns (Aiden / Max / Elliot) | Low-volume, high-value decisions | Per-decision audit trail; cost-per-deliberation; **never aggregate away the individual decision** |
| Research callsign (scout — me) | Intermittent research bursts (multi-hour spikes) | Cost-spike alerts; long-running session detection |
| Customer-facing Keira (`persona.chat_agent_identity`) | Real-time chat; UX-sensitive | Latency p95/p99 per turn; response-quality proxy metric (no current spec); customer-visible failures |
| Ephemeral agents (`crit1.ephemeral`) | Spawn-die cycles tied to chat turns | Spawn time, init-to-first-token, container-leak guard |

**Implication for cost dashboard panel:** `cost.dashboard` LOOSE line 80 already names "per-tenant + per-callsign + per-agent-role" — so the inventory anticipates this. Engineer-tier honours all three axes when implementing.

**Implication for alert routing:** P0/P1 severity already handles severity-by-incident. We should ALSO route by *agent role* in a future iteration — a worker-callsign rate-limit incident is operationally different from a deliberator-callsign stall, and the on-call response differs. **Future iteration; not V1.**

---

## Cross-cutting concerns (where Layer 12 touches them)

1. **Multi-tenancy enforcement (mechanical at API not UI).** Observability MUST enforce `tenant_id` filter at API not UI. Admin dashboards see cross-tenant; customer dashboards NEVER see another tenant's data. Engineer-tier item: every metric API endpoint takes `tenant_id` as a path/query param + RLS-enforces it server-side. Cross-cite `tenant.single_supabase` line 141.
2. **Security (BYOK custody + secret-mgmt + per-customer segregation).** Observability NEVER logs raw API keys or BYOK material. Cross-cite my Phase A4 Go Sidecar `ScanResponse` posture (PR #1144) — same secret-pattern catalogue should apply to observability log emission. Engineer-tier item: wire same pattern catalogue server-side as a log-redaction filter.
3. **CI/CD + rollback.** Cross-cite my CI/CD gap audit (PR #1125). Rollback runbook is **missing entirely**; observability has no "is the current main green or red?" surface; `notify-failure` is a no-op echo. Layer 12 item: a single panel showing "current main commit + age + deploy status + last successful rollback drill date". Until that ships, V1 has a real risk that nobody notices a bad deploy until customer reports.
4. **Backup-DR (V1.x feature per `infra.backup_dr`).** V1 ships Supabase PITR Pro + multi-region. Observability needs: PITR window-age metric (alert if window-end < 1h-from-now), failover-region last-health timestamp, last-successful-restore-drill timestamp. Without these, "we have backups" is unverifiable claim.
5. **Customer file system (`ux.surface.files`).** Engineer-tier item: per-tenant storage-usage metric on the customer dashboard (storage is tier-gated per `ux.files.tier_storage_differentiator`). System-files isolation enforced by Go Sidecar per Phase A4; observability surfaces ATTEMPTED denials (audit log of `validator: system path access denied` 403s) to detect probe-style intrusion attempts.
6. **Reasoning trace + audit trail (`mem.wrap.trace` PR #1134).** Observability is the surface where audit-event throughput + retention compliance become visible. Engineer-tier item: throughput counter (audit events emitted per minute, per tenant), retention-compliance check (oldest event < retention window).
7. **Compliance gates (HIPAA / legal / accounting downstream).** Per `mem.wrap.trace`, the trace composition exists; the COMPLIANCE-GATE surface does not. Engineer-tier item: a per-vertical compliance dashboard (HIPAA: PHI-access log + retention; legal: chain-of-custody; accounting: append-only + cryptographic seal) — likely V1.x not V1 (most regulated verticals self-select to V1.x per `infra.backup_dr` framing).

---

## Sources (verbatim probe trail)

- `mcp__supabase__execute_sql` against `public.ceo_memory` — `ceo:cache_framework_canonical` + `ceo:keiracom_architecture_v2_locked` (updated 2026-05-25 21:59:49Z / 13:17:35Z respectively)
- `/home/elliotbot/clawd/Agency_OS/docs/architecture/keiracom_architecture_v2_inventory.md` — Cat 4, Cat 5, Cat 6, Cat 9, Cat 16 rows verbatim quoted above
- `mcp__betterstack__uptime_list_monitors_tool` (live state 2026-05-25)
- `mcp__betterstack__uptime_list_heartbeats_tool` (live state 2026-05-25)
- `docs/runbooks/betterstack-slack-routing.md` (KEI-20 severity routing runbook)
- `src/api/webhooks/betterstack.py` + `src/api/webhooks/betterstack_severity_router.py` (BS webhook + severity classifier)
- `src/api/routes/health.py` (FastAPI liveness/readiness)
- `scripts/orchestrator/betterstack_setup.py` + `betterstack_uptime_monitors.py` + `betterstack_routing_policy.py` + `betterstack_status_page.py`
- PR #1137 (`cost.metering_pipeline`)
- PR #1134 (`mem.wrap.trace`)
- PR #1125 (my CI/CD gap audit — rollback runbook gap)
- PR #1144 (my Phase A4 Go Sidecar — secret-scan posture for log-redaction parity)
