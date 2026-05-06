#!/usr/bin/env python3
"""Register the Python `governance` VirtualObject with the Restate server.

Runs after the Python service container is healthy on Railway. POSTs the
service URI to Restate's admin /deployments endpoint so Restate can route
incoming directive_start/complete/get_state calls to our handlers.

Usage:
    RESTATE_ADMIN_URL=https://restate-server-production-60d4.up.railway.app:9070 \
    PYTHON_SERVICE_URI=http://restate-py-service.railway.internal:9070 \
    python3 scripts/register_restate_service.py
"""

from __future__ import annotations

import os
import sys

import httpx

ADMIN_URL = os.environ.get("RESTATE_ADMIN_URL", "http://localhost:9070")
SERVICE_URI = os.environ.get(
    "PYTHON_SERVICE_URI",
    "http://restate-py-service.railway.internal:9070",
)


def register() -> int:
    url = f"{ADMIN_URL.rstrip('/')}/deployments"
    payload = {"uri": SERVICE_URI, "force": False}
    print(f"POST {url} with {payload}", file=sys.stderr)
    try:
        resp = httpx.post(url, json=payload, timeout=30)
    except httpx.HTTPError as exc:
        print(f"register failed: {exc}", file=sys.stderr)
        return 2
    if resp.status_code >= 400:
        print(f"non-2xx ({resp.status_code}): {resp.text}", file=sys.stderr)
        return 1
    print(resp.text)
    return 0


def list_services() -> int:
    url = f"{ADMIN_URL.rstrip('/')}/services"
    try:
        resp = httpx.get(url, timeout=15)
        print(resp.text)
        return 0 if resp.status_code < 400 else 1
    except httpx.HTTPError as exc:
        print(f"list failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        sys.exit(list_services())
    sys.exit(register())
