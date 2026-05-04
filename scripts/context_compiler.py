#!/usr/bin/env python3
"""Context Compiler — synthesizes a scored, budget-aware briefing for agent
session startup. Replaces static file reads with intelligent context delivery.

Usage:
    python3 scripts/context_compiler.py --callsign elliot
    python3 scripts/context_compiler.py --callsign max --budget 3000
    python3 scripts/context_compiler.py --callsign aiden --raw  # dump scored memories

Queries agent_memories, ceo_memory, and git log. Scores each memory by:
    score = recency_decay(timestamp, type) × importance × role_relevance

Outputs a synthesized briefing within the token budget, structured as:
    IDENTITY (stable) → STRATEGIC (slow-change) → OPERATIONAL (fast-change) → RECENT (session-level)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv("/home/elliotbot/.config/agency-os/.env")

# Decay half-lives in hours — how fast each memory type loses relevance
DECAY_HALF_LIVES = {
    "identity_fact": 720,       # 30 days — very stable
    "ceo_instruction": 720,     # 30 days — Dave's rules persist
    "strategic_shift": 336,     # 14 days
    "pattern": 336,             # 14 days
    "milestone": 168,           # 7 days
    "decision": 72,             # 3 days
    "lesson": 72,               # 3 days
    "session_reflection": 24,   # 1 day
    "daily_log": 12,            # 12 hours
    "rsi_output": 48,           # 2 days
}

# Role relevance — which memory types matter most per callsign
ROLE_WEIGHTS = {
    "elliot": {"decision": 1.2, "lesson": 1.3, "pattern": 1.2, "milestone": 1.0},
    "aiden": {"decision": 1.2, "lesson": 1.3, "pattern": 1.2, "milestone": 1.0},
    "max": {"ceo_instruction": 1.5, "strategic_shift": 1.3, "decision": 1.2, "milestone": 1.1},
}

DEFAULT_BUDGET = 2000  # tokens (rough: 1 token ≈ 4 chars)
CHARS_PER_TOKEN = 4


def query_memories(callsign: str) -> list[dict]:
    """Pull scored memories from agent_memories."""
    import requests
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    # Get memories for this callsign + shared (dave instructions apply to all)
    resp = requests.get(
        f"{url}/rest/v1/agent_memories"
        f"?or=(callsign.eq.{callsign},callsign.eq.dave)"
        f"&state=eq.confirmed"
        f"&order=created_at.desc"
        f"&limit=500"
        f"&select=source_type,content,typed_metadata,created_at,callsign",
        headers=headers,
        timeout=10,
    )
    if resp.status_code != 200:
        return []
    return resp.json()


def query_checkpoint(callsign: str) -> dict | None:
    """Get latest operational checkpoint from ceo_memory."""
    import requests
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    key_name = f"ceo:{callsign}_operational_state"
    resp = requests.get(
        f"{url}/rest/v1/ceo_memory?key=eq.{key_name}&select=value,updated_at",
        headers=headers,
        timeout=5,
    )
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]
    return None


def get_recent_git(n: int = 10) -> list[str]:
    """Get recent commit messages from the main repo."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{n}", "--format=%h %s"],
            capture_output=True, text=True, timeout=5,
            cwd="/home/elliotbot/clawd/Agency_OS",
        )
        return result.stdout.strip().split("\n") if result.returncode == 0 else []
    except Exception:
        return []


def score_memory(memory: dict, callsign: str) -> float:
    """Score a memory: recency_decay × importance × role_relevance."""
    now = datetime.now(timezone.utc)
    source_type = memory.get("source_type", "unknown")

    # Parse timestamp
    created_str = memory.get("created_at", "")
    try:
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        created = now

    # Recency decay
    hours_ago = max((now - created).total_seconds() / 3600, 0.1)
    half_life = DECAY_HALF_LIVES.get(source_type, 48)
    recency = math.pow(0.5, hours_ago / half_life)

    # Importance (from metadata or default)
    meta = {}
    if memory.get("typed_metadata"):
        try:
            meta = json.loads(memory["typed_metadata"]) if isinstance(memory["typed_metadata"], str) else memory["typed_metadata"]
        except (json.JSONDecodeError, TypeError):
            pass
    importance = meta.get("importance", 5) / 10.0

    # Role relevance
    role_weights = ROLE_WEIGHTS.get(callsign, {})
    role_factor = role_weights.get(source_type, 1.0)

    return recency * importance * role_factor


def classify_tier(source_type: str) -> str:
    """Classify memory into briefing tier."""
    if source_type in ("identity_fact", "ceo_instruction"):
        return "IDENTITY"
    elif source_type in ("strategic_shift", "pattern", "milestone"):
        return "STRATEGIC"
    elif source_type in ("decision", "lesson"):
        return "OPERATIONAL"
    else:
        return "RECENT"


