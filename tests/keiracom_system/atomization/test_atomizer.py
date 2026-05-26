"""Atomizer unit tests — uses fake LLM client + AtomStore + job DB."""

from typing import Any
from uuid import uuid4

import pytest

from src.keiracom_system.atomization.atom_store import AtomStore
from src.keiracom_system.atomization.atomizer import (
    ATOMS_RESPONSE_SCHEMA,
    FEATURE_FLAG_ENV,
    Atomizer,
    AtomizerError,
    is_atomizer_enabled,
)
from src.keiracom_system.atomization.llm_client import LLMResponse
from src.keiracom_system.embeddings.tei_client import TEIClient, _HTTPResponse


def _fake_tei() -> TEIClient:
    def fake_post(url: str, payload: dict[str, Any], timeout: float) -> _HTTPResponse:
        n = len(payload["inputs"])
        body = (
            b"["
            + b",".join(b"[" + b",".join(b"0.1" for _ in range(384)) + b"]" for _ in range(n))
            + b"]"
        )
        return _HTTPResponse(200, body)

    def fake_get(url: str, timeout: float) -> _HTTPResponse:
        return _HTTPResponse(200, b'{"status": "ok"}')

    return TEIClient(http_get=fake_get, http_post=fake_post)


class _FakeDB:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self._next_one: Any = None

    def execute(self, query: str, *params):
        self.calls.append((query, params))

    def fetchone(self):
        return self._next_one

    def fetchall(self):
        return []

    def queue_fetchone(self, row: Any) -> None:
        self._next_one = row


class _FakeLLM:
    """Returns canned LLMResponse — no live LiteLLM call."""

    def __init__(self, parsed: Any, *, tokens_in: int = 100, tokens_out: int = 50):
        self.parsed = parsed
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.calls: list[dict] = []

    def call_structured(self, **kwargs):
        self.calls.append(kwargs)
        return LLMResponse(
            parsed=self.parsed,
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
            latency_ms=42,
            model=kwargs.get("model", "test/model"),
        )


def _well_formed_atom() -> dict:
    return {
        "trigger_condition": {"kind": "request_shape", "params": {"matches": "summarize"}},
        "content": "When user asks to summarize, return 3 bullet points.",
        "anti_pattern": "Returning a long paragraph instead of bullets.",
        "example": "Q: summarize X. A: - point 1\n- point 2\n- point 3",
        "provenance": {
            "source": "skills/summarize.md@abc",
            "freshness": "2026-05-26T11:00:00Z",
            "confidence": 0.92,
            "last_validated": "2026-05-26T11:00:00Z",
        },
    }


# ----- Feature flag --------------------------------------------------------


def test_atomizer_disabled_by_default(monkeypatch):
    monkeypatch.delenv(FEATURE_FLAG_ENV, raising=False)
    assert is_atomizer_enabled() is False


def test_atomizer_enabled_when_env_on(monkeypatch):
    monkeypatch.setenv(FEATURE_FLAG_ENV, "on")
    assert is_atomizer_enabled() is True


def test_atomizer_disabled_for_other_env_values(monkeypatch):
    monkeypatch.setenv(FEATURE_FLAG_ENV, "false")
    assert is_atomizer_enabled() is False


# ----- Response schema lock ------------------------------------------------


def test_response_schema_enum_locks_trigger_vocabulary():
    """Atomizer's structured-output schema MUST enumerate VALID_TRIGGER_KINDS.

    If a future PR adds a kind to the vocabulary, ATOMS_RESPONSE_SCHEMA must
    update — otherwise Gemini refuses to emit the new kind. Test locks parity.
    """
    from src.keiracom_system.atomization.schema import VALID_TRIGGER_KINDS

    schema_enum = set(
        ATOMS_RESPONSE_SCHEMA["schema"]["properties"]["atoms"]["items"]["properties"][
            "trigger_condition"
        ]["properties"]["kind"]["enum"]
    )
    assert schema_enum == set(VALID_TRIGGER_KINDS)


# ----- atomize() happy path + invariants -----------------------------------


def _make_atomizer(parsed: Any, *, db: _FakeDB | None = None):
    tid = uuid4()
    db = db or _FakeDB()
    db.queue_fetchone((str(uuid4()),))  # AtomStore INSERT returning atom_id
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    llm = _FakeLLM(parsed)
    return Atomizer(llm=llm, store=store, job_db=db), llm, db


def test_atomize_rejects_invalid_source_kind():
    atomizer, _, _ = _make_atomizer({"atoms": []})
    with pytest.raises(AtomizerError, match="source_kind"):
        atomizer.atomize(source_ref="x", source_kind="_bogus", source_text="t")


