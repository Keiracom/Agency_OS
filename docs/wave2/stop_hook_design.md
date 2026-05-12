# Stop-Hook Auto-`[READY:<callsign>]` Design

Source: Claude Code docs (`https://code.claude.com/docs/en/hooks`) + existing `.claude/hooks/stop_relay_hook.sh` and `.claude/settings.json` from this worktree.

## 1. Claude Code Stop hook spec — what we get

### Fires per conversation TURN, not per session

Per the Claude Code lifecycle: *"`Stop` | When Claude finishes responding"*. It fires every time the assistant completes a turn (response sent back to user/orchestrator). Session-end is a separate `SessionEnd` event; sub-agent end is `SubagentStop`. So a Stop hook is the right place to mechanically emit a per-turn `[READY:<callsign>]` marker.

### Stdin JSON payload (fed to the hook on stdin)

```json
{
  "session_id": "abc123",
  "transcript_path": "/home/elliotbot/.claude/projects/<proj>/<session>.jsonl",
  "cwd": "/home/elliotbot/clawd/Agency_OS-scout",
  "permission_mode": "default | plan | acceptEdits | auto | dontAsk | bypassPermissions",
  "hook_event_name": "Stop",
  "effort": {"level": "low | medium | high | xhigh | max"},
  "agent_id": "<present only inside a subagent>",
  "agent_type": "<present with --agent flag>"
}
```

Per our own `stop_relay_hook.sh`, the rendered final assistant response is available via `.last_assistant_message` / `.message.content` / `.response` / `.text` in the JSON payload — note this isn't in the public docs, the keys are discovered empirically (file comments at `.claude/hooks/stop_relay_hook.sh:43-50`). The `transcript_path` is the authoritative source if the inline body is missing.

### Environment variables inherited

- `CLAUDE_PROJECT_DIR` — set by Claude Code, points at repo root.
- `CLAUDE_EFFORT` — mirrors `effort.level`.
- All other parent-process env, including our own `CALLSIGN` (set per worktree via systemd EnvironmentFile or shell rc).
- **NOT available:** `CLAUDE_MODEL`, `CLAUDE_AGENT_ID` (for non-subagent turns).

### Exit-code semantics

- `0` — success, Claude proceeds.
- `2` — **blocking**; stderr is fed back to Claude as an error, preventing the turn from ending. Useful for "tests must pass" gates. **We do NOT want this for `[READY:]` emission** — relay failure must never block the turn.
- Other non-zero — non-blocking error, logged.

### Registration in `.claude/settings.json`

```json
"hooks": {
  "Stop": [
    {"type": "command", "command": "bash .claude/hooks/<name>.sh", "timeout": 5}
  ]
}
```

Docs say Stop hooks **don't support matchers** — but our current `settings.json` does use a `"matcher": "*"` envelope (likely legacy / version-tolerant). New hook should follow whichever shape the existing 3 Stop hooks use to stay consistent.

### Hooks already wired in our Stop chain (this worktree)

1. `scripts/governance_router.py` — runs Python governance routing, **consumes stdin** first.
2. `stop_relay_hook.sh` — falls back to `/tmp/.stop_event_payload.json` because governance_router saved stdin to that file.
3. `session_store_stop.sh` — closes the session DB row.

The new hook MUST be ordered AFTER `governance_router.py` (i.e. read stdin from the temp-file fallback, same pattern as `stop_relay_hook.sh`). Order in the JSON array determines firing order.

## 2. Implementation sketch — `.claude/hooks/emit_ready_marker.sh`

```bash
#!/usr/bin/env bash
# Stop-hook companion: auto-emit [READY:<callsign>] marker if the agent's final
# response didn't already include one. Mechanical replacement for the
# discipline-dependent "agent remembers to type [READY:scout]" pattern.

set -u

# 1. Resolve callsign (CALLSIGN env preferred; IDENTITY.md fallback)
CALLSIGN="${CALLSIGN:-}"
if [[ -z "$CALLSIGN" && -r ./IDENTITY.md ]]; then
    CALLSIGN="$(grep -m1 -oE '\*\*CALLSIGN:\*\* [A-Za-z]+' ./IDENTITY.md \
        | awk '{print $NF}' | tr '[:upper:]' '[:lower:]')"
fi
CALLSIGN="${CALLSIGN:-unknown}"

# 2. Skip sub-agents (parent surfaces results; double-emit otherwise)
if [[ -n "${CLAUDE_AGENT_ID:-}" ]]; then exit 0; fi

# 3. Read Stop payload (stdin or temp-file fallback set by governance_router)
PAYLOAD="$(cat || true)"
[[ -z "$PAYLOAD" && -f /tmp/.stop_event_payload.json ]] && \
    PAYLOAD="$(cat /tmp/.stop_event_payload.json 2>/dev/null || true)"
[[ -z "$PAYLOAD" ]] && exit 0     # fail-open

# 4. Extract final response body
BODY=""
if command -v jq >/dev/null 2>&1; then
    BODY="$(printf '%s' "$PAYLOAD" | jq -r '.last_assistant_message // .message.content // .response // .text // ""')"
fi

# 5. De-dup: if body already contains [READY:<callsign>] (case-insensitive), skip
SHOUTY="$(echo "$CALLSIGN" | tr '[:lower:]' '[:upper:]')"
if echo "$BODY" | grep -qi -E "\[READY:(${CALLSIGN}|${SHOUTY})\]"; then
    exit 0
fi

# 6. Emit via slack_relay (fail-open: never block the turn)
/home/elliotbot/.local/bin/tg "[READY:${CALLSIGN}]" >/dev/null 2>&1 || true
exit 0
```

Wire-up in `.claude/settings.json` — append to existing `Stop` array AFTER `stop_relay_hook.sh`:

```json
{"type": "command", "command": "bash .claude/hooks/emit_ready_marker.sh", "timeout": 5}
```

## 3. Edge cases

| Case | Behaviour | Mitigation |
|---|---|---|
| Agent already typed `[READY:scout]` in body | Skipped via grep in step 5 | covered |
| Sub-agent turn ends | Skipped via `CLAUDE_AGENT_ID` check | covered |
| Agent crashed mid-turn (process killed) | Stop hook does NOT fire | **known gap** — document; out of scope for this hook |
| User runs `/reset` or `/clear` | Stop hook fires for the in-flight turn first, then context wipes | OK — marker emitted for the turn that actually finished |
| Mid-tool-call (Stop never fires until response complete) | Not a problem — Stop is post-response | covered |
| `tg` CLI unavailable or relay down | `|| true` swallows failure | covered (fail-open) |
| stdin already consumed by governance_router | Fallback to `/tmp/.stop_event_payload.json` | covered |
| Empty / malformed payload | Step 3 fail-open returns 0 | covered |

## 4. Test plan (post-build, for Aiden)

- Manual: type a reply without `[READY:scout]`, observe outbox/slack receives `[READY:scout]` within 5s.
- Manual: type a reply WITH `[READY:scout]`, observe outbox receives the body once (no double-emit).
- Sub-agent: invoke a Task and confirm sub-agent's Stop does NOT emit `[READY:scout]`.
- Failure: kill `tg` binary, confirm turn still ends cleanly (exit 0).
- Order: confirm `emit_ready_marker.sh` fires AFTER `stop_relay_hook.sh` so both see the same payload.

## Net

~35 LOC bash + 1 line in settings.json per worktree. Single-PR addition. Fail-open everywhere. The mechanical fix Dave flagged — `[READY:<callsign>]` no longer depends on the agent remembering.
