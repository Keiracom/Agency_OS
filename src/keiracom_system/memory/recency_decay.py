"""recency_decay.py — exponential recency decay on retrieval scores.

Wave 2 CUTOVER GATE (Dave ratify 2026-05-27, Agency_OS-3rpe): older memories
must lose to newer at equal similarity unless they carry a canonical tag
(ratified ceo_memory keys, governance-locked architecture facts, etc.).
Pure math + small policy layer; no external clients.

Canonical key citations (per audit-dispatch checklist `_orchestrator.md`):

ceo:cutover_plan_v1 — full_retrieval_tier_ratify_2026_05_27_22Z.waves.wave_2_retrieval_core:
    "hybrid search + cross-encoder reranker + recency decay"

ceo:memory_abstraction_layer_v1 — substantive_lock:
    "mem.topology_tier_keyed" (per-topology half-life)

DESIGN — `apply_recency_decay(score, age_seconds, half_life_seconds)` is the
pure scalar. `decay_scored_memories(memories, *, config, now=...)` applies
the policy: per-topology half-life lookup + canonical-tag bypass + optional
floor so decay doesn't collapse a high-similarity old memory below the
noise threshold.

Half-life table is config-injected, not hardcoded here — different deploys
tune differently. The DEFAULT_HALF_LIVES dict below is the V1 baseline
Dave-ratified topology->half-life mapping; production wiring may override
per-tenant.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger(__name__)


SECONDS_PER_DAY = 86400
LN_2 = math.log(2.0)


# V1 baseline half-lives per topology (in days). Source: Dave ratify
# 2026-05-27 (ceo:cutover_plan_v1 wave_2_retrieval_core) — values chosen so
# fast-moving banks (KEI tracker, agent memories) decay quickly and
# slow-moving banks (codebase, decisions) decay slowly. Tuning is empirical
# Phase 2 work; these are starting points, not final.
DEFAULT_HALF_LIVES: dict[str, float] = {
    "fleet_keis": 7.0,
    "fleet_agent_memories": 7.0,
    "fleet_tool_calls": 3.0,
    "fleet_session_transcripts": 3.0,
    "fleet_discoveries": 14.0,
    "fleet_decisions": 30.0,
    "fleet_global_governance_patterns": 60.0,
    "fleet_strategic_documents": 90.0,
    "fleet_codebase": 90.0,
    "fleet_sessions": 14.0,
}

# Tags that EXEMPT a memory from decay. Ratified ceo_memory keys + canonical
# architecture facts must always surface — recency must not bury "Hindsight
# was chosen as MAL engine 2026-05-24" under last week's tool-call chatter.
DEFAULT_EXEMPT_TAGS: frozenset[str] = frozenset(
    {"canonical", "ceo_ratified", "ratified", "governance_locked"}
)


@dataclass(frozen=True)
class RecencyDecayConfig:
    """Per-deploy recency-decay policy.

    `half_lives` maps topology key -> half-life in days. Unknown topology
    falls back to `default_half_life_days` (None = no decay applied).
    `exempt_tags` short-circuits decay when any of these tags are present
    on the memory.
    `score_floor` clamps the decayed score from below so high-similarity
    old memories don't collapse to zero (e.g. a 4-year-old decision with
    similarity 0.95 still beats a 1-hour-old chatter with 0.10).
    """

    half_lives: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_HALF_LIVES))
    default_half_life_days: float | None = 30.0
    exempt_tags: frozenset[str] = DEFAULT_EXEMPT_TAGS
    score_floor: float = 0.0


@dataclass(frozen=True)
class ScoredMemory:
    """Scored retrieval candidate.

    `original_score` preserves the pre-decay similarity so callers can
    inspect the delta (e.g. observability + explain-this-rank UX).
    """

    memory_id: str
    score: float
    original_score: float
    age_seconds: float
    topology: str
    decay_applied: bool
    exempt_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def apply_recency_decay(score: float, age_seconds: float, half_life_seconds: float) -> float:
    """Pure exponential decay: score * 2^(-age / half_life).

    Equivalent to `score * exp(-ln(2) * age / half_life)`. Half-life is the
    age at which a score halves; the curve is monotonically decreasing in age.
    """
    if half_life_seconds <= 0:
        raise ValueError(f"half_life_seconds must be positive, got {half_life_seconds!r}")
    if age_seconds < 0:
        # A negative age (future-dated atom) is a clock-skew signal — log
        # but do not penalise; treat as age=0.
        log.warning("apply_recency_decay called with negative age_seconds=%s", age_seconds)
        age_seconds = 0
    factor = math.exp(-LN_2 * age_seconds / half_life_seconds)
    return score * factor


def _resolve_half_life_seconds(topology: str, config: RecencyDecayConfig) -> float | None:
    """Look up the half-life for a topology, falling back to default."""
    days = config.half_lives.get(topology)
    if days is None:
        days = config.default_half_life_days
    if days is None:
        return None
    if days <= 0:
        raise ValueError(f"half-life for topology {topology!r} must be positive days, got {days}")
    return days * SECONDS_PER_DAY


def _exempt_reason(tags: list[str], exempt_tags: frozenset[str]) -> str:
    """Return the matching exempt tag if any, empty string otherwise."""
    for t in tags:
        if t in exempt_tags:
            return t
    return ""


def _parse_atom_timestamp(value: Any) -> float | None:
    """Best-effort parse of a memory's created_at into an epoch seconds float.

    Accepts int/float (epoch), or ISO-8601 strings. Returns None on parse
    failure — caller decides whether to skip decay (treat as fresh) or fail
    loud.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # ISO-8601 with optional Z. fromisoformat in 3.11+ handles 'Z'; below
        # that, normalise.
        s = value.rstrip("Z")
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.timestamp()
        except ValueError:
            return None
    return None


