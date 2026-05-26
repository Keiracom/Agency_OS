# Stale Producer Audit — User-scope systemd timers + services

**Agent:** scout (Agency_OS-vs1m)
**Dispatched by:** elliot 2026-05-26
**Trigger:** Phase A6 dual-publish observation gap — Nova's empirical verifier (PR #1162) caught `fleet-supervisor.service` inactive 5 days while advertised as the publishing producer. Suggests other "we think it's running" producer-side gaps exist.
**Mandate:** Read-only audit. NO fixes. Sweep ALL user-scope systemd timers + services; cross-reference against canonical sources for "running" claims; produce table + verdict.
**Probe window:** 2026-05-26 04:50-04:55 UTC.
**Host:** Elliot fleet host (CALLSIGN=scout worktree).

---

## TL;DR — five categories of finding

| Category | Count | Action signal |
|---|---:|---|
| ✅ **Healthy** — Active + matches advertised cadence | 24 long-running services + 22 timer-driven services firing on cadence | none |
| ⚠️ **FAILED** — systemd reports failed-state, ExecMainStatus=1 | **3 services** | engineer-tier triage REQUIRED |
| ⚠️ **STALE BY POLICY** — service Active but the underlying system is marked retired in inventory | **3 services** (cognee + cognee-auto-ingest + openclaw) | retire-or-justify decision needed |
| ⚠️ **PARTIAL FLEET COVERAGE** — set-of-N units where one is INACTIVE while peers are Active | **1 cluster** (agent-self-claim-loop@elliot inactive; other 6 callsigns active) | confirm intentional vs drift |
| ℹ️ **RECOVERED** — was stale at recent witness, now firing | **1 service** (fleet-supervisor — Nova's anchor finding, restored since the PR body was written) | track but no action |

**Net read-out for the dispatch question ("are other 'we think it's running' producers actually inactive?"):** the fleet-supervisor gap Nova surfaced has been closed in the last ~24h. Three NEW gaps surface here: (1) three FAILED services, (2) three SHOULD-BE-RETIRED services still running (cognee×2 + openclaw), (3) elliot self-claim loop INACTIVE while 6/7 peers active.

---

## §1 — Timer cadence + last-fire table (28 timers)

Verbatim from `systemctl --user list-timers --all --no-pager` at 2026-05-26 04:53 UTC. Drift verdict per the dispatch criteria (a) Active state, (b) cadence-matches-advertised, (c) last successful fire within expected window.

| Timer | Last fire | Cadence (inferred from NEXT-LAST) | Drift verdict |
|---|---|---|---|
| evo-callback-poller.timer | 2026-05-26 04:52:47 UTC (37s ago) | ~1 min | ✅ on cadence |
| elliot-supervisor-wake.timer | 2026-05-26 04:49:21 UTC (4m ago) | ~5 min | ✅ on cadence |
| agency-os-auto-pull-main.timer | 2026-05-26 04:49:46 UTC (3m ago) | ~5 min | ✅ on cadence |
| agency-os-hook-failure-monitor.timer | 2026-05-26 04:50:00 UTC (3m ago) | ~5 min | ✅ on cadence |
| agency-os-service-health-monitor.timer | 2026-05-26 04:50:00 UTC (3m ago) | ~5 min | ✅ on cadence |
| fleet-supervisor.timer | 2026-05-26 04:50:51 UTC (2m ago) | ~5 min | ✅ on cadence (**recovered** — see §4) |
| linear-oneway-push.timer | 2026-05-26 04:43:33 UTC (9m ago) | ~15 min | ✅ on cadence |
| agency-os-alert-budget-threshold.timer | 2026-05-26 04:00:00 UTC (53m ago) | ~1 hour | ✅ on cadence |
| agency-os-alert-vendor-budget.timer | 2026-05-26 04:00:00 UTC (53m ago) | ~1 hour | ✅ on cadence |
| agency-os-skill-pr-staleness-monitor.timer | 2026-05-26 04:45:04 UTC (8m ago) | ~15 min | ✅ on cadence |
| bd_linear_sync.timer | 2026-05-26 04:50:11 UTC (3m ago) | ~10 min | ✅ on cadence |
| drive-strategic-indexer.timer | 2026-05-26 04:45:20 UTC (8m ago) | ~15 min | ✅ on cadence |
| migration-apply-watcher.timer | 2026-05-26 04:51:20 UTC (2m ago) | ~10 min | ✅ on cadence |
| agency-os-alert-pipeline-failure.timer | 2026-05-26 04:49:08 UTC (4m ago) | ~15 min | ✅ on cadence |
| keiracom-agent-status.timer | 2026-05-26 04:49:08 UTC (4m ago) | ~15 min | ✅ on cadence |
| keiracom-classify-replies.timer | 2026-05-26 04:49:08 UTC (4m ago) | ~15 min | ✅ on cadence |
| keiracom-poll-replies.timer | 2026-05-26 04:49:08 UTC (4m ago) | ~15 min | ✅ on cadence |
| reconcile_three_stores.timer | 2026-05-26 04:43:20 UTC (10m ago) | ~30 min | ✅ on cadence |
| agency-os-artifact-freshness-monitor.timer | 2026-05-25 09:00:06 UTC (19h ago) | daily | ✅ on cadence |
| agency-os-alert-lead-quality.timer | 2026-05-26 04:37:16 UTC (16m ago) | ~6 hours | ✅ on cadence |
| **openai-cost-daily.timer** | 2026-05-25 13:55:08 UTC (14h ago) | daily | ✅ timer on cadence; **service FAILED — see §2** |
| launchpadlib-cache-clean.timer | 2026-05-25 22:30:08 UTC (6h ago) | daily | ✅ on cadence (system maintenance) |
| keiracom-cost-collector.timer | 2026-05-26 03:00:08 UTC (1h 53m ago) | daily | ✅ on cadence |
| weaviate-backup.timer | 2026-05-26 03:30:08 UTC (1h 23m ago) | daily | ✅ on cadence |
| **openai-cost-weekly.timer** | 2026-05-22 08:00:08 UTC (3 days ago) | weekly | ✅ timer on cadence; **service FAILED — see §2** |
| external-knowledge-ingester.timer | 2026-05-23 17:00:20 UTC (2 days ago) | weekly | ✅ on cadence (last KEI-232 weekly fire) |
| agency-os-llm-wiki-refresh.timer | 2026-05-24 03:00:08 UTC (2 days ago) | weekly | ✅ on cadence |
| **memory-core-fact-probe.timer** | 2026-05-24 00:58:00 UTC (2 days ago) | **NEXT="-"** — no next fire scheduled | ❌ **STALE** — service FAILED + no rearm |

**Read-out:** 27 of 28 timers are firing on cadence. The one outlier is `memory-core-fact-probe.timer` (Agency_OS-zbvs) — `NEXT="-"` means systemd has no future fire planned. Combined with the FAILED service state (§2), this timer is effectively dead.

---

## §2 — FAILED services (three RED ALARMS)

`systemctl --user list-units --type=service --all` shows three units in failed state (verbatim ● marker in the output):

| Service | systemd Result | ExecMainStatus | InactiveEnterTimestamp | Anchor |
|---|---|---:|---|---|
| `memory-core-fact-probe.service` | `exit-code` | `1` | 2026-05-24 00:58:01 UTC | Agency_OS-zbvs |
| `openai-cost-daily.service` | `exit-code` | `1` | 2026-05-25 13:55:08 UTC | OpenAI daily cost rollup |
| `openai-cost-weekly.service` | `exit-code` | `1` | (similar pattern — weekly cadence) | OpenAI weekly cost rollup |

**Engineer-tier action:** `journalctl --user -u <service> -p err -n 50` for each to surface the underlying error. All three are oneshots fired by their respective timers; the systemd timer keeps firing the (broken) service on schedule.

**Implication for the dispatch question:** these are NOT silent-stale — they are loudly-failed. systemd reports `● failed`. But because we lack the active-alert wiring (cross-cite my Layer 12 deep-dive PR #1148 — Better Stack is shipped but most heartbeats are not green; `notify-failure` is a no-op echo per my CI/CD audit PR #1125), nobody was paged. **Same blind-spot family as Nova's fleet-supervisor catch.**

---

## §3 — STALE-BY-POLICY services (running despite inventory retirement)

Two systems are marked for retirement in canonical sources but are still running:

### 3.1 Cognee — `mem.cognee_retired` lock

V2 inventory lists `mem.cognee_retired` in the `v2_locks_not_for_redeliberation` array (canonical query of `ceo:keiracom_architecture_v2_locked`). Recent PRs anchor the retirement direction:
- PR #1143 — Orion: Cognee data-quality report recommending COLD-START
- PR #1142 — Atlas: LlamaIndex pin + consumers inventory (pre-Hindsight-cutover)
- PR #1115 — Aiden: retire Agency OS arch + publish Keiracom V1.0 architecture root with MAL V1

Yet on the host:
```
cognee.service            loaded  active  running  Agency OS — Cognee API server (knowledge graph + memory layer)
cognee-auto-ingest.service loaded  active  running  Agency OS — Cognee auto-ingest watcher (re-ingests governance files on change)
```

Both Active, both running. The retirement is ratified in canonical state; the runtime hasn't been quiesced. **Possible explanations (engineer-tier resolves):**
- Bridging window during memory migration to Hindsight — Cognee kept warm for fall-back recall.
- Quiesce step deferred behind upstream Hindsight PR (M2 per Orion il34 spike).
- Just-not-shut-off drift.

**Cost signal:** Cognee + auto-ingest running = continuous CPU + RAM + disk-IO with zero forward-investment value if the retirement is intentional. **Engineer-tier item:** confirm retirement-or-bridge intent + decide quiesce timing.

### 3.2 OpenClaw — disqualified from production deployment

My memory anchor (`reference_model_routing.md` + strategic_shift memory): "OpenClaw has fundamental and unpatchable security vulnerabilities (137 advisories, CVSS 9.9 criticals, 341+ malicious skills), making its runtime deployment disqualifying."

Yet on the host:
```
openclaw.service          loaded  active  running  OpenClaw Gateway
```

This is the **second-most concerning finding** in this audit. The strategic decision rejected OpenClaw for runtime deployment; the runtime is, in fact, deployed.

**Possible explanations (engineer-tier resolves):**
- Reading the systemd unit description — "OpenClaw Gateway" — may be a *vendored* OpenClaw component (e.g. the gateway shim only, not the full runtime), in which case the security disqualification may not apply at this scope.
- Or the unit is genuinely running the disqualified surface and needs to be stopped per the strategic decision.

**Engineer-tier action:** read the unit file (`systemctl --user cat openclaw.service`) and confirm what's actually running. If the vulnerable surface is exposed, stop the unit. If it's a benign shim, document the scope to defuse the false-positive in this audit.

---

## §4 — fleet-supervisor: Nova's anchor finding has RECOVERED

Anchor: Nova's PR #1162 body verbatim:
> "fleet-supervisor.service is inactive since 2026-05-20 23:11:54 UTC."

Live probe 2026-05-26 04:51 UTC:
```
systemctl --user show fleet-supervisor.service -p Result -p InactiveEnterTimestamp
  Result=success
  InactiveEnterTimestamp=Tue 2026-05-26 04:51:13 UTC

systemctl --user list-timers fleet-supervisor.timer
  Tue 2026-05-26 04:55:52 UTC ← NEXT
  Tue 2026-05-26 04:50:51 UTC ← LAST (2 minutes before this probe)
```

**Read-out:** fleet-supervisor.timer is firing every ~5 minutes; service oneshot completes cleanly (`Result=success`) and goes Inactive between fires — that's normal for a timer-driven oneshot. Whoever restarted the timer (likely as part of Phase A6 work) restored the producer.

Nova's catch was honest at PR-write time. The empirical verifier (`scripts/a6_observation_check.sh` from PR #1162) will now produce signal once the Phase A6 7-day window accumulates publishes. **No engineer-tier action needed here.** The verifier and the producer are both now alive.

---

## §5 — Partial fleet coverage — `agent-self-claim-loop@<callsign>.service`

Six of seven callsigns have an Active self-claim loop:

```
agent-self-claim-loop@aiden.service   active   running
agent-self-claim-loop@atlas.service   active   running
agent-self-claim-loop@elliot.service  inactive dead       ← INACTIVE
agent-self-claim-loop@max.service     active   running
agent-self-claim-loop@nova.service    active   running
agent-self-claim-loop@orion.service   active   running
agent-self-claim-loop@scout.service   active   running
```

Anchor: KEI-92 / Linear KEI-130 ("self-claim loop").

**Two possibilities, both legitimate but only one is the right one:**

- **(A) Intentional:** Elliot is the orchestrator who dispatches; he doesn't auto-claim from the queue (orchestrator role per IDENTITY.md + `_orchestrator.md`). Self-claim loop disabled by design.
- **(B) Drift:** The unit was stopped during some past maintenance and not restored.

Per `feedback_check_open_prs_before_bd_claim` + `feedback_no_ask_on_claims`, I'd expect Elliot the orchestrator NOT to self-claim, which aligns with (A). But the audit's job is to surface, not adjudicate.

**Engineer-tier action:** confirm (A) is the intended posture and document why elliot is intentionally excluded; OR restart the loop if (B).

---

## §6 — Cross-reference against ceo_memory "running" claims

Queried `ceo:*` keys matching `running` or `active`. Surfaced rows that anchor a production-running service:

| ceo_memory key (latest update) | Claims as running | Live state | Verdict |
|---|---|---|---|
| `ceo:deep_dive:layer_11_cost_optimization` (2026-05-25) | "Valkey running per Cat 4" | Not in user-scope systemd (likely Docker / Vultr-hosted) | Out of audit scope — host-level not user-scope |
| `ceo:deep_dive:layer_10_infrastructure` (2026-05-25) | "Vultr fleet host + Vault running" | Vault not in user-scope systemd (host-level Vultr) | Out of audit scope |
| `ceo:deep_dive:layer_12_observability` (2026-05-25, my own dive) | observability scaffolding shipped | See PR #1148 verdict — scaffolding shipped, not yet observing | Cross-cite |

V2 inventory rows tagged `running` (line numbers from canonical inventory):

| Inventory row | Phase column | Live evidence | Verdict |
|---|---|---|---|
| `nats.fleet_inter_agent` (line 107) | `running` | `nats-server.service` ACTIVE ✓ | ✅ confirmed |
| `comms.slack_relay` (line 111) | `running` | `agency-os-elliot-slack-listener.service` ACTIVE ✓ | ✅ confirmed |
| `mcp.tei_sidecar` (line 150) | `running` | Not in user-scope systemd (Docker compose per `infra/keiracom_system/embeddings/docker-compose.tei.yml`) | Out of audit scope — host-level |
| `gov.litellm_router` (line 160) | `running` | `litellm.service` ACTIVE ✓ | ✅ confirmed |
| `gov.internal_gemini` (line 161) | `running` | Not a service (model-routing config) | N/A |
| `cost.semantic_cache_valkey` (line 81) | `running` (Valkey running today) | Not in user-scope systemd | Out of audit scope |
| `op.orchestrator_merge` (line 662) | `running` | Not a service (governance pattern) | N/A |
| `op.discovery_log` (line 663) | `running` | Not a service (bd integration) | N/A |
| `op.audit_dispatch_checklist` (line 664) | `running` | Not a service (governance protocol) | N/A |
| `op.codeql_migration` (line 665) | `running` | GitHub Actions workflow — not user-scope systemd | Cross-cite (PR #1138) |

**Read-out:** all 4 user-scope-systemd-visible "running" claims from canonical sources confirmed Active. Non-systemd "running" claims (Valkey, Vault, TEI sidecar) are out of audit scope — those run on different hosts / Docker layers and would need a separate audit pass (engineer-tier follow-up #2 in §8).

---

## §7 — Healthy long-running services (24 confirmed)

For completeness — services that are Active + running + not flagged as concerns. No engineer-tier action needed; recorded so this audit is exhaustive rather than focused-only-on-bad-news:

```
agency-os-elliot-slack-listener  ← comms.slack_relay
agency-os-opa                    ← OPA policy server (no inventory anchor probed)
agency-os-phoenix-export         ← Phoenix audit-event export
agent-memories-indexer           ← Agency_OS-lsyd (Weaviate AgentMemories)
agent-self-claim-loop@{aiden,atlas,max,nova,orion,scout}  (6/7 — see §5 for elliot)
aiden-agent / atlas-agent / elliot-agent / max-agent / nova-agent / orion-agent  ← KEI-94 keep-alive
{aiden,atlas,elliot,max,nova,orion}-inbox-watcher
{aiden,max}-nats-review-bridge
{atlas,nova,orion}-nats-dispatch-bridge
elliot-nats-inbox-bridge
atlas-clone                      ← ATLAS Build Clone (Elliot Tier A executor)
ceo-memory-indexer               ← KEI-85 phase A
completion-sync-worker           ← KEI-74
deliberator-concur-router        ← round-2 concur auto-dispatch
dispatcher.service               ← KEI-213
elliot-memories-indexer          ← KEI-109
git-commits-indexer              ← KEI-85 phase C
indexing-queue-worker            ← KEI-61
keiracom-temporal-worker         ← Phase A6 first-workflow dual-publish ✓ (consumer side healthy per Nova PR #1162 body)
linear-state-indexer             ← KEI-85 phase B
litellm.service                  ← gov.litellm_router
nats-server.service              ← nats.fleet_inter_agent
peer-event-ceo-relay             ← Peer NATS events → Slack #ceo bridge
```

---

## §8 — Engineer-tier handoff items

In order of payoff:

1. **Triage 3 FAILED services** (§2). Run `journalctl --user -u <service> -p err -n 100` for each; fix or retire. memory-core-fact-probe + openai-cost-{daily,weekly}. ~30 min total.
2. **Decide Cognee + OpenClaw retirement status** (§3). Engineer-tier + Aiden architectural lens: are these intentional bridges or drift? If drift, file quiesce KEIs. ~15 min decision + ~30 min execution if quiesce.
3. **Confirm `agent-self-claim-loop@elliot` posture** (§5). Document intentional-exclusion in the orchestrator module OR restart the unit. ~10 min.
4. **Run the host-level audit** for the services I couldn't see from user-scope: Valkey, Vault, TEI sidecar (Docker), Postgres (Supabase-hosted), Hindsight, OPA-Gatekeeper (Railway). This audit covered user-scope systemd ONLY. ~1-2 hour separate pass.
5. **Close the alert-wiring gap surfaced by §2** — failed user-scope services emit ZERO active alert today. Cross-cite my Layer 12 deep-dive PR #1148 (Better Stack heartbeats not green) + my CI/CD audit PR #1125 (`notify-failure` no-op echo). Same blind-spot family as Nova's catch. Engineer-tier: wire `OnFailure=` to a NATS-publish unit on every user-scope service. ~2-3 hours fleet-wide.
6. **Document `memory-core-fact-probe.timer NEXT="-"` resolution** — either fix the timer rearm or remove the unit. ~15 min.

---

## §9 — Risks + open questions

1. **This audit covers user-scope systemd ONLY.** Anything host-level (root systemd, Docker, Railway-managed) is invisible to this pass. Cross-cite my CI/CD audit Finding F1 (railway.toml stale — 9 services live but only 4 declared). A host-level audit is the natural next pass.
2. **"Advertised cadence" is inferred from `NEXT - LAST`** in the systemd timer output, not from a canonical cadence registry. There is no `ceo:timer_cadence_canonical` key. If a timer drifted to a wrong cadence months ago, this audit would NOT catch the drift — it would only catch units that are inactive or failing. **Open question:** should there be a canonical cadence registry?
3. **The `memory-core-fact-probe.timer NEXT="-"` case is suspicious** — systemd shows no next fire. Either the unit has `Persistent=true` + a `OnCalendar` that hasn't matched recently, or the unit was disabled. Engineer-tier confirms.
4. **fleet-supervisor recovery** between Nova's PR write-time and this audit's probe time is a positive signal but creates a docs-vs-reality drift: PR #1162 body claims 5-day inactive; current state shows ~5 min cadence. Engineer-tier should update the PR body or annotate the recovery in the merge commit.
5. **Cognee + OpenClaw running** despite canonical retirement claims is the highest-impact finding here. If unintentional, it's a quiet resource burn + (for OpenClaw) a security posture violation. Both need decisions.

---

## Sources (verbatim probe trail)

- `systemctl --user list-timers --all --no-pager` at 2026-05-26 04:53 UTC (28 timers)
- `systemctl --user list-units --type=service --all --no-pager` at 2026-05-26 04:54 UTC
- `systemctl --user show <unit> -p Result -p ExecMainStatus -p ActiveEnterTimestamp -p InactiveEnterTimestamp` per individual unit
- `ceo:keiracom_architecture_v2_locked` V2 inventory (lines 41, 81, 93-98, 107-111, 150, 160-161, 222-223, 662-665)
- `ceo:deep_dive:layer_11_cost_optimization` + `layer_10_infrastructure` + `layer_12_observability` (ceo_memory queries)
- Cross-cite: PR #1162 (Nova's a6_observation_check.sh — the catch that motivated this audit)
- Cross-cite: PR #1148 (my Layer 12 observability deep-dive — same blind-spot family as the FAILED services here)
- Cross-cite: PR #1125 (my CI/CD gap audit — `notify-failure` no-op + railway.toml stale)
- Memory anchor: `reference_model_routing.md` strategic_shift on OpenClaw runtime disqualification
