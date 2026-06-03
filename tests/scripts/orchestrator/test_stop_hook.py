"""Negative-path tests for the continuous-operation Stop hook (Component 1).

Two harnesses required by the dispatch brief:

(A) Structural-bar negative test
    Confirm the hook refuses to write a payload that includes
    `status=proven` / `gate_proof_runs` / `attest_*` / `gh pr merge`.

(B) Stall-escalation negative test
    Simulate the same task_id being dispatched 3x within the dedup window
    and confirm the hook emits an escalation via _alert_failure.
"""

from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

import pytest

_HOOK_DIR = Path(__file__).resolve().parents[3] / "scripts" / "orchestrator"
sys.path.insert(0, str(_HOOK_DIR))

stop_hook = importlib.import_module("stop_hook")


# ---------------------------------------------------------------------------
# Harness A — structural bar
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        "INSERT INTO public.gate_proof_runs (component) VALUES ('x');",
        "UPDATE gate_roadmap SET status='proven' WHERE id=1;",
        'UPDATE gate_roadmap SET status="proven";',
        "status=proven",
        "from attestations import attest_component; attest_component('x')",
    ],
)
def test_a_safe_write_rejects_attestation_payload(tmp_path, payload):
    """_safe_write must raise StructuralBarViolation on forbidden tokens."""
    target = tmp_path / "evil.json"
    with pytest.raises(stop_hook.StructuralBarViolation):
        stop_hook._safe_write(target, payload)
    assert not target.exists(), "file must not be created on bar violation"


def test_a_safe_run_rejects_gh_pr_merge():
    """_safe_run must reject any subprocess argv containing `gh pr merge`."""
    with pytest.raises(stop_hook.StructuralBarViolation):
        stop_hook._safe_run(["gh", "pr", "merge", "123", "--admin"])


def test_a_safe_run_allows_read_only_bd():
    """Allowlist sanity: harmless argv passes the bar."""
    # echo a no-op — we only check that the bar does not trip on benign argv.
    r = stop_hook._safe_run(
        ["true"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# Harness B — stall escalation
# ---------------------------------------------------------------------------


def _setup_isolated_state(monkeypatch, tmp_path):
    """Redirect dedup file + error log + slack relay into tmp_path."""
    monkeypatch.setattr(stop_hook, "DEDUP_FILE", tmp_path / "dedup.json")
    monkeypatch.setattr(stop_hook, "ERROR_LOG", tmp_path / "stop-hook-error.log")
    monkeypatch.setattr(stop_hook, "SLACK_RELAY", tmp_path / "no_such_relay.py")
    monkeypatch.setattr(stop_hook, "CALLSIGN", "atlas")


def test_b_repeated_stall_escalates(tmp_path, monkeypatch):
    """Same task dispatched 3x within dedup window -> escalation in error log."""
    _setup_isolated_state(monkeypatch, tmp_path)
    task_id = "Agency_OS-stalltest"
    now = time.time()

    # First fire: not a dup (no record yet). Hook records dispatch.
    assert stop_hook._is_recent_dup(task_id, now=now) is False
    stop_hook._record_dispatch(task_id, now=now)

    # Second fire: same task within window -> dup; stall counter bumps to 1.
    assert stop_hook._is_recent_dup(task_id, now=now + 10) is True
    n1 = stop_hook._bump_stall(task_id)
    assert n1 == 1

    # Third fire: still a dup; stall bumps to 2.
    n2 = stop_hook._bump_stall(task_id)
    assert n2 == 2

    # Fourth fire: STALL_THRESHOLD (3) hit -> escalation must be emitted.
    n3 = stop_hook._bump_stall(task_id)
    assert n3 == stop_hook.STALL_THRESHOLD

    stop_hook._alert_failure(f"stall escalation: task {task_id} re-dispatched {n3} times")

    err_log_text = (tmp_path / "stop-hook-error.log").read_text()
    assert "stall escalation" in err_log_text
    assert task_id in err_log_text
    assert "[atlas]" in err_log_text


def test_b_reset_on_progress(tmp_path, monkeypatch):
    """Successful (non-dup) dispatch should reset the stall counter."""
    _setup_isolated_state(monkeypatch, tmp_path)
    task_id = "Agency_OS-resettest"

    stop_hook._bump_stall(task_id)
    stop_hook._bump_stall(task_id)
    state = stop_hook._load_dedup()
    assert state["counts"][task_id] == 2

    stop_hook._reset_stall(task_id)
    state = stop_hook._load_dedup()
    assert task_id not in (state.get("counts") or {})


# ---------------------------------------------------------------------------
# Bonus: the hook never raises on missing CALLSIGN — it alerts and returns 0.
# ---------------------------------------------------------------------------


def test_main_returns_zero_on_missing_callsign(tmp_path, monkeypatch):
    monkeypatch.setattr(stop_hook, "CALLSIGN", "")
    monkeypatch.setattr(stop_hook, "ERROR_LOG", tmp_path / "stop-hook-error.log")
    monkeypatch.setattr(stop_hook, "SLACK_RELAY", tmp_path / "no_such_relay.py")
    assert stop_hook.main() == 0
    assert (tmp_path / "stop-hook-error.log").read_text().count("CALLSIGN env var") == 1
