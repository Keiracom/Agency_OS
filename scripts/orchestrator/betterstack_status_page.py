#!/usr/bin/env python3
"""betterstack_status_page.py — KEI Better Stack public status page bootstrap.

PR-D of the Better Stack bundle. One-shot operator script that creates ONE
public status page named "Agency OS" + attaches the 3 uptime monitors from
PR-B and the 5 heartbeats from PR-A as page resources. Free-tier-supported
(empirical 2026-05-12: POST /status-pages with timezone returns 201).

Idempotent: re-runs reaffirm attachments by name; existing page (matched by
subdomain) is reused; existing resources are not duplicated.

Usage:
    BETTERSTACK_API_KEY=<key> python3 scripts/orchestrator/betterstack_status_page.py

After running this once, the public URL is:
    https://<SUBDOMAIN>.betteruptime.com

Env overrides (tests + non-default subdomains):
    AGENCY_OS_BETTERSTACK_API_BASE — API root (default uptime.betterstack.com/api/v2)
    AGENCY_OS_BETTERSTACK_STATUS_SUBDOMAIN — page subdomain (default 'agency-os')

Exits 0 on success or clean no-op; non-zero only on missing API key.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API_BASE_DEFAULT = "https://uptime.betterstack.com/api/v2"

# Page identity. Subdomain is the slug under .betteruptime.com.
DEFAULT_SUBDOMAIN = "agency-os"
PAGE_BODY = {
    "company_name": "Agency OS",
    "company_url": "https://agencyxos.ai",
    "contact_url": "mailto:dvidstephens@gmail.com",
    "timezone": "UTC",
}

# Resources to attach (name → matched by attribute on /monitors or /heartbeats).
# Names match the pronounceable_name set in betterstack_uptime_monitors.py +
# betterstack_setup.py. Public-facing labels rendered on the status page.
MONITOR_RESOURCES: list[tuple[str, str]] = [
    ("agencyxos.ai", "Agency OS marketing site"),
    ("supabase-rest", "Supabase REST API"),
    ("railway-prefect", "Railway Prefect server"),
]
HEARTBEAT_RESOURCES: list[tuple[str, str]] = [
    ("elliot-polling-loop", "Elliot polling loop (KEI-17)"),
    ("cognee-phase1-ingest", "Cognee Phase 1 ingestion"),
    ("prefect-pipeline", "Prefect orchestrator flow"),
    ("central-listener", "Slack central listener"),
    ("agency-os-discovery", "Agency OS discovery pipeline"),
]


def _api_base() -> str:
    return os.environ.get("AGENCY_OS_BETTERSTACK_API_BASE", API_BASE_DEFAULT)


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _request(method: str, path: str, api_key: str, body: dict | None = None) -> dict | None:
    """Best-effort BS API call. Returns parsed JSON or None on error."""
    url = f"{_api_base()}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_auth_headers(api_key), method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read() or "null")
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace") if exc.fp else ""
        print(f"[bs-status] HTTP {exc.code} on {method} {url}: {body_text[:200]}", file=sys.stderr)
        return None
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        print(f"[bs-status] network/parse error on {method} {url}: {exc}", file=sys.stderr)
        return None


def list_status_pages(api_key: str) -> list[dict]:
    resp = _request("GET", "/status-pages?per_page=50", api_key)
    return (resp or {}).get("data", []) or []


def list_monitors(api_key: str) -> list[dict]:
    resp = _request("GET", "/monitors?per_page=100", api_key)
    return (resp or {}).get("data", []) or []


def list_heartbeats(api_key: str) -> list[dict]:
    resp = _request("GET", "/heartbeats?per_page=100", api_key)
    return (resp or {}).get("data", []) or []


def list_resources(api_key: str, page_id: str) -> list[dict]:
    resp = _request("GET", f"/status-pages/{page_id}/resources?per_page=100", api_key)
    return (resp or {}).get("data", []) or []


def ensure_page(api_key: str, subdomain: str, existing: list[dict]) -> dict | None:
    """Return the status-page record. Match by subdomain; create if absent."""
    for p in existing:
        if p.get("attributes", {}).get("subdomain") == subdomain:
            return p
    body = {**PAGE_BODY, "subdomain": subdomain}
    resp = _request("POST", "/status-pages", api_key, body)
    return (resp or {}).get("data") if resp else None


def _resource_already_attached(
    existing: list[dict], resource_id: int, resource_type: str
) -> bool:
    for r in existing:
        attrs = r.get("attributes", {})
        if attrs.get("resource_id") == resource_id and attrs.get("resource_type") == resource_type:
            return True
    return False


def attach_resource(
    api_key: str,
    page_id: str,
    resource_id: int,
    resource_type: str,
    public_name: str,
    existing: list[dict],
) -> dict | None:
    if _resource_already_attached(existing, resource_id, resource_type):
        return next(
            (
                r
                for r in existing
                if r.get("attributes", {}).get("resource_id") == resource_id
                and r.get("attributes", {}).get("resource_type") == resource_type
            ),
            None,
        )
    body = {
        "resource_id": resource_id,
        "resource_type": resource_type,
        "public_name": public_name,
    }
    resp = _request("POST", f"/status-pages/{page_id}/resources", api_key, body)
    return (resp or {}).get("data") if resp else None


def _by_name(records: list[dict], name: str, attr: str = "pronounceable_name") -> dict | None:
    for r in records:
        if r.get("attributes", {}).get(attr) == name:
            return r
    return None


def _by_heartbeat_name(records: list[dict], name: str) -> dict | None:
    return _by_name(records, name, attr="name")


def main() -> int:
    api_key = os.environ.get("BETTERSTACK_API_KEY", "").strip()
    if not api_key:
        print("ERROR: BETTERSTACK_API_KEY env not set", file=sys.stderr)
        return 2

    subdomain = os.environ.get("AGENCY_OS_BETTERSTACK_STATUS_SUBDOMAIN", DEFAULT_SUBDOMAIN)

    print("# Better Stack status page — operator review", file=sys.stderr)
    print(f"# Subdomain: {subdomain}", file=sys.stderr)

    pages = list_status_pages(api_key)
    page = ensure_page(api_key, subdomain, pages)
    if not page:
        print("# ERROR: status page create/fetch failed — review stderr", file=sys.stderr)
        return 1

    page_id = str(page.get("id"))
    public_url = f"https://{subdomain}.betteruptime.com"
    print(f"# Page id={page_id}  url={public_url}", file=sys.stderr)

    monitors = list_monitors(api_key)
    heartbeats = list_heartbeats(api_key)
    existing_resources = list_resources(api_key, page_id)

    attached = 0
    for mon_name, public_name in MONITOR_RESOURCES:
        m = _by_name(monitors, mon_name)
        if not m:
            print(f"#   SKIP monitor '{mon_name}' — not found in BS", file=sys.stderr)
            continue
        rid = int(m["id"])
        result = attach_resource(api_key, page_id, rid, "Monitor", public_name, existing_resources)
        if result:
            attached += 1
            print(f"#   monitor   '{mon_name}' (id={rid}) → '{public_name}'", file=sys.stderr)

    for hb_name, public_name in HEARTBEAT_RESOURCES:
        hb = _by_heartbeat_name(heartbeats, hb_name)
        if not hb:
            print(f"#   SKIP heartbeat '{hb_name}' — not found in BS", file=sys.stderr)
            continue
        rid = int(hb["id"])
        result = attach_resource(api_key, page_id, rid, "Heartbeat", public_name, existing_resources)
        if result:
            attached += 1
            print(f"#   heartbeat '{hb_name}' (id={rid}) → '{public_name}'", file=sys.stderr)

    print(f"# done — {attached} resource(s) attached/affirmed. Public URL: {public_url}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
