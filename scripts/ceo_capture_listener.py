#!/usr/bin/env python3
"""ceo_capture_listener.py — post-cutover #ceo capture listener (Agency_OS-yku8).

Replaces the tmux-injecting elliot_slack_listener for the ephemeral model. After
cutover there is no persistent pane, so this listener has NO tmux dependency: it
watches #ceo over Slack Socket Mode (WebSocket, real-time) and, when a human
message carries a capture-worthy signal, fires a John capture spawn via the
dispatcher HTTP API.

Pipeline per non-bot #ceo message:
  Stage 1 (heuristic, free): does the text contain a ratification / architecture
    / decision signal? If not → skip.
  Stage 2 (Gemini Flash, only if stage 1 passed): classify DECISION | ARCHITECTURE
    | DIRECTIVE | NOISE with a confidence 0..1.
  Decision: spawn iff label != NOISE AND confidence > threshold (0.75).
  Cost control: at most 5 spawns/hour (Redis/Valkey counter). Over cap → skip.

Fail-open by contract: Gemini, the dispatcher, or the rate-limit store being
unreachable NEVER crashes the listener — it logs and continues. The rate-limit
gate fails *closed* on a counter error (skip the spawn to protect the cost cap)
while the process keeps running.

Security: the untrusted Slack message text is passed to the spawned capture
process via an ENV var only — it is never interpolated into a shell command
(command-injection guard).

The listener itself is NOT an AI agent — it is a plain Python process. Heavy
deps (slack_sdk, google.genai, redis) are imported lazily so the classification
+ decision logic is unit-testable without them installed.

Env: SLACK_BOT_TOKEN, SLACK_ENFORCER_APP_TOKEN (Socket Mode app token),
REDIS_URL (rate-limit counter), EMBEDDING/GEMINI key via GEMINI_API_KEY,
DISPATCHER_URL (default http://127.0.0.1:4001).
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ceo_capture_listener")

CEO_CHANNEL = os.environ.get("CEO_CAPTURE_CHANNEL", "C0B2PM3TV0B")
DISPATCHER_URL = os.environ.get("DISPATCHER_URL", "http://127.0.0.1:4001").rstrip("/")
CONFIDENCE_THRESHOLD = float(os.environ.get("CEO_CAPTURE_CONFIDENCE_THRESHOLD", "0.75"))
MAX_SPAWNS_PER_HOUR = int(os.environ.get("CEO_CAPTURE_MAX_SPAWNS_PER_HOUR", "5"))
RATE_LIMIT_KEY = "ceo_capture_listener:spawns_this_hour"
GEMINI_MODEL = os.environ.get("CEO_CAPTURE_GEMINI_MODEL", "gemini-2.5-flash")
JOHN_WORKING_DIR = os.environ.get("CEO_CAPTURE_WORKING_DIR", "/home/elliotbot/clawd/Agency_OS-john")
# Capture command run inside the spawned session. The message text is NOT
# interpolated here — it is read from the CEO_CAPTURE_MESSAGE env var the
# dispatcher injects (injection-safe). Override per deploy as the John launch
# mechanism settles.
DEFAULT_CAPTURE_COMMAND = (
    'python3 -c "import os; '
    "from src.keiracom_system.chat.exit_cycle import classify_and_save; "
    "classify_and_save(os.environ['CEO_CAPTURE_MESSAGE'])\""
)
CAPTURE_COMMAND = os.environ.get("CEO_CAPTURE_COMMAND", DEFAULT_CAPTURE_COMMAND)
# Dispatcher spawn backend. The listener itself has zero terminal-multiplexer
# dependency (Socket Mode + HTTP only); this only selects how the *dispatcher*
# backs the short-lived capture session. Default "tmux" matches the current
# dispatcher + John-workspace reality; set "container" for a fully ephemeral
# spawn once the container backend is provisioned (post-cutover target).
SPAWN_BACKEND = os.environ.get("CEO_CAPTURE_SPAWN_BACKEND", "tmux")

VALID_LABELS = ("DECISION", "ARCHITECTURE", "DIRECTIVE", "NOISE")

# ─── Stage 1 — free heuristic signals ─────────────────────────────────────────
RATIFICATION_SIGNALS = ("ratified", "confirmed", "go ahead", "approved", "locked", "canonical")
ARCHITECTURE_SIGNALS = (
    "the architecture is",
    "how this works",
    "the design is",
    "layer",
    "system prompt",
)
DECISION_SIGNALS = ("we will use", "decision:", "always do", "never do", "the rule is")
STAGE1_SIGNALS = RATIFICATION_SIGNALS + ARCHITECTURE_SIGNALS + DECISION_SIGNALS


def stage1_heuristic(text: str) -> bool:
    """Free first pass: does the text carry any capture-worthy signal?"""
    low = (text or "").lower()
    return any(signal in low for signal in STAGE1_SIGNALS)


def stage2_classify(text: str) -> tuple[str, float]:
    """Gemini Flash classifier → (label, confidence). Fail-open to ('NOISE', 0.0)."""
    prompt = (
        "Classify this #ceo message into exactly one label: DECISION, ARCHITECTURE, "
        "DIRECTIVE, or NOISE. DECISION = a ratified choice/rule; ARCHITECTURE = an "
        "explanation of how the system is designed; DIRECTIVE = an instruction to act; "
        "NOISE = chatter with no durable signal. Respond ONLY as JSON: "
        '{"label": "<LABEL>", "confidence": <0.0-1.0>}.\n\nMessage:\n' + (text or "")
    )
    try:
        from google import genai

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return _parse_classification(resp.text)
    except Exception:  # noqa: BLE001 — classification must never crash the listener
        logger.warning("stage2 Gemini classify failed — treating as NOISE", exc_info=True)
        return ("NOISE", 0.0)


def _parse_classification(raw: str) -> tuple[str, float]:
    """Parse the classifier's JSON (tolerant of code-fence wrapping)."""
    body = (
        (raw or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    )
    data = json.loads(body)
    label = str(data.get("label", "NOISE")).upper().strip()
    if label not in VALID_LABELS:
        label = "NOISE"
    confidence = float(data.get("confidence", 0.0))
    return (label, max(0.0, min(1.0, confidence)))


def classify(text: str) -> tuple[bool, str, float]:
    """Full pipeline decision (no side effects). Returns (should_spawn, label, confidence)."""
    if not stage1_heuristic(text):
        return (False, "STAGE1_SKIP", 0.0)
    label, confidence = stage2_classify(text)
    should = label != "NOISE" and confidence > CONFIDENCE_THRESHOLD
    return (should, label, confidence)


# ─── Rate limit (cost control) ────────────────────────────────────────────────


def _redis_client():
    """Lazy redis/valkey client from REDIS_URL/VALKEY_URL, or None if unconfigured."""
    url = os.environ.get("REDIS_URL") or os.environ.get("VALKEY_URL")
    if not url:
        return None
    import redis

    return redis.from_url(url, socket_timeout=3, socket_connect_timeout=3)


def within_rate_limit() -> bool:
    """True if under the hourly spawn cap.

    No store configured → rate limiting disabled (allow + warn). Store configured
    but errors → fail CLOSED (skip the spawn to protect the cost cap), never crash.
    """
    try:
        client = _redis_client()
    except Exception:  # noqa: BLE001
        logger.warning("rate-limit store error — skipping spawn to protect cost cap", exc_info=True)
        return False
    if client is None:
        logger.warning("REDIS_URL unset — spawn rate limiting DISABLED")
        return True
    try:
        current = int(client.get(RATE_LIMIT_KEY) or 0)
    except Exception:  # noqa: BLE001
        logger.warning("rate-limit read failed — skipping spawn to protect cost cap", exc_info=True)
        return False
    if current >= MAX_SPAWNS_PER_HOUR:
        logger.info("rate limit reached (%d/%d this hour) — skip", current, MAX_SPAWNS_PER_HOUR)
        return False
    return True


def record_spawn() -> None:
    """Increment the hourly counter after a successful spawn (sets 1h TTL on first)."""
    try:
        client = _redis_client()
        if client is None:
            return
        new_count = client.incr(RATE_LIMIT_KEY)
        if int(new_count) == 1:
            client.expire(RATE_LIMIT_KEY, 3600)
    except Exception:  # noqa: BLE001 — counter bookkeeping must never crash the listener
        logger.warning("rate-limit increment failed (non-fatal)", exc_info=True)


# ─── Spawn a John capture session via the dispatcher ──────────────────────────


def build_spawn_request(message_text: str) -> dict:
    """SpawnRequest payload for /dispatcher/spawn. The untrusted message is carried
    in env (CEO_CAPTURE_MESSAGE) — NEVER interpolated into the command string."""
    import time as _time

    key = f"ceo-capture-{int(_time.time() * 1000)}"
    brief = (
        "Classify and save this #ceo message to ceo_memory: "
        f"{message_text}. Use src.keiracom_system.chat.exit_cycle.classify_and_save()"
    )
    return {
        "backend": SPAWN_BACKEND,
        "key": key,
        "spawn_kwargs": {
            "session_name": key,
            "callsign": "john",
            "task_type": "capture",
            "working_dir": JOHN_WORKING_DIR,
            "command": CAPTURE_COMMAND,
            "brief": brief,
            "env": {"CALLSIGN": "john", "CEO_CAPTURE_MESSAGE": message_text},
        },
        "ttl_s": 600.0,
    }


def post_spawn(payload: dict) -> bool:
    """POST the spawn request to the dispatcher. Fail-open: log + return False on any error."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{DISPATCHER_URL}/dispatcher/spawn",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = 200 <= resp.status < 300
        if ok:
            logger.info("spawned John capture session key=%s", payload.get("key"))
        return ok
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("dispatcher spawn unreachable (%s) — skipping, listener continues", exc)
        return False


# ─── Message handling ─────────────────────────────────────────────────────────


def is_capture_candidate(event: dict) -> bool:
    """A top-level human text message in #ceo (not a bot, edit, join, or thread noise)."""
    if event.get("bot_id") or event.get("subtype"):
        return False
    if event.get("channel") != CEO_CHANNEL:
        return False
    return bool((event.get("text") or "").strip())


def handle_event(event: dict) -> str:
    """Run the pipeline for one Slack event. Returns an action label (for logs/tests)."""
    if not is_capture_candidate(event):
        return "skip_not_candidate"
    text = event["text"]
    should, label, confidence = classify(text)
    if not should:
        logger.info("skip [%s conf=%.2f]: %s", label, confidence, text[:80])
        return f"skip_{label.lower()}"
    if not within_rate_limit():
        return "skip_rate_limit"
    if post_spawn(build_spawn_request(text)):
        record_spawn()
        return "spawned"
    return "skip_spawn_failed"


# ─── Socket Mode runtime ──────────────────────────────────────────────────────


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
            event = (req.payload or {}).get("event", {})
            if event.get("type") == "message":
                handle_event(event)
        except Exception:  # noqa: BLE001 — one bad event must never kill the listener
            logger.warning("event handling error (non-fatal)", exc_info=True)

    sm = SocketModeClient(app_token=app_token, web_client=WebClient(token=bot_token))
    sm.socket_mode_request_listeners.append(_on_request)
    logger.info(
        "ceo_capture_listener up — channel=%s threshold=%.2f cap=%d/h dispatcher=%s",
        CEO_CHANNEL,
        CONFIDENCE_THRESHOLD,
        MAX_SPAWNS_PER_HOUR,
        DISPATCHER_URL,
    )
    sm.connect()
    import threading

    threading.Event().wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
