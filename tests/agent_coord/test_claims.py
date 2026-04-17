"""Tests for agent_coord.claims."""

import json
import os
import time

import pytest

import src.agent_coord.claims as claims_mod
from src.agent_coord.claims import (
    CLAIMS_DIR,
    claim,
    is_claimed,
    release,
    scan_stale,
    _path_to_key,
)


@pytest.fixture(autouse=True)
def redirect_claims_dir(tmp_path, monkeypatch):
    """Redirect CLAIMS_DIR to a tmp directory for isolation."""
    fake_dir = str(tmp_path / "claims")
    os.makedirs(fake_dir, exist_ok=True)
    monkeypatch.setattr(claims_mod, "CLAIMS_DIR", fake_dir)
    yield fake_dir


def test_claim_happy_path(redirect_claims_dir):
    path = "src/some_module.py"
    assert claim(path, "aiden") is True
    result = is_claimed(path)
    assert result is not None
    assert result["callsign"] == "aiden"
    assert result["path"] == path
    assert result["seconds_remaining"] > 0
    assert release(path, "aiden") is True
    assert is_claimed(path) is None


def test_claim_collision(redirect_claims_dir):
    path = "src/shared.py"
    assert claim(path, "aiden") is True
    assert claim(path, "elliot") is False
    # aiden still holds it
    result = is_claimed(path)
    assert result["callsign"] == "aiden"


def test_claim_reentrant(redirect_claims_dir):
    path = "src/reentered.py"
    assert claim(path, "aiden", ttl_seconds=60) is True
    first_ts = is_claimed(path)["timestamp_utc"]
    time.sleep(0.05)
    assert claim(path, "aiden", ttl_seconds=60) is True
    second_ts = is_claimed(path)["timestamp_utc"]
    # Timestamp must be refreshed (second >= first)
    assert second_ts >= first_ts


def test_claim_expired(redirect_claims_dir):
    path = "src/expiring.py"
    # Claim with TTL=0 so it expires immediately
    assert claim(path, "aiden", ttl_seconds=0) is True
    # is_claimed should see it as expired
    assert is_claimed(path) is None
    # Another agent can now claim it
    assert claim(path, "elliot", ttl_seconds=60) is True
    assert is_claimed(path)["callsign"] == "elliot"


def test_release_wrong_callsign(redirect_claims_dir):
    path = "src/protected.py"
    assert claim(path, "aiden") is True
    assert release(path, "elliot") is False
    # Still claimed by aiden
    assert is_claimed(path) is not None


def test_release_nothing(redirect_claims_dir):
    path = "src/never_claimed.py"
    assert release(path, "aiden") is False


def test_scan_stale_finds_expired(redirect_claims_dir):
    path = "src/stale.py"
    assert claim(path, "aiden", ttl_seconds=0) is True
    stale = scan_stale()
    assert len(stale) == 1
    assert stale[0]["path"] == path
    assert stale[0]["callsign"] == "aiden"
    assert stale[0]["elapsed_seconds"] >= 0


def test_scan_stale_skips_active(redirect_claims_dir):
    path = "src/active.py"
    assert claim(path, "aiden", ttl_seconds=900) is True
    stale = scan_stale()
    assert stale == []


def test_atomic_write_no_partial_file(redirect_claims_dir):
    path = "src/atomic.py"
    assert claim(path, "aiden") is True
    # No .tmp.* files should remain
    tmp_files = [f for f in os.listdir(redirect_claims_dir) if ".tmp." in f]
    assert tmp_files == []
