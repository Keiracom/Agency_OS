"""Verifier unit tests — uses fake LLM client + AtomStore + job DB."""

from typing import Any
from uuid import UUID, uuid4

import pytest

from src.keiracom_system.atomization.atom_store import AtomStore
from src.keiracom_system.atomization.llm_client import LLMResponse
from src.keiracom_system.atomization.verifier import (
    SEVERITY_BLOCKING,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    VALID_SEVERITIES,
    VERIFIER_RESPONSE_SCHEMA,
    Verifier,
    VerifierError,
    VerifierFlag,
)
from src.keiracom_system.embeddings.tei_client import TEIClient, _HTTPResponse


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

    def execute(self, query, *params):
        self.calls.append((query, params))

    def fetchone(self):
        return self._q.pop(0) if self._q else None

    def fetchall(self):
        return []

    def queue_many(self, rows):
        self._q.extend(rows)


class _FakeLLM:
    def __init__(self, parsed: Any):
        self.parsed = parsed
        self.calls: list[dict] = []

    def call_structured(self, **kwargs):
        self.calls.append(kwargs)
        return LLMResponse(
            parsed=self.parsed,
            tokens_in=100,
            tokens_out=50,
            latency_ms=84,
            model=kwargs.get("model", "test/pro"),
        )


def _stored_atom_row(atom_id: UUID, tenant_id: UUID) -> tuple:
    return (
        str(atom_id),
        str(tenant_id),
        '{"kind": "request_shape", "params": {"q": "x"}}',
        "stored content",
        None,
        None,
        '{"source": "x", "freshness": "2026-05-26T11:00:00Z", '
        '"confidence": 0.9, "last_validated": "2026-05-26T11:00:00Z"}',
        None,
        1,
        "active",
    )


# ----- VerifierFlag invariants ---------------------------------------------


def test_verifier_flag_valid():
    f = VerifierFlag(atom_id=uuid4(), severity=SEVERITY_WARNING, message="x")
    assert f.severity == SEVERITY_WARNING


def test_verifier_flag_rejects_unknown_severity():
    with pytest.raises(VerifierError, match="severity"):
        VerifierFlag(atom_id=uuid4(), severity="_bogus", message="x")


def test_valid_severities_three():
    assert frozenset({SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_BLOCKING}) == VALID_SEVERITIES


# ----- Verifier behaviour --------------------------------------------------


def _make_verifier(parsed: Any, *, db: _MultiDB | None = None):
    tid = uuid4()
    db = db or _MultiDB()
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    llm = _FakeLLM(parsed)
    return Verifier(llm=llm, store=store, job_db=db), llm, db, tid


def test_verify_empty_atom_list_returns_empty_flags():
    verifier, _, db, _ = _make_verifier({"flags": []})
    flags = verifier.verify(job_id=uuid4(), atom_ids=[])
    assert flags == []
    # Still marks verifier_done with empty flags JSON
    update_calls = [c for c in db.calls if "verifier_done" in c[0]]
    assert len(update_calls) == 1


def test_verify_marks_verifier_done_on_clean_batch():
    aid = uuid4()
    verifier, _, db, tid = _make_verifier({"flags": []})
    db.queue_many([_stored_atom_row(aid, tid)])
    flags = verifier.verify(job_id=uuid4(), atom_ids=[aid])
    assert flags == []
    update_calls = [c for c in db.calls if "verifier_done" in c[0]]
    assert len(update_calls) == 1


