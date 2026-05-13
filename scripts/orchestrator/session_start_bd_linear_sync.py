#!/usr/bin/env python3
"""session_start_bd_linear_sync.py — KEI-22 D1.

Wraps `bd linear sync --pull-if-stale` for invocation from the SessionStart
hook chain. Per Dave CEO directive ts ~1778653940: every agent boot must
reconcile bd ↔ Linear so the board reflects truth before any dispatch
decision (root cause of today's bad dispatch: KEI-27 / KEI-28 showed Todo
in Linear when both were already Done).

Operation:
    bd linear sync --pull-if-stale --threshold 20m
        Native staleness gate (20-minute threshold + 5-minute debounce per
        Max empirical probe ts ~1778622767). Won't spin if data fresh.

Hook-chain ordering (per dispatch literal, post-#813 KEI-31):
    audit → context_compiler → cognee_recall --on-wake → bd_task_state
        → session_uuid_resume → bd_sync_linear (THIS SCRIPT) → anti_amnesia_capsule

Best-effort: bd sync failures must NEVER block session start. Failures
are logged to /home/elliotbot/clawd/logs/bd-linear-sync.log + the script
exits 0 either way.

CLI:
    --threshold 20m    bd staleness threshold (default per dispatch)
    --bd /path/to/bd   bd binary path (default 'bd' on PATH)
    --dry-run          print the planned command, don't execute
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_LOG = Path("/home/elliotbot/clawd/logs/bd-linear-sync.log")


def _log(msg: str, log_path: Path = DEFAULT_LOG) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")
    except OSError:
        pass


def run(
    *,
    threshold: str = "20m",
    bd_bin: str = "bd",
    dry_run: bool = False,
    log_path: Path = DEFAULT_LOG,
    runner=None,
) -> dict:
    """Pure-Python entry. Returns {'ok': bool, 'reason': str, 'exit_code': int}."""
    if not shutil.which(bd_bin) and bd_bin == "bd":
        _log(
            f"bd_unavailable: bd binary not on PATH (callsign={os.environ.get('CALLSIGN', '-')})",
            log_path,
        )
        return {"ok": False, "reason": "bd_unavailable", "exit_code": 0}

    cmd = [bd_bin, "linear", "sync", "--pull-if-stale", "--threshold", threshold]
    if dry_run:
        _log(f"dry_run: would exec {' '.join(cmd)}", log_path)
        return {"ok": True, "reason": "dry_run", "exit_code": 0}

    invoke = runner or (lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=30))
    try:
        result = invoke()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        _log(f"sync_failed_swallowed: {exc}", log_path)
        return {"ok": False, "reason": f"exception: {exc}", "exit_code": 0}

    if result.returncode != 0:
        _log(
            f"sync_nonzero_swallowed rc={result.returncode} stderr={result.stderr[:200]}",
            log_path,
        )
        return {
            "ok": False,
            "reason": f"bd_rc_{result.returncode}",
            "exit_code": 0,
        }

    _log(f"sync_ok stdout={result.stdout[:200]}", log_path)
    return {"ok": True, "reason": "synced", "exit_code": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", default="20m")
    parser.add_argument("--bd", default="bd")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    result = run(threshold=args.threshold, bd_bin=args.bd, dry_run=args.dry_run)
    print(f"[session_start_bd_linear_sync] {result['reason']}")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
