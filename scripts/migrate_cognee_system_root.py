#!/usr/bin/env python3
"""migrate_cognee_system_root.py — Agency_OS-5vu: relocate Cognee .cognee_system
tree from venv-resident to stable storage.

Problem: Cognee's default base_config.system_root_directory falls back to
`.cognee_system/` under the installed package directory (i.e. inside the venv).
`pip install --upgrade cognee` wipes this — including 1.6 GB of Lance vector
data + the Ladybug graph + the SQLite cognee_db that hold Phase 1 ingest
(~4332 nodes / 6486 edges per cognee-recall skill).

Fix shape: set `SYSTEM_ROOT_DIRECTORY=<stable-path>` in .env, then move
the existing tree to that path. Cognee's Pydantic BaseSettings picks up
the env var on next process start (cognee/base_config.py:13).

Execution gate (Max CRITICAL CORRECTION ts ~1778653100): cp -a + env-flip
BLOCKED while Stream 2 (or any other cognify run) is active. This script
refuses to execute when any cognee ingest process is detected.

Usage:
    python3 scripts/migrate_cognee_system_root.py --dry-run
    python3 scripts/migrate_cognee_system_root.py --execute

--dry-run: prints plan + safety checks, makes no changes.
--execute: requires explicit flag, runs cp -a then verifies size match.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_STABLE_PATH = Path("/home/elliotbot/.cognee_system")
COGNEE_INGEST_PATTERNS: tuple[str, ...] = (
    r"cognee_ingest",
    r"pipeline_runner",
    r"cognify",
)
_COGNEE_RE = re.compile("|".join(COGNEE_INGEST_PATTERNS), re.IGNORECASE)


def _venv_cognee_system_root() -> Path | None:
    """Return current venv-resident .cognee_system path, or None if cognee not importable."""
    try:
        import cognee  # type: ignore[import-untyped]
    except ImportError:
        return None
    cognee_dir = Path(cognee.__file__).resolve().parent
    candidate = cognee_dir / ".cognee_system"
    return candidate if candidate.exists() else None


def _detect_active_cognee_processes() -> list[str]:
    """Return command-lines of any running cognee ingest/cognify processes.
    Returns [] if clean to migrate. Returns non-empty list = refuse migration.
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["/usr/bin/ps", "-ef"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    matches = []
    for line in result.stdout.splitlines():
        if _COGNEE_RE.search(line) and "migrate_cognee_system_root" not in line:
            matches.append(line.strip())
    return matches


def _dir_size_bytes(path: Path) -> int:
    """Recursive size of a directory in bytes."""
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def plan(src: Path, dst: Path) -> dict:
    """Return a migration plan + safety status dict."""
    return {
        "src": str(src),
        "dst": str(dst),
        "src_exists": src.exists(),
        "dst_exists": dst.exists(),
        "src_size_bytes": _dir_size_bytes(src) if src.exists() else 0,
        "active_cognee_processes": _detect_active_cognee_processes(),
    }


def print_plan(p: dict) -> None:
    print(f"Source: {p['src']}  (exists={p['src_exists']}, size={p['src_size_bytes']:,} bytes)")
    print(f"Target: {p['dst']}  (exists={p['dst_exists']})")
    active = p["active_cognee_processes"]
    if active:
        print(f"\nREFUSE: {len(active)} active cognee process(es) detected:")
        for line in active:
            print(f"  {line}")
        print("\nMigration BLOCKED. Wait until all cognee ingest/cognify processes finish.")
    else:
        print("\nNo active cognee processes — migration would be safe NOW.")
    print("\nPost-migration manual step:")
    print(f"  Add to /home/elliotbot/.config/agency-os/.env:  SYSTEM_ROOT_DIRECTORY={p['dst']}")


def execute(src: Path, dst: Path) -> int:
    """Run the migration. Returns 0 on success, non-zero on failure."""
    active = _detect_active_cognee_processes()
    if active:
        print("REFUSE: active cognee process(es) — migration blocked.", file=sys.stderr)
        for line in active:
            print(f"  {line}", file=sys.stderr)
        return 2
    if not src.exists():
        print(f"REFUSE: source path does not exist: {src}", file=sys.stderr)
        return 3
    if dst.exists():
        print(f"REFUSE: target path already exists: {dst} — remove it first.", file=sys.stderr)
        return 4
    src_size = _dir_size_bytes(src)
    print(f"Copying {src} → {dst}  ({src_size:,} bytes)...")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, symlinks=True)
    dst_size = _dir_size_bytes(dst)
    if dst_size != src_size:
        print(f"FAIL: post-copy size mismatch — src={src_size:,} dst={dst_size:,}", file=sys.stderr)
        return 5
    print(
        f"OK: {dst_size:,} bytes copied. Source preserved at {src} (delete manually after verify)."
    )
    print(f"\nNEXT: add SYSTEM_ROOT_DIRECTORY={dst} to /home/elliotbot/.config/agency-os/.env")
    print("THEN: restart any Cognee-using services + smoke-test cognee_recall.py.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Cognee .cognee_system tree out of venv.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print plan + safety check, make no changes."
    )
    parser.add_argument("--execute", action="store_true", help="Run cp -a + verify.")
    parser.add_argument(
        "--src", type=Path, default=None, help="Source path (default: auto-detect venv-resident)."
    )
    parser.add_argument(
        "--dst",
        type=Path,
        default=DEFAULT_STABLE_PATH,
        help=f"Target path (default: {DEFAULT_STABLE_PATH}).",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.error("must specify --dry-run or --execute")
    if args.dry_run and args.execute:
        parser.error("--dry-run and --execute are mutually exclusive")

    src = args.src or _venv_cognee_system_root()
    if src is None:
        print(
            "ERROR: could not auto-detect venv-resident .cognee_system path. Pass --src.",
            file=sys.stderr,
        )
        return 1
    dst = args.dst

    p = plan(src, dst)
    print_plan(p)

    if args.dry_run:
        return 0
    return execute(src, dst)


if __name__ == "__main__":
    raise SystemExit(main())
