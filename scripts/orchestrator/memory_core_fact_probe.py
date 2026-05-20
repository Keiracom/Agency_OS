#!/usr/bin/env python3
"""memory_core_fact_probe.py — standing core-fact drift check (Agency_OS-zbvs).

The memory-content audit (2026-05-20) found 4 of 5 core system facts in
Cognee stale or missing despite the indexers/stores being healthy — working
plumbing, wrong facts ("the Anthropic error"). The plumbing probes
(governance_freshness_probe) cannot catch this: they check that memory is
fresh, not that it is CORRECT.

This probe is the content check. It recalls each core system fact from
Cognee and asserts the answer contains the ground-truth keywords (sourced
from ARCHITECTURE.md / docs/governance/model_routing.md). A missing keyword
= DRIFT — memory has gone stale or lost a fact. On drift it emits a
structured alert to keiracom.elliot.inbox and exits non-zero (fail-loud).

Runs as a systemd timer (6h cadence). NOT a Linear/Supabase writer.

Usage:
    python3 scripts/orchestrator/memory_core_fact_probe.py

Exit codes:
  0  every core fact recalled correctly
  1  one or more facts drifted (logged + alerted)
  2  config error (no recall path available)
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys

logger = logging.getLogger("memory_core_fact_probe")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_NATS_BIN = "/usr/local/bin/nats"
_ALERT_SUBJECT = "keiracom.elliot.inbox"

# Core system facts + the ground-truth keywords every correct recall must
# contain. Sources: ARCHITECTURE.md §4/§5/§7, docs/governance/model_routing.md.
# When ARCHITECTURE.md changes, update the expected keywords here in lock-step
# (the probe is the lock — a drift here vs the doc fails CI's own review).
_CORE_FACTS: tuple[dict[str, object], ...] = (
    {
        "label": "model-routing",
        "query": "which LLM do worker agents versus internal governance tiers run on",
        "required": ["Claude Max", "OpenAI"],
    },
    {
        "label": "enrichment-pipeline",
        "query": "active lead enrichment email waterfall layer count F2.2",
        "required": ["6-layer", "F2.2"],
    },
    {
        "label": "active-vendors",
        "query": "active production outreach vendors",
        "required": ["Salesforge", "Unipile"],
    },
    {
        "label": "active-channels",
        "query": "active outreach channels for campaigns",
        "required": ["Email", "LinkedIn", "Voice", "SMS"],
    },
    {
        "label": "fleet-structure",
        "query": "agent fleet worker callsigns and deliberators",
        "required": ["Atlas", "Orion", "Elliot"],
    },
)


def recall(query: str) -> str:
    """Return Cognee's recalled text for a query (empty string on failure)."""
    try:
        from cognee_http_client import search  # noqa: PLC0415 — fail-open import
    except ImportError as exc:
        logger.debug("cognee_http_client import failed: %s", exc)
        return ""
    try:
        resp = search(query, top_k=3, search_type="GRAPH_COMPLETION")
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("cognee search failed (query_len=%d): %s", len(query), exc)
        return ""
    if isinstance(resp, list):
        return " ".join(str(item) for item in resp if item)
    if isinstance(resp, dict):
        for key in ("results", "hits", "items", "answers"):
            if isinstance(resp.get(key), list):
                return " ".join(str(item) for item in resp[key] if item)
    return str(resp or "")


def check_facts() -> list[dict[str, object]]:
    """Recall every core fact; return the list of drifted facts (empty = OK)."""
    drifts: list[dict[str, object]] = []
    for fact in _CORE_FACTS:
        label = str(fact["label"])
        text = recall(str(fact["query"])).lower()
        required = [str(r) for r in fact["required"]]  # type: ignore[union-attr]
        missing = [r for r in required if r.lower() not in text]
        if missing:
            drifts.append({"label": label, "missing": missing})
            logger.error("DRIFT %s — missing from recall: %s", label, missing)
        else:
            logger.info("ok %s — all ground-truth keywords recalled", label)
    return drifts


def _emit_drift_alert(drifts: list[dict[str, object]]) -> None:
    """Fail-loud — publish a structured drift alert. Best-effort."""
    lines = "\n".join(f"  {d['label']}: missing {d['missing']}" for d in drifts)
    text = (
        f"[ALERT:memory-core-fact-probe] {len(drifts)} core fact(s) DRIFTED — "
        f"Cognee recall no longer matches ARCHITECTURE.md ground truth:\n{lines}\n"
        f"Force a re-ingest: scripts/cognee_auto_ingest.py --once"
    )
    envelope = {"from": "memory-core-fact-probe", "kind": "blocker", "summary": text}
    try:
        subprocess.run(  # noqa: S603 — fixed args, no shell
            [_NATS_BIN, "pub", _ALERT_SUBJECT, json.dumps(envelope)],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        logger.exception("drift-alert NATS publish failed")


def main() -> int:
    drifts = check_facts()
    if drifts:
        _emit_drift_alert(drifts)
        print(f"DRIFT: {len(drifts)}/{len(_CORE_FACTS)} core facts stale")
        return 1
    print(f"OK: {len(_CORE_FACTS)}/{len(_CORE_FACTS)} core facts recalled correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
