#!/usr/bin/env python3
"""auto_label_kei.py — auto-apply Linear labels to KEI issues by inferred type.

KEI-28. Pattern-matches issue title/description text and applies one or more
labels from a fixed taxonomy:

    audit / pattern                          → "audit-finding"
    incident / outage / rate limit           → "pipeline-incident"
    build / feature / wire                   → "build"
    docs / runbook                           → "docs"
    research / diagnosis                     → "research"

Idempotent: labels already on the issue are not re-added. Missing labels in
the KEI team are auto-created with team-default color.

Two run modes:

  CLI backfill / one-off:
      auto_label_kei.py --issue-id KEI-28
      auto_label_kei.py --backfill-all        (every Todo / In Progress KEI)

  Importable from webhook receiver (src/api/webhooks/linear.py):
      from scripts.auto_label_kei import label_issue
      label_issue(issue_id="KEI-99", title="…", description="…")

Fail-open: any Linear API error logs to stderr and exits 0. Auto-labeling
must never block issue creation or webhook delivery.

Env: LINEAR_API_KEY (required).
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from typing import Any

import httpx

logger = logging.getLogger("auto_label_kei")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

LINEAR_API_URL = "https://api.linear.app/graphql"
KEI_TEAM_ID = "4686528f-ce77-4c2f-968b-3dc76b34d6fe"

LABEL_PATTERNS: list[tuple[str, list[str]]] = [
    ("audit-finding", ["audit", "pattern"]),
    ("pipeline-incident", ["incident", "outage", "rate limit"]),
    ("build", ["build", "feature", "wire"]),
    ("docs", ["docs", "runbook"]),
    ("research", ["research", "diagnosis"]),
]


def _api_key() -> str:
    key = os.environ.get("LINEAR_API_KEY", "")
    if not key:
        raise OSError("LINEAR_API_KEY env var is not set")
    return key


def _post(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call Linear GraphQL. Returns response JSON. Raises on HTTP error."""
    resp = httpx.post(
        LINEAR_API_URL,
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": _api_key(), "Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def infer_labels(title: str, description: str) -> list[str]:
    """Return the set of label names whose patterns match the text.

    Case-insensitive substring match. Stable order matching LABEL_PATTERNS.
    """
    text = f"{title or ''} {description or ''}".lower()
    matched: list[str] = []
    for label_name, patterns in LABEL_PATTERNS:
        if any(re.search(rf"\b{re.escape(p)}\b", text) for p in patterns):
            matched.append(label_name)
    return matched


# Linear-read-only LAW (Dave ratified 2026-05-20): the team-label-map read,
# _create_label (issueLabelCreate) and _resolve_label_ids writer chain were
# removed — auto_label_kei no longer writes Linear in any form. Label
# inference still runs (read-only) via _issue_label_ids + infer_labels.


def _issue_label_ids(issue_id: str) -> tuple[list[str], list[str]]:
    """Return (current_label_ids, current_label_names) for an issue."""
    data = _post(
        "query($id: String!) { issue(id: $id) { labels { nodes { id name } } } }",
        {"id": issue_id},
    )
    nodes = (data.get("data") or {}).get("issue", {}).get("labels", {}).get("nodes", []) or []
    return [n["id"] for n in nodes], [n["name"] for n in nodes]


def label_issue(issue_id: str, title: str, description: str) -> dict[str, Any]:
    """Apply inferred labels to a Linear issue. Idempotent.

    Returns a small report dict for the caller / tests:
      {"issue_id": "...", "applied": [...], "skipped_already_present": [...],
       "matched_no_change": bool}
    """
    matched_names = infer_labels(title, description)
    if not matched_names:
        return {
            "issue_id": issue_id,
            "applied": [],
            "skipped_already_present": [],
            "matched_no_change": True,
        }

    current_ids, current_names = _issue_label_ids(issue_id)
    to_add_names = [n for n in matched_names if n not in current_names]
    if not to_add_names:
        return {
            "issue_id": issue_id,
            "applied": [],
            "skipped_already_present": matched_names,
            "matched_no_change": True,
        }

    # Linear-read-only LAW (Dave ratified 2026-05-20): the issueUpdate label
    # write is locked to a no-op. Linear is read-only — no automated process
    # writes it. Label inference above still runs (read-only) so callers see
    # what WOULD be applied; nothing is written to Linear.
    logger.info(
        "Linear-read-only LAW: label write suppressed for %s (would-add: %s)",
        issue_id,
        to_add_names,
    )

    return {
        "issue_id": issue_id,
        "applied": [],
        "skipped_already_present": [n for n in matched_names if n in current_names],
        "matched_no_change": False,
    }


def _backfill_all() -> int:
    """Iterate all open KEI issues and label them. Returns nonzero only on hard env error.

    Hard env errors (missing LINEAR_API_KEY, list-fetch HTTP failure) return 1 so a
    cron / CI invocation can detect total failure. Per-issue exceptions are logged
    and skipped (one bad issue doesn't abort the batch); the function returns 0
    when the batch completed at all, even if some issues failed individually.
    """
    try:
        data = _post(
            "query($teamId: String!) {"
            "  issues(filter: { team: { id: { eq: $teamId } },"
            '                   state: { type: { in: ["unstarted", "started", "backlog"] } } },'
            "         first: 250)"
            "    { nodes { id identifier title description } } }",
            {"teamId": KEI_TEAM_ID},
        )
    except (OSError, httpx.HTTPError) as exc:
        logger.warning("backfill list failed (hard env error): %s", exc)
        return 1
    nodes = (data.get("data") or {}).get("issues", {}).get("nodes", []) or []
    for n in nodes:
        try:
            rep = label_issue(n["id"], n.get("title", ""), n.get("description", "") or "")
            if rep["applied"]:
                print(f"{n['identifier']}: applied {rep['applied']}")
            elif rep["matched_no_change"]:
                print(f"{n['identifier']}: matched_no_change")
        except (OSError, httpx.HTTPError, KeyError) as exc:
            logger.warning("%s label failed: %s", n.get("identifier"), exc)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-id", help="Linear issue UUID or identifier (e.g. KEI-28)")
    parser.add_argument("--backfill-all", action="store_true", help="Label every open KEI issue")
    args = parser.parse_args(argv)

    if not args.issue_id and not args.backfill_all:
        parser.print_help(sys.stderr)
        return 0

    if args.backfill_all:
        return _backfill_all()

    try:
        data = _post(
            "query($id: String!) { issue(id: $id) { id title description } }",
            {"id": args.issue_id},
        )
        issue = (data.get("data") or {}).get("issue") or {}
        if not issue.get("id"):
            print(f"issue {args.issue_id} not found", file=sys.stderr)
            return 0
        rep = label_issue(issue["id"], issue.get("title", ""), issue.get("description") or "")
        print(rep)
    except Exception as exc:
        logger.warning("label_issue failed: %s", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
