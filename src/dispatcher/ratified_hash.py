"""KEI-194 — ratified_decisions_hash computation + JWT auto-reissue.

Queries Weaviate global_governance_patterns collection, sorts by UUID stably,
concatenates UUIDs + ratified_date, returns sha256 hex. Fail-open: if Weaviate
is unreachable the sentinel "weaviate-unreachable-fallback" is returned so
legacy verify paths do not false-fail during a Weaviate outage.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel returned when Weaviate is unreachable (fail-open)
WEAVIATE_UNREACHABLE_SENTINEL = "weaviate-unreachable-fallback"


def _build_weaviate_client() -> Any:
    """Build a Weaviate client from env; returns None on import or config error."""
    try:
        import os  # noqa: PLC0415

        import weaviate  # noqa: PLC0415

        url = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
        api_key = os.environ.get("WEAVIATE_API_KEY", "")
        if api_key:
            auth = weaviate.auth.AuthApiKey(api_key=api_key)
            return weaviate.Client(url=url, auth_client_secret=auth)
        return weaviate.Client(url=url)
    except Exception:  # noqa: BLE001
        return None


# Module-level client (replaced by tests via monkeypatch.setattr)
_weaviate_client: Any = None


def _get_client() -> Any:
    """Return module-level client; lazy-init on first call."""
    global _weaviate_client  # noqa: PLW0603
    if _weaviate_client is None:
        _weaviate_client = _build_weaviate_client()
    return _weaviate_client


def compute_ratified_decisions_hash() -> str:
    """Compute a stable sha256 hash of all ratified decisions in Weaviate.

    Queries global_governance_patterns, sorts by UUID, concatenates
    uuid + ratified_date for each record, then returns sha256 hex.
    Returns WEAVIATE_UNREACHABLE_SENTINEL if Weaviate is down (fail-open).
    """
    client = _get_client()
    if client is None:
        logger.warning("Weaviate client unavailable — returning sentinel hash (fail-open, KEI-194)")
        return WEAVIATE_UNREACHABLE_SENTINEL

    try:
        result = (
            client.query.get(
                "global_governance_patterns",
                ["ratified_date"],
            )
            .with_additional(["id"])
            .do()
        )
        objects = result.get("data", {}).get("Get", {}).get("global_governance_patterns", [])
        # Sort by UUID for stable ordering regardless of Weaviate return order
        objects_sorted = sorted(objects, key=lambda o: o["_additional"]["id"])
        concat = "".join(
            f"{o['_additional']['id']}{o.get('ratified_date', '')}" for o in objects_sorted
        )
        return hashlib.sha256(concat.encode()).hexdigest()
    except Exception:  # noqa: BLE001
        logger.warning("Weaviate query failed — returning sentinel hash (fail-open, KEI-194)")
        return WEAVIATE_UNREACHABLE_SENTINEL


def auto_reissue_jwt(
    old_token: str,
    tenant_id: str,
    scopes: list[str] | None = None,
) -> str:
    """Mint a fresh JWT with the current live ratified_decisions_hash.

    Called on the hash-mismatch path to give the container a valid short-TTL
    token with the updated governance hash, preserving tenant_id and scopes.
    """
    from src.dispatcher.container_jwt import mint_container_jwt  # noqa: PLC0415

    live_hash = compute_ratified_decisions_hash()
    return mint_container_jwt(
        tenant_id,
        scopes=scopes,
        ratified_decisions_hash=live_hash,
    )
