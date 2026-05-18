"""sonar_qg_verify.py — Mechanical dual-endpoint Sonar verification (KEI-189).

Queries BOTH:
  /api/issues/search?componentKeys=<k>&pullRequest=<n>&resolved=false
  /api/qualitygates/project_status?projectKey=<k>&pullRequest=<n>

APPROVE-eligibility = (issues_total == 0) AND (qg_status == 'OK').

Public SonarCloud endpoints; no auth token required for public projects
(verified KEI-89: Keiracom_Agency_OS is public).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

SONARCLOUD_BASE = "https://sonarcloud.io"

SOURCE_DOC_ISSUES = "/api/issues/search"
SOURCE_DOC_QG = "/api/qualitygates/project_status"


@dataclass
class SonarVerifyResult:
    """Combined result from both Sonar endpoints."""

    issues_total: int
    qg_status: str  # 'OK', 'ERROR', 'WARN', 'NONE', or 'ERROR_FETCHING'
    qg_conditions: list[dict[str, Any]] = field(default_factory=list)
    passing: bool = False
    error_detail: str = ""

    def __post_init__(self) -> None:
        self.passing = self.issues_total == 0 and self.qg_status == "OK"


def _fetch_json(url: str, http_client: Any | None) -> dict[str, Any]:
    """Fetch JSON from URL using http_client or stdlib urllib."""
    if http_client is not None:
        resp = http_client.get(url)
        resp.raise_for_status()
        return resp.json()
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def verify_pr(
    project_key: str,
    pr_number: int,
    *,
    base_url: str = SONARCLOUD_BASE,
    http_client: Any | None = None,
) -> SonarVerifyResult:
    """Query both Sonar endpoints and return a combined SonarVerifyResult.

    Args:
        project_key: SonarCloud component/project key.
        pr_number: Pull-request number as int.
        base_url: Override for tests (defaults to SonarCloud production).
        http_client: Injectable HTTP client (e.g. httpx.Client). Uses
            urllib.request when None.

    Returns:
        SonarVerifyResult with passing=True only when issues_total==0 AND
        qg_status=='OK'.
    """
    issues_total = 0
    qg_status = "NONE"
    qg_conditions: list[dict[str, Any]] = []
    errors: list[str] = []

    # ── Endpoint 1: issues search ───────────────────────────────────────────
    issues_url = (
        f"{base_url}{SOURCE_DOC_ISSUES}"
        f"?componentKeys={project_key}&pullRequest={pr_number}&resolved=false"
    )
    try:
        data = _fetch_json(issues_url, http_client)
        issues_total = int(data.get("total", data.get("paging", {}).get("total", 0)))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"issues endpoint error: {exc}")
        qg_status = "ERROR_FETCHING"

    # ── Endpoint 2: quality gate status ────────────────────────────────────
    qg_url = f"{base_url}{SOURCE_DOC_QG}?projectKey={project_key}&pullRequest={pr_number}"
    try:
        qg_data = _fetch_json(qg_url, http_client)
        ps = qg_data.get("projectStatus", {})
        qg_status = ps.get("status", "NONE")
        qg_conditions = ps.get("conditions", [])
    except Exception as exc:  # noqa: BLE001
        errors.append(f"qualitygates endpoint error: {exc}")
        if qg_status != "ERROR_FETCHING":
            qg_status = "ERROR_FETCHING"

    result = SonarVerifyResult(
        issues_total=issues_total,
        qg_status=qg_status,
        qg_conditions=qg_conditions,
        error_detail="; ".join(errors),
    )
    # passing computed in __post_init__; recalculate since we set fields after
    result.passing = issues_total == 0 and qg_status == "OK"
    return result


def format_review_brief_sonar_block(result: SonarVerifyResult) -> str:
    """Format Sonar findings into a review-brief text block.

    Includes BOTH endpoint URLs so agents know exactly what to query.
    Lists each failing QG condition explicitly.
    Enforces the AND-rule: APPROVE only when issues==0 AND QG==OK.
    """
    lines: list[str] = [
        "── Sonar Dual-Endpoint Verification (KEI-189) ──",
        f"  issues endpoint : {SONARCLOUD_BASE}{SOURCE_DOC_ISSUES}",
        f"    → issues_total = {result.issues_total}",
        f"  qualitygates endpoint : {SONARCLOUD_BASE}{SOURCE_DOC_QG}",
        f"    → qg_status = {result.qg_status}",
    ]

    failing = [c for c in result.qg_conditions if c.get("status") not in ("OK", "NO_VALUE")]
    if failing:
        lines.append("  Failing QG conditions:")
        for cond in failing:
            metric = cond.get("metricKey", "unknown")
            actual = cond.get("actualValue", "?")
            threshold = cond.get("errorThreshold", "?")
            lines.append(f"    • {metric}: actual={actual} threshold={threshold}")
    elif result.qg_conditions:
        lines.append("  All QG conditions: OK")

    if result.error_detail:
        lines.append(f"  Fetch errors: {result.error_detail}")

    verdict = "PASS" if result.passing else "FAIL"
    lines.append(f"  AND-rule verdict: issues_total==0 AND qg_status=='OK' → {verdict}")
    lines.append("APPROVE only when AND-rule = PASS. Issues API clean + QG=ERROR is still a HOLD.")
    return "\n".join(lines)
