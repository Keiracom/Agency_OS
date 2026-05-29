# Stale Producer Audit — User-scope systemd timers + services (2026-05-29 refresh)

**Agent:** scout (Agency_OS-vs1m refresh)
**Dispatched by:** elliot 2026-05-29 (V1 dress-rehearsal pre-flight: confirm producer-side ground truth before chain runs)
**Predecessor:** `docs/audits/stale_producer_audit_2026-05-26.md` (#1163). This refresh re-probes the prior findings and the V1-chain services explicitly flagged in the dispatch.
**Mandate:** Read-only audit. NO fixes. Sweep ALL user-scope systemd timers + services; cross-reference V1-chain services against canonical sources; produce table + verdict per dispatch question.
**Probe window:** 2026-05-29 21:23-21:25 UTC.
**Host:** Elliot fleet host (CALLSIGN=scout worktree, branch `scout/audit-stale-producer-2026-05-29`).

---

## TL;DR — what changed since 2026-05-26

| Category | 2026-05-26 | 2026-05-29 | Change |
|---|---|---|---|
| Total user services loaded | (not measured) | **164** | — |
| Active + running services | (not measured) | **57** | — |
| FAILED services | **3** | **0** | ✅ all recovered |
| STALE-BY-POLICY services | **3** (cognee×2 + openclaw) | **1** (openclaw only) | ✅ cognee×2 decommissioned |
| Partial-fleet-coverage gaps | **1** (self-claim-loop@elliot inactive) | **0** | ✅ recovered |
| User timers loaded | **28** | **22** | **-6 net** (8 decommissioned, 2 added) |
| All timers firing on cadence | 27/28 | **22/22** | ✅ |

**Net read-out for V1 dress rehearsal:**
- ✅ Every V1-chain producer the dispatch asked about is **ACTIVE/running** (§4): `keiracom-work-loop-bridge`, `keiracom-work-loop-consumer`, `dispatcher`, `nats-server`, all 6 callsign NATS dispatch bridges, `peer-event-ceo-relay`, all 7 callsign inbox-watchers.
- ✅ Zero failed services (was 3).
- ✅ All 3 prior FAILED services now `Result=success` (one-shot timer-driven units, currently idle between fires — healthy posture).
- ✅ cognee + cognee-auto-ingest **decommissioned** (matches ARCHITECTURE.md retirement, commit `f50a240d2`).
- ⚠️ `openclaw.service` still active — UNCHANGED status from prior audit. Engineer-tier triage still required.
- ℹ️ `face` and `persona_bank` are **not systemd services by design** (Face = on-demand spawn entrypoint per `src/keiracom_system/chat/face.py`; persona_bank = Postgres table + dispatcher endpoint per PR #1314). The dispatch's flag list named them as concerns — the audit clarifies neither is a long-running unit.

---

## §1 — Timer cadence + last-fire table (22 timers)

Verbatim from `systemctl --user list-timers --all --no-pager` at 2026-05-29 21:23-21:25 UTC.

| Timer | Last fire | Cadence (inferred) | Drift verdict |
|---|---|---|---|
| evo-callback-poller.timer | 45s ago | ~1 min | ✅ on cadence |
| keiracom-classify-replies.timer | 12 min ago | ~5 min | ✅ on cadence |
| agency-os-auto-pull-main.timer | 2m45s ago | ~5 min | ✅ on cadence |
| agency-os-pane-enter-sweep.timer | 2m45s ago | ~5 min | ✅ on cadence (jne8 workaround timer — see §6) |
| drive-strategic-indexer.timer | 13 min ago | ~15 min | ✅ on cadence |
| linear-oneway-push.timer | 10 min ago | ~15 min | ✅ on cadence |
| bd_linear_sync.timer | 6 min ago | ~15 min | ✅ on cadence |
| migration-apply-watcher.timer | 3m45s ago | ~10 min | ✅ on cadence |
| agency-os-alert-pipeline-failure.timer | 2m45s ago | ~15 min | ✅ on cadence |
| keiracom-poll-replies.timer | 2m45s ago | ~15 min | ✅ on cadence |
| keiracom-agent-status.timer | 1m50s ago | ~15 min | ✅ on cadence |
| agency-os-alert-budget-threshold.timer | 25 min ago | ~1 hour | ✅ on cadence |
| agency-os-alert-vendor-budget.timer | 25 min ago | ~1 hour | ✅ on cadence |
| postgres-dump-r2.timer | 24 min ago | ~1 hour | ✅ on cadence (NEW since 2026-05-26 — see §6) |
| agency-os-alert-lead-quality.timer | 2h39m ago | ~6 hours | ✅ on cadence |
| keiracom-cost-collector.timer | 03:00:01 UTC | daily | ✅ on cadence |
| weaviate-backup.timer | 03:30:01 UTC | daily | ✅ on cadence (and PR #1316 false-fail fix landed on main) |
| launchpadlib-cache-clean.timer | 8h ago | daily | ✅ on cadence |
| openai-cost-daily.timer | 7h ago | daily | ✅ on cadence (**service RECOVERED — see §3**) |
| external-knowledge-ingester.timer | 8h ago | daily | ✅ on cadence |
| agency-os-llm-wiki-refresh.timer | 2026-05-24 03:00 UTC | weekly | ✅ on cadence (next Sun 03:00) |
| openai-cost-weekly.timer | 2026-05-29 08:00 UTC | weekly | ✅ on cadence (**service RECOVERED — see §3**) |

**Read-out:** **22/22 timers firing on cadence.** No timer with `NEXT="-"` and no rearm; no STALE timer in the set. The 2026-05-26 outlier (`memory-core-fact-probe.timer`, `NEXT="-"`) is now intentionally decommissioned at the repo (§6).

---

## §2 — FAILED services — NONE (was 3)

```
$ systemctl --user list-units --state=failed --no-pager
0 loaded units listed.
```

**Read-out:** zero failed user services across the entire 164-unit space. The prior audit's 3 FAILED services (`memory-core-fact-probe`, `openai-cost-daily`, `openai-cost-weekly`) have all recovered — see §3.

---

## §3 — Status of prior FAILED services (dispatch question 3)

All 3 prior FAILED services now report `Result=success`. Their `ActiveState=inactive / SubState=dead` is the healthy posture for a Type=oneshot timer-driven unit between fires:

| Unit (2026-05-26 verdict) | Now ActiveState | Now Result | Last successful fire | Verdict |
|---|---|---|---|---|
| `memory-core-fact-probe.service` (was FAILED + no rearm) | inactive | success | (decommissioned — see §6) | ✅ removed-by-design |
| `openai-cost-daily.service` (was FAILED) | inactive | success | 2026-05-29 13:55 UTC | ✅ recovered |
| `openai-cost-weekly.service` (was FAILED) | inactive | success | 2026-05-29 08:00 UTC | ✅ recovered |

---

## §4 — V1-chain services (dispatch questions 2 + 5)

Explicit probe of every V1-chain producer the dispatch flagged. **All present-by-design units are active.**

| Service | LoadState | ActiveState | SubState | Verdict |
|---|---|---|---|---|
| `keiracom-work-loop-bridge.service` (Postgres task_event → Valkey producer) | loaded | active | running | ✅ ACTIVE |
| `keiracom-work-loop-consumer.service` (tier-gated task→spawn driver) | loaded | active | running | ✅ ACTIVE |
| `dispatcher.service` (KEI-213 — interceptor proxy + watchdog + reaper) | loaded | active | running | ✅ ACTIVE |
| `nats-server.service` (JetStream — KEI-205 messaging layer) | loaded | active | running | ✅ ACTIVE |
| `peer-event-ceo-relay.service` (peer NATS → #ceo; PR #1328 unblocks pytest collection) | loaded | active | running | ✅ ACTIVE |
| `elliot-nats-inbox-bridge.service` (NATS `keiracom.elliot.inbox` → elliot tmux) | loaded | active | running | ✅ ACTIVE |
| `aiden-nats-review-bridge.service` (NATS review/deliberation → aiden tmux) | loaded | active | running | ✅ ACTIVE |
| `max-nats-review-bridge.service` (NATS review/deliberation → max tmux) | loaded | active | running | ✅ ACTIVE |
| `atlas-nats-dispatch-bridge.service` (NATS `keiracom.dispatch.atlas` → atlas tmux) | loaded | active | running | ✅ ACTIVE |
| `orion-nats-dispatch-bridge.service` (NATS `keiracom.dispatch.orion` → orion tmux) | loaded | active | running | ✅ ACTIVE |
| `nova-nats-dispatch-bridge.service` (NATS `keiracom.dispatch.nova` → nova tmux) | loaded | active | running | ✅ ACTIVE |
| `scout-nats-dispatch-bridge.service` (NATS `keiracom.dispatch.scout` → scout tmux) | loaded | active | running | ✅ ACTIVE |
| `{aiden,atlas,elliot,max,nova,orion,scout}-inbox-watcher.service` (7/7) | loaded | active | running | ✅ ACTIVE (post-#1309) |
| `face.service` / `face-agent.service` / `face-spawn.service` | **not-found** | inactive | dead | ℹ️ **by design** — Face is `src/keiracom_system/chat/face.py` (spawnable entrypoint per #1311), not a long-running unit |
| `persona_bank.service` / `persona-bank.service` | **not-found** | inactive | dead | ℹ️ **by design** — persona_bank is a Postgres table + dispatcher endpoint per PR #1314, not a unit |

**Read-out:** every V1-chain unit the dispatch named — and every unit it could be naming under a different shape — is in the correct state for cutover. `face` and `persona_bank` not appearing in systemd is not a gap; both are realised at a different layer than producer/consumer units. **No V1-chain producer is silently failed.**

---

## §5 — STALE-BY-POLICY services (dispatch question 4)

### 5.1 Cognee — RESOLVED ✅

Both Cognee units that were `active running` at 2026-05-26 (against the `mem.cognee_retired` lock in `ceo:keiracom_architecture_v2_locked`) are now `inactive / dead`. ARCHITECTURE.md was updated commit `f50a240d2` ("docs(architecture): retire Cognee") in the interim.

| Service | 2026-05-26 | 2026-05-29 | Verdict |
|---|---|---|---|
| `cognee.service` | active running | inactive dead | ✅ retired |
| `cognee-auto-ingest.service` | active running | inactive dead | ✅ retired |

### 5.2 openclaw — UNCHANGED (still flagged)

```
$ systemctl --user show openclaw.service -p Description,FragmentPath,ActiveState,Result
Description=OpenClaw Gateway
FragmentPath=/home/elliotbot/.config/systemd/user/openclaw.service
ActiveState=active
Result=success
```

**No change since 2026-05-26.** The prior audit's flag stands: engineer-tier should read `systemctl --user cat openclaw.service` and confirm scope. If the vulnerable surface is exposed, stop the unit. If it is a benign shim, document it to defuse the recurring false-positive.

---

## §6 — Timer delta vs 2026-05-26 (28 → 22)

### 8 timers REMOVED (all decommissioned at the repo — `git cat-file -e origin/main:<path>` returns absent for every one)

| Timer | Why it was here | Status |
|---|---|---|
| `agency-os-artifact-freshness-monitor.timer` | governance freshness probe | decommissioned (repo-deleted) |
| `agency-os-hook-failure-monitor.timer` | hook-failure alerting | decommissioned |
| `agency-os-service-health-monitor.timer` | service-health monitor | decommissioned |
| `agency-os-skill-pr-staleness-monitor.timer` | skill-PR staleness alert | decommissioned |
| `elliot-supervisor-wake.timer` | elliot session-wake | decommissioned |
| `fleet-supervisor.timer` | fleet supervisor (the Nova-flagged unit) | decommissioned |
| `memory-core-fact-probe.timer` | core-fact probe (was FAILED at 2026-05-26) | decommissioned |
| `reconcile_three_stores.timer` | LAW XV three-store reconcile | decommissioned |

All 8 repo unit files were git-removed before this probe window. Removals look **intentional** (the unit files are gone from `origin/main`, not just disabled). Engineer-tier verifies the surrounding functionality migrated to a successor (e.g. the 4 monitors may have been consolidated into a different probe path).

### 2 timers ADDED

| Timer | Cadence | Purpose |
|---|---|---|
| `agency-os-pane-enter-sweep.timer` | ~5 min | Periodic Enter sweep across worker tmux panes — workaround for inbox-watcher submission-reliability bug Agency_OS-jne8 (note: jne8 is now resolved by PR #1309, so this timer is now compensating-but-redundant; engineer-tier confirms whether to retire it). |
| `postgres-dump-r2.timer` | ~1 hour | Postgres dump → Vultr R2 (the cutover-aligned backup pipeline). |

---

## §7 — Partial fleet coverage — RESOLVED ✅

The 2026-05-26 finding `agent-self-claim-loop@elliot.service inactive while 6/7 callsigns active` is **resolved**:

```
$ systemctl --user show agent-self-claim-loop@elliot.service -p ActiveState,SubState,Result
ActiveState=active
SubState=running
Result=success
```

All 7 callsign self-claim loops are now active. No drift.

---

## §8 — Engineer-tier triage actions (next dispatches)

1. **openclaw.service** — UNCHANGED from 2026-05-26 flag. Confirm posture: vulnerable / benign shim. (5-10 min owner; not blocking V1.)
2. **`agency-os-pane-enter-sweep.timer`** — jne8 is closed by #1309; this compensating sweep is now likely redundant. Owner decides keep / retire. (5 min.)
3. **Confirm the 8 decommissions were intentional** — diff `config/systemd/user/` between the 2026-05-26 commit and current `origin/main`; the unit files are gone but downstream functionality (4 monitor probes + fleet-supervisor + three-store reconcile + elliot-wake + memory-core-fact-probe) should have moved to a successor path. This is a paper exercise, not a host change. (15 min.)

**Nothing in this audit blocks the V1 dress rehearsal on the producer side.** Every V1-chain unit the dispatch flagged is active; zero failed services; cognee retirement is done in the runtime. The single residual flag — openclaw — was already-flagged at 2026-05-26 and is not on the V1 chain.

---

**Probe commands (verbatim, for reproducibility):**

```bash
systemctl --user list-timers --all --no-pager
systemctl --user list-units --state=failed --no-pager
systemctl --user list-units --type=service --state=active --no-pager --plain --no-legend | wc -l
systemctl --user show <unit> -p ActiveState,SubState,Result,ExecMainStatus
git cat-file -e origin/main:config/systemd/user/<unit>.timer  # check repo presence
```