def test_atomize_rejects_empty_source_text():
    atomizer, _, _ = _make_atomizer({"atoms": []})
    with pytest.raises(AtomizerError, match="source_text must be non-empty"):
        atomizer.atomize(source_ref="x", source_kind="skill", source_text="")


def test_atomize_writes_pending_then_atomizer_done():
    """Job row INSERTed pending BEFORE LLM, UPDATEd to atomizer_done AFTER."""
    atomizer, _llm, db = _make_atomizer({"atoms": []})
    atomizer.atomize(source_ref="skills/test.md", source_kind="skill", source_text="content")
    # First execute: INSERT job row with status='pending'
    assert "INSERT INTO keiracom_atomizer_jobs" in db.calls[0][0]
    assert "'pending'" in db.calls[0][0]
    # Final execute: UPDATE job row status='atomizer_done'
    last = db.calls[-1][0]
    assert "UPDATE keiracom_atomizer_jobs" in last
    assert "atomizer_done" in last


def test_atomize_calls_llm_at_temperature_zero():
    atomizer, llm, _ = _make_atomizer({"atoms": []})
    atomizer.atomize(source_ref="x", source_kind="skill", source_text="t")
    assert llm.calls[0]["temperature"] == 0.0


def test_atomize_invokes_atom_store_insert_per_atom():
    """One atom in response → one INSERT INTO keiracom_atoms."""

    # Multi-queue DB for the multiple fetchones needed
    class _MultiDB(_FakeDB):
        def __init__(self):
            super().__init__()
            self._q = []

        def queue_many(self, rows):
            self._q.extend(rows)

        def fetchone(self):
            return self._q.pop(0) if self._q else None

    db = _MultiDB()
    # 1 atom → 1 INSERT INTO keiracom_atoms → 1 fetchone returning atom_id
    db.queue_many([(str(uuid4()),)])
    tid = uuid4()
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    llm = _FakeLLM({"atoms": [_well_formed_atom()]})
    atomizer = Atomizer(llm=llm, store=store, job_db=db)
    job = atomizer.atomize(source_ref="x", source_kind="skill", source_text="t")
    assert job.atoms_produced == 1
    assert len(job.atom_ids) == 1
    # Check that an INSERT INTO keiracom_atoms call landed in db.calls
    atom_inserts = [c for c in db.calls if "INSERT INTO keiracom_atoms" in c[0]]
    assert len(atom_inserts) == 1


def test_atomize_emits_metering_when_emitter_provided():
    """Metric emitter receives 4 metric names per atomize() call."""
    captured: list[tuple[str, dict]] = []

    def emit(name: str, tags: dict[str, str]) -> None:
        captured.append((name, tags))

    class _MultiDB(_FakeDB):
        def __init__(self):
            super().__init__()
            self._q = []

        def queue_many(self, rows):
            self._q.extend(rows)

        def fetchone(self):
            return self._q.pop(0) if self._q else None

    db = _MultiDB()
    db.queue_many([(str(uuid4()),)])
    tid = uuid4()
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    llm = _FakeLLM({"atoms": [_well_formed_atom()]})
    atomizer = Atomizer(llm=llm, store=store, job_db=db, metric_emitter=emit)
    atomizer.atomize(source_ref="x", source_kind="skill", source_text="t")
    names = {n for n, _ in captured}
    assert "keiracom.atomization.atomizer.tokens" in names
    assert "keiracom.atomization.atomizer.latency_ms" in names
    assert "keiracom.atomization.atoms_produced" in names


def test_atomize_rejects_non_list_atoms_payload():
    """If LLM returns malformed shape, job marked failed + AtomizerError raised."""
    atomizer, _, db = _make_atomizer({"atoms": "not-a-list"})
    with pytest.raises(AtomizerError, match="non-list 'atoms' payload"):
        atomizer.atomize(source_ref="x", source_kind="skill", source_text="t")
    # job row updated to 'failed'
    failures = [c for c in db.calls if "status = 'failed'" in c[0]]
    assert len(failures) == 1


def test_atomize_handles_atom_with_invalid_trigger():
    """A single malformed atom in the response raises AtomizerError + marks failed."""

    class _MultiDB(_FakeDB):
        def __init__(self):
            super().__init__()
            self._q = []

        def queue_many(self, rows):
            self._q.extend(rows)

        def fetchone(self):
            return self._q.pop(0) if self._q else None

    bad_atom = dict(_well_formed_atom())
    bad_atom["trigger_condition"] = {"kind": "_bogus", "params": {}}
    db = _MultiDB()
    tid = uuid4()
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    llm = _FakeLLM({"atoms": [bad_atom]})
    atomizer = Atomizer(llm=llm, store=store, job_db=db)
    with pytest.raises(ValueError, match="kind"):  # raised by AtomV1.__post_init__
        atomizer.atomize(source_ref="x", source_kind="skill", source_text="t")
