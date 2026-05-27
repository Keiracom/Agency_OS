#!/usr/bin/env python3
"""agency_cost_rollup.py — daily 3-provider cost rollup to ceo channel.

Cutover Blocker 1 / Cutover Readiness Gate COST-TELEMETRY criterion
(bd Agency_OS-j12p). Daily per-provider + per-callsign cost rollup that
posts to ceo channel at 23:55 AEST (13:55 UTC).

Providers aggregated:
- Anthropic — derived from session JSONLs at
  ~/.claude/projects/-home-elliotbot-clawd-*/<session>.jsonl (last 24h).
  Per-callsign attribution via the projects/<dir>/ naming convention
  (-home-elliotbot-clawd-Agency-OS-<callsign>).
- OpenAI — existing /home/elliotbot/clawd/logs/openai-cost.jsonl
  (already callsign-tagged per call). Same shape as openai_cost_rollup.py.
- Vultr — Vultr Billing API IF VULTR_API_KEY env present;
  graceful "Vultr: API_KEY missing" skip otherwise. Attributed to
  callsign=fleet (infrastructure-level).

Anthropic pricing per published Anthropic API rates (USD per 1M tokens).
NOTE — Atlas bounded-spawn measurement 2026-05-27 (session
78408655-03d9-4459-ba90-ea172b4fb952) showed that for the [1m] 1M-context
Opus 4.7 the actual 1h-cache-write rate back-derives to ~$5.14/M, not the
published $30/M (~6× discount). The MODEL_PRICING table below uses
PUBLISHED rates as a CONSERVATIVE cost estimate; actual bills may be lower.
Calibrate rates when more empirical points land.

CLI:
    python3 scripts/agency_cost_rollup.py            # run once + post + log
    python3 scripts/agency_cost_rollup.py --dry-run  # compute + print, no post
    python3 scripts/agency_cost_rollup.py --hours N  # window override (default 24)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("agency_cost_rollup")

CLAUDE_PROJECTS_ROOT = Path.home() / ".claude" / "projects"
OPENAI_COST_LOG = Path("/home/elliotbot/clawd/logs/openai-cost.jsonl")
AGENCY_DAILY_LOG = Path("/home/elliotbot/clawd/logs/agency-cost-daily.jsonl")

# Anthropic published per-1M USD rates (input, output, cache_read, cache_write_5m, cache_write_1h)
MODEL_PRICING = {
    "claude-opus-4-7": (15.0, 75.0, 1.50, 18.75, 30.0),
    "claude-opus-4-6": (15.0, 75.0, 1.50, 18.75, 30.0),
    "claude-opus-4-5": (15.0, 75.0, 1.50, 18.75, 30.0),
    "claude-sonnet-4-6": (3.0, 15.0, 0.30, 3.75, 6.0),
    "claude-sonnet-4-5": (3.0, 15.0, 0.30, 3.75, 6.0),
    "claude-haiku-4-5": (1.0, 5.0, 0.10, 1.25, 2.0),
}


def _normalise_model(model: str | None) -> str | None:
    """Map session-JSONL model strings to MODEL_PRICING keys (drop [1m] etc.)."""
    if not model:
        return None
    base = model.split("[")[0].strip()  # "claude-opus-4-7[1m]" -> "claude-opus-4-7"
    # Strip dated suffix variants like "claude-haiku-4-5-20251001"
    base = (
        base.rsplit("-", 1)[0]
        if base.split("-")[-1].isdigit() and len(base.split("-")[-1]) >= 8
        else base
    )
    return base if base in MODEL_PRICING else None


def cost_for_usage(usage: dict, model: str) -> float:
    """USD cost for one assistant-message usage block."""
    key = _normalise_model(model)
    if key is None:
        return 0.0
    inp, out, cread, cw5m, cw1h = MODEL_PRICING[key]
    fresh_input = usage.get("input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    out_tok = usage.get("output_tokens", 0)
    cw = usage.get("cache_creation", {}) or {}
    cw_5m = cw.get("ephemeral_5m_input_tokens", 0)
    cw_1h = cw.get("ephemeral_1h_input_tokens", 0)
    if not cw and usage.get("cache_creation_input_tokens"):
        cw_5m = usage["cache_creation_input_tokens"]
    return (
        fresh_input / 1e6 * inp
        + cache_read / 1e6 * cread
        + cw_5m / 1e6 * cw5m
        + cw_1h / 1e6 * cw1h
        + out_tok / 1e6 * out
    )


def callsign_from_project_dir(dirname: str) -> str:
    """Map ~/.claude/projects/<dirname> to a callsign string."""
    if dirname.endswith("-home-elliotbot-clawd-Agency-OS"):
        return "elliot"  # main worktree = elliot
    if dirname.endswith("-home-elliotbot-clawd"):
        return "elliot-clawd-root"
    if dirname.endswith("-home-elliotbot"):
        return "elliot-home"
    suffix = dirname.rsplit("-", 1)[-1]
    return suffix or "unknown"


def load_anthropic_session_cost(
    hours: int, *, projects_root: Path | None = None
) -> dict[str, float]:
    """Walk session JSONLs in last `hours` window + return per-callsign USD totals."""
    root = projects_root or CLAUDE_PROJECTS_ROOT
    if not root.exists():
        return {}
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    by_callsign: dict[str, float] = defaultdict(float)
    for project_dir in root.iterdir():
        if not project_dir.is_dir():
            continue
        callsign = callsign_from_project_dir(project_dir.name)
        for jsonl_path in project_dir.glob("*.jsonl"):
            try:
                if datetime.fromtimestamp(jsonl_path.stat().st_mtime, tz=UTC) < cutoff:
                    continue
            except OSError:
                continue
            try:
                with jsonl_path.open(encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if row.get("type") != "assistant":
                            continue
                        ts_str = row.get("timestamp")
                        if ts_str:
                            try:
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if ts < cutoff:
                                    continue
                            except ValueError:
                                pass
                        msg = row.get("message", {}) or {}
                        usage = msg.get("usage")
                        if not usage:
                            continue
                        model = msg.get("model")
                        by_callsign[callsign] += cost_for_usage(usage, model)
            except OSError:
                continue
    return dict(by_callsign)


def load_openai_cost(hours: int, *, log_path: Path | None = None) -> dict[str, float]:
    """Per-callsign USD totals from existing openai-cost.jsonl in last `hours`."""
    path = log_path or OPENAI_COST_LOG
    if not path.exists():
        return {}
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    by_callsign: dict[str, float] = defaultdict(float)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["ts"])
                if ts < cutoff:
                    continue
                by_callsign[entry.get("callsign", "unknown")] += float(
                    entry.get("estimated_cost_usd", 0.0)
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return dict(by_callsign)


def load_vultr_cost(hours: int, *, api_key: str | None = None) -> tuple[float, str]:
    """Vultr last-`hours` spend via Billing API. Returns (usd_total, note)."""
    key = api_key if api_key is not None else os.environ.get("VULTR_API_KEY", "")
    if not key:
        return 0.0, "VULTR_API_KEY missing — Vultr line skipped"
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    req = urllib.request.Request(
        "https://api.vultr.com/v2/billing/history",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return 0.0, f"Vultr API error: {type(exc).__name__}"
    total = 0.0
    for entry in body.get("billing_history") or []:
        date_str = entry.get("date")
        try:
            entry_ts = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            continue
        if entry_ts < cutoff:
            continue
        amount = float(entry.get("amount") or 0.0)
        # Vultr billing_history amount is signed: charges negative, payments positive.
        # Sum absolute charges only.
        if amount < 0:
            total += abs(amount)
    return round(total, 6), "Vultr API OK"


def aggregate(
    anthropic: dict[str, float],
    openai: dict[str, float],
    vultr_usd: float,
) -> dict[str, Any]:
    """Aggregate per-provider + per-callsign + grand total."""
    by_provider = {
        "anthropic": round(sum(anthropic.values()), 6),
        "openai": round(sum(openai.values()), 6),
        "vultr": round(vultr_usd, 6),
    }
    by_callsign: dict[str, float] = defaultdict(float)
    for cs, v in anthropic.items():
        by_callsign[cs] += v
    for cs, v in openai.items():
        by_callsign[cs] += v
    by_callsign["fleet"] += vultr_usd
    return {
        "date": datetime.now(UTC).date().isoformat(),
        "total_usd": round(sum(by_provider.values()), 6),
        "total_aud": round(sum(by_provider.values()) * 1.55, 6),
        "by_provider_usd": by_provider,
        "by_callsign_usd": {k: round(v, 6) for k, v in sorted(by_callsign.items())},
    }


def load_attribution_breakdown(hours: int = 24) -> dict[str, dict[str, Any]]:
    """Cutover Blocker 6 attribution — per-source_type breakdown from
    spawn-attribution JSONL. Returns {source_type: {cost_usd_sum, spawn_count}}.
    Imports done locally to keep the rollup script runnable when the
    attribution module is absent (e.g. legacy environments)."""
    try:
        from src.keiracom_system.attribution.logger import (
            aggregate_by_source_type,
            load_attribution_last_24h,
        )
    except ImportError:
        return {}
    entries = load_attribution_last_24h(hours=hours)
    return aggregate_by_source_type(entries)


def format_ceo_post(
    summary: dict[str, Any],
    vultr_note: str,
    attribution: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Plain-English ceo-channel post per Dave's plain-English-strict rule.

    Optional `attribution` is the per-source_type breakdown from
    `load_attribution_breakdown()` — Cutover Blocker 6 / Viktor lever 27.
    Omitted when empty so the rollup stays clean before dispatch
    integration lands.
    """
    bp = summary["by_provider_usd"]
    bc = summary["by_callsign_usd"]
    aud_total = summary["total_aud"]
    lines = [
        f"[ELLIOT] Daily cost: ${aud_total:.2f} AUD (24h to {summary['date']})",
        f"  by provider:  Anthropic ${bp['anthropic'] * 1.55:.2f} | OpenAI ${bp['openai'] * 1.55:.2f} | Vultr ${bp['vultr'] * 1.55:.2f} AUD",
        "  by callsign:  "
        + " | ".join(f"{cs} ${v * 1.55:.2f}" for cs, v in bc.items() if v > 0.001),
    ]
    if attribution:
        parts = []
        for st in sorted(attribution):
            row = attribution[st]
            aud = row.get("cost_usd_sum", 0) * 1.55
            n = row.get("spawn_count", 0)
            if aud > 0.001 or n > 0:
                parts.append(f"{st} ${aud:.2f} ({n} spawns)")
        if parts:
            lines.append("  by source:    " + " | ".join(parts))
    if "missing" in vultr_note or "error" in vultr_note:
        lines.append(f"  note: {vultr_note}")
    return "\n".join(lines)


