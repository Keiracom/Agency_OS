#!/usr/bin/env python3
"""deliberator_concur_router.py — auto-routes deliberator divergence back to concur.

Watches /tmp/telegram-relay-elliot/inbox/ (processed mirror) for NATS messages
tagged from deliberators (aiden, max) on a deliberation or review topic. Pairs
responses by topic. On divergence, auto-dispatches a round-2 concur prompt to
both deliberators via tmux send-keys.

Runs as a small systemd service. Idempotent: each (topic, deliberator) pair is
processed once per round; concur state stored at /tmp/elliot_concur_state.json.

Per Dave directive 2026-05-19 — deliberators must concur with each other on
per-item details; never escalate to Dave. This service automates round-2.

Design constraints (Stage 6.5):
- Classification heuristic only (no LLM) for round-1 → round-2 trigger.
- Two heuristic divergence signals: (a) explicit [HOLD:peer] markers, (b)
  same-key opposite-value lines (e.g. "LAW XVI: HOT" vs "LAW XVI: POINTER").
- DEADLOCK after round-2: both must mark [DEADLOCK:<item>]; only then alert
  elliot via slack_relay.
"""
from __future__ import annotations
import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

PROCESSED_DIR = Path("/tmp/telegram-relay-elliot/processed")
STATE_PATH = Path("/tmp/elliot_concur_state.json")
TMUX_TARGETS = {"aiden": "aiden:0.0", "max": "maxbot:0.0"}
DELIBERATORS = {"aiden", "max"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("deliberator_concur_router")


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"deliberations": {}, "processed_files": []}
    try:
        return json.loads(STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"deliberations": {}, "processed_files": []}


def save_state(state: dict) -> None:
    try:
        STATE_PATH.write_text(json.dumps(state, indent=2))
    except OSError:
        pass


def classify_topic(text: str) -> str | None:
    """Heuristic: detect deliberation topic from response text."""
    # explicit topic markers
    m = re.search(r"\[deliberation:([a-z0-9_-]+)\]", text, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    # stage marker
    m = re.search(r"\bstage\s*(\d+)\b", text, re.IGNORECASE)
    if m:
        return f"stage-{m.group(1)}"
    # KEI reference
    m = re.search(r"\bKEI-?(\d+)\b", text, re.IGNORECASE)
    if m:
        return f"kei-{m.group(1)}"
    return None


def detect_divergence(a_text: str, m_text: str) -> list[str]:
    """Return list of divergence summaries between aiden + max responses."""
    divergences = []
    # Explicit HOLD markers
    for who, text in (("aiden", a_text), ("max", m_text)):
        for m in re.finditer(r"\[HOLD:([a-z0-9_-]+)\]", text, re.IGNORECASE):
            divergences.append(f"{who} HOLD on {m.group(1)}")
    # Tier-placement disagreements: "LAW X: HOT" vs "LAW X: POINTER"
    pattern = re.compile(r"(LAW\s*[A-Z\-]+\d*|GOV-\d+)\s*[:|]\s*(HOT|POINTER|REFERENCE)", re.IGNORECASE)
    a_tiers = {m.group(1).upper(): m.group(2).upper() for m in pattern.finditer(a_text)}
    m_tiers = {k: v for k, v in (m_tiers_iter := ((m.group(1).upper(), m.group(2).upper()) for m in pattern.finditer(m_text)))}
    for law in set(a_tiers) & set(m_tiers):
        if a_tiers[law] != m_tiers[law]:
            divergences.append(f"tier divergence on {law} — aiden={a_tiers[law]}, max={m_tiers[law]}")
    return divergences


def detect_deadlock(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"\[DEADLOCK:([a-z0-9_-]+)\]", text, re.IGNORECASE)]


