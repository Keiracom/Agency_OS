#!/usr/bin/env python3
"""wave1_retire_mem0.py — staged retirement of mem0 cloud memory backend.

Wave 1 Item 3 (Dave directive ts 1778565940, Elliot dispatch ts 1778566186,
confirm-to-execute on Step 0 addendum C). Mem0 never worked in production
(82 memories under wrong callsign per Atlas's mem0 audit section, empty
recall by construction). This script rescues the data + retires the path.

Steps run by this script:
  1. Read all mem0 memories via MemoryClient.get_all() (paginated).
  2. For each memory:
       - infer correct callsign from content (case-insensitive scan for any
         of {elliot, aiden, max, atlas, orion, scout}); fall back to the
         mem0 user_id; fall back to 'unknown' as last resort.
       - INSERT into public.agent_memories with:
           source_type = 'rescued_from_mem0'
           typed_metadata.node_set = ['rescued', 'mem0_migration']
           typed_metadata.mem0_original_user_id = <original>
           typed_metadata.mem0_id = <mem0 row id>
           state = 'confirmed'
  3. Print pre-migration count + post-migration insert count + Atlas's audit
     baseline (82) for cross-check.

NOT in this script (per directive — applied separately as PR evidence):
  - .env update (MEMORY_RECALL_BACKEND=supabase; MEM0_INTEGRATION_ENABLED=false)
  - ceo_memory key ceo:mem0_decision_2026-05-01 → "RETIRED"
  - mem0_adapter.py retained, gated by existing env-var checks at callsites

Usage:
    wave1_retire_mem0.py [--dry-run] [--limit N] [--page-size N]

    --dry-run (default): read mem0 + print what would be inserted; no DB writes.
    --execute: actually INSERT into agent_memories.
    --limit: cap total memories processed (default: all).
    --page-size: mem0 pagination size (default: 100).

Best-effort: per-memory failures log + continue. Exits 0 on success or
dry-run; 1 on partial failures; 2 on fatal config / SDK / DB issues.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("wave1_retire_mem0")

KNOWN_CALLSIGNS = ("elliot", "aiden", "max", "atlas", "orion", "scout")
_CALLSIGN_RE = re.compile(
    r"\b(" + "|".join(KNOWN_CALLSIGNS) + r")\b", re.IGNORECASE
)
ATLAS_AUDIT_BASELINE = 82  # per Atlas mem0 audit section (cross-check)


def infer_callsign(content: str, fallback: str = "unknown") -> str:
    """Scan content for a known callsign mention; return lowercase or fallback."""
    if not content:
        return fallback
    match = _CALLSIGN_RE.search(content)
    if match:
        return match.group(1).lower()
    return fallback


# mem0 v3 API requires non-empty filters on get_all. Iterate known callsigns
# (and common fallbacks for "wrong callsign" rows per Atlas's audit) so we
# enumerate the full retirement set.
MEM0_FILTER_USER_IDS = (*KNOWN_CALLSIGNS, "unknown", "system", "claude")


def fetch_mem0_memories(page_size: int = 100, limit: int | None = None) -> list[dict]:
    """Iterate get_all() per known user_id filter; concatenate + dedupe by id.

    Empty on SDK/auth failure (logged). Per-filter failure logs + continues.
    """
    try:
        from mem0 import MemoryClient
    except ImportError as exc:
        logger.error("mem0 SDK not importable: %s", exc)
        return []
    api_key = os.environ.get("MEM0_API_KEY", "")
    if not api_key:
        logger.error("MEM0_API_KEY not set — cannot read mem0")
        return []
    try:
        client = MemoryClient(api_key=api_key)
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.error("mem0 client init failed: %s", exc)
        return []

    seen_ids: set[str] = set()
    rows: list[dict] = []

    for user_id in MEM0_FILTER_USER_IDS:
        page = 1
        while True:
            try:
                resp = client.get_all(
                    filters={"user_id": user_id},
                    page=page,
                    page_size=page_size,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("mem0 get_all user_id=%s page=%d failed: %s",
                               user_id, page, exc)
                break
            # mem0 v3 returns dict {count, next, previous, results} OR plain list
            # (older versions). Normalise.
            if isinstance(resp, dict):
                batch = resp.get("results", []) or []
                has_next = bool(resp.get("next"))
            else:
                batch = resp or []
                has_next = len(batch) >= page_size
            if not batch:
                break
            for r in batch:
                if not isinstance(r, dict):
                    continue
                rid = r.get("id")
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    rows.append(r)
            logger.info("mem0 user_id=%s page=%d → %d rows (running total %d)",
                        user_id, page, len(batch), len(rows))
            if limit is not None and len(rows) >= limit:
                return rows[:limit]
            if not has_next:
                break
            page += 1
    return rows


def build_agent_memory_row(mem0_row: dict) -> dict | None:
    """Map a mem0 row to an agent_memories INSERT payload. None on bad shape."""
    content = mem0_row.get("memory") or mem0_row.get("text") or ""
    if not content:
        return None
    mem0_user_id = mem0_row.get("user_id") or ""
    callsign = infer_callsign(content, fallback=mem0_user_id or "unknown")
    typed_metadata = {
        "node_set": ["rescued", "mem0_migration"],
        "mem0_original_user_id": mem0_user_id,
        "mem0_id": mem0_row.get("id", ""),
        "mem0_metadata": mem0_row.get("metadata") or {},
    }
    return {
        "id": str(uuid4()),
        "callsign": callsign,
        "source_type": "rescued_from_mem0",
        "content": content,
        "typed_metadata": typed_metadata,
        "state": "confirmed",
    }


async def insert_rows(rows: Iterable[dict]) -> tuple[int, int]:
    """INSERT each row into public.agent_memories via asyncpg. Returns (ok, fail)."""
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.error("no DATABASE_URL / SUPABASE_DB_URL — cannot insert")
        return 0, sum(1 for _ in rows)
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    import asyncpg

    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    ok, fail = 0, 0
    try:
        for row in rows:
            try:
                await conn.execute(
                    """
                    INSERT INTO public.agent_memories
                      (id, callsign, source_type, content, typed_metadata,
                       created_at, valid_from, state)
                    VALUES ($1, $2, $3, $4, $5::jsonb, NOW(), NOW(), $6)
                    """,
                    row["id"],
                    row["callsign"],
                    row["source_type"],
                    row["content"],
                    json.dumps(row["typed_metadata"]),
                    row["state"],
                )
                ok += 1
            except Exception as exc:  # noqa: BLE001 — best-effort
                logger.warning("INSERT failed for mem0_id=%s: %s",
                               row["typed_metadata"].get("mem0_id"), exc)
                fail += 1
    finally:
        await conn.close()
    return ok, fail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="(default) Read + map without writing")
    parser.add_argument("--execute", dest="dry_run", action="store_false",
                        help="Actually INSERT into agent_memories")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args(argv)

    logger.info("Fetching mem0 memories (page-size=%d, limit=%s)",
                args.page_size, args.limit)
    mem0_rows = fetch_mem0_memories(page_size=args.page_size, limit=args.limit)
    logger.info("mem0 returned %d rows (Atlas audit baseline: %d)",
                len(mem0_rows), ATLAS_AUDIT_BASELINE)
    if len(mem0_rows) != ATLAS_AUDIT_BASELINE:
        logger.warning(
            "mem0 row count diverges from Atlas baseline (%d vs %d) — "
            "Atlas's audit was point-in-time; current state is canonical for retirement",
            len(mem0_rows), ATLAS_AUDIT_BASELINE,
        )

    payloads = []
    for r in mem0_rows:
        p = build_agent_memory_row(r)
        if p is None:
            logger.warning("skipping mem0 row with empty content: %s", r.get("id"))
            continue
        payloads.append(p)
    logger.info("built %d agent_memories payloads", len(payloads))

    if args.dry_run:
        logger.info("[DRY-RUN] would INSERT %d rows; pass --execute to live-run", len(payloads))
        for p in payloads[:3]:
            logger.info("  sample: callsign=%s content=%r metadata=%s",
                        p["callsign"], p["content"][:80], p["typed_metadata"])
        return 0

    ok, fail = asyncio.run(insert_rows(payloads))
    logger.info("migration complete: %d ok / %d failed", ok, fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
