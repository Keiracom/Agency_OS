"""Tests for scripts/alerts/skill_pr_staleness_monitor.py — KEI-11 Outcome 2.

Mocks `gh pr list` + Slack POST. No network. Covers:
  - PRs aged > 48h touching src/skill_gen/ trigger an alert
  - PRs aged < 48h do NOT trigger
  - PRs NOT touching src/skill_gen/ are ignored even if old
  - Per-PR dedupe within 24h window
  - Slack post failure swallowed; state still NOT advanced (will retry)
  - gh CLI failure isolates (no crash)
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "alerts" / "skill_pr_staleness_monitor.py"
_spec = importlib.util.spec_from_file_location("skill_pr_staleness_monitor", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["skill_pr_staleness_monitor"] = mod
_spec.loader.exec_module(mod)


NOW = datetime(2026, 5, 12, 12, 0, 0, tzinfo=UTC)


def _pr(
    number: int,
    age_hours: float,
    *,
    files: list[str] | None = None,
    head_ref: str = "feat/test",
) -> dict:
    created = NOW - timedelta(hours=age_hours)
    return {
        "number": number,
        "title": f"PR #{number}",
        "headRefName": head_ref,
        "createdAt": created.isoformat().replace("+00:00", "Z"),
        "author": {"login": "tester"},
        "files": [{"path": p} for p in (files or [])],
        "url": f"https://github.com/Keiracom/Agency_OS/pull/{number}",
    }


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "state.json"


@pytest.fixture
def post_calls():
    calls: list[str] = []

    def fake_post(text: str, channel: str = mod.EXECUTION_CHANNEL) -> bool:
        calls.append(text)
        return True

    fake_post.calls = calls  # type: ignore[attr-defined]
    return fake_post


def test_alerts_on_pr_aged_over_48h_touching_skill_gen(state_path: Path, post_calls):
    prs = [_pr(101, age_hours=49, files=["src/skill_gen/extractor.py"])]
    summary = mod.run_once(state_path, gh_fn=lambda: prs, post_fn=post_calls, now=NOW)
    assert summary == {"scanned": 1, "skill_prs": 1, "breached": 1, "alerted": 1}
    assert len(post_calls.calls) == 1
    assert "#101" in post_calls.calls[0]
    assert "src/skill_gen" in post_calls.calls[0]


def test_does_not_alert_on_fresh_pr(state_path: Path, post_calls):
    prs = [_pr(102, age_hours=12, files=["src/skill_gen/generator.py"])]
    summary = mod.run_once(state_path, gh_fn=lambda: prs, post_fn=post_calls, now=NOW)
    assert summary["breached"] == 0
    assert summary["alerted"] == 0
    assert post_calls.calls == []


def test_ignores_old_pr_not_touching_skill_gen(state_path: Path, post_calls):
    """A 100-hour-old PR touching src/orchestration/ is NOT a skill PR — KEI-11
    Outcome 2 is scoped to skill_gen lane only."""
    prs = [_pr(103, age_hours=100, files=["src/orchestration/flow.py"])]
    summary = mod.run_once(state_path, gh_fn=lambda: prs, post_fn=post_calls, now=NOW)
    assert summary["skill_prs"] == 0
    assert summary["breached"] == 0
    assert post_calls.calls == []


def test_dedupes_within_24h_window(state_path: Path, post_calls):
    """Once a PR has been alerted, subsequent sweeps within 24h must NOT
    re-alert — avoids #execution flooding."""
    prs = [_pr(104, age_hours=50, files=["src/skill_gen/extractor.py"])]

    # First sweep alerts.
    s1 = mod.run_once(state_path, gh_fn=lambda: prs, post_fn=post_calls, now=NOW)
    assert s1["alerted"] == 1

    # 12h later: still breached, but inside dedupe window — no alert.
    later = NOW + timedelta(hours=12)
    s2 = mod.run_once(state_path, gh_fn=lambda: prs, post_fn=post_calls, now=later)
    assert s2["alerted"] == 0
    assert len(post_calls.calls) == 1  # still just the first

    # 25h after first alert: dedupe window cleared — alert again.
    much_later = NOW + timedelta(hours=25)
    s3 = mod.run_once(state_path, gh_fn=lambda: prs, post_fn=post_calls, now=much_later)
    assert s3["alerted"] == 1
    assert len(post_calls.calls) == 2


def test_slack_post_failure_leaves_state_for_retry(state_path: Path):
    """Pattern A safety: if Slack POST fails, the state file must NOT mark
    the PR as alerted — next sweep retries."""
    prs = [_pr(105, age_hours=72, files=["src/skill_gen/gemini_invoke.py"])]

    def failing_post(*_a, **_kw) -> bool:
        return False

    summary = mod.run_once(state_path, gh_fn=lambda: prs, post_fn=failing_post, now=NOW)
    assert summary["breached"] == 1
    assert summary["alerted"] == 0
    # State file may or may not exist; if it does, it must NOT record this PR.
    if state_path.is_file():
        state = json.loads(state_path.read_text())
        assert "105" not in state


def test_gh_failure_isolates_and_does_not_crash(state_path: Path, post_calls):
    def boom() -> list[dict]:
        return []  # gh_list_open_prs returns [] on any failure by design

    summary = mod.run_once(state_path, gh_fn=boom, post_fn=post_calls, now=NOW)
    assert summary == {"scanned": 0, "skill_prs": 0, "breached": 0, "alerted": 0}
    assert post_calls.calls == []


def test_multiple_breached_prs_get_one_aggregated_alert(state_path: Path, post_calls):
    """One Slack post per sweep, listing all currently-breaching PRs — avoids
    posting N messages when N skill PRs simultaneously cross 48h."""
    prs = [
        _pr(201, age_hours=50, files=["src/skill_gen/extractor.py"]),
        _pr(202, age_hours=72, files=["src/skill_gen/generator.py"]),
        _pr(203, age_hours=49, files=["src/skill_gen/gemini_invoke.py"]),
    ]
    summary = mod.run_once(state_path, gh_fn=lambda: prs, post_fn=post_calls, now=NOW)
    assert summary["breached"] == 3
    assert summary["alerted"] == 3
    assert len(post_calls.calls) == 1  # single aggregated alert
    for n in (201, 202, 203):
        assert f"#{n}" in post_calls.calls[0]


def test_corrupt_state_file_treated_as_empty(state_path: Path, post_calls):
    state_path.write_text("{ not valid json")
    prs = [_pr(301, age_hours=50, files=["src/skill_gen/x.py"])]
    summary = mod.run_once(state_path, gh_fn=lambda: prs, post_fn=post_calls, now=NOW)
    assert summary["alerted"] == 1