def decay_scored_memories(
    memories: list[dict[str, Any]],
    *,
    config: RecencyDecayConfig,
    now: float | None = None,
) -> list[ScoredMemory]:
    """Apply the recency-decay policy to a list of scored memories.

    Each memory dict must carry:
      - `id` / `memory_id` — identifier
      - `score` — pre-decay similarity (0.0–1.0)
      - `created_at` / `timestamp` — atom age signal (epoch seconds or ISO-8601)
      - `topology` / `bank` — topology key for half-life lookup
      - `tags` — list[str] used for exempt-tag matching

    Missing fields fail loud (ValueError) — silent fallback to "no decay"
    would mask wiring bugs at the call site. The caller is expected to
    canonicalise the upstream payload before passing in.
    """
    if now is None:
        now = time.time()
    out: list[ScoredMemory] = []
    for raw in memories:
        if not isinstance(raw, dict):
            raise ValueError(f"memory entry must be dict, got {type(raw).__name__}")
        mid = str(raw.get("id") or raw.get("memory_id") or "")
        if not mid:
            raise ValueError("memory entry missing id / memory_id")
        score = raw.get("score")
        if score is None:
            raise ValueError(f"memory {mid!r} missing score")
        topology = str(raw.get("topology") or raw.get("bank") or "")
        if not topology:
            raise ValueError(f"memory {mid!r} missing topology / bank")
        tags_raw = raw.get("tags") or []
        if isinstance(tags_raw, str):
            tags = [tags_raw]
        elif isinstance(tags_raw, (list, tuple, set)):
            tags = [str(t) for t in tags_raw]
        else:
            raise ValueError(f"memory {mid!r} tags must be list/tuple/set/str")
        exempt = _exempt_reason(tags, config.exempt_tags)
        created_at_raw = raw.get("created_at") or raw.get("timestamp")
        atom_epoch = _parse_atom_timestamp(created_at_raw)
        age_seconds = max(now - atom_epoch, 0.0) if atom_epoch is not None else 0.0
        original_score = float(score)
        if exempt:
            out.append(
                ScoredMemory(
                    memory_id=mid,
                    score=original_score,
                    original_score=original_score,
                    age_seconds=age_seconds,
                    topology=topology,
                    decay_applied=False,
                    exempt_reason=exempt,
                    metadata=dict(raw.get("metadata") or {}),
                )
            )
            continue
        half_life_seconds = _resolve_half_life_seconds(topology, config)
        if half_life_seconds is None or atom_epoch is None:
            # No half-life configured OR no atom timestamp — pass through
            # without decay. This is a legitimate config choice (e.g. a
            # topology that's intentionally not aged); flag in the result
            # so observability can detect a wiring oversight.
            out.append(
                ScoredMemory(
                    memory_id=mid,
                    score=original_score,
                    original_score=original_score,
                    age_seconds=age_seconds,
                    topology=topology,
                    decay_applied=False,
                    exempt_reason="no_half_life" if half_life_seconds is None else "no_timestamp",
                    metadata=dict(raw.get("metadata") or {}),
                )
            )
            continue
        decayed = apply_recency_decay(original_score, age_seconds, half_life_seconds)
        if decayed < config.score_floor:
            decayed = config.score_floor
        out.append(
            ScoredMemory(
                memory_id=mid,
                score=decayed,
                original_score=original_score,
                age_seconds=age_seconds,
                topology=topology,
                decay_applied=True,
                metadata=dict(raw.get("metadata") or {}),
            )
        )
    return out


def rerank_by_decayed_score(memories: list[ScoredMemory]) -> list[ScoredMemory]:
    """Sort scored memories by decayed score descending. Stable sort
    preserves original relative order on ties."""
    return sorted(memories, key=lambda m: m.score, reverse=True)
