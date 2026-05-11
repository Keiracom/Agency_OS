#!/usr/bin/env python3
"""gen_skill.py — CLI shim for src.skill_gen.generator.generate().

Usage:
    scripts/gen_skill.py \\
        --session-id <uuid> \\
        --start-ts <iso8601> \\
        --end-ts <iso8601> \\
        --directive-ref <label> \\
        [--skill-name <slug>] \\
        [--overwrite]

Internal tooling only. Does NOT touch the Agency OS pipeline. OAuth-only:
the spawned `claude` process uses your Max plan credentials, $0 incremental.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo-root on sys.path so src.skill_gen imports resolve regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.skill_gen.generator import generate  # noqa: E402


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--session-id", required=True)
    p.add_argument("--start-ts", required=True)
    p.add_argument("--end-ts", required=True)
    p.add_argument("--directive-ref", required=True)
    p.add_argument("--skill-name", default=None)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Repo root (defaults to the parent of scripts/)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    result = generate(
        repo_root=Path(args.repo_root),
        session_id=args.session_id,
        start_ts=args.start_ts,
        end_ts=args.end_ts,
        directive_ref=args.directive_ref,
        skill_name_override=args.skill_name,
        overwrite=args.overwrite,
    )
    print(f"skill_name: {result.skill_name}")
    print(f"skill_path: {result.skill_path}")
    print(f"pr_url:     {result.pr_url or '(PR creation failed or skipped)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
