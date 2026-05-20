"""KEI-194 — JWT ratified_decisions_hash rotation tests.

Covers: short-TTL mint, hash-bearing verify, mismatch exception,
auto_reissue_jwt, compute_ratified_decisions_hash determinism, Weaviate
unreachable fail-open, and legacy-token warning-not-blocking fallback.

All Weaviate calls are mocked via monkeypatch — no live Weaviate required.
"""

from __future__ import annotations

import jwt
import pytest

import src.dispatcher.ratified_hash as ratified_hash_mod
from src.dispatcher.container_jwt import (
    DEFAULT_EXPIRES_IN_SECONDS,
    RATIFIED_HASH_TTL_SECONDS,
    RatifiedHashMismatchError,
    mint_container_jwt,
    verify_container_jwt,
)
from src.dispatcher.ratified_hash import (
    WEAVIATE_UNREACHABLE_SENTINEL,
    auto_reissue_jwt,
    compute_ratified_decisions_hash,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_HASH = "abc123deadbeef"
TENANT = "tenant-kei194"


def _fake_client_returning(objects: list[dict]):
    """Build a fake Weaviate client that returns `objects` from the query chain."""

    class _FakeQuery:
        def get(self, *_a, **_kw):
            return self

        def with_additional(self, *_a, **_kw):
            return self

        def do(self):
            return {
                "data": {
                    "Get": {
                        "global_governance_patterns": objects,
                    }
                }
            }

    class _FakeClient:
        query = _FakeQuery()

    return _FakeClient()


def _make_objects(*pairs: tuple[str, str]) -> list[dict]:
    """Build fake Weaviate objects from (uuid, ratified_date) pairs."""
    return [{"_additional": {"id": uid}, "ratified_date": rd} for uid, rd in pairs]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv("CONTAINER_JWT_SECRET", "test-secret-kei194")
    monkeypatch.delenv("ENVIRONMENT", raising=False)


@pytest.fixture()
def _fake_weaviate(monkeypatch):
    """Provide a fake Weaviate client with 5 ratified decisions."""
    objects = _make_objects(
        ("aaaaaaaa-0000-0000-0000-000000000001", "2026-01-01"),
        ("aaaaaaaa-0000-0000-0000-000000000002", "2026-01-02"),
        ("aaaaaaaa-0000-0000-0000-000000000003", "2026-01-03"),
        ("aaaaaaaa-0000-0000-0000-000000000004", "2026-01-04"),
        ("aaaaaaaa-0000-0000-0000-000000000005", "2026-01-05"),
    )
    monkeypatch.setattr(ratified_hash_mod, "_weaviate_client", _fake_client_returning(objects))
    return objects


# ---------------------------------------------------------------------------
# Test 1 — mint with ratified_decisions_hash=None → legacy behaviour unchanged
# ---------------------------------------------------------------------------


def test_mint_no_hash_uses_default_ttl():
    """Legacy mint (no hash kwarg) must use DEFAULT_EXPIRES_IN_SECONDS TTL."""
    tok = mint_container_jwt(TENANT)
    claims = jwt.decode(
        tok,
        "test-secret-kei194",
        algorithms=["HS256"],
    )
    assert claims["exp"] - claims["iat"] == DEFAULT_EXPIRES_IN_SECONDS
    assert "ratified_decisions_hash" not in claims


# ---------------------------------------------------------------------------
# Test 2 — mint with hash → TTL defaults to RATIFIED_HASH_TTL_SECONDS + claim present
# ---------------------------------------------------------------------------


def test_mint_with_hash_uses_short_ttl():
    tok = mint_container_jwt(TENANT, ratified_decisions_hash=FAKE_HASH)
    claims = jwt.decode(tok, "test-secret-kei194", algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] == RATIFIED_HASH_TTL_SECONDS
    assert claims["ratified_decisions_hash"] == FAKE_HASH


# ---------------------------------------------------------------------------
# Test 3 — explicit expires_in_seconds overrides short-TTL default
# ---------------------------------------------------------------------------


def test_mint_with_hash_explicit_ttl_wins():
    tok = mint_container_jwt(TENANT, ratified_decisions_hash=FAKE_HASH, expires_in_seconds=600)
    claims = jwt.decode(tok, "test-secret-kei194", algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] == 600


# ---------------------------------------------------------------------------
# Test 4 — verify on hash-less token → no exception, returns claims
# ---------------------------------------------------------------------------


def test_verify_legacy_token_passes(monkeypatch):
    """Hash-less token must verify without exception (warning-not-blocking)."""
    # No hash in token; also no Weaviate needed
    monkeypatch.setattr(ratified_hash_mod, "_weaviate_client", None)
    tok = mint_container_jwt(TENANT)
    claims = verify_container_jwt(tok)
    assert claims["tenant_id"] == TENANT


# ---------------------------------------------------------------------------
# Test 5 — verify hashed token + live hash matches → returns claims silently
# ---------------------------------------------------------------------------


def test_verify_hashed_token_match(_fake_weaviate, monkeypatch):
    live = compute_ratified_decisions_hash()
    tok = mint_container_jwt(TENANT, ratified_decisions_hash=live)
    claims = verify_container_jwt(tok)
    assert claims["tenant_id"] == TENANT
    assert claims["ratified_decisions_hash"] == live


# ---------------------------------------------------------------------------
# Test 6 — verify hashed token + live hash MISMATCHES → RatifiedHashMismatchError
# ---------------------------------------------------------------------------


def test_verify_hashed_token_mismatch_raises(_fake_weaviate):
    stale_hash = "stale-hash-999"
    tok = mint_container_jwt(TENANT, ratified_decisions_hash=stale_hash)
    with pytest.raises(RatifiedHashMismatchError):
        verify_container_jwt(tok)


# ---------------------------------------------------------------------------
# Test 7 — auto_reissue_jwt returns NEW token with current live hash
# ---------------------------------------------------------------------------


def test_auto_reissue_jwt(_fake_weaviate):
    live = compute_ratified_decisions_hash()
    old_tok = mint_container_jwt(TENANT, ratified_decisions_hash="old-stale")
    new_tok = auto_reissue_jwt(old_tok, TENANT)
    new_claims = jwt.decode(new_tok, "test-secret-kei194", algorithms=["HS256"])
    assert new_claims["tenant_id"] == TENANT
    assert new_claims["ratified_decisions_hash"] == live


# ---------------------------------------------------------------------------
# Test 8 — compute_ratified_decisions_hash deterministic across 2 calls
# ---------------------------------------------------------------------------


def test_compute_hash_deterministic(_fake_weaviate):
    h1 = compute_ratified_decisions_hash()
    h2 = compute_ratified_decisions_hash()
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


# ---------------------------------------------------------------------------
# Test 9 — hash is ordering-stable (Weaviate returns different order)
# ---------------------------------------------------------------------------


def test_compute_hash_ordering_stable(monkeypatch):
    objects_asc = _make_objects(
        ("aaaaaaaa-0000-0000-0000-000000000001", "2026-01-01"),
        ("aaaaaaaa-0000-0000-0000-000000000002", "2026-01-02"),
    )
    objects_desc = list(reversed(objects_asc))

    monkeypatch.setattr(ratified_hash_mod, "_weaviate_client", _fake_client_returning(objects_asc))
    h1 = compute_ratified_decisions_hash()

    monkeypatch.setattr(ratified_hash_mod, "_weaviate_client", _fake_client_returning(objects_desc))
    h2 = compute_ratified_decisions_hash()

    assert h1 == h2


# ---------------------------------------------------------------------------
# Test 10 — Weaviate unreachable → sentinel + no exception (fail-open)
# ---------------------------------------------------------------------------


def test_compute_hash_weaviate_unreachable(monkeypatch):
    monkeypatch.setattr(ratified_hash_mod, "_weaviate_client", None)
    # Also prevent lazy-init from connecting
    monkeypatch.setattr(ratified_hash_mod, "_build_weaviate_client", lambda: None)
    result = compute_ratified_decisions_hash()
    assert result == WEAVIATE_UNREACHABLE_SENTINEL


# ---------------------------------------------------------------------------
# Test 11 — legacy-token warning emitted for hash-less tokens
# ---------------------------------------------------------------------------


def test_legacy_token_logs_warning(caplog, monkeypatch):
    """verify_container_jwt on hash-less token must emit a deprecation warning."""
    import logging  # noqa: PLC0415

    monkeypatch.setattr(ratified_hash_mod, "_weaviate_client", None)
    tok = mint_container_jwt(TENANT)
    with caplog.at_level(logging.WARNING, logger="src.dispatcher.container_jwt"):
        verify_container_jwt(tok)
    assert any("ratified_decisions_hash" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Test 12 — JWT shape: hashed token has exactly 5 expected keys
# ---------------------------------------------------------------------------


def test_hashed_token_jwt_shape():
    tok = mint_container_jwt(TENANT, ratified_decisions_hash=FAKE_HASH)
    claims = jwt.decode(tok, "test-secret-kei194", algorithms=["HS256"])
    assert set(claims.keys()) == {"tenant_id", "scope", "iat", "exp", "ratified_decisions_hash"}
