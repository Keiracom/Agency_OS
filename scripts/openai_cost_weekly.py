"""
openai_cost_weekly.py — weekly OpenAI cost summary from daily rollup JSONL.

Reads last 7 days of /home/elliotbot/clawd/logs/openai-cost-daily.jsonl,
computes 7-day totals, writes to Supabase ceo_memory key
'ceo:openai_weekly_cost', and sends Telegram summary to group.

Intended to run via systemd timer on Fridays at 18:00 AEST (08:00 UTC).
"""
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import dotenv_values

DAILY_LOG = Path("/home/elliotbot/clawd/logs/openai-cost-daily.jsonl")
ENV_PATH = "/home/elliotbot/.config/agency-os/.env"


def load_env() -> tuple[str, str]:
    env = dotenv_values(ENV_PATH)
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_KEY", "") or env.get("SUPABASE_KEY", "")
    if not url or not key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY missing from env.")
        sys.exit(1)
    return url, key


def load_last_7_days(log_path: Path) -> list[dict]:
    """Read daily summary lines from the last 7 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    entries = []
    if not log_path.exists():
        return entries
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("date", "") >= cutoff:
                    entries.append(entry)
            except Exception:
                continue
    return entries


def compute_weekly(entries: list[dict]) -> dict:
    """Aggregate 7-day totals from daily summaries."""
    total = 0.0
    by_use_case: dict[str, float] = defaultdict(float)
    by_callsign: dict[str, float] = defaultdict(float)
    total_calls = 0

    for e in entries:
        total += e.get("total_usd", 0.0)
        total_calls += e.get("total_calls", 0)
        for k, v in e.get("by_use_case", {}).items():
            by_use_case[k] += v
        for k, v in e.get("by_callsign", {}).items():
            by_callsign[k] += v

    return {
        "week_ending": datetime.now(timezone.utc).date().isoformat(),
        "total_usd": round(total, 6),
        "by_use_case": {k: round(v, 6) for k, v in by_use_case.items()},
        "by_callsign": {k: round(v, 6) for k, v in by_callsign.items()},
        "total_calls": total_calls,
        "days_covered": len(entries),
    }


def write_to_ceo_memory(supabase_url: str, supabase_key: str, summary: dict) -> None:
    """Upsert weekly cost summary to ceo_memory."""
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    payload = {
        "key": "ceo:openai_weekly_cost",
        "value": json.dumps(summary),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = requests.post(
        f"{supabase_url}/rest/v1/ceo_memory",
        headers=headers,
        json=payload,
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        print(f"WARNING: ceo_memory write failed ({resp.status_code}): {resp.text[:200]}")
    else:
        print("ceo_memory updated: ceo:openai_weekly_cost")


def send_telegram(summary: dict) -> None:
    """Send weekly summary to Telegram group."""
    total = summary["total_usd"]
    total_aud = round(total * 1.55, 4)
    by_uc = summary.get("by_use_case", {})
    embed_cost = by_uc.get("embedding", 0) + by_uc.get("store_embedding", 0) + by_uc.get("backfill_embedding", 0)
    disc_cost = by_uc.get("discernment", 0)
    save_cost = by_uc.get("save_extraction", 0)
    qe_cost = by_uc.get("query_expansion", 0)
    calls = summary.get("total_calls", 0)
    days = summary.get("days_covered", 0)
    msg = (
        f"[ELLIOT] Weekly OpenAI cost ({days}d): ${total:.4f} USD (${total_aud:.4f} AUD) — "
        f"embeddings ${embed_cost:.4f} | discernment ${disc_cost:.4f} | "
        f"save ${save_cost:.4f} | query-expansion ${qe_cost:.4f} "
        f"({calls} total calls)"
    )
    subprocess.run(["tg", "-g", msg], check=False)


def main() -> None:
    supabase_url, supabase_key = load_env()
    entries = load_last_7_days(DAILY_LOG)
    summary = compute_weekly(entries)
    write_to_ceo_memory(supabase_url, supabase_key, summary)
    send_telegram(summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