def compile_briefing(callsign: str, budget: int = DEFAULT_BUDGET, raw: bool = False) -> str:
    """Compile a scored, budget-aware briefing."""
    memories = query_memories(callsign)
    checkpoint = query_checkpoint(callsign)
    git_log = get_recent_git()

    # Score and sort
    scored = []
    for m in memories:
        s = score_memory(m, callsign)
        scored.append((s, m))
    scored.sort(key=lambda x: -x[0])

    if raw:
        lines = [f"{'SCORE':>6}  {'TYPE':<20}  {'TIER':<12}  CONTENT"]
        for s, m in scored[:50]:
            tier = classify_tier(m["source_type"])
            content = m["content"][:60].replace("\n", " ")
            lines.append(f"{s:6.3f}  {m['source_type']:<20}  {tier:<12}  {content}")
        return "\n".join(lines)

    # Build briefing by tier, respecting budget
    char_budget = budget * CHARS_PER_TOKEN
    tiers = {"IDENTITY": [], "STRATEGIC": [], "OPERATIONAL": [], "RECENT": []}

    for s, m in scored:
        if s < 0.01:  # below noise floor
            break
        tier = classify_tier(m["source_type"])
        tiers[tier].append((s, m))

    sections = []

    # IDENTITY — who we are (allocate 25% of budget)
    identity_budget = char_budget * 0.25
    identity_lines = []
    used = 0
    for s, m in tiers["IDENTITY"][:15]:
        line = f"- {m['content']}"
        if used + len(line) > identity_budget:
            break
        identity_lines.append(line)
        used += len(line)
    if identity_lines:
        sections.append("## IDENTITY\n" + "\n".join(identity_lines))

    # STRATEGIC — where we're going (allocate 25%)
    strat_budget = char_budget * 0.25
    strat_lines = []
    used = 0
    for s, m in tiers["STRATEGIC"][:15]:
        line = f"- [{m['source_type']}] {m['content']}"
        if used + len(line) > strat_budget:
            break
        strat_lines.append(line)
        used += len(line)
    if strat_lines:
        sections.append("## STRATEGIC\n" + "\n".join(strat_lines))

    # OPERATIONAL — current work (allocate 30%)
    ops_budget = char_budget * 0.30
    ops_lines = []
    used = 0
    for s, m in tiers["OPERATIONAL"][:20]:
        line = f"- [{m['source_type']}] {m['content']}"
        if used + len(line) > ops_budget:
            break
        ops_lines.append(line)
        used += len(line)
    if ops_lines:
        sections.append("## OPERATIONAL\n" + "\n".join(ops_lines))

    # RECENT — latest session context (allocate 20%)
    recent_budget = char_budget * 0.20
    recent_lines = []
    used = 0
    for s, m in tiers["RECENT"][:10]:
        line = f"- {m['content'][:200]}"
        if used + len(line) > recent_budget:
            break
        recent_lines.append(line)
        used += len(line)
    if recent_lines:
        sections.append("## RECENT\n" + "\n".join(recent_lines))

    # Checkpoint state
    if checkpoint:
        val = checkpoint.get("value", {})
        cp_lines = []
        if val.get("dave_last_instruction"):
            cp_lines.append(f"- Dave's last instruction: {val['dave_last_instruction']}")
        if val.get("active_threads"):
            threads = val["active_threads"]
            if isinstance(threads, list):
                cp_lines.append(f"- Active threads: {', '.join(threads)}")
        if val.get("agent_status"):
            statuses = val["agent_status"]
            if isinstance(statuses, dict):
                cp_lines.append(f"- Agent status: {', '.join(f'{k}={v}' for k,v in statuses.items())}")
        if val.get("notes"):
            cp_lines.append(f"- Notes: {val['notes']}")
        if cp_lines:
            sections.append("## CHECKPOINT\n" + "\n".join(cp_lines))

    # Git context
    if git_log:
        sections.append("## RECENT COMMITS\n" + "\n".join(f"- {c}" for c in git_log[:5]))

    briefing = f"# SESSION BRIEFING — {callsign.upper()}\nCompiled: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n" + "\n\n".join(sections)

    return briefing


def detect_callsign() -> str:
    """Auto-detect callsign from IDENTITY.md in the repo root."""
    identity_path = REPO_ROOT / "IDENTITY.md"
    if identity_path.exists():
        for line in identity_path.read_text().splitlines():
            if "CALLSIGN:" in line:
                # Format: **CALLSIGN:** elliot
                return line.split("CALLSIGN:")[-1].strip().strip("*").strip()
    return "elliot"


def main():
    parser = argparse.ArgumentParser(description="Context Compiler — scored session briefing")
    parser.add_argument("--callsign", default=None, help="Agent callsign (auto-detected from IDENTITY.md if omitted)")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="Token budget")
    parser.add_argument("--raw", action="store_true", help="Dump scored memories instead of briefing")
    args = parser.parse_args()

    callsign = args.callsign or detect_callsign()
    print(compile_briefing(callsign, args.budget, args.raw))


if __name__ == "__main__":
    main()
