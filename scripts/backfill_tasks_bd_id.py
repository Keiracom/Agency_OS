#!/usr/bin/env python3
"""backfill_tasks_bd_id.py — KEI-227 K1 backfill.

Walks public.tasks rows with linear_url IS NOT NULL AND bd_id IS NULL,
matches them against bd-Dolt issues by external_ref URL, and writes the
paired Agency_OS-xxx into the new bd_id column.

Usage:
    python3 scripts/backfill_tasks_bd_id.py            # dry-run
    python3 scripts/backfill_tasks_bd_id.py --apply    # mutate Postgres

Idempotent. Re-running on already-paired rows is a no-op (only filters
WHERE bd_id IS NULL). Safe to wire into a periodic timer post-merge.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from typing import Any

logger = logging.getLogger("backfill_tasks_bd_id")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_BD_BIN_DEFAULT = os.path.expanduser("~/.local/bin/bd")


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def _bd_bin() -> str:
    return os.environ.get("AGENCY_OS_BD_BIN", _BD_BIN_DEFAULT)


def _bd_list_json() -> list[dict[str, Any]]:
    """Return all bd issues (open + in_progress + closed) as a list of dicts.

    Default `bd list` filters to open/in_progress. The --all flag widens the
    set so closed bd issues with external_ref still pair against Postgres
    rows whose status='done' (which is most of them).
    """
    try:
        proc = subprocess.run(  # noqa: S603 — controlled args, no shell
            [_bd_bin(), "list", "--all", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.error("bd list --json failed: %s", exc)
        return []
    if proc.returncode != 0:
        logger.error("bd list --json exit %d: %s", proc.returncode, proc.stderr[:200])
        return []
    try:
        return json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        logger.error("bd list --json parse: %s", exc)
        return []


def _build_url_to_bd_id(issues: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map external_ref URL -> list of bd IDs. List form catches dual-claims."""
    url_to_ids: dict[str, list[str]] = {}
    for issue in issues:
        ref = issue.get("external_ref") or (issue.get("metadata") or {}).get("external_ref")
        if not ref:
            continue
        url_to_ids.setdefault(ref, []).append(issue.get("id", ""))
    return url_to_ids


def _candidate_url_variants(url: str) -> list[str]:
    """Linear URLs vary by trailing slug — strip suffix to widen the match.

    Examples:
      https://linear.app/keiracom/issue/KEI-227
      https://linear.app/keiracom/issue/KEI-227/atlas-k1-id-canonicalisation-...
    Both should pair with the same bd issue.
    """
    if not url:
        return []
    out = [url, url.rstrip("/")]
    parts = url.split("/issue/", 1)
    if len(parts) == 2:
        kei_part = parts[1].split("/", 1)[0]
        out.append(f"{parts[0]}/issue/{kei_part}")
    return list(dict.fromkeys(out))


def plan_backfill(conn: Any, url_to_ids: dict[str, list[str]]) -> dict[str, Any]:
    """Return {matched: [(task_id, bd_id, linear_url)], ambiguous: [...], unmatched: [...]}.

    Two ambiguity shapes:
      1. One Linear URL maps to multiple bd issues (dual-mirror) — bd-side.
      2. URL-variant stripping causes two Postgres rows to claim the same bd_id
         (e.g., KEI-54 and KEI-54B both stripping to /issue/KEI-54). Resolved
         here by passing through unique-bd_id detection: rows beyond the first
         claimant of a bd_id are demoted to ambiguous so the UNIQUE constraint
         never fires at apply time.
    """
    result: dict[str, Any] = {"matched": [], "ambiguous": [], "unmatched": []}
    bd_id_taken: dict[str, str] = {}  # bd_id -> first task_id that claimed it
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, linear_url FROM public.tasks "
            "WHERE linear_url IS NOT NULL AND bd_id IS NULL "
            "ORDER BY id"
        )
        rows = cur.fetchall()
    for row in rows:
        task_id, linear_url = row[0], row[1]
        bd_ids: list[str] = []
        for variant in _candidate_url_variants(linear_url):
            bd_ids = url_to_ids.get(variant, [])
            if bd_ids:
                break
        if not bd_ids:
            result["unmatched"].append((task_id, linear_url))
        elif len(bd_ids) > 1:
            result["ambiguous"].append((task_id, bd_ids, linear_url))
        else:
            bd_id = bd_ids[0]
            prior_claimant = bd_id_taken.get(bd_id)
            if prior_claimant is not None:
                result["ambiguous"].append(
                    (
                        task_id,
                        [bd_id],
                        f"{linear_url} (bd_id {bd_id} already claimed by {prior_claimant})",
                    )
                )
            else:
                bd_id_taken[bd_id] = task_id
                result["matched"].append((task_id, bd_id, linear_url))
    return result


def apply_backfill(conn: Any, matched: list[tuple[str, str, str]]) -> int:
    """Write bd_id for matched rows. Returns count written."""
    written = 0
    with conn.cursor() as cur:
        for task_id, bd_id, _url in matched:
            cur.execute(
                "UPDATE public.tasks SET bd_id = %s, updated_at = NOW() "
                "WHERE id = %s AND bd_id IS NULL",
                (bd_id, task_id),
            )
            written += cur.rowcount
    conn.commit()
    return written


def _print_summary(plan: dict[str, Any], applied: int | None) -> None:
    print(f"matched:    {len(plan['matched'])}")
    print(f"ambiguous:  {len(plan['ambiguous'])}")
    print(f"unmatched:  {len(plan['unmatched'])}")
    if applied is not None:
        print(f"applied:    {applied}")
    if plan["ambiguous"]:
        print("\nAmbiguous (Linear URL maps to multiple bd issues — manual triage):")
        for task_id, bd_ids, url in plan["ambiguous"][:10]:
            print(f"  {task_id} → {bd_ids} ({url})")
    if plan["unmatched"]:
        print("\nUnmatched sample (Linear URL has no bd issue with that external_ref):")
        for task_id, url in plan["unmatched"][:10]:
            print(f"  {task_id} → {url}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Mutate Postgres (default dry-run)")
    args = parser.parse_args(argv)

    try:
        import psycopg
    except ImportError:
        logger.error("psycopg not installed; pip install psycopg")
        return 2

    issues = _bd_list_json()
    if not issues:
        logger.warning("bd returned 0 issues — backfill aborted")
        return 1
    logger.info("loaded %d bd issues", len(issues))
    url_to_ids = _build_url_to_bd_id(issues)
    logger.info("indexed %d unique external_ref URLs", len(url_to_ids))

    with psycopg.connect(_dsn(), prepare_threshold=None) as conn:
        plan = plan_backfill(conn, url_to_ids)
        applied: int | None = None
        if args.apply:
            applied = apply_backfill(conn, plan["matched"])
            logger.info("applied %d rows", applied)
    _print_summary(plan, applied)
    return 0


if __name__ == "__main__":
    sys.exit(main())
