#!/usr/bin/env python3
"""check_migration_completeness.py — CI gate for Pattern A audit finding.

Pattern A (from 2026-05-12 memory audit): a PR removes a WRITE path to some
table / file / function X but leaves READERS of X in the codebase. The
classic case caught by the audit: elliot_internal.memories had its writes
removed during a migration, but pg_stat shows 2858 seq_scans because
readers were left in place (global CLAUDE.md startup block). Same shape
hit Drevon's `messages` table — schema + writer function existed, NO
production hook invoked the writer, but `_fetch_user_messages` actively
queried it (silent zero-row reads).

This script is the runtime enforcement Pattern A demands: given a
"removed-writer target" (table name, file path, function name) it greps
the post-change source tree for residual reads and exits non-zero if any
are found. Action runner upstream extracts the targets from the PR diff.

Exit codes:
  0  no residual readers found — migration is complete
  1  residual readers found — migration is incomplete; CI fails
  2  invocation error (missing arg, unreadable path)

Usage (script-direct; the GitHub Action wraps this in a diff loop):

    scripts/check_migration_completeness.py --removed-target elliot_internal.memories
    scripts/check_migration_completeness.py --removed-target /tmp/.session_ --check-paths src,scripts,skills
    scripts/check_migration_completeness.py --removed-target foo --check-paths src --extra-grep-flag -F
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_CHECK_PATHS = ("src", "scripts", "skills")
EXCLUDE_DIRS = ("__pycache__", "node_modules", ".venv", ".git")
EXCLUDE_GLOBS = ("*.pyc",)


def _grep_for_target(target: str, check_paths: list[Path], extra_flag: str | None) -> list[str]:
    """Run grep across check_paths for `target`; return matching file:line strings.

    Uses --fixed-strings by default so target can contain regex meta-chars
    (e.g. dots, slashes in `elliot_internal.memories` or `/tmp/.session_`).
    Caller can override with --extra-grep-flag if regex matching is needed.
    """
    existing = [str(p) for p in check_paths if p.exists()]
    if not existing:
        return []

    args = ["grep", "-rn"]
    if extra_flag:
        args.append(extra_flag)
    else:
        args.append("--fixed-strings")
    for d in EXCLUDE_DIRS:
        args.extend(["--exclude-dir", d])
    for g in EXCLUDE_GLOBS:
        args.extend(["--exclude", g])
    args.append(target)
    args.extend(existing)

    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        print(
            f"[check] grep error (rc={result.returncode}): {result.stderr.strip()}", file=sys.stderr
        )
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--removed-target",
        required=True,
        help="Identifier whose writers were removed (table/path/function). "
        "Treated as a literal fixed-string by default.",
    )
    parser.add_argument(
        "--check-paths",
        default=",".join(DEFAULT_CHECK_PATHS),
        help=f"Comma-separated dirs to grep (default: {','.join(DEFAULT_CHECK_PATHS)})",
    )
    parser.add_argument(
        "--extra-grep-flag",
        default=None,
        help="Override default --fixed-strings with this grep flag (e.g. -E for regex).",
    )
    args = parser.parse_args()

    target = args.removed_target.strip()
    if not target:
        print("[check] --removed-target cannot be empty", file=sys.stderr)
        return 2

    check_paths = [Path(p.strip()) for p in args.check_paths.split(",") if p.strip()]
    hits = _grep_for_target(target, check_paths, args.extra_grep_flag)

    if not hits:
        print(
            f"[check] PASS — no residual readers found for {target!r} in {[str(p) for p in check_paths]}"
        )
        return 0

    print(f"[check] FAIL — {len(hits)} residual reader(s) found for {target!r}:")
    for line in hits:
        print(f"  {line}")
    print(
        f"\n[check] Pattern A: a writer for {target!r} was removed in this change but "
        f"{len(hits)} reader callsite(s) remain. Either restore the writer, reroute the "
        f"readers, or remove them. See docs/audits/memory_audit_2026-05-12.md."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
