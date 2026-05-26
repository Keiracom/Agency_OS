"""Composer — Week 2 atomization pilot.

Renders retrieved atoms into human-facing output for endpoints. Per
ceo:atomization_architecture_v1 component layer #4. The CRITICAL HARD
CONSTRAINT: "Composer output never reaches agent reasoning input."

This means: Composer's `compose_chat_reply()` output goes to the USER
(rendered into a chat message, email, etc.). It does NOT get fed back into
an agent's prompt. Architecturally separate from MalRetriever (which IS
the agent-reasoning input path).

Why the separation matters: Composer is non-deterministic by design (LLM-
shaped prose; future variant: tier-aware formatting). If Composer output
fed agent reasoning, multi-agent reasoning chains would break on the
non-determinism. The hard constraint prevents that class of failure.

Week 2 scope: chat-reply endpoint ONLY. Other endpoints (email, voice,
SMS) are Week 2-3 dispatch via Endpoint Translator (separate module).

DI: caller passes a list of RetrievalResult (from MalRetriever) + endpoint
name. No LLM call required at this layer — atoms carry pre-validated
content; Composer's job is rendering not generation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.keiracom_system.atomization.retriever import RetrievalResult

log = logging.getLogger(__name__)

# Supported endpoint kinds for Week 2 (chat-reply only). Week 2-3 expansion
# adds email + voice + sms via Endpoint Translator dispatch.
VALID_ENDPOINTS: frozenset[str] = frozenset({"chat_reply"})

# Max atoms to include in a single composed response. Bounded so a high
# top_k retrieve doesn't produce a verbose chat reply.
DEFAULT_MAX_ATOMS_IN_RESPONSE: int = 5

# Score floor for inclusion in composed output. Lower scores indicate weaker
# matches; surfacing them in user-facing prose is a noise risk.
DEFAULT_MIN_SCORE_FOR_INCLUSION: float = 0.1


class ComposerError(RuntimeError):
    """Raised on invalid composer input."""


@dataclass(frozen=True, kw_only=True)
class ComposedOutput:
    """The rendered output + provenance trail.

    `text` is the user-facing string. `atoms_used` lists the AtomV1 atom_ids
    that contributed — useful for downstream audit + the cite-back UX.
    """

    text: str
    endpoint: str
    atoms_used: list[str]
    truncated_count: int = 0


class Composer:
    """Render atoms to user-facing output.

    Endpoint-only. Output does NOT enter agent reasoning input
    (per atomization_architecture_v1 hard constraint).
    """

    def __init__(
        self,
        *,
        max_atoms: int = DEFAULT_MAX_ATOMS_IN_RESPONSE,
        min_score: float = DEFAULT_MIN_SCORE_FOR_INCLUSION,
    ):
        if max_atoms <= 0:
            raise ComposerError("max_atoms must be > 0")
        self._max_atoms = max_atoms
        self._min_score = min_score

    def compose_chat_reply(
        self,
        *,
        atoms: list[RetrievalResult],
        query_text: str | None = None,
    ) -> ComposedOutput:
        """Render retrieved atoms into a chat-reply string.

        Format: a short prose preamble citing the query (if provided), then a
        numbered list of atom contents with the anti-pattern note (if any),
        then an example (if any).
        """
        return self.compose(atoms=atoms, endpoint="chat_reply", query_text=query_text)

    def compose(
        self,
        *,
        atoms: list[RetrievalResult],
        endpoint: str,
        query_text: str | None = None,
    ) -> ComposedOutput:
        """Generic compose for any supported endpoint.

        Week 2 supports `endpoint="chat_reply"` only. Other endpoints raise
        ComposerError until the Endpoint Translator dispatch lands (Week 2-3).
        """
        if endpoint not in VALID_ENDPOINTS:
            raise ComposerError(
                f"endpoint {endpoint!r} not in {sorted(VALID_ENDPOINTS)} — "
                "additional endpoints land via Endpoint Translator dispatch"
            )

        # Filter by min_score + take top max_atoms
        relevant = [r for r in atoms if r.score >= self._min_score]
        truncated = max(0, len(relevant) - self._max_atoms)
        relevant = relevant[: self._max_atoms]

        if not relevant:
            text = self._render_empty(query_text)
            return ComposedOutput(
                text=text,
                endpoint=endpoint,
                atoms_used=[],
                truncated_count=0,
            )

        if endpoint == "chat_reply":
            text = self._render_chat_reply(relevant, query_text=query_text)
        else:
            # Defensive — should be unreachable given VALID_ENDPOINTS gate.
            raise ComposerError(f"endpoint {endpoint!r} unhandled")

        return ComposedOutput(
            text=text,
            endpoint=endpoint,
            atoms_used=[str(r.atom.atom_id) for r in relevant],
            truncated_count=truncated,
        )

    def _render_empty(self, query_text: str | None) -> str:
        """No atoms above threshold — return a non-hallucinating placeholder.

        Per anti-hallucination discipline: if we have no high-confidence atoms,
        the response acknowledges that rather than fabricating content. Caller
        (the endpoint) can treat empty atoms_used as a signal to ask a
        clarifying question OR escalate to a human.
        """
        if query_text:
            return (
                f"I don't have high-confidence knowledge matching {query_text!r}. "
                "Could you rephrase or provide more context?"
            )
        return "I don't have high-confidence knowledge for that query."

    def _render_chat_reply(
        self,
        relevant: list[RetrievalResult],
        *,
        query_text: str | None,
    ) -> str:
        """Render atoms as a numbered chat reply.

        Format keeps it minimal: numbered list, one atom per item, with
        anti_pattern called out + example shown when present.
        """
        lines: list[str] = []
        if query_text and len(relevant) > 1:
            lines.append(f"Based on what I know about {query_text!r}:")
            lines.append("")

        for idx, result in enumerate(relevant, start=1):
            atom = result.atom
            if len(relevant) > 1:
                lines.append(f"{idx}. {atom.content}")
            else:
                lines.append(atom.content)
            if atom.anti_pattern:
                lines.append(f"   (Avoid: {atom.anti_pattern})")
            if atom.example:
                example_first_line = atom.example.split("\n", 1)[0]
                lines.append(f"   Example: {example_first_line}")
            if idx < len(relevant):
                lines.append("")

        return "\n".join(lines)


def select_provenance_trail(output: ComposedOutput) -> dict[str, Any]:
    """Build a JSON-serializable provenance dict for audit logging.

    Composer output IS persisted (audit log) even though it doesn't enter
    agent reasoning. The atoms_used list lets reviewers cross-check that
    the user-facing prose was actually grounded in stored atoms vs invented.
    """
    return {
        "endpoint": output.endpoint,
        "atoms_used": output.atoms_used,
        "truncated_count": output.truncated_count,
        "text_length_chars": len(output.text),
    }
