"""Dynamic context composer for the Chat agent (John).

John's spawn system prompt is intentionally minimal (identity + the spawn
governance contract per docs/cutover/spawn_governance_template.md). What it
needs to *answer* the current message is injected at spawn time by this module:
classify the latest customer message, then run a Hindsight retrieval pass scoped
to that message type, and return a bounded context block to inject.

Pipeline:
  1. Classify the message with a lightweight Gemini call (gemini-2.5-flash via
     the LiteLLM proxy — `src.keiracom_system.atomization.llm_client`, which
     honours the internal-vs-customer routing policy and GEMINI_API_KEY env).
  2. Map the type to Hindsight collections and run one retrieval pass:
       technical  → Decisions + AgentMemories
       task       → Decisions + Keis
       escalation → AgentMemories (this customer's prior context)
       ambiguous  → no retrieval; return the fail-open escalate block.
  3. Build a ≤800-token context block.

Fail-open throughout (matches the retrieval-layer + spawn-governance §3
contract): a classification failure is treated as `ambiguous`; a retrieval
failure yields an empty block, never an exception. The classifier carries NO
business routing rules — it labels the message into one of four abstract types;
the actual routing rules / tier logic / escalation protocols live in Hindsight
and are surfaced by the retrieval pass, not hardcoded here.

Two entry points for two lifecycle moments (additive, non-overlapping):
  * `compose_chat_context` — per *message*: classify the incoming message and
    retrieve the context block to answer it.
  * `compose_context` — per *spawn startup*: hydrate a fresh John spawn with
    tenant config + prior decisions/patterns before it sees any message. Async
    + fail-open; every source degrades to empty/{} independently.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from src.keiracom_system.atomization.llm_client import (
    LiteLLMGeminiClient,
    LLMClient,
    resolve_api_key_from_env,
)
from src.retrieval import agent_query

logger = logging.getLogger(__name__)

# gemini-2.5-flash through the LiteLLM proxy (provider-prefixed model name).
CLASSIFIER_MODEL = "google/gemini-2.5-flash"

MAX_CONTEXT_TOKENS = 800
CHARS_PER_TOKEN = 4  # matches the repo-wide token approximation
_MAX_BLOCK_CHARS = MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN
_HISTORY_TURNS = 5  # recent turns fed to the classifier for disambiguation

AMBIGUOUS_BLOCK = "insufficient context to classify — escalate to Deliberator"

# Type → Hindsight collections. Empty tuple = no retrieval (fail-open block).
# Collection names match orchestrator.HINDSIGHT_BANK_BY_CLASS ("Keis", not "KEIs").
_COLLECTIONS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "technical": ("Decisions", "AgentMemories"),
    "task": ("Decisions", "Keis"),
    "escalation": ("AgentMemories",),
    "ambiguous": (),
}

_CLASSIFY_SCHEMA: dict[str, Any] = {
    "name": "chat_message_classification",
    "schema": {
        "type": "object",
        "properties": {
            "classification": {
                "type": "string",
                "enum": ["technical", "task", "escalation", "ambiguous"],
            }
        },
        "required": ["classification"],
        "additionalProperties": False,
    },
}

# Abstract type definitions only — deliberately NO business routing rules.
_CLASSIFY_INSTRUCTION = (
    "You classify a customer message for a chat agent. Read the latest message "
    "(recent conversation is given for context) and label it as exactly one of:\n"
    "- technical: asks how the system/product works, its behaviour or design.\n"
    "- task: requests that work be performed, set up, or changed.\n"
    "- escalation: expresses dissatisfaction or urgency, or asks for a human.\n"
    "- ambiguous: intent cannot be determined from the message.\n"
    "Return only the classification label."
)

RetrieveFn = Callable[[str, tuple[str, ...]], Any]


@dataclass(frozen=True)
class ChatContextResult:
    context_block: str
    classification: str
    citations: list[dict[str, Any]]
    token_estimate: int


def _classify(message: str, last_n_messages: Sequence[str], llm_client: LLMClient | None) -> str:
    """Gemini classification → one of the four types. Fail-open to 'ambiguous'."""
    try:
        client = llm_client or LiteLLMGeminiClient(api_key=resolve_api_key_from_env())
        history = "\n".join(last_n_messages[-_HISTORY_TURNS:]) if last_n_messages else "(none)"
        prompt = (
            f"{_CLASSIFY_INSTRUCTION}\n\nRecent conversation:\n{history}"
            f"\n\nLatest message:\n{message}"
        )
        resp = client.call_structured(
            model=CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_schema=_CLASSIFY_SCHEMA,
            temperature=0.0,
        )
        label = str((resp.parsed or {}).get("classification", "")).strip().lower()
        if label in _COLLECTIONS_BY_TYPE:
            return label
        logger.warning("chat classifier returned unknown label — treating as ambiguous")
        return "ambiguous"
    except Exception:  # noqa: BLE001 — fail-open: any classifier failure → ambiguous
        logger.warning("chat classification failed — treating as ambiguous", exc_info=True)
        return "ambiguous"


def _default_retrieve(query_text: str, collections: tuple[str, ...]) -> Any:
    """Production retrieval — one Hindsight pass over the mapped collections.

    citation_required=False so the best-available context still surfaces even
    when scores are low/zero (the chat agent wants context, not an empty block).
    """
    return agent_query.query(
        query_text, agent="john", collections=collections, citation_required=False
    )


def _build_block(classification: str, answer: str, citations: list[dict[str, Any]]) -> str:
    """Render the dynamic context block, hard-capped at the token budget."""
    lines = [f"[DYNAMIC CONTEXT — {classification}]"]
    if answer:
        lines.append(answer)
    if citations:
        lines.append("")
        lines.append("Retrieved context:")
        lines.extend(f"- [{c['source_id']}] ({c['collection']}) {c['excerpt']}" for c in citations)
    block = "\n".join(lines)
    return block[:_MAX_BLOCK_CHARS]  # token budget: len(block)//4 <= 800


def _retrieve(
    message: str, customer_id: int, classification: str, retrieve_fn: RetrieveFn | None
) -> tuple[str, list[dict[str, Any]]]:
    """Run the scoped Hindsight pass. Fail-open to ('', []) on any retrieval error."""
    collections = _COLLECTIONS_BY_TYPE[classification]
    if not collections:
        return "", []
    query_text = message
    if classification == "escalation":
        # Bias retrieval toward this customer's prior interactions.
        query_text = f"customer {customer_id} prior context: {message}"
    try:
        result = (retrieve_fn or _default_retrieve)(query_text, collections)
    except Exception:  # noqa: BLE001 — retrieval failure → empty block, not exception
        logger.warning("chat retrieval failed (classification=%s)", classification, exc_info=True)
        return "", []
    citations = [
        {
            "source_id": c.source_id,
            "collection": c.collection,
            "score": round(c.score, 3),
            "excerpt": c.excerpt,
        }
        for c in result.citations
    ]
    return _build_block(classification, result.answer, citations), citations


def compose_chat_context(
    message: str,
    customer_id: int,
    last_n_messages: list[str],
    *,
    llm_client: LLMClient | None = None,
    retrieve_fn: RetrieveFn | None = None,
) -> ChatContextResult:
    """Classify `message` and return the dynamic context block for John's spawn.

    `llm_client` / `retrieve_fn` are injection seams for tests (mock Gemini +
    mock Hindsight); production uses the LiteLLM Gemini client + agent_query.
    """
    classification = _classify(message, last_n_messages, llm_client)
    if classification == "ambiguous":
        block, citations = AMBIGUOUS_BLOCK, []
    else:
        block, citations = _retrieve(message, customer_id, classification, retrieve_fn)
    return ChatContextResult(
        context_block=block,
        classification=classification,
        citations=citations,
        token_estimate=len(block) // CHARS_PER_TOKEN,
    )


# ─────────────────────── Spawn-startup hydration ───────────────────────
# compose_context: a SECOND, additive entry point. Where compose_chat_context
# reacts to one message, this hydrates a fresh John spawn at startup from three
# sources — keiracom tenant config, Hindsight prior decisions/patterns, and
# relevant ceo_memory keys — and returns a ChatContext. Async + fail-open; the
# three fetchers are injection seams (tests mock them).

DECISIONS_COLLECTION: tuple[str, ...] = ("Decisions",)
PATTERNS_COLLECTION: tuple[str, ...] = ("Discoveries",)  # recurring patterns / discovery log
MAX_DECISIONS = 5
MAX_PATTERNS = 5
_MEMORY_TERM_MINLEN = 4
_MEMORY_MAX_TERMS = 4

TenantFetch = Callable[[int], Awaitable[dict[str, Any]]]
MemoryFetch = Callable[[str], Awaitable[list[str]]]
AsyncRetrieveFn = Callable[[str, tuple[str, ...]], Awaitable[Any]]


@dataclass(frozen=True)
class ChatContext:
    tenant_config: dict[str, Any]
    relevant_decisions: list[str]
    prior_patterns: list[str]


def _hydration_dsn() -> str | None:
    """Resolve a plain `postgresql://` DSN for asyncpg (strip SQLAlchemy tags)."""
    dsn = os.environ.get("SUPABASE_DB_DSN") or os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


async def _default_async_retrieve(query_text: str, collections: tuple[str, ...]) -> Any:
    """Production Hindsight pass (async). citation_required=False → best-available."""
    return await agent_query.query_async(
        query_text,
        agent="john",
        collections=collections,
        k_returned=max(MAX_DECISIONS, MAX_PATTERNS),
        citation_required=False,
    )


async def _default_tenant_fetch(customer_id: int) -> dict[str, Any]:
    """Fail-open tenant-config lookup.

    SCHEMA GAP (flagged to orchestrator): the keiracom tenant tables
    (keiracom_tenants / keiracom_tenant_budgets / dispatcher_customers) are all
    UUID-keyed — there is no int `customer_id` column, and no
    `max_concurrent_tasks` column anywhere. Until an int→tenant mapping exists,
    the default cannot resolve config, so it returns {}. Callers that hold the
    customer→tenant mapping inject `tenant_fetch`.
    """
    logger.info(
        "compose_context: default tenant_fetch is a no-op for customer_id=%s — "
        "no int customer_id→tenant mapping in schema yet; inject tenant_fetch",
        customer_id,
    )
    return {}


async def _default_memory_fetch(conversation_seed: str) -> list[str]:
    """Recent ceo_memory keys whose key/value matches conversation terms."""
    dsn = _hydration_dsn()
    terms = [t for t in conversation_seed.lower().split() if len(t) >= _MEMORY_TERM_MINLEN]
    terms = terms[:_MEMORY_MAX_TERMS]
    if not dsn or not terms:
        return []
    from src.utils.asyncpg_connection import get_asyncpg_connection

    patterns = [f"%{t}%" for t in terms]
    conn = await get_asyncpg_connection(dsn)
    try:
        rows = await conn.fetch(
            "SELECT key, LEFT(value::text, 160) AS preview FROM public.ceo_memory "
            "WHERE key ILIKE ANY($1) OR value::text ILIKE ANY($1) "
            "ORDER BY updated_at DESC LIMIT $2",
            patterns,
            MAX_DECISIONS,
        )
    finally:
        await conn.close()
    return [f"{r['key']} — {r['preview']}" for r in rows]


def _citations_to_strings(result: Any) -> list[str]:
    return [f"[{c.source_id}] {c.excerpt}" for c in (getattr(result, "citations", None) or [])]


async def _resolve_tenant(customer_id: int, tenant_fetch: TenantFetch | None) -> dict[str, Any]:
    try:
        return await (tenant_fetch or _default_tenant_fetch)(customer_id) or {}
    except Exception:  # noqa: BLE001 — fail-open: never block the spawn
        logger.warning("compose_context: tenant_fetch failed", exc_info=True)
        return {}


async def _resolve_decisions(
    seed: str, retrieve_fn: AsyncRetrieveFn | None, memory_fetch: MemoryFetch | None
) -> list[str]:
    """Hindsight Decisions + relevant ceo_memory keys, merged + capped. Fail-open."""
    retrieve = retrieve_fn or _default_async_retrieve
    mem = memory_fetch or _default_memory_fetch

    async def _hindsight() -> list[str]:
        try:
            return _citations_to_strings(await retrieve(seed, DECISIONS_COLLECTION))
        except Exception:  # noqa: BLE001
            logger.warning("compose_context: decisions retrieval failed", exc_info=True)
            return []

    async def _memory() -> list[str]:
        try:
            return await mem(seed)
        except Exception:  # noqa: BLE001
            logger.warning("compose_context: ceo_memory fetch failed", exc_info=True)
            return []

    hits, mem_hits = await asyncio.gather(_hindsight(), _memory())
    return (hits + mem_hits)[:MAX_DECISIONS]


async def _resolve_patterns(
    customer_id: int, seed: str, retrieve_fn: AsyncRetrieveFn | None
) -> list[str]:
    """Hindsight recurring patterns, biased toward this customer. Fail-open."""
    try:
        result = await (retrieve_fn or _default_async_retrieve)(
            f"customer {customer_id}: {seed}", PATTERNS_COLLECTION
        )
    except Exception:  # noqa: BLE001
        logger.warning("compose_context: patterns retrieval failed", exc_info=True)
        return []
    return _citations_to_strings(result)[:MAX_PATTERNS]


async def compose_context(
    customer_id: int,
    conversation_seed: str,
    *,
    tenant_fetch: TenantFetch | None = None,
    memory_fetch: MemoryFetch | None = None,
    retrieve_fn: AsyncRetrieveFn | None = None,
) -> ChatContext:
    """Assemble the spawn-startup context payload for a John spawn.

    Fail-open: each of the three sources degrades to empty/{} independently —
    a failure in one never blocks the spawn. The three fetchers are injection
    seams for tests (mock tenant config + ceo_memory + Hindsight). Retrieval is
    capped at MAX_DECISIONS + MAX_PATTERNS for the token budget.
    """
    tenant_config, relevant_decisions, prior_patterns = await asyncio.gather(
        _resolve_tenant(customer_id, tenant_fetch),
        _resolve_decisions(conversation_seed, retrieve_fn, memory_fetch),
        _resolve_patterns(customer_id, conversation_seed, retrieve_fn),
    )
    return ChatContext(
        tenant_config=tenant_config,
        relevant_decisions=relevant_decisions,
        prior_patterns=prior_patterns,
    )
