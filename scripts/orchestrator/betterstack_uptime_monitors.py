#!/usr/bin/env python3
"""betterstack_uptime_monitors.py — KEI Better Stack uptime HTTP monitors.

Per Dave directive ts ~1778588500 + Elliot dispatch, PR-B of 4. One-shot
operator script that creates uptime HTTP monitors via Better Stack API v2.

3 publicly-monitorable services land in this PR:
  - agencyxos.ai (Vercel)
  - Supabase REST API (project jatzvazlbusedwsnqxzr)
  - Railway Prefect dashboard URL

2 services flagged as GOV-9 unresolved (alternative-strategy options
documented in PR description):
  - Vultr VPS health endpoint — no default endpoint exists on Vultr instances
    (verified per Vultr API docs). Options: (i) /healthz on a small Flask app
    bound to a public port + Vultr firewall opening; (ii) monitor a service
    we know runs publicly (e.g., the slack listener — but Slack-bot tokens
    don't expose a public health URL); (iii) defer + monitor only via the
    Agent Team heartbeat sweep. Lean (iii) — already covered by PR-A.
  - Cognee service (port 8000 localhost) — external Better Stack can't hit
    127.0.0.1. Options: (i) expose via firewall + reverse-proxy /healthz;
    (ii) host-side polling script that emits the cognee-phase1-ingest
    heartbeat. Already covered by PR-A heartbeat pattern; cognee_ingest.py
    wire-in is a follow-up edit to Max's script.

Idempotent: re-run is safe (checks for existing monitors by URL).

Usage:
    BETTERSTACK_API_KEY=<key> python3 scripts/orchestrator/betterstack_uptime_monitors.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

API_BASE = "https://uptime.betterstack.com/api/v2"

# (pronounceable_name, url, check_frequency_sec, expected_http_status_codes).
# 60s cadence per Elliot dispatch; Better Stack tier may coerce upward (observed 180s).
# Expected codes empirically chosen from live probes:
#   - agencyxos.ai responds 200 direct, no redirect (probed 2026-05-12). Sending
#     [301,302] alongside 200 trips Better Stack 422 ("Cannot follow redirects
#     when expecting a 3xx status code") when follow_redirects=true (default).
#   - Supabase REST root returns 401 publicly (no anon-200 endpoint exists on
#     PostgREST). Accept [200,401,404] so the monitor stays UP on healthy host.
MONITORS: list[tuple[str, str, int, list[int]]] = [
    ("agencyxos.ai", "https://agencyxos.ai", 60, [200]),
    (
        "supabase-rest",
        "https://jatzvazlbusedwsnqxzr.supabase.co/rest/v1/",
        60,
        [200, 401, 404],
    ),
    ("railway-prefect", "https://prefect.keiracom.app/api/health", 60, [200, 401]),
]


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _request(method: str, url: str, api_key: str, body: dict | None = None) -> dict | None:
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_auth_headers(api_key), method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read() or "null")
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace") if exc.fp else ""
        print(f"[bs-uptime] HTTP {exc.code} on {method} {url}: {body_text[:200]}", file=sys.stderr)
        return None
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        print(f"[bs-uptime] network/parse error on {method} {url}: {exc}", file=sys.stderr)
        return None


def list_monitors(api_key: str) -> list[dict]:
    resp = _request("GET", f"{API_BASE}/monitors?per_page=100", api_key)
    if not resp:
        return []
    return resp.get("data", []) or []


def _desired_config_drift(attrs: dict, url: str, freq: int, codes: list[int]) -> bool:
    """True iff existing monitor attrs differ from desired config."""
    if attrs.get("url") != url:
        return True
    if attrs.get("expected_status_codes") != codes:
        return True
    return attrs.get("check_frequency") != freq


def ensure_monitor(
    api_key: str,
    name: str,
    url: str,
    frequency_sec: int,
    expected_codes: list[int],
    existing: list[dict],
) -> dict | None:
    """Return monitor record. Match by URL OR pronounceable_name; PATCH if config drifts.

    Idempotent: re-run safely. If a monitor with matching URL or matching name
    exists with stale/wrong config (wrong URL on manually-created record, wrong
    expected_status_codes, wrong frequency), PATCH it in place — never POST a
    duplicate.
    """
    desired_body: dict[str, Any] = {
        "url": url,
        "monitor_type": "status",
        "pronounceable_name": name,
        "check_frequency": frequency_sec,
        "expected_status_codes": expected_codes,
    }

    matched: dict | None = None
    for m in existing:
        attrs = m.get("attributes", {})
        if attrs.get("url") == url or attrs.get("pronounceable_name") == name:
            matched = m
            break

    if matched:
        attrs = matched.get("attributes", {})
        if not _desired_config_drift(attrs, url, frequency_sec, expected_codes):
            return matched
        mid = matched.get("id")
        patch_body = {
            "url": url,
            "pronounceable_name": name,
            "check_frequency": frequency_sec,
            "expected_status_codes": expected_codes,
        }
        resp = _request("PATCH", f"{API_BASE}/monitors/{mid}", api_key, patch_body)
        if not resp:
            return None
        return resp.get("data")

    resp = _request("POST", f"{API_BASE}/monitors", api_key, desired_body)
    if not resp:
        return None
    return resp.get("data")


def main() -> int:
    api_key = os.environ.get("BETTERSTACK_API_KEY", "").strip()
    if not api_key:
        print("ERROR: BETTERSTACK_API_KEY env not set", file=sys.stderr)
        return 2

    print("# Better Stack uptime monitors — operator review", file=sys.stderr)
    print("# Source: scripts/orchestrator/betterstack_uptime_monitors.py", file=sys.stderr)
    print("", file=sys.stderr)

    existing = list_monitors(api_key)

    for name, url, freq, codes in MONITORS:
        m = ensure_monitor(api_key, name, url, freq, codes, existing)
        if not m:
            print(f"# {name}: CREATE/PATCH FAILED — review stderr", file=sys.stderr)
            continue
        attrs = m.get("attributes", {})
        actual_freq = attrs.get("check_frequency", freq)
        print(
            f"# {name}: id={m.get('id')} url={attrs.get('url')} "
            f"freq_requested={freq}s freq_actual={actual_freq}s "
            f"expected_codes={attrs.get('expected_status_codes')}",
            file=sys.stderr,
        )

    print("", file=sys.stderr)
    print(
        "# GOV-9 deferred: Vultr health endpoint (no default) + Cognee localhost (covered by",
        file=sys.stderr,
    )
    print(
        "# PR-A heartbeat pattern). See PR description for alternative-strategy options.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
