"""Verifier service — second pass over atomizer output using Gemini Pro.

Per dispatch failure-mode mitigation: "Legacy free-text trigger interpretation
= Pro verifier spot-checks a sample". Verifier runs AFTER atomizer in a
separate pass, flags issues, and updates the job row with verifier_flags.

Flags are non-blocking by design — grain violation = degrade-with-flag plus
human review queue (per dispatch hard constraint), NOT a hard reject. This
matches the failure-mode mitigation: "Grain violation = degrade-with-flag
plus human review queue".

Verifier checks per atom:
  1. Factual coherence — content + example + anti_pattern internally consistent
  2. Trigger condition specificity — kind + params concrete enough to actually fire
  3. Provenance plausibility — freshness/last_validated dates reasonable; confidence in [0,1]
  4. Composition tags consistency — tags align with content domain

Caller passes the AtomizerJob from a prior atomizer.atomize() call.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.keiracom_system.atomization.atom_store import AtomStore
from src.keiracom_system.atomization.atomizer import _JobLogger
from src.keiracom_system.atomization.llm_client import (
    DEFAULT_VERIFIER_MODEL,
    LLMClient,
    LLMClientError,
)
from src.keiracom_system.atomization.schema import AtomV1

log = logging.getLogger(__name__)


class VerifierError(RuntimeError):
    """Raised on verifier-side errors that should HALT the verification pass.

    Per-atom flags are NOT errors — they're returned as VerifierFlag entries.
    """


# Severity scale — caller / human reviewer routes on this.
SEVERITY_INFO: str = "info"
SEVERITY_WARNING: str = "warning"
SEVERITY_BLOCKING: str = "blocking"

VALID_SEVERITIES: frozenset[str] = frozenset({SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_BLOCKING})


@dataclass(frozen=True, kw_only=True)
class VerifierFlag:
    """One verifier flag on one atom. Persisted in keiracom_atomizer_jobs.verifier_flags."""

    atom_id: UUID
    severity: str
    message: str

    def __post_init__(self) -> None:
        if self.severity not in VALID_SEVERITIES:
            raise VerifierError(f"severity {self.severity!r} not in {sorted(VALID_SEVERITIES)}")


_VERIFIER_SYSTEM_PROMPT = (
    "You are a verifier for atom_schema_v1 knowledge-base atoms. "
    "Given a JSON array of atoms produced by an upstream atomizer, return a "
    "JSON array of flags. Each flag names one issue with one atom.\n"
    "FLAG CATEGORIES:\n"
    "1. factual_incoherence — content + example + anti_pattern do not match\n"
    "2. trigger_unspecific — trigger_condition.params too vague to actually fire\n"
    "3. provenance_implausible — freshness/last_validated dates wrong OR "
    "confidence outside reasonable range\n"
    "4. tag_mismatch — composition_tags don't fit content domain\n"
    "5. grain_violation — atom too coarse (mixes multiple knowledge units) OR "
    "too fine (fragment without context)\n"
    "SEVERITY: 'info' (FYI), 'warning' (human review), 'blocking' (do not use).\n"
    "If an atom is fine, do NOT emit a flag for it. Return [] for clean batches.\n"
    "Return ONLY the JSON matching the response schema."
)


VERIFIER_RESPONSE_SCHEMA: dict[str, Any] = {
    "name": "VerifierFlagsResponse",
    "schema": {
        "type": "object",
        "required": ["flags"],
        "properties": {
            "flags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["atom_index", "category", "severity", "message"],
                    "properties": {
                        "atom_index": {"type": "integer"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "factual_incoherence",
                                "trigger_unspecific",
                                "provenance_implausible",
                                "tag_mismatch",
                                "grain_violation",
                            ],
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["info", "warning", "blocking"],
                        },
                        "message": {"type": "string"},
                    },
                },
            },
        },
    },
}


class Verifier:
    """Run Pro-tier verifier pass on a batch of atoms; update the job row.

    Caller passes the atom_ids the atomizer produced. Verifier fetches them
    from the AtomStore (re-confirming tenant ownership at the boundary), sends
    them to Gemini Pro, and writes the flag list back to keiracom_atomizer_jobs.
    """

    def __init__(
        self,
        *,
        llm: LLMClient,
        store: AtomStore,
        job_db: _JobLogger,
        model: str = DEFAULT_VERIFIER_MODEL,
        metric_emitter: Any = None,
    ):
        self._llm = llm
        self._store = store
        self._job_db = job_db
        self._model = model
        self._metric_emitter = metric_emitter

    def verify(self, *, job_id: UUID, atom_ids: list[UUID]) -> list[VerifierFlag]:
        """Run verifier on the atoms produced by an atomizer job.

        Returns the list of flags. Empty list = clean batch.

        Atoms not found (e.g. wrong tenant) are silently skipped — the
        AtomStore tenant guard already collapses cross-tenant misses.
        """
        if not atom_ids:
            self._mark_verifier_done(job_id, flags=[])
            return []

        atoms: list[AtomV1] = []
        for aid in atom_ids:
            atom = self._store.get_atom(aid)
            if atom is not None:
                atoms.append(atom)
        if not atoms:
            self._mark_verifier_done(job_id, flags=[])
            return []

        atom_dicts = [
            {
                "trigger_condition": a.trigger_condition,
                "content": a.content,
                "anti_pattern": a.anti_pattern,
                "example": a.example,
                "provenance": a.provenance,
                "composition_tags": a.composition_tags,
            }
            for a in atoms
        ]

        import json as _json

        messages = [
            {"role": "system", "content": _VERIFIER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _json.dumps({"atoms": atom_dicts}),
            },
        ]
        start = time.time()
        try:
            response = self._llm.call_structured(
                model=self._model,
                messages=messages,
                response_schema=VERIFIER_RESPONSE_SCHEMA,
                temperature=0.0,
            )
        except LLMClientError as exc:
            log.exception("verifier LLM call failed for job %s", job_id)
            raise VerifierError(f"verifier LLM call failed: {exc}") from exc
        latency_ms = int((time.time() - start) * 1000)

        raw_flags = response.parsed.get("flags") if isinstance(response.parsed, dict) else None
        if not isinstance(raw_flags, list):
            raw_flags = []

        flags: list[VerifierFlag] = []
        for rf in raw_flags:
            try:
                idx = int(rf["atom_index"])
                if not 0 <= idx < len(atoms):
                    continue
                flags.append(
                    VerifierFlag(
                        atom_id=atoms[idx].atom_id,
                        severity=rf.get("severity", SEVERITY_WARNING),
                        message=f"{rf.get('category', 'unknown')}: {rf.get('message', '')}",
                    )
                )
            except (KeyError, ValueError, VerifierError) as exc:
                log.warning("verifier flag parse failed: %s; raw=%s", exc, rf)
                continue

        # Persist flags + verifier metering.
        self._mark_verifier_done(
            job_id,
            flags=flags,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            latency_ms=latency_ms,
        )

        if self._metric_emitter is not None:
            for flag in flags:
                self._metric_emitter(
                    "keiracom.atomization.verifier.flags",
                    {
                        "tenant_id": self._store.tenant_id,
                        "severity": flag.severity,
                    },
                )

        return flags

    def _mark_verifier_done(
        self,
        job_id: UUID,
        *,
        flags: list[VerifierFlag],
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int = 0,
    ) -> None:
        """UPDATE the job row with verifier metering + flags JSONB."""
        import json as _json

        flag_jsonb = _json.dumps(
            [
                {
                    "atom_id": str(f.atom_id),
                    "severity": f.severity,
                    "message": f.message,
                }
                for f in flags
            ]
        )
        self._job_db.execute(
            "UPDATE keiracom_atomizer_jobs SET "
            "verifier_model = %s, verifier_tokens_in = %s, "
            "verifier_tokens_out = %s, verifier_latency_ms = %s, "
            "verifier_flags = %s, status = 'verifier_done' "
            "WHERE job_id = %s",
            self._model,
            tokens_in,
            tokens_out,
            latency_ms,
            flag_jsonb,
            str(job_id),
        )
