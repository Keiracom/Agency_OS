#!/usr/bin/env python3
"""staging_schema.py — KEI-55 Weaviate staging schema apply.

Creates the `Staging_discoveries` class for discovery validation governance.
Mirrors the 5 mandatory properties from schema.py and adds 11 governance
properties required by the tier-1/2/3 promotion workflow.

Idempotent: safe to re-run. Existing class is left untouched.

Usage:
    python3 infra/weaviate/staging_schema.py --host 127.0.0.1 --port 8090
    python3 infra/weaviate/staging_schema.py --dry-run   (print plan, no calls)
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

STAGING_CLASS = "Staging_discoveries"

# 5 mandatory props from schema.py — kept identical so the promotion copy
# (staging → Discoveries) is a property-compatible transfer.
MANDATORY_PROPERTIES = (
    {"name": "raw_text", "dataType": ["text"]},
    {"name": "environment_hash", "dataType": ["text"]},
    {"name": "created_at", "dataType": ["date"]},
    {"name": "agent", "dataType": ["text"]},
    {"name": "kei", "dataType": ["text"]},
)

# Governance props added by KEI-55.
STAGING_PROPERTIES = (
    {"name": "validation_tier", "dataType": ["int"]},
    {"name": "tier_classification_reason", "dataType": ["text"]},
    {"name": "state", "dataType": ["text"]},
    {"name": "concur_callsign", "dataType": ["text"]},
    {"name": "concur_at", "dataType": ["date"]},
    {"name": "challenged_by", "dataType": ["text"]},
    {"name": "challenged_at", "dataType": ["date"]},
    {"name": "tier_3_dave_notified_at", "dataType": ["date"]},
    {"name": "submitted_by", "dataType": ["text"]},
    {"name": "expires_at", "dataType": ["date"]},
    # JSON-encoded {kei,date,software_versions} — Weaviate text, deserialize on read.
    {"name": "context_version", "dataType": ["text"]},
    # Free-text counter findings appended by challenge() calls.
    {"name": "counter_findings", "dataType": ["text"]},
)

_CLASS_DEFINITION = {
    "class": STAGING_CLASS,
    "description": "KEI-55 staging tier for discovery validation governance.",
    "vectorizer": "none",
    "properties": list(MANDATORY_PROPERTIES) + list(STAGING_PROPERTIES),
}


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
    """Return the set of class names already present in the Weaviate instance."""
    try:
        data = _get(f"{base_url}/v1/schema")
    except urllib.error.HTTPError as exc:
        print(f"warn: GET /v1/schema returned HTTP {exc.code}", file=sys.stderr)
        return set()
    classes = data.get("classes") or []
    return {c.get("class") for c in classes if c.get("class")}


def apply_schema(base_url: str, dry_run: bool = False) -> int:
    """Create Staging_discoveries if absent. Returns 0 on success, 1 on error."""
    existing = existing_classes(base_url)
    if STAGING_CLASS in existing:
        print(f"  {STAGING_CLASS} → exists")
        print("plan: 0 create, 1 already exist")
        return 0

    print(f"  {STAGING_CLASS} → create")
    if dry_run:
        print("plan: 1 create (dry-run — no calls made)")
        return 0

    try:
        _post(f"{base_url}/v1/schema", _CLASS_DEFINITION)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(
            f"ERROR creating {STAGING_CLASS}: HTTP {exc.code} body={body[:200]}",
            file=sys.stderr,
        )
        return 1

    print("plan: 1 create, 0 already exist")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8090)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    # NOSONAR python:S5332 — loopback-only internal service; see schema.py for rationale.
    base = f"http://{args.host}:{args.port}"  # NOSONAR python:S5332 loopback-only
    return apply_schema(base, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
