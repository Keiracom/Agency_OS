#!/usr/bin/env python3
"""cognee_http_client.py — thin auth+search wrapper around the running Cognee HTTP API.

The cognee Python SDK opens its own connection to the Ladybug graph DB. The
running cognee.service holds an exclusive lock on that file. So any external
process using the SDK gets a lock error. Solution: always go through the HTTP
API the server exposes.

Public surface:
  get_token() -> str               # cached JWT
  search(query, top_k=5, search_type="GRAPH_COMPLETION") -> list/dict
  recall(query, top_k=5) -> list/dict
  health() -> dict
  ingest(text, source_path, dataset_name) -> dict  # multipart upload

Fail-open everywhere — never raises; returns empty/error dicts so hot-path
callers don't crash the agent.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = os.environ.get("COGNEE_URL", "http://127.0.0.1:8000")
LOGIN_USER = os.environ.get("COGNEE_USER", "default_user@example.com")
LOGIN_PASS = os.environ.get("COGNEE_PASS", "default_password")
TOKEN_CACHE = Path("/tmp/elliot_cognee_token.json")
TOKEN_TTL_SECONDS = 50 * 60  # JWT is 1h; refresh 10 min early


def get_token() -> str | None:
    if TOKEN_CACHE.exists():
        try:
            d = json.loads(TOKEN_CACHE.read_text())
            if d.get("expires_at", 0) > time.time():
                return d.get("token")
        except (json.JSONDecodeError, OSError):
            pass
    data = urllib.parse.urlencode({"username": LOGIN_USER, "password": LOGIN_PASS}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/auth/login",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        raw = urllib.request.urlopen(req, timeout=5).read()
        token = json.loads(raw).get("access_token")
        if token:
            with contextlib.suppress(OSError):
                TOKEN_CACHE.write_text(
                    json.dumps({"token": token, "expires_at": time.time() + TOKEN_TTL_SECONDS})
                )
            return token
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        pass
    return None


def _authed_post(path: str, body: dict, timeout: int = 30) -> dict | list | None:
    token = get_token()
    if not token:
        return None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read()
        return json.loads(raw)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP_{e.code}", "body": e.read().decode()[:300]}
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        # TimeoutError fires when urlopen's read() exceeds `timeout` mid-stream
        # (urllib does not wrap socket timeouts in URLError for read-timeouts).
        # /cognify can run minutes — without this branch the caller crashes.
        return {"error": str(e)[:200] or type(e).__name__}


def search(query: str, top_k: int = 5, search_type: str = "GRAPH_COMPLETION"):
    return _authed_post(
        "/api/v1/search", {"query": query, "top_k": top_k, "search_type": search_type}
    )


def recall(query: str, top_k: int = 5):
    return _authed_post("/api/v1/recall", {"query": query, "top_k": top_k})


def cognify(datasets: list[str] | None = None, timeout: int = 600):
    # Per Agency_OS-cuee: /add stores raw content; only /cognify rebuilds the
    # knowledge graph that GRAPH_COMPLETION recall reads. /cognify processes
    # only un-cognified pending data, so per-batch delta cost is bounded.
    body = {"datasets": datasets} if datasets else {}
    return _authed_post("/api/v1/cognify", body, timeout=timeout)


def health() -> dict:
    try:
        raw = urllib.request.urlopen(f"{BASE}/health", timeout=3).read()
        return json.loads(raw)
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        return {"status": "down", "error": str(e)[:200]}


def ingest(text: str, source_path: str = "", dataset_name: str = "governance"):
    """Add content via multipart/form-data — required by /api/v1/add."""
    token = get_token()
    if not token:
        return None
    boundary = f"----cognee_ingest_{uuid.uuid4().hex[:16]}"
    filename = source_path.replace("/", "_") if source_path else f"chunk_{uuid.uuid4().hex[:8]}.txt"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(value.encode())
        parts.append(b"\r\n")

    def add_file(name: str, fname: str, content: bytes, ctype: str = "text/markdown") -> None:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{fname}"\r\n'.encode()
        )
        parts.append(f"Content-Type: {ctype}\r\n\r\n".encode())
        parts.append(content)
        parts.append(b"\r\n")

    add_file("data", filename, text.encode("utf-8"))
    add_field("datasetName", dataset_name)
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        f"{BASE}/api/v1/add",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        raw = urllib.request.urlopen(req, timeout=120).read()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": True, "raw": raw.decode()[:300]}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP_{e.code}", "body": e.read().decode()[:300]}
    except urllib.error.URLError as e:
        return {"error": str(e)[:200]}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("health:", health())
        print("token:", "ok" if get_token() else "FAIL")
        print("search:", json.dumps(search("test", top_k=2), default=str)[:300])
