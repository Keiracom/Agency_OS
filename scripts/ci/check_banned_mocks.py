"""check_banned_mocks.py — refuse mocks anywhere under tests/proof_tier/**.

Per gate_roadmap.spike_real_deps_proof: the proof tier MUST exercise real
dependencies (Testcontainers Postgres/Weaviate/NATS). A pytest-only
attestation that imports unittest.mock / MagicMock / AsyncMock / Mock /
mocker / patch defeats the gate (cf. 2026-06-03 product_proof_enforcement
shape-only flip). This script is the CI enforcer.

Usage:
    python scripts/ci/check_banned_mocks.py [--root tests/proof_tier]

Exit 0: clean (no banned imports/usages).
Exit 1: found banned items; prints the offending line per file.

Banned tokens (case-sensitive, exact match where possible):
  - unittest.mock        (full module)
  - MagicMock            (class name)
  - AsyncMock            (class name)
  - mock.patch / patch(  (decorator/context-manager)
  - pytest-mock fixtures: mocker.

The conftest.py at tests/proof_tier is exempt for `import pytest` etc.
This script scans for the BANNED tokens in any .py under the root.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_BANNED_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bfrom\s+unittest\.mock\b"), "unittest.mock import"),
    (re.compile(r"\bimport\s+unittest\.mock\b"), "unittest.mock import"),
    (re.compile(r"\bimport\s+mock\b"), "mock package import"),
    (re.compile(r"\bfrom\s+mock\b"), "mock package import"),
    (re.compile(r"\bMagicMock\b"), "MagicMock usage"),
    (re.compile(r"\bAsyncMock\b"), "AsyncMock usage"),
    (re.compile(r"\bmocker\.(patch|spy|stub|MagicMock)\b"), "pytest-mock mocker usage"),
    (re.compile(r"\b@patch\b"), "@patch decorator"),
    (re.compile(r"\bmock\.patch\b"), "mock.patch usage"),
)


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return [(line_no, snippet, reason)] for every banned hit."""
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"WARN: cannot read {path}: {exc}", file=sys.stderr)
        return hits
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue  # plain comment line — not enforced (e.g. README citations)
        for pat, reason in _BANNED_PATTERNS:
            if pat.search(line):
                hits.append((line_no, line.rstrip(), reason))
                break
    return hits


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--root",
        default="tests/proof_tier",
        help="Directory to scan recursively (default: tests/proof_tier)",
    )
    args = p.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"OK: {root} does not exist — nothing to scan.")
        return 0

    total = 0
    for py in sorted(root.rglob("*.py")):
        hits = scan_file(py)
        if hits:
            for line_no, snippet, reason in hits:
                print(f"BANNED ({reason}): {py}:{line_no}: {snippet}")
                total += 1

    if total:
        print(f"\nFAIL: {total} banned-mock hit(s) under {root}/.")
        print("Proof tier requires real dependencies. Use Testcontainers, not mocks.")
        return 1
    print(f"OK: 0 banned-mock hits under {root}/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
