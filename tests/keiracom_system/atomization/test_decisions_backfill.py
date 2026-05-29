"""Tests for the one-time decisions → Hindsight backfill orchestrator."""

from __future__ import annotations

import json

from src.keiracom_system.atomization.decision_sources import DecisionSource
from src.keiracom_system.atomization.decisions_backfill import (
    DecisionsBackfill,
    atom_to_hindsight_item,
    sample_atom,
)


def _src(ref: str, kind: str) -> DecisionSource:
    return DecisionSource(source_ref=ref, source_kind=kind, source_text="ratified text")


class _Job:
    def __init__(self, atom_ids: list) -> None:
        self.atom_ids = atom_ids


class _Atomizer:
    """Returns one job per source, with N atom_ids drawn from a queue."""

    def __init__(self, atom_ids_per_source: list[list]) -> None:
        self._queue = list(atom_ids_per_source)
        self.calls: list[DecisionSource] = []

    def atomize(self, source: DecisionSource) -> _Job:
        self.calls.append(source)
        return _Job(self._queue.pop(0) if self._queue else [])


class _Store:
    def __init__(self, atoms_by_id: dict) -> None:
        self._atoms = atoms_by_id

    def get_atom(self, atom_id):
        return self._atoms.get(atom_id)


def _recorder():
    calls: list[tuple] = []

    def ingest(bank: str, items: list) -> None:
        calls.append((bank, items))

    return ingest, calls


# ---------- serializer (the format-match seam) ----------


def test_atom_to_hindsight_item_shape():
    atom = sample_atom()
    item = atom_to_hindsight_item(atom)
    assert item["content"] == atom.content
    assert "atom_v1" in item["tags"]
    assert "state:active" in item["tags"]
    assert "engineering" in item["tags"] and "security" in item["tags"]
    md = item["metadata"]
    assert md["atom_id"] == str(atom.atom_id)
    assert md["source"] == "decisions_backfill"
    assert json.loads(md["trigger_condition"])["kind"] == "context_predicate"
    assert json.loads(md["provenance"])["confidence"] == 0.95


# ---------- dry-run (no LLM, no Hindsight) ----------


def test_dry_run_counts_only_no_side_effects():
    sources = [_src("a", "governance_doc"), _src("b", "governance_doc"), _src("c", "manual")]
    ingest, calls = _recorder()
    atomizer = _Atomizer([])
    backfill = DecisionsBackfill(atomizer=atomizer, store=None, ingest_fn=ingest)
    result = backfill.run(sources, dry_run=True)
    assert result.dry_run is True
    assert result.sources_seen == 3
    assert result.by_source_kind == {"governance_doc": 2, "manual": 1}
    assert result.atoms_produced == 0
    assert result.atoms_ingested == 0
    assert atomizer.calls == []  # no LLM atomization in dry-run
    assert calls == []  # no Hindsight write


# ---------- execute (atomize + ingest) ----------


def test_execute_atomizes_and_ingests():
    a1, a2, a3 = sample_atom(), sample_atom(), sample_atom()
    sources = [_src("s1", "governance_doc"), _src("s2", "manual")]
    atomizer = _Atomizer([[a1.atom_id, a2.atom_id], [a3.atom_id]])
    store = _Store({a1.atom_id: a1, a2.atom_id: a2, a3.atom_id: a3})
    ingest, calls = _recorder()
    backfill = DecisionsBackfill(
        atomizer=atomizer, store=store, ingest_fn=ingest, bank="fleet_decisions"
    )
    result = backfill.run(sources, dry_run=False)
    assert result.atoms_produced == 3
    assert result.atoms_ingested == 3
    assert len(atomizer.calls) == 2
    # one ingest call per source that produced atoms
    assert len(calls) == 2
    assert calls[0][0] == "fleet_decisions"
    assert all(it["content"] == a1.content for it in calls[0][1])


def test_execute_skips_missing_atoms():
    a1 = sample_atom()
    sources = [_src("s1", "governance_doc")]
    atomizer = _Atomizer([[a1.atom_id, "missing-id"]])
    store = _Store({a1.atom_id: a1})  # 'missing-id' not present
    ingest, calls = _recorder()
    backfill = DecisionsBackfill(atomizer=atomizer, store=store, ingest_fn=ingest)
    result = backfill.run(sources, dry_run=False)
    assert result.atoms_produced == 1  # only the resolvable atom
    assert result.atoms_ingested == 1
    assert len(calls[0][1]) == 1
