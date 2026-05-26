"""AtomStore unit tests — tenant-prefix guard + insert/retrieve + supersession."""

from typing import Any
from uuid import UUID, uuid4

import pytest

from src.keiracom_system.atomization.atom_store import AtomStore, AtomStoreError
from src.keiracom_system.atomization.schema import (
    AtomV1,
    SupersessionEdgeV1,
)
from src.keiracom_system.embeddings.tei_client import TEIClient, _HTTPResponse


class _FakeDB:
    """Minimal DB fake — record executes + serve canned fetchone/fetchall."""

    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self._next_one: Any = None
        self._next_all: list[Any] = []

    def execute(self, query: str, *params):
        self.calls.append((query, params))

    def fetchone(self):
        return self._next_one

    def fetchall(self):
        return self._next_all

    def queue_fetchone(self, row: Any) -> None:
        self._next_one = row

    def queue_fetchall(self, rows: list[Any]) -> None:
        self._next_all = rows


def _fake_tei() -> TEIClient:
    """TEIClient with HTTP DI — returns deterministic 384-dim vectors of 0.1."""

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


def _make_atom(tenant_id: UUID) -> AtomV1:
    return AtomV1(
        atom_id=uuid4(),
        tenant_id=tenant_id,
        trigger_condition={"kind": "request_shape", "params": {"q": "x"}},
        content="test content",
        anti_pattern=None,
        example=None,
        provenance={
            "source": "test",
            "freshness": "2026-05-26T11:00:00Z",
            "confidence": 0.9,
            "last_validated": "2026-05-26T11:00:00Z",
        },
    )


# ----- Construction invariants ---------------------------------------------


def test_init_rejects_empty_tenant_id():
    with pytest.raises(AtomStoreError, match="tenant_id is required"):
        AtomStore(db=_FakeDB(), tenant_id="", embedder=_fake_tei())


def test_tenant_id_property():
    tid = str(uuid4())
    store = AtomStore(db=_FakeDB(), tenant_id=tid, embedder=_fake_tei())
    assert store.tenant_id == tid


# ----- Tenant-prefix guard (read/write boundary defence-in-depth) ----------


def test_insert_atom_rejects_cross_tenant():
    tid_a = uuid4()
    tid_b = uuid4()
    store = AtomStore(db=_FakeDB(), tenant_id=tid_a, embedder=_fake_tei())
    atom = _make_atom(tid_b)  # built for tenant B
    with pytest.raises(AtomStoreError, match="tenant_id mismatch"):
        store.insert_atom(atom)


def test_insert_supersession_edge_rejects_cross_tenant():
    tid_a = uuid4()
    tid_b = uuid4()
    store = AtomStore(db=_FakeDB(), tenant_id=tid_a, embedder=_fake_tei())
    edge = SupersessionEdgeV1(
        edge_id=uuid4(),
        tenant_id=tid_b,
        predecessor_atom=uuid4(),
        successor_atom=uuid4(),
        relationship_type="supersedes",
        confidence=0.9,
    )
    with pytest.raises(AtomStoreError, match="tenant_id mismatch"):
        store.insert_supersession_edge(edge)


# ----- insert_atom happy path + embedding computation ----------------------


def test_insert_atom_returns_atom_id_and_invokes_execute():
    tid = uuid4()
    db = _FakeDB()
    atom = _make_atom(tid)
    db.queue_fetchone((str(atom.atom_id),))
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    returned = store.insert_atom(atom)
    assert returned == atom.atom_id
    assert len(db.calls) == 1
    assert "INSERT INTO keiracom_atoms" in db.calls[0][0]


def test_insert_atom_computes_embedding_when_absent():
    """Atom built without content_embedding gets one computed from TEIClient."""
    tid = uuid4()
    db = _FakeDB()
    atom = _make_atom(tid)
    db.queue_fetchone((str(atom.atom_id),))
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    store.insert_atom(atom)
    # Embedding is the 9th positional param (atom_id, tenant_id, trigger,
    # content, anti, example, provenance, composition_tags, embedding, ...)
    params = db.calls[0][1]
    embedding_arg = params[8]
    # pgvector string format
    assert embedding_arg.startswith("[")
    assert embedding_arg.endswith("]")


def test_insert_atom_raises_on_no_row_returned():
    """If RETURNING gives no row, that's an error (should never happen)."""
    tid = uuid4()
    db = _FakeDB()
    db.queue_fetchone(None)
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    with pytest.raises(AtomStoreError, match="no atom_id returned"):
        store.insert_atom(_make_atom(tid))


# ----- get_atom + cross-tenant collapse ------------------------------------


def test_get_atom_returns_none_when_not_found():
    tid = uuid4()
    db = _FakeDB()
    db.queue_fetchone(None)
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    assert store.get_atom(uuid4()) is None


