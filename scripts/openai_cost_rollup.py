"""
openai_cost_rollup.py — daily OpenAI cost summary from the JSONL cost log.

Reads last 24h of /home/elliotbot/clawd/logs/openai-cost.jsonl,
computes totals by use_case and callsign, writes a daily summary line to
/home/elliotbot/clawd/logs/openai-cost-daily.jsonl, and sends a Telegram
summary to the group.

Intended to run via systemd timer at 23:55 AEST (13:55 UTC).
"""

import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

COST_LOG = Path("/home/elliotbot/clawd/logs/openai-cost.jsonl")
DAILY_LOG = Path("/home/elliotbot/clawd/logs/openai-cost-daily.jsonl")


def load_last_24h(log_path: Path) -> list[dict]:
    """Read all JSONL lines from the last 24 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
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
                ts = datetime.fromisoformat(entry["ts"])
                if ts >= cutoff:
                    entries.append(entry)
            except Exception:
                continue
    return entries


def compute_summary(entries: list[dict]) -> dict:
    """Compute cost totals by use_case and callsign."""
    total = 0.0
    by_use_case: dict[str, float] = defaultdict(float)
    by_callsign: dict[str, float] = defaultdict(float)
    call_counts: dict[str, int] = defaultdict(int)

    for e in entries:
        cost = e.get("estimated_cost_usd", 0.0)
        use_case = e.get("use_case", "unknown")
        callsign = e.get("callsign", "unknown")
        total += cost
        by_use_case[use_case] += cost
        by_callsign[callsign] += cost
        call_counts[use_case] += 1

    return {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "total_usd": round(total, 6),
        "by_use_case": {k: round(v, 6) for k, v in by_use_case.items()},
        "by_callsign": {k: round(v, 6) for k, v in by_callsign.items()},
        "call_counts": dict(call_counts),
        "total_calls": len(entries),
    }


def write_daily_summary(summary: dict) -> None:
    """Append summary to daily JSONL log."""
    with open(DAILY_LOG, "a") as f:
        f.write(json.dumps(summary) + "\n")


def send_telegram(summary: dict) -> None:
    """Send daily summary to Telegram group."""
    total = summary["total_usd"]
    by_uc = summary.get("by_use_case", {})
    embed_cost = (
        by_uc.get("embedding", 0)
        + by_uc.get("store_embedding", 0)
        + by_uc.get("backfill_embedding", 0)
    )
    disc_cost = by_uc.get("discernment", 0)
    save_cost = by_uc.get("save_extraction", 0)
    qe_cost = by_uc.get("query_expansion", 0)
    calls = summary.get("total_calls", 0)
    msg = (
        f"[ELLIOT] Daily OpenAI cost: ${total:.4f} USD — "
        f"embeddings ${embed_cost:.4f} | discernment ${disc_cost:.4f} | "
        f"save ${save_cost:.4f} | query-expansion ${qe_cost:.4f} "
        f"({calls} calls)"
    )
    subprocess.run(["tg", "-g", msg], check=False)


def main() -> None:
    entries = load_last_24h(COST_LOG)
    summary = compute_summary(entries)
    write_daily_summary(summary)
    send_telegram(summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
