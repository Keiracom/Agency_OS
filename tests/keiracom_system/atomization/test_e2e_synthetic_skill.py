"""Week 1 acceptance test — synthetic skill atomized end-to-end with verifier pass.

Per Elliot dispatch: "Synthetic skill atomized end-to-end with verifier pass =
Week 1 acceptance."

Uses fake LLM + fake DB so no live Gemini key + no Postgres dependency. The
fakes return canned structured outputs matching ATOMS_RESPONSE_SCHEMA /
VERIFIER_RESPONSE_SCHEMA — the real Gemini Flash + Pro would emit identically-
shaped responses on real input.

Locks the integration contract: atomizer→store→verifier→store→job-row
sequence works without coupling between the components beyond the documented
Protocol surfaces.
"""

from typing import Any
from uuid import UUID, uuid4

from src.keiracom_system.atomization.atom_store import AtomStore
from src.keiracom_system.atomization.atomizer import Atomizer
from src.keiracom_system.atomization.llm_client import LLMResponse
from src.keiracom_system.atomization.verifier import Verifier
from src.keiracom_system.embeddings.tei_client import TEIClient, _HTTPResponse

SYNTHETIC_SKILL_TEXT = """\
# /summarize skill

When the user asks Keira to summarize a document, return exactly 3 bullet
points. Each bullet should be one sentence covering one key idea.

DO NOT return a paragraph — bullets only.

Example:
  Q: Summarize the Q4 results.
  A:
    - Revenue grew 22% year-over-year, driven by enterprise tier adoption.
    - Operating margin expanded 4 percentage points on lower customer acquisition cost.
    - Active customer count crossed 5,000 for the first time.
"""


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


# Canned Gemini Flash response for the synthetic skill above.
SYNTHETIC_ATOMIZER_PARSED = {
    "atoms": [
        {
            "trigger_condition": {
                "kind": "request_shape",
                "params": {"intent": "summarize", "object_type": "document"},
            },
            "content": "When the user asks Keira to summarize a document, return exactly 3 bullet points.",
            "anti_pattern": "Returning a paragraph instead of bullets.",
            "example": "Q: Summarize Q4. A: - revenue grew - margin expanded - customers crossed 5000",
            "provenance": {
                "source": "skills/summarize.md@v1",
                "freshness": "2026-05-26T11:00:00Z",
                "confidence": 0.93,
                "last_validated": "2026-05-26T11:00:00Z",
            },
        },
        {
            "trigger_condition": {
                "kind": "context_predicate",
                "params": {"in_response_to": "summarize_intent"},
            },
            "content": "Each bullet should be one sentence covering one key idea.",
            "anti_pattern": "Multi-sentence bullets or bullets that overlap on the same idea.",
            "example": None,
            "provenance": {
                "source": "skills/summarize.md@v1",
                "freshness": "2026-05-26T11:00:00Z",
                "confidence": 0.91,
                "last_validated": "2026-05-26T11:00:00Z",
            },
        },
    ]
}

# Canned Gemini Pro verifier response — clean batch (no flags).
CLEAN_VERIFIER_PARSED = {"flags": []}


class _IntegrationDB:
    """Single DB fake used by AtomStore + Atomizer.job_db + Verifier.job_db."""

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
    def __init__(self, parsed: Any, *, tokens_in: int = 250, tokens_out: int = 180):
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
            latency_ms=120,
            model=kwargs["model"],
        )


