#!/usr/bin/env python3
"""bd_status_to_linear_immediate.py — KEI-22 D3.

Per Dave CEO directive ts ~1778653940: bd status changes must push to
Linear *immediately* (not on the next 20-minute pull cycle). Wraps the
native `bd linear sync --push` (reuses canonical state-map). PR #807
reverted a bespoke bd_to_linear.py in favour of this native — we
reconstruct minimally as a thin push wrapper plus a 60-second systemd
timer cadence so any bd state change reaches Linear within ~60 seconds.

Operation:
    bd linear sync --push
        Native push: bd → Linear. Default conflict resolution is
        newer-timestamp-wins; we keep that default (--prefer-local would
        clobber Linear-side human edits).

Best-effort: a push failure (Linear API outage, rate-limit, etc.) MUST
NOT raise — the next 60s tick retries. We log to
/home/elliotbot/clawd/logs/bd-linear-push.log and exit 0 either way.

Run via timer (infra/alerts/agency-os-bd-linear-push.{service,timer},
OnUnitActiveSec=60s).

CLI:
    --bd /path/to/bd   bd binary path (default 'bd' on PATH)
    --dry-run          plan only, don't execute
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_LOG = Path("/home/elliotbot/clawd/logs/bd-linear-push.log")


def _log(msg: str, log_path: Path = DEFAULT_LOG) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")
    except OSError:
        pass


def run(
    *,
    bd_bin: str = "bd",
    dry_run: bool = False,
    log_path: Path = DEFAULT_LOG,
    runner=None,
) -> dict:
    """Pure-Python entry. Always returns exit_code=0 (best-effort)."""
    if not shutil.which(bd_bin) and bd_bin == "bd":
        _log(f"bd_unavailable callsign={os.environ.get('CALLSIGN', '-')}", log_path)
        return {"ok": False, "reason": "bd_unavailable", "exit_code": 0}

    cmd = [bd_bin, "linear", "sync", "--push"]
    if dry_run:
        _log(f"dry_run: would exec {' '.join(cmd)}", log_path)
        return {"ok": True, "reason": "dry_run", "exit_code": 0}

    invoke = runner or (lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=45))
    try:
        result = invoke()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        _log(f"push_failed_swallowed: {exc}", log_path)
        return {"ok": False, "reason": f"exception: {exc}", "exit_code": 0}

    if result.returncode != 0:
        _log(
            f"push_nonzero_swallowed rc={result.returncode} stderr={result.stderr[:200]}",
            log_path,
        )
        return {"ok": False, "reason": f"bd_rc_{result.returncode}", "exit_code": 0}

    _log(f"push_ok stdout={result.stdout[:200]}", log_path)
    return {"ok": True, "reason": "pushed", "exit_code": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bd", default="bd")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    result = run(bd_bin=args.bd, dry_run=args.dry_run)
    print(f"[bd_status_to_linear_immediate] {result['reason']}")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
