"""
listener_discernment.py — L2 discernment layer for the memory listener.

Takes top-N retrieved candidates + the original query, calls GPT-4o-mini to:
  1. Pick the 5 most contextually useful rows (intelligence, not math)
  2. Compose a ≤100-word brief citing row IDs per sentence
  3. Return JSON: {selected_ids, brief, citations}

Fabrication guard: every sentence in `brief` must map to ≥1 row_id in
`citations`. Sentences that don't cite a row are dropped. Content must come
from the candidate rows, never from the LLM's training data.

Max plan discipline: uses OpenAI GPT-4o-mini (separate credit pool from
Anthropic Max). OPENAI_API_KEY already in env for embeddings; same key used
here. ~$0.00005 USD per call.

Integration point: memory_listener.find_relevant_memories() calls
discern_and_summarise(query, candidate_rows) after retrieval returns the
top-20 candidates. The result replaces the raw-row injection with a
synthesised brief block.
"""
import json
import logging
import os  # noqa: F401 — used in cost logging block
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
DISCERNMENT_MODEL = "gpt-4o-mini"
MAX_BRIEF_WORDS = 100
MAX_SELECTED = 5
CALL_TIMEOUT_S = 10


DISCERNMENT_SYSTEM_PROMPT = """You are a memory-discernment filter for a multi-agent conversational system.

Given a USER QUERY and a list of CANDIDATE MEMORIES (each with id + content), your job:

1. Pick the 5 most contextually useful memories for THIS specific query. Math-closest is not enough — judge which memories would actually help someone respond to the query. Contradictions count as useful. Relevant-but-stale count as useful. Off-topic-but-high-similarity do NOT count.

2. Compose a brief (≤100 words) summarising the picked memories as they relate to the query. The brief should read like "when you asked about X, here's what past context says." Use concrete language, not hedging.

3. Tag every sentence of the brief with which memory row_ids it cites.

STRICT RULES (violation = output rejected):
- Content in the brief MUST come from the picked memories. Do not add facts from your training data.
- Every sentence must cite ≥1 row_id. Sentences with no citation are invalid.
- If fewer than 5 candidates are genuinely useful, pick fewer — do not pad.
- If NONE of the candidates are useful, return empty selected_ids + empty brief.
- Output valid JSON only. No prose outside the JSON.

OUTPUT FORMAT:
{
  "selected_ids": ["uuid-1", "uuid-2", ...],
  "brief": "Sentence 1. Sentence 2. ...",
  "citations": {"0": ["uuid-1"], "1": ["uuid-1", "uuid-2"], ...}
}

The citations key is a sentence-index (0-based) → list of row_ids that support that sentence.
"""


async def discern_and_summarise(
    query_text: str,
    candidate_rows: list[dict],
) -> dict[str, Any]:
    """Call GPT-4o-mini to pick best 5 + write cited brief.

    Returns dict with keys: selected_ids (list), brief (str), citations (dict),
    and provenance_ok (bool — True if citation validator passed).

    On failure (API error, invalid JSON, citation validation failure), returns
    an empty discernment dict so the caller can fall back to raw-row injection.
    """
    if not OPENAI_API_KEY:
        return _empty_result("no_openai_key")
    if not candidate_rows:
        return _empty_result("no_candidates")

    candidates_payload = [
        {"id": r.get("id"), "content": (r.get("content") or "")[:500]}
        for r in candidate_rows
    ]

    user_message = json.dumps(
        {"query": query_text, "candidates": candidates_payload},
        ensure_ascii=False,
    )

    try:
        async with httpx.AsyncClient(timeout=CALL_TIMEOUT_S) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DISCERNMENT_MODEL,
                    "messages": [
                        {"role": "system", "content": DISCERNMENT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                    "max_tokens": 800,
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    f"[discernment] OpenAI returned {resp.status_code}: {resp.text[:200]}"
                )
                return _empty_result("openai_http_error")
            resp_json = resp.json()
            raw = resp_json["choices"][0]["message"]["content"]
            try:
                from src.telegram_bot.openai_cost_logger import log_openai_call
                usage = resp_json.get("usage", {})
                log_openai_call(
                    callsign=os.environ.get("CALLSIGN", "unknown"),
                    use_case="discernment",
                    model="gpt-4o-mini",
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                )
            except Exception:
                pass
    except Exception as exc:
        logger.warning(f"[discernment] call failed: {exc}")
        return _empty_result("call_exception")

    parsed = _parse_and_validate(raw, candidate_rows)
    return parsed


def _parse_and_validate(
    raw: str, candidate_rows: list[dict]
) -> dict[str, Any]:
    """Parse the JSON + run citation validation. Drops sentences missing citations."""
    try:
        data = json.loads(raw)
    except Exception as exc:
        logger.warning(f"[discernment] JSON parse failed: {exc}")
        return _empty_result("json_parse_error")

    selected_ids = [
        s for s in (data.get("selected_ids") or []) if isinstance(s, str)
    ][:MAX_SELECTED]
    brief = data.get("brief") or ""
    citations = data.get("citations") or {}

    # Only keep selected_ids that actually appear in candidate_rows
    valid_ids = {r.get("id") for r in candidate_rows if r.get("id")}
    selected_ids = [s for s in selected_ids if s in valid_ids]

    # Split brief into sentences, keep only those with cite ≥1 valid row_id
    if not brief.strip():
        return {
            "selected_ids": selected_ids,
            "brief": "",
            "citations": {},
            "provenance_ok": True,  # empty is valid — no fabrication to check
            "empty_reason": "empty_brief",
        }

    sentences = _split_sentences(brief)
    validated_sentences: list[str] = []
    validated_citations: dict[str, list[str]] = {}
    dropped_sentences = 0

    for i, sentence in enumerate(sentences):
        cite_list = citations.get(str(i), [])
        valid_cites = [c for c in cite_list if c in valid_ids]
        if valid_cites:
            validated_sentences.append(sentence)
            validated_citations[str(len(validated_sentences) - 1)] = valid_cites
        else:
            dropped_sentences += 1

    # Enforce word cap AFTER dropping uncited sentences
    brief_out = " ".join(validated_sentences)
    word_count = len(brief_out.split())
    if word_count > MAX_BRIEF_WORDS:
        words = brief_out.split()
        brief_out = " ".join(words[:MAX_BRIEF_WORDS])

    provenance_ok = dropped_sentences == 0

    return {
        "selected_ids": selected_ids,
        "brief": brief_out,
        "citations": validated_citations,
        "provenance_ok": provenance_ok,
        "dropped_uncited_sentences": dropped_sentences,
    }


def _split_sentences(text: str) -> list[str]:
    """Simple sentence splitter — good enough for our 100-word briefs."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _empty_result(reason: str) -> dict[str, Any]:
    return {
        "selected_ids": [],
        "brief": "",
        "citations": {},
        "provenance_ok": True,
        "empty_reason": reason,
    }


def format_discernment_block(discernment: dict[str, Any]) -> str:
    """Format the discernment output for injection into the message context."""
    brief = discernment.get("brief", "")
    if not brief:
        return ""
    selected_ids = discernment.get("selected_ids", [])
    lines = ["[MEMORY BRIEF — discerned past context:]"]
    lines.append(brief)
    if selected_ids:
        lines.append(f"[cited row IDs: {', '.join(selected_ids[:5])}]")
    lines.append("[END MEMORY BRIEF]")
    return "\n".join(lines)
