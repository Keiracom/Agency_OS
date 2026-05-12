#!/usr/bin/env python3
"""session_uuid_resume.py — KEI-31 component 4: session UUID preservation + resume.

Dave's verbatim: 'Session UUID preservation and resume (PR-C already built —
wire into restart flow)'. The 'PR-C already built' refers to Drevon
PR-A's record_session_start in src/session_store/recorder.py:57 which
accepts a session_uuid parameter. This script reads the most-recent
session row for the current callsign from the Supabase sessions table
and emits a resume-context markdown block for the SessionStart hook chain.

Failure modes:
  - No Supabase access / missing env: emit a no-state block, exit 0.
  - No prior sessions row: emit "first-session" block, exit 0.

Always exits 0 — operator-script discipline.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request

logger = logging.getLogger("session_uuid_resume")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

_SUPABASE_URL_ENV = "SUPABASE_URL"
_SUPABASE_KEY_ENV = "SUPABASE_SERVICE_KEY"


def _callsign() -> str:
    cs = (os.environ.get("CALLSIGN") or "").strip().lower()
    if cs:
        return cs
    try:
        with open("./IDENTITY.md") as f:
            for line in f:
                if "CALLSIGN:" in line:
                    return line.split("CALLSIGN:")[-1].strip().strip("*").strip().lower()
    except OSError:
        pass
    return "unknown"


def fetch_recent_session(callsign: str) -> dict | None:
    """Return the most recent sessions row for this callsign, or None."""
    url = os.environ.get(_SUPABASE_URL_ENV, "").rstrip("/")
    key = os.environ.get(_SUPABASE_KEY_ENV, "")
    if not (url and key):
        return None
    query_url = (
        f"{url}/rest/v1/sessions"
        f"?callsign=eq.{callsign}"
        f"&order=started_at.desc"
        f"&limit=1"
    )
    req = urllib.request.Request(
        query_url,
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read() or "[]")
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Supabase sessions query failed: %s", exc)
        return None
    return rows[0] if rows else None


def render_resume(callsign: str, prior: dict | None) -> str:
    """Emit a markdown context block."""
    lines = ["## Session UUID resume (KEI-31 component 4)"]
    if not prior:
        lines.append(f"- No prior session row found for callsign **{callsign}** — first session OR Supabase unreachable.")
        lines.append("")
        return "\n".join(lines)
    sid = prior.get("session_uuid") or prior.get("id") or "?"
    started = prior.get("started_at") or "?"
    status = prior.get("status") or "?"
    lines.append(f"- Previous session: **{sid}**")
    lines.append(f"  - Started: {started}")
    lines.append(f"  - Status at last close: {status}")
    lines.append(f"  - Resume context: this session continues callsign {callsign}'s prior work; ")
    lines.append("    consult the prior session's recorded turns at sessions table for full history.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    callsign = _callsign()
    prior = fetch_recent_session(callsign)
    sys.stdout.write(render_resume(callsign, prior))
    return 0


if __name__ == "__main__":
    sys.exit(main())
