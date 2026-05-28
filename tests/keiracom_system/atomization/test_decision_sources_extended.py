"""Full-coverage decision-source extension tests (e–i iterators + filters).

Covers the Dave-directive extension to decision_sources.py: the ceo: decision-
keyword iterator, completion:KEI-* / ceo:deliberation:* iterators, persona +
architecture-doc file iterators, the human-facing exclusion list, and the
is_atomisable_value content filter.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.keiracom_system.atomization import decision_sources as ds


class FakeDB:
    """Minimal _DBProtocol stub — answers LIKE queries from an in-memory store."""

    def __init__(self, store: dict[str, str]):
        self._store = store
        self._rows: list[tuple[str, str]] = []

    def execute(self, query: str, *params: object) -> None:
        like = str(params[0]) if params else (re.search(r"LIKE '([^']+)'", query) or [None, "%"])[1]
        rx = re.compile("^" + re.escape(like).replace("%", ".*") + "$")
        self._rows = [(k, self._store[k]) for k in sorted(self._store) if rx.match(k)]

    def fetchall(self) -> list[tuple[str, str]]:
        return self._rows


# ── is_atomisable_value ──────────────────────────────────────────────────


def test_is_atomisable_value_rejects_short_and_scalar_and_flags():
    assert ds.is_atomisable_value("a ratified three word") is True
    assert ds.is_atomisable_value("too short") is False  # 2 words
    assert ds.is_atomisable_value("true") is False
    assert ds.is_atomisable_value("42") is False
    assert ds.is_atomisable_value("  active  ") is False
    assert ds.is_atomisable_value(None) is False
    assert ds.is_atomisable_value('{"decision": "ratified the thing for good"}') is True
    assert ds.is_atomisable_value("false") is False  # bare bool token


def test_is_excluded_ceo_key():
    for bad in (
        "ceo:session_end_2026-05-28",
        "ceo:diag_run_5",
        "ceo:heartbeat_orion",
        "ceo:approval_flow",
        "ceo:save_point_3",
        "ceo:handoff_atlas",
        "ceo:directive_10028_status",
    ):
        assert ds._is_excluded_ceo_key(bad) is True, bad
    assert ds._is_excluded_ceo_key("ceo:memory_abstraction_layer_v1") is False


# ── ceo: decision-keyword iterator ───────────────────────────────────────


def test_iter_ceo_memory_decisions_filters_correctly():
    store = {
        "ceo:memory_abstraction_layer_v1": "Ratified MAL V1 with eleven agreed positions and gates.",
        "ceo:cutover_plan_v1": "Cutover plan ratified 2026-05-27 with phase steps enumerated.",
        "ceo:directive_10028_complete": "should be skipped — covered by directive iterator",
        "ceo:directive_10028_status": "active",  # excluded + short
        "ceo:heartbeat_orion": "this contains the memory keyword but is excluded by list",
        "ceo:random_counter": "5",  # no keyword + scalar
        "ceo:governance_note": "x",  # keyword but <3 words → filtered
    }
    out = list(ds.iter_ceo_memory_decisions(FakeDB(store)))
    refs = {s.source_ref for s in out}
    assert refs == {
        "ceo_memory:ceo:memory_abstraction_layer_v1",
        "ceo_memory:ceo:cutover_plan_v1",
    }
    assert all(s.source_kind == "governance_doc" for s in out)


def test_iter_ceo_memory_completions_and_deliberations():
    store = {
        "completion:KEI-101": "Completed the Valkey wiring with rationale and verification output.",
        "completion:KEI-bad": "x",  # short → filtered
        "ceo:deliberation:mal_v1": "Three deliberators concurred on the memory engine choice.",
        "ceo:other": "not a deliberation key",
    }
    comps = {s.source_ref for s in ds.iter_ceo_memory_completions(FakeDB(store))}
    delibs = {s.source_ref for s in ds.iter_ceo_memory_deliberations(FakeDB(store))}
    assert comps == {"ceo_memory:completion:KEI-101"}
    assert delibs == {"ceo_memory:ceo:deliberation:mal_v1"}


# ── file iterators ───────────────────────────────────────────────────────


def test_iter_persona_definitions(tmp_path: Path):
    pdir = tmp_path / "personas"
    pdir.mkdir()
    (pdir / "orion.md").write_text("Orion is the build clone with a defined role and scope.")
    (pdir / "empty.md").write_text("hi")  # <3 words → filtered
    out = list(ds.iter_persona_definitions(tmp_path))
    assert [s.source_ref for s in out] == ["personas/orion.md"]


def test_iter_architecture_docs_recurses(tmp_path: Path):
    adir = tmp_path / "docs" / "architecture"
    (adir / "sub").mkdir(parents=True)
    (adir / "top.md").write_text("Top-level architecture decision recorded for the fleet.")
    (adir / "sub" / "nested.md").write_text("Nested architecture decision also recorded here.")
    refs = {s.source_ref for s in ds.iter_architecture_docs(tmp_path)}
    assert refs == {"docs/architecture/top.md", "docs/architecture/sub/nested.md"}


def test_iter_persona_definitions_missing_dir_is_safe(tmp_path: Path):
    assert list(ds.iter_persona_definitions(tmp_path)) == []


# ── aggregator includes the new sources ──────────────────────────────────


def test_iter_all_includes_extension_sources(tmp_path: Path):
    (tmp_path / "personas").mkdir()
    (tmp_path / "personas" / "x.md").write_text("Persona x has a role definition worth atomising.")
    store = {"ceo:cutover_plan_v1": "Cutover plan ratified with enumerated phase steps here."}
    out = list(ds.iter_all_decision_sources(db=FakeDB(store), repo_root=tmp_path))
    refs = {s.source_ref for s in out}
    assert "ceo_memory:ceo:cutover_plan_v1" in refs
    assert "personas/x.md" in refs
