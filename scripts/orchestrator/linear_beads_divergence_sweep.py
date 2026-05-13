#!/usr/bin/env python3
"""linear_beads_divergence_sweep.py — KEI-22 D4 weekly divergence sweep.

Per Dave CEO directive ts ~1778653940: weekly Linear ↔ Beads divergence
sweep, diff posted to #execution. Joins Linear issues to Beads issues by
external-ref (Linear URL), surfaces:

  - Linear In-Progress / Todo with NO bd row     (Linear-only)
  - bd In-Progress / Open with NO Linear row     (bd-only)
  - State mismatch (e.g. bd=closed, Linear=Todo) (divergent_state)

Best-effort: any individual API failure (Linear GraphQL down, bd CLI
missing, Slack POST 429) is logged + the sweep continues. Final summary
posted to #execution with counts + first 10 lines of each bucket.

Run via timer: infra/alerts/agency-os-linear-beads-divergence-sweep.{service,timer}
  OnCalendar = Sun 22:00 UTC (Mon 08:00 AEST — hour after KEI-29 weekly cycle).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

EXECUTION_CHANNEL = "C0B3QB0K1GQ"
LINEAR_GRAPHQL = "https://api.linear.app/graphql"
DEFAULT_LOG = Path("/home/elliotbot/clawd/logs/linear-beads-divergence-sweep.log")


def _log(msg: str, log_path: Path = DEFAULT_LOG) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")
    except OSError:
        pass


def _fetch_linear_issues(api_key: str) -> list[dict]:
    """Return list of {id, identifier, state_name, url}. [] on any failure."""
    query = (
        'query { issues(filter: {state: {type: {nin: ["completed", "canceled"]}}}, '
        "first: 250) { nodes { id identifier title state { name type } url } } }"
    )
    req = urllib.request.Request(
        LINEAR_GRAPHQL,
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        _log(f"linear_fetch_failed: {exc}")
        return []
    nodes = (((body.get("data") or {}).get("issues") or {}).get("nodes")) or []
    return [
        {
            "id": n["id"],
            "identifier": n["identifier"],
            "title": n.get("title", ""),
            "state_name": (n.get("state") or {}).get("name", "?"),
            "state_type": (n.get("state") or {}).get("type", "?"),
            "url": n.get("url", ""),
        }
        for n in nodes
    ]


def _fetch_bd_issues(bd_bin: str = "bd") -> list[dict]:
    """`bd list --json`. [] on any failure."""
    try:
        r = subprocess.run(
            [bd_bin, "list", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        _log(f"bd_fetch_failed: {exc}")
        return []
    if r.returncode != 0:
        _log(f"bd_list_nonzero rc={r.returncode}")
        return []
    try:
        data = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return []
    items = data if isinstance(data, list) else data.get("issues") or data.get("data") or []
    return [
        {
            "id": i.get("id", ""),
            "title": i.get("title", ""),
            "status": (i.get("status") or "").lower(),
            "external": i.get("external") or "",
        }
        for i in items
        if isinstance(i, dict)
    ]


def _linear_id_from_external(ext: str) -> str | None:
    """`https://linear.app/<team>/issue/KEI-22/...` → 'KEI-22'."""
    if not ext:
        return None
    parts = ext.rstrip("/").split("/")
    for i, p in enumerate(parts):
        if p.lower() == "issue" and i + 1 < len(parts):
            return parts[i + 1].split("?")[0]
    return None


def diff(linear_issues: list[dict], bd_issues: list[dict]) -> dict:
    """Return three buckets: linear_only, bd_only, divergent_state."""
    bd_by_kei: dict[str, dict] = {}
    bd_unrefd: list[dict] = []
    for b in bd_issues:
        kei = _linear_id_from_external(b.get("external", ""))
        if kei:
            bd_by_kei[kei] = b
        elif b.get("status") in ("open", "in_progress"):
            bd_unrefd.append(b)

    linear_only = [li for li in linear_issues if li["identifier"] not in bd_by_kei]

    divergent: list[dict] = []
    for li in linear_issues:
        b = bd_by_kei.get(li["identifier"])
        if not b:
            continue
        bd_closed = b["status"] in ("closed", "done")
        linear_open = li["state_type"] not in ("completed", "canceled")
        if bd_closed and linear_open:
            divergent.append(
                {
                    "kei": li["identifier"],
                    "bd_status": b["status"],
                    "linear_state": li["state_name"],
                    "linear_url": li["url"],
                }
            )

    return {
        "linear_only": linear_only,
        "bd_only": bd_unrefd,
        "divergent_state": divergent,
    }


def format_alert(buckets: dict) -> str:
    lines = [
        ":mag: *Weekly Linear ↔ Beads divergence sweep* — KEI-22 D4",
        f"  • Linear-only (open in Linear, no bd row): {len(buckets['linear_only'])}",
        f"  • bd-only (open in bd, no Linear external-ref): {len(buckets['bd_only'])}",
        f"  • State mismatch (bd closed, Linear still open): {len(buckets['divergent_state'])}",
    ]
    for label, items, fmt in (
        (
            "Linear-only",
            buckets["linear_only"][:10],
            lambda x: f"      - {x['identifier']} ({x['state_name']}) — {x['title'][:60]}",
        ),
        (
            "bd-only",
            buckets["bd_only"][:10],
            lambda x: f"      - {x['id']} ({x['status']}) — {x['title'][:60]}",
        ),
        (
            "State mismatch",
            buckets["divergent_state"][:10],
            lambda x: f"      - {x['kei']}: bd={x['bd_status']} vs Linear={x['linear_state']}",
        ),
    ):
        if items:
            lines.append(f"\n  *{label}* (first 10):")
            for it in items:
                lines.append(fmt(it))
    return "\n".join(lines)


def post_to_slack(text: str, channel: str = EXECUTION_CHANNEL) -> bool:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        _log("slack_token_missing")
        return False
    payload = json.dumps(
        {
            "channel": channel,
            "text": text,
            "username": "LinearBeadsDivergence",
            "icon_emoji": ":mag:",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read())
            return bool(body.get("ok"))
    except (OSError, json.JSONDecodeError) as exc:
        _log(f"slack_post_failed: {exc}")
        return False


def run(
    *,
    linear_fetch=None,
    bd_fetch=None,
    post_fn=None,
) -> dict:
    """Pure-Python entry. Injectable for tests."""
    api_key = os.environ.get("LINEAR_API_KEY", "")
    linear_fetch = linear_fetch or (lambda: _fetch_linear_issues(api_key))
    bd_fetch = bd_fetch or _fetch_bd_issues
    post_fn = post_fn or post_to_slack

    linear = linear_fetch()
    bd = bd_fetch()
    buckets = diff(linear, bd)
    text = format_alert(buckets)
    posted = post_fn(text)
    return {
        "linear_count": len(linear),
        "bd_count": len(bd),
        "linear_only": len(buckets["linear_only"]),
        "bd_only": len(buckets["bd_only"]),
        "divergent_state": len(buckets["divergent_state"]),
        "posted": posted,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.dry_run:
        result = run(post_fn=lambda _t: True)
    else:
        result = run()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
