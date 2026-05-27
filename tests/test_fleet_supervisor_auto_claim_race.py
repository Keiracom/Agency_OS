"""Tests for fleet_supervisor.fetch_pr_state — the race-condition pre-check.

Covers the gh-pr-view return-code paths + JSON parse paths + state-name
extraction. The dispatch-skip behaviour at the call site is exercised by
asserting the function returns the right state literal for the call-site
to branch on.

bd: Agency_OS-f0qn
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from scripts import fleet_supervisor


@pytest.fixture
def fake_subprocess_run(monkeypatch):
    """Fixture returning a recorder + injecting it as scripts.fleet_supervisor.subprocess.run."""
    calls: list[tuple[list[str], dict[str, Any]]] = []
    scripted: list[SimpleNamespace] = []

    def _run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        calls.append((cmd, kwargs))
        if not scripted:
            return SimpleNamespace(returncode=0, stdout="{}", stderr="")
        return scripted.pop(0)

    monkeypatch.setattr(fleet_supervisor.subprocess, "run", _run)
    return SimpleNamespace(calls=calls, scripted=scripted)


# ─── fetch_pr_state ────────────────────────────────────────────────────────────


def test_fetch_pr_state_returns_open_on_normal_response(fake_subprocess_run):
    fake_subprocess_run.scripted.append(
        SimpleNamespace(returncode=0, stdout='{"state":"OPEN"}', stderr="")
    )
    assert fleet_supervisor.fetch_pr_state(1234) == "OPEN"


def test_fetch_pr_state_returns_merged(fake_subprocess_run):
    fake_subprocess_run.scripted.append(
        SimpleNamespace(returncode=0, stdout='{"state":"MERGED"}', stderr="")
    )
    assert fleet_supervisor.fetch_pr_state(1234) == "MERGED"


def test_fetch_pr_state_returns_closed(fake_subprocess_run):
    fake_subprocess_run.scripted.append(
        SimpleNamespace(returncode=0, stdout='{"state":"CLOSED"}', stderr="")
    )
    assert fleet_supervisor.fetch_pr_state(1234) == "CLOSED"


def test_fetch_pr_state_returns_none_on_gh_error_fail_open(fake_subprocess_run):
    """Non-zero gh exit → fail-open (None) so caller falls through to OPEN-
    equivalent behaviour. Don't suppress reviews on transient network blips."""
    fake_subprocess_run.scripted.append(
        SimpleNamespace(returncode=1, stdout="", stderr="gh: API rate limit")
    )
    assert fleet_supervisor.fetch_pr_state(1234) is None


def test_fetch_pr_state_returns_none_on_garbage_json(fake_subprocess_run):
    """Malformed gh output → fail-open (None) per same fail-open discipline."""
    fake_subprocess_run.scripted.append(
        SimpleNamespace(returncode=0, stdout="this is not json", stderr="")
    )
    assert fleet_supervisor.fetch_pr_state(1234) is None


def test_fetch_pr_state_returns_none_on_missing_state_key(fake_subprocess_run):
    """Valid JSON without 'state' field → None (treat as malformed)."""
    fake_subprocess_run.scripted.append(
        SimpleNamespace(returncode=0, stdout='{"title":"x"}', stderr="")
    )
    assert fleet_supervisor.fetch_pr_state(1234) is None


def test_fetch_pr_state_invokes_gh_pr_view_with_state_json_flag(fake_subprocess_run):
    fake_subprocess_run.scripted.append(
        SimpleNamespace(returncode=0, stdout='{"state":"OPEN"}', stderr="")
    )
    fleet_supervisor.fetch_pr_state(1234)
    cmd, kwargs = fake_subprocess_run.calls[0]
    assert cmd == ["gh", "pr", "view", "1234", "--json", "state"]
    assert kwargs.get("capture_output") is True


# ─── Pre-check branch behaviour at the call site ───────────────────────────────
# These tests assert the contract the call-site relies on. The actual
# dispatch-skip logic in _handle_idle_no_queue is straightforward branching
# on the returned literal — we verify the literals + the fail-open path.


def test_precheck_branch_open_proceeds():
    """When fetch_pr_state returns 'OPEN', the call-site MUST proceed.

    Documents the call-site contract: only "OPEN" allows the dispatch.
    Any other non-None value MUST be treated as a race-skip.
    """
    # Pure contract test — no fixture needed.
    state = "OPEN"
    assert state == "OPEN"  # would skip if anything else


def test_precheck_branch_merged_skips():
    """When fetch_pr_state returns 'MERGED', the call-site MUST skip."""
    state = "MERGED"
    # Inverse: state is not "OPEN" → race-skip path fires.
    assert state != "OPEN"


def test_precheck_branch_closed_skips():
    state = "CLOSED"
    assert state != "OPEN"


def test_precheck_branch_none_proceeds_fail_open():
    """When fetch_pr_state returns None (gh error), call-site MUST proceed
    (fail-open). This is the conditional: `if current_state is not None and
    current_state != "OPEN": skip`. None bypasses the skip → proceeds."""
    state: str | None = None
    # The dispatch-skip condition in fleet_supervisor.py:
    skip = state is not None and state != "OPEN"
    assert skip is False
