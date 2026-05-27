"""Decisions atomizer tests — Phase Alpha extension (Agency_OS-decisions-atomization)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from src.keiracom_system.atomization.atom_store import AtomStore
from src.keiracom_system.atomization.decision_sources import (
    DEFAULT_DECISIONS_BANK,
    DecisionSource,
    decision_composition_tags,
    iter_all_decision_sources,
    iter_consolidated_rules,
    iter_manual_section_13,
    iter_v2_inventory_ratified,
    parse_directive_json,
    serialize_decision_source,
)
from src.keiracom_system.atomization.decisions_atomizer import (
    DECISION_ATOMS_RESPONSE_SCHEMA,
    DecisionsAtomizer,
    DecisionsAtomizerError,
    atomize_decisions_run,
)
from src.keiracom_system.atomization.llm_client import LLMResponse
from src.keiracom_system.embeddings.tei_client import TEIClient, _HTTPResponse

# ────────────────────────────────────────────────────────────────────────────
# Source iterator coverage
# ────────────────────────────────────────────────────────────────────────────


def test_iter_consolidated_rules_yields_blocks(tmp_path: Path):
    rules = tmp_path / "rules.md"
    rules.write_text(
        "# Frontmatter — should be skipped\n\n"
        "## RULE 1 — restate\n"
        "Body of rule 1 line a.\nBody of rule 1 line b.\n\n"
        "## RULE 2 — coordinate\n"
        "Body of rule 2.\n",
        encoding="utf-8",
    )
    sources = list(iter_consolidated_rules(rules))
    assert len(sources) == 2
    assert sources[0].source_ref.endswith("#rule-1")
    assert "Body of rule 1 line a." in sources[0].source_text
    assert "Body of rule 1 line b." in sources[0].source_text
    assert sources[1].source_ref.endswith("#rule-2")
    assert "Body of rule 2." in sources[1].source_text


def test_iter_consolidated_rules_missing_file_returns_empty(tmp_path: Path):
    sources = list(iter_consolidated_rules(tmp_path / "does_not_exist.md"))
    assert sources == []


def test_iter_v2_inventory_ratified_picks_only_ratified_rows(tmp_path: Path):
    inventory = tmp_path / "inv.md"
    inventory.write_text(
        "| element_id | desc | status | source | install | phase |\n"
        "|---|---|---|---|---|---|\n"
        "| mem.engine | Hindsight | RATIFIED-CEO | x | none | V1 |\n"
        "| cost.cache_discipline | Cache | RATIFIED-DM | y | none | V1 |\n"
        "| mem.foo_loose | Loose item | LOOSE | z | install | V2 |\n"
        "| mem.gap | Gap item | GAP | w | install | V1 |\n",
        encoding="utf-8",
    )
    sources = list(iter_v2_inventory_ratified(inventory))
    # 2 RATIFIED rows picked; LOOSE + GAP skipped
    assert len(sources) == 2
    refs = [s.source_ref for s in sources]
    assert any("mem.engine" in r for r in refs)
    assert any("cost.cache_discipline" in r for r in refs)


def test_iter_manual_section_13_yields_directive_blocks(tmp_path: Path):
    manual = tmp_path / "manual.md"
    manual.write_text(
        "# Manual frontmatter\n\nSome prose before §13.\n\n"
        "## Section 13\n\n"
        "### Directive #10028 — KEI-CEO-BOUNDARY-MATRIX-V1\n"
        "Body of directive 10028.\n\n"
        "### Directive #10029 — UNIVERSAL ATOMIZATION\n"
        "Body of directive 10029 line a.\nLine b.\n",
        encoding="utf-8",
    )
    sources = list(iter_manual_section_13(manual))
    assert len(sources) == 2
    assert sources[0].source_ref.endswith("#directive-10028")
    assert "Body of directive 10028" in sources[0].source_text
    assert sources[1].source_ref.endswith("#directive-10029")
    assert sources[1].source_kind == "manual"


def test_iter_all_decision_sources_walks_all_three_doc_sources(tmp_path: Path):
    """Aggregator yields from rules + inventory + manual when db=None."""
    (tmp_path / "docs" / "governance").mkdir(parents=True)
    (tmp_path / "docs" / "architecture").mkdir(parents=True)
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "governance" / "CONSOLIDATED_RULES.md").write_text(
        "## RULE 1 — x\nBody.\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "architecture" / "keiracom_architecture_v2_inventory.md").write_text(
        "| x | y | RATIFIED-CEO | s | none | V1 |\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "MANUAL.md").write_text(
        "### Directive #1000 — title\nBody.\n", encoding="utf-8"
    )
    sources = list(iter_all_decision_sources(db=None, repo_root=tmp_path))
    assert len(sources) == 3


# ────────────────────────────────────────────────────────────────────────────
# Helpers — composition tags + serialize + parse_directive_json
# ────────────────────────────────────────────────────────────────────────────


def test_decision_composition_tags_returns_audit_review_band():
    tags = decision_composition_tags()
    assert tags["domain"] == "internal"
    assert tags["concern"] == "compliance"
    assert tags["applicable_context"] == "audit_review"


def test_serialize_decision_source_truncates_text():
    src = DecisionSource(source_ref="x", source_kind="manual", source_text="A" * 1000)
    serialized = serialize_decision_source(src)
    assert len(serialized["source_text_preview"]) == 400
    assert serialized["source_text_length"] == 1000


def test_parse_directive_json_parses_canonical_shape():
    body = (
        "DIRECTIVE #10028 — completion marker JSON:\n"
        '{"directive_id": 10028, "ratified_at": "2026-05-26T08:30:00Z"}'
    )
    parsed = parse_directive_json(body)
    assert parsed is not None
    assert parsed["directive_id"] == 10028


def test_parse_directive_json_returns_none_on_garbage():
    assert parse_directive_json("not a json directive") is None


def test_default_decisions_bank_is_fleet_decisions():
    assert DEFAULT_DECISIONS_BANK == "fleet_decisions"


# ────────────────────────────────────────────────────────────────────────────
# Response schema lock — decision-class atoms still fit atom_schema_v1
# ────────────────────────────────────────────────────────────────────────────


def test_response_schema_has_atoms_array():
    schema = DECISION_ATOMS_RESPONSE_SCHEMA["schema"]
    assert "atoms" in schema["properties"]
    assert schema["required"] == ["atoms"]


def test_response_schema_enum_locks_trigger_vocabulary():
    """Decision-atomizer's structured-output schema MUST enumerate same
    VALID_TRIGGER_KINDS as the skills atomizer — same atom_schema_v1
    constraint applies."""
    from src.keiracom_system.atomization.schema import VALID_TRIGGER_KINDS

    enum = set(
        DECISION_ATOMS_RESPONSE_SCHEMA["schema"]["properties"]["atoms"]["items"]["properties"][
            "trigger_condition"
        ]["properties"]["kind"]["enum"]
    )
    assert enum == set(VALID_TRIGGER_KINDS)


def test_response_schema_includes_supersedes_reference_optional():
    item_props = DECISION_ATOMS_RESPONSE_SCHEMA["schema"]["properties"]["atoms"]["items"][
        "properties"
    ]
    assert "supersedes_reference" in item_props


# ────────────────────────────────────────────────────────────────────────────
# DecisionsAtomizer behaviour
# ────────────────────────────────────────────────────────────────────────────


class _FakeLLM:
    def __init__(self, parsed: Any):
        self.parsed = parsed
        self.calls: list[dict] = []

    def call_structured(self, **kwargs):
        self.calls.append(kwargs)
        return LLMResponse(
            parsed=self.parsed,
            tokens_in=200,
            tokens_out=80,
            latency_ms=100,
            model=kwargs.get("model", "google/gemini-2.5-flash"),
        )


def _fake_tei() -> TEIClient:
    def fake_post(url, payload, timeout):
        n = len(payload["inputs"])
        body = (
            b"["
            + b",".join(b"[" + b",".join(b"0.1" for _ in range(384)) + b"]" for _ in range(n))
            + b"]"
        )
        return _HTTPResponse(200, body)

    def fake_get(url, timeout):
        return _HTTPResponse(200, b'{"status": "ok"}')

    return TEIClient(http_get=fake_get, http_post=fake_post)


class _MultiDB:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self._q: list[Any] = []

    def execute(self, query: str, *params):
        self.calls.append((query, params))

    def fetchone(self):
        return self._q.pop(0) if self._q else None

    def fetchall(self):
        return []

    def queue_many(self, rows):
        self._q.extend(rows)


def _well_formed_decision_atom() -> dict:
    return {
        "trigger_condition": {
            "kind": "context_predicate",
            "params": {"domain": "internal", "in_response_to": "compliance_audit"},
        },
        "content": "Cutover only at 100 percent pre-flight.",
        "anti_pattern": "Cutover with subscription burning down before all gate items met.",
        "example": (
            "RATIONALE: premature cutover burns 1500+ AUD in the first month. "
            "OUTCOME: rule ratified 2026-05-27 alongside CONCUR-GATE."
        ),
        "provenance": {
            "source": "ceo_memory:ceo:directive_10028_complete",
            "freshness": "2026-05-27T00:00:00Z",
            "confidence": 1.0,
            "last_validated": "2026-05-27T00:00:00Z",
        },
        "composition_tags": {
            "domain": "internal",
            "concern": "compliance",
            "applicable_context": "audit_review",
        },
        "supersedes_reference": None,
    }


def _make_decisions_atomizer(parsed: Any):
    tid = uuid4()
    db = _MultiDB()
    db.queue_many([(str(uuid4()),)])  # AtomStore INSERT returning atom_id
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    llm = _FakeLLM(parsed)
    return DecisionsAtomizer(llm=llm, store=store, job_db=db), llm, db


def test_atomize_rejects_empty_source_text():
    atomizer, _, _ = _make_decisions_atomizer({"atoms": []})
    with pytest.raises(DecisionsAtomizerError, match="source_text empty"):
        atomizer.atomize(DecisionSource(source_ref="x", source_kind="manual", source_text=""))


def test_atomize_writes_pending_then_atomizer_done():
    atomizer, _, db = _make_decisions_atomizer({"atoms": []})
    atomizer.atomize(
        DecisionSource(
            source_ref="docs/MANUAL.md#directive-10028",
            source_kind="manual",
            source_text="some directive content",
        )
    )
    # First execute = INSERT pending job row
    assert "INSERT INTO keiracom_atomizer_jobs" in db.calls[0][0]
    assert "'pending'" in db.calls[0][0]
    # Final = UPDATE to atomizer_done
    last_query = db.calls[-1][0]
    assert "UPDATE keiracom_atomizer_jobs" in last_query
    assert "atomizer_done" in last_query


def test_atomize_calls_llm_at_temperature_zero():
    atomizer, llm, _ = _make_decisions_atomizer({"atoms": [_well_formed_decision_atom()]})
    atomizer.atomize(DecisionSource(source_ref="x", source_kind="manual", source_text="t"))
    assert llm.calls[0]["temperature"] == 0.0


def test_atomize_invokes_atom_store_insert_per_atom():
    atomizer, _, db = _make_decisions_atomizer({"atoms": [_well_formed_decision_atom()]})
    job = atomizer.atomize(DecisionSource(source_ref="x", source_kind="manual", source_text="t"))
    assert job.atoms_produced == 1
    assert len(job.atom_ids) == 1
    atom_inserts = [c for c in db.calls if "INSERT INTO keiracom_atoms" in c[0]]
    assert len(atom_inserts) == 1


def test_atomize_extracts_supersedes_reference():
    raw = dict(_well_formed_decision_atom())
    raw["supersedes_reference"] = "ceo:four_store_completion_rule"
    atomizer, _, _ = _make_decisions_atomizer({"atoms": [raw]})
    job = atomizer.atomize(DecisionSource(source_ref="x", source_kind="manual", source_text="t"))
    assert "ceo:four_store_completion_rule" in job.supersedes_refs


def test_atomize_skips_blank_supersedes_reference():
    raw = dict(_well_formed_decision_atom())
    raw["supersedes_reference"] = ""
    atomizer, _, _ = _make_decisions_atomizer({"atoms": [raw]})
    job = atomizer.atomize(DecisionSource(source_ref="x", source_kind="manual", source_text="t"))
    assert job.supersedes_refs == []


def test_atomize_forces_default_composition_tags_when_llm_omits():
    """If LLM forgets composition_tags, atomizer fills with decision-class defaults."""
    raw = dict(_well_formed_decision_atom())
    raw["composition_tags"] = {}  # LLM omitted
    atomizer, _, _ = _make_decisions_atomizer({"atoms": [raw]})
    job = atomizer.atomize(DecisionSource(source_ref="x", source_kind="manual", source_text="t"))
    assert job.atoms_produced == 1


def test_atomize_rejects_non_list_atoms_payload():
    atomizer, _, db = _make_decisions_atomizer({"atoms": "not-a-list"})
    with pytest.raises(DecisionsAtomizerError, match="non-list payload"):
        atomizer.atomize(DecisionSource(source_ref="x", source_kind="manual", source_text="t"))
    # job marked failed
    failures = [c for c in db.calls if "status = 'failed'" in c[0]]
    assert len(failures) == 1


def test_atomize_emits_metering_with_decisions_flow_tag():
    captured: list[tuple[str, dict]] = []

    def emit(name, tags):
        captured.append((name, tags))

    tid = uuid4()
    db = _MultiDB()
    db.queue_many([(str(uuid4()),)])
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    llm = _FakeLLM({"atoms": [_well_formed_decision_atom()]})
    atomizer = DecisionsAtomizer(llm=llm, store=store, job_db=db, metric_emitter=emit)
    atomizer.atomize(DecisionSource(source_ref="x", source_kind="manual", source_text="t"))
    flow_tags = {tags.get("flow") for _, tags in captured}
    assert flow_tags == {"decisions"}


def test_decisions_bank_property():
    atomizer, _, _ = _make_decisions_atomizer({"atoms": []})
    assert atomizer.decisions_bank == DEFAULT_DECISIONS_BANK


# ────────────────────────────────────────────────────────────────────────────
# atomize_decisions_run() — dry-run + execute paths
# ────────────────────────────────────────────────────────────────────────────


def test_atomize_decisions_run_dry_run_does_not_call_atomizer():
    class _SpyAtomizer:
        def __init__(self):
            self.calls = []

        def atomize(self, source):
            self.calls.append(source)

    spy = _SpyAtomizer()
    sources = [
        DecisionSource(source_ref=f"x{i}", source_kind="manual", source_text="t") for i in range(3)
    ]
    rc = atomize_decisions_run(atomizer=spy, sources=sources, execute=False)
    assert rc == 0
    assert spy.calls == []  # dry-run skipped


def test_atomize_decisions_run_execute_atomizes_each_source():
    class _StubJob:
        atoms_produced = 1

    class _StubAtomizer:
        def __init__(self):
            self.calls = []

        def atomize(self, source):
            self.calls.append(source)
            return _StubJob()

    stub = _StubAtomizer()
    sources = [
        DecisionSource(source_ref="x1", source_kind="manual", source_text="t"),
        DecisionSource(source_ref="x2", source_kind="governance_doc", source_text="t"),
    ]
    rc = atomize_decisions_run(atomizer=stub, sources=sources, execute=True)
    assert rc == 0
    assert len(stub.calls) == 2


def test_atomize_decisions_run_returns_one_on_any_failure():
    class _FlakyAtomizer:
        def atomize(self, source):
            if source.source_ref == "bad":
                raise DecisionsAtomizerError("simulated")

            class _StubJob:
                atoms_produced = 1

            return _StubJob()

    sources = [
        DecisionSource(source_ref="good", source_kind="manual", source_text="t"),
        DecisionSource(source_ref="bad", source_kind="manual", source_text="t"),
    ]
    rc = atomize_decisions_run(atomizer=_FlakyAtomizer(), sources=sources, execute=True)
    assert rc == 1
