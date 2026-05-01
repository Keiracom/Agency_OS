"""
migrations/mem0_backfill.py — Backfill recent elliot_internal.memories to Mem0.

Usage:
    python migrations/mem0_backfill.py [--limit N] [--apply]

Flags:
    --limit N   Number of records to read (default: 100)
    --apply     Actually write to Mem0 (default: dry-run)
"""

import argparse
import json
import os
import sys

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
)


def fetch_memories(limit: int) -> list[dict]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.", file=sys.stderr)
        sys.exit(1)
    url = (
        f"{SUPABASE_URL}/rest/v1/agent_memories"
        f"?select=id,callsign,source_type,content,typed_metadata,tags,created_at"
        f"&order=created_at.desc"
        f"&limit={limit}"
    )
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    resp = httpx.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        print(f"ERROR: Supabase returned {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill memories to Mem0")
    parser.add_argument("--limit", type=int, default=100, help="Records to read (default: 100)")
    parser.add_argument("--apply", action="store_true", help="Write to Mem0 (default: dry-run)")
    args = parser.parse_args()

    rows = fetch_memories(args.limit)
    print(f"Fetched {len(rows)} records from public.agent_memories")

    if not args.apply:
        print(f"DRY-RUN: would write {len(rows)} records to Mem0. Pass --apply to execute.")
        for i, row in enumerate(rows[:5], 1):
            preview = (row.get("content") or "")[:80]
            print(f"  [{i}] source_type={row.get('source_type')} | callsign={row.get('callsign')} | {preview}")
        if len(rows) > 5:
            print(f"  ... and {len(rows) - 5} more")
        return

    from src.governance.mem0_adapter import Mem0Adapter

    adapter = Mem0Adapter()
    added = failed = 0

    for row in rows:
        content = (row.get("content") or "").strip()
        if not content:
            continue
        meta = row.get("typed_metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        try:
            adapter.add(
                content=content,
                metadata={**meta, "legacy_id": row.get("id"), "legacy_tags": row.get("tags") or []},
                callsign=row.get("callsign", "backfill"),
                source_type=row.get("source_type", "daily_log"),
            )
            added += 1
        except Exception as exc:
            print(f"WARN: failed to write record {row.get('id')}: {exc}")
            failed += 1

    usage = adapter.get_monthly_usage() if hasattr(adapter, "get_monthly_usage") else {}
    print(f"Backfill complete: {added} added, {failed} failed")
    print(f"Monthly usage after backfill: {usage}")


if __name__ == "__main__":
    main()
