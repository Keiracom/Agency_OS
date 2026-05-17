"""Tests for scripts/orchestrator/self_assign_on_ready.py — KEI-21.

Pure-Python; no real `bd` invocation (ready_fn + claim_fn are injected).
Covers:
  - claim success on top-priority eligible issue
  - claim race lost on first → retry next, eventually succeed
  - claim race lost on all attempts → graceful no-op
  - no eligible work (empty bd ready)
  - equal-worker model: any agent may claim any KEI (assignee filter removed
    per Dave 2026-05-17 standing order — phase-lock + SKIP LOCKED governs)
  - priority ordering: P0 beats P1, P1 beats P2
  - dry-run prints the target without calling claim_fn
  - invalid callsign rejected
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "self_assign_on_ready.py"
_spec = importlib.util.spec_from_file_location("self_assign_on_ready", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["self_assign_on_ready"] = mod
_spec.loader.exec_module(mod)


def _item(
    id_: str,
    *,
    title: str = "test",
    priority: str = "P2",
    assignee: str = "",
    owner: str = "",
    created: str = "2026-05-12T10:00:00Z",
) -> dict:
    return {
        "id": id_,
        "title": title,
        "priority": priority,
        "assignee": assignee,
        "owner": owner,
        "created": created,
    }


# ─── 1. Claim success on top-priority eligible issue ────────────────────


def test_claim_success_on_top_priority_eligible(monkeypatch):
    items = [
        _item("Agency_OS-aaa", priority="P2"),
        _item("Agency_OS-bbb", priority="P0", title="urgent"),
        _item("Agency_OS-ccc", priority="P1"),
    ]
    claimed: list[str] = []

    def claim_fn(iid: str) -> bool:
        claimed.append(iid)
        return True

    result = mod.run(callsign="orion", ready_fn=lambda: items, claim_fn=claim_fn)
    assert result["claimed"] is True
    assert result["issue_id"] == "Agency_OS-bbb"
    assert result["priority"] == "P0"
    assert claimed == ["Agency_OS-bbb"]
    assert result["reason"] == "claimed"


# ─── 2. Race lost on first → retry next, eventually succeed ─────────────


def test_race_lost_first_then_succeed(monkeypatch):
    items = [
        _item("Agency_OS-aaa", priority="P0"),
        _item("Agency_OS-bbb", priority="P0"),
        _item("Agency_OS-ccc", priority="P1"),
    ]
    attempts: list[str] = []

    def claim_fn(iid: str) -> bool:
        attempts.append(iid)
        return iid == "Agency_OS-bbb"  # first one fails, second wins

    result = mod.run(callsign="orion", ready_fn=lambda: items, claim_fn=claim_fn)
    assert result["claimed"] is True
    assert result["issue_id"] == "Agency_OS-bbb"
    assert attempts == ["Agency_OS-aaa", "Agency_OS-bbb"]


# ─── 3. Race lost on ALL attempts → graceful no-op ──────────────────────


def test_race_lost_all_returns_graceful_noop():
    items = [
        _item("Agency_OS-aaa", priority="P0"),
        _item("Agency_OS-bbb", priority="P0"),
        _item("Agency_OS-ccc", priority="P1"),
    ]

    def claim_fn(iid: str) -> bool:
        return False

    result = mod.run(callsign="orion", ready_fn=lambda: items, claim_fn=claim_fn)
    assert result["claimed"] is False
    assert result["reason"] == "race_lost_all"
    assert result["attempted"] == ["Agency_OS-aaa", "Agency_OS-bbb", "Agency_OS-ccc"]


# ─── 4. Empty bd ready → no_eligible_work ───────────────────────────────


def test_no_eligible_work_when_bd_ready_empty():
    result = mod.run(callsign="orion", ready_fn=lambda: [], claim_fn=lambda _: True)
    assert result["claimed"] is False
    assert result["reason"] == "no_eligible_work"


# ─── 5. Equal-worker model: any agent claims any eligible KEI ────────────


def test_any_agent_can_claim_peer_assigned_work():
    """Equal-worker model (Dave 2026-05-17): assignee filter is gone.
    Any agent in bd ready output is claimable by any callsign.
    Phase-lock + SKIP LOCKED in bd governs collision, not the filter."""
    items = [
        _item("Agency_OS-peer", priority="P0", assignee="atlas"),
    ]
    claimed: list[str] = []

    def claim_fn(iid: str) -> bool:
        claimed.append(iid)
        return True

    result = mod.run(callsign="orion", ready_fn=lambda: items, claim_fn=claim_fn)
    assert result["claimed"] is True
    assert result["issue_id"] == "Agency_OS-peer"
    assert claimed == ["Agency_OS-peer"]


def test_claims_own_pre_assigned_work():
    items = [
        _item("Agency_OS-mine", priority="P0", assignee="orion"),
    ]
    result = mod.run(callsign="orion", ready_fn=lambda: items, claim_fn=lambda _: True)
    assert result["claimed"] is True
    assert result["issue_id"] == "Agency_OS-mine"


def test_claims_unassigned_work():
    items = [
        _item("Agency_OS-open", priority="P0", assignee="", owner=""),
    ]
    result = mod.run(callsign="orion", ready_fn=lambda: items, claim_fn=lambda _: True)
    assert result["claimed"] is True


# ─── 7. Priority ordering across letters + numbers ──────────────────────


def test_priority_orders_p0_first_then_p1_then_p2():
    items = [
        _item("Agency_OS-low", priority="P2"),
        _item("Agency_OS-mid", priority="P1"),
        _item("Agency_OS-hi", priority="P0"),
    ]
    sorted_ids = [i["id"] for i in sorted(items, key=mod._priority_key)]
    assert sorted_ids == ["Agency_OS-hi", "Agency_OS-mid", "Agency_OS-low"]


def test_priority_falls_back_to_created_at_when_priority_missing():
    items = [
        _item("Agency_OS-old", priority="", created="2026-05-10T00:00:00Z"),
        _item("Agency_OS-new", priority="", created="2026-05-12T00:00:00Z"),
    ]
    sorted_ids = [i["id"] for i in sorted(items, key=mod._priority_key)]
    assert sorted_ids == ["Agency_OS-old", "Agency_OS-new"]


# ─── 8. Dry-run prints target without calling claim_fn ──────────────────


def test_dry_run_does_not_invoke_claim_fn():
    items = [_item("Agency_OS-aaa", priority="P0", title="would claim")]
    calls: list[str] = []

    def claim_fn(iid: str) -> bool:
        calls.append(iid)
        return True

    result = mod.run(
        callsign="orion",
        ready_fn=lambda: items,
        claim_fn=claim_fn,
        dry_run=True,
    )
    assert result["claimed"] is False
    assert result["reason"] == "dry_run"
    assert result["issue_id"] == "Agency_OS-aaa"
    assert calls == [], "dry-run must not call claim_fn"


# ─── 9. Invalid callsign rejected ───────────────────────────────────────


def test_invalid_callsign_returns_invalid_reason():
    for bad in ("", "../etc", "123foo", "orion;ls", "or ion"):
        result = mod.run(callsign=bad, ready_fn=lambda: [], claim_fn=lambda _: True)
        assert result["claimed"] is False
        assert result["reason"] == "invalid_callsign", f"failed for {bad!r}"


# ─── 10. max_attempts caps retries ──────────────────────────────────────


def test_max_attempts_caps_retries():
    items = [_item(f"Agency_OS-{i:03d}", priority="P0") for i in range(10)]

    def claim_fn(iid: str) -> bool:
        return False

    result = mod.run(
        callsign="orion",
        ready_fn=lambda: items,
        claim_fn=claim_fn,
        max_attempts=2,
    )
    assert result["claimed"] is False
    assert result["reason"] == "race_lost_all"
    assert len(result["attempted"]) == 2  # capped at max_attempts


# ─── 11. CLI smoke: prints valid JSON + exits 0 on no-op ────────────────


def test_cli_main_prints_json_and_exits_zero(capsys, monkeypatch):
    """Main must always emit parseable JSON, even on no-op."""
    import json as _json

    monkeypatch.setattr(mod, "_bd_ready", lambda _bd: [])
    rc = mod.main(["--callsign", "orion"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = _json.loads(out)
    assert payload["callsign"] == "orion"
    assert payload["claimed"] is False
