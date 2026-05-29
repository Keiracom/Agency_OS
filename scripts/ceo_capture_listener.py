#!/usr/bin/env python3
"""ceo_capture_listener.py — #ceo capture listener (Agency_OS-yku8, FINAL design).

Viktor-ratified 2026-05-28. Haiku is cheap enough (~0.6¢ AUD/spawn) to classify
every #ceo message, so there is NO Python pre-filter, NO rate limiter, and NO
buffer file. The flow is simply:

    #ceo Socket Mode event → spawn one claude-haiku-4-5 agent → agent classifies
    → if decision/directive/ratified-architecture: write to ceo_memory via
      src.keiracom_system.chat.exit_cycle.classify_and_save(); else exit, nothing
      stored → agent exits.

The listener is NOT an AI agent — it is a thin Socket Mode → dispatcher bridge.
No tmux / send-keys dependency of any kind. Fail-open: a dispatcher outage or a
bad event logs and is skipped; the listener never crashes. `slack_sdk` is
lazy-imported so the bridge logic is unit-testable without it installed.

Security: the untrusted Slack message text is handed to the spawned agent via an
ENV var only (`CEO_CAPTURE_MESSAGE`) — it is never interpolated into the spawn
command string (command-injection guard).

Env: SLACK_BOT_TOKEN, SLACK_ENFORCER_APP_TOKEN (Socket Mode app token),
DISPATCHER_URL (default http://127.0.0.1:4001), CEO_CAPTURE_MODEL
(default claude-haiku-4-5 — Dave directive 2026-05-28).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ceo_capture_listener")

CEO_CHANNEL = os.environ.get("CEO_CAPTURE_CHANNEL", "C0B2PM3TV0B")
DISPATCHER_URL = os.environ.get("DISPATCHER_URL", "http://127.0.0.1:4001").rstrip("/")
# Tier-2 listener-agent model — claude-haiku-4-5 per Dave directive 2026-05-28.
CAPTURE_MODEL = os.environ.get("CEO_CAPTURE_MODEL", "claude-haiku-4-5")
CAPTURE_WORKING_DIR = os.environ.get(
    "CEO_CAPTURE_WORKING_DIR", "/home/elliotbot/clawd/Agency_OS-face"
)
SPAWN_BACKEND = os.environ.get("CEO_CAPTURE_SPAWN_BACKEND", "tmux")
CAPTURE_BRIEF = (
    "Classify this #ceo message. Is it a ratified decision, a directive, or a "
    "ratified architecture/'how it works' explanation? If YES: extract it as a "
    "clean self-contained statement and write it to ceo_memory by calling "
    "src.keiracom_system.chat.exit_cycle.classify_and_save() with a single-message "
    "conversation. If it is NOISE (chatter, acknowledgement, a bare question): "
    "exit with nothing stored. The message text is in the CEO_CAPTURE_MESSAGE env var."
)
# Agent launch command run inside the spawned session. The message is read from
# the env var at runtime (shell expansion of the injected env) — it is NEVER
# interpolated into this string by Python, so untrusted text cannot inject shell.
# Override per deploy as the agent-launch mechanism settles.
CAPTURE_COMMAND = os.environ.get(
    "CEO_CAPTURE_COMMAND",
    'claude -p --model "$CEO_CAPTURE_MODEL" --append-system-prompt "$CEO_CAPTURE_BRIEF" '
    '-- "$CEO_CAPTURE_MESSAGE"',
)

# Direct Slack→task creator (Agency_OS-evbn, Dave approved 2026-05-29). A
# 'TASK:'-prefixed #ceo message creates a public.tasks row directly; the
# kei45_emit_task_event trigger then drives the work-loop (Atlas wire #1283:
# id supplied, title NOT NULL, status MUST be 'available'). Skips Linear
# entirely — the [CEO]→Linear→webhook path is dead AND writing Linear violates
# the Linear-read-only LAW.
TASK_PREFIX = "TASK:"
TASK_TITLE_MAX_CHARS = 500
# kei45 trigger fires new_available only on INSERT with this status.
_TASK_INSERT_SQL = "INSERT INTO public.tasks (id, title, status) VALUES (%s, %s, 'available')"


def is_human_ceo_message(event: dict) -> bool:
    """Event hygiene only (NOT a content filter): a top-level human text message
    in #ceo. Bot messages + edits/joins are skipped so the listener never spawns
    on its own fleet's posts (loop/cost guard)."""
    if event.get("type") != "message" or event.get("bot_id") or event.get("subtype"):
        return False
    if event.get("channel") != CEO_CHANNEL:
        return False
    return bool((event.get("text") or "").strip())


