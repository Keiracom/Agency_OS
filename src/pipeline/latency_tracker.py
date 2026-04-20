"""Pipeline latency tracker — per-stage UTC timestamps for SLA monitoring.

Records entry/exit timestamps for each stage in a pipeline run.
Designed to complement the existing ``domain_data["timings"]`` dict
(which stores wall-clock seconds) by adding ISO-8601 start/end
timestamps suitable for SLA dashboards.

Usage::

    tracker = LatencyTracker(domain="example.com.au")
    tracker.start_stage("stage3")
    # ... stage work ...
    tracker.end_stage("stage3")

    report = tracker.report()
    # {
    #   "domain": "example.com.au",
    #   "run_start_utc": "2026-04-16T...",
    #   "total_seconds": 45.2,
    #   "stages": {
    #     "stage3": {"start_utc": "...", "end_utc": "...", "seconds": 12.3},
    #   },
    #   "stage_count": 1,
    #   "p50_stage_seconds": 12.3,
    #   "slowest_stage": "stage3",
    # }
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class LatencyTracker:
    """Track per-stage latency with UTC timestamps for a single domain run."""

    def __init__(self, domain: str) -> None:
        self.domain = domain
        self._stages: dict[str, dict] = {}
        self._run_start_mono = time.monotonic()
        self._run_start_utc = datetime.now(timezone.utc)

    def start_stage(self, stage_name: str) -> None:
        """Record stage entry. Safe to call even if stage already started."""
        self._stages[stage_name] = {
            "_start_mono": time.monotonic(),
            "start_utc": datetime.now(timezone.utc).isoformat(),
        }

    def end_stage(self, stage_name: str) -> None:
        """Record stage exit and compute duration. No-op if start was never called."""
        if stage_name not in self._stages:
            logger.warning("LatencyTracker.end_stage: stage %r was never started", stage_name)
            return
        end_mono = time.monotonic()
        stage = self._stages[stage_name]
        stage["end_utc"] = datetime.now(timezone.utc).isoformat()
        stage["seconds"] = round(end_mono - stage["_start_mono"], 3)

    def report(self) -> dict:
        """Return a serialisable summary of all recorded stage timings."""
        total = round(time.monotonic() - self._run_start_mono, 3)

        completed = {
            name: {k: v for k, v in data.items() if not k.startswith("_")}
            for name, data in self._stages.items()
            if "end_utc" in data
        }

        stage_times = [s["seconds"] for s in completed.values()]
        sorted_times = sorted(stage_times)
        p50 = sorted_times[len(sorted_times) // 2] if sorted_times else 0.0
        slowest = (
            max(completed.items(), key=lambda x: x[1]["seconds"])[0]
            if completed
            else "none"
        )

        return {
            "domain": self.domain,
            "run_start_utc": self._run_start_utc.isoformat(),
            "total_seconds": total,
            "stages": completed,
            "stage_count": len(completed),
            "p50_stage_seconds": round(p50, 3),
            "slowest_stage": slowest,
        }