def test_synthetic_skill_e2e_atomize_then_verify_clean():
    """Week 1 acceptance: synthetic skill → 2 atoms → verifier returns 0 flags.

    Sequence:
      1. Atomizer.atomize(source_text=synthetic_skill) — Gemini Flash fake
         returns 2 well-formed atoms. AtomStore.insert_atom invoked twice.
         Job row UPDATE'd to atomizer_done.
      2. Verifier.verify(job_id, atom_ids) — Gemini Pro fake returns 0 flags.
         Job row UPDATE'd to verifier_done with verifier_flags='[]'.
    """
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")  # Dave's tenant
    db = _IntegrationDB()
    # AtomStore insert flow: each insert_atom returns an atom_id via fetchone.
    # 2 atoms = 2 fetchone results for INSERT, plus we'll need verifier-side
    # get_atom fetchones (2 atoms read back).
    expected_atom_ids = [uuid4(), uuid4()]
    # Atomizer flow:
    #  - INSERT job row (no fetchone needed)
    #  - INSERT atom 1 → returns atom_id 1
    #  - INSERT atom 2 → returns atom_id 2
    #  - UPDATE job to atomizer_done (no fetchone)
    # Verifier flow:
    #  - get_atom(atom 1) → returns row
    #  - get_atom(atom 2) → returns row
    #  - LLM call
    #  - UPDATE job to verifier_done
    db.queue_many(
        [
            (str(expected_atom_ids[0]),),  # atomizer insert atom 1
            (str(expected_atom_ids[1]),),  # atomizer insert atom 2
            (  # verifier get_atom(atom 1)
                str(expected_atom_ids[0]),
                str(tenant_id),
                '{"kind": "request_shape", "params": {"intent": "summarize"}}',
                "atom 1 content",
                None,
                None,
                '{"source": "x", "freshness": "2026-05-26T11:00:00Z", '
                '"confidence": 0.93, "last_validated": "2026-05-26T11:00:00Z"}',
                None,
                1,
                "active",
            ),
            (  # verifier get_atom(atom 2)
                str(expected_atom_ids[1]),
                str(tenant_id),
                '{"kind": "context_predicate", "params": {}}',
                "atom 2 content",
                None,
                None,
                '{"source": "x", "freshness": "2026-05-26T11:00:00Z", '
                '"confidence": 0.91, "last_validated": "2026-05-26T11:00:00Z"}',
                None,
                1,
                "active",
            ),
        ]
    )

    store = AtomStore(db=db, tenant_id=tenant_id, embedder=_fake_tei())
    atomizer_llm = _FakeLLM(SYNTHETIC_ATOMIZER_PARSED)
    verifier_llm = _FakeLLM(CLEAN_VERIFIER_PARSED)

    # Captures metrics for both atomizer + verifier emission paths
    captured: list[tuple[str, dict]] = []

    def emit(name, tags):
        captured.append((name, tags))

    atomizer = Atomizer(llm=atomizer_llm, store=store, job_db=db, metric_emitter=emit)
    verifier = Verifier(llm=verifier_llm, store=store, job_db=db, metric_emitter=emit)

    # 1. ATOMIZE
    job = atomizer.atomize(
        source_ref="skills/summarize.md@v1",
        source_kind="skill",
        source_text=SYNTHETIC_SKILL_TEXT,
    )
    assert job.atoms_produced == 2
    assert len(job.atom_ids) == 2
    assert job.status == "atomizer_done"
    assert job.atomizer_tokens_in == 250
    assert job.atomizer_tokens_out == 180

    # 2. VERIFY
    flags = verifier.verify(job_id=job.job_id, atom_ids=job.atom_ids)
    assert flags == []

    # SQL invariants
    job_inserts = [c for c in db.calls if "INSERT INTO keiracom_atomizer_jobs" in c[0]]
    assert len(job_inserts) == 1  # one job row
    assert "'pending'" in job_inserts[0][0]

    atom_inserts = [c for c in db.calls if "INSERT INTO keiracom_atoms" in c[0]]
    assert len(atom_inserts) == 2  # 2 atoms inserted

    atomizer_done_updates = [c for c in db.calls if "atomizer_done" in c[0]]
    assert len(atomizer_done_updates) == 1

    verifier_done_updates = [c for c in db.calls if "verifier_done" in c[0]]
    assert len(verifier_done_updates) == 1

    # Metric invariants — atomizer emitted 4 metric names + verifier emitted 0
    # (no flags on a clean batch).
    atomizer_metric_names = {
        n for n, _ in captured if "atomization.atomizer" in n or "atomization.atoms" in n
    }
    assert atomizer_metric_names == {
        "keiracom.atomization.atomizer.tokens",
        "keiracom.atomization.atomizer.latency_ms",
        "keiracom.atomization.atoms_produced",
    }

    verifier_metric_count = sum(1 for n, _ in captured if "atomization.verifier" in n)
    assert verifier_metric_count == 0  # no flags → no verifier metric


def test_synthetic_skill_e2e_with_verifier_flag():
    """Same shape but verifier flags one atom — flag persisted, severity emitted."""
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    db = _IntegrationDB()
    expected_atom_ids = [uuid4(), uuid4()]
    db.queue_many(
        [
            (str(expected_atom_ids[0]),),
            (str(expected_atom_ids[1]),),
            (
                str(expected_atom_ids[0]),
                str(tenant_id),
                '{"kind": "request_shape", "params": {}}',
                "atom 1",
                None,
                None,
                '{"source": "x", "freshness": "2026-05-26T11:00:00Z", '
                '"confidence": 0.9, "last_validated": "2026-05-26T11:00:00Z"}',
                None,
                1,
                "active",
            ),
            (
                str(expected_atom_ids[1]),
                str(tenant_id),
                '{"kind": "context_predicate", "params": {}}',
                "atom 2",
                None,
                None,
                '{"source": "x", "freshness": "2026-05-26T11:00:00Z", '
                '"confidence": 0.9, "last_validated": "2026-05-26T11:00:00Z"}',
                None,
                1,
                "active",
            ),
        ]
    )
    store = AtomStore(db=db, tenant_id=tenant_id, embedder=_fake_tei())
    atomizer_llm = _FakeLLM(SYNTHETIC_ATOMIZER_PARSED)
    verifier_parsed_with_flag = {
        "flags": [
            {
                "atom_index": 1,
                "category": "trigger_unspecific",
                "severity": "warning",
                "message": "context_predicate params empty",
            }
        ]
    }
    verifier_llm = _FakeLLM(verifier_parsed_with_flag)
    captured: list[tuple[str, dict]] = []

    def emit(name, tags):
        captured.append((name, tags))

    atomizer = Atomizer(llm=atomizer_llm, store=store, job_db=db, metric_emitter=emit)
    verifier = Verifier(llm=verifier_llm, store=store, job_db=db, metric_emitter=emit)

    job = atomizer.atomize(source_ref="x", source_kind="skill", source_text="t")
    flags = verifier.verify(job_id=job.job_id, atom_ids=job.atom_ids)

    assert len(flags) == 1
    assert flags[0].severity == "warning"
    assert "trigger_unspecific" in flags[0].message
    # Verifier flag metric emitted
    verifier_flag_metrics = [n for n, _ in captured if n == "keiracom.atomization.verifier.flags"]
    assert verifier_flag_metrics == ["keiracom.atomization.verifier.flags"]
