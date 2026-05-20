#!/usr/bin/env python3
"""weekly_cycle_from_bd.py — KEI-29 P2: weekly Linear cycle from bd ready.

Every Monday 07:00 AEST (Sun 21:00 UTC) via systemd timer:
  1. `bd ready --json` → list of unblocked issues.
  2. Filter to priority IN (0, 1) (P0+P1) AND non-empty external_ref. Per
     Dave ratification ts ~1778631920: full picture, not a cap.
  3. Resolve each KEI-N external_ref → Linear issue UUID via GraphQL.
  4. Compute target Monday 07:00 AEST (next Monday if today's Monday is past).
  5. Idempotent: look up cycle with startsAt == target. Skip-create if exists;
     reuse its UUID for issue top-up.
  6. issueUpdate(input: {cycleId}) per resolved issue.

Operator override: `--force-now` creates an ad-hoc cycle starting now.

Exit codes:
  0 — happy path OR idempotent skip OR no-eligible-items no-op
  2 — LINEAR_API_KEY unset (operator misconfig signal — surfaces in timer log)

Mirrors the GraphQL + state-path patterns in scripts/betterstack_to_linear.py.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

logger = logging.getLogger("weekly_cycle_from_bd")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_LINEAR_GRAPHQL = "https://api.linear.app/graphql"
_DEFAULT_TEAM_ID = "4686528f-ce77-4c2f-968b-3dc76b34d6fe"  # Keiracom team
_BD_BIN = os.path.expanduser("~/.local/bin/bd")
_KEI_REF_RE = re.compile(r"linear\.app/[^/]+/issue/KEI-(\d+)", re.IGNORECASE)
# AEST = UTC+10 (no DST in NSW; Brisbane). Monday 07:00 AEST → Sun 21:00 UTC prev day.
_AEST_OFFSET_HOURS = 10
_TARGET_HOUR_AEST = 7
_CYCLE_DURATION_DAYS = 7


def _linear_graphql(api_key: str, query: str, variables: dict | None = None) -> dict | None:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        _LINEAR_GRAPHQL,
        data=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read() or "null")
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Linear GraphQL failed: %s", exc)
        return None


def _bd_ready() -> list[dict]:
    """Returns parsed `bd ready --json` output (empty list on any failure)."""
    try:
        proc = subprocess.run(  # noqa: S603 — absolute path, no shell, no user input
            [_BD_BIN, "ready", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            logger.warning("bd ready exit %d: %s", proc.returncode, proc.stderr[:200])
            return []
        return json.loads(proc.stdout or "[]")
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("bd ready failed: %s", exc)
        return []


def _extract_kei_number(external_ref: str) -> int | None:
    """Parse 'https://linear.app/keiracom/issue/KEI-29' → 29; None if not a KEI URL."""
    if not external_ref:
        return None
    m = _KEI_REF_RE.search(external_ref)
    return int(m.group(1)) if m else None


def filter_eligible(items: list[dict]) -> list[tuple[dict, int]]:
    """Return (item, kei_number) pairs where priority in {0,1} AND external_ref is KEI."""
    out: list[tuple[dict, int]] = []
    for it in items:
        if it.get("priority") not in (0, 1):
            continue
        kei_n = _extract_kei_number(it.get("external_ref", ""))
        if kei_n is None:
            logger.info("skip %s — no Linear external_ref", it.get("id", "?"))
            continue
        out.append((it, kei_n))
    return out


def _resolve_kei_to_uuid(api_key: str, kei_number: int) -> str | None:
    """Translate KEI-N → Linear issue UUID."""
    query = 'query($n:Float!){issues(filter:{team:{key:{eq:"KEI"}},number:{eq:$n}}){nodes{id}}}'
    resp = _linear_graphql(api_key, query, {"n": float(kei_number)})
    nodes = (((resp or {}).get("data") or {}).get("issues") or {}).get("nodes") or []
    return nodes[0].get("id") if nodes else None


def compute_target_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (starts_at_utc, ends_at_utc) for the next Monday 07:00 AEST cycle.

    If `now` is Monday before 07:00 AEST, use THIS Monday. Otherwise, next Monday.
    """
    n = now or datetime.now(UTC)
    aest = n + timedelta(hours=_AEST_OFFSET_HOURS)
    # weekday(): Monday=0 ... Sunday=6 in AEST frame.
    days_until_monday = (7 - aest.weekday()) % 7
    # If today IS Monday AND we're still before the target hour, fire for TODAY.
    if aest.weekday() == 0 and aest.hour < _TARGET_HOUR_AEST:
        days_until_monday = 0
    elif days_until_monday == 0:
        days_until_monday = 7  # already past Monday 07:00 — use next week
    starts_aest = (aest + timedelta(days=days_until_monday)).replace(
        hour=_TARGET_HOUR_AEST, minute=0, second=0, microsecond=0
    )
    starts_utc = starts_aest - timedelta(hours=_AEST_OFFSET_HOURS)
    ends_utc = starts_utc + timedelta(days=_CYCLE_DURATION_DAYS)
    return starts_utc.replace(tzinfo=UTC), ends_utc.replace(tzinfo=UTC)


