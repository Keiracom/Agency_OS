#!/usr/bin/env python3
"""check_product_test_allowlist.py — Phase 1.2.5 bundle artefact 7 enforcer.

CI guard for the PRODUCT REPO test matrix. Walks tests/** and fails (exit 1)
if any test file is NOT matched by an entry in config/product_repo_test_allowlist.txt.

WHY:
Per ceo:agency_os_keiracom_separation_v1 sign-off item 2 — the product repo
ships a STRIPPED test matrix until first paying customer (Dave-ratified
2026-05-24). Discipline: every test in the product repo is explicitly
enumerated; nothing carried over implicitly from the fleet repo.

ALGORITHM:
  1. Read allowlist (skip blank lines + # comments). Each non-comment line
     is a path or glob (no `**`).
  2. Walk tests/** for *.py files (skipping __init__.py and __pycache__).
  3. For each test file, check if any allowlist entry matches via fnmatch.
  4. If unmatched: print to stderr + collect for the final exit code.
  5. Exit 0 if zero unmatched, 1 otherwise.

USAGE:
    python3 scripts/ci/check_product_test_allowlist.py
    python3 scripts/ci/check_product_test_allowlist.py --allowlist <path>
    python3 scripts/ci/check_product_test_allowlist.py --report  # show counts only

LOCAL VERIFICATION expected output (in fleet repo today, before any migration):
    most tests/** files are NOT product-repo-survivors — that is the design.
    The script prints them to stderr as "rejected — not in product allowlist"
    + exits 1. The product repo CI invocation (post-migration) walks a
    tests/** tree that's already pruned to allowlist members; exit 0 then.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ALLOWLIST = REPO_ROOT / "config" / "product_repo_test_allowlist.txt"
DEFAULT_TESTS_ROOT = REPO_ROOT / "tests"


def load_allowlist(path: Path) -> list[str]:
    """Parse the allowlist file. Returns list of path patterns (sorted, deduped)."""
    if not path.is_file():
        sys.stderr.write(f"ERROR: allowlist not found: {path}\n")
        sys.exit(2)
    patterns: set[str] = set()
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "**" in line:
            sys.stderr.write(
                f"ERROR: '**' recursive glob disallowed in allowlist (line: {line!r})\n"
                "Enumerate paths explicitly or use a single-level glob like dir/*.py\n"
            )
            sys.exit(2)
        patterns.add(line)
    return sorted(patterns)


def walk_tests(tests_root: Path) -> list[Path]:
    """All test files under tests_root, relative paths from tests_root's parent.

    Bug-fix 2026-05-24 (caught by negative-path test sweep): previously used
    REPO_ROOT as the relativisation base, which broke when --tests-root pointed
    outside the repo (e.g. a tmp_path test fixture or a separate worktree).
    Using tests_root.parent makes the path display + allowlist matching work
    consistently in both cases:
      - default: tests_root = REPO_ROOT/tests → parent = REPO_ROOT → "tests/foo.py"
      - test:    tests_root = /tmp/.../tests → parent = /tmp/... → "tests/foo.py"
    Allowlist patterns reference 'tests/...' either way, so matching is stable.
    """
    if not tests_root.is_dir():
        return []
    base = tests_root.parent
    files: list[Path] = []
    for p in tests_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        if p.name == "__init__.py":
            continue
        files.append(p.relative_to(base))
    return sorted(files)


def matches_any(path: Path, patterns: list[str]) -> bool:
    """True if path matches at least one allowlist pattern via fnmatch."""
    s = str(path)
    return any(fnmatch.fnmatch(s, pat) for pat in patterns)


def _print_report(matched: list[Path], unmatched: list[Path], patterns: list[str]) -> None:
    """Render --report-mode diagnostic to stderr (extracted from main per Max
    HOLD on PR #1118 — Sonar S3776 cognitive-complexity refactor)."""
    sys.stderr.write(f"  allowlist patterns: {len(patterns)}\n")
    for f in matched[:10]:
        sys.stderr.write(f"  matched  {f}\n")
    if len(matched) > 10:
        sys.stderr.write(f"  ... + {len(matched) - 10} more matched\n")
    for f in unmatched[:10]:
        sys.stderr.write(f"  rejected {f}\n")
    if len(unmatched) > 10:
        sys.stderr.write(f"  ... + {len(unmatched) - 10} more rejected\n")


def _print_rejections(unmatched: list[Path]) -> None:
    """Render enforcement-mode rejection block to stderr (extracted from main)."""
    sys.stderr.write(
        "REJECT: the following test files are not in the product-repo allowlist. "
        "Either add their path to config/product_repo_test_allowlist.txt (with "
        "review of whether they actually belong in the product repo CI matrix) "
        "OR move them to the fleet/archive repo before this check runs.\n"
    )
    for f in unmatched:
        sys.stderr.write(f"  rejected — not in product allowlist: {f}\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--allowlist",
        type=Path,
        default=DEFAULT_ALLOWLIST,
        help="Path to allowlist file (default: config/product_repo_test_allowlist.txt)",
    )
    p.add_argument(
        "--tests-root",
        type=Path,
        default=DEFAULT_TESTS_ROOT,
        help="Path to tests root (default: tests/)",
    )
    p.add_argument(
        "--report",
        action="store_true",
        help="Print counts (matched / unmatched / total) and exit 0 — no enforcement",
    )
    args = p.parse_args(argv)

    patterns = load_allowlist(args.allowlist)
    files = walk_tests(args.tests_root)

    matched: list[Path] = []
    unmatched: list[Path] = []
    for f in files:
        (matched if matches_any(f, patterns) else unmatched).append(f)

    total = len(files)
    pct_matched = (100.0 * len(matched) / total) if total else 0.0
    sys.stderr.write(
        f"product-repo allowlist: {len(matched)} / {total} test files matched "
        f"({pct_matched:.1f}%); {len(unmatched)} would be rejected.\n"
    )

    if args.report:
        _print_report(matched, unmatched, patterns)
        return 0

    if unmatched:
        _print_rejections(unmatched)
        return 1

    sys.stderr.write("OK: every tests/** file is in the product allowlist.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
