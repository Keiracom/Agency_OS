#!/usr/bin/env python3
"""
session_start_load.py — Load relevant context from agent_memories at session start.

Queries agent_memories for:
1. Last 5 daily_logs (recent session summaries)
2. All dave_confirmed memories (CEO ground truth)
3. Top patterns and skills (by access_count)
4. Recent confirmed rows from last 3 days (sign of active learning)
5. Active blockers from ceo_memory

Outputs a structured brief that can be pasted into a new Claude session
or auto-injected via session-start hook.

Usage:
    python scripts/session_start_load.py
    python scripts/session_start_load.py --callsign aiden
    python scripts/session_start_load.py --format json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = "/home/elliotbot/.config/agency-os/.env"
SUPABASE_PROJECT_ID = "jatzvazlbusedwsnqxzr"


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def load_env() -> tuple[str, str]:
    env = dotenv_values(ENV_PATH)
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY missing from env.", file=sys.stderr)
        sys.exit(1)
    return url, key


def _headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def supabase_get(base_url: str, key: str, path: str) -> list:
    resp = requests.get(
        f"{base_url}/rest/v1/{path}",
        headers=_headers(key),
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"WARNING: Supabase query failed ({resp.status_code}): {path}", file=sys.stderr)
        return []
    return resp.json()


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def fetch_daily_logs(base_url: str, key: str, callsign: str | None) -> list:
    path = (
        "agent_memories"
        "?source_type=eq.daily_log"
        "&state=eq.confirmed"
        "&order=created_at.desc"
        "&limit=5"
        "&select=id,callsign,content,created_at,tags"
    )
    if callsign:
        path += f"&callsign=eq.{callsign}"
    return supabase_get(base_url, key, path)


def fetch_dave_confirmed(base_url: str, key: str, callsign: str | None) -> list:
    path = (
        "agent_memories"
        "?trust=eq.dave_confirmed"
        "&state=eq.confirmed"
        "&order=created_at.desc"
        "&limit=10"
        "&select=id,callsign,source_type,content,created_at,category,tags"
    )
    if callsign:
        path += f"&callsign=eq.{callsign}"
    return supabase_get(base_url, key, path)


def fetch_top_patterns_skills(base_url: str, key: str, callsign: str | None) -> list:
    path = (
        "agent_memories"
        "?source_type=in.(pattern,skill)"
        "&state=eq.confirmed"
        "&order=access_count.desc"
        "&limit=10"
        "&select=id,callsign,source_type,content,access_count,last_accessed_at,tags"
    )
    if callsign:
        path += f"&callsign=eq.{callsign}"
    return supabase_get(base_url, key, path)


def fetch_recent_confirmed_v2(base_url: str, key: str, callsign: str | None) -> list:
    """Use explicit ISO cutoff for the 3-day window — PostgREST safe.

    Note: PostgREST requires UTC timestamps without timezone suffix in query
    params (the +00:00 offset confuses URL parsing). Strip the offset and
    append 'Z' to keep it unambiguous.
    """
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=3)
    # Use UTC-naive ISO string with Z suffix — avoids + sign in URL params
    cutoff = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    path = (
        f"agent_memories"
        f"?state=eq.confirmed"
        f"&created_at=gt.{cutoff}"
        f"&order=created_at.desc"
        f"&limit=10"
        f"&select=id,callsign,source_type,content,created_at,trust,category"
    )
    if callsign:
        path += f"&callsign=eq.{callsign}"
    return supabase_get(base_url, key, path)


def fetch_active_blockers(base_url: str, key: str) -> list:
    """Pull known blocker keys from ceo_memory."""
    blocker_keys = ["ceo:pipeline_blockers", "ceo:dave_blockers", "ceo:launch_blockers_canonical"]
    rows = []
    for bkey in blocker_keys:
        path = f"ceo_memory?key=eq.{bkey}&select=key,value,updated_at"
        result = supabase_get(base_url, key, path)
        rows.extend(result)
    return rows


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _short_date(iso: str) -> str:
    """Return YYYY-MM-DD from an ISO timestamp."""
    try:
        return iso[:10]
    except Exception:
        return iso


def _truncate(text: str, n: int = 200) -> str:
    text = (text or "").strip()
    return text[:n] + "…" if len(text) > n else text


def format_markdown(
    callsign: str | None,
    daily_logs: list,
    dave_confirmed: list,
    patterns_skills: list,
    recent: list,
    blockers: list,
) -> str:
    label = callsign or "all"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Session Start Brief — {label} — {now}", ""]

    # --- Recent Sessions ---
    lines.append("## Recent Sessions")
    if daily_logs:
        for r in daily_logs:
            date = _short_date(r.get("created_at", ""))
            cs = r.get("callsign") or "?"
            snippet = _truncate(r.get("content", ""), 300)
            lines.append(f"- **{date}** [{cs}] {snippet}")
    else:
        lines.append("_No daily_log entries found._")
    lines.append("")

    # --- Dave's Ground Truth ---
    lines.append("## Dave's Ground Truth")
    if dave_confirmed:
        for r in dave_confirmed:
            date = _short_date(r.get("created_at", ""))
            cat = r.get("category") or r.get("source_type") or "?"
            snippet = _truncate(r.get("content", ""), 200)
            lines.append(f"- **[{cat}]** ({date}) {snippet}")
    else:
        lines.append("_No dave_confirmed memories found._")
    lines.append("")

    # --- Top Patterns & Skills ---
    lines.append("## Top Patterns & Skills")
    if patterns_skills:
        for r in patterns_skills:
            stype = r.get("source_type", "?")
            count = r.get("access_count") or 0
            last = _short_date(r.get("last_accessed_at") or "")
            snippet = _truncate(r.get("content", ""), 180)
            lines.append(f"- **[{stype}]** (used {count}x, last {last}) {snippet}")
    else:
        lines.append("_No pattern/skill memories found._")
    lines.append("")

    # --- Recent Activity ---
    lines.append("## Recent Activity (last 3 days)")
    if recent:
        for r in recent:
            date = _short_date(r.get("created_at", ""))
            stype = r.get("source_type") or "?"
            trust = r.get("trust") or ""
            cat = r.get("category") or ""
            meta = " | ".join(x for x in [stype, trust, cat] if x)
            snippet = _truncate(r.get("content", ""), 180)
            lines.append(f"- **{date}** [{meta}] {snippet}")
    else:
        lines.append("_No recent confirmed memories in last 3 days._")
    lines.append("")

    # --- Active Blockers ---
    lines.append("## Active Blockers")
    if blockers:
        for r in blockers:
            bkey = r.get("key", "?")
            updated = _short_date(r.get("updated_at", ""))
            val = r.get("value")
            if isinstance(val, list):
                for item in val[:5]:
                    snippet = _truncate(str(item), 150)
                    lines.append(f"- **{bkey}** ({updated}): {snippet}")
            elif isinstance(val, dict):
                snippet = _truncate(json.dumps(val), 200)
                lines.append(f"- **{bkey}** ({updated}): {snippet}")
            else:
                snippet = _truncate(str(val), 200)
                lines.append(f"- **{bkey}** ({updated}): {snippet}")
    else:
        lines.append("_No active blockers found._")
    lines.append("")

    return "\n".join(lines)


def format_json(
    callsign: str | None,
    daily_logs: list,
    dave_confirmed: list,
    patterns_skills: list,
    recent: list,
    blockers: list,
) -> str:
    return json.dumps(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "callsign": callsign,
            "daily_logs": daily_logs,
            "dave_confirmed": dave_confirmed,
            "patterns_skills": patterns_skills,
            "recent_confirmed": recent,
            "active_blockers": blockers,
        },
        indent=2,
        default=str,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Load agent_memories context brief for session start."
    )
    parser.add_argument(
        "--callsign",
        default=None,
        help="Filter memories by callsign (e.g. aiden). Omit for all callsigns.",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown).",
    )
    args = parser.parse_args()

    base_url, key = load_env()

    print("Querying agent_memories...", file=sys.stderr)

    daily_logs = fetch_daily_logs(base_url, key, args.callsign)
    dave_confirmed = fetch_dave_confirmed(base_url, key, args.callsign)
    patterns_skills = fetch_top_patterns_skills(base_url, key, args.callsign)
    recent = fetch_recent_confirmed_v2(base_url, key, args.callsign)
    blockers = fetch_active_blockers(base_url, key)

    print(
        f"Loaded: {len(daily_logs)} logs, {len(dave_confirmed)} dave_confirmed, "
        f"{len(patterns_skills)} patterns/skills, {len(recent)} recent, "
        f"{len(blockers)} blocker keys.",
        file=sys.stderr,
    )

    if args.format == "json":
        output = format_json(args.callsign, daily_logs, dave_confirmed, patterns_skills, recent, blockers)
    else:
        output = format_markdown(args.callsign, daily_logs, dave_confirmed, patterns_skills, recent, blockers)

    print(output)


if __name__ == "__main__":
    main()
