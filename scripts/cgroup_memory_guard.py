"""
P11 — cgroup memory guard for sub-agent containers.

Polls the container's cgroup memory accounting (v2 first, v1 fallback)
and reacts to two thresholds:

  warn_pct (default 80)  → log a structured WARN line so deploys can
                            alert on it. No process action.
  kill_pct (default 95)  → SIGTERM every registered sub-agent PID
                            (then SIGKILL after a grace period) so the
                            kernel OOM killer never has to choose for
                            us — uncontrolled OOM tends to take the
                            *parent* with the children.

Usage:
    python3 scripts/cgroup_memory_guard.py                      # foreground, prints status
    python3 scripts/cgroup_memory_guard.py --once               # one read+report+exit
    python3 scripts/cgroup_memory_guard.py --interval 5         # poll every 5s
    python3 scripts/cgroup_memory_guard.py --pid-dir /tmp/agents

Per-agent overrides (env):
    AGENT_MEMORY_LIMIT_MB__BUILD_2=2048
    AGENT_MEMORY_LIMIT_MB__RESEARCH_1=512
    ...
The override is informational — actual enforcement happens via the
cgroup limit set by the container runtime (Docker `--memory`, Railway
service memory ceiling). The guard reads the cgroup-reported limit and
treats env overrides as a hint for richer logging only.

Public surface (importable for tests):
    read_cgroup_memory()         -> CgroupReading
    classify_pressure(usage,
                      limit,
                      warn_pct,
                      kill_pct)  -> "ok" | "warn" | "kill"
    list_agent_pids(pid_dir)     -> list[int]
    terminate_pids(pids,
                   grace_seconds) -> int   (count actually signalled)
    parse_agent_overrides(env)   -> dict[str, int]   MB per agent_type

Exit codes: 0 normal · 2 cgroup unreadable · 3 invalid CLI args.

The module is pure-Python, depends only on stdlib, and never raises
on read errors — unreadable cgroup files yield CgroupReading with
available=False so the caller can degrade gracefully.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────
CGROUP_V2_USAGE = "/sys/fs/cgroup/memory.current"
CGROUP_V2_MAX = "/sys/fs/cgroup/memory.max"
CGROUP_V1_USAGE = "/sys/fs/cgroup/memory/memory.usage_in_bytes"
CGROUP_V1_LIMIT = "/sys/fs/cgroup/memory/memory.limit_in_bytes"

# v1 reports a sentinel "no limit" as a giant int (LONG_MAX rounded by page
# size). Anything above this is treated as "unlimited" for our purposes.
_V1_UNLIMITED_FLOOR = 1 << 62

DEFAULT_WARN_PCT = 80.0
DEFAULT_KILL_PCT = 95.0
DEFAULT_INTERVAL = 10.0  # seconds between polls in daemon mode
DEFAULT_GRACE = 5.0  # seconds between SIGTERM and SIGKILL

ENV_PREFIX = "AGENT_MEMORY_LIMIT_MB__"

logger = logging.getLogger("cgroup_memory_guard")


# ── Reading the cgroup ────────────────────────────────────────────────────


@dataclass
class CgroupReading:
    """Snapshot of memory accounting at a point in time."""

    available: bool
    version: str  # "v2" | "v1" | "none"
    usage_bytes: int  # 0 when unavailable
    limit_bytes: int  # 0 when unlimited / unavailable
    source: str  # filesystem path that was read

    @property
    def usage_pct(self) -> float:
        if not self.limit_bytes:
            return 0.0
        return 100.0 * self.usage_bytes / self.limit_bytes


def _read_int(path: str) -> int | None:
    try:
        with open(path) as fh:
            txt = fh.read().strip()
    except OSError:
        return None
    if txt == "max":  # cgroup v2 sentinel
        return 0
    try:
        return int(txt)
    except ValueError:
        return None


def read_cgroup_memory(
    *,
    v2_usage_path: str = CGROUP_V2_USAGE,
    v2_max_path: str = CGROUP_V2_MAX,
    v1_usage_path: str = CGROUP_V1_USAGE,
    v1_limit_path: str = CGROUP_V1_LIMIT,
) -> CgroupReading:
    """Read current memory usage + limit from the kernel.

    Tries cgroup v2 (the default on modern hosts and Railway) first,
    falls back to v1, then reports unavailable. NEVER raises.
    """
    usage = _read_int(v2_usage_path)
    limit = _read_int(v2_max_path)
    if usage is not None:
        return CgroupReading(
            available=True,
            version="v2",
            usage_bytes=usage,
            limit_bytes=(limit or 0),
            source=v2_usage_path,
        )
    usage = _read_int(v1_usage_path)
    limit = _read_int(v1_limit_path)
    if usage is not None:
        if limit is not None and limit >= _V1_UNLIMITED_FLOOR:
            limit = 0
        return CgroupReading(
            available=True,
            version="v1",
            usage_bytes=usage,
            limit_bytes=(limit or 0),
            source=v1_usage_path,
        )
    return CgroupReading(
        available=False,
        version="none",
        usage_bytes=0,
        limit_bytes=0,
        source="",
    )


# ── Classifying pressure ──────────────────────────────────────────────────


def classify_pressure(
    usage_bytes: int,
    limit_bytes: int,
    warn_pct: float = DEFAULT_WARN_PCT,
    kill_pct: float = DEFAULT_KILL_PCT,
) -> str:
    """Return one of "ok" | "warn" | "kill" given a usage/limit pair.

    Unlimited (limit_bytes == 0) → always "ok": there is no ceiling we
    can be near. Negative/garbage inputs also return "ok" rather than
    accidentally killing things on a bad read.
    """
    if limit_bytes <= 0 or usage_bytes < 0:
        return "ok"
    pct = 100.0 * usage_bytes / limit_bytes
    if pct >= kill_pct:
        return "kill"
    if pct >= warn_pct:
        return "warn"
    return "ok"


# ── Sub-agent PID registry ────────────────────────────────────────────────
# Convention: each spawned sub-agent writes its PID to a file under
# `pid_dir`, named `<agent_type>.<pid>.pid`. The dispatcher already
# does this for the OpenClaw fork-context flow; the guard just reads
# whatever it finds and never writes.


def list_agent_pids(pid_dir: str | os.PathLike) -> list[int]:
    """Enumerate live sub-agent PIDs from a pid directory.

    Stale files (process gone) are ignored. Never raises on missing
    directory — returns an empty list.
    """
    p = Path(pid_dir)
    if not p.is_dir():
        return []
    pids: list[int] = []
    for entry in p.iterdir():
        if entry.suffix != ".pid" or not entry.is_file():
            continue
        try:
            txt = entry.read_text().strip()
            pid = int(txt) if txt else int(entry.stem.split(".")[-1])
        except (OSError, ValueError):
            continue
        if pid <= 1:  # never signal init
            continue
        if _pid_alive(pid):
            pids.append(pid)
    return pids


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but we can't signal — count it
    return True


def terminate_pids(
    pids: list[int],
    grace_seconds: float = DEFAULT_GRACE,
    *,
    sleeper=time.sleep,
    killer=os.kill,
) -> int:
    """SIGTERM each pid; after `grace_seconds`, SIGKILL any survivors.

    Returns the number of pids that actually received a signal. The
    `sleeper` and `killer` injection points exist so tests can drive
    the function deterministically without real sleeps or signals.
    """
    if not pids:
        return 0
    signalled = 0
    for pid in pids:
        try:
            killer(pid, signal.SIGTERM)
            signalled += 1
        except (ProcessLookupError, PermissionError):
            continue
    if grace_seconds > 0:
        sleeper(grace_seconds)
    for pid in pids:
        if _pid_alive(pid):
            try:
                killer(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                continue
    return signalled


# ── Per-agent overrides ───────────────────────────────────────────────────


def parse_agent_overrides(env: dict[str, str]) -> dict[str, int]:
    """Pull AGENT_MEMORY_LIMIT_MB__<AGENT_TYPE> overrides from env.

    Underscores in the env-var suffix are converted to dashes so
    "BUILD_2" maps back to the canonical "build-2" agent_type. Bad
    integers are silently dropped — the env is a hint, not a contract.
    """
    out: dict[str, int] = {}
    for key, val in env.items():
        if not key.startswith(ENV_PREFIX):
            continue
        try:
            mb = int(val)
        except (TypeError, ValueError):
            continue
        if mb <= 0:
            continue
        agent = key[len(ENV_PREFIX) :].lower().replace("_", "-")
        if agent:
            out[agent] = mb
    return out


# ── Top-level loop ────────────────────────────────────────────────────────


def _emit(reading: CgroupReading, status: str, **extra) -> None:
    logger.info(
        json.dumps(
            {
                "event": "cgroup_memory_guard",
                "status": status,
                "version": reading.version,
                "usage_bytes": reading.usage_bytes,
                "limit_bytes": reading.limit_bytes,
                "usage_pct": round(reading.usage_pct, 2),
                **extra,
            }
        )
    )


def run_once(
    *,
    pid_dir: str,
    warn_pct: float,
    kill_pct: float,
    grace_seconds: float,
) -> str:
    reading = read_cgroup_memory()
    if not reading.available:
        _emit(reading, "unavailable")
        return "unavailable"
    status = classify_pressure(
        reading.usage_bytes,
        reading.limit_bytes,
        warn_pct,
        kill_pct,
    )
    if status == "kill":
        pids = list_agent_pids(pid_dir)
        signalled = terminate_pids(pids, grace_seconds=grace_seconds)
        _emit(reading, status, signalled=signalled, pid_count=len(pids))
    else:
        _emit(reading, status)
    return status


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P11 cgroup memory guard.")
    ap.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL,
        help="Polling interval in seconds (default 10).",
    )
    ap.add_argument(
        "--warn-pct",
        type=float,
        default=DEFAULT_WARN_PCT,
        help="Warning threshold percentage (default 80).",
    )
    ap.add_argument(
        "--kill-pct",
        type=float,
        default=DEFAULT_KILL_PCT,
        help="Kill threshold percentage (default 95).",
    )
    ap.add_argument(
        "--pid-dir", default="/tmp/agency_os/agents", help="Directory containing agent .pid files."
    )
    ap.add_argument(
        "--grace",
        type=float,
        default=DEFAULT_GRACE,
        help="SIGTERM→SIGKILL grace window in seconds (default 5).",
    )
    ap.add_argument("--once", action="store_true", help="Read + report + exit (no loop).")
    args = ap.parse_args(argv)

    if args.warn_pct >= args.kill_pct or args.kill_pct > 100:
        print("warn-pct must be < kill-pct ≤ 100", file=sys.stderr)
        return 3

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.once:
        status = run_once(
            pid_dir=args.pid_dir,
            warn_pct=args.warn_pct,
            kill_pct=args.kill_pct,
            grace_seconds=args.grace,
        )
        return 0 if status != "unavailable" else 2

    while True:
        run_once(
            pid_dir=args.pid_dir,
            warn_pct=args.warn_pct,
            kill_pct=args.kill_pct,
            grace_seconds=args.grace,
        )
        time.sleep(max(1.0, args.interval))


if __name__ == "__main__":
    sys.exit(main())