def test_get_atom_query_includes_tenant_filter():
    tid = uuid4()
    db = _FakeDB()
    db.queue_fetchone(None)
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    store.get_atom(uuid4())
    query, params = db.calls[0]
    assert "tenant_id = %s" in query
    assert params[1] == str(tid)


def test_get_atom_builds_atom_v1_from_row():
    tid = uuid4()
    aid = uuid4()
    db = _FakeDB()
    db.queue_fetchone(
        (
            str(aid),
            str(tid),
            '{"kind": "request_shape", "params": {"x": 1}}',
            "stored content",
            None,
            None,
            '{"source": "x", "freshness": "2026-05-26T11:00:00Z", '
            '"confidence": 0.9, "last_validated": "2026-05-26T11:00:00Z"}',
            None,
            1,
            "active",
        )
    )
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    atom = store.get_atom(aid)
    assert atom is not None
    assert atom.atom_id == aid
    assert atom.content == "stored content"
    assert atom.state == "active"


# ----- retrieve_top_k ------------------------------------------------------


def test_retrieve_top_k_filters_by_tenant_and_active_state():
    tid = uuid4()
    db = _FakeDB()
    db.queue_fetchall([])
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    store.retrieve_top_k("anchor query", top_k=5)
    query, params = db.calls[0]
    assert "tenant_id = %s" in query
    assert "state = 'active'" in query
    assert params[0] == str(tid)
    assert params[2] == 5


def test_retrieve_top_k_rejects_non_positive():
    tid = uuid4()
    store = AtomStore(db=_FakeDB(), tenant_id=tid, embedder=_fake_tei())
    with pytest.raises(AtomStoreError, match="top_k must be > 0"):
        store.retrieve_top_k("x", top_k=0)


# ----- transition_state ----------------------------------------------------


def test_transition_state_to_cold_archive():
    tid = uuid4()
    db = _FakeDB()
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    store.transition_state(uuid4(), "cold_archive")
    query, params = db.calls[0]
    assert "UPDATE keiracom_atoms" in query
    assert params[0] == "cold_archive"
    assert params[2] == str(tid)  # tenant filter present


def test_transition_state_rejects_invalid():
    tid = uuid4()
    store = AtomStore(db=_FakeDB(), tenant_id=tid, embedder=_fake_tei())
    with pytest.raises(AtomStoreError, match="not in"):
        store.transition_state(uuid4(), "_bogus")


# ----- insert_supersession_edge --------------------------------------------


def test_insert_supersession_edge_verifies_endpoints_exist():
    tid = uuid4()
    pred_id = uuid4()
    succ_id = uuid4()
    db = _FakeDB()
    # First get_atom call (predecessor) → returns None
    db.queue_fetchone(None)
    store = AtomStore(db=db, tenant_id=tid, embedder=_fake_tei())
    edge = SupersessionEdgeV1(
        edge_id=uuid4(),
        tenant_id=tid,
        predecessor_atom=pred_id,
        successor_atom=succ_id,
        relationship_type="supersedes",
        confidence=0.9,
    )
    with pytest.raises(AtomStoreError, match="predecessor_atom .* not found"):
        store.insert_supersession_edge(edge)


def test_insert_supersession_edge_happy_path():
    tid = uuid4()
    pred_id = uuid4()
    succ_id = uuid4()
    # _MultiStubDB defined below; pred/succ rows + edge_id queued via queue_many.
    pred_row = (
        str(pred_id),
        str(tid),
        '{"kind": "request_shape", "params": {}}',
        "pred content",
        None,
        None,
        '{"source": "x", "freshness": "2026-05-26T11:00:00Z", "confidence": 0.9, "last_validated": "2026-05-26T11:00:00Z"}',
        None,
        1,
        "active",
    )
    succ_row = (
        str(succ_id),
        str(tid),
        '{"kind": "request_shape", "params": {}}',
        "succ content",
        None,
        None,
        '{"source": "x", "freshness": "2026-05-26T11:00:00Z", "confidence": 0.9, "last_validated": "2026-05-26T11:00:00Z"}',
        None,
        1,
        "active",
    )
    edge_id = uuid4()

    # _FakeDB only has 1 slot of queued fetchone. Use a custom stub instead.
    class _MultiStubDB(_FakeDB):
        def __init__(self):
            super().__init__()
            self._queue: list[Any] = []

        def queue_many(self, rows: list[Any]) -> None:
            self._queue.extend(rows)

        def fetchone(self):
            return self._queue.pop(0) if self._queue else None

    db2 = _MultiStubDB()
    db2.queue_many([pred_row, succ_row, (str(edge_id),)])
    store = AtomStore(db=db2, tenant_id=tid, embedder=_fake_tei())
    edge = SupersessionEdgeV1(
        edge_id=edge_id,
        tenant_id=tid,
        predecessor_atom=pred_id,
        successor_atom=succ_id,
        relationship_type="supersedes",
        confidence=0.9,
    )
    returned = store.insert_supersession_edge(edge)
    assert returned == edge_id
