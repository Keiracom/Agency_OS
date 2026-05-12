#!/usr/bin/env python3
"""cognee_smoke.py — Phase 0 smoke test for Cognee integration.

Drives `src.cognee.client` through the directive's add → cognify → search
sequence and asserts both verify conditions. Captures stdout for the Phase 0
evidence items (#ceo post) and returns exit code 0 (pass) / 2 (fail) so CI +
shell pipelines can gate on it.

Usage (after [READY:atlas] + GEMINI_API_KEY present in .env):

    python3 scripts/cognee_smoke.py

Override scope (defaults match the directive smoke test verbatim):

    python3 scripts/cognee_smoke.py \
        --org-id keiracom_platform --app-id agency_os --agent-id aiden

The assertion content + query are fixed to the directive spec so this script
is the canonical Phase 0 → Phase 1 gate check; not parameterised on payload.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import traceback

# Fixed per Phase 0 directive (Elliot dispatch ts 1778562982 step 5).
SMOKE_CONTENT = (
    "Agency OS uses DFS domain_metrics_by_categories as the sole working "
    "discovery endpoint for AU dental."
)
SMOKE_QUERY = "What is the Agency OS discovery endpoint?"
EXPECTED_TOKEN = "domain_metrics_by_categories"


async def _run(org_id: str, app_id: str, agent_id: str) -> int:
    from src.cognee.client import add, cognify, search

    print(f"[smoke] add → dataset={org_id}__{app_id} agent={agent_id} node_set=[test]")
    await add(
        SMOKE_CONTENT,
        org_id=org_id,
        app_id=app_id,
        agent_id=agent_id,
        node_set=["test"],
    )

    print("[smoke] cognify → processing pending data into graph + embeddings")
    await cognify()

    print(f"[smoke] search → {SMOKE_QUERY!r}")
    results = await search(SMOKE_QUERY, org_id=org_id, app_id=app_id)

    print(f"[smoke] results: {results!r}")

    # Assertion 1 — Phase 0 evidence item 2
    if not results or len(results) == 0:
        print("[smoke] FAIL — assertion 1: len(results) > 0 → False (0 results)")
        return 2
    print(f"[smoke] PASS — assertion 1: len(results) > 0 → True ({len(results)} result(s))")

    # Assertion 2 — Phase 0 evidence item 3
    results_text = str(results)
    if EXPECTED_TOKEN not in results_text:
        print(f"[smoke] FAIL — assertion 2: {EXPECTED_TOKEN!r} in results → False")
        print(f"[smoke] results snippet: {results_text[:500]}")
        return 2
    print(f"[smoke] PASS — assertion 2: {EXPECTED_TOKEN!r} in results → True")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org-id", default="keiracom_platform")
    parser.add_argument("--app-id", default="agency_os")
    parser.add_argument("--agent-id", default="aiden")
    args = parser.parse_args()

    try:
        return asyncio.run(_run(args.org_id, args.app_id, args.agent_id))
    except Exception:
        print("[smoke] FAIL — exception during smoke run:")
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
