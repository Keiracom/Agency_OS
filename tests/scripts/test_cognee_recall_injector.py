"""Tests for KEI-76 cognee_recall_injector — bd claim Cognee preamble emission.

Mirrors the test layout of test_claim_context_injector.py (KEI-51). Covers:
fail-open on import error, fail-open on search error, empty result, success
path with hits, token-cap drop semantics, and combined-cap interaction with
KEI-51's discovery_log injector under cmd_claim.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ORCH = REPO_ROOT / "scripts" / "orchestrator"
SCRIPTS = REPO_ROOT / "scripts"

# Make scripts/ + scripts/orchestrator/ importable.
for p in (SCRIPTS, ORCH):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

_spec = importlib.util.spec_from_file_location(
    "cognee_recall_injector", ORCH / "cognee_recall_injector.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["cognee_recall_injector"] = _mod
_spec.loader.exec_module(_mod)

format_preamble = _mod.format_preamble


# ─── unit ────────────────────────────────────────────────────────────────────


def test_empty_kei_returns_empty():
    assert format_preamble("", callsign="scout") == ""


def test_empty_callsign_returns_empty():
    assert format_preamble("KEI-76", callsign="") == ""


def test_zero_budget_returns_empty():
    assert format_preamble("KEI-76", callsign="scout", max_tokens=0) == ""


def test_enrich_dispatch_returns_unchanged_query_returns_empty(monkeypatch):
    """Cognee fail-open: enrich_dispatch returned original query (no context block)."""
    import cognee_recall as cr  # noqa: PLC0415

    monkeypatch.setattr(cr, "enrich_dispatch", lambda q, **kw: q)
    assert format_preamble("KEI-76", callsign="scout") == ""


def test_enrich_dispatch_raises_returns_empty(monkeypatch):
    """Fail-open contract: enrich_dispatch raises → empty preamble."""
    import cognee_recall as cr  # noqa: PLC0415

    def _raise(q, **kw):
        raise RuntimeError("cognee dead")

    monkeypatch.setattr(cr, "enrich_dispatch", _raise)
    assert format_preamble("KEI-76", callsign="scout") == ""


def test_success_path_returns_context_block(monkeypatch):
    """When enrich_dispatch returns a context-block-prefixed string, extract just the block."""
    import cognee_recall as cr  # noqa: PLC0415

    fake_block = (
        "## Cognee context (top semantic hits)\n"
        "1. KEI-76 design ratified 2026-05-16\n"
        "2. KEI-51 preamble pattern shipped PR #888"
    )
    monkeypatch.setattr(cr, "enrich_dispatch", lambda q, **kw: fake_block + "\n\n" + q)
    out = format_preamble("KEI-76", callsign="scout")
    assert out.startswith("## Cognee context")
    assert "KEI-76 design" in out
    assert "KEI-51 preamble" in out
    # Original query NOT included in the preamble (only the block)
    assert "Recent decisions" not in out


def test_token_cap_drops_entirely_when_block_too_big(monkeypatch):
    """KEI-55 semantics — block over cap is dropped entirely, no mid-truncate."""
    import cognee_recall as cr  # noqa: PLC0415

    big_block = "## Cognee context (top semantic hits)\n" + "X" * 5000
    monkeypatch.setattr(cr, "enrich_dispatch", lambda q, **kw: big_block + "\n\n" + q)
    out = format_preamble("KEI-76", callsign="scout", max_tokens=100)
    assert out == ""


def test_block_fits_under_remaining_budget(monkeypatch):
    """Small block under remaining budget renders verbatim."""
    import cognee_recall as cr  # noqa: PLC0415

    small_block = "## Cognee context (top semantic hits)\n1. short hit"
    monkeypatch.setattr(cr, "enrich_dispatch", lambda q, **kw: small_block + "\n\n" + q)
    out = format_preamble("KEI-76", callsign="scout", max_tokens=50)
    assert out == small_block


# ─── KEI-76 ACCEPTANCE — cmd_claim ↔ both injectors with combined cap ────────


@pytest.fixture(scope="module")
def tasks_cli_mod():
    """Fresh tasks_cli — sibling tests cache different importlib paths."""
    sys.modules.pop("tasks_cli", None)
    spec = importlib.util.spec_from_file_location("tasks_cli", SCRIPTS / "tasks_cli.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["tasks_cli"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def patch_connect(tasks_cli_mod, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _db_mocks import make_patch_connect  # noqa: PLC0415

    return make_patch_connect(monkeypatch)


def test_cmd_claim_emits_both_preambles_combined_cap(
    tasks_cli_mod, patch_connect, capsys, monkeypatch, tmp_path
):
    """Acceptance: cmd_claim emits discovery_log preamble + cognee preamble +
    success line in that order, with combined 500-token cap respected."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    # Seed discovery_log for KEI-51 injector
    import discovery_log as dl  # noqa: PLC0415
    from _db_mocks import FakeCursor  # noqa: PLC0415

    p = tmp_path / "discovery_log.jsonl"
    monkeypatch.setattr(dl, "DEFAULT_DISCOVERY_LOG", p)
    for name, mod in sys.modules.items():
        if name == "discovery_log" or name.endswith(".discovery_log"):
            if hasattr(mod, "DEFAULT_DISCOVERY_LOG"):
                monkeypatch.setattr(mod, "DEFAULT_DISCOVERY_LOG", p, raising=False)
    dl.append_discovery(
        {
            "kei": "KEI-76",
            "agent": "scout",
            "tags": ["cognee", "memory"],
            "finding": "discovery-hit-A",
            "failed_path": "f",
            "verified_path": "v",
            "validation_tier": 2,
        },
        p,
    )

    # Stub cognee_recall.enrich_dispatch
    import cognee_recall as cr  # noqa: PLC0415

    monkeypatch.setattr(
        cr,
        "enrich_dispatch",
        lambda q, **kw: "## Cognee context (top semantic hits)\n1. cognee-hit-B\n\n" + q,
    )

    monkeypatch.setenv("CALLSIGN", "scout")
    cur = FakeCursor(
        fetchone_row=("KEI-76", "cognee wiring", 1, "active", "scout", "url", ["cognee", "memory"]),
    )
    patch_connect(cur)
    rc = tasks_cli_mod.main(["claim", "--id", "KEI-76"])
    assert rc == 0
    out = capsys.readouterr().out

    # Both preambles present
    assert "discovery-hit-A" in out
    assert "cognee-hit-B" in out
    # Success line present
    success = "claimed KEI-76 by scout"
    assert success in out
    # Ordering: discovery first, then cognee, then success
    assert out.index("discovery-hit-A") < out.index("cognee-hit-B") < out.index(success)
    # Combined cap respected (rough 4-char heuristic)
    combined_preamble_len = out.index(success)
    assert (combined_preamble_len + 3) // 4 <= 500


