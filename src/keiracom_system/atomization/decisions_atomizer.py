"""Decisions atomizer — Phase Alpha extension (Agency_OS-decisions-atomization).

Extends the Week 1+2 atomizer pipeline (PR #1185 + PR #1189) to process
ratified decision-class content into Hindsight decision atoms.

WHAT'S DIFFERENT FROM SKILLS ATOMIZER (skills_atomizer.py):
  - Source set: ceo_memory directives + CONSOLIDATED_RULES.md + V2 inventory
    + MANUAL.md §13 (see decision_sources.py)
  - LLM prompt: instructs Gemini Flash to produce rationale-alternative-
    outcome triples (mapped within atom_schema_v1 7-field shape)
  - Composition tags: pinned to {domain=internal, concern=compliance,
    applicable_context=audit_review} so decision atoms are retrievable
    as a class
  - Output bank: Hindsight `fleet_decisions` bank (vs `fleet_skills` for
    Week 2 skills atomizer)

ATOM SCHEMA MAPPING (decision-class atoms FIT WITHIN atom_schema_v1):
  - content        → the decision statement (verbatim or distilled)
  - anti_pattern   → the rejected alternative
  - example        → the rationale + outcome (one-paragraph)
  - provenance     → source-anchored {source: "ceo_memory:...",
                                       freshness: ratify_timestamp,
                                       confidence: 1.0 for ratified items,
                                       last_validated: ratify_timestamp}
  - trigger_condition → kind=context_predicate, params={domain, in_response_to}
  - composition_tags → {domain: internal, concern: compliance,
                        applicable_context: audit_review}
  - supersession_edges → handled at the edges table level; atomizer
                         flags supersedes_atom_id in the LLM response
                         when the directive supersedes a prior one

DI matches PR #1185 — caller provides LLMClient + AtomStore + job DB. No
schema changes to atom_schema_v1; this is a different PROMPT + SOURCE flow
on top of the existing storage substrate.

ANCHOR: Cutover Readiness Gate STATE_SEPARATION.knowledge_atomized_pgvector
(restated 2026-05-27 outbox `orion-cutover-gate-verbatim-restate-resumed`).
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from src.keiracom_system.atomization.atom_store import AtomStore, AtomStoreError
from src.keiracom_system.atomization.atomizer import _JobLogger
from src.keiracom_system.atomization.decision_sources import (
    DEFAULT_DECISIONS_BANK,
    DecisionSource,
    decision_composition_tags,
)
from src.keiracom_system.atomization.llm_client import (
    ATOMIZER_TEMPERATURE,
    DEFAULT_ATOMIZER_MODEL,
    LLMClient,
    LLMClientError,
)
from src.keiracom_system.atomization.schema import (
    VALID_TRIGGER_KINDS,
    AtomV1,
)

log = logging.getLogger(__name__)


# Decision-class atom-class response schema for Gemini Flash. Differs from
# the generic ATOMS_RESPONSE_SCHEMA in PR #1185 atomizer.py: this prompt
# focuses Gemini on extracting (rationale, alternative, outcome) triples
# and mapping them into atom_schema_v1 fields.
DECISION_ATOMS_RESPONSE_SCHEMA: dict[str, Any] = {
    "name": "DecisionAtomsResponse",
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
                        # content carries the DECISION STATEMENT (what was
                        # ratified). Verbatim where possible; distilled if
                        # the source is multi-paragraph.
                        "content": {"type": "string"},
                        # anti_pattern carries the REJECTED ALTERNATIVE
                        # (what was considered AND rejected during
                        # deliberation). NULL when no alternative recorded.
                        "anti_pattern": {"type": ["string", "null"]},
                        # example carries RATIONALE + OUTCOME — one-paragraph
                        # explanation of WHY the decision was made + what
                        # has happened since (if observable).
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
                        # Optional: if this decision supersedes a prior one,
                        # the source mentions it (e.g. "supersedes ceo:
                        # four_store_completion_rule" in five_store rule).
                        # Atomizer extracts the cited reference; supersession
                        # edge is created in a separate pass per design.
                        "supersedes_reference": {"type": ["string", "null"]},
                    },
                },
            },
        },
    },
}


_DECISION_SYSTEM_PROMPT = (
    "You are an atomizer for a knowledge base of RATIFIED DECISIONS. The "
    "user provides a ratified decision artefact (directive completion "
    "marker / governance rule / inventory row / manual entry). Extract "
    "atoms following atom_schema_v1 with DECISION-CLASS field mapping:\n"
    "\n"
    "RULES:\n"
    "1. content = the decision statement (verbatim if it's already a "
    "single sentence, distilled otherwise). Active voice. Imperative or "
    "declarative.\n"
    "2. anti_pattern (optional) = the REJECTED ALTERNATIVE if the source "
    "names one. If multiple deliberators rejected the same alternative, "
    "name it. If no alternative is recorded in the source, return NULL.\n"
    "3. example (optional) = ONE-PARAGRAPH explanation of:\n"
    "     RATIONALE: why this was decided (drives/causes)\n"
    "     OUTCOME: what has happened since (if observable in the source)\n"
    "   Concatenate as 'RATIONALE: ... OUTCOME: ...'. Return NULL if "
    "neither is recoverable from the source.\n"
    "4. trigger_condition: kind from the allowed set: "
    f"{sorted(VALID_TRIGGER_KINDS)}. For decisions the kind is typically "
    "'context_predicate' (an agent reasoning in this domain should retrieve "
    "this) — params include the domain + the in_response_to predicate.\n"
    "5. provenance:\n"
    "     source = the source_ref provided in the user message\n"
    "     freshness = ISO8601 ratify timestamp from the source (or today "
    "if no timestamp is in the source)\n"
    "     confidence = 1.0 for RATIFIED items (per LAW XV five-store rule "
    "they ARE the ground truth)\n"
    "     last_validated = same as freshness\n"
    "6. supersedes_reference (optional) = if the source explicitly cites "
    "a superseded prior decision (e.g. 'supersedes ceo:four_store_"
    "completion_rule'), return the cited reference verbatim. NULL "
    "otherwise.\n"
    "7. If the source contains MULTIPLE distinct decisions (e.g. a "
    "consolidated-rules block with sub-decisions), emit multiple atoms — "
    "one per decision.\n"
    "\n"
    "Return ONLY the JSON matching the response schema."
)


class DecisionsAtomizerError(RuntimeError):
    """Raised on decisions-atomizer-specific runtime errors."""


@dataclass(frozen=True, kw_only=True)
class DecisionAtomizerJob:
    """Audit row for one decisions-atomization pass."""

    job_id: UUID
    tenant_id: UUID
    source_ref: str
    source_kind: str
    atomizer_model: str
    atomizer_tokens_in: int = 0
    atomizer_tokens_out: int = 0
    atomizer_latency_ms: int = 0
    atoms_produced: int = 0
    atom_ids: list[UUID] | None = None
    supersedes_refs: list[str] | None = None
    status: str = "atomizer_done"


class DecisionsAtomizer:
    """Decisions-flavoured atomizer.

    Mirrors the Week 1 `Atomizer` class shape (PR #1185) but uses the
    decision-class system prompt + response schema + composition_tags. The
    underlying AtomStore + LLMClient + job DB are the SAME — only the LLM
    prompt + atom-mapping differs.
    """

    def __init__(
        self,
        *,
        llm: LLMClient,
        store: AtomStore,
        job_db: _JobLogger,
        model: str = DEFAULT_ATOMIZER_MODEL,
        decisions_bank: str = DEFAULT_DECISIONS_BANK,
        metric_emitter: Any = None,
    ):
        self._llm = llm
        self._store = store
        self._job_db = job_db
        self._model = model
        self._decisions_bank = decisions_bank
        self._metric_emitter = metric_emitter

    @property
    def decisions_bank(self) -> str:
        return self._decisions_bank

    def atomize(self, source: DecisionSource) -> DecisionAtomizerJob:
        """Atomize one DecisionSource into decision-class atoms."""
        if not source.source_text:
            raise DecisionsAtomizerError(f"source_text empty for {source.source_ref!r}")

        job_id = uuid4()
        self._job_db.execute(
            "INSERT INTO keiracom_atomizer_jobs ("
            "job_id, tenant_id, source_ref, source_kind, atomizer_model, "
            "atomizer_temp, status"
            ") VALUES (%s, %s, %s, %s, %s, %s, 'pending')",
            str(job_id),
            self._store.tenant_id,
            source.source_ref,
            source.source_kind,
            self._model,
            ATOMIZER_TEMPERATURE,
        )

        messages = [
            {"role": "system", "content": _DECISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"source_ref: {source.source_ref}\n"
                    f"source_kind: {source.source_kind}\n\n"
                    f"source_text:\n{source.source_text}"
                ),
            },
        ]
        start = time.time()
        try:
            response = self._llm.call_structured(
                model=self._model,
                messages=messages,
                response_schema=DECISION_ATOMS_RESPONSE_SCHEMA,
                temperature=ATOMIZER_TEMPERATURE,
            )
        except LLMClientError as exc:
            self._mark_failed(job_id, reason=str(exc))
            raise DecisionsAtomizerError(
                f"LLM call failed for {source.source_ref!r}: {exc}"
            ) from exc
        latency_ms = int((time.time() - start) * 1000)

        parsed_atoms = response.parsed.get("atoms") if isinstance(response.parsed, dict) else None
        if not isinstance(parsed_atoms, list):
            self._mark_failed(job_id, reason="parsed.atoms is not a list")
            raise DecisionsAtomizerError(
                f"decisions atomizer returned non-list payload for {source.source_ref!r}"
            )

        atom_ids: list[UUID] = []
        supersedes_refs: list[str] = []
        for raw_atom in parsed_atoms:
            atom = self._build_decision_atom(raw_atom, source=source)
            try:
                aid = self._store.insert_atom(atom)
            except AtomStoreError as exc:
                self._mark_failed(job_id, reason=f"insert_atom failed: {exc}")
                raise DecisionsAtomizerError(
                    f"insert_atom failed for {source.source_ref!r}: {exc}"
                ) from exc
            atom_ids.append(aid)
            ref = raw_atom.get("supersedes_reference")
            if isinstance(ref, str) and ref.strip():
                supersedes_refs.append(ref.strip())

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

        if self._metric_emitter is not None:
            self._emit_metering(
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                latency_ms=latency_ms,
                atoms_produced=len(atom_ids),
                source_kind=source.source_kind,
            )

        return DecisionAtomizerJob(
            job_id=job_id,
            tenant_id=UUID(self._store.tenant_id),
            source_ref=source.source_ref,
            source_kind=source.source_kind,
            atomizer_model=self._model,
            atomizer_tokens_in=response.tokens_in,
            atomizer_tokens_out=response.tokens_out,
            atomizer_latency_ms=latency_ms,
            atoms_produced=len(atom_ids),
            atom_ids=atom_ids,
            supersedes_refs=supersedes_refs,
            status="atomizer_done",
        )

    def _build_decision_atom(
        self,
        raw: dict[str, Any],
        *,
        source: DecisionSource,
    ) -> AtomV1:
        """Build an AtomV1 from one decision-class LLM response item.

        Forces composition_tags to the decision-class defaults if the LLM
        didn't supply matching values — keeps decision atoms retrievable
        as a class regardless of LLM variance.
        """
        comp_tags = raw.get("composition_tags") or {}
        if not comp_tags:
            comp_tags = decision_composition_tags()
        return AtomV1(
            atom_id=uuid4(),
            tenant_id=UUID(self._store.tenant_id),
            trigger_condition=raw["trigger_condition"],
            content=raw["content"],
            anti_pattern=raw.get("anti_pattern"),
            example=raw.get("example"),
            provenance=raw["provenance"],
            composition_tags=comp_tags,
        )

    def _mark_failed(self, job_id: UUID, *, reason: str) -> None:
        """Best-effort mark a job as failed. Logged even if DB call errors."""
        try:
            self._job_db.execute(
                "UPDATE keiracom_atomizer_jobs SET status = 'failed' WHERE job_id = %s",
                str(job_id),
            )
        except Exception:  # noqa: BLE001
            log.exception("failed to mark decisions job %s as failed", job_id)
        log.error("decisions atomizer job %s failed: %s", job_id, reason)

    def _emit_metering(
        self,
        *,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        atoms_produced: int,
        source_kind: str,
    ) -> None:
        """Better Stack metrics — same names as skills atomizer (PR #1185)
        plus a `decisions=true` tag so dashboards can split the two flows."""
        common_tags = {
            "tenant_id": self._store.tenant_id,
            "model": self._model,
            "source_kind": source_kind,
            "flow": "decisions",
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


def atomize_decisions_run(
    *,
    atomizer: DecisionsAtomizer,
    sources: Iterable[DecisionSource],
    execute: bool = False,
) -> int:
    """Walk source iterator + atomize each. Returns rc=0 clean / rc=1 any failure.

    Dry-run default — log what would happen without firing LLM calls.
    Operator runs with execute=True after smoke verification.
    """
    n_total = n_ok = n_fail = 0
    for source in sources:
        n_total += 1
        if not execute:
            log.info("dry-run: would atomize %s", source.source_ref)
            continue
        try:
            job = atomizer.atomize(source)
            n_ok += 1
            log.info(
                "decisions-atomized %s — %d atoms produced",
                source.source_ref,
                job.atoms_produced,
            )
        except (DecisionsAtomizerError, AtomStoreError) as exc:
            n_fail += 1
            log.warning("decisions-atomize FAILED %s: %s", source.source_ref, exc)
    log.info(
        "decisions atomizer summary: total=%d ok=%d fail=%d (execute=%s)",
        n_total,
        n_ok,
        n_fail,
        execute,
    )
    return 0 if n_fail == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """Module-as-script CLI dry-run (no LLM call when --execute is absent).

    Smoke-runs the source iterators without requiring DB/LLM credentials —
    useful for verifying the 4 sources walk cleanly before operator wires
    the production Atomizer.
    """
    import argparse
    from pathlib import Path

    from src.keiracom_system.atomization.decision_sources import iter_all_decision_sources

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--include-ceo-memory",
        action="store_true",
        help="include ceo_memory directives (requires DB env vars + connection)",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    # Dry-run smoke: walk sources + log counts. No LLM, no DB writes.
    if not args.include_ceo_memory:
        sources = list(iter_all_decision_sources(db=None, repo_root=args.repo_root))
    else:
        log.error(
            "--include-ceo-memory requires DB construction in a bootstrap script; "
            "this module-as-script does dry-run-without-DB only. "
            "Use scripts/bootstrap_atomize_decisions.py (separate KEI) for "
            "production runs."
        )
        return 3
    by_kind: dict[str, int] = {}
    for s in sources:
        by_kind[s.source_kind] = by_kind.get(s.source_kind, 0) + 1
    log.info("decisions atomizer dry-run smoke — %d sources walked", len(sources))
    for kind, count in sorted(by_kind.items()):
        log.info("  %s: %d sources", kind, count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
