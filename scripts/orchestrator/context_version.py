"""context_version.py — KEI-58 environment snapshot for discovery freshness.

Single source of truth for the `context_version` field on discovery_log rows.
Used at both append-time (via bd discover when it ships) and verify-time
(via bd verify) so drift detection compares like-for-like.

Snapshot is intentionally narrow: vendor pins that materially change LLM /
retrieval / DB behaviour, plus the kernel string. Keep narrow — adding fields
invalidates every prior discovery the next time pins move.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from functools import lru_cache
from typing import Any

VENDORED_PACKAGES = (
    "anthropic",
    "openai",
    "supabase",
    "weaviate-client",
    "llama-index",
    "cognee",
    "psycopg",
)


def _pip_show_version(pkg: str) -> str | None:
    try:
        out = subprocess.run(
            ["pip", "show", pkg],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if out.returncode != 0:
        return None
    for line in out.stdout.splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    return None


@lru_cache(maxsize=1)
def current_context_version() -> dict[str, Any]:
    """Return the current environment snapshot as the canonical context_version dict.

    Cached per-process (pip lookups are slow). Missing packages emit None —
    preserved in the dict so absence is itself a signal (e.g. a discovery
    written when openai was installed becomes STALE when openai is uninstalled).

    Override via env AGENCY_OS_CONTEXT_VERSION_JSON for tests / containers
    that don't have pip available.
    """
    override = os.environ.get("AGENCY_OS_CONTEXT_VERSION_JSON")
    if override:
        return json.loads(override)
    snapshot: dict[str, Any] = {"kernel": platform.release()}
    for pkg in VENDORED_PACKAGES:
        snapshot[pkg] = _pip_show_version(pkg)
    return snapshot


def context_drift(stored: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    """Return list of field names where stored != current. Empty = no drift.

    Treats missing stored as full-drift over all current fields (legacy rows
    pre-KEI-56 have no context_version). Caller decides how to weight that.
    """
    if not stored:
        return list(current.keys())
    return sorted({k for k in current if stored.get(k) != current.get(k)})
