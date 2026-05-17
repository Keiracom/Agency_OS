# Part 15 v2 — Governance Model A→B Amendment

**Status:** awaiting Dave ratification under G-09 (3-way CONCUR ✓ → CEO approve → commit-on-merge = effective).
**Source:** CEO Drive doc (Part 15 v2), three-way deliberation in `#execution` 2026-05-17.
**Authors:** elliot (deliberator), aiden (peer CTO), max (peer CTO).
**Scope:** captures the converged amendment shape only — does not re-host the full Drive body, which remains the source-of-truth narrative.

---

## Converged position across the seven axes

| Axis                          | Outcome   | Notes                                                                                                  |
| ----------------------------- | --------- | ------------------------------------------------------------------------------------------------------ |
| SURVIVES (5 rules)            | adopt     | Organisational + quality rules independent of architecture. No edits.                                  |
| REWRITES (9 rules)            | adopt+    | Adopt as drafted, plus G-01 "simple-bypass" threshold tightening (see Refinement #1).                  |
| DEPRECATED for workers (6)    | adopt+    | Adopt, conditional on Enforcer-regex fixture-replay empirical gate (see Refinement #2).                |
| NEW G-01 to G-10              | adopt all | G-01 (Spec Completeness Standard) has the strongest anchor — see §"G-01 anchor evidence".              |
| Phase transitions (G-06)      | adopt     | Explicit Dave approval per phase. Phase 2→3 (ephemeral deliberators) is the highest-stakes transition. |
| G-09 self-bootstrap           | adopt+    | This amendment is the first ratification under G-09. Dogfood the protocol (see Refinement #4).         |
| Pre-spawn CONCUR latency      | resolved  | Tabletop both offline-CTO and offline-orchestrator scenarios (see Refinement #3).                      |

---

## Four refinements baked into the converged shape

### Refinement #1 — G-01 simple-bypass requires six conditions, not five

Bypass of pre-spawn CONCUR for "simple" tasks requires **all six** of the following, not any subset:

1. Single-file change OR config-only change.
2. <50 LoC delta.
3. No schema migration.
4. No external service contract change (API / MCP / webhook surface).
5. Bypass auto-logged via `bd remember key=bypass-<KEI>` for audit.
6. **No shared-infrastructure SPOF.** Bug fixes to systems every callsign depends on still require pre-spawn CONCUR even when the other five conditions hold.

**SPOF list (editable in this doc):** `relay_watcher.sh`, `slack_relay.py`, `tg` shim, Valkey coordination bus, Dispatcher, `central_listener`, inbox-watcher systemd services.

**Anchor:** PR #907 (relay watcher session resilience) — single-file, +57 LoC, no schema, no external contract, bypass-loggable. Under five conditions it qualifies for bypass. Without the SPOF clause, every callsign's inbox flows through that loop and the bypass *becomes* the path. Aiden caught this gap; adopted.

### Refinement #2 — Enforcer regex deprecation uses fixture-replay, not free-running shadow

Empirical proof gate before the LiteLLM-interceptor replaces Enforcer-regex:

- **Frozen test set:** ≥10 historical incidents sourced from audit-log events covering R11 violation, CEO_FORMAT mismatch, and concur-gate bypass.
- **Threshold:** ≥90% recall AND ≥98% precision against the frozen set.
- **Floor:** ≥48h shadow run, but the empirical gate is fixture-replay against the frozen set — not signal-dependent free-running.

Free-running shadow has signal-dependent variance (a quiet 48h could fail to surface incidents the regex would catch). Fixture replay is deterministic and reproducible.

### Refinement #3 — CONCUR-latency tabletop covers both CTO and orchestrator failure

Tabletop runs at 03:00 UTC on the day Phase-2 transition opens. Two synthetic scenarios in the same window:

- **Offline-CTO** (e.g. Aiden unreachable): 2-of-3 fallback + bypass protocol. Measure bypass latency vs the 7-day median pre-spawn CONCUR latency from `#execution` timestamps. Target: bypass latency ≤4× median.
- **Offline-orchestrator** (Elliot unreachable): different failure shape — dispatch routing breaks, not just CONCUR. Needs a separate bypass mechanism + latency target. Both scenarios pass before Phase 2→3 transition.

### Refinement #4 — G-09 self-bootstrap dogfood

Part 15 v2 itself is the first amendment ratified under G-09 (3-way CONCUR → CEO approve → commit → effective on commit). The amendment dogfoods its own protocol:

- 3-way CONCUR — complete (elliot + aiden + max converged in `#execution` 2026-05-17).
- CEO approve — pending, via review of this PR.
- Commit-on-merge — this PR's merge is the moment Part 15 v2 takes effect.

If G-09 cannot survive its own application, the gap surfaces here before larger amendments land under it.

---

## G-01 anchor evidence

G-01 (Spec Completeness Standard) is the strongest of the new rules because two independent spec-mismatch incidents happened on 2026-05-17 during the deliberation itself:

- Elliot's KEI-71 (Dispatcher) dispatch to Atlas: Python + Agency_OS-coupled, vs the bd record's TypeScript + zero-coupling spec. Atlas held the dispatch on spec mismatch; corrected dispatch v2 issued.
- My KEI-101 (Valkey) Step 0: four spec mismatches (private bind→localhost, AOF→RDB, AUTH→no-AUTH, missing 2GB cgroup + 6-stream requirements) until I pulled Linear KEI-75 verbatim via MCP. Corrected Step 0 re-confirmed.

Both incidents shared a single cause: drafting from Dave's compressed verbatim directive without reading the bd / Linear record first. G-01 codifies the fix — pull `mcp__linear-server__get_issue` (or `bd show`) before any Step 0 or dispatch brief. Memory pinned as `feedback_bd_show_before_dispatch` (2026-05-17).

---

## Open items for Dave ratification

- Confirm the SPOF list above is accurate and editable in this doc going forward, not in a separate registry.
- Confirm the fixture-replay frozen set is sourced from audit logs (not a one-off curation by Enforcer maintainer).
- Confirm Phase 2→3 transition gate is BOTH tabletops passing, not either-or.
- Confirm G-09 dogfood: this PR's merge IS the activation moment for Part 15 v2 — no separate ratification step.

On Dave's `[CEO-RATIFY]` post in `#ceo`, this PR merges. Effective on merge per G-09.
