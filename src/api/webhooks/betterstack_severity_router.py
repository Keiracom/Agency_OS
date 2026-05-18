"""betterstack_severity_router.py — KEI-20 severity → channel routing.

Closes Linear KEI-20 / bd Agency_OS-lrcvie P0.

The Better Stack webhook receiver at src/api/webhooks/betterstack.py already
creates a Linear KEI for every incoming incident. KEI-20 layers Slack
notification on top, routed by severity:

    P0 (critical)        → #ceo         (C0B2PM3TV0B)
    P1 (high)            → #execution   (C0B3QB0K1GQ)
    P2 / P3 / P4 / lower → #alerts      (C0B2EJU53EK)

This module is pure-function so it can be exercised against synthetic
payloads without booting FastAPI or hitting Slack. The receiver wires it in
as a fail-open step alongside the existing Linear dispatch — a Slack post
failure (network blip, fake-token in tests, missing scope) must never block
the incident from reaching Linear.

Severity-field discovery:
  Better Stack's incident webhook payload doesn't have a stable
  documented `priority` field. Empirically (probed against the
  attributes dict from /api/v2/incidents on 2026-05-18) the routing
  signal lives in one of:
      attributes.priority           — "P0" / "P1" / "high" / etc.
      attributes.severity           — same shape on heartbeat events
      attributes.metadata.Priority  — operator-set tag on monitor
  This module reads ALL three; first non-empty wins. Anything that
  doesn't parse as P0 / P1 falls through to the "alerts" bucket so we
  never silently drop a routing decision.
"""

from __future__ import annotations

import re
from typing import Any

CHANNEL_CEO = "C0B2PM3TV0B"
CHANNEL_EXECUTION = "C0B3QB0K1GQ"
CHANNEL_ALERTS = "C0B2EJU53EK"

# Canonical bucket names — receiver logs / metrics consume these strings.
SEVERITY_P0 = "P0"
SEVERITY_P1 = "P1"
SEVERITY_OTHER = "OTHER"

# Synonyms accepted from Better Stack payloads. Any token not in P0/P1 falls
# through to the lower bucket — alerts.
_P0_TOKENS = frozenset({"p0", "critical", "sev0", "sev-0", "urgent"})
_P1_TOKENS = frozenset({"p1", "high", "sev1", "sev-1"})

_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]+")


def extract_severity_token(payload: dict[str, Any]) -> str:
    """Return the raw severity token from a Better Stack incident payload.

    Searches (in order): attributes.priority, attributes.severity,
    attributes.metadata.Priority. Returns "" if no value found — caller
    treats that as "OTHER" (routes to #alerts).
    """
    record = payload.get("data") or payload
    if isinstance(record, list):
        record = record[0] if record else {}
    attrs = (record or {}).get("attributes") or {}
    candidates = (
        attrs.get("priority"),
        attrs.get("severity"),
        (attrs.get("metadata") or {}).get("Priority"),
    )
    for candidate in candidates:
        if candidate is None:
            continue
        token = str(candidate).strip()
        if token:
            return token
    return ""


def classify(token: str) -> str:
    """Map a raw severity token to SEVERITY_P0 / SEVERITY_P1 / SEVERITY_OTHER.

    Case-insensitive; matches synonyms (critical / urgent / high / sev0 …).
    Empty / unknown → SEVERITY_OTHER so the unknown-case routes to #alerts
    rather than silently dropping.
    """
    if not token:
        return SEVERITY_OTHER
    # Normalise: pick the first alphanumeric word, lowercase. Handles "P0",
    # "P0 - critical", "sev-0", " P1 ", etc.
    match = _TOKEN_RE.search(token)
    if not match:
        return SEVERITY_OTHER
    norm = match.group(0).strip().lower()
    if norm in _P0_TOKENS:
        return SEVERITY_P0
    if norm in _P1_TOKENS:
        return SEVERITY_P1
    return SEVERITY_OTHER


def severity_to_channel(severity: str) -> str:
    """Map a classified severity bucket to a Slack channel ID."""
    if severity == SEVERITY_P0:
        return CHANNEL_CEO
    if severity == SEVERITY_P1:
        return CHANNEL_EXECUTION
    return CHANNEL_ALERTS


def route(payload: dict[str, Any]) -> tuple[str, str]:
    """One-shot: extract severity from payload + return (bucket, channel_id).

    Caller posts to channel_id; bucket is for logging / metrics.
    """
    severity = classify(extract_severity_token(payload))
    return severity, severity_to_channel(severity)
