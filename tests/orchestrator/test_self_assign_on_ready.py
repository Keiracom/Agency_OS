"""Tests for scripts/orchestrator/self_assign_on_ready.py — KEI-21.

Pure-Python; no real `bd` invocation (ready_fn + claim_fn are injected).
Covers:
  - claim success on top-priority eligible issue
  - claim race lost on first → retry next, eventually succeed
  - claim race lost on all attempts → graceful no-op
  - no eligible work (empty bd ready)
  - eligibility filter: KEI-150 — any agent can claim any item (assignee
    filtering removed; phase-lock + SKIP LOCKED gate mechanically)
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


# ─── 5. KEI-150 — assignee filtering removed; any agent can claim any item ───


def test_claims_peer_assigned_work_kei150():
    """KEI-150 (Dave 2026-05-17) — assignee filtering removed. Phase-lock
    + SKIP LOCKED handle eligibility mechanically; an item assigned to
    atlas in Linear is still claimable by orion via the auto-claim loop.
    The prior 'never poach' rule blocked agents from picking up stale
    pre-assignments and was the #1 source of READY-loop idle time."""
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


# ─── 6. Eligibility filter: own-callsign assignee passes ────────────────


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


def test_priority_handles_int_priority_from_tasks_cli_json():
    """Regression: bd ready --json post-KEI-22 returns priority as int
    (1/2/3/4), not 'P\\d' string. _priority_key must not raise
    AttributeError ('int' object has no attribute 'upper') on the int shape.
    """
    items = [
        _item("Agency_OS-low", priority=3),
        _item("Agency_OS-mid", priority=2),
        _item("Agency_OS-hi", priority=0),
    ]
    sorted_ids = [i["id"] for i in sorted(items, key=mod._priority_key)]
    assert sorted_ids == ["Agency_OS-hi", "Agency_OS-mid", "Agency_OS-low"]


def test_priority_handles_mixed_int_and_str_priority():
    """Robustness: mixed feed (one int, one P-string) sorts without crash."""
    items = [
        _item("Agency_OS-int", priority=2),
        _item("Agency_OS-str", priority="P1"),
    ]
    sorted_ids = [i["id"] for i in sorted(items, key=mod._priority_key)]
    assert sorted_ids == ["Agency_OS-str", "Agency_OS-int"]


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


# ─── 12. y2al — skip dispatch + close when linked PR is already merged ──


def test_extract_pr_number_from_full_pr_url():
    item = {"external_ref": "https://github.com/Keiracom/Agency_OS/pull/1318"}
    assert mod._extract_pr_number(item) == 1318


def test_extract_pr_number_from_gh_shortform_in_title():
    item = {"title": "[NOVA] follow-up to gh-1199 race fix"}
    assert mod._extract_pr_number(item) == 1199


def test_extract_pr_number_none_for_linear_only_external_ref():
    item = {"external_ref": "https://linear.app/keiracom/issue/KEI-42"}
    assert mod._extract_pr_number(item) is None


def test_skip_closes_merged_pr_then_claims_next():
    """First candidate's PR is merged → close + skip; claim falls through to next."""
    items = [
        {
            "id": "Agency_OS-stale",
            "priority": "P0",
            "title": "stale work",
            "external_ref": "https://github.com/Keiracom/Agency_OS/pull/100",
        },
        {"id": "Agency_OS-fresh", "priority": "P1", "title": "live work"},
    ]
    closed: list[tuple] = []
    claimed: list[str] = []
    result = mod.run(
        callsign="nova",
        ready_fn=lambda: items,
        claim_fn=lambda iid: (claimed.append(iid) or True),
        pr_merged_fn=lambda pr_n: pr_n == 100,  # only #100 is merged
        close_fn=lambda iid, reason: (closed.append((iid, reason)) or True),
    )
    assert result["claimed"] is True
    assert result["issue_id"] == "Agency_OS-fresh"
    assert result["skipped_pr_merged"] == ["Agency_OS-stale"]
    assert claimed == ["Agency_OS-fresh"]
    assert closed[0][0] == "Agency_OS-stale"
    assert "PR #100" in closed[0][1] and "y2al" in closed[0][1]


def test_all_candidates_pr_merged_returns_all_pr_merged_no_claim():
    """Every candidate's PR is merged → all closed, no brief, reason=all_pr_merged."""
    items = [
        {
            "id": f"Agency_OS-{i}",
            "priority": "P1",
            "external_ref": f"https://github.com/Keiracom/Agency_OS/pull/{i + 10}",
        }
        for i in range(3)
    ]
    closed: list[str] = []
    claim_calls: list[str] = []
    result = mod.run(
        callsign="nova",
        ready_fn=lambda: items,
        claim_fn=lambda iid: (claim_calls.append(iid) or True),
        pr_merged_fn=lambda _pr: True,  # everything is merged
        close_fn=lambda iid, _r: (closed.append(iid) or True),
    )
    assert result["claimed"] is False
    assert result["reason"] == "all_pr_merged"
    assert result["attempted"] == []  # no claim attempts spent
    assert set(result["skipped_pr_merged"]) == {f"Agency_OS-{i}" for i in range(3)}
    assert claim_calls == []  # claim_fn never invoked
    assert len(closed) == 3


def test_merged_skips_do_not_consume_max_attempts_budget():
    """3 merged + 2 race-lost should still try the 2 non-merged within max_attempts=2."""
    items = [
        {
            "id": f"Agency_OS-merged-{i}",
            "priority": "P0",
            "created": f"2026-05-12T10:0{i}:00Z",
            "external_ref": f"https://github.com/Keiracom/Agency_OS/pull/{200 + i}",
        }
        for i in range(3)
    ] + [
        {
            "id": f"Agency_OS-race-{i}",
            "priority": "P0",
            "created": f"2026-05-12T10:1{i}:00Z",
        }
        for i in range(2)
    ]
    result = mod.run(
        callsign="nova",
        ready_fn=lambda: items,
        claim_fn=lambda _iid: False,  # always race-lost
        pr_merged_fn=lambda pr_n: 200 <= pr_n <= 202,
        close_fn=lambda _iid, _r: True,
        max_attempts=2,
    )
    assert result["claimed"] is False
    assert result["reason"] == "race_lost_all"
    assert len(result["skipped_pr_merged"]) == 3
    assert len(result["attempted"]) == 2  # both race candidates tried (budget honoured)


def test_pr_merged_fn_default_fail_closed_when_gh_missing(monkeypatch):
    """Default merged-check returns False on FileNotFoundError (gh absent) — fail-closed."""
    import subprocess as _sp

    def _boom(*_a, **_kw):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(_sp, "run", _boom)
    assert mod._gh_pr_merged_on_main(1234) is False  # fail-closed → keep dispatch open
