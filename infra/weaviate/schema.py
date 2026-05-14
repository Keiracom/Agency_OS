#!/usr/bin/env python3
"""schema.py — KEI-48 Weaviate schema apply.

Creates the 5 collections per Dave verbatim (codebase / decisions / discoveries /
sessions / keis), each with the 5 mandatory properties from
docs/schema/weaviate-schema-requirements.md:

    raw_text          text    (required — re-embedding insurance per KEI-60)
    environment_hash  text    (required — reproducible re-embedding)
    created_at        date    (required — ISO-8601 UTC)
    agent             text    (required — callsign or 'system')
    kei               text    (optional — KEI ID that triggered the write)

Vectorizer: `none`. The agent writes vectors directly (via gemini-embedding-001
or whichever model the AGENCY_OS_EMBEDDING_MODEL env pins). Server-side
vectorization is deliberately disabled to keep model pinning explicit.

Idempotent: safe to re-run. Existing collections are left untouched (does not
overwrite or drop) — re-runs only add missing collections.

Usage:
    python3 infra/weaviate/schema.py --host 127.0.0.1 --port 8090
    python3 infra/weaviate/schema.py --dry-run   (print plan, no calls)
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

COLLECTIONS = ("codebase", "decisions", "discoveries", "sessions", "keis")

MANDATORY_PROPERTIES = (
    {"name": "raw_text", "dataType": ["text"]},
    {"name": "environment_hash", "dataType": ["text"]},
    {"name": "created_at", "dataType": ["date"]},
    {"name": "agent", "dataType": ["text"]},
    {"name": "kei", "dataType": ["text"]},
)


def _get(url: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(url: str, payload: dict, timeout: float = 10.0) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def existing_classes(base_url: str) -> set[str]:
    try:
        data = _get(f"{base_url}/v1/schema")
    except urllib.error.HTTPError as exc:
        print(f"warn: GET /v1/schema returned HTTP {exc.code}", file=sys.stderr)
        return set()
    classes = data.get("classes") or []
    return {c.get("class") for c in classes if c.get("class")}


def class_definition(name: str) -> dict:
    return {
        "class": name.capitalize(),
        "description": f"KEI-48 Agency OS — {name} collection",
        "vectorizer": "none",
        "properties": list(MANDATORY_PROPERTIES),
    }


def apply_schema(base_url: str, dry_run: bool = False) -> int:
    existing = existing_classes(base_url)
    plan = []
    for name in COLLECTIONS:
        cls = class_definition(name)
        if cls["class"] in existing:
            plan.append((name, "exists"))
            continue
        plan.append((name, "create"))
        if dry_run:
            continue
        try:
            _post(f"{base_url}/v1/schema", cls)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(
                f"ERROR creating {cls['class']}: HTTP {exc.code} body={body[:200]}",
                file=sys.stderr,
            )
            return 1

    for name, action in plan:
        print(f"  {name:12s} → {action}")
    print(
        f"plan: {sum(1 for _, a in plan if a == 'create')} create, "
        f"{sum(1 for _, a in plan if a == 'exists')} already exist"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8090)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    # NOSONAR python:S5332 — Weaviate is a loopback-only internal service
    # (default --host 127.0.0.1). HTTPS on loopback adds cert-management
    # overhead with no security benefit since there is no network attack
    # surface. If Weaviate is ever exposed beyond loopback, terminate TLS at
    # a reverse-proxy layer (nginx/caddy), not in this client.
    base = f"http://{args.host}:{args.port}"  # NOSONAR python:S5332 loopback-only
    return apply_schema(base, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
