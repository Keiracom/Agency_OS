#!/usr/bin/env python3
"""sync_linear_viewer_env.py — KEI-238 helper.

Queries Linear `{ viewer { id } }` and prints `export LINEAR_VIEWER_ID=<uuid>`
ready for paste into `~/.config/agency-os/.env`. The viewer id is the user
uuid that the API key authenticates as — needed by the Linear webhook
handler to recognise + skip its own echo events.

Usage:
    python3 scripts/sync_linear_viewer_env.py
    # → export LINEAR_VIEWER_ID=f29152a3-3700-4217-a451-d6070f09de3c

Exits 0 on success, 2 on missing LINEAR_API_KEY, 1 on GraphQL failure.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

_LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"


def main() -> int:
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        print("ERROR: LINEAR_API_KEY not set", file=sys.stderr)
        return 2
    body = json.dumps({"query": "{ viewer { id name email } }"}).encode()
    req = urllib.request.Request(
        _LINEAR_GRAPHQL_URL,
        data=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read() or "null")
    except (json.JSONDecodeError, urllib.error.URLError, OSError) as exc:
        print(f"ERROR: viewer query failed: {exc}", file=sys.stderr)
        return 1
    viewer = ((payload or {}).get("data") or {}).get("viewer") or {}
    viewer_id = viewer.get("id")
    if not viewer_id:
        print(f"ERROR: no viewer.id in response: {payload}", file=sys.stderr)
        return 1
    print(f"# Linear viewer: {viewer.get('name', '?')} <{viewer.get('email', '?')}>")
    print(f"export LINEAR_VIEWER_ID={viewer_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