def post_to_ceo(text: str, *, runner=subprocess.run) -> int:
    """Run `tg -c ceo "<text>"`. Returns exit code (0 = posted)."""
    try:
        result = runner(["tg", "-c", "ceo", text], capture_output=True, text=True, timeout=30)
        return int(result.returncode)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return 2


def write_daily_log(summary: dict[str, Any], *, log_path: Path | None = None) -> None:
    path = log_path or AGENCY_DAILY_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(summary) + "\n")


def run(*, hours: int = 24, dry_run: bool = False) -> int:
    anthropic = load_anthropic_session_cost(hours)
    openai = load_openai_cost(hours)
    vultr_usd, vultr_note = load_vultr_cost(hours)
    attribution = load_attribution_breakdown(hours)
    summary = aggregate(anthropic, openai, vultr_usd)
    summary["vultr_note"] = vultr_note
    if attribution:
        summary["by_source_type_usd"] = {
            k: {"cost_usd_sum": v["cost_usd_sum"], "spawn_count": v["spawn_count"]}
            for k, v in attribution.items()
        }
    text = format_ceo_post(summary, vultr_note, attribution=attribution)
    print(text)
    print(json.dumps(summary, indent=2))
    if dry_run:
        return 0
    write_daily_log(summary)
    rc = post_to_ceo(text)
    if rc != 0:
        logger.warning("tg post returned rc=%d", rc)
    return rc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="compute + print, don't post or log")
    p.add_argument("--hours", type=int, default=24, help="lookback window in hours (default 24)")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    return run(hours=args.hours, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
