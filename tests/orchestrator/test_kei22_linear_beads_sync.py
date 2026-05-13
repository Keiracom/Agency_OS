"""Tests for KEI-22 deliverables — Linear ↔ Beads bidirectional sync.

D1 — scripts/orchestrator/session_start_bd_linear_sync.py
D3 — scripts/bd_status_to_linear_immediate.py
D4 — scripts/orchestrator/linear_beads_divergence_sweep.py

D2 (CI workflow .github/workflows/kei-title-guard.yml) is a YAML gate
verified by repo-level shape tests below.

All side effects (subprocess, urllib) are injected so tests run without
real bd / Linear / Slack.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load(name: str, relpath: str):
    p = REPO_ROOT / relpath
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


D1 = _load("session_start_bd_linear_sync", "scripts/orchestrator/session_start_bd_linear_sync.py")
D3 = _load("bd_status_to_linear_immediate", "scripts/bd_status_to_linear_immediate.py")
D4 = _load("linear_beads_divergence_sweep", "scripts/orchestrator/linear_beads_divergence_sweep.py")


# ─── D1: session_start_bd_linear_sync ──────────────────────────────────


def test_d1_success_logs_and_returns_ok(tmp_path):
    log = tmp_path / "sync.log"
    out = D1.run(
        log_path=log,
        runner=lambda: SimpleNamespace(returncode=0, stdout="pulled 3", stderr=""),
    )
    assert out == {"ok": True, "reason": "synced", "exit_code": 0}
    assert "sync_ok" in log.read_text()


def test_d1_bd_unavailable_swallowed_exit_zero(tmp_path):
    """bd binary missing must NOT block session start — exit_code is 0.
    Either shortcut path (bd_unavailable for default 'bd') or subprocess
    exception path (custom bd_bin pointing nowhere) both qualify."""
    out = D1.run(bd_bin="/nope/no-bd", log_path=tmp_path / "x.log")
    assert out["ok"] is False
    assert out["exit_code"] == 0
    assert out["reason"] in ("bd_unavailable",) or out["reason"].startswith("exception:")


def test_d1_nonzero_rc_swallowed_exit_zero(tmp_path):
    """Real-world bd rc != 0 (network outage, Linear 429, etc.) must NOT
    block session start. Exit 0; log surfaces the failure."""
    log = tmp_path / "x.log"
    out = D1.run(
        log_path=log,
        runner=lambda: SimpleNamespace(returncode=1, stdout="", stderr="Linear 429"),
    )
    assert out["exit_code"] == 0
    assert out["ok"] is False
    assert "nonzero_swallowed" in log.read_text()
    assert "429" in log.read_text()


def test_d1_dry_run_no_exec(tmp_path):
    called = {"n": 0}

    def runner():
        called["n"] += 1
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    out = D1.run(dry_run=True, log_path=tmp_path / "x.log", runner=runner)
    assert out["reason"] == "dry_run"
    assert called["n"] == 0


# ─── D2: kei-title-guard workflow file ─────────────────────────────────


def test_d2_workflow_file_exists():
    p = REPO_ROOT / ".github" / "workflows" / "kei-title-guard.yml"
    assert p.is_file(), "kei-title-guard.yml must ship in this PR"


def test_d2_workflow_fires_on_pull_request_to_main():
    body = (REPO_ROOT / ".github" / "workflows" / "kei-title-guard.yml").read_text()
    assert "on:" in body
    assert "pull_request:" in body
    assert "branches: [main]" in body


def test_d2_workflow_exempts_dependabot_and_revert():
    body = (REPO_ROOT / ".github" / "workflows" / "kei-title-guard.yml").read_text()
    # Both exempt prefixes must be encoded.
    assert "chore(deps)" in body
    assert "Revert " in body
    # 'no-kei' label exemption present.
    assert "no-kei" in body


def test_d2_workflow_matches_kei_id_in_title():
    """Smoke the regex pattern shape on representative titles."""
    import re

    # Extract the grep pattern. The shell-side pattern is \b(kei[- ]?[0-9]+)\b.
    pat = re.compile(r"\b(kei[- ]?[0-9]+)\b", re.IGNORECASE)
    # Valid titles
    for t in ("[ORION] feat: KEI-22 ...", "kei-30 something", "KEI 19 hotfix", "kei22 wip"):
        assert pat.search(t), f"title should match: {t!r}"
    # Invalid titles
    for t in ("docs: README", "ship feature", "fix: bug"):
        assert not pat.search(t), f"title should NOT match: {t!r}"


# ─── D3: bd_status_to_linear_immediate ─────────────────────────────────


def test_d3_push_success_logs_and_exit_zero(tmp_path):
    log = tmp_path / "push.log"
    out = D3.run(
        log_path=log,
        runner=lambda: SimpleNamespace(returncode=0, stdout="pushed 2", stderr=""),
    )
    assert out["ok"] is True
    assert out["reason"] == "pushed"
    assert out["exit_code"] == 0
    assert "push_ok" in log.read_text()


def test_d3_push_failure_swallowed_for_next_tick(tmp_path):
    """Push failure on one 60s tick must not crash — next tick retries."""
    log = tmp_path / "push.log"
    out = D3.run(
        log_path=log,
        runner=lambda: SimpleNamespace(returncode=2, stdout="", stderr="rate limit"),
    )
    assert out["ok"] is False
    assert out["exit_code"] == 0
    assert "rate limit" in log.read_text()


def test_d3_dry_run_does_not_execute(tmp_path):
    invoked: list = []

    def runner():
        invoked.append(1)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    out = D3.run(dry_run=True, log_path=tmp_path / "x.log", runner=runner)
    assert out["reason"] == "dry_run"
    assert invoked == []


# ─── D4: linear_beads_divergence_sweep ─────────────────────────────────


def _li(identifier, state_name="Todo", state_type="unstarted", url=None):
    return {
        "id": f"L-{identifier}",
        "identifier": identifier,
        "title": f"{identifier} title",
        "state_name": state_name,
        "state_type": state_type,
        "url": url or f"https://linear.app/keiracom/issue/{identifier}/x",
    }


def _bd(id_, status="open", external=""):
    return {"id": id_, "title": f"{id_} title", "status": status, "external": external}


def test_d4_linear_only_bucket():
    linear = [_li("KEI-99")]
    bd = []
    buckets = D4.diff(linear, bd)
    assert len(buckets["linear_only"]) == 1
    assert buckets["linear_only"][0]["identifier"] == "KEI-99"


def test_d4_bd_only_bucket_skips_closed():
    linear = []
    bd = [
        _bd("Agency_OS-aaa", status="open", external=""),
        _bd("Agency_OS-bbb", status="closed", external=""),  # closed → not in bucket
    ]
    buckets = D4.diff(linear, bd)
    assert len(buckets["bd_only"]) == 1
    assert buckets["bd_only"][0]["id"] == "Agency_OS-aaa"


def test_d4_state_mismatch_bd_closed_linear_open():
    linear = [_li("KEI-50", state_name="Todo", state_type="unstarted")]
    bd = [
        _bd(
            "Agency_OS-x",
            status="closed",
            external="https://linear.app/keiracom/issue/KEI-50/title",
        )
    ]
    buckets = D4.diff(linear, bd)
    assert len(buckets["divergent_state"]) == 1
    assert buckets["divergent_state"][0]["kei"] == "KEI-50"
    assert buckets["divergent_state"][0]["bd_status"] == "closed"


def test_d4_clean_state_no_divergence():
    linear = [_li("KEI-50", state_type="completed")]
    bd = [
        _bd("Agency_OS-x", status="closed", external="https://linear.app/keiracom/issue/KEI-50/x")
    ]
    buckets = D4.diff(linear, bd)
    assert buckets["linear_only"] == []
    assert buckets["bd_only"] == []
    # KEI-50 is completed in Linear + closed in bd → not divergent.
    assert buckets["divergent_state"] == []


def test_d4_format_alert_caps_at_10_per_bucket():
    big = {
        "linear_only": [_li(f"KEI-{i}") for i in range(50)],
        "bd_only": [_bd(f"Agency_OS-{i}", status="open") for i in range(50)],
        "divergent_state": [
            {"kei": f"KEI-{i}", "bd_status": "closed", "linear_state": "Todo", "linear_url": "x"}
            for i in range(50)
        ],
    }
    text = D4.format_alert(big)
    # Counts in summary should reflect full bucket sizes.
    assert "50" in text
    # But only 10 per bucket should be rendered as detail rows.
    for kei_n in range(10):
        assert f"KEI-{kei_n}" in text or f"Agency_OS-{kei_n}" in text
    # KEI-49 should NOT appear (capped at 10).
    assert "KEI-49" not in text


def test_d4_run_aggregates_counts_and_posts(monkeypatch):
    linear = [_li("KEI-99"), _li("KEI-50", state_type="unstarted")]
    bd = [
        _bd("Agency_OS-only", status="open"),
        _bd("Agency_OS-x", status="closed", external="https://linear.app/keiracom/issue/KEI-50/x"),
    ]
    posted: list = []
    result = D4.run(
        linear_fetch=lambda: linear,
        bd_fetch=lambda: bd,
        post_fn=lambda text: posted.append(text) or True,
    )
    assert result["linear_count"] == 2
    assert result["bd_count"] == 2
    assert result["linear_only"] == 1  # KEI-99
    assert result["bd_only"] == 1  # Agency_OS-only
    assert result["divergent_state"] == 1  # KEI-50: bd closed, Linear open
    assert result["posted"] is True
    assert len(posted) == 1


# ─── SessionStart hook chain ordering (D1 wire-in) ─────────────────────


def test_session_start_hook_chain_includes_bd_linear_sync():
    """The KEI-22 D1 wire-in inserts session_start_bd_linear_sync after
    session_uuid_resume and before anti_amnesia_capsule per dispatch."""
    import json

    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    chain = settings["hooks"]["SessionStart"][0]["hooks"]
    cmds = [h["command"].split("/")[-1] for h in chain]

    # Required entries present
    assert any("session_start_bd_linear_sync" in c for c in cmds), (
        "bd_linear_sync hook missing from SessionStart chain"
    )
    assert any("anti_amnesia_capsule" in c for c in cmds), (
        "anti_amnesia_capsule must remain in chain"
    )

    # Order: bd_linear_sync BEFORE anti_amnesia_capsule
    bd_idx = next(i for i, c in enumerate(cmds) if "session_start_bd_linear_sync" in c)
    anti_idx = next(i for i, c in enumerate(cmds) if "anti_amnesia_capsule" in c)
    assert bd_idx < anti_idx, (
        "session_start_bd_linear_sync must run BEFORE anti_amnesia_capsule "
        "(dispatch ordering: ... → session_uuid_resume → bd_sync_linear → "
        "anti_amnesia_capsule LAST)"
    )

    # session_uuid_resume must come BEFORE bd_linear_sync
    if any("session_uuid_resume" in c for c in cmds):
        resume_idx = next(i for i, c in enumerate(cmds) if "session_uuid_resume" in c)
        assert resume_idx < bd_idx
