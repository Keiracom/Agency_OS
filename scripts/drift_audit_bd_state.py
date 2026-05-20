#!/usr/bin/env python3
"""drift_audit_bd_state.py — KEI Agency_OS-z27a.

Cross-reference bd in_progress KEIs against merged Agency_OS PRs to surface
the systemic "in_progress remains stale after PR merge" gap.

Algorithm:
  1. List bd issues with status=in_progress (JSON via `bd list`).
  2. For each issue, extract every KEI-<N> token from title + description.
  3. For each KEI-<N>, look up merged PRs in Keiracom/Agency_OS whose title
     contains that token.
  4. Output: one record per (bd_id, kei_id, pr_number) drift triple, with the
     suggested `bd-original close` command verbatim.

Advisory only. Never auto-closes. Human ratifies + runs the close command.

Usage:
  drift_audit_bd_state.py                # human-readable plaintext
  drift_audit_bd_state.py --json         # JSONL (one finding per line)
  drift_audit_bd_state.py --dry-run      # alias for default (advisory mode);
                                         # reserved switch in case --execute
                                         # is ever added (intentionally absent
                                         # for now — close is human-only)

Exit codes:
  0  success (zero or more findings)
  2  `bd` or `gh` CLI not available / errored
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import subprocess
import sys
from typing import Any

logger = logging.getLogger("drift_audit_bd_state")

KEI_RE = re.compile(r"\bKEI-?(\d+)\b", re.IGNORECASE)
GH_REPO = "Keiracom/Agency_OS"


def _require_clis() -> None:
    """Fail-fast if either CLI is missing — clearer than subprocess exception."""
    for cli in ("bd", "gh"):
        if shutil.which(cli) is None:
            logger.error("required CLI not on PATH: %s", cli)
            sys.exit(2)


def list_in_progress(
    runner=subprocess.run,
) -> list[dict[str, Any]]:
    """Return bd issues currently in_progress as a list of dicts.

    `runner` is injectable for tests (no subprocess in unit tests).
    """
    result = runner(
        ["bd", "list", "--status=in_progress", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout or "[]")


def extract_kei_ids(text: str) -> set[str]:
    """Return normalised KEI-<N> tokens (uppercase) found in text."""
    return {f"KEI-{m.group(1)}" for m in KEI_RE.finditer(text or "")}


def fetch_merged_prs(
    kei_id: str,
    runner=subprocess.run,
) -> list[dict[str, Any]]:
    """gh pr list merged + matching kei_id in title. Empty list on no match."""
    result = runner(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            GH_REPO,
            "--state",
            "merged",
            "--search",
            f"in:title {kei_id}",
            "--json",
            "number,title,mergedAt",
            "--limit",
            "5",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout or "[]")


def primary_kei_id(issue: dict[str, Any]) -> str | None:
    """Return the issue's canonical KEI-ID.

    Precedence (definitive → heuristic):
      1. `external_ref` Linear URL  — `.../issue/KEI-225` is the canonical mapping.
      2. Leading KEI-<N> token in the title — works for bd-only issues with
         no Linear mirror, and for prefixes like `[ATLAS] fix(kei20):`.

    Returns None when neither source yields a KEI-ID. The description is NOT
    scanned: cross-references in descriptions trigger false positives (an
    issue that *mentions* KEI-X is not delivered by a PR addressing KEI-X).
    """
    ext = issue.get("external_ref") or ""
    if (m := KEI_RE.search(ext)) is not None:
        return f"KEI-{m.group(1)}"
    title = issue.get("title") or ""
    if (m := KEI_RE.search(title)) is not None:
        return f"KEI-{m.group(1)}"
    return None


def pr_delivers_kei(pr_title: str, kei_id: str) -> bool:
    """True iff the PR title puts ``kei_id`` inside a conventional-commit
    scope — e.g. ``feat(kei20):``, ``fix(kei221a):`` — not merely a passing
    cross-reference like ``feat(kei92): … KEI-130 idle-loop fix``.

    The trailing negative lookahead `(?![0-9a-z])` prevents KEI-22 matching
    a kei221 PR via prefix bleed.
    """
    n = kei_id.split("-", 1)[1]  # "94" from "KEI-94", "221a" from "KEI-221a"
    pattern = re.compile(rf"\(kei-?{re.escape(n)}(?![0-9a-z])", re.IGNORECASE)
    return bool(pattern.search(pr_title or ""))


def audit(
    list_fn=list_in_progress,
    pr_fn=fetch_merged_prs,
) -> list[dict[str, Any]]:
    """Run a full pass. Returns one finding per drift (bd_id → PR) match.

    Dependencies injected for tests.
    """
    findings: list[dict[str, Any]] = []
    for issue in list_fn():
        kei_id = primary_kei_id(issue)
        if kei_id is None:
            continue
        for pr in pr_fn(kei_id):
            if not pr_delivers_kei(pr.get("title") or "", kei_id):
                continue
            findings.append(
                {
                    "bd_id": issue.get("id"),
                    "bd_title": issue.get("title"),
                    "kei_id": kei_id,
                    "pr_number": pr.get("number"),
                    "pr_title": pr.get("title"),
                    "merged_at": pr.get("mergedAt"),
                }
            )
            break
    return findings


def format_plaintext(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "drift_audit_bd_state: 0 drift candidates — bd in_progress is clean.\n"
    lines = [f"drift_audit_bd_state: {len(findings)} drift candidate(s):", ""]
    for f in findings:
        lines.append(
            f"  {f['bd_id']} ({f['kei_id']}) → PR #{f['pr_number']} merged {f['merged_at']}"
        )
        lines.append(f"    bd: {f['bd_title']}")
        lines.append(f"    pr: {f['pr_title']}")
        lines.append(
            f"    → bd-original close {f['bd_id']} "
            f'-r "PR #{f["pr_number"]} merged {f["merged_at"]} — '
            f'surfaced by drift_audit_bd_state (z27a)"'
        )
        lines.append("")
    return "\n".join(lines)


def format_jsonl(findings: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(f) + "\n" for f in findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="emit JSONL")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="alias for default behaviour (advisory only — no closes)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _require_clis()
    findings = audit()
    output = format_jsonl(findings) if args.json else format_plaintext(findings)
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
