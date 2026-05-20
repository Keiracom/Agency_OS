#!/bin/bash
# elliot_session_start_slack_wake.sh — Auto-post 'elliot online' to Slack #ceo
# AND emit a self-direction file explaining bidirectional Slack so the fresh
# session reads it on startup and knows the comms channel.
#
# Triggered by elliot's .claude/settings.json SessionStart hook on every
# claude process bootstrap (keepalive respawn, /clear, fresh login).
#
# Dave directive 2026-05-19: only message Dave in Slack #ceo, never terminal.
# Hook persistence makes the auto-hello + recipe survive any session restart.

set -u

# Only fire for elliot worktree (defence in depth — hook is only installed
# in elliot's settings.json but guard against accidental copy).
CALLSIGN="${CALLSIGN:-}"
WT=$(pwd 2>/dev/null || echo "?")
if [[ "$CALLSIGN" != "elliot" && "$WT" != *"/clawd/Agency_OS"* ]]; then
    exit 0
fi

ENV_FILE="/home/elliotbot/.config/agency-os/.env"
RELAY="/home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py"
PYTHON="/home/elliotbot/clawd/Agency_OS/.venv/bin/python3"
SELF_DIRECTION="/tmp/elliot-slack-self-direction.md"

# Self-direction file the fresh session reads (anti_amnesia capsule will
# surface this on next SessionStart audit if wired in there too).
cat > "$SELF_DIRECTION" <<'MD'
# Elliot Slack Bidirectional — Self-direction (auto-written on wake)

**Comms channel for Dave is Slack #ceo. Terminal output is for tool calls only.**

## How bidirectional works
- **Outbound (you → Dave):** `slack_relay.py "<message>"` defaults to #ceo for elliot.
  The `tg` shim wraps this. Posts must be **plain-English bulleted** (bold category
  header + `- ` bullets). No PR numbers, commit SHAs, file paths, env vars, or PIDs
  in #ceo — those trip the format gate. Technical detail belongs in tool output, not Dave-facing posts.
- **Inbound (Dave → you):** `agency-os-elliot-slack-listener.service` (Slack
  Socket Mode) subscribes to channel ID `C0B2PM3TV0B` (#ceo) and writes
  incoming posts to `/tmp/telegram-relay-elliot/inbox/`. The
  `elliot-inbox-watcher.service` injects them into the elliot tmux pane as
  `[dave@ceo] <text>` followed by Enter. You see Dave's post as a user prompt.

## Access enforcement
- `slack_relay.py` has a callsign guard: only `CALLSIGN=elliot` may post.
  Other callsigns get `SLACK_ACCESS_DENIED` and exit 2. Don't try to bypass.
- The default channel for elliot is `C0B2PM3TV0B` (#ceo). Override with `-c`
  only when explicitly needed (rare; default is correct).

## Recovery if Slack relay breaks
1. Check both services: `systemctl --user status agency-os-elliot-slack-listener.service elliot-inbox-watcher.service`
2. Check the listener subscribed to the right channel ID (not name): `grep SLACK_LISTENER_CHANNELS /home/elliotbot/.config/systemd/user/agency-os-elliot-slack-listener.service` must show `C0B2PM3TV0B`
3. Check `SLACK_BOT_TOKEN` and `SLACK_ENFORCER_APP_TOKEN` present in `.env` (Socket Mode needs both — `xoxb-` and `xapp-1-`)
4. Test outbound: `source .env && CALLSIGN=elliot python3 slack_relay.py "test"` — should print `→ [ELLIOT] sent to Slack #C0B2PM3TV0B`

## Standing rule (Dave 2026-05-19)
Only message Dave in Slack #ceo. Never reply in the terminal pane, even when
Dave's prompt arrives there (it arrived via the listener — terminal is the
inject surface, not the reply surface). Replying in terminal is the explicit
failure mode Dave anchored.
MD

# Fetch last 40 Slack #ceo messages (Dave-elliot recent conversation).
# Per Dave 2026-05-19: this is the primary wake-recovery context.
if [[ -f "$ENV_FILE" && -x "$PYTHON" ]]; then
    (
        # shellcheck source=/dev/null
        set -a; source "$ENV_FILE"; set +a
        timeout 12 "$PYTHON" /home/elliotbot/clawd/Agency_OS/scripts/hooks/slack_history_wake.py
    ) >/dev/null 2>&1 || true
fi

# Probe live operational state — PIDs, services, bd, git, cursors.
# Complements the Slack-history file: discussion + live state = full wake context.
if [[ -x "$PYTHON" ]]; then
    timeout 15 "$PYTHON" /home/elliotbot/clawd/Agency_OS/scripts/hooks/live_state_probe.py >/dev/null 2>&1 || true
fi

# Emit both context files to stdout so Claude Code's SessionStart hook
# captures them as session context (same pattern as anti_amnesia_capsule).
echo "=== SLACK CEO RECENT HISTORY (last 40 messages, wake-recovery context) ==="
cat /tmp/elliot-slack-history.md 2>/dev/null || echo "(slack history file missing)"
echo ""
echo "=== LIVE OPERATIONAL STATE (PIDs, services, bd, git, cursors) ==="
cat /tmp/elliot-live-state.md 2>/dev/null || echo "(live state file missing)"
echo ""

# Side-effect: post wake message to #ceo. Output suppressed.
if [[ -f "$ENV_FILE" && -x "$RELAY" && -x "$PYTHON" ]]; then
    CALLSIGN=elliot timeout 15 "$PYTHON" "$RELAY" "**Elliot online**
- Session resumed
- Bidirectional Slack live
- Recent ceo history fetched and live state snapshotted
- Awaiting direction" >/dev/null 2>&1 || true
fi

exit 0
