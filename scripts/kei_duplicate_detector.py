#!/usr/bin/env python3
"""kei_duplicate_detector.py — KEI-30 thin wrapper over `bd find-duplicates`.

Per Elliot dispatch STEP 0 PRE-CONFIRMED ts ~1778630929 (Dave-relay):
duplicate-KEI detection at issue-create time. Empirical probe confirmed
`bd find-duplicates` is native (mechanical Jaccard default + AI mode).
This script wraps that — no bespoke similarity reimplementation
(per `feedback_empirical_probe_before_concur` lesson: vendor X DOES Y →
don't bespoke).

Flow on a newly-created Linear KEI:
    1. Caller invokes this script with the new issue's title + description
       + Linear issue id (from PR #804 webhook receiver).
    2. We run `bd find-duplicates --json --status open --threshold <T>`.
    3. For each `pair` that includes the new issue's mirrored bd id (or
       whose title-prefix matches), we surface the conflict.
    4. If `--linear-comment` and the duplicate score >= the comment
       threshold, we post a Linear comment via the existing GraphQL
       pattern flagging the existing issue inline for human review
       (auto-close is OUT of scope per dispatch).
    5. Emit structured JSON to stdout for the webhook receiver to log.

Output JSON shape (always parseable):
    {
      "duplicate_found":     bool,
      "candidate_title":     str,
      "candidate_bd_id":     str|null,
      "best_match": {
        "bd_id":             str,
        "title":             str,
        "similarity":        float,
        "linear_url":        str|null
      } | null,
      "all_matches":         [ {bd_id, title, similarity}, ...],
      "linear_comment":      "posted" | "skipped" | "failed" | "disabled",
      "reason":              "above_threshold" | "below_threshold" |
                             "no_pairs" | "bd_unavailable" | "candidate_not_in_bd"
    }

Exit codes:
    0 — duplicate-found OR clean-no-dupe (caller chooses on JSON)
    1 — bd binary missing or unexpected exception

Out of scope (per dispatch):
  - Auto-close duplicates (human review only)
  - Cross-team detection
  - Webhook receiver wiring (PR #804)

CLI:
    scripts/kei_duplicate_detector.py \
        --candidate-bd-id Agency_OS-abc123 \
        --threshold 0.85 \
        --linear-comment            # POST a Linear comment on match
        --linear-issue-id KEI-99    # the just-created Linear KEI to comment on
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from typing import Any

_BD_ID_RE = re.compile(r"^\w+-[A-Za-z0-9]+$")
_LINEAR_GRAPHQL = "https://api.linear.app/graphql"


def _bd_find_duplicates(
    bd_bin: str,
    *,
    threshold: float,
    status: str = "open",
    limit: int = 50,
) -> dict[str, Any]:
    """Return parsed JSON from `bd find-duplicates`. Empty dict on failure."""
    try:
        result = subprocess.run(
            [
                bd_bin,
                "find-duplicates",
                "--json",
                "--status",
                status,
                "--threshold",
                str(threshold),
                "--limit",
                str(limit),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def _filter_pairs_for_candidate(pairs: list[dict], candidate_bd_id: str) -> list[dict]:
    """Return pairs that involve the candidate, normalised so the OTHER
    issue is the 'match' (i.e. the existing duplicate)."""
    matches: list[dict] = []
    for p in pairs:
        a = p.get("a") or {}
        b = p.get("b") or {}
        sim = float(p.get("similarity", 0.0))
        if a.get("id") == candidate_bd_id:
            matches.append({"bd_id": b.get("id"), "title": b.get("title"), "similarity": sim})
        elif b.get("id") == candidate_bd_id:
            matches.append({"bd_id": a.get("id"), "title": a.get("title"), "similarity": sim})
    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches


def _post_linear_comment(
    *,
    linear_issue_id: str,
    body: str,
    api_key: str,
) -> bool:
    """Linear GraphQL commentCreate. Returns True on ok=true, else False.
    Best-effort: any network/JSON failure returns False without raising."""
    # Linear retirement (Dave 2026-06-03 "we don't need linear"): commentCreate
    # is suppressed by default — no mutation is POSTed. Reversible via
    # LINEAR_RETIRED=0. governance_hooks.py also blocks Linear write mutations at
    # the PreToolUse hook (defense-in-depth). Returns False (best-effort: comment
    # not posted), which all callers already tolerate.
    if os.environ.get("LINEAR_RETIRED", "1") != "0":
        return False
    query = (
        "mutation Comment($issueId: String!, $body: String!) {"
        "  commentCreate(input: {issueId: $issueId, body: $body}) {"
        "    success comment { id } } }"
    )
    payload = json.dumps(
        {"query": query, "variables": {"issueId": linear_issue_id, "body": body}}
    ).encode("utf-8")
    req = urllib.request.Request(
        _LINEAR_GRAPHQL,
        data=payload,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body_obj = json.loads(r.read())
    except (OSError, json.JSONDecodeError):
        # urllib.error.URLError subclasses OSError — single tuple entry covers both.
        return False
    return bool((body_obj.get("data") or {}).get("commentCreate", {}).get("success"))


def _format_linear_comment(best_match: dict) -> str:
    return (
        f":mag: **Possible duplicate detected** (similarity "
        f"{best_match['similarity']:.2f}).\n\n"
        f"Existing issue: **{best_match['title']}** "
        f"(`{best_match['bd_id']}`).\n\n"
        f"_Flagged for human review by KEI-30 duplicate detector. "
        f"Not auto-closed._"
    )


def run(
    *,
    candidate_bd_id: str,
    threshold: float = 0.85,
    linear_comment: bool = False,
    linear_issue_id: str | None = None,
    bd_bin: str = "bd",
    bd_fn=None,
    comment_fn=None,
) -> dict[str, Any]:
    """Pure-Python entry point. Side effects injectable for tests."""
    # Capture injection state BEFORE wrapping the default — bd availability
    # only matters when we'd actually shell out to it (no test injection).
    bd_fn_injected = bd_fn is not None
    bd_fn = bd_fn or (lambda: _bd_find_duplicates(bd_bin, threshold=threshold))

    base = {
        "duplicate_found": False,
        "candidate_title": None,
        "candidate_bd_id": candidate_bd_id,
        "best_match": None,
        "all_matches": [],
        "linear_comment": "disabled" if not linear_comment else "skipped",
        "reason": "no_pairs",
    }

    if not _BD_ID_RE.fullmatch(candidate_bd_id or ""):
        base["reason"] = "candidate_not_in_bd"
        return base

    if not bd_fn_injected and not shutil.which(bd_bin) and bd_bin == "bd":
        base["reason"] = "bd_unavailable"
        return base

    data = bd_fn()
    pairs = data.get("pairs") or []
    matches = _filter_pairs_for_candidate(pairs, candidate_bd_id)
    base["all_matches"] = matches

    if not matches:
        base["reason"] = "no_pairs"
        return base

    best = matches[0]
    base["best_match"] = best
    if best["similarity"] < threshold:
        base["reason"] = "below_threshold"
        return base

    base["duplicate_found"] = True
    base["reason"] = "above_threshold"

    if linear_comment and linear_issue_id:
        api_key = os.environ.get("LINEAR_API_KEY", "")
        body = _format_linear_comment(best)
        commenter = comment_fn or (
            lambda iid, b: _post_linear_comment(linear_issue_id=iid, body=b, api_key=api_key)
        )
        ok = commenter(linear_issue_id, body)
        base["linear_comment"] = "posted" if ok else "failed"

    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-bd-id", required=True)
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--bd", default="bd")
    parser.add_argument("--linear-comment", action="store_true")
    parser.add_argument("--linear-issue-id", default=None)
    args = parser.parse_args(argv)

    try:
        result = run(
            candidate_bd_id=args.candidate_bd_id,
            threshold=args.threshold,
            linear_comment=args.linear_comment,
            linear_issue_id=args.linear_issue_id,
            bd_bin=args.bd,
        )
    except Exception as exc:  # pragma: no cover — defensive
        print(json.dumps({"duplicate_found": False, "reason": f"exception: {exc}"}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
