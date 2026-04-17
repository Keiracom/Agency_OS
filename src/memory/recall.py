"""
FILE: src/memory/recall.py
PURPOSE: High-level retrieval backing the /recall Telegram command.
         v1 — text+tag content_contains + tag match, grouped by source_type.
         v2 will layer semantic search when embeddings ship.
"""

from .retrieve import retrieve, retrieve_by_tags
from .types import Memory

_HIGH_VALUE_TYPES = ["pattern", "decision", "skill", "dave_confirmed"]


def recall(topic: str | None = None, n: int = 20) -> dict[str, list[Memory]]:
    """High-level retrieval backing the /recall Telegram command.

    v1 behavior: if topic is a string, use it as content_contains + try-tag-match.
    Combines results from both. Groups the output by source_type.

    Returns: {source_type: [Memory, ...]} — empty types omitted.

    v2 will layer semantic search on top when embeddings ship.
    """
    if topic is None:
        memories = retrieve(types=_HIGH_VALUE_TYPES, n=n)
    else:
        by_content = retrieve(content_contains=topic, n=n)
        by_tag = retrieve_by_tags([topic], n=n)

        # Dedupe by id
        seen: set = set()
        memories = []
        for m in by_content + by_tag:
            if m.id not in seen:
                seen.add(m.id)
                memories.append(m)

    grouped: dict[str, list[Memory]] = {}
    for m in memories:
        grouped.setdefault(m.source_type, []).append(m)
    return grouped
