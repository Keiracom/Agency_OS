"""
Gatekeeper — OPA client for completion-claim policy decisions.

Phase 1 Track A — A2. Wraps the OPA sidecar policy bundle defined in
infra/opa/policies/completion_claims.rego.

Public surface:

    >>> result = check_completion_claim(
    ...     callsign="atlas",
    ...     directive_id="GOV-PHASE1-TRACK-A",
    ...     claim_text="...",
    ...     evidence="$ pytest -q\\nOK",
    ...     target_files=["src/foo.py"],
    ...     store_writes=[
    ...         {"directive_id": "GOV-PHASE1-TRACK-A", "store": "manual"},
    ...         ...
    ...     ],
    ... )
    >>> result.allow, result.reasons
    (False, ["store writes incomplete for ..."])

Frozen-paths inputs are pulled from the registry by `check_completion_claim`
unless the caller passes them explicitly (used for tests).
"""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_OPA_URL = os.environ.get("OPA_URL", "http://localhost:8181")
DEFAULT_DECISION_PATH = "v1/data/agency/completion_claims"


def _emit_verdict(
    *,
    callsign: str,
    directive_id: str,
    claim_text: str,
    allow: bool,
    reasons: list[str],
    error: str | None = None,
) -> None:
    """Emit one governance_events row per Gatekeeper verdict (GOV-12)."""
    try:
        from src.governance._mcp_helpers import governance_event_emit
        claim_hash = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()[:16]
        governance_event_emit(
            callsign=callsign,
            event_type="gatekeeper_decision",
            event_data={
                "allow": allow,
                "reasons": reasons,
                "claim_text_sha256_16": claim_hash,
                "error": error,
            },
            tool_name="governance.gatekeeper",
            directive_id=directive_id,
        )
    except Exception:  # pragma: no cover
        pass


@dataclass
class GatekeeperResult:
    allow: bool
    reasons: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def _post_decision(
    payload: dict[str, Any],
    *,
    opa_url: str = DEFAULT_OPA_URL,
    decision_path: str = DEFAULT_DECISION_PATH,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """POST input payload to OPA, return the parsed `result` object."""
    url = f"{opa_url.rstrip('/')}/{decision_path.lstrip('/')}"
    body = {"input": payload}
    response = httpx.post(url, json=body, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data.get("result", {}) if isinstance(data, dict) else {}


def check_completion_claim(
    *,
    callsign: str,
    directive_id: str,
    claim_text: str,
    evidence: str,
    target_files: Iterable[str],
    store_writes: Iterable[dict[str, Any]],
    frozen_paths: Iterable[str] | None = None,
    opa_url: str = DEFAULT_OPA_URL,
) -> GatekeeperResult:
    """Evaluate the OPA completion-claims policy.

    `frozen_paths` defaults to the live frozen_artifacts registry if not
    supplied — pass an explicit list in tests to avoid the Supabase round-trip.
    """
    if frozen_paths is None:
        from src.governance.freeze import list_frozen_paths
        frozen_paths = list_frozen_paths()

    payload = {
        "callsign": callsign,
        "directive_id": directive_id,
        "claim_text": claim_text,
        "evidence": evidence,
        "target_files": list(target_files),
        "store_writes": list(store_writes),
        "frozen_paths": list(frozen_paths),
    }

    try:
        result = _post_decision(payload, opa_url=opa_url)
    except httpx.HTTPError as exc:
        logger.warning("Gatekeeper OPA request failed: %s", exc)
        err_reasons = [f"opa request failed: {exc}"]
        _emit_verdict(
            callsign=callsign, directive_id=directive_id, claim_text=claim_text,
            allow=False, reasons=err_reasons, error=str(exc),
        )
        return GatekeeperResult(
            allow=False,
            reasons=err_reasons,
            raw={"error": str(exc)},
        )

    allow = bool(result.get("allow", False))
    reasons = list(result.get("deny_reasons", []) or [])
    _emit_verdict(
        callsign=callsign, directive_id=directive_id, claim_text=claim_text,
        allow=allow, reasons=reasons,
    )
    return GatekeeperResult(allow=allow, reasons=reasons, raw=result)


def opa_health(opa_url: str = DEFAULT_OPA_URL, timeout: float = 2.0) -> bool:
    """Lightweight health probe against OPA's built-in /health."""
    try:
        url = f"{opa_url.rstrip('/')}/health"
        return httpx.get(url, timeout=timeout).status_code == 200
    except httpx.HTTPError:
        return False
