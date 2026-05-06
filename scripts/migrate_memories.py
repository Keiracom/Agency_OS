#!/usr/bin/env python3
"""
Migrate elliot_internal.memories → public.agent_memories (unified SSOT).

Usage:
    python3 scripts/migrate_memories.py          # dry-run (safe, no writes)
    python3 scripts/migrate_memories.py --execute  # actually write rows

Field mapping:
    type        → source_type
    metadata    → typed_metadata
    content     → content
    created_at  → created_at + valid_from
    <fixed>     → callsign='elliot', state='confirmed'

Deduplication: skip rows whose content already exists in agent_memories
(matched by content equality, not content_hash, since agent_memories has
no content_hash column).

Safety guarantees:
    - Dry-run by default (--execute required to write)
    - Never deletes from elliot_internal.memories (source kept as backup)
    - Idempotent: re-running produces zero new inserts if all rows present
    - Reports: total, skipped, migrated, errors
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[migrate-memories] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = "/home/elliotbot/.config/agency-os/.env"


# ── DSN resolution (same pattern as session_end_hook.py) ───────────────────


def _supabase_dsn() -> str | None:
    raw = (os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or "").strip()
    if raw:
        return raw.replace("postgresql+asyncpg://", "postgresql://")
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from dotenv import load_dotenv

        load_dotenv(ENV_FILE)
        from src.config.settings import settings  # type: ignore[import-not-found]

        return (settings.database_url or "").replace(
            "postgresql+asyncpg://", "postgresql://"
        ) or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("DSN unavailable: %s", exc)
        return None


# ── field mapping ───────────────────────────────────────────────────────────


def _map_row(row: dict) -> dict:
    """Map one elliot_internal.memories row → agent_memories insert dict."""
    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {"raw": metadata}

    # Provenance keys for audit traceability (N1 from PR #488 review)
    metadata["legacy_source"] = "elliot_internal.memories"
    metadata["legacy_id"] = str(row.get("id", ""))

    return {
        "callsign": "elliot",
        "source_type": row.get("type") or "unknown",
        "content": row.get("content") or "",
        "typed_metadata": metadata,
        "created_at": row.get("created_at"),
        "valid_from": row.get("created_at"),
        "state": "confirmed",
    }


# ── core migration logic ────────────────────────────────────────────────────


async def _fetch_legacy(conn) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, type, content, metadata, created_at
        FROM elliot_internal.memories
        WHERE deleted_at IS NULL
        ORDER BY created_at ASC
        """
    )
    return [dict(r) for r in rows]


async def _fetch_existing_contents(conn) -> set[str]:
    rows = await conn.fetch("SELECT content FROM public.agent_memories WHERE callsign = 'elliot'")
    return {r["content"] for r in rows}


async def _insert_row(conn, mapped: dict) -> None:
    await conn.execute(
        """
        INSERT INTO public.agent_memories
          (callsign, source_type, content, typed_metadata, created_at, valid_from, state)
        VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
        """,
        mapped["callsign"],
        mapped["source_type"],
        mapped["content"],
        json.dumps(mapped["typed_metadata"]),
        mapped["created_at"],
        mapped["valid_from"],
        mapped["state"],
    )


async def _migrate(dsn: str, execute: bool) -> dict:
    import asyncpg  # noqa: PLC0415

    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    counts = {"total": 0, "skipped": 0, "migrated": 0, "errors": 0}
    try:
        legacy_rows = await _fetch_legacy(conn)
        counts["total"] = len(legacy_rows)
        logger.info("Fetched %d non-deleted rows from elliot_internal.memories", counts["total"])

        existing = await _fetch_existing_contents(conn)
        logger.info("Found %d existing elliot rows in agent_memories (dedup set)", len(existing))

        for row in legacy_rows:
            mapped = _map_row(row)
            if mapped["content"] in existing:
                counts["skipped"] += 1
                continue

            if not execute:
                logger.debug(
                    "DRY-RUN: would insert source_type=%s created_at=%s",
                    mapped["source_type"],
                    mapped["created_at"],
                )
                counts["migrated"] += 1
                continue

            try:
                await _insert_row(conn, mapped)
                existing.add(mapped["content"])  # prevent in-batch dupes
                counts["migrated"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Insert failed for row (type=%s): %s", mapped["source_type"], exc)
                counts["errors"] += 1

    finally:
        await conn.close()

    return counts


# ── entry-point ─────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate elliot_internal.memories → public.agent_memories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Actually write rows. Default is dry-run (no writes).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    mode = "EXECUTE" if args.execute else "DRY-RUN"
    logger.info("Mode: %s", mode)

    dsn = _supabase_dsn()
    if not dsn:
        logger.error("No DATABASE_URL found — cannot connect. Aborting.")
        return 1

    counts = asyncio.run(_migrate(dsn, execute=args.execute))

    print(f"\n=== Migration report ({mode}) ===")
    print(f"  Total legacy rows:  {counts['total']}")
    print(f"  Already in target:  {counts['skipped']}")
    print(f"  Migrated:           {counts['migrated']}")
    print(f"  Errors:             {counts['errors']}")
    if not args.execute:
        print("\n  (DRY-RUN — re-run with --execute to apply)")

    return 0 if counts["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
