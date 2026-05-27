# Ephemeral-Agent Decommission Tracker

**Owner:** nova (Agency_OS-zf5a, PR #1140 §7 piece #7)
**Status:** TRACKING-ONLY — execution is post-Stage-4 cutover (cutover not yet fired)
**Companion:** Atlas's PR #1140 §7 piece #6 cutover-day checklist (operator runs piece 6 first, then this tracker)
**Date opened:** 2026-05-26

## §1 Scope + non-goals

This doc is the **canonical tracking artefact** enumerating every tmux/keepalive/runbook/memory artefact that must be removed or updated **after** the per-callsign Stage-4 cutover (PR #1140 §6 Stage 4) completes for that callsign. It is **not the cleanup itself** — it is the checklist a future operator (Dave + engineer-tier worker) runs against the live host post-cutover to confirm the obsolete-tmux layer is fully torn down.

**Out of scope (separate KEIs):**
- The cutover-day checklist (Atlas, §7 piece #6).
- The dispatcher binary (Nova PR #1188, §7 piece #1) + composer (Nova PR #1184) + envelope schema (Nova PR #1181) + paused_tasks (Nova PR #1193) + systemd template (Scout PR #1180).
- Any actual `git rm`, `systemctl disable`, or memory-file edits in this PR (the doc IS the change).

## §2 Pre-cutover artefact inventory (empirical, 2026-05-26)

### §2.1 Live tmux-dependent systemd user units (21 callsign-scoped + 2 elliot-only)

Captured via `systemctl --user list-unit-files | grep <pattern>`:

| Callsign | `-agent.service` | `-inbox-watcher.service` | NATS bridge unit |
|---|---|---|---|
| elliot | `elliot-agent.service` | `elliot-inbox-watcher.service` | `elliot-nats-inbox-bridge.service` |
| aiden | `aiden-agent.service` | `aiden-inbox-watcher.service` | `aiden-nats-review-bridge.service` |
| max | `max-agent.service` | `max-inbox-watcher.service` | `max-nats-review-bridge.service` |
| atlas | `atlas-agent.service` | `atlas-inbox-watcher.service` | `atlas-nats-dispatch-bridge.service` |
| orion | `orion-agent.service` | `orion-inbox-watcher.service` | `orion-nats-dispatch-bridge.service` |
| scout | `scout-agent.service` | `scout-inbox-watcher.service` | `scout-nats-dispatch-bridge.service` |
| nova | `nova-agent.service` | `nova-inbox-watcher.service` | `nova-nats-dispatch-bridge.service` |

Elliot-only additional units:
- `elliot-check-agents.service` + `elliot-check-agents.timer` — periodic `tmux capture-pane` liveness checker on the 7 agent panes.

**Keep-as-is (NOT decommissioned):**
- `agent-self-claim-loop@<callsign>.service` × 6 — KEI-92 bd-claim helper; not tmux-coupled.
- `agent-memories-indexer.service` — KEI-109 Weaviate indexer.
- `<callsign>-memories-indexer.service` (elliot only at present) — KEI-109 personal-memory indexer.
- `keiracom-agent-status.service` + `.timer` — agent-health collector; not tmux-coupled.
- All `keiracom-dispatcher@<callsign>.service` instances (Scout PR #1180) — these REPLACE the tmux units.

### §2.2 Scripts referencing `tmux send-keys` / `tmux capture-pane` / `tmux new-session`

Captured via `git grep -ln "tmux capture-pane\|tmux send-keys\|tmux new-session" scripts/`:

| Path | Role | Decommission action |
|---|---|---|
| `scripts/agent_keepalive.sh` | Per-pane tmux liveness loop | Archive to `scripts/archive/` |
| `scripts/fleet_supervisor.py` | Multi-pane supervisor | Archive |
| `scripts/bd_fleet_check.py` | Fleet-wide bd-state from panes | Update to read from dispatcher logs instead of `tmux capture-pane` |
| `scripts/orchestrator/auto_session_recovery.py` | Tmux session recovery | Archive |
| `scripts/orchestrator/elliot_polling_loop.py` | Elliot tmux poll loop | Update to read from inbox dir directly (no tmux) |
| `scripts/orchestrator/kei45_idle_daemon.sh` | Idle-pane detector | Archive (idle-detection is now per-spawn-exit) |
| `scripts/orchestrator/kei45_realtime_listener.py` | Tmux pane realtime listener | Archive |
| `scripts/orchestrator/kei45_acceptance_test.sh` | KEI-45 acceptance | Archive |
| `scripts/orchestrator/relay_watcher.sh` | Inbox → tmux send-keys | Archive (replaced by dispatcher binary) |
| `scripts/orchestrator/bd_complete_hook.sh` | Tmux-aware hook | Update — strip `tmux capture-pane` calls |
| `scripts/orchestrator/deliberator_concur_router.py` | Tmux-aware router | Update — read from inbox queue directly |
| `scripts/systemd_agent_supervisor.sh` | Systemd × tmux supervisor | Archive |

### §2.3 Per-callsign install scripts

Captured via `ls scripts/install_*_agent.sh`:

| Path | Status | Decommission action |
|---|---|---|
| `scripts/install_nova_agent.sh` | Tmux-based; installs `nova-agent.service` + `nova-inbox-watcher.service` | Archive to `scripts/archive/` after nova cutover |
| `scripts/install_<other-callsign>_agent.sh` | Not present in repo at audit time — likely host-side or in callsign-specific worktrees | Per-callsign: verify presence at cutover-day and archive if found |
| `scripts/install_dispatcher.sh` | NEW — installs the ephemeral-agent dispatcher | **KEEP** (replacement, not legacy) |

### §2.4 Memory files referencing the old "silence-in-pane" model

Captured via `find ~/.claude/projects -name 'feedback*silence*' -o -name 'feedback*tmux*'`:

| Path | Current semantics | Post-cutover update |
|---|---|---|
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/feedback_silence_means_silence.md` | "Agent silence in tmux pane = agent silent" | Update text → "Agent termination (no spawn process) = no work in progress; new dispatch arrives via inbox" |
| `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/feedback_silence_is_status.md` | Same family | Update or archive after the rewrite above lands |
| `~/.claude/projects/-home-elliotbot/memory/feedback_direct_address_overrides_silence.md` | "Direct @callsign overrides pane silence" | Update text → "Direct @callsign routes via decision_request envelope to the addressed callsign's inbox" |

### §2.5 Documentation references

`git grep -l "tmux" docs/` returns 30+ files. **Most are historical** (audit docs, architecture deep-dives describing the old model — these stay as historical record). **Active operational docs requiring update**:

- `docs/operations/agent-systemd-recovery.md` — Update to reflect dispatcher-based recovery (no tmux pane to recover).
- `docs/runbooks/<callsign>-identity.md` × 7 — Remove "tmux session" mentions from each callsign's runbook; the dispatcher binary (PR #1188) replaces the tmux substrate.
- `docs/architecture/keiracom_architecture_v2_inventory.md` — Add `inf.ephemeral_agent_dispatcher` inventory row (FULLY-LIVE post-cutover); flag any old `inf.tmux_*` rows as RETIRED.

Historical docs (no update needed — they describe the old model accurately for the period when it was canonical):
- `docs/architecture/deep_dives/layer_03_deliberators.md`, `layer_04_worker_agents.md`, `layer_05_orchestration.md`
- `docs/audits/*` (audit snapshots preserve their moment)
- `docs/architecture/drevon_port_2026-05-11.md`
- `docs/research/managed_agents_evaluation_2026-04-26.md`

## §3 Per-item decommission steps + verification commands

For each item: action, command, verification (passes only when correctly done).

### §3.1 Disable + remove per-callsign tmux-keepalive units

```bash
# Per callsign in cutover order from §6 Stage 4 (clones first: atlas, orion, scout, nova; then deliberators: aiden, max; then elliot last):
systemctl --user disable --now <callsign>-agent.service
systemctl --user disable --now <callsign>-inbox-watcher.service
systemctl --user disable --now <callsign>-nats-(dispatch|review|inbox)-bridge.service

# Verification (passes only when all 3 units for callsign X are gone):
systemctl --user is-active <callsign>-agent.service <callsign>-inbox-watcher.service 2>&1 | grep -qv "active" && echo OK || echo FAIL
```

### §3.2 Disable elliot-check-agents tmux-pane liveness checker

```bash
systemctl --user disable --now elliot-check-agents.timer elliot-check-agents.service

# Verification:
systemctl --user is-enabled elliot-check-agents.timer 2>&1 | grep -q "disabled\|not-found" && echo OK || echo FAIL
```

### §3.3 Archive obsolete scripts

```bash
mkdir -p scripts/archive/
# Items from §2.2 in the "Archive" column:
git mv scripts/agent_keepalive.sh scripts/archive/
git mv scripts/fleet_supervisor.py scripts/archive/
git mv scripts/orchestrator/auto_session_recovery.py scripts/archive/
git mv scripts/orchestrator/kei45_idle_daemon.sh scripts/archive/
git mv scripts/orchestrator/kei45_realtime_listener.py scripts/archive/
git mv scripts/orchestrator/kei45_acceptance_test.sh scripts/archive/
git mv scripts/orchestrator/relay_watcher.sh scripts/archive/
git mv scripts/systemd_agent_supervisor.sh scripts/archive/
git mv scripts/install_nova_agent.sh scripts/archive/

# Verification: no tmux-coupled scripts remain in the runtime path
git grep -l "tmux send-keys\|tmux capture-pane\|tmux new-session" scripts/ | grep -v "scripts/archive/" && echo FAIL || echo OK
```

### §3.4 Update (do not archive) the scripts that have non-tmux roles

`scripts/bd_fleet_check.py`, `scripts/orchestrator/elliot_polling_loop.py`, `scripts/orchestrator/bd_complete_hook.sh`, `scripts/orchestrator/deliberator_concur_router.py`:

```bash
# Replace tmux capture-pane calls with reads from dispatcher log
# or inbox queue. Per-script edits — operator opens each, removes tmux
# branches, leaves the non-tmux logic intact. Out-of-scope as a single
# command; tracked here as a per-script TODO.

# Verification after edits:
git grep -l "tmux send-keys\|tmux capture-pane\|tmux new-session" scripts/ | grep -v "scripts/archive/" && echo FAIL || echo OK
```

### §3.5 Update memory files

Per §2.4 — three files need text rewrites (not deletions). Each rewrite is its own commit. Verification:

```bash
# After rewrites, grep the OLD semantics out:
grep -l "tmux pane\|tmux silence\|capture-pane" \
    ~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/feedback_silence_*.md \
    ~/.claude/projects/-home-elliotbot/memory/feedback_direct_address_overrides_silence.md \
    2>/dev/null && echo FAIL || echo OK
```

### §3.6 Update active operational docs

Per §2.5 — three docs need updates:
- `docs/operations/agent-systemd-recovery.md`
- `docs/runbooks/<callsign>-identity.md` × 7
- `docs/architecture/keiracom_architecture_v2_inventory.md`

Verification:
```bash
# Each callsign's identity runbook should mention "dispatcher" + NOT mention "tmux"
for callsign in elliot aiden max atlas orion scout nova; do
    runbook="docs/runbooks/${callsign}-identity.md"
    if [ -f "$runbook" ]; then
        grep -q "dispatcher" "$runbook" && \
        ! grep -qE "tmux session|tmux pane" "$runbook" && \
        echo "OK: $callsign" || echo "FAIL: $callsign"
    fi
done
```

## §4 Per-callsign progress matrix

Operator marks each cell on cutover-day per callsign. State values: `TODO` / `IN-PROGRESS` / `DONE` / `BLOCKED:<reason>`.

| Callsign | §3.1 units | §3.2 elliot-only | §3.3 scripts | §3.4 script-edits | §3.5 memories | §3.6 docs |
|---|---|---|---|---|---|---|
| atlas (1st cutover) | TODO | N/A | shared (after all 7 cutover) | shared | shared | TODO |
| orion | TODO | N/A | shared | shared | shared | TODO |
| scout | TODO | N/A | shared | shared | shared | TODO |
| nova | TODO | N/A | shared | shared | shared | TODO |
| aiden | TODO | N/A | shared | shared | shared | TODO |
| max | TODO | N/A | shared | shared | shared | TODO |
| elliot (last cutover) | TODO | TODO | shared | shared | shared | TODO |

Shared items (script archive + memory rewrites + doc updates) execute ONCE after all 7 per-callsign §3.1 cutovers complete.

## §5 Memory cleanup detail

Per §2.4 the three memory files retain their FILE PATH but have their TEXT updated. The semantics shift from "tmux pane state" to "dispatcher + spawn lifecycle":

| File | Keep file? | Update what |
|---|---|---|
| `feedback_silence_means_silence.md` | Keep | Rewrite to define "no spawn process" instead of "tmux silence" |
| `feedback_silence_is_status.md` | Optionally archive | If silence is no longer a status signal (ephemeral spawns either run or don't exist), this memory may be obsolete |
| `feedback_direct_address_overrides_silence.md` | Keep | Rewrite to route via `decision_request` envelope to addressed callsign's inbox |

The actual rewrites are deferred to a follow-up commit per `feedback_split_orthogonal_scope`.

## §6 Rollback path per item

Each §3 item has a single-command rollback so an operator can undo if cutover validation fails:

| Item | Rollback |
|---|---|
| §3.1 unit disable | `systemctl --user enable --now <unit>` (restores) |
| §3.2 elliot-check-agents | `systemctl --user enable --now elliot-check-agents.timer` |
| §3.3 script archive | `git mv scripts/archive/<file> scripts/<original-path>` |
| §3.4 script edits | `git revert <commit>` |
| §3.5 memory rewrites | `git revert <commit>` |
| §3.6 doc updates | `git revert <commit>` |

The cutover order in §6 Stage 4 (clones first, deliberators second, elliot last) keeps blast-radius small at every step — if anything breaks, rollback is one `systemctl enable --now` per callsign.

## §7 Sign-off + completion criteria

This decommission tracker is **COMPLETE** when:

1. All 7 callsigns have §3.1 marked `DONE` in §4.
2. §3.2 `elliot-check-agents` is `DONE`.
3. All §3.3 archive moves are `DONE` and the verification grep returns `OK`.
4. All §3.4 script edits are `DONE` with verification `OK`.
5. All §3.5 memory rewrites are `DONE`.
6. All §3.6 doc updates are `DONE`.
7. Final verification: `git grep -l "tmux send-keys\|tmux capture-pane\|tmux new-session" scripts/ docs/runbooks/` returns ONLY `scripts/archive/` paths (no runtime-path tmux references).
8. A `ceo:tmux_layer_retired_<date>` canonical key is written to `ceo_memory` with the verbatim verification output (per `feedback_empirical_probe_before_concur`).

## §8 References

- PR #1140 §6 Stage 5 — post-cutover hardening narrative
- PR #1140 §7 piece #7 — this tracking artefact
- Companion: Atlas PR #1140 §7 piece #6 (cutover-day checklist) — operator runs piece #6 first
- Substrate scaffolding: PR #1180 (systemd template, Scout) + PR #1181 (envelope schema, Nova) + PR #1184 (composer, Nova) + PR #1188 (dispatcher, Nova) + PR #1193 (paused_tasks, Nova)
- bd: Agency_OS-zf5a

🤖 Generated with [Claude Code](https://claude.com/claude-code)