def _find_existing_cycle(api_key: str, team_id: str, starts_at_iso: str) -> str | None:
    """Return UUID of cycle whose startsAt matches target, else None."""
    query = (
        "query($t:String!,$s:DateTimeOrDuration!){"
        "team(id:$t){cycles(filter:{startsAt:{eq:$s}}){nodes{id startsAt}}}}"
    )
    resp = _linear_graphql(api_key, query, {"t": team_id, "s": starts_at_iso})
    if resp is None:
        # Fall back to scanning without filter — defensive against API schema drift.
        return _scan_existing_cycle(api_key, team_id, starts_at_iso)
    nodes = (((resp or {}).get("data") or {}).get("team") or {}).get("cycles", {}).get(
        "nodes"
    ) or []
    return nodes[0].get("id") if nodes else None


def _scan_existing_cycle(api_key: str, team_id: str, starts_at_iso: str) -> str | None:
    query = "query($t:String!){team(id:$t){cycles{nodes{id startsAt}}}}"
    resp = _linear_graphql(api_key, query, {"t": team_id})
    nodes = (((resp or {}).get("data") or {}).get("team") or {}).get("cycles", {}).get(
        "nodes"
    ) or []
    target = starts_at_iso.rstrip("Z")
    for n in nodes:
        sa = (n.get("startsAt") or "").rstrip("Z")
        if sa.startswith(target[:19]):  # compare to second precision
            return n.get("id")
    return None


def _create_cycle(
    api_key: str, team_id: str, starts_at_iso: str, ends_at_iso: str, name: str
) -> str | None:
    mutation = "mutation($input:CycleCreateInput!){cycleCreate(input:$input){success cycle{id}}}"
    input_fields = {
        "teamId": team_id,
        "name": name,
        "startsAt": starts_at_iso,
        "endsAt": ends_at_iso,
    }
    resp = _linear_graphql(api_key, mutation, {"input": input_fields})
    cycle = (((resp or {}).get("data") or {}).get("cycleCreate") or {}).get("cycle")
    return cycle.get("id") if cycle else None


def _add_issue_to_cycle(api_key: str, issue_uuid: str, cycle_uuid: str) -> bool:
    """Locked to a no-op under the Linear-read-only LAW (Dave ratified
    2026-05-20). This previously POSTed an issueUpdate to assign an issue to
    a Linear cycle. Linear is read-only — no automated process writes it.
    Returns False — no cycle assignment was written.
    """
    del api_key, issue_uuid, cycle_uuid  # intentionally unused — write suppressed
    logger.info("Linear-read-only LAW: cycle-assignment write suppressed")
    return False


def _cycle_name(starts_at_utc: datetime) -> str:
    starts_aest = starts_at_utc + timedelta(hours=_AEST_OFFSET_HOURS)
    return f"KEI Week of {starts_aest.strftime('%Y-%m-%d')}"


def run(force_now: bool = False, now: datetime | None = None) -> int:
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        logger.warning("LINEAR_API_KEY not set; cannot create Linear cycle")
        return 2
    team_id = os.environ.get("LINEAR_TEAM_ID", _DEFAULT_TEAM_ID)

    eligible = filter_eligible(_bd_ready())
    if not eligible:
        logger.info("no P0/P1 unblocked items with Linear refs — no cycle created")
        return 0

    if force_now:
        starts_utc = (now or datetime.now(UTC)).replace(microsecond=0)
        ends_utc = starts_utc + timedelta(days=_CYCLE_DURATION_DAYS)
    else:
        starts_utc, ends_utc = compute_target_window(now)
    starts_iso = starts_utc.isoformat().replace("+00:00", "Z")
    ends_iso = ends_utc.isoformat().replace("+00:00", "Z")

    cycle_uuid = _find_existing_cycle(api_key, team_id, starts_iso)
    if cycle_uuid:
        logger.info("idempotent reuse: existing cycle %s for startsAt=%s", cycle_uuid, starts_iso)
    else:
        cycle_uuid = _create_cycle(api_key, team_id, starts_iso, ends_iso, _cycle_name(starts_utc))
        if not cycle_uuid:
            logger.warning("cycleCreate returned no cycle — abort")
            return 0
        logger.info("created cycle %s (%s)", cycle_uuid, _cycle_name(starts_utc))

    added = skipped = failed = 0
    for _item, kei_n in eligible:
        issue_uuid = _resolve_kei_to_uuid(api_key, kei_n)
        if not issue_uuid:
            logger.warning("skip KEI-%d — could not resolve UUID", kei_n)
            skipped += 1
            continue
        if _add_issue_to_cycle(api_key, issue_uuid, cycle_uuid):
            added += 1
        else:
            failed += 1
    logger.info(
        "cycle %s populated: %d added, %d skipped, %d failed (of %d eligible)",
        cycle_uuid,
        added,
        skipped,
        failed,
        len(eligible),
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly Linear cycle from bd ready (KEI-29)")
    parser.add_argument(
        "--force-now",
        action="store_true",
        help="Create cycle starting now instead of next Monday 07:00 AEST.",
    )
    args = parser.parse_args()
    return run(force_now=args.force_now)


if __name__ == "__main__":
    sys.exit(main())
