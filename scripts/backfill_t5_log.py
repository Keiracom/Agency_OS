"""
Backfill the T5 run log → business_universe.

Parses `Stage 2 VERIFY` lines out of a stage-2 verify log file and writes
each unique domain into business_universe. For rows that already exist
(e.g. the ~102 domains that advanced to Stage 4/9), only NULL columns
are filled — nothing is overwritten.

Usage:
    python3 scripts/backfill_t5_log.py [--source PATH] [--dry-run]

Default source:
    /tmp/claude-1001/-home-elliotbot-clawd-Agency-OS/4625e05a-5aec-4265-8fe5-41e7214dc167/tasks/boy0crzm2.output

Zero paid API calls — pure log parse + DB upsert.

Output (end of run):
    total parsed:    N
    total inserted:  N
    total updated:   N
    total skipped:   N
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg  # noqa: E402
from src.config.settings import settings  # noqa: E402

DEFAULT_SOURCE = (
    "/tmp/claude-1001/-home-elliotbot-clawd-Agency-OS/"
    "4625e05a-5aec-4265-8fe5-41e7214dc167/tasks/boy0crzm2.output"
)

# Stage 2 VERIFY line — biz= may contain spaces / punctuation; dm= may contain
# a full name with spaces. Lazy matches anchor on the next `<token>=` boundary.
LINE_RE = re.compile(
    r"Stage 2 VERIFY (\S+): "
    r"biz=(.*?) "
    r"abn=(\S+) "
    r"li=(\S+) "
    r"dm=(.*?) "
    r"fb=(\S+) "
    r"\(f_status=(\S+)\)"
)


def normalise_domain(raw: str) -> str:
    d = raw.strip().lower().rstrip(":")
    if d.startswith("www."):
        d = d[4:]
    return d


def truthy(raw: str) -> bool:
    return raw.strip().lower() == "true"


def null_or(raw: str) -> str | None:
    v = raw.strip()
    return None if v.lower() == "null" or not v else v


def parse_log(path: str) -> dict[str, dict]:
    """Return a {domain: row} dict. Last-seen values win on duplicates."""
    out: dict[str, dict] = {}
    parsed = 0
    with open(path) as f:
        for line in f:
            m = LINE_RE.search(line)
            if not m:
                continue
            parsed += 1
            raw_domain, biz, abn, li, dm, fb, _f_status = m.groups()
            domain = normalise_domain(raw_domain)
            if not domain:
                continue
            out[domain] = {
                "domain": domain,
                "display_name": (null_or(biz) or domain)[:255],
                "abn": null_or(abn),
                "has_linkedin": truthy(li),
                "dm_name_serp": null_or(dm),
                "has_facebook": truthy(fb),
            }
    print(f"total parsed:    {parsed}")
    print(f"unique domains:  {len(out)}")
    return out


async def upsert(pool, rows: dict[str, dict], *, dry_run: bool) -> tuple[int, int, int]:
    """Insert new domains / fill NULLs on existing. Returns (ins, upd, skip)."""
    inserted = updated = skipped = 0

    async with pool.acquire() as conn:
        existing = await conn.fetch(
            "SELECT id, domain, abn, dm_name, pipeline_stage FROM business_universe "
            "WHERE domain = ANY($1::text[])",
            list(rows.keys()),
        )
        # ABN is UNIQUE in business_universe — preload already-used ABNs so
        # we avoid inserting a duplicate (ABNs can legitimately map to >1
        # domain; the log is a secondary source so we drop the ABN on new
        # rows when it collides with an existing row for a different domain).
        incoming_abns = [r["abn"] for r in rows.values() if r["abn"]]
        used_abn_rows = (
            await conn.fetch(
                "SELECT abn FROM business_universe WHERE abn = ANY($1::text[])",
                incoming_abns,
            )
            if incoming_abns
            else []
        )
    by_domain = {r["domain"]: r for r in existing}
    used_abns = {r["abn"] for r in used_abn_rows}

    for domain, r in rows.items():
        exists = by_domain.get(domain)
        if exists:
            # Only fill NULL columns — never overwrite existing stage 4/9 data.
            sets: list[tuple[str, object]] = []
            if r["display_name"] and exists.get("display_name") is None:
                sets.append(("display_name", r["display_name"]))
            # Only set ABN if target is NULL AND this ABN isn't already
            # mapped to some other row (UNIQUE constraint on abn).
            if r["abn"] and exists["abn"] is None and r["abn"] not in used_abns:
                sets.append(("abn", r["abn"]))
                used_abns.add(r["abn"])
            if r["dm_name_serp"] and exists["dm_name"] is None:
                sets.append(("dm_name", r["dm_name_serp"]))
            # Stage stamp — only if below 2 (don't downgrade a stage-4/9 row).
            current_stage = exists["pipeline_stage"] or 0
            if current_stage < 2:
                sets.append(("pipeline_stage", 2))
                sets.append(("pipeline_status", "verified"))

            if not sets:
                skipped += 1
                continue

            if dry_run:
                updated += 1
                continue

            cols = ", ".join(f"{k} = ${i + 2}" for i, (k, _) in enumerate(sets))
            args = [exists["id"]] + [v for _, v in sets]
            async with pool.acquire() as conn:
                await conn.execute(
                    f"UPDATE business_universe SET {cols}, updated_at = NOW() WHERE id = $1",
                    *args,
                )
            updated += 1
        else:
            if dry_run:
                inserted += 1
                continue
            abn_for_insert = r["abn"]
            if abn_for_insert and abn_for_insert in used_abns:
                # ABN already mapped to another domain — drop it on this row.
                abn_for_insert = None
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO business_universe (
                            domain, website, display_name, abn, dm_name,
                            pipeline_stage, pipeline_status,
                            discovery_source, discovered_at,
                            pipeline_updated_at, created_at, updated_at
                        ) VALUES (
                            $1, $2, $3, $4, $5,
                            2, 'verified',
                            't5_log_backfill', NOW(),
                            NOW(), NOW(), NOW()
                        )
                        ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain <> ''
                        DO NOTHING
                        """,
                        domain,
                        f"https://{domain}",
                        r["display_name"],
                        abn_for_insert,
                        r["dm_name_serp"],
                    )
                # Track newly-used ABN so downstream rows in this run don't
                # try to re-use it.
                if abn_for_insert:
                    used_abns.add(abn_for_insert)
                inserted += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  skip {domain}: {type(exc).__name__}: {exc}")
                skipped += 1

    return inserted, updated, skipped


async def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument(
        "--dry-run", action="store_true", help="Parse + compute counts without writing."
    )
    args = ap.parse_args()

    print(f"source: {args.source}")
    print(f"mode:   {'DRY-RUN' if args.dry_run else 'EXECUTE'}")
    print("=" * 60)

    rows = parse_log(args.source)
    if not rows:
        print("no domains parsed — aborting")
        return

    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(
        dsn,
        min_size=2,
        max_size=8,
        statement_cache_size=0,
    )
    try:
        ins, upd, skp = await upsert(pool, rows, dry_run=args.dry_run)
    finally:
        await pool.close()

    print()
    print(f"total parsed:    {len(rows)}")
    print(f"total inserted:  {ins}")
    print(f"total updated:   {upd}")
    print(f"total skipped:   {skp}")


if __name__ == "__main__":
    asyncio.run(main())
