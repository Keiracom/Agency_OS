#!/usr/bin/env python3
"""verify_model_assignment.py — KEI-32 read-only model assignment audit.

Compares each callsign's running `--model` flag (inspected via /proc/<pane_pid>/
cmdline) against the canonical mapping stored in ceo_memory under key
'orchestration:model_assignment'. Reports per-callsign drift + summary.

Acceptance criterion (KEI-32 verbatim — acceptance_criteria=NULL so plain
UPDATE close path is allowed; this script ships the audit per Step 0 framing):
    Audit each callsign's running model vs ceo_memory expected. Report drift.

This is a READ-ONLY audit — no runtime switching, no restart-on-drift, no
cost dashboard. Pre-revenue right-sizing.

ceo_memory mapping (Dave directive ts ~1778625870):
    Primaries (max/aiden/elliot CTOs+COO):    Opus 4.7   1M context
    Clones    (atlas/orion/scout engineers):  Sonnet 4.6 200K (haiku-mechanical 4.5 for scout)

Usage:
    python3 scripts/orchestrator/verify_model_assignment.py             # text summary
    python3 scripts/orchestrator/verify_model_assignment.py --json      # machine output

Composes with HEARTBEAT `Running:` field (KEI-36) — the per-callsign running
model lookup pattern lives here so heartbeat + this audit share one source.

Env:
    AGENCY_OS_MCP_BRIDGE  path to mcp-bridge repo (default /home/elliotbot/clawd/skills/mcp-bridge)
    SUPABASE_PROJECT_ID   Supabase project id (default jatzvazlbusedwsnqxzr)

Exit codes:
    0  all callsigns match expected
    1  one or more drifted
    2  ceo_memory unreachable / required-data missing
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any

CALLSIGNS = ("elliot", "aiden", "max", "atlas", "orion", "scout")

# Map callsign → tmux session name. Mirrors elliot_polling_loop.py +
# kei45_realtime_listener.py CALLSIGN_TO_TMUX (single source-of-truth at
# kei45_realtime_listener.py).
TMUX_SESSION = {
    "elliot": "elliottbot",
    "aiden": "aiden",
    "max": "maxbot",
    "atlas": "atlas",
    "orion": "orion",
    "scout": "scout",
}

DEFAULT_PROJECT_ID = os.environ.get("SUPABASE_PROJECT_ID", "jatzvazlbusedwsnqxzr")
DEFAULT_MCP_BRIDGE = os.environ.get(
    "AGENCY_OS_MCP_BRIDGE", "/home/elliotbot/clawd/skills/mcp-bridge"
)

_MODEL_FLAG_RE = re.compile(r"--model[\s=]*(\S+)")


class AuditError(RuntimeError):
    """Raised when ceo_memory is unreachable or the canonical key is missing."""


def fetch_expected_assignment() -> dict[str, str]:
    """Read ceo_memory key orchestration:model_assignment. Returns flat
    {callsign: expected_model} mapping (clones drilled out of nested dict).

    Direct psycopg query — simpler than wrapping the MCP-bridge response
    parsing. Same pattern as Scout's KEI-61 worker + my KEI-54B indexer.
    """
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise AuditError("DATABASE_URL / SUPABASE_DB_URL env required")
    dsn = dsn.replace("+asyncpg", "").replace("+psycopg2", "")
    try:
        import psycopg  # noqa: PLC0415
    except ImportError as exc:
        raise AuditError("psycopg not installed; pip install psycopg[binary]") from exc

    # prepare_threshold=None — Supabase pooler transaction-mode pgbouncer
    # drops PREPARE statements. See reference_psycopg_supabase_pgbouncer.md.
    with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT value FROM public.ceo_memory "
            "WHERE key = 'orchestration:model_assignment' LIMIT 1"
        )
        rows = cur.fetchall()
    if not rows:
        raise AuditError("ceo_memory key orchestration:model_assignment not found")
    value = rows[0][0]  # jsonb column returns dict directly via psycopg type adapter
    return _flatten_assignment(value)


def _flatten_assignment(value: dict[str, Any]) -> dict[str, str]:
    """Convert the nested ceo_memory value into {callsign: model_id}."""
    out: dict[str, str] = {}
    for cs, info in (value.get("primaries_unchanged") or {}).items():
        if isinstance(info, dict) and "model" in info:
            out[cs] = info["model"]
    for cs, info in (value.get("clones_switched") or {}).items():
        if not isinstance(info, dict):
            continue
        # Clones can have 'model' OR ('primary'+'mechanical'); pick 'primary' if dual.
        if "model" in info:
            out[cs] = info["model"]
        elif "primary" in info:
            out[cs] = info["primary"].split(" ")[0]  # strip "(200K)" suffix
    return out


def running_model_for(callsign: str) -> str | None:
    """Inspect the tmux session for `callsign` and return the --model flag
    visible on the pane_current_command (or its parent process). Returns
    None if session not running or no --model flag found.
    """
    session = TMUX_SESSION.get(callsign)
    if not session:
        return None
    try:
        proc = subprocess.run(  # noqa: S603
            ["tmux", "list-panes", "-t", session, "-F", "#{pane_pid}"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    pids = [p for p in proc.stdout.strip().splitlines() if p]
    if not pids:
        return None
    return _scan_pids_for_model_flag(pids)


def _scan_pids_for_model_flag(pids: list[str]) -> str | None:
    """Walk the pids + their descendants looking for --model in any cmdline.

    Returns:
        the model flag value (e.g. 'claude-opus-4-7') if found
        '<implicit>' if `claude` process is running but no --model on cmdline
        None if no claude process and no --model flag found
    """
    seen: set[str] = set()
    queue = list(pids)
    found_claude = False
    while queue:
        pid = queue.pop(0)
        if pid in seen:
            continue
        seen.add(pid)
        cmdline = _read_cmdline(pid)
        if cmdline:
            match = _MODEL_FLAG_RE.search(cmdline)
            if match:
                return match.group(1)
            if " claude " in cmdline or cmdline.startswith("claude "):
                found_claude = True
        queue.extend(_children_of(pid))
    return "<implicit>" if found_claude else None


def _read_cmdline(pid: str) -> str:
    path = f"/proc/{pid}/cmdline"
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", errors="ignore")


def _children_of(pid: str) -> list[str]:
    try:
        proc = subprocess.run(  # noqa: S603
            ["pgrep", "-P", pid],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    return [p for p in proc.stdout.strip().splitlines() if p]


def audit(
    expected_fn=None,
    running_fn=None,
) -> tuple[list[dict], int]:
    """Return (drift_rows, num_drifted). Each row has callsign + expected + running + status.

    Resolve fn refs at call time (not module-load) so mock.patch.object works.
    """
    if expected_fn is None:
        expected_fn = fetch_expected_assignment
    if running_fn is None:
        running_fn = running_model_for
    expected = expected_fn()
    rows: list[dict[str, Any]] = []
    drifted = 0
    for cs in CALLSIGNS:
        exp = expected.get(cs)
        run = running_fn(cs)
        if exp is None:
            status = "no-expected"
        elif run is None:
            status = "no-pane"
            drifted += 1
        elif run == "<implicit>":
            status = "implicit"
            drifted += 1  # implicit model is undetectable drift — surfaces the gap
        elif run == exp:
            status = "match"
        else:
            status = "drift"
            drifted += 1
        rows.append({"callsign": cs, "expected": exp, "running": run, "status": status})
    return rows, drifted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    try:
        rows, drifted = audit()
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary = {"matched": sum(1 for r in rows if r["status"] == "match"), "drifted": drifted}
    if args.json:
        print(json.dumps({"rows": rows, "summary": summary}, default=str))
    else:
        print(f"=== Model assignment audit ({len(rows)} callsigns) ===")
        for r in rows:
            mark = {
                "match": "OK",
                "drift": "DRIFT",
                "no-pane": "NO-PANE",
                "no-expected": "NO-EXPECTED",
                "implicit": "IMPLICIT",
            }.get(r["status"], r["status"])
            print(
                f"  {r['callsign']:<8}  expected={r['expected']:<24}  "
                f"running={r['running']!s:<24}  [{mark}]"
            )
        print(f"\n{summary['matched']}/{len(rows)} matched, {summary['drifted']} drifted")
    return 0 if drifted == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