def dispatch_concur_round(topic: str, deliberators: list[str], divergences: list[str], round_n: int) -> None:
    msg = (
        f"CONCUR ROUND {round_n} [from:elliot router, topic:{topic}]\n\n"
        f"Both of you responded but divergences remain. Per the deliberator-concur rule, "
        f"resolve these with each other before Dave sees the result:\n\n"
        + "\n".join(f"- {d}" for d in divergences) + "\n\n"
        f"Respond with your concur decision per divergence. If after this round you still "
        f"disagree, mark `[DEADLOCK:<item>]` and both deliberators must mark it for it to "
        f"escalate to Dave. Output your decisions in this turn — your stop hook publishes "
        f"to elliot's inbox."
    )
    for cs in deliberators:
        target = TMUX_TARGETS.get(cs)
        if not target:
            continue
        import subprocess
        try:
            subprocess.run(["tmux", "send-keys", "-t", target, msg, "Enter"], check=False, timeout=5)
        except Exception as e:
            log.warning("dispatch fail for %s: %s", cs, e)


def alert_elliot_deadlock(topic: str, items: list[str]) -> None:
    import subprocess
    msg = (
        f"**Deliberator deadlock — Dave call needed**\n"
        f"- Topic: {topic}\n"
        + "\n".join(f"- {item}" for item in items)
    )
    try:
        subprocess.run(
            ["/home/elliotbot/clawd/Agency_OS/.venv/bin/python3",
             "/home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py", msg],
            env={**__import__('os').environ, "CALLSIGN": "elliot"},
            timeout=10, check=False,
        )
    except Exception as e:
        log.warning("alert fail: %s", e)


def scan_once(state: dict) -> dict:
    """Scan recent processed inbox files for paired deliberator responses."""
    files = sorted(PROCESSED_DIR.glob("nats_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    cutoff = time.time() - 3600  # last 1h
    seen_topics = state.setdefault("deliberations", {})
    new_processed = []
    for f in files[:50]:
        if str(f) in state.get("processed_files", []):
            continue
        if f.stat().st_mtime < cutoff:
            continue
        try:
            d = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        sender = d.get("sender", "").lower()
        if sender not in DELIBERATORS:
            continue
        text = d.get("text", "")
        topic = classify_topic(text)
        if not topic:
            continue
        entry = seen_topics.setdefault(topic, {"round": 1, "responses": {}, "completed": False})
        if entry.get("completed"):
            continue
        entry["responses"][sender] = text
        new_processed.append(str(f))
    state["processed_files"] = (state.get("processed_files", []) + new_processed)[-500:]
    # check each topic for pair-completeness + divergence
    for topic, entry in seen_topics.items():
        if entry.get("completed"):
            continue
        responses = entry["responses"]
        if "aiden" not in responses or "max" not in responses:
            continue
        a, m = responses["aiden"], responses["max"]
        deadlocks_a = set(detect_deadlock(a))
        deadlocks_m = set(detect_deadlock(m))
        mutual_deadlocks = deadlocks_a & deadlocks_m
        if mutual_deadlocks:
            log.info("topic=%s mutual deadlock on %s — alerting elliot", topic, mutual_deadlocks)
            alert_elliot_deadlock(topic, list(mutual_deadlocks))
            entry["completed"] = True
            entry["outcome"] = "deadlock_escalated"
            continue
        divergences = detect_divergence(a, m)
        if not divergences:
            log.info("topic=%s concur reached — marking complete", topic)
            entry["completed"] = True
            entry["outcome"] = "concur"
            continue
        round_n = entry.get("round", 1)
        if round_n >= 2:
            log.warning("topic=%s round %d still diverges but no mutual deadlock — leaving for manual review", topic, round_n)
            entry["completed"] = True
            entry["outcome"] = "stuck_no_deadlock_mark"
            continue
        log.info("topic=%s dispatching concur round 2: %s", topic, divergences)
        dispatch_concur_round(topic, ["aiden", "max"], divergences, round_n + 1)
        entry["round"] = round_n + 1
        # reset responses for the new round
        entry["responses"] = {}
    return state


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true")
    p.add_argument("--daemon", type=int, default=30, metavar="SECONDS")
    args = p.parse_args()
    if args.once:
        state = load_state()
        state = scan_once(state)
        save_state(state)
        return 0
    log.info("daemon mode poll=%ss", args.daemon)
    while True:
        try:
            state = load_state()
            state = scan_once(state)
            save_state(state)
        except Exception:
            log.exception("scan err")
        time.sleep(args.daemon)


if __name__ == "__main__":
    sys.exit(main())
