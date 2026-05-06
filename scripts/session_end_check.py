"""
FILE: scripts/session_end_check.py
PURPOSE: Session-end 3-store consistency check.
         Verifies each directive completed in the last 7 days has:
           1. A row in public.cis_directive_metrics
           2. A key in public.ceo_memory (ceo:directive_NNN_complete)
           3. An entry in docs/MANUAL.md Section 13
USAGE: python scripts/session_end_check.py
EXIT: Always 0 — informational only, never blocking.
"""

import sys
import re
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = "/home/elliotbot/.config/agency-os/.env"
MANUAL_PATH = Path("/home/elliotbot/clawd/Agency_OS/docs/MANUAL.md")
LOOKBACK_DAYS = 7


def load_env():
    env = dotenv_values(ENV_PATH)
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY missing from env.")
        sys.exit(0)
    return url, key


def supabase_get(base_url: str, key: str, path: str) -> list:
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    resp = requests.get(f"{base_url}/rest/v1/{path}", headers=headers, timeout=15)
    if resp.status_code != 200:
        print(f"WARNING: Supabase query failed ({resp.status_code}): {path}")
        return []
    return resp.json()


def fetch_recent_metrics(base_url: str, key: str) -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).date().isoformat()
    path = f"cis_directive_metrics?completed_date=gte.{cutoff}&order=completed_date.desc"
    return supabase_get(base_url, key, path)


def fetch_ceo_memory_keys(base_url: str, key: str) -> set:
    path = "ceo_memory?key=like.ceo:directive_*_complete&select=key"
    rows = supabase_get(base_url, key, path)
    return {row["key"] for row in rows}


def extract_manual_directives() -> set:
    """Return set of directive numbers found in Section 13 of MANUAL.md."""
    if not MANUAL_PATH.exists():
        print(f"WARNING: {MANUAL_PATH} not found.")
        return set()
    text = MANUAL_PATH.read_text(encoding="utf-8")
    # Match headers like: ### Directive #309, ### Directive 309, ### D1.8 ...
    nums = set()
    for m in re.finditer(r"#{2,4}\s+(?:Directive\s+)?[#D]?(\d+)", text, re.IGNORECASE):
        nums.add(int(m.group(1)))
    return nums


def directive_num_from_key(key: str) -> int | None:
    """Extract number from 'ceo:directive_309_complete'."""
    m = re.search(r"directive_(\d+)_complete", key)
    return int(m.group(1)) if m else None


def main():
    print("Session End — 3-Store Consistency Check")
    print("=" * 40)

    base_url, key = load_env()

    metrics = fetch_recent_metrics(base_url, key)
    ceo_keys = fetch_ceo_memory_keys(base_url, key)
    manual_nums = extract_manual_directives()

    print(f"Directives completed (last {LOOKBACK_DAYS} days): {len(metrics)}")
    print()

    gaps = 0
    for row in metrics:
        dir_id = row.get("directive_id") or row.get("directive_number") or row.get("id")
        completed = row.get("completed_date", "unknown")

        # Try to extract numeric ID
        num = None
        if dir_id is not None:
            try:
                num = int(str(dir_id).lstrip("Dd#"))
            except ValueError:
                num = None

        expected_key = f"ceo:directive_{num}_complete" if num is not None else None

        has_metrics = True  # We're iterating from metrics, so always True
        has_ceo = (expected_key in ceo_keys) if expected_key else False
        has_manual = (num in manual_nums) if num is not None else False

        metrics_str = "cis_directive_metrics: OK"
        ceo_str = (
            f"ceo_memory: OK" if has_ceo else f"ceo_memory: MISSING (expected key: {expected_key})"
        )
        manual_str = "Manual Section 13: OK" if has_manual else "Manual Section 13: MISSING"

        row_gaps = (not has_ceo) + (not has_manual)
        gaps += row_gaps

        label = f"Directive #{num}" if num is not None else f"Directive id={dir_id}"
        print(f"  {label} ({completed})")
        print(f"    {metrics_str}")
        print(f"    {ceo_str}")
        print(f"    {manual_str}")
        print()

    total_stores = len(metrics) * 3 if metrics else 0
    missing_stores = gaps
    complete_stores = total_stores - missing_stores

    print(
        f"Summary: {complete_stores}/{total_stores} stores complete across {len(metrics)} directives"
    )
    print(f"Gaps found: {gaps}")

    if gaps > 0:
        print()
        print("ACTION: Run scripts/three_store_save.py for any directives with gaps before /reset.")


if __name__ == "__main__":
    main()
