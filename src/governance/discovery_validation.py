"""discovery_validation.py — KEI-55 discovery validation governance.

Public API:
    classify_tier(text, ratified_rules) -> tuple[int, str]
    submit_discovery(text, agent, kei, ratified_rules, environment_hash) -> str
    submit_concur(discovery_id, peer_callsign) -> bool
    promote_to_permanent(discovery_id) -> bool
    challenge(discovery_id, challenged_by_callsign, counter_finding_text) -> bool
    expire_stale_staging(now=None) -> dict
    _notify_dave(discovery_id, text)  (helper — best-effort only)

Transport: urllib only (no third-party HTTP deps). Psycopg not needed here —
all persistence is Weaviate-native via /v1/objects and /v1/graphql.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT = os.environ.get("WEAVIATE_PORT", "8090")
WEAVIATE_BASE = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"  # NOSONAR python:S5332 loopback-only

STAGING_COLLECTION = "Staging_discoveries"
PERMANENT_COLLECTION = "Discoveries"

# Tier expiry windows.
_TIER_EXPIRY: dict[int, timedelta] = {
    1: timedelta(hours=24),
    2: timedelta(hours=48),
    3: timedelta(hours=72),
}

# Regex for architecture-claim language that signals tier-2.
_ARCH_PATTERN = re.compile(
    r"\b(use\s+\w+\s+instead\s+of\s+\w+|architecture|design\s+decision|approach\s+selection)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# HTTP helpers (mirror tool_call_log_indexer.py)
# ---------------------------------------------------------------------------


def _http_request(
    method: str,
    path: str,
    body: dict | None = None,
    timeout: float = 10.0,
) -> Any:
    """Open a urllib request against WEAVIATE_BASE. Returns the response object."""
    url = f"{WEAVIATE_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urlrequest.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    return urlrequest.urlopen(req, timeout=timeout)  # noqa: S310 — fixed loopback URL


def _read_response(resp: Any) -> dict:
    """Decode a urllib response object to a dict."""
    raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------


def classify_tier(text: str, ratified_rules: list[str]) -> tuple[int, str]:
    """Return (tier, reason) based on text content and known ratified rules.

    Tier 3: text contradicts any ratified ceo:rule:* entry (simple keyword
    overlap — caller supplies the rule text, no internal query).
    Tier 2: text matches architecture-claim language regex.
    Tier 1: everything else.
    """
    text_lower = text.lower()
    for rule in ratified_rules:
        # Contradiction heuristic: any multi-word phrase from the rule appears
        # in the text alongside negation or "instead" language.
        words = [w.strip(".,;:") for w in rule.lower().split() if len(w) > 4]
        overlap = [w for w in words if w in text_lower]
        if len(overlap) >= 3:  # noqa: PLR2004 — 3-word overlap threshold
            negation_nearby = bool(
                re.search(
                    r"\b(not|never|instead|wrong|incorrect|contradicts|override|without|may|can|could)\b",
                    text_lower,
                )
            )
            if negation_nearby:
                return (3, f"contradicts ratified rule (overlap: {overlap[:3]})")

    if _ARCH_PATTERN.search(text):
        return (2, "matches architecture-claim language pattern")

    return (1, "no architecture claims or rule contradictions detected")


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


def submit_discovery(
    text: str,
    agent: str,
    kei: str,
    ratified_rules: list[str],
    environment_hash: str = "prod",
) -> str:
    """Classify, build and POST a discovery to Staging_discoveries.

    Returns the Weaviate object id. Idempotent — deterministic UUID means
    a repeat submit with the same (agent, text, kei) is a 422 no-op.
    """
    tier, reason = classify_tier(text, ratified_rules)
    now = datetime.now(UTC)
    expires_at = now + _TIER_EXPIRY[tier]
    # Deterministic id so re-submits are idempotent (422 = already exists).
    det_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{agent}:{kei}:{text}"))

    doc = {
        "class": STAGING_COLLECTION,
        "id": det_id,
        "properties": {
            "raw_text": text,
            "environment_hash": environment_hash,
            "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": agent,
            "kei": kei,
            "validation_tier": tier,
            "tier_classification_reason": reason,
            "state": "staging",
            "submitted_by": agent,
            "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "concur_callsign": "",
            "challenged_by": "",
            "counter_findings": "",
            "context_version": json.dumps(
                {"kei": kei, "date": now.strftime("%Y-%m-%d"), "software_versions": {}}
            ),
        },
    }

    try:
        with _http_request("POST", "/v1/objects", doc):
            logger.info("submit_discovery %s tier=%d id=%s", kei, tier, det_id)
    except urlerror.HTTPError as exc:
        if exc.code == 422:
            logger.info("submit_discovery %s already exists — idempotent no-op", det_id)
            return det_id
        raise

    if tier == 3:
        _notify_dave(det_id, text)

    return det_id


# ---------------------------------------------------------------------------
# Concur (tier-2 peer approval)
# ---------------------------------------------------------------------------


def submit_concur(discovery_id: str, peer_callsign: str) -> bool:
    """Record peer concurrence on a tier-2 staging discovery.

    Raises ValueError if the discovery is not tier-2.
    Returns True to signal promote_to_permanent should be called.
    """
    obj = _fetch_object(discovery_id)
    tier = obj.get("properties", {}).get("validation_tier")
    if tier != 2:  # noqa: PLR2004
        raise ValueError(f"submit_concur is only valid for tier-2 discoveries; got tier={tier}")

    patch = {
        "properties": {
            "concur_callsign": peer_callsign,
            "concur_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    }
    _patch_object(discovery_id, patch)
    logger.info(
        "submit_concur %s by %s — promote_to_permanent should follow", discovery_id, peer_callsign
    )
    return True


# ---------------------------------------------------------------------------
# Promote
# ---------------------------------------------------------------------------


def promote_to_permanent(discovery_id: str) -> bool:
    """Copy staging discovery to Discoveries collection and mark state=permanent.

    Idempotent — 422 on the POST means the permanent copy already exists.
    Returns True on success.
    """
    obj = _fetch_object(discovery_id)
    props = obj.get("properties", {})

    permanent_doc = {
        "class": PERMANENT_COLLECTION,
        "id": discovery_id,
        "properties": {
            "raw_text": props.get("raw_text", ""),
            "environment_hash": props.get("environment_hash", ""),
            "created_at": props.get("created_at", ""),
            "agent": props.get("agent", ""),
            "kei": props.get("kei", ""),
        },
    }

    try:
        with _http_request("POST", "/v1/objects", permanent_doc):
            logger.info("promote_to_permanent %s copied to Discoveries", discovery_id)
    except urlerror.HTTPError as exc:
        if exc.code == 422:
            logger.info(
                "promote_to_permanent %s already in Discoveries — idempotent no-op", discovery_id
            )
        else:
            raise

    _patch_object(discovery_id, {"properties": {"state": "permanent"}})
    logger.info("promote_to_permanent %s staging state → permanent", discovery_id)
    return True


# ---------------------------------------------------------------------------
# Challenge
# ---------------------------------------------------------------------------


def challenge(
    discovery_id: str,
    challenged_by_callsign: str,
    counter_finding_text: str,
) -> bool:
    """Transition a discovery to challenged state and record the counter finding.

    Returns True on success.
    """
    obj = _fetch_object(discovery_id)
    existing_cf = obj.get("properties", {}).get("counter_findings", "")
    appended = f"{existing_cf}\n[{challenged_by_callsign}] {counter_finding_text}".strip()

    patch = {
        "properties": {
            "state": "challenged",
            "challenged_by": challenged_by_callsign,
            "challenged_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "counter_findings": appended,
        }
    }
    _patch_object(discovery_id, patch)
    logger.info("challenge %s by %s", discovery_id, challenged_by_callsign)
    return True


# ---------------------------------------------------------------------------
# Expire stale staging
# ---------------------------------------------------------------------------


def expire_stale_staging(now: datetime | None = None) -> dict[str, int]:
    """Scan staging discoveries and promote/expire based on tier and expires_at.

    Returns counts: {tier_1_promoted, tier_2_expired, tier_3_expired,
                      tier_3_dave_notify_sent}.
    """
    now = now or datetime.now(UTC)
    counters: dict[str, int] = {
        "tier_1_promoted": 0,
        "tier_2_expired": 0,
        "tier_3_expired": 0,
        "tier_3_dave_notify_sent": 0,
    }

    staging_objects = _query_staging_objects()
    for obj in staging_objects:
        props = obj.get("properties", {})
        state = props.get("state", "")
        if state != "staging":
            continue

        expires_raw = props.get("expires_at", "")
        if not expires_raw:
            continue

        try:
            expires_dt = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(
                "expire_stale_staging: cannot parse expires_at=%r for %s",
                expires_raw,
                obj.get("id"),
            )
            continue

        if expires_dt >= now:
            continue

        tier = props.get("validation_tier", 0)
        obj_id = obj.get("id", "")

        if tier == 1:
            # Tier-1 unchallenged past deadline → auto-promote.
            promote_to_permanent(obj_id)
            counters["tier_1_promoted"] += 1
        elif tier == 2:  # noqa: PLR2004
            _patch_object(obj_id, {"properties": {"state": "expired"}})
            counters["tier_2_expired"] += 1
            logger.info("expire_stale_staging tier-2 expired %s", obj_id)
        elif tier == 3:  # noqa: PLR2004
            _patch_object(obj_id, {"properties": {"state": "expired"}})
            counters["tier_3_expired"] += 1
            _notify_dave(obj_id, props.get("raw_text", "")[:200])
            counters["tier_3_dave_notify_sent"] += 1
            logger.info("expire_stale_staging tier-3 expired %s", obj_id)

    logger.info("expire_stale_staging result: %s", counters)
    return counters


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_object(object_id: str) -> dict[str, Any]:
    """GET a Weaviate object by id from Staging_discoveries."""
    path = f"/v1/objects/{STAGING_COLLECTION}/{object_id}"
    try:
        with _http_request("GET", path) as resp:
            return _read_response(resp)
    except urlerror.HTTPError as exc:
        raise RuntimeError(f"_fetch_object {object_id} failed: HTTP {exc.code}") from exc


def _patch_object(object_id: str, patch: dict) -> None:
    """PATCH partial update on a Weaviate Staging_discoveries object."""
    path = f"/v1/objects/{STAGING_COLLECTION}/{object_id}"
    try:
        with _http_request("PATCH", path, patch):
            pass
    except urlerror.HTTPError as exc:
        raise RuntimeError(f"_patch_object {object_id} failed: HTTP {exc.code}") from exc


def _query_staging_objects() -> list[dict[str, Any]]:
    """GraphQL query for all Staging_discoveries objects."""
    query = {
        "query": """
        {
          Get {
            Staging_discoveries {
              _additional { id }
              raw_text
              agent
              kei
              validation_tier
              state
              expires_at
              challenged_by
              counter_findings
            }
          }
        }
        """
    }
    try:
        with _http_request("POST", "/v1/graphql", query) as resp:
            data = _read_response(resp)
    except OSError as exc:
        logger.error("_query_staging_objects: Weaviate unreachable — %s", exc)
        return []

    items = (data.get("data", {}).get("Get", {}).get("Staging_discoveries", [])) or []
    # Normalise: promote _additional.id to top-level id for uniform access.
    result = []
    for item in items:
        additional = item.pop("_additional", {})
        item["id"] = additional.get("id", "")
        result.append({"id": item["id"], "properties": item})
    return result


def _notify_dave(discovery_id: str, text: str) -> None:
    """Best-effort Slack relay notification to #ceo for tier-3 discoveries.

    Never raises — network flake must not block the discovery write.
    """
    msg = (
        f"[KEI-55] Tier-3 discovery requires Dave approval.\n"
        f"id: {discovery_id}\n"
        f"text (first 200 chars): {text[:200]}"
    )
    with contextlib.suppress(Exception):
        subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["tg", "-c", "ceo", msg],
            timeout=10,
            check=False,
        )
        logger.info("_notify_dave sent for %s", discovery_id)


# ---------------------------------------------------------------------------
# Self-tests (hit real Weaviate if reachable, skip cleanly if not)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    _SKIP_MSG = "SKIP: Weaviate unreachable at %s:%s — skipping live tests"

    def _weaviate_up() -> bool:
        try:
            with _http_request("GET", "/v1/.well-known/ready", timeout=3.0):
                return True
        except OSError:
            return False

    if not _weaviate_up():
        print(_SKIP_MSG % (WEAVIATE_HOST, WEAVIATE_PORT))
        sys.exit(0)

    print("=== KEI-55 discovery_validation self-tests ===")
    errors: list[str] = []

    # Test 1 — classify_tier classifications
    t1_result, t1_reason = classify_tier("routine operational note", [])
    assert t1_result == 1, f"expected tier 1 got {t1_result}"
    t2_result, _ = classify_tier("use psycopg instead of asyncpg for this architecture", [])
    assert t2_result == 2, f"expected tier 2 got {t2_result}"  # noqa: PLR2004
    t3_result, _ = classify_tier(
        "this contradicts the rule: never skip validation instead do it another way",
        ["never skip validation ever in this system"],
    )
    assert t3_result == 3, f"expected tier 3 got {t3_result}"  # noqa: PLR2004
    print("PASS test-1: classify_tier")

    # Test 2 — submit then check staging state
    _test_id = submit_discovery(
        text="test: routine discovery for self-test",
        agent="orion-selftest",
        kei="KEI-55",
        ratified_rules=[],
        environment_hash="test",
    )
    _obj = _fetch_object(_test_id)
    assert _obj.get("properties", {}).get("state") == "staging", (
        "state should be staging after submit"
    )
    assert _obj.get("properties", {}).get("validation_tier") == 1, (
        "tier should be 1 for routine text"
    )
    print(f"PASS test-2: submit_discovery id={_test_id}")

    # Test 3 — submit_concur raises for tier-1
    try:
        submit_concur(_test_id, "atlas")
        errors.append("test-3: expected ValueError for tier-1 concur — not raised")
    except ValueError:
        print("PASS test-3: submit_concur raises ValueError on non-tier-2")

    # Test 4 — expire_stale_staging promotes tier-1 past deadline
    # Patch the staging object to an already-expired timestamp.
    _patch_object(_test_id, {"properties": {"expires_at": "2000-01-01T00:00:00Z"}})
    _expire_result = expire_stale_staging()
    assert _expire_result["tier_1_promoted"] >= 1, (
        f"expected >=1 tier_1_promoted, got {_expire_result}"
    )
    print(f"PASS test-4: expire_stale_staging promotes tier-1 — {_expire_result}")

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(" ", e)
        sys.exit(1)

    print("\nAll self-tests passed.")
