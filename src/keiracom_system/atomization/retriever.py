"""MAL Retriever — Week 2 atomization pilot.

Wraps AtomStore.retrieve_top_k with composition-tag filtering + relevance
scoring threshold. Per ceo:atomization_architecture_v1 component layer #3,
this is what agents call at reasoning time to recall atoms for context.

NOT the same as Composer (component layer #4) — that one renders atoms for
USER-FACING output. Retriever feeds atoms to AGENT REASONING input. The
hard-constraint "Composer output never reaches agent reasoning input" does
NOT apply here: Retriever IS the agent's reasoning-input path by design.

DI: caller passes an `AtomStore` already bound to the right tenant. Retriever
inherits the store's tenant isolation guarantee — no separate guard needed
at this layer.

Composition tag filtering: caller passes a dict of {domain, concern,
applicable_context} (any subset); retrieve narrows the AtomStore.retrieve_top_k
result to atoms matching ALL specified axes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.keiracom_system.atomization.atom_store import AtomStore
from src.keiracom_system.atomization.schema import AtomV1

log = logging.getLogger(__name__)

# Default similarity score threshold below which atoms are excluded. The
# cosine-similarity score from pgvector is 1 - cosine_distance, so higher is
# better; values <0 mean the embedding model returned a negative similarity
# (unusual for BGE-small but defensible to bound). 0.0 = no threshold.
DEFAULT_SCORE_THRESHOLD: float = 0.0

# Maximum top_k a caller can request. Bounds the cost of a single retrieve.
MAX_TOP_K: int = 50


class RetrieverError(RuntimeError):
    """Raised on invalid retriever input."""


@dataclass(frozen=True, kw_only=True)
class RetrievalResult:
    """One retrieved atom + its retrieval-time score.

    Score is the cosine similarity from pgvector. AtomV1 itself does not
    carry the score (atoms are immutable values; score is retrieval-context).
    """

    atom: AtomV1
    score: float


class MalRetriever:
    """Recall top-K atoms for a query, with optional composition-tag filtering."""

    def __init__(self, *, store: AtomStore):
        self._store = store

    @property
    def tenant_id(self) -> str:
        return self._store.tenant_id

    def retrieve(
        self,
        *,
        query_text: str,
        top_k: int = 10,
        composition_filter: dict[str, Any] | None = None,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    ) -> list[RetrievalResult]:
        """Recall atoms matching the query.

        Args:
            query_text: natural-language search query (embedded via TEIClient
                inside AtomStore).
            top_k: max atoms to return. Bounded by MAX_TOP_K.
            composition_filter: optional dict subset of {domain, concern,
                applicable_context}; atoms must match ALL specified axes to
                be included. Empty dict / None = no filter.
            score_threshold: minimum cosine-similarity score to include.

        Returns:
            List of RetrievalResult ordered by descending score. May be empty
            (no matches, no atoms in store, all below threshold, or all
            filtered out by composition_filter).
        """
        if not query_text:
            raise RetrieverError("query_text must be non-empty")
        if top_k <= 0:
            raise RetrieverError("top_k must be > 0")
        if top_k > MAX_TOP_K:
            raise RetrieverError(f"top_k {top_k} exceeds MAX_TOP_K {MAX_TOP_K}")

        # AtomStore.retrieve_top_k already filters to tenant_id + state=active
        # + cold_archive excluded. AtomStore does NOT currently return scores
        # — Week 2 enhancement: assume atoms come back ordered by similarity
        # and assign a placeholder score = 1.0 / (rank + 1) for now. Real
        # cosine-similarity score wire-up is a Week 2.5 follow-up that needs
        # AtomStore.retrieve_top_k to project the similarity column.
        atoms = self._store.retrieve_top_k(query_text, top_k=top_k)
        results: list[RetrievalResult] = []
        for rank, atom in enumerate(atoms):
            score = 1.0 / (rank + 1)  # placeholder rank-based score
            if score < score_threshold:
                continue
            if composition_filter and not _matches_composition_filter(
                atom.composition_tags, composition_filter
            ):
                continue
            results.append(RetrievalResult(atom=atom, score=score))
        return results

    def retrieve_with_min_score(
        self,
        *,
        query_text: str,
        top_k: int = 10,
        min_score: float,
    ) -> list[RetrievalResult]:
        """Convenience wrapper: retrieve(score_threshold=min_score)."""
        return self.retrieve(query_text=query_text, top_k=top_k, score_threshold=min_score)


def _matches_composition_filter(
    atom_tags: dict[str, Any],
    composition_filter: dict[str, Any],
) -> bool:
    """True iff the atom's composition_tags match ALL specified axes in the filter.

    Axes not in the filter are not constrained (i.e. {"domain": "sales"}
    matches any atom with domain=sales regardless of concern/context).
    """
    for axis, required_value in composition_filter.items():
        if atom_tags.get(axis) != required_value:
            return False
    return True
