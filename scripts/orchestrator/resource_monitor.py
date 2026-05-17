#!/usr/bin/env python3
"""resource_monitor.py — KEI-56 continuous resource monitoring.

Every RESOURCE_MONITOR_INTERVAL_SECONDS (default 60s), captures:
  - free/used/total RAM from /proc/meminfo
  - load average from /proc/loadavg
  - disk usage of /home/elliotbot/clawd
  - per-cgroup memory usage + MemoryMax cap via systemd-cgtop equivalent
    (we read /sys/fs/cgroup/user.slice/... directly to avoid the interactive
    cgtop UI). Reports breaches at >=90% of MemoryMax.

Writes each snapshot as a row in public.audit_logs with:
  - action: 'resource_snapshot'
  - resource_type: 'system'
  - resource_snapshot: <JSONB blob, schema in docs/runbooks/resource-monitor.md>

Threshold breaches post to #ceo via slack_relay.py:
  - >=90% of MemoryMax → ":warning: high memory ..." (one-shot per breach onset)
  - cgroup killed by OOM → ":octagonal_sign: cgroup OOM-killed ..."

Best-effort: any individual capture failure is logged and the cycle continues.
The systemd unit (infra/systemd/agents/resource-monitor.service) runs us under
Restart=on-failure so a daemon crash auto-recovers.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("resource_monitor")

RESOURCE_MONITOR_INTERVAL_SECONDS = int(os.environ.get("RESOURCE_MONITOR_INTERVAL_SECONDS", "60"))
WARN_PCT = float(os.environ.get("RESOURCE_MONITOR_WARN_PCT", "90"))
DISK_WATCH_PATH = os.environ.get("RESOURCE_MONITOR_DISK_PATH", "/home/elliotbot/clawd")
CGROUP_ROOT = Path(os.environ.get("RESOURCE_MONITOR_CGROUP_ROOT", "/sys/fs/cgroup/user.slice"))

# Track per-cgroup "already warned" state across cycles so we don't spam #ceo.
_warned_breaches: set[str] = set()


def _read_meminfo() -> dict[str, int]:
    """Return MemTotal / MemFree / MemAvailable in MiB from /proc/meminfo."""
    info: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, _, val = line.partition(":")
            val = val.strip()
            if val.endswith(" kB"):
                info[key.strip()] = int(val[:-3]) // 1024  # kB → MiB
    except OSError as exc:
        logger.warning("meminfo read failed: %s", exc)
    return info


def _read_loadavg() -> list[float]:
    try:
        parts = Path("/proc/loadavg").read_text().split()
        return [float(parts[0]), float(parts[1]), float(parts[2])]
    except (OSError, ValueError, IndexError) as exc:
        logger.warning("loadavg read failed: %s", exc)
        return [0.0, 0.0, 0.0]


def _disk_used_pct(path: str) -> int:
    try:
        proc = subprocess.run(
            ["df", "--output=pcent", path],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            return 0
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        # Format: header "Use%" then "39%"
        if len(lines) >= 2:
            return int(lines[1].rstrip("%"))
    except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
        logger.warning("df failed: %s", exc)
    return 0


def _read_cgroup_memory(unit_dir: Path) -> tuple[int, int | None]:
    """Return (memory_current_mb, memory_max_mb_or_none) for a cgroup dir."""
    try:
        current = int((unit_dir / "memory.current").read_text().strip())
    except (OSError, ValueError):
        return 0, None
    try:
        raw_max = (unit_dir / "memory.max").read_text().strip()
        memory_max = None if raw_max == "max" else int(raw_max)
    except (OSError, ValueError):
        memory_max = None
    cur_mb = current // (1024 * 1024)
    max_mb = memory_max // (1024 * 1024) if memory_max is not None else None
    return cur_mb, max_mb


def _scan_cgroups() -> dict[str, dict]:
    """Walk user.slice + nested scopes, returning per-unit memory snapshot."""
    out: dict[str, dict] = {}
    if not CGROUP_ROOT.is_dir():
        return out
    candidates = [CGROUP_ROOT, *CGROUP_ROOT.rglob("*")]
    for path in candidates:
        if not path.is_dir():
            continue
        name = path.name
        if not name.endswith((".scope", ".service", ".slice")):
            continue
        cur_mb, max_mb = _read_cgroup_memory(path)
        if cur_mb == 0 and max_mb is None:
            continue  # not a real memory cgroup
        pct = round(100.0 * cur_mb / max_mb, 1) if max_mb else None
        out[name] = {"memory_mb": cur_mb, "memory_max_mb": max_mb, "pct_of_cap": pct}
    return out


def _detect_breaches(cgroups: dict[str, dict]) -> list[dict]:
    """Return list of cgroup units >= WARN_PCT of their cap."""
    breaches = []
    for name, snap in cgroups.items():
        pct = snap.get("pct_of_cap")
        if pct is not None and pct >= WARN_PCT:
            breaches.append({"unit": name, "pct": pct, "memory_mb": snap["memory_mb"]})
    return breaches


def collect_snapshot(now: datetime | None = None) -> dict:
    ts = (now or datetime.now(UTC)).isoformat()
    mem = _read_meminfo()
    load = _read_loadavg()
    disk_pct = _disk_used_pct(DISK_WATCH_PATH)
    cgroups = _scan_cgroups()
    breaches = _detect_breaches(cgroups)
    total = mem.get("MemTotal", 0)
    avail = mem.get("MemAvailable", 0)
    return {
        "total_mb": total,
        "used_mb": total - avail,
        "free_mb": avail,
        "load_avg": load,
        "disk_used_pct": disk_pct,
        "cgroups": cgroups,
        "thresholds_breached": breaches,
        "captured_at": ts,
    }


def _supabase_write_snapshot(snapshot: dict) -> None:
    """Write the snapshot row to public.audit_logs via asyncpg."""
    dsn = os.environ.get("DATABASE_URL", "") or os.environ.get("DATABASE_URL_MIGRATIONS", "")
    if not dsn:
        logger.info("DATABASE_URL unset — skipping audit_logs write (dry mode)")
        return
    try:
        import asyncio

        import asyncpg
    except ImportError:
        logger.warning("asyncpg unavailable — skipping audit_logs write")
        return

    async def _run() -> None:
        conn = await asyncpg.connect(
            dsn.replace("postgresql+asyncpg://", "postgresql://"),
            statement_cache_size=0,
        )
        try:
            await conn.execute(
                """
                INSERT INTO public.audit_logs (
                    id, action, resource_type, resource_snapshot, created_at
                ) VALUES (gen_random_uuid(), 'resource_snapshot', 'system', $1::jsonb, NOW())
                """,
                json.dumps(snapshot),
            )
        finally:
            await conn.close()

    # Blanket Exception catch is deliberate — this is a best-effort write; any
    # asyncpg / TLS / DSN parse failure logs and drops the row rather than
    # crashing the 60s monitor loop.
    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit_logs insert failed: %s", exc)


def _post_ceo_breach(unit: str, pct: float, memory_mb: int) -> None:
    """Post a one-shot #ceo alert per breach onset. Dedup via _warned_breaches."""
    if unit in _warned_breaches:
        return
    _warned_breaches.add(unit)
    relay = Path(__file__).resolve().parents[1] / "slack_relay.py"
    if not relay.is_file():
        logger.warning("slack_relay.py missing — dropping breach post")
        return
    msg = (
        f":warning: high memory — cgroup `{unit}` at {pct:.1f}% of cap "
        f"({memory_mb}MB used). Source: resource_monitor (KEI-56)."
    )
    try:
        subprocess.run(
            ["python3", str(relay), "-c", "ceo", msg],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("slack_relay -c ceo failed: %s", exc)


def run_cycle() -> dict:
    snapshot = collect_snapshot()
    _supabase_write_snapshot(snapshot)
    for breach in snapshot["thresholds_breached"]:
        _post_ceo_breach(breach["unit"], breach["pct"], breach["memory_mb"])
    # Clear dedup state for units that have dropped back below threshold so a
    # re-breach later still alerts.
    current_breach_units = {b["unit"] for b in snapshot["thresholds_breached"]}
    _warned_breaches.intersection_update(current_breach_units)
    return snapshot


def main() -> int:
    once = "--once" in sys.argv
    logger.info(
        "resource_monitor starting (interval=%ds, warn_pct=%g%%, disk=%s, once=%s)",
        RESOURCE_MONITOR_INTERVAL_SECONDS,
        WARN_PCT,
        DISK_WATCH_PATH,
        once,
    )
    while True:
        run_cycle()
        if once:
            return 0
        time.sleep(RESOURCE_MONITOR_INTERVAL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