def build_spawn_request(text: str) -> dict:
    """SpawnRequest payload for /dispatcher/spawn. The untrusted message is carried
    in env (CEO_CAPTURE_MESSAGE) — never interpolated into the command."""
    key = f"ceo-capture-{int(time.time() * 1000)}"
    return {
        "backend": SPAWN_BACKEND,
        "key": key,
        "spawn_kwargs": {
            "session_name": key,
            "callsign": "face",
            "task_type": "capture",
            "model": CAPTURE_MODEL,
            "working_dir": CAPTURE_WORKING_DIR,
            "command": CAPTURE_COMMAND,
            "brief": CAPTURE_BRIEF,
            "env": {
                "CALLSIGN": "face",
                "CEO_CAPTURE_MODEL": CAPTURE_MODEL,
                "CEO_CAPTURE_BRIEF": CAPTURE_BRIEF,
                "CEO_CAPTURE_MESSAGE": text,
            },
        },
        "ttl_s": 600.0,
    }


def spawn_capture_agent(text: str) -> bool:
    """POST the spawn request to the dispatcher. Fail-open: log + return False on error."""
    payload = build_spawn_request(text)
    req = urllib.request.Request(
        f"{DISPATCHER_URL}/dispatcher/spawn",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = 200 <= resp.status < 300
        logger.info("spawned %s capture agent key=%s ok=%s", CAPTURE_MODEL, payload["key"], ok)
        return ok
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("dispatcher spawn failed (%s) — listener continues", exc)
        return False


def is_task_command(text: str) -> bool:
    """A 'TASK:'-prefixed #ceo message is a direct task-creation command (evbn)."""
    return (text or "").strip().upper().startswith(TASK_PREFIX)


def extract_task_title(text: str) -> str:
    """Task title = the message body after the 'TASK:' prefix (trimmed + capped)."""
    body = (text or "").strip()
    if body.upper().startswith(TASK_PREFIX):
        body = body[len(TASK_PREFIX) :].strip()
    return body[:TASK_TITLE_MAX_CHARS]


def create_task_from_message(text: str, *, dsn: str | None = None) -> str | None:
    """INSERT one public.tasks row from a 'TASK:' message (Atlas wire #1283). The
    kei45_emit_task_event trigger then drives the loop. Values are bound as params
    (injection-safe); NO Linear. Returns the task id, or None on any error
    (fail-open — task-creation failure must never crash the listener)."""
    title = extract_task_title(text)
    if not title:
        logger.warning("TASK: message had no body — no task created")
        return None
    dsn = dsn or os.environ.get("DATABASE_URL") or os.environ.get("RETRIEVAL_EVENTS_DSN")
    if not dsn:
        logger.warning("no DATABASE_URL — cannot create task from #ceo TASK: message")
        return None
    task_id = f"ceo-task-{int(time.time() * 1000)}"
    try:
        import psycopg

        clean = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
        with (
            psycopg.connect(clean, prepare_threshold=None, autocommit=True) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(_TASK_INSERT_SQL, (task_id, title))
        logger.info("created task %s ('%s') from #ceo TASK: message", task_id, title[:60])
        return task_id
    except Exception:  # noqa: BLE001 — task creation must never crash the listener
        logger.warning("task creation failed (non-fatal)", exc_info=True)
        return None


def handle_event(event: dict) -> str:
    """Route one human #ceo message: a 'TASK:' command creates a public.tasks row
    (drives the work-loop); anything else spawns a Haiku capture agent. Returns an
    action label."""
    if not is_human_ceo_message(event):
        return "skip"
    text = event["text"]
    if is_task_command(text):
        return "task_created" if create_task_from_message(text) else "task_create_failed"
    return "spawned" if spawn_capture_agent(text) else "spawn_failed"


def main() -> int:
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.request import SocketModeRequest
    from slack_sdk.socket_mode.response import SocketModeResponse
    from slack_sdk.web import WebClient

    bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
    app_token = os.environ.get("SLACK_ENFORCER_APP_TOKEN", "")
    if not bot_token or not app_token:
        logger.error("SLACK_BOT_TOKEN and SLACK_ENFORCER_APP_TOKEN are both required")
        return 2

    def _on_request(client: SocketModeClient, req: SocketModeRequest) -> None:
        client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
        if req.type != "events_api":
            return
        try:
            handle_event((req.payload or {}).get("event", {}))
        except Exception:  # noqa: BLE001 — one bad event must never kill the listener
            logger.warning("event handling error (non-fatal)", exc_info=True)

    sm = SocketModeClient(app_token=app_token, web_client=WebClient(token=bot_token))
    sm.socket_mode_request_listeners.append(_on_request)
    logger.info(
        "ceo_capture_listener up — channel=%s model=%s dispatcher=%s",
        CEO_CHANNEL,
        CAPTURE_MODEL,
        DISPATCHER_URL,
    )
    sm.connect()
    import threading

    threading.Event().wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
