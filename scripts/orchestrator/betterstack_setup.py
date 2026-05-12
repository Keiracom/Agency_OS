#!/usr/bin/env python3
"""betterstack_setup.py — KEI Better Stack heartbeats + groups bootstrap.

Per Dave directive ts ~1778588500 + Elliot dispatch. One-shot operator script
that creates the 5 heartbeat monitors + 2 groups via Better Stack API.

Usage:
    BETTERSTACK_API_KEY=<key> python3 scripts/orchestrator/betterstack_setup.py
    # → prints heartbeat tokens + URLs as KEY=VALUE lines for .env append.

After running this once, operator appends the printed lines to
/home/elliotbot/.config/agency-os/.env, then wires `curl -m 5 <url>` as the
LAST line of each scheduled process script:

  - elliot-polling-loop.py (per-cycle end)              → BETTERSTACK_HB_ELLIOT_POLLING_LOOP
  - cognee_ingest.py (per-batch end)                    → BETTERSTACK_HB_COGNEE_PHASE1_INGEST
  - prefect orchestrator flow (per-flow end)            → BETTERSTACK_HB_PREFECT_PIPELINE
  - slack_bot/central_listener.py (per-loop iter end)   → BETTERSTACK_HB_CENTRAL_LISTENER
  - agency-os-discovery pipeline (per-stage end)        → BETTERSTACK_HB_AGENCY_OS_DISCOVERY

API: https://uptime.betterstack.com/api/v2/heartbeats (Bearer auth).

Idempotent: if a heartbeat with the same name exists, skip creation +
print existing token. Re-run is safe.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

API_BASE = "https://uptime.betterstack.com/api/v2"

# Heartbeat name → (period_sec, grace_sec, group_name) per Elliot dispatch.
HEARTBEATS: list[tuple[str, int, int, str]] = [
    ("elliot-polling-loop", 60, 90, "Keiracom Agent Team"),
    ("cognee-phase1-ingest", 600, 300, "Keiracom Agent Team"),
    ("prefect-pipeline", 600, 300, "Keiracom Agent Team"),
    ("central-listener", 300, 120, "Keiracom Agent Team"),
    ("agency-os-discovery", 1800, 600, "Agency OS Pipeline"),
]

GROUP_NAMES: tuple[str, ...] = ("Keiracom Agent Team", "Agency OS Pipeline")


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _request(method: str, url: str, api_key: str, body: dict | None = None) -> dict | None:
    """Best-effort Better Stack API call. Returns parsed JSON or None on error."""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_auth_headers(api_key), method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read() or "null")
    except urllib.error.HTTPError as exc:
        # 422 on duplicate-name is expected (idempotent path); other 4xx/5xx are errors.
        body_text = exc.read().decode(errors="replace") if exc.fp else ""
        print(f"[bs] HTTP {exc.code} on {method} {url}: {body_text[:200]}", file=sys.stderr)
        return None
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        print(f"[bs] network/parse error on {method} {url}: {exc}", file=sys.stderr)
        return None


def list_heartbeats(api_key: str) -> list[dict]:
    """Return all existing heartbeats (paginated, single page assumed sufficient)."""
    resp = _request("GET", f"{API_BASE}/heartbeats?per_page=100", api_key)
    if not resp:
        return []
    return resp.get("data", []) or []


def list_heartbeat_groups(api_key: str) -> list[dict]:
    resp = _request("GET", f"{API_BASE}/heartbeat-groups?per_page=100", api_key)
    if not resp:
        return []
    return resp.get("data", []) or []


def ensure_group(api_key: str, name: str, existing: list[dict]) -> str | None:
    """Return group_id; create if absent. None on failure."""
    for g in existing:
        if g.get("attributes", {}).get("name") == name:
            return str(g.get("id"))
    resp = _request("POST", f"{API_BASE}/heartbeat-groups", api_key, {"name": name})
    if not resp:
        return None
    return str(resp.get("data", {}).get("id"))


def ensure_heartbeat(
    api_key: str,
    name: str,
    period_sec: int,
    grace_sec: int,
    group_id: str | None,
    existing: list[dict],
) -> dict | None:
    """Return the heartbeat record (existing or newly created)."""
    for hb in existing:
        if hb.get("attributes", {}).get("name") == name:
            return hb
    body: dict[str, Any] = {
        "name": name,
        "period": period_sec,
        "grace": grace_sec,
    }
    if group_id:
        body["heartbeat_group_id"] = group_id
    resp = _request("POST", f"{API_BASE}/heartbeats", api_key, body)
    if not resp:
        return None
    return resp.get("data")


def main() -> int:
    api_key = os.environ.get("BETTERSTACK_API_KEY", "").strip()
    if not api_key:
        print("ERROR: BETTERSTACK_API_KEY env not set", file=sys.stderr)
        return 2

    print("# Better Stack heartbeats — paste into .env", file=sys.stderr)
    print("# Source: scripts/orchestrator/betterstack_setup.py")
    print("# Generated: $(date -u)")
    print("")

    existing_groups = list_heartbeat_groups(api_key)
    existing_hbs = list_heartbeats(api_key)

    group_ids: dict[str, str | None] = {}
    for gname in GROUP_NAMES:
        gid = ensure_group(api_key, gname, existing_groups)
        group_ids[gname] = gid
        print(f"# group: {gname} → id={gid}", file=sys.stderr)

    for name, period, grace, group_name in HEARTBEATS:
        hb = ensure_heartbeat(api_key, name, period, grace, group_ids.get(group_name), existing_hbs)
        if not hb:
            print(f"# {name}: CREATE FAILED — review stderr", file=sys.stderr)
            continue
        attrs = hb.get("attributes", {})
        url = attrs.get("url") or ""
        env_key = "BETTERSTACK_HB_" + name.upper().replace("-", "_")
        print(f"{env_key}={url}")

    print("", file=sys.stderr)
    print(
        "# Append the KEY=VALUE lines above to /home/elliotbot/.config/agency-os/.env",
        file=sys.stderr,
    )
    print(
        '# Then wire `curl -fsS -m 5 "$BETTERSTACK_HB_<NAME>" >/dev/null 2>&1 || true`',
        file=sys.stderr,
    )
    print("# as the LAST line of each scheduled process script.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
