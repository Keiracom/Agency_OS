"""src/governance/router.py — assistant-output classifier + Stop-hook entrypoint.

GOV-PHASE1-TRACK-B / B1.

Classifies an assistant text response and decides whether it should be
force-routed to the Telegram group (Dave-addressed) vs left as terminal-only
output (peer or system context).

Routing model: gpt-4o-mini (cheap, fast, deterministic for short inputs).
Cost is logged per call to logs/openai-cost.jsonl via openai_cost_logger.

Public API:
    classify(text, *, callsign=None, client=None) -> RoutingDecision
    main()                                         — Stop-hook entrypoint

Hook integration: .claude/settings.json `Stop` event invokes
`scripts/governance_router.py` which calls `main()` here. ATLAS owns the
PreToolUse hook entry; this hook is sequential and does not conflict.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from src.telegram_bot.openai_cost_logger import log_openai_call, COST_LOG_PATH

logger = logging.getLogger(__name__)

Audience = Literal["dave", "peer", "system"]
DEFAULT_MODEL = "gpt-4o-mini"
_USD_TO_AUD = 1.55
_DEFAULT_DAILY_CAP_AUD = 5.00


def _daily_cost_usd_today() -> float:
    """Sum estimated_cost_usd from COST_LOG_PATH for current UTC date. Best-effort."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = 0.0
    try:
        with open(COST_LOG_PATH, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("ts", "").startswith(today):
                        total += float(entry.get("estimated_cost_usd", 0))
                except (json.JSONDecodeError, ValueError):
                    continue
    except FileNotFoundError:
        pass
    except Exception as exc:
        logger.warning("router: cost cap read failed: %s", exc)
    return total


def _over_daily_cap() -> bool:
    """Return True if today's OpenAI spend (converted to AUD) exceeds ROUTER_DAILY_CAP_AUD."""
    cap_aud = float(os.environ.get("ROUTER_DAILY_CAP_AUD", _DEFAULT_DAILY_CAP_AUD))
    spent_aud = _daily_cost_usd_today() * _USD_TO_AUD
    if spent_aud >= cap_aud:
        logger.warning(
            "router: daily cap reached ($%.4f AUD of $%.2f AUD limit); "
            "skipping OpenAI classifier",
            spent_aud, cap_aud,
        )
        return True
    return False


# ── Classifier prompt ────────────────────────────────────────────────────────
# Kept short on purpose — gpt-4o-mini is fast at <300 input tokens. The text
# itself is appended at call time.
_SYSTEM_PROMPT = """You classify a single Claude-Code assistant message into:
  audience: "dave"   — addressed to Dave (the human CEO) — needs Telegram routing
  audience: "peer"   — addressed to a peer bot (Elliot/Aiden coordination) — keep terminal
  audience: "system" — internal / tool-result narration / log noise — keep terminal

Cues for "dave":
  - second-person address ("you", "Dave")
  - decision asks ("approve | reject | alternative")
  - completion announcements (PR URLs, summary tables)
  - questions Dave needs to answer

Cues for "peer":
  - [CALLSIGN:...] tags ([ELLIOT], [AIDEN], [CONCUR], [DIFFER])
  - bot-to-bot dispatch / outbox-style content

Cues for "system":
  - tool-call narration ("running pytest", "reading file X")
  - status updates without a human ask

Respond with strict JSON: {"audience": "...", "force_tg": true|false}
force_tg=true ONLY when audience="dave" AND content is a deliverable / decision ask."""


@dataclass(frozen=True)
class RoutingDecision:
    audience: Audience
    force_tg: bool
    raw_response: str | None = None  # full classifier reply for audit
    error: str | None = None         # populated on classifier failure

    def to_json(self) -> str:
        return json.dumps(asdict(self))


def _heuristic_fallback(text: str) -> RoutingDecision:
    """Conservative fallback used when the OpenAI client is unavailable
    (no API key in env, mocked-out tests, network failure). Errs on the
    side of NOT force-routing to TG — the goal is to never spam Dave on
    classifier failure."""
    lowered = text.lower()
    if any(tag in text for tag in ("[ELLIOT]", "[AIDEN]", "[ATLAS:", "[ORION:",
                                    "[CONCUR]", "[DIFFER]", "[CLAIM:")):
        return RoutingDecision(audience="peer", force_tg=False)
    # Strong Dave cues + a deliverable signature.
    has_dave_cue = (
        "approve | reject" in lowered
        or "awaiting your call" in lowered
        or "https://github.com/" in text
    )
    if has_dave_cue:
        return RoutingDecision(audience="dave", force_tg=True)
    # Default to system (terminal-only) on uncertainty.
    return RoutingDecision(audience="system", force_tg=False)


def _build_openai_client():
    """Lazy import + construct an OpenAI client. Returns None if the key
    is unset OR the openai package is not installed."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        logger.warning("router: openai package not installed; falling back to heuristic")
        return None
    return OpenAI(api_key=api_key)


def classify(
    text: str,
    *,
    callsign: str | None = None,
    client: Any | None = None,
) -> RoutingDecision:
    """Classify `text` into an audience + force_tg flag.

    Args:
        text:     assistant response to classify (full message body).
        callsign: optional ORION/ATLAS/ELLIOT/AIDEN tag for cost-log
                  attribution. Falls back to env CALLSIGN.
        client:   pre-built OpenAI client (used for tests). When None,
                  the function lazy-builds one from OPENAI_API_KEY.

    Returns:
        RoutingDecision dataclass — always returns a decision; classifier
        failures fall back to heuristic + populate `error`.
    """
    if not text or not text.strip():
        return RoutingDecision(audience="system", force_tg=False)
    if len(text) > 8000:
        # Truncate to keep input-token cost bounded.
        text = text[:8000]

    cs = callsign or os.environ.get("CALLSIGN") or "unknown"
    if _over_daily_cap():
        # GOV-PHASE1-COMPREHENSIVE-FIX D2 — emit a governance event so the
        # cost-cap fallback is loud, not silent. event_emit is a no-op on
        # any failure (governance signals must NEVER block the assistant).
        try:
            from src.governance._mcp_helpers import governance_event_emit
            governance_event_emit(
                callsign=cs,
                event_type="router_cost_cap_reached",
                event_data={
                    "spent_aud": round(_daily_cost_usd_today() * _USD_TO_AUD, 4),
                    "cap_aud": float(os.environ.get(
                        "ROUTER_DAILY_CAP_AUD", _DEFAULT_DAILY_CAP_AUD)),
                    "fallback": "heuristic_only",
                },
                tool_name="governance.router",
            )
        except Exception:  # pragma: no cover
            pass
        # Conservative default on cost-cap: peer + force_tg=False so we
        # never spam Dave when the classifier is unavailable for spend
        # reasons. Heuristic could mis-flag dave-cue content here.
        return RoutingDecision(audience="peer", force_tg=False)
    if client is None:
        client = _build_openai_client()
    if client is None:
        # GOV-PHASE1-COMPREHENSIVE-FIX D3 — heuristic-only fallback fired
        # because the OpenAI client could not be built (no API key, package
        # missing). Emit a governance event so the absence is observable.
        try:
            from src.governance._mcp_helpers import governance_event_emit
            governance_event_emit(
                callsign=cs,
                event_type="router_heuristic_fallback",
                event_data={
                    "reason": "no_openai_client",
                    "openai_key_present": bool(os.environ.get("OPENAI_API_KEY")),
                },
                tool_name="governance.router",
            )
        except Exception:  # pragma: no cover
            pass
        return _heuristic_fallback(text)

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=60,
        )
    except Exception as exc:
        logger.warning("router: OpenAI call failed (%s); using heuristic", exc)
        fallback = _heuristic_fallback(text)
        return RoutingDecision(
            audience=fallback.audience,
            force_tg=fallback.force_tg,
            error=str(exc),
        )

    # Cost logging — best-effort via openai_cost_logger.
    try:
        usage = getattr(response, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
        out_tok = getattr(usage, "completion_tokens", 0) if usage else 0
        log_openai_call(
            callsign=cs,
            use_case="governance.router",
            model=DEFAULT_MODEL,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
    except Exception as exc:
        logger.warning("router: cost log write failed: %s", exc)

    raw = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
        audience: Audience = parsed.get("audience", "system")
        if audience not in ("dave", "peer", "system"):
            audience = "system"
        force_tg = bool(parsed.get("force_tg", False))
        # Safety: only allow force_tg when audience is dave.
        if audience != "dave":
            force_tg = False
        return RoutingDecision(
            audience=audience, force_tg=force_tg, raw_response=raw,
        )
    except json.JSONDecodeError as exc:
        logger.warning("router: classifier returned non-JSON (%s); raw=%r",
                       exc, raw[:200])
        fallback = _heuristic_fallback(text)
        return RoutingDecision(
            audience=fallback.audience,
            force_tg=fallback.force_tg,
            raw_response=raw,
            error=f"json_decode: {exc}",
        )


def main() -> int:
    """Stop-hook entrypoint. Reads JSON from stdin (Claude Code Stop event
    payload), classifies the assistant message, prints a single-line JSON
    routing decision to stdout, exits 0.

    Failures still exit 0 — this hook must NEVER block the assistant.
    """
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}

    # Claude Code Stop event payload shape varies; try common keys.
    text = (
        payload.get("message", {}).get("content", "")
        or payload.get("response", "")
        or payload.get("text", "")
        or ""
    )
    decision = classify(text)
    print(decision.to_json())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
