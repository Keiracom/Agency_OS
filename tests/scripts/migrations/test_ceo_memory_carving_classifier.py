"""Tests for the ceo_memory carving classifier (Phase A5 piece 1a).

Locks the policy-vs-memory rule per Elliot dispatch 2026-05-26 Path (C):
- POLICY → stays in Supabase ceo_memory (don't backfill to Hindsight)
- MEMORY → tenant-specific (Dave) → backfill via DecisionWrapper

bd: Agency_OS-oq3c
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migrations"))

_mod = importlib.import_module("ceo_memory_carving_classifier")


def test_bare_key_classifies_as_memory():
    """Pre-ceo:-convention bare keys (e.g. 'architecture_version',
    'bu_redesign_mar25') are historical operational state about Dave's
    BDR product → tenant-specific memory."""
    assert _mod.classify_row("architecture_version") == _mod.MEMORY
    assert _mod.classify_row("bu_redesign_mar25") == _mod.MEMORY
    assert _mod.classify_row("campaign_model") == _mod.MEMORY


def test_meta_rule_keys_classify_as_policy():
    """boundary_matrix + memory_abstraction + comm_architecture + governance
    laws + rule:* are governance content that would read the same way for any
    tenant → POLICY → stays in Supabase."""
    assert _mod.classify_row("ceo:boundary_matrix_v1") == _mod.POLICY
    assert _mod.classify_row("ceo:memory_abstraction_layer_v1") == _mod.POLICY
    assert _mod.classify_row("ceo:comm_architecture") == _mod.POLICY
    assert _mod.classify_row("ceo:rule:subprocess_memory_cap") == _mod.POLICY
    assert _mod.classify_row("ceo:agency_os_keiracom_separation_v1") == _mod.POLICY
    assert _mod.classify_row("ceo:governance_freshness") == _mod.POLICY
    assert _mod.classify_row("ceo:cognee_retirement_posture_2026_05_26") == _mod.POLICY
    assert _mod.classify_row("ceo:cognee_retirement_execution_complete_2026_05_26") == _mod.POLICY


def test_dave_prefixed_keys_classify_as_memory():
    """ceo:dave_* are explicit Dave-tenant memory candidates."""
    assert _mod.classify_row("ceo:dave_plain_english_preference") == _mod.MEMORY
    assert _mod.classify_row("ceo:dave_decisions_2026_05_26") == _mod.MEMORY


def test_byok_keys_classify_as_memory():
    """ceo:byok_* are Dave's per-tenant API-key references."""
    assert _mod.classify_row("ceo:byok_apollo") == _mod.MEMORY


def test_directive_complete_keys_classify_as_memory():
    """ceo:directive_NNNNN_complete are historical decision markers about
    Dave's own directives → tenant memory."""
    assert _mod.classify_row("ceo:directive_10028_complete") == _mod.MEMORY
    assert _mod.classify_row("ceo:directive_10029_complete") == _mod.MEMORY


def test_session_end_keys_classify_as_memory():
    """ceo:session_end_* track Dave's own session activity."""
    assert _mod.classify_row("ceo:session_end_2026-05-25") == _mod.MEMORY


def test_unknown_ceo_prefixed_defaults_to_policy_conservative():
    """Conservative default: any unrecognised ceo:* key stays in Supabase
    (POLICY) until operator promotes it to MEMORY explicitly. Avoids
    over-backfilling and preserves the boundary-matrix-v1 guard intent."""
    assert _mod.classify_row("ceo:some_new_key") == _mod.POLICY


def test_classify_rows_annotates_each_row():
    rows = [
        {"key": "ceo:boundary_matrix_v1", "value": {"x": 1}},
        {"key": "ceo:dave_plain_english_preference", "value": "verbose"},
        {"key": "architecture_version", "value": "v7"},
    ]
    classified = _mod.classify_rows(rows)
    assert classified[0]["_carve"] == _mod.POLICY
    assert classified[1]["_carve"] == _mod.MEMORY
    assert classified[2]["_carve"] == _mod.MEMORY
    # Original fields preserved
    assert classified[0]["key"] == "ceo:boundary_matrix_v1"
    assert classified[1]["value"] == "verbose"


def test_report_counts_by_carve_with_samples():
    rows = [
        {"key": "ceo:boundary_matrix_v1", "_carve": _mod.POLICY},
        {"key": "ceo:memory_abstraction_layer_v1", "_carve": _mod.POLICY},
        {"key": "ceo:dave_x", "_carve": _mod.MEMORY},
        {"key": "ceo:dave_y", "_carve": _mod.MEMORY},
        {"key": "ceo:dave_z", "_carve": _mod.MEMORY},
    ]
    rep = _mod.report(rows, sample_size=2)
    assert rep["policy_count"] == 2
    assert rep["memory_count"] == 3
    assert rep["totals"] == {_mod.POLICY: 2, _mod.MEMORY: 3}
    assert len(rep["samples_by_carve"][_mod.POLICY]) == 2
    assert len(rep["samples_by_carve"][_mod.MEMORY]) == 2  # sample_size cap


def test_load_and_write_jsonl_roundtrip(tmp_path):
    rows = [
        {"key": "ceo:dave_x", "value": "v1"},
        {"key": "architecture_version", "value": "v7"},
    ]
    src = tmp_path / "in.jsonl"
    src.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    loaded = _mod.load_rows_from_jsonl(str(src))
    assert loaded == rows
    out = tmp_path / "sub" / "out.jsonl"
    classified = _mod.classify_rows(loaded)
    _mod.write_rows_to_jsonl(classified, str(out))
    re_loaded = _mod.load_rows_from_jsonl(str(out))
    assert all("_carve" in r for r in re_loaded)
    assert re_loaded[0]["_carve"] == _mod.MEMORY  # ceo:dave_x
    assert re_loaded[1]["_carve"] == _mod.MEMORY  # bare key


def test_main_end_to_end_with_export(tmp_path, capsys):
    src = tmp_path / "rows.jsonl"
    rows = [
        {"key": "ceo:boundary_matrix_v1", "value": {}},
        {"key": "ceo:dave_decisions_2026_05_26", "value": {}},
        {"key": "campaign_model", "value": "x"},
    ]
    src.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    out = tmp_path / "classifications.jsonl"
    rc = _mod.main(["--input", str(src), "--export-classifications", str(out)])
    assert rc == 0
    captured = capsys.readouterr().out
    rep = json.loads(captured)
    assert rep["totals"] == {_mod.POLICY: 1, _mod.MEMORY: 2}
    classified = _mod.load_rows_from_jsonl(str(out))
    assert len(classified) == 3
    assert {r["key"]: r["_carve"] for r in classified} == {
        "ceo:boundary_matrix_v1": _mod.POLICY,
        "ceo:dave_decisions_2026_05_26": _mod.MEMORY,
        "campaign_model": _mod.MEMORY,
    }
