#!/usr/bin/env python3
"""smoke_test.py — KEI-48 Weaviate install verification.

End-to-end acceptance test:

    1. GET  /v1/meta                  → Weaviate version reachable
    2. GET  /v1/schema                → 5 mandatory collections present
    3. POST /v1/objects               → insert probe object into Discoveries
    4. GET  /v1/objects/<uuid>        → retrieve by UUID, properties match
    5. DELETE /v1/objects/<uuid>      → clean up

Exits 0 on success; non-zero on first failure with verbatim error context.

Usage:
    python3 infra/weaviate/smoke_test.py --host 127.0.0.1 --port 8090
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime

EXPECTED_CLASSES = {"Codebase", "Decisions", "Discoveries", "Sessions", "Keis"}


def _req(url: str, method: str, payload: dict | None = None, timeout: float = 10.0) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def meta_probe(base: str) -> dict:
    return _req(f"{base}/v1/meta", "GET")


def schema_probe(base: str) -> set[str]:
    data = _req(f"{base}/v1/schema", "GET")
    return {c.get("class") for c in (data.get("classes") or []) if c.get("class")}


def insert_probe(base: str, obj_id: str) -> dict:
    payload = {
        "id": obj_id,
        "class": "Discoveries",
        "properties": {
            "raw_text": f"KEI-48 smoke probe — {obj_id}",
            "environment_hash": "smoke-test-fixed-hash-not-real",
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": "atlas",
            "kei": "KEI-48",
        },
        # Skip vector — vectorizer is 'none', so absent vector is fine for a metadata probe.
    }
    return _req(f"{base}/v1/objects", "POST", payload)


def fetch_probe(base: str, obj_id: str) -> dict:
    return _req(f"{base}/v1/objects/Discoveries/{obj_id}", "GET")


def delete_probe(base: str, obj_id: str) -> None:
    _req(f"{base}/v1/objects/Discoveries/{obj_id}", "DELETE")


def run(base: str) -> int:
    print(f"[1/5] GET {base}/v1/meta")
    meta = meta_probe(base)
    version = meta.get("version", "?")
    print(f"      version={version}")

    print(f"[2/5] GET {base}/v1/schema — expect classes={sorted(EXPECTED_CLASSES)}")
    classes = schema_probe(base)
    missing = EXPECTED_CLASSES - classes
    if missing:
        print(f"      FAIL: missing classes: {sorted(missing)}", file=sys.stderr)
        return 1
    print(f"      OK: all 5 classes present (found={sorted(classes & EXPECTED_CLASSES)})")

    obj_id = str(uuid.uuid4())
    print(f"[3/5] POST {base}/v1/objects (id={obj_id}, class=Discoveries)")
    insert_resp = insert_probe(base, obj_id)
    print(f"      OK: insert response id={insert_resp.get('id', '?')}")

    print(f"[4/5] GET  {base}/v1/objects/Discoveries/{obj_id}")
    fetched = fetch_probe(base, obj_id)
    rt = (fetched.get("properties") or {}).get("raw_text", "")
    if obj_id not in rt:
        print(f"      FAIL: round-trip mismatch. raw_text={rt!r}", file=sys.stderr)
        return 1
    print(f"      OK: round-trip raw_text contains obj_id={obj_id}")

    print(f"[5/5] DELETE {base}/v1/objects/Discoveries/{obj_id}")
    delete_probe(base, obj_id)
    print("      OK: probe cleaned up")

    print(f"\nKEI-48 SMOKE PASSED — Weaviate {version} reachable, schema valid, round-trip OK.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8090)
    args = p.parse_args(argv)
    # NOSONAR python:S5332 — Weaviate is loopback-only (see infra/weaviate/schema.py
    # for the full rationale). HTTPS on 127.0.0.1 adds cert-mgmt overhead with no
    # security benefit. TLS terminates at the reverse-proxy if Weaviate ever
    # listens beyond loopback.
    base = f"http://{args.host}:{args.port}"  # NOSONAR python:S5332 loopback-only
    try:
        return run(base)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:200]
        print(f"FAIL: HTTP {exc.code} on {exc.url}: {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"FAIL: URLError on {base}: {exc.reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