def test_verify_persists_flag_payload():
    """Verifier flags returned by LLM get persisted as JSONB to job row."""
    aid = uuid4()
    parsed = {
        "flags": [
            {
                "atom_index": 0,
                "category": "trigger_unspecific",
                "severity": "warning",
                "message": "params too vague",
            }
        ]
    }
    verifier, _, db, tid = _make_verifier(parsed)
    db.queue_many([_stored_atom_row(aid, tid)])
    flags = verifier.verify(job_id=uuid4(), atom_ids=[aid])
    assert len(flags) == 1
    assert flags[0].atom_id == aid
    assert flags[0].severity == "warning"
    assert "trigger_unspecific" in flags[0].message
    # JSON serialized into the UPDATE call
    update_call = next(c for c in db.calls if "verifier_done" in c[0])
    serialized_flags = update_call[1][4]
    assert "trigger_unspecific" in serialized_flags
    assert "warning" in serialized_flags


def test_verify_drops_out_of_range_atom_index():
    """LLM might emit atom_index=99 for a 2-atom batch — silently drop, don't crash."""
    aid = uuid4()
    parsed = {
        "flags": [
            {"atom_index": 99, "category": "grain_violation", "severity": "warning", "message": "x"}
        ]
    }
    verifier, _, db, tid = _make_verifier(parsed)
    db.queue_many([_stored_atom_row(aid, tid)])
    flags = verifier.verify(job_id=uuid4(), atom_ids=[aid])
    assert flags == []


def test_verify_drops_unknown_severity():
    """Invalid severity → log warning + drop the flag."""
    aid = uuid4()
    parsed = {
        "flags": [
            {"atom_index": 0, "category": "grain_violation", "severity": "_bogus", "message": "x"}
        ]
    }
    verifier, _, db, tid = _make_verifier(parsed)
    db.queue_many([_stored_atom_row(aid, tid)])
    flags = verifier.verify(job_id=uuid4(), atom_ids=[aid])
    assert flags == []


def test_verify_calls_llm_with_atom_payload():
    """Verifier sends atoms as JSON array to the LLM."""
    aid = uuid4()
    verifier, llm, db, tid = _make_verifier({"flags": []})
    db.queue_many([_stored_atom_row(aid, tid)])
    verifier.verify(job_id=uuid4(), atom_ids=[aid])
    user_msg = next(m for m in llm.calls[0]["messages"] if m["role"] == "user")
    import json as _json

    payload = _json.loads(user_msg["content"])
    assert "atoms" in payload
    assert len(payload["atoms"]) == 1


def test_verifier_response_schema_has_severity_enum():
    """Schema locks 3-severity vocabulary."""
    schema_enum = set(
        VERIFIER_RESPONSE_SCHEMA["schema"]["properties"]["flags"]["items"]["properties"][
            "severity"
        ]["enum"]
    )
    assert schema_enum == {"info", "warning", "blocking"}


def test_verify_skips_atoms_not_in_store():
    """If get_atom returns None (e.g. wrong tenant), the atom is silently skipped."""
    aid_a = uuid4()
    aid_b = uuid4()
    verifier, _, db, tid = _make_verifier({"flags": []})
    # First atom found, second not found (None)
    db.queue_many([_stored_atom_row(aid_a, tid), None])
    flags = verifier.verify(job_id=uuid4(), atom_ids=[aid_a, aid_b])
    assert flags == []


def test_verify_emits_metering_per_flag():
    """Each flag → 1 keiracom.atomization.verifier.flags metric."""
    captured: list[tuple[str, dict]] = []

    def emit(name, tags):
        captured.append((name, tags))

    aid = uuid4()
    parsed = {
        "flags": [
            {
                "atom_index": 0,
                "category": "factual_incoherence",
                "severity": "blocking",
                "message": "x",
            }
        ]
    }
    tid = uuid4()
    db = _MultiDB()
    db.queue_many([_stored_atom_row(aid, tid)])
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    llm = _FakeLLM(parsed)
    verifier = Verifier(llm=llm, store=store, job_db=db, metric_emitter=emit)
    verifier.verify(job_id=uuid4(), atom_ids=[aid])
    flag_metrics = [(n, t) for n, t in captured if n == "keiracom.atomization.verifier.flags"]
    assert len(flag_metrics) == 1
    assert flag_metrics[0][1]["severity"] == "blocking"
