"""Tests for agent_coord.status."""

import json
import os

import pytest

import src.agent_coord.status as status_mod
from src.agent_coord.status import get_peer_status, set_status


SAMPLE_AGENTS = [
    {"name": "build-2", "task": "write claims.py", "file": "src/agent_coord/claims.py", "started_at": "2026-04-16T00:00:00+00:00"},
]


@pytest.fixture(autouse=True)
def redirect_status_dir(tmp_path, monkeypatch):
    """Redirect STATUS_DIR to a tmp directory for isolation."""
    fake_dir = str(tmp_path / "status")
    os.makedirs(fake_dir, exist_ok=True)
    monkeypatch.setattr(status_mod, "STATUS_DIR", fake_dir)
    yield fake_dir


def test_set_and_get_status(redirect_status_dir):
    set_status("aiden", SAMPLE_AGENTS)
    result = get_peer_status("aiden")
    assert result is not None
    assert result["callsign"] == "aiden"
    assert result["active_agents"] == SAMPLE_AGENTS
    assert "last_updated" in result


def test_get_missing_peer(redirect_status_dir):
    result = get_peer_status("nobody")
    assert result is None


def test_atomic_write_no_partial(redirect_status_dir):
    set_status("aiden", SAMPLE_AGENTS)
    tmp_files = [f for f in os.listdir(redirect_status_dir) if ".tmp." in f]
    assert tmp_files == []


def test_set_overwrites(redirect_status_dir):
    set_status("aiden", SAMPLE_AGENTS)
    new_agents = [{"name": "test-4", "task": "run tests", "file": "tests/", "started_at": "2026-04-16T01:00:00+00:00"}]
    set_status("aiden", new_agents)

    result = get_peer_status("aiden")
    assert result["active_agents"] == new_agents
    # Ensure only one file exists
    files = [f for f in os.listdir(redirect_status_dir) if f.endswith(".json")]
    assert len(files) == 1


def test_get_tolerates_malformed_json(redirect_status_dir):
    bad_file = os.path.join(redirect_status_dir, "broken.json")
    with open(bad_file, "w") as f:
        f.write("{this is not valid json")
    result = get_peer_status("broken")
    assert result is None
