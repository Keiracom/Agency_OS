#!/usr/bin/env python3
"""write_heartbeat.py — Stop-hook entry-point that refreshes HEARTBEAT.md.

Invoked by the Claude Code Stop hook whenever a session ends or `/clear`
fires (Dave directive 2026-05-31, Defect 2 of recovery-infra triplet).

Hard constraint: complete in <5 s. The Stop hook drops the call if we run
long, so all external IO runs in parallel under tight per-call timeouts.

Live data:
  - Current phase     — `ceo:gate_skip_enforced_rule_v1` → `value->>'phase_1_status'`
  - Open PRs          — `gh pr list --limit 5 --json number,title,author`
  - Active directives — `ceo_memory WHERE key LIKE 'ceo:directive_%'
                         AND value->>status = 'active' LIMIT 3`

Output path: $HEARTBEAT_PATH (default /home/elliotbot/clawd/Agency_OS/HEARTBEAT.md).
Exit 0 on success, 1 on failure (non-fatal — watchdog must still boot).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

from scripts.orchestrator.write_compact_state import (  # noqa: E402
    PHASE_FALLBACK,
    current_phase,
)

DEFAULT_HEARTBEAT_PATH = "/home/elliotbot/clawd/Agency_OS/HEARTBEAT.md"
HTTP_TIMEOUT_SEC = 3  # tight — leaves headroom under the 5 s Stop-hook ceiling
SUBPROC_TIMEOUT_SEC = 4


def _open_prs() -> list[dict]:
    """Return open PRs or [] on any failure. gh subprocess with 4 s timeout."""
    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--limit", "5", "--json", "number,title,author"],
            capture_output=True,
            text=True,
            timeout=SUBPROC_TIMEOUT_SEC,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        if r.returncode != 0:
            return []
        return list(json.loads(r.stdout))
    except Exception:
        return []


def _active_directives() -> list[dict]:
    """Return up to 3 active directives from ceo_memory, or [] on failure."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return []
    try:
        import urllib.request

        # PostgREST LIKE wildcard is % (URL-encoded as %25); status filter on JSONB field.
        q = "ceo_memory?key=like.ceo:directive_%25&value->>status=eq.active&select=key,value&limit=3"
        req = urllib.request.Request(
            f"{url}/rest/v1/{q}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SEC) as r:
            rows = json.loads(r.read())
        return list(rows) if isinstance(rows, list) else []
    except Exception:
        return []


def _render_prs(prs: list[dict]) -> str:
    if not prs:
        return "- none open"
    out = []
    for p in prs:
        author = (p.get("author") or {}).get("login", "?")
        title = (p.get("title") or "")[:70]
        out.append(f"- #{p.get('number')} {title} (@{author})")
    return "\n".join(out)


def _render_directives(rows: list[dict]) -> str:
    if not rows:
        return "- none active"
    out = []
    for r in rows:
        key = r.get("key", "?")
        value = r.get("value") or {}
        title = (value.get("title") or value.get("summary") or "")[:80]
        out.append(f"- {key}: {title}")
    return "\n".join(out)


def _render(phase: str, prs: list[dict], directives: list[dict], ts: str) -> str:
    return f"""# Elliot HEARTBEAT — Session continuation anchor

## Last update: {ts} (hook-written on session end)

## Current Phase: {phase}

## Open PRs:
{_render_prs(prs)}

## Active directives:
{_render_directives(directives)}

## First Actions for Restored Elliot:
1. Read /tmp/elliot-compact-state.md for fleet status.
2. Read IDENTITY.md and this file only — do NOT reload full history.
3. Run fleet sweep: working / waiting / finished→dispatch / stuck→revive.
4. Post #ceo: "resumed at [phase/task], fleet: [one-line status]."
5. No paid chain runs without explicit Dave approval.
"""


def main() -> int:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    # Parallelise the three IO calls so total wall-clock = slowest single call
    # rather than sum. Keeps us well under the 5 s Stop-hook ceiling even when
    # one call hits its timeout.
    with ThreadPoolExecutor(max_workers=3) as pool:
        phase_fut = pool.submit(current_phase)
        prs_fut = pool.submit(_open_prs)
        dir_fut = pool.submit(_active_directives)
        phase = phase_fut.result()
        prs = prs_fut.result()
        directives = dir_fut.result()

    out_path = Path(os.environ.get("HEARTBEAT_PATH") or DEFAULT_HEARTBEAT_PATH)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_render(phase, prs, directives, ts))
    except OSError as exc:
        print(f"write_heartbeat: write failed → {exc}", file=sys.stderr)
        return 1

    fallback_marker = " (fallback)" if phase == PHASE_FALLBACK else ""
    print(f"HEARTBEAT written: {ts} → {out_path}{fallback_marker}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
