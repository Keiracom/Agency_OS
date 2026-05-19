"""tests for scripts/drift_audit_bd_state.py — KEI Agency_OS-z27a."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "drift_audit_bd_state.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("drift_audit_bd_state", SCRIPT_PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules["drift_audit_bd_state"] = m
    spec.loader.exec_module(m)
    return m


# extract_kei_ids ────────────────────────────────────────────────────────────


def test_extract_kei_ids_finds_single(mod) -> None:
    assert mod.extract_kei_ids("fix(kei94): keepalive") == {"KEI-94"}


def test_extract_kei_ids_finds_multiple(mod) -> None:
    text = "KEI-209/210/211/212 G4 — but also mentions KEI-117 for context"
    # Slash-separated IDs only the first matches \bKEI-\d+\b cleanly; later refs
    # still picked up via their own KEI- prefix
    assert "KEI-209" in mod.extract_kei_ids(text)
    assert "KEI-117" in mod.extract_kei_ids(text)


def test_extract_kei_ids_case_insensitive(mod) -> None:
    assert mod.extract_kei_ids("kei-123 lowercase") == {"KEI-123"}


def test_extract_kei_ids_no_match(mod) -> None:
    assert mod.extract_kei_ids("no identifiers here") == set()
    assert mod.extract_kei_ids("") == set()


def test_extract_kei_ids_handles_none_safely(mod) -> None:
    assert mod.extract_kei_ids(None) == set()


# audit() — happy path ─────────────────────────────────────────────────────


def test_audit_finds_drift_for_matching_pr_title(mod) -> None:
    in_progress = [
        {
            "id": "Agency_OS-tjgihu",
            "title": "KEI-94 — agent_keepalive.sh",
            "external_ref": "https://linear.app/keiracom/issue/KEI-223",
        }
    ]
    pr_match = [
        {
            "number": 1033,
            "title": "[ORION] fix(kei94): agent_keepalive.sh — in-pane respawn loop",
            "mergedAt": "2026-05-18T12:01:53Z",
        }
    ]
    # external_ref takes precedence — KEI-223 — but PR matches the title
    # heuristic via KEI-94. Confirm precedence by mapping pr_fn on KEI-223:
    findings = mod.audit(
        list_fn=lambda: in_progress,
        pr_fn=lambda kei: pr_match if kei == "KEI-223" else [],
    )
    assert len(findings) == 0  # PR title says kei94, not kei223 — guard against false positive

    # Now drop external_ref so title becomes primary
    in_progress[0].pop("external_ref")
    findings = mod.audit(
        list_fn=lambda: in_progress,
        pr_fn=lambda kei: pr_match if kei == "KEI-94" else [],
    )
    assert len(findings) == 1
    assert findings[0]["bd_id"] == "Agency_OS-tjgihu"
    assert findings[0]["kei_id"] == "KEI-94"
    assert findings[0]["pr_number"] == 1033


def test_audit_ignores_description_cross_references(mod) -> None:
    """Regression: an issue mentioning KEI-X in its description is NOT
    drifted just because some PR delivered KEI-X. Cross-references in
    description are not identity. Confirmed against live data showing
    Agency_OS-yvlr51 (CONCUR gate routing) was incorrectly flagged against
    PRs for KEI-22/38/45/63 mentioned only in its description."""
    in_progress = [
        {
            "id": "Agency_OS-yvlr51",
            "title": "KEI — CONCUR gate routing (no leading numeric ID)",
            "description": "see also KEI-22 KEI-38 KEI-45 KEI-63 for context",
        }
    ]
    findings = mod.audit(
        list_fn=lambda: in_progress,
        pr_fn=lambda kei: [{"number": 9999, "title": f"fix({kei.lower()})", "mergedAt": "x"}],
    )
    assert findings == []


def test_primary_kei_id_prefers_external_ref(mod) -> None:
    issue = {
        "title": "KEI-94 something",
        "external_ref": "https://linear.app/keiracom/issue/KEI-223",
    }
    assert mod.primary_kei_id(issue) == "KEI-223"


def test_primary_kei_id_falls_back_to_title(mod) -> None:
    issue = {"title": "KEI-94 something", "external_ref": ""}
    assert mod.primary_kei_id(issue) == "KEI-94"


def test_primary_kei_id_returns_none_when_no_id(mod) -> None:
    issue = {"title": "no identifiers", "external_ref": ""}
    assert mod.primary_kei_id(issue) is None


# pr_delivers_kei — strict conventional-commit match ─────────────────────


def test_pr_delivers_kei_accepts_conventional_commit_form(mod) -> None:
    assert mod.pr_delivers_kei("[ORION] fix(kei94): keepalive", "KEI-94")
    assert mod.pr_delivers_kei("[ATLAS] feat(kei20): alert routing", "KEI-20")
    assert mod.pr_delivers_kei("[MAX] feat(kei20-followup): tweak", "KEI-20")
    assert mod.pr_delivers_kei("[ORION] fix(kei221a): rename flag", "KEI-221a")


def test_pr_delivers_kei_rejects_cross_reference_only(mod) -> None:
    """Regression: a PR title mentioning KEI-X in prose (not as the commit
    scope) is not delivering it. Anchored against live false positives:
    - PR #920 'feat(kei92): agent self-claim loop — Linear KEI-92 / KEI-130
      idle-loop fix' must NOT match KEI-130 (it delivers KEI-92).
    - PR #782 'feat(orchestrator): KEI-17 schedule update' must NOT match
      KEI-17 (no conventional-commit scope on this PR; orchestrator scope)."""
    assert not mod.pr_delivers_kei(
        "[MAX] feat(kei92): agent self-claim loop — Linear KEI-92 / KEI-130 idle-loop fix",
        "KEI-130",
    )
    assert not mod.pr_delivers_kei(
        "[AIDEN] feat(orchestrator): KEI-17 schedule update — peak 07-24 AEST",
        "KEI-17",
    )


def test_pr_delivers_kei_prefix_bleed_guarded(mod) -> None:
    """KEI-22 must NOT match a PR for kei221a (prefix bleed)."""
    assert not mod.pr_delivers_kei("[ORION] fix(kei221a): canonicalise", "KEI-22")
    assert not mod.pr_delivers_kei("[ORION] fix(kei2): X", "KEI-22")


def test_pr_delivers_kei_handles_dash_form(mod) -> None:
    """Some PRs use KEI-94 form inside scope (rare but possible)."""
    assert mod.pr_delivers_kei("fix(KEI-94): thing", "KEI-94")


def test_audit_excludes_pr_whose_title_does_not_contain_kei_id(mod) -> None:
    """Belt-and-suspenders: gh search may return tangential matches; the
    `kei_id in pr title` re-check excludes them."""
    in_progress = [{"id": "Agency_OS-aaa", "title": "KEI-99 work"}]
    unrelated_pr = [{"number": 100, "title": "unrelated fix", "mergedAt": "2026-05-18T00:00:00Z"}]
    findings = mod.audit(
        list_fn=lambda: in_progress,
        pr_fn=lambda kei: unrelated_pr,
    )
    assert findings == []


def test_audit_returns_empty_when_no_in_progress(mod) -> None:
    findings = mod.audit(list_fn=lambda: [], pr_fn=lambda kei: [])
    assert findings == []


def test_audit_returns_empty_when_no_merged_pr(mod) -> None:
    in_progress = [{"id": "Agency_OS-bbb", "title": "KEI-77 work"}]
    findings = mod.audit(list_fn=lambda: in_progress, pr_fn=lambda kei: [])
    assert findings == []


def test_audit_handles_missing_title_field(mod) -> None:
    in_progress = [{"id": "Agency_OS-ccc"}]  # no title, no external_ref
    findings = mod.audit(list_fn=lambda: in_progress, pr_fn=lambda kei: [])
    assert findings == []


# format_plaintext / format_jsonl ───────────────────────────────────────────


def test_format_plaintext_zero(mod) -> None:
    out = mod.format_plaintext([])
    assert "0 drift candidates" in out
    assert "is clean" in out


def test_format_plaintext_includes_close_command(mod) -> None:
    findings = [
        {
            "bd_id": "Agency_OS-x",
            "bd_title": "thing",
            "kei_id": "KEI-1",
            "pr_number": 42,
            "pr_title": "PR",
            "merged_at": "2026-05-19T00:00:00Z",
        }
    ]
    out = mod.format_plaintext(findings)
    assert "bd-original close Agency_OS-x" in out
    assert "PR #42 merged" in out
    assert "z27a" in out  # references the parent audit KEI


def test_format_jsonl(mod) -> None:
    findings = [{"bd_id": "A", "kei_id": "KEI-1"}]
    out = mod.format_jsonl(findings)
    assert json.loads(out.strip()) == {"bd_id": "A", "kei_id": "KEI-1"}


# main() integration ────────────────────────────────────────────────────────


def test_main_returns_zero_on_clean_state(mod, monkeypatch, capsys) -> None:
    monkeypatch.setattr(mod, "_require_clis", lambda: None)
    monkeypatch.setattr(mod, "audit", lambda: [])
    rc = mod.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "0 drift candidates" in out


def test_main_returns_zero_and_emits_jsonl_when_flagged(mod, monkeypatch, capsys) -> None:
    monkeypatch.setattr(mod, "_require_clis", lambda: None)
    monkeypatch.setattr(
        mod,
        "audit",
        lambda: [{"bd_id": "A", "kei_id": "KEI-1"}],
    )
    rc = mod.main(["--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert json.loads(out.strip()) == {"bd_id": "A", "kei_id": "KEI-1"}


def test_main_exits_2_when_cli_missing(mod, monkeypatch) -> None:
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit) as excinfo:
        mod.main([])
    assert excinfo.value.code == 2


# subprocess-level ─────────────────────────────────────────────────────────


def test_list_in_progress_parses_subprocess_stdout(mod) -> None:
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(stdout='[{"id":"X","title":"t"}]')

    result = mod.list_in_progress(runner=fake_run)
    assert result == [{"id": "X", "title": "t"}]
    assert "in_progress" in captured["cmd"][2]


def test_fetch_merged_prs_parses_subprocess_stdout(mod) -> None:
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(stdout='[{"number":1,"title":"x","mergedAt":"z"}]')

    result = mod.fetch_merged_prs("KEI-1", runner=fake_run)
    assert result[0]["number"] == 1
    assert "KEI-1" in " ".join(captured["cmd"])
    assert "merged" in captured["cmd"]
