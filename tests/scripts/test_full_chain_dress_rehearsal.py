"""Tests for scripts/cutover/full_chain_dress_rehearsal.py (Agency_OS-jb4e).

The harness drives the live loop only with --live + a reachable consumer
(gated on f5yt); these tests cover the PURE gate logic — real-KEI selection,
the memory-gap computation, and the §5 success evaluation (pass + every fail
reason) — which is verifiable now, without the live loop. Plus the skip-guard.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "cutover" / "full_chain_dress_rehearsal.py"


def _load():
    spec = importlib.util.spec_from_file_location("_dress_rehearsal", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass annotation resolution can find the module.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


m = _load()


def _hop(name, *, fired=True, bypass=False, cit="C-1", score=0.8):
    return m.HopTrace(
        hop=name,
        agent=name,
        fired=fired,
        bypass_rerank=bypass,
        top_citation_id=cit,
        top_score=score,
    )


def _useful_run(kei="Agency_OS-real", active=True, hops=m.HOP_AGENTS_DEFAULT):
    return m.RunResult(
        kei=kei,
        recall_active=active,
        hop_traces=tuple(_hop(h) for h in hops),
        pr_number=42,
        pr_merged=True,
        ci_passed=True,
        governance={
            "callsign_tagged": True,
            "concur_count": 2,
            "no_linear_write": True,
            "claim_observed": True,
        },
        worker_retries=0,
    )


def _cold_run(kei="Agency_OS-real", hops=m.HOP_AGENTS_DEFAULT):
    # recall off → hops fire but bypass / surface nothing useful
    return m.RunResult(
        kei=kei,
        recall_active=False,
        hop_traces=tuple(_hop(h, bypass=True, cit=None, score=0.0) for h in hops),
        pr_number=43,
        pr_merged=True,
        ci_passed=True,
        governance={
            "callsign_tagged": True,
            "concur_count": 2,
            "no_linear_write": True,
            "claim_observed": True,
        },
        worker_retries=1,
    )


# ─── §2 real-KEI selection ────────────────────────────────────────────────────


def test_is_synthetic_flags_test_fixtures():
    assert m.is_synthetic("KEI-TEST", "smoke") is True
    assert m.is_synthetic("Agency_OS-test001", "bd claim smoke test") is True
    assert (
        m.is_synthetic("Agency_OS-jb4e", "full chain dress-rehearsal test") is True
    )  # the harness's own KEI


def test_is_synthetic_passes_real_kei():
    assert m.is_synthetic("Agency_OS-abcd", "Add recency decay to retrieval scores") is False


def test_select_real_kei_skips_synthetic_returns_first_real():
    cands = [
        {"id": "KEI-TEST", "title": "smoke"},
        {"id": "Agency_OS-test001", "title": "bd claim smoke test"},
        {"id": "Agency_OS-9xyz", "title": "Wire FlashRank sidecar timeout"},
        {"id": "Agency_OS-zzzz", "title": "another real one"},
    ]
    assert m.select_real_kei(cands)["id"] == "Agency_OS-9xyz"


def test_select_real_kei_none_when_all_synthetic():
    assert m.select_real_kei([{"id": "KEI-TEST", "title": "smoke"}]) is None


def test_real_test_writing_kei_is_not_synthetic():
    # bare "test" in a title must NOT flag a real KEI as synthetic (Elliot fix)
    assert m.is_synthetic("Agency_OS-w1re", "Add unit tests for the reranker client") is False


# ─── §2 first-run low-stakes selection (Elliot 2026-05-29) ────────────────────


def test_is_low_stakes_by_title_and_priority():
    assert m.is_low_stakes("Agency_OS-a", "Fix typo in README") is True
    assert m.is_low_stakes("Agency_OS-b", "docs: clarify cutover plan") is True
    assert m.is_low_stakes("Agency_OS-c", "Rewrite billing engine", "P1") is False
    assert m.is_low_stakes("Agency_OS-d", "Refactor dispatcher", "P4") is True  # low priority


def test_select_gate_kei_prefers_low_stakes_real():
    cands = [
        {"id": "KEI-TEST", "title": "smoke"},  # synthetic
        {
            "id": "Agency_OS-hi",
            "title": "Rewrite the scoring engine",
            "priority": "P1",
        },  # real, high-stakes
        {
            "id": "Agency_OS-lo",
            "title": "docs: fix typo in ARCHITECTURE",
            "priority": "P3",
        },  # real, low-stakes
    ]
    assert m.select_gate_kei(cands)["id"] == "Agency_OS-lo"


def test_select_gate_kei_falls_back_to_rehearsal_when_no_low_stakes_real():
    # real KEIs exist but all high-stakes → fall back to synthetic rehearsal (never auto-merge high-stakes)
    cands = [{"id": "Agency_OS-hi", "title": "Rewrite the scoring engine", "priority": "P1"}]
    out = m.select_gate_kei(cands)
    assert out["id"] == "rehearsal-1" and out.get("synthetic_fallback") is True


def test_select_gate_kei_falls_back_when_all_synthetic():
    out = m.select_gate_kei([{"id": "KEI-TEST", "title": "smoke"}])
    assert out["id"] == "rehearsal-1" and out.get("synthetic_fallback") is True


# ─── §3/§5-S5 memory gap ──────────────────────────────────────────────────────


def test_memory_gap_active_outtraces_cold():
    gap = m.memory_gap(_useful_run(), _cold_run())
    assert gap["active_strictly_outtraces_cold"] is True
    assert set(gap["active_only_hops"]) == set(m.HOP_AGENTS_DEFAULT)
    assert gap["retries_not_worse"] is True


def test_memory_gap_no_gap_when_equal():
    gap = m.memory_gap(_useful_run(), _useful_run(active=False))
    assert gap["active_strictly_outtraces_cold"] is False


# ─── §5 gate evaluation ───────────────────────────────────────────────────────


def test_gate_passes_when_all_criteria_met():
    out = m.evaluate_gate(_useful_run(), _cold_run())
    assert out.passed is True
    assert out.reasons == ()


def test_gate_fails_when_pr_not_merged():
    active = _useful_run()
    active = m.RunResult(**{**active.__dict__, "pr_merged": False})
    out = m.evaluate_gate(active, _cold_run())
    assert not out.passed and any("S1" in r for r in out.reasons)


def test_gate_fails_on_insufficient_concur():
    active = _useful_run()
    active = m.RunResult(
        **{**active.__dict__, "governance": {**active.governance, "concur_count": 1}}
    )
    out = m.evaluate_gate(active, _cold_run())
    assert not out.passed and any("S3" in r and "concur" in r for r in out.reasons)


def test_gate_fails_on_linear_write():
    active = _useful_run()
    active = m.RunResult(
        **{**active.__dict__, "governance": {**active.governance, "no_linear_write": False}}
    )
    out = m.evaluate_gate(active, _cold_run())
    assert not out.passed and any("Linear write" in r for r in out.reasons)


def test_gate_fails_on_missing_hop_trace():
    active = _useful_run(hops=("chat", "deliberator", "worker"))  # reviewer hop missing
    out = m.evaluate_gate(active, _cold_run())
    assert not out.passed and any("S4" in r and "reviewer" in r for r in out.reasons)


def test_gate_fails_when_no_memory_gap():
    out = m.evaluate_gate(_useful_run(), _useful_run(active=False))  # cold also useful → no gap
    assert not out.passed and any("S5" in r for r in out.reasons)


# ─── §7 seed (injection-safe) ─────────────────────────────────────────────────


def test_build_seed_sql_is_parameterised():
    sql = m.build_seed_sql()
    assert "VALUES (%s, %s, 'available')" in sql  # values bound, not interpolated
    assert "public.tasks" in sql and "id, title, status" in sql


# ─── recall-atom assert (THE memory assert) ───────────────────────────────────


def test_assert_recall_returned_atom_passes_on_useful_run():
    ok, n = m.assert_recall_returned_atom(_useful_run())
    assert ok is True and n == len(m.HOP_AGENTS_DEFAULT)


def test_assert_recall_returned_atom_fails_on_cold_run():
    ok, n = m.assert_recall_returned_atom(_cold_run())
    assert ok is False and n == 0


def test_gate_fails_when_recall_returns_no_atom():
    # recall-active arm where every hop fired but bypassed / surfaced nothing
    barren = m.RunResult(
        kei="Agency_OS-real",
        recall_active=True,
        hop_traces=tuple(_hop(h, bypass=True, cit=None, score=0.0) for h in m.HOP_AGENTS_DEFAULT),
        pr_number=42,
        pr_merged=True,
        ci_passed=True,
        governance={
            "callsign_tagged": True,
            "concur_count": 2,
            "no_linear_write": True,
            "claim_observed": True,
        },
    )
    out = m.evaluate_gate(barren, _cold_run())
    assert not out.passed
    assert any("0 relevant atoms" in r for r in out.reasons)
    assert out.gap["recall_atoms_active"] == 0


# ─── §9 failure classification (spawn 400 etc.) ───────────────────────────────


def test_classify_spawn_failure_success_is_none():
    assert m.classify_spawn_failure(200) is None
    assert m.classify_spawn_failure(201) is None


def test_classify_spawn_failure_400_today_is_spawn_rejected():
    # TODAY's known failure: 400 = missing container image/name/port (Atlas fix pending)
    assert m.classify_spawn_failure(400, "missing image") == "spawn_rejected"
    assert m.classify_spawn_failure(503) == "spawn_rejected"
    assert "spawn_rejected" in m.FAILURE_MODES


# ─── skip-guard ───────────────────────────────────────────────────────────────


def test_main_skips_without_live_flag(capsys):
    rc = m.main([])
    assert rc == 0
    assert "SKIP (dress-rehearsal)" in capsys.readouterr().out
