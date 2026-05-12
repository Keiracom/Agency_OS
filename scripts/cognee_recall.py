#!/usr/bin/env python3
"""cognee_recall.py — task-keyed Cognee semantic-recall wrapper for dispatch enrichment.

KEI-7 Cognee Phase 2 Wire-into-Agent-Sessions (Dave directive ts ~1778591500,
Elliot confirm ts 1778592025).

Pipes a dispatch text through Cognee's semantic search and prepends the
top-N matched chunks as a `## Cognee context` comment block, then emits
the enriched dispatch on stdout.

The mechanical hook point is inbox-watcher delivery: when atlas / orion /
scout inbox-watchers read a new dispatch file and have CONTENT to inject
into the agent's tmux pane, they pipe CONTENT through this wrapper FIRST.
The agent reads the enriched dispatch with governance corpus context
already in place — no Step 0 boilerplate needed to fetch it.

Fail-open semantics:
  - Cognee unavailable / search raises / empty results → output original
    dispatch unchanged, exit 0. Agent dispatch path never blocks on
    knowledge-graph health.
  - GEMINI_API_KEY / LLM_API_KEY missing → skip search, pass-through.
  - Wrapper itself raises → still exit 0 (caller's `|| echo "$CONTENT"`
    fallback is a belt-and-braces guard).

Usage:
    echo "<dispatch text>" | cognee_recall.py [--limit N] [--org-id ID]
                                              [--app-id ID] [--agent-id ID]

    --text TEXT       use TEXT instead of stdin
    --limit N         top-N hits (default 5)
    --org-id ID       default 'keiracom_platform'
    --app-id ID       default 'agency_os'
    --agent-id ID     scope results to a specific agent (default unscoped)

Exit codes:
  0  always — wrapper is fail-open by contract
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("cognee_recall")

DEFAULT_ORG = "keiracom_platform"
DEFAULT_APP = "agency_os"
DEFAULT_LIMIT = 5
MAX_CHUNK_PREVIEW_CHARS = 400


def _format_context(hits: list, limit: int) -> str:
    """Render top-N hits as a markdown comment block. Empty list → empty string."""
    if not hits:
        return ""
    lines = ["## Cognee context (top semantic hits)"]
    for i, hit in enumerate(hits[:limit], 1):
        text = str(hit)
        preview = text[:MAX_CHUNK_PREVIEW_CHARS].rstrip()
        if len(text) > MAX_CHUNK_PREVIEW_CHARS:
            preview += "…"
        preview_oneline = preview.replace("\n", " ").strip()
        lines.append(f"{i}. {preview_oneline}")
    return "\n".join(lines) + "\n\n"


def _has_credentials() -> bool:
    """LiteLLM needs an LLM API key for Cognee's Gemini-backed search."""
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY"))


async def _search(query: str, org_id: str, app_id: str, agent_id: str | None):
    """Call src.cognee.client.search. Any failure logs + returns []."""
    try:
        from src.cognee.client import search
    except ImportError as exc:
        logger.warning("cognee.client import failed: %s", exc)
        return []
    try:
        kwargs: dict = {"org_id": org_id, "app_id": app_id}
        if agent_id:
            kwargs["agent_id"] = agent_id
        result = await search(query, **kwargs)
        return result or []
    except Exception as exc:  # noqa: BLE001 — fail-open by contract
        logger.warning("cognee.search failed: %s", exc)
        return []


def enrich_dispatch(
    text: str,
    *,
    limit: int = DEFAULT_LIMIT,
    org_id: str = DEFAULT_ORG,
    app_id: str = DEFAULT_APP,
    agent_id: str | None = None,
    search_fn=None,
) -> str:
    """Return `{context-block}{original-text}` or unchanged text on failure.

    search_fn is injectable for tests; production omits it and the wrapper
    routes through asyncio.run + src.cognee.client.search.
    """
    if not text.strip():
        return text
    if not _has_credentials():
        return text

    if search_fn is None:
        hits = asyncio.run(_search(text, org_id, app_id, agent_id))
    else:
        hits = search_fn(text, org_id=org_id, app_id=app_id, agent_id=agent_id) or []

    context = _format_context(hits, limit)
    if not context:
        return text
    return context + text


_ON_WAKE_QUERY_TEMPLATE = (
    "Recent decisions for callsign {callsign} — what is the current task context, "
    "what KEI issues are open, what was decided in the last 24 hours, "
    "and what should the agent resume on?"
)


def _on_wake_query() -> str:
    """KEI-31 component 2: synthesize a generic restart-context query
    using the callsign from IDENTITY.md (or CALLSIGN env). The query
    surfaces recent decisions + open KEI context for the resumed session."""
    cs = os.environ.get("CALLSIGN", "")
    if not cs:
        identity = os.path.expanduser("./IDENTITY.md")
        if os.path.isfile(identity):
            try:
                with open(identity) as f:
                    for line in f:
                        if "CALLSIGN:" in line:
                            cs = line.split("CALLSIGN:")[-1].strip().strip("*").strip().lower()
                            break
            except OSError:
                pass
    return _ON_WAKE_QUERY_TEMPLATE.format(callsign=cs or "agent")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", default=None, help="dispatch text (overrides stdin)")
    parser.add_argument(
        "--on-wake",
        action="store_true",
        help="KEI-31 component 2: synthesize restart-context query from callsign and "
        "emit recall hits as markdown block on stdout (no stdin needed)",
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--org-id", default=DEFAULT_ORG)
    parser.add_argument("--app-id", default=DEFAULT_APP)
    parser.add_argument("--agent-id", default=None)
    args = parser.parse_args(argv)

    try:
        if args.on_wake:
            text = _on_wake_query()
        elif args.text is not None:
            text = args.text
        elif not sys.stdin.isatty():
            text = sys.stdin.read()
        else:
            text = ""
    except OSError:
        text = ""

    try:
        enriched = enrich_dispatch(
            text,
            limit=args.limit,
            org_id=args.org_id,
            app_id=args.app_id,
            agent_id=args.agent_id,
        )
    except Exception as exc:  # noqa: BLE001 — fail-open by contract
        logger.warning("enrich_dispatch raised: %s", exc)
        enriched = text

    sys.stdout.write(enriched)
    return 0  # always succeed — caller's pipe relies on it


if __name__ == "__main__":
    sys.exit(main())
