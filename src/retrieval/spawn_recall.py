"""FILE: src/retrieval/spawn_recall.py
PURPOSE: Wave 3 — spawn-time recall lifecycle hook.

Before an ephemeral agent acts, query Hindsight for prior context about
tasks like this one — what has failed before, the canonical approach, and
any superseded decisions — and surface the top-3 results as a
'Prior context from memory' block injected into the spawn's environment.

Contract:
  * query_for_spawn(task_type, task_brief) -> list[str]
        Structured recall. Returns up to TOP_K excerpt strings; [] on any
        error or empty corpus.
  * build_prior_context_block(results) -> str
        Formats results into the injectable block ("" when no results).
  * inject_prior_context(spawn_kwargs, *, task_type, task_brief) -> dict
        Returns a copy of spawn_kwargs with the block placed in
        env[PRIOR_CONTEXT_ENV_KEY]; spawn_kwargs unchanged when nothing to
        inject.

Wave 6 — negative-example recall (RETRIEVAL_FAILURE_RECALL_ENABLED, default
off): build_spawn_context_block() appends a separate 'Past failures to avoid'
block (query_failures_for_spawn -> build_failure_context_block) below the
positive block. Byte-identical to the positive-only block when the flag is off.

Fail-open by contract: Hindsight unreachable / any error → no block, the
spawn proceeds without recall (never blocks). Budget-capped at the KEI-55
500-token ceiling (enforced by agent_query.query() max_tokens + a hard
char clamp here).

Out of scope (separate PRs): the cross-encoder reranker wiring, and the
session-launch wrapper that reads PRIOR_CONTEXT_ENV_KEY and forwards it to
the agent CLI via --append-system-prompt.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SPAWN_RECALL_AGENT = "spawn-recall"  # agent label recorded in retrieval_events
TOP_K = 3
MAX_TOKENS = 500  # KEI-55 ceiling
MAX_BLOCK_CHARS = MAX_TOKENS * 4  # ~4 chars/token belt-and-suspenders clamp
BRIEF_PREFIX_CHARS = 100
PRIOR_CONTEXT_ENV_KEY = "AGENCY_OS_PRIOR_CONTEXT"
BLOCK_HEADER = "Prior context from memory (auto-recall — what failed before, canonical approach, superseded decisions):"
FAILURE_BLOCK_HEADER = (
    "Past failures to avoid (auto-recall — documented failure cases for tasks like this):"
)


def _build_query(task_type: str, task_brief: str) -> str:
    """Structured recall query from task_type + the first 100 chars of brief."""
    brief_head = (task_brief or "").strip()[:BRIEF_PREFIX_CHARS]
    return (
        f'For a {task_type or "build"} task: "{brief_head}" — what has failed '
        "in tasks like this before, what is the canonical approach, and which "
        "decisions have been superseded?"
    )


def query_for_spawn(task_type: str, task_brief: str) -> list[str]:
    """Run a structured Hindsight recall for an about-to-spawn agent.

    Returns up to TOP_K citation strings ('[source · collection] excerpt').
    Fail-open: returns [] on any error or empty corpus so a recall outage
    never blocks a spawn.
    """
    try:
        from src.retrieval import agent_query  # lazy: keep dispatcher import light

        result = agent_query.query(
            _build_query(task_type, task_brief),
            agent=SPAWN_RECALL_AGENT,
            max_tokens=MAX_TOKENS,
            k_returned=TOP_K,
        )
    except Exception:  # noqa: BLE001 — recall must never block a spawn
        logger.debug("spawn recall failed — proceeding without prior context", exc_info=True)
        return []
    return [f"[{c.source_id} · {c.collection}] {c.excerpt}" for c in result.citations[:TOP_K]]


def query_failures_for_spawn(task_type: str, task_brief: str) -> list[str]:
    """Negative-example recall for an about-to-spawn agent (Wave 6).

    Thin fail-open wrapper over agent_query.query_failures — itself flag-gated
    (RETRIEVAL_FAILURE_RECALL_ENABLED, default off) and fail-open, so this
    returns [] when the feature is disabled, on empty corpus, or on any error.
    """
    try:
        from src.retrieval import agent_query  # lazy: keep dispatcher import light

        return agent_query.query_failures(task_type, task_brief)
    except Exception:  # noqa: BLE001 — failure recall must never block a spawn
        logger.debug("spawn failure-recall failed — proceeding without it", exc_info=True)
        return []


def build_prior_context_block(results: list[str]) -> str:
    """Format positive recall results into the injectable block, clamped to KEI-55."""
    if not results:
        return ""
    lines = [BLOCK_HEADER, *(f"- {r}" for r in results)]
    return "\n".join(lines)[:MAX_BLOCK_CHARS]


def build_failure_context_block(results: list[str]) -> str:
    """Format failure recall results into a separate block, clamped to KEI-55."""
    if not results:
        return ""
    lines = [FAILURE_BLOCK_HEADER, *(f"- {r}" for r in results)]
    return "\n".join(lines)[:MAX_BLOCK_CHARS]


def build_spawn_context_block(task_type: str, task_brief: str) -> str:
    """The full spawn-context block: positive recall + (flag-gated) failures.

    When RETRIEVAL_FAILURE_RECALL_ENABLED is off (default), the failure block is
    empty and this is byte-identical to the positive-only block — no regression
    on the existing path. When on, the 'Past failures to avoid' block is
    appended as a separate section. Each section is independently KEI-55-clamped;
    enabling failure recall opts the spawn into a second bounded block.
    """
    positive = build_prior_context_block(query_for_spawn(task_type, task_brief))
    failures = build_failure_context_block(query_failures_for_spawn(task_type, task_brief))
    return "\n\n".join(block for block in (positive, failures) if block)


def inject_prior_context(
    spawn_kwargs: dict,
    *,
    task_type: str,
    task_brief: str,
) -> dict:
    """Return spawn_kwargs with the recall block injected into env.

    The block lands in env[PRIOR_CONTEXT_ENV_KEY] — the only context-bearing
    field forwarded verbatim to the backend spawn. Fail-open: returns the
    original spawn_kwargs unchanged on error or when there is nothing to
    inject.
    """
    try:
        block = build_spawn_context_block(task_type, task_brief)
        return inject_block(spawn_kwargs, block)
    except Exception:  # noqa: BLE001 — injection must never block a spawn
        logger.debug("inject_prior_context failed — spawn proceeds unchanged", exc_info=True)
        return spawn_kwargs


def inject_block(spawn_kwargs: dict, block: str) -> dict:
    """Place an already-built prior-context block into the spawn env.

    Split out from inject_prior_context so a caller that produced the block by
    another path (e.g. a workflow-scoped cache that reuses an earlier spawn's
    recall — see src/retrieval/workflow_recall) injects it identically. Returns
    spawn_kwargs unchanged when block is empty.
    """
    if not block:
        return spawn_kwargs
    new_kwargs = dict(spawn_kwargs)
    env = dict(new_kwargs.get("env") or {})
    env[PRIOR_CONTEXT_ENV_KEY] = block
    new_kwargs["env"] = env
    return new_kwargs
