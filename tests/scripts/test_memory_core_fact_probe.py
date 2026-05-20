"""tests for scripts/orchestrator/memory_core_fact_probe.py — Agency_OS-zbvs.

Cognee recall mocked. Verifies:
  - check_facts flags a fact when a ground-truth keyword is absent from recall
  - check_facts passes a fact when every keyword is present (case-insensitive)
  - the 5 core facts are all covered
  - _emit_drift_alert is fail-open (no NATS binary required)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "memory_core_fact_probe.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("memory_core_fact_probe", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["memory_core_fact_probe"] = m
    spec.loader.exec_module(m)
    return m


def test_core_facts_cover_the_five_audit_areas(mod):
    labels = {str(f["label"]) for f in mod._CORE_FACTS}
    assert labels == {
        "model-routing",
        "enrichment-pipeline",
        "active-vendors",
        "active-channels",
        "fleet-structure",
    }


def test_check_facts_all_correct_no_drift(mod, monkeypatch):
    """Every fact's keywords present in recall → zero drift."""
    full = (
        "worker agents run on Claude Max OAuth; governance tiers on OpenAI / Gemini. "
        "The F2.2 enrichment pipeline has a 6-layer email waterfall. "
        "Active vendors: Salesforge, Unipile, ElevenAgents. "
        "Channels: Email, LinkedIn, Voice, SMS. "
        "Fleet: deliberators Elliot/Aiden/Max, workers Atlas/Orion/Scout/Nova."
    )
    monkeypatch.setattr(mod, "recall", lambda _q: full)
    assert mod.check_facts() == []


def test_check_facts_detects_missing_keyword(mod, monkeypatch):
    """A fact whose recall lacks a ground-truth keyword → flagged as drift."""
    # recall returns text missing 'Claude Max' (model-routing) and '6-layer'.
    stale = (
        "governance tiers run on OpenAI. The pipeline has a 4-layer email waterfall. "
        "Vendors: Salesforge, Unipile. Channels: Email, LinkedIn, Voice, SMS. "
        "Fleet: Elliot, Atlas, Orion."
    )
    monkeypatch.setattr(mod, "recall", lambda _q: stale)
    drifts = mod.check_facts()
    drifted = {str(d["label"]) for d in drifts}
    assert "model-routing" in drifted  # 'Claude Max' missing
    assert "enrichment-pipeline" in drifted  # '6-layer' / 'F2.2' missing
    assert "active-vendors" not in drifted  # Salesforge + Unipile present


def test_check_facts_keyword_match_is_case_insensitive(mod, monkeypatch):
    monkeypatch.setattr(
        mod,
        "recall",
        lambda _q: (
            "CLAUDE MAX oauth, openai, f2.2 6-LAYER, salesforge, unipile, "
            "email linkedin voice sms, elliot atlas orion"
        ),
    )
    assert mod.check_facts() == []


def test_recall_empty_on_import_failure_flags_all(mod, monkeypatch):
    """If Cognee is unreachable, recall returns '' → every fact drifts (fail-loud,
    not silently green)."""
    monkeypatch.setattr(mod, "recall", lambda _q: "")
    drifts = mod.check_facts()
    assert len(drifts) == len(mod._CORE_FACTS)


def test_emit_drift_alert_is_fail_open(mod, monkeypatch):
    """A missing NATS binary must not crash the probe."""
    monkeypatch.setattr(mod, "_NATS_BIN", "/nonexistent/nats")
    mod._emit_drift_alert([{"label": "model-routing", "missing": ["Claude Max"]}])  # no raise