def test_cmd_claim_json_path_emits_no_preambles(tasks_cli_mod, patch_connect, capsys, monkeypatch):
    """--json output stays clean — no preambles, only the JSON row."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cognee_recall as cr  # noqa: PLC0415
    from _db_mocks import FakeCursor  # noqa: PLC0415

    monkeypatch.setattr(
        cr,
        "enrich_dispatch",
        lambda q, **kw: "## Cognee context\n1. should-not-appear\n\n" + q,
    )

    monkeypatch.setenv("CALLSIGN", "scout")
    cur = FakeCursor(
        fetchone_row=("KEI-76", "x", 1, "active", "scout", "url", ["a"]),
    )
    patch_connect(cur)
    rc = tasks_cli_mod.main(["claim", "--id", "KEI-76", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Cognee context" not in out
    assert "should-not-appear" not in out


def test_cmd_claim_cognee_failure_does_not_block_success_line(
    tasks_cli_mod, patch_connect, capsys, monkeypatch
):
    """If Cognee recall raises, claim still succeeds with no Cognee preamble."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cognee_recall as cr  # noqa: PLC0415
    from _db_mocks import FakeCursor  # noqa: PLC0415

    def _raise(q, **kw):
        raise RuntimeError("cognee dead")

    monkeypatch.setattr(cr, "enrich_dispatch", _raise)

    monkeypatch.setenv("CALLSIGN", "scout")
    cur = FakeCursor(
        fetchone_row=("KEI-76", "x", 1, "active", "scout", "url", None),
    )
    patch_connect(cur)
    rc = tasks_cli_mod.main(["claim", "--id", "KEI-76"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Cognee context" not in out
    assert "claimed KEI-76 by scout" in out
