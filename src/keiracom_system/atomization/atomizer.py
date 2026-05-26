"""Atomizer service — produces AtomV1 instances from source text via LLM.

Per dispatch hard constraints:
  - Gemini 2.5 Flash for the Dave pilot
  - Temperature = 0
  - Structured output (JSON schema-constrained)
  - REJECTS free-text triggers via the VALID_TRIGGER_KINDS whitelist
  - Feature flag: KEIRACOM_ATOMIZER_ENABLED=on (default off)

Caller injects an LLMClient (production = LiteLLMGeminiClient; tests = fake).
Caller also injects an AtomStore to persist the produced atoms + an embedder
(TEIClient) for computing content_embedding.

Job audit row written to keiracom_atomizer_jobs BEFORE and AFTER the LLM call
for idempotency (re-runs of the same source_ref produce a new job row).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID, uuid4

from src.keiracom_system.atomization.atom_store import AtomStore, AtomStoreError
from src.keiracom_system.atomization.llm_client import (
    ATOMIZER_TEMPERATURE,
    DEFAULT_ATOMIZER_MODEL,
    LLMClient,
    LLMClientError,
)
from src.keiracom_system.atomization.schema import (
    VALID_SOURCE_KINDS,
    VALID_TRIGGER_KINDS,
    AtomV1,
)

log = logging.getLogger(__name__)

# Feature flag — atomizer no-op until ops explicitly enables.
FEATURE_FLAG_ENV: str = "KEIRACOM_ATOMIZER_ENABLED"


def is_atomizer_enabled() -> bool:
    """Read the feature flag from env. Default OFF."""
    return os.environ.get(FEATURE_FLAG_ENV, "off").lower() == "on"


class AtomizerError(RuntimeError):
    """Raised on atomizer-side errors that should HALT the job."""


class _JobLogger(Protocol):
    """Subset of DB calls the atomizer needs for keiracom_atomizer_jobs."""

    def execute(self, query: str, *params: Any) -> Any: ...
    def fetchone(self) -> Any: ...


@dataclass(frozen=True, kw_only=True)
class AtomizerJob:
    """Audit row for one atomizer pass — mirrors keiracom_atomizer_jobs.

    Created BEFORE the LLM call (status=pending) so a crash leaves the row
    visible. Updated to atomizer_done after structured output + atom inserts.
    """

    job_id: UUID
    tenant_id: UUID
    source_ref: str
    source_kind: str
    atomizer_model: str
    atomizer_temp: float
    atomizer_tokens_in: int = 0
    atomizer_tokens_out: int = 0
    atomizer_latency_ms: int = 0
    atoms_produced: int = 0
    atom_ids: list[UUID] = field(default_factory=list)
    status: str = "pending"

    def __post_init__(self) -> None:
        if self.source_kind not in VALID_SOURCE_KINDS:
            raise AtomizerError(
                f"source_kind {self.source_kind!r} not in {sorted(VALID_SOURCE_KINDS)}"
            )


# JSON schema that the atomizer prompts Gemini Flash to return.
# Restricts trigger_condition.kind to the frozen vocabulary — Gemini's
# structured output guarantees the response will match (Gemini enforces
# enum constraints on its side, refusing to emit values outside the set).
ATOMS_RESPONSE_SCHEMA: dict[str, Any] = {
    "name": "AtomsResponse",
    "schema": {
        "type": "object",
        "required": ["atoms"],
        "properties": {
            "atoms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "trigger_condition",
                        "content",
                        "provenance",
                    ],
                    "properties": {
                        "trigger_condition": {
                            "type": "object",
                            "required": ["kind", "params"],
                            "properties": {
                                "kind": {
                                    "type": "string",
                                    "enum": sorted(VALID_TRIGGER_KINDS),
                                },
                                "params": {"type": "object"},
                            },
                        },
                        "content": {"type": "string"},
                        "anti_pattern": {"type": ["string", "null"]},
                        "example": {"type": ["string", "null"]},
                        "provenance": {
                            "type": "object",
                            "required": [
                                "source",
                                "freshness",
                                "confidence",
                                "last_validated",
                            ],
                            "properties": {
                                "source": {"type": "string"},
                                "freshness": {"type": "string"},
                                "confidence": {"type": "number"},
                                "last_validated": {"type": "string"},
                            },
                        },
                        "composition_tags": {"type": "object"},
                    },
                },
            },
        },
    },
}


_SYSTEM_PROMPT = (
    "You are an atomizer for a knowledge base. Convert the user-provided "
    "source text into a list of atoms following the atom_schema_v1 contract. "
    "RULES:\n"
    "1. Each atom MUST have a structured trigger_condition with a 'kind' from "
    f"the allowed set: {sorted(VALID_TRIGGER_KINDS)}. NEVER emit free-text "
    "in trigger_condition.\n"
    "2. content is a clear, self-contained statement of one piece of "
    "knowledge.\n"
    "3. anti_pattern (optional) names a common wrong approach.\n"
    "4. example (optional) is a brief concrete illustration.\n"
    "5. provenance MUST include source, freshness (ISO8601), confidence "
    "(float 0..1), last_validated (ISO8601).\n"
    "6. If the source text expresses multiple distinct pieces of knowledge, "
    "emit multiple atoms rather than one bloated atom.\n"
    "Return ONLY the JSON matching the response schema."
)


class Atomizer:
    """Produce AtomV1 instances + persist them via AtomStore.

    Owns the LLM call + job-row bookkeeping. Verifier is a separate component
    called on the produced atoms (see verifier.py).
    """

    def __init__(
        self,
        *,
        llm: LLMClient,
        store: AtomStore,
        job_db: _JobLogger,
        model: str = DEFAULT_ATOMIZER_MODEL,
        metric_emitter: Any = None,
    ):
        self._llm = llm
        self._store = store
        self._job_db = job_db
        self._model = model
        self._metric_emitter = metric_emitter

    def atomize(
        self,
        *,
        source_ref: str,
        source_kind: str,
        source_text: str,
    ) -> AtomizerJob:
        """Atomize a source document. Returns the job audit row.

        Caller checks is_atomizer_enabled() — this method does NOT — because
        we want test paths to drive the atomizer directly regardless of env.
        """
        if source_kind not in VALID_SOURCE_KINDS:
            raise AtomizerError(f"source_kind {source_kind!r} not in {sorted(VALID_SOURCE_KINDS)}")
        if not source_text:
            raise AtomizerError("source_text must be non-empty")

        job_id = uuid4()
        # Insert pending job row BEFORE the LLM call (idempotency + crash-visibility).
        self._job_db.execute(
            "INSERT INTO keiracom_atomizer_jobs ("
            "job_id, tenant_id, source_ref, source_kind, atomizer_model, "
            "atomizer_temp, status"
            ") VALUES (%s, %s, %s, %s, %s, %s, 'pending')",
            str(job_id),
            self._store.tenant_id,
            source_ref,
            source_kind,
            self._model,
            ATOMIZER_TEMPERATURE,
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": source_text},
        ]
        start = time.time()
        try:
            response = self._llm.call_structured(
                model=self._model,
                messages=messages,
                response_schema=ATOMS_RESPONSE_SCHEMA,
                temperature=ATOMIZER_TEMPERATURE,
            )
        except LLMClientError as exc:
            self._mark_failed(job_id, reason=str(exc))
            raise AtomizerError(f"LLM call failed for source_ref={source_ref!r}: {exc}") from exc
        latency_ms = int((time.time() - start) * 1000)

        atoms_payload = response.parsed.get("atoms") if isinstance(response.parsed, dict) else None
        if not isinstance(atoms_payload, list):
            self._mark_failed(job_id, reason="parsed.atoms is not a list")
            raise AtomizerError(
                f"atomizer returned non-list 'atoms' payload: {type(atoms_payload).__name__}"
            )

        atom_ids: list[UUID] = []
        for raw in atoms_payload:
            atom = self._build_atom_v1(raw)
            try:
                aid = self._store.insert_atom(atom)
            except AtomStoreError as exc:
                self._mark_failed(job_id, reason=f"insert_atom failed: {exc}")
                raise AtomizerError(
                    f"insert_atom failed for source_ref={source_ref!r}: {exc}"
                ) from exc
            atom_ids.append(aid)

        # Update job row to atomizer_done with metering.
        self._job_db.execute(
            "UPDATE keiracom_atomizer_jobs SET "
            "atomizer_tokens_in = %s, atomizer_tokens_out = %s, "
            "atomizer_latency_ms = %s, atoms_produced = %s, "
            "status = 'atomizer_done' "
            "WHERE job_id = %s",
            response.tokens_in,
            response.tokens_out,
            latency_ms,
            len(atom_ids),
            str(job_id),
        )

        # Emit metering metrics (no-op if emitter is None).
        if self._metric_emitter is not None:
            self._emit_metering(
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                latency_ms=latency_ms,
                atoms_produced=len(atom_ids),
                source_kind=source_kind,
            )

        return AtomizerJob(
            job_id=job_id,
            tenant_id=UUID(self._store.tenant_id),
            source_ref=source_ref,
            source_kind=source_kind,
            atomizer_model=self._model,
            atomizer_temp=ATOMIZER_TEMPERATURE,
            atomizer_tokens_in=response.tokens_in,
            atomizer_tokens_out=response.tokens_out,
            atomizer_latency_ms=latency_ms,
            atoms_produced=len(atom_ids),
            atom_ids=atom_ids,
            status="atomizer_done",
        )

    def _build_atom_v1(self, raw: dict[str, Any]) -> AtomV1:
        """Construct AtomV1 from one raw atom dict in the LLM response.

        Validation happens via AtomV1.__post_init__ — invalid atoms raise
        ValueError, which bubbles up as a job failure (no partial inserts).
        """
        return AtomV1(
            atom_id=uuid4(),
            tenant_id=UUID(self._store.tenant_id),
            trigger_condition=raw["trigger_condition"],
            content=raw["content"],
            anti_pattern=raw.get("anti_pattern"),
            example=raw.get("example"),
            provenance=raw["provenance"],
            composition_tags=raw.get("composition_tags") or {},
        )

    def _mark_failed(self, job_id: UUID, *, reason: str) -> None:
        """Best-effort mark a job as failed. Logged even if DB call errors."""
        try:
            self._job_db.execute(
                "UPDATE keiracom_atomizer_jobs SET status = 'failed' WHERE job_id = %s",
                str(job_id),
            )
        except Exception:  # noqa: BLE001
            log.exception("failed to mark job %s as failed", job_id)
        log.error("atomizer job %s failed: %s", job_id, reason)

    def _emit_metering(
        self,
        *,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        atoms_produced: int,
        source_kind: str,
    ) -> None:
        """Better Stack metrics per design §5 (atomization_pilot_schema_lock_proposal.md)."""
        common_tags = {
            "tenant_id": self._store.tenant_id,
            "model": self._model,
            "source_kind": source_kind,
        }
        self._metric_emitter(
            "keiracom.atomization.atomizer.tokens",
            dict(common_tags, type="in", count=str(tokens_in)),
        )
        self._metric_emitter(
            "keiracom.atomization.atomizer.tokens",
            dict(common_tags, type="out", count=str(tokens_out)),
        )
        self._metric_emitter(
            "keiracom.atomization.atomizer.latency_ms",
            dict(common_tags, value=str(latency_ms)),
        )
        self._metric_emitter(
            "keiracom.atomization.atoms_produced",
            dict(common_tags, count=str(atoms_produced)),
        )
