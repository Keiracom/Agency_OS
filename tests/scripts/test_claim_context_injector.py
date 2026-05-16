"""Tests for KEI-51 claim_context_injector — bd claim preamble emission.

Covers: missing file (no preamble), no-match (no preamble), KEI exact match
ranks above tag-only match, token-cap drop-entirely semantics (KEI-55 — no
mid-sentence truncation), extra_sources extension hook (Weaviate retrieval
post-KEI-49 / PR #887), and deprecated-row exclusion (KEI-63).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ORCH = REPO_ROOT / "scripts" / "orchestrator"

# Make orchestrator/ importable so the injector's `from discovery_log import ...`
# resolves the same way as it does in production.
if str(ORCH) not in sys.path:
    sys.path.insert(0, str(ORCH))

_dl_spec = importlib.util.spec_from_file_location("discovery_log", ORCH / "discovery_log.py")
_dl = importlib.util.module_from_spec(_dl_spec)
sys.modules["discovery_log"] = _dl
_dl_spec.loader.exec_module(_dl)

_inj_spec = importlib.util.spec_from_file_location(
    "claim_context_injector", ORCH / "claim_context_injector.py"
)
_inj = importlib.util.module_from_spec(_inj_spec)
sys.modules["claim_context_injector"] = _inj
_inj_spec.loader.exec_module(_inj)

format_preamble = _inj.format_preamble
append_discovery = _dl.append_discovery


@pytest.fixture(autouse=True)
def _redirect_jsonl(tmp_path, monkeypatch):
    """Point every cached discovery_log module at a per-test tmp jsonl.

    sys.modules['discovery_log'] gets overwritten by test_discovery_log.py
    when full-suite tests interleave. cmd_claim's in-function importlib
    resolves `from discovery_log import ...` via sys.modules — so we need
    to patch every cached instance, not just our own `_dl`.
    """
    p = tmp_path / "discovery_log.jsonl"
    for name, mod in list(sys.modules.items()):
        if name == "discovery_log" or name.endswith(".discovery_log"):
            if hasattr(mod, "DEFAULT_DISCOVERY_LOG"):
                monkeypatch.setattr(mod, "DEFAULT_DISCOVERY_LOG", p, raising=False)
    monkeypatch.setattr(_dl, "DEFAULT_DISCOVERY_LOG", p)
    return p


def _seed(p, *rows):
    for r in rows:
        append_discovery(r, p)


def test_missing_file_returns_empty(_redirect_jsonl):
    assert format_preamble("KEI-51", tags=["python"]) == ""


def test_no_match_returns_empty(_redirect_jsonl):
    _seed(
        _redirect_jsonl,
        {"kei": "KEI-99", "tags": ["rust"], "finding": "x", "validation_tier": 1},
    )
    assert format_preamble("KEI-51", tags=["python"]) == ""


def test_exact_kei_match_renders_entry(_redirect_jsonl):
    _seed(
        _redirect_jsonl,
        {"kei": "KEI-51", "agent": "scout", "tags": ["python"],
         "finding": "F", "failed_path": "X", "verified_path": "Y", "validation_tier": 2},
    )
    out = format_preamble("KEI-51", tags=[])
    assert "KEI-51" in out and "scout" in out
    assert "F" in out and "X" in out and "Y" in out
    assert "context preamble" in out


def test_kei_match_outranks_tag_match(_redirect_jsonl):
    _seed(
        _redirect_jsonl,
        {"kei": "KEI-99", "agent": "max", "tags": ["python"],
         "finding": "tag-only", "validation_tier": 3},
        {"kei": "KEI-51", "agent": "scout", "tags": ["python"],
         "finding": "kei-exact", "validation_tier": 1},
    )
    out = format_preamble("KEI-51", tags=["python"])
    assert out.index("kei-exact") < out.index("tag-only")


def test_token_cap_drops_lower_priority_entirely(_redirect_jsonl):
    big_finding = "A" * 1600
    _seed(
        _redirect_jsonl,
        {"kei": "KEI-51", "agent": "scout", "tags": ["a"],
         "finding": big_finding, "failed_path": "f", "verified_path": "v",
         "validation_tier": 3},
        {"kei": "KEI-51", "agent": "max", "tags": ["a"],
         "finding": big_finding, "failed_path": "f", "verified_path": "v",
         "validation_tier": 1},
    )
    out = format_preamble("KEI-51", tags=[], max_tokens=500)
    assert "scout" in out
    assert "max" not in out
    assert (len(out) + 3) // 4 <= 500


def test_no_mid_sentence_truncation_marker(_redirect_jsonl):
    _seed(
        _redirect_jsonl,
        {"kei": "KEI-51", "agent": "scout",
         "finding": "F" * 10000, "validation_tier": 1},
    )
    out = format_preamble("KEI-51", tags=[], max_tokens=50)
    assert "..." not in out
    assert "truncated" not in out.lower()


def test_extra_sources_merged(_redirect_jsonl):
    _seed(_redirect_jsonl,
          {"kei": "KEI-51", "agent": "scout", "finding": "from-jsonl"})

    def weaviate_stub():
        return [{"kei": "KEI-51", "agent": "weaviate", "finding": "from-weaviate"}]

    out = format_preamble("KEI-51", tags=[], extra_sources=(weaviate_stub,))
    assert "from-jsonl" in out
    assert "from-weaviate" in out


def test_deprecated_rows_excluded(_redirect_jsonl):
    _seed(
        _redirect_jsonl,
        {"kei": "KEI-51", "agent": "scout", "finding": "live"},
        {"kei": "KEI-51", "agent": "scout", "finding": "stale",
         "deprecated": True, "deprecated_reason": "x", "deprecated_by": "y"},
    )
    out = format_preamble("KEI-51", tags=[])
    assert "live" in out
    assert "stale" not in out


# ─── KEI-51 ACCEPTANCE — cmd_claim ↔ injector end-to-end ────────────────────


@pytest.fixture(scope="module")
def tasks_cli_mod():
    """Load tasks_cli fresh — sibling tests cache their own copy with a
    different in-function importlib path for the injector, which then races
    with our test's pre-registered sys.modules entry. Force a clean load."""
    import importlib.util as _u
    for _stale in ("tasks_cli",):
        sys.modules.pop(_stale, None)
    spec = _u.spec_from_file_location("tasks_cli", REPO_ROOT / "scripts" / "tasks_cli.py")
    m = _u.module_from_spec(spec)
    sys.modules["tasks_cli"] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def patch_connect(tasks_cli_mod, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _db_mocks import make_patch_connect  # noqa: PLC0415
    return make_patch_connect(monkeypatch)


def test_cmd_claim_emits_preamble_before_success_line(
    tasks_cli_mod, patch_connect, capsys, monkeypatch, _redirect_jsonl
):
    """KEI-51 acceptance — bd claim writes preamble before 'claimed X' line."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _db_mocks import FakeCursor  # noqa: PLC0415

    _seed(
        _redirect_jsonl,
        {"kei": "KEI-51", "agent": "scout", "tags": ["python", "memory"],
         "finding": "preamble-row-1", "failed_path": "f1", "verified_path": "v1",
         "validation_tier": 2},
        {"kei": "KEI-51", "agent": "max", "tags": ["python"],
         "finding": "preamble-row-2", "failed_path": "f2", "verified_path": "v2",
         "validation_tier": 1},
        {"kei": "KEI-99", "agent": "atlas", "tags": ["rust"],
         "finding": "unrelated-row", "validation_tier": 1},
    )
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = FakeCursor(
        fetchone_row=("KEI-51", "claim ctx injection", 1, "active",
                      "scout", "url", ["python", "memory"]),
    )
    patch_connect(cur)
    rc = tasks_cli_mod.main(["claim", "--id", "KEI-51"])
    assert rc == 0
    out = capsys.readouterr().out
    # Preamble present
    assert "context preamble" in out
    assert "preamble-row-1" in out
    assert "preamble-row-2" in out
    # Unrelated row absent
    assert "unrelated-row" not in out
    # Success line present + AFTER preamble
    success = "claimed KEI-51 by scout"
    assert success in out
    assert out.index("preamble-row-1") < out.index(success)
    # Tags propagated into RETURNING — verifies wiring change held
    assert "RETURNING" in cur.last_sql
    assert " tags" in cur.last_sql or "tags\n" in cur.last_sql


def test_cmd_claim_json_path_skips_preamble(
    tasks_cli_mod, patch_connect, capsys, monkeypatch, _redirect_jsonl
):
    """--json output stays clean — no preamble noise — for machine consumers."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _db_mocks import FakeCursor  # noqa: PLC0415

    _seed(_redirect_jsonl,
          {"kei": "KEI-51", "agent": "scout", "finding": "should-not-appear"})
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = FakeCursor(
        fetchone_row=("KEI-51", "x", 1, "active", "scout", "url", ["a"]),
    )
    patch_connect(cur)
    rc = tasks_cli_mod.main(["claim", "--id", "KEI-51", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "context preamble" not in out
    assert "should-not-appear" not in out
    import json as _j
    data = _j.loads(out)
    assert data["id"] == "KEI-51"
    assert data["tags"] == ["a"]


def test_cmd_claim_preamble_missing_jsonl_is_non_fatal(
    tasks_cli_mod, patch_connect, capsys, monkeypatch, _redirect_jsonl
):
    """If discovery_log.jsonl missing, claim still succeeds (no preamble)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _db_mocks import FakeCursor  # noqa: PLC0415

    # _redirect_jsonl points at tmp_path/discovery_log.jsonl which does not exist
    assert not _redirect_jsonl.exists()
    monkeypatch.setenv("CALLSIGN", "scout")
    cur = FakeCursor(
        fetchone_row=("KEI-51", "x", 1, "active", "scout", "url", None),
    )
    patch_connect(cur)
    rc = tasks_cli_mod.main(["claim", "--id", "KEI-51"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "context preamble" not in out
    assert "claimed KEI-51 by scout" in out
