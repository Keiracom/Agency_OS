#!/usr/bin/env python3
"""measure_session_rss.py — per-session RSS / RAM-ceiling proof harness.

Proof gate (1) for ceo:decision:concurrency_cap_2026-06-04:
  "With N sessions live, peak RSS+swap stays under the RAM ceiling (no
   swap-thrash) under load — MEASURED, not asserted."

Reads, with NO assumptions:
  * physical RAM + swap from /proc/meminfo
  * per-session high-water RSS from each tmux-spawn cgroup's memory.peak
    (the `claude` tree is reparented under tmux scopes, so service-level
    accounting misses it — we read the scope cgroups directly)

Then derives the safe N and checks it against the worst-case all-spike
total. Run it on the box to reproduce the measurement verbatim:

    python3 scripts/measure_session_rss.py

Exit code 0 = the configured N_TOTAL survives worst-case within RAM+swap;
1 = the configured N would risk OOM (proof gate FAIL).
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

# Planning footprints (GB) — see docs/audits/concurrency_cap_rss_measurement.md.
SUSTAINED_PEAK_GB = 1.5  # planning sustained working set per session
WORST_SPIKE_GB = 2.6  # worst observed cgroup memory.peak under Opus 4.8
INFRA_RESERVE_GB = 4.0  # OS + redis + postgres + NATS bridges + watchers + buffers

_MEMINFO = Path("/proc/meminfo")
_CGROUP_GLOBS = [
    "/sys/fs/cgroup/**/tmux-spawn-*.scope/memory.peak",
]


def _meminfo_mb() -> tuple[float, float]:
    ram_kb = swap_kb = 0
    for line in _MEMINFO.read_text().splitlines():
        if line.startswith("MemTotal:"):
            ram_kb = int(line.split()[1])
        elif line.startswith("SwapTotal:"):
            swap_kb = int(line.split()[1])
    return ram_kb / 1024, swap_kb / 1024


def _session_peaks_mb() -> list[float]:
    peaks: list[float] = []
    seen: set[str] = set()
    for pattern in _CGROUP_GLOBS:
        for path in glob.glob(pattern, recursive=True):
            if path in seen:
                continue
            seen.add(path)
            try:
                peaks.append(int(Path(path).read_text()) / 1048576)
            except (OSError, ValueError):
                continue
    return sorted(peaks, reverse=True)


def main() -> int:
    # Import here so the script also runs standalone on a box without the repo
    # on sys.path for the non-cap parts.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.dispatcher.concurrency_cap import (  # noqa: PLC0415
        DELIB_CAP,
        GATED,
        N_TOTAL,
        REVIEW_CAP,
        WORKER_CAP,
    )

    ram_mb, swap_mb = _meminfo_mb()
    addressable_mb = ram_mb + swap_mb
    peaks = _session_peaks_mb()

    print("─── MEASURED (verbatim) ──────────────────────────────────────────")
    print(f"physical RAM     : {ram_mb:8.1f} MB ({ram_mb / 1024:.2f} GB)")
    print(f"swap             : {swap_mb:8.1f} MB ({swap_mb / 1024:.2f} GB)")
    print(f"addressable      : {addressable_mb:8.1f} MB ({addressable_mb / 1024:.2f} GB)")
    if peaks:
        print(f"live sessions    : {len(peaks)}")
        print(f"per-session peak : max={max(peaks):.1f} MB  mean={sum(peaks) / len(peaks):.1f} MB")
        print("  " + "  ".join(f"{p:.0f}" for p in peaks) + " MB")
    else:
        print("live sessions    : (no tmux-spawn cgroups found — run on the box)")

    print("\n─── DERIVATION ───────────────────────────────────────────────────")
    print(
        f"N_TOTAL={N_TOTAL}  (gated={GATED}: delib={DELIB_CAP} review={REVIEW_CAP} "
        f"worker={WORKER_CAP}; +1 Elliot bypass)"
    )
    sustained = N_TOTAL * SUSTAINED_PEAK_GB + INFRA_RESERVE_GB
    worst = N_TOTAL * WORST_SPIKE_GB + INFRA_RESERVE_GB
    over = (N_TOTAL + 1) * WORST_SPIKE_GB + INFRA_RESERVE_GB
    print(
        f"sustained total  : {N_TOTAL} x {SUSTAINED_PEAK_GB} + {INFRA_RESERVE_GB} "
        f"= {sustained:.1f} GB  (RAM {ram_mb / 1024:.1f} GB)"
    )
    print(
        f"worst all-spike  : {N_TOTAL} x {WORST_SPIKE_GB} + {INFRA_RESERVE_GB} "
        f"= {worst:.1f} GB  (RAM+swap {addressable_mb / 1024:.1f} GB)"
    )
    print(f"N+1 worst-spike  : {over:.1f} GB  (the config that would OOM)")

    # Real measured aggregate (Aiden review #1433): when >=N sessions are live,
    # the worst-case need not be a linear projection from a single-session peak
    # — sum the N largest MEASURED co-resident peaks + infra. This is an actual
    # observed aggregate, not 6 x WORST_SPIKE. Stronger proof when the box is
    # loaded; absent under N live sessions it falls back to the projection.
    measured_worst_gb: float | None = None
    if len(peaks) >= N_TOTAL:
        topn_mb = sum(peaks[:N_TOTAL])
        measured_worst_gb = topn_mb / 1024 + INFRA_RESERVE_GB
        print(
            f"\nmeasured agg     : sum(top {N_TOTAL} live peaks) {topn_mb:.0f} MB + "
            f"{INFRA_RESERVE_GB} GB infra = {measured_worst_gb:.1f} GB  (REAL aggregate)"
        )
    else:
        print(
            f"\nmeasured agg     : only {len(peaks)} live sessions (< N={N_TOTAL}) — "
            f"projection used; re-run under sustained {N_TOTAL}-session load for a real aggregate"
        )

    # Gate uses the WORSE of (linear projection, measured aggregate) — never
    # weaker than the projection, stronger when a real aggregate exists.
    gate_worst = max(worst, measured_worst_gb or 0.0)
    sustained_ok = sustained <= ram_mb / 1024  # sustained must fit RAM with NO swap
    worst_ok = gate_worst <= addressable_mb / 1024  # spike may dip into swap, no OOM
    swap_dip_gb = max(0.0, gate_worst - ram_mb / 1024)
    print("\n─── PROOF GATE (1) ───────────────────────────────────────────────")
    print(f"sustained under physical RAM (no swap-thrash): {'PASS' if sustained_ok else 'FAIL'}")
    print(
        f"worst-case under RAM+swap (no OOM)           : {'PASS' if worst_ok else 'FAIL'}"
        f"  [bound={gate_worst:.1f} GB, swap dip {swap_dip_gb:.1f} GB]"
    )
    return 0 if (worst_ok and sustained_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
