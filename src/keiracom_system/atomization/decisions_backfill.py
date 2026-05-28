"""decisions_backfill.py — one-time historical decision backfill → Hindsight.

Pulls the historical ratified-decision backlog (ceo_memory directive keys +
CONSOLIDATED_RULES + v2 inventory + MANUAL §13 via decision_sources), atomizes
each into AtomV1 (DecisionsAtomizer), and ingests the atoms into the Hindsight
`fleet_decisions` bank — so a freshly-spawned agent recalls the full decision
history, not just atoms written after live atomization came online.

Built ahead of Orion's live AtomV1 writer (Agency_OS-d0kh). `atom_to_hindsight_item`
is the FORMAT-MATCH SEAM: it must serialize an AtomV1 the same way the live
writer does. RECONCILE the mapping below with d0kh before the live run; the
`--execute` path is gated so it cannot run against prod until that confirm lands.

Default is dry-run (enumerate + plan, no LLM spend, no Hindsight write).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.keiracom_system.atomization.decision_sources import (
    DecisionSource,
    iter_all_decision_sources,
)
from src.keiracom_system.atomization.schema import AtomV1

logger = logging.getLogger(__name__)

DEFAULT_BANK = "fleet_decisions"
HINDSIGHT_BASE = os.environ.get("HINDSIGHT_BASE", "http://localhost:8889")
HINDSIGHT_TENANT = os.environ.get("HINDSIGHT_TENANT_SLUG", "default")
IngestFn = Callable[[str, list[dict[str, Any]]], None]


def atom_to_hindsight_item(atom: AtomV1) -> dict[str, Any]:
    """Serialize an AtomV1 into a Hindsight memory item.

    ⚠ FORMAT-MATCH SEAM (Agency_OS-d0kh): this must mirror the live writer's
    AtomV1→item mapping exactly, or backfilled atoms diverge from live atoms in
    the same bank. Reconcile before the --execute run. Reference mapping:
      content  = atom.content (the decision statement; what recall ranks on)
      tags     = ["atom_v1", state, schema_vN] + composition-tag axis values
      metadata = the full structured atom (so retrieval keeps trigger/provenance)
    """
    ct = atom.composition_tags or {}
    tags = ["atom_v1", f"state:{atom.state}", f"schema_v{atom.schema_version}"]
    tags += [v for v in (ct.get("domain"), ct.get("concern"), ct.get("applicable_context")) if v]
    metadata = {
        "atom_id": str(atom.atom_id),
        "tenant_id": str(atom.tenant_id),
        "schema_version": atom.schema_version,
        "state": atom.state,
        "trigger_condition": json.dumps(atom.trigger_condition),
        "anti_pattern": atom.anti_pattern or "",
        "example": atom.example or "",
        "provenance": json.dumps(atom.provenance),
        "composition_tags": json.dumps(ct),
        "source": "decisions_backfill",
    }
    return {"content": atom.content, "tags": tags, "metadata": metadata}


def default_hindsight_ingest(bank: str, items: list[dict[str, Any]]) -> None:
    """POST items to the Hindsight bank (synchronous retain). Live path only."""
    from urllib import request as urlrequest

    body = json.dumps({"items": items, "async": False}).encode()
    url = f"{HINDSIGHT_BASE}/v1/{HINDSIGHT_TENANT}/banks/{bank}/memories"
    req = urlrequest.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    with urlrequest.urlopen(req, timeout=120) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"hindsight ingest HTTP {resp.status} for bank {bank}")


@dataclass
class BackfillResult:
    sources_seen: int = 0
    atoms_produced: int = 0
    atoms_ingested: int = 0
    by_source_kind: dict[str, int] = field(default_factory=dict)
    bank: str = DEFAULT_BANK
    dry_run: bool = True


def enumerate_sources(db: Any | None, repo_root: Path) -> list[DecisionSource]:
    """All historical decision sources (ceo_memory directives + the 3 docs)."""
    return list(iter_all_decision_sources(db=db, repo_root=repo_root))


class DecisionsBackfill:
    """Orchestrates: sources → AtomV1 (atomizer) → Hindsight fleet_decisions."""

    def __init__(
        self,
        *,
        atomizer: Any,
        store: Any,
        ingest_fn: IngestFn = default_hindsight_ingest,
        bank: str = DEFAULT_BANK,
    ) -> None:
        self._atomizer = atomizer
        self._store = store
        self._ingest = ingest_fn
        self._bank = bank

    def run(self, sources: Sequence[DecisionSource], *, dry_run: bool = True) -> BackfillResult:
        result = BackfillResult(bank=self._bank, dry_run=dry_run)
        for source in sources:
            result.sources_seen += 1
            result.by_source_kind[source.source_kind] = (
                result.by_source_kind.get(source.source_kind, 0) + 1
            )
            if dry_run:
                continue  # no LLM spend, no Hindsight write in dry-run
            items = self._atomize_and_serialize(source)
            result.atoms_produced += len(items)
            if items:
                self._ingest(self._bank, items)
                result.atoms_ingested += len(items)
        logger.info(
            "decisions_backfill %s: sources=%d by_kind=%s atoms=%d ingested=%d bank=%s",
            "PLAN" if dry_run else "RUN",
            result.sources_seen,
            result.by_source_kind,
            result.atoms_produced,
            result.atoms_ingested,
            result.bank,
        )
        return result

    def _atomize_and_serialize(self, source: DecisionSource) -> list[dict[str, Any]]:
        job = self._atomizer.atomize(source)
        items: list[dict[str, Any]] = []
        for atom_id in job.atom_ids or []:
            atom = self._store.get_atom(atom_id)
            if atom is not None:
                items.append(atom_to_hindsight_item(atom))
        return items


def sample_atom() -> AtomV1:
    """A valid synthetic decision atom for the serializer self-check + tests."""
    from uuid import uuid4

    return AtomV1(
        atom_id=uuid4(),
        tenant_id=uuid4(),
        trigger_condition={"kind": "context_predicate", "params": {"topic": "tenancy"}},
        content="Ratified: single shared system with tenant isolation; Dave=tenant_id 1.",
        anti_pattern="Do not spin per-tenant mirrored stacks.",
        example="customer onboarding assigns tenant_id 2+",
        provenance={
            "source": "ceo_memory:ceo:directive_10001_complete",
            "freshness": "2026-05-28",
            "confidence": 0.95,
            "last_validated": "2026-05-28",
        },
        composition_tags={
            "domain": "engineering",
            "concern": "security",
            "applicable_context": "background_job",
        },
    )


def _dry_run_plan(repo_root: Path) -> BackfillResult:
    """Enumerate sources + validate the serializer on a sample — no prod I/O."""
    sources = enumerate_sources(db=None, repo_root=repo_root)  # docs-only (no DB) for safety
    backfill = DecisionsBackfill(atomizer=None, store=None)
    result = backfill.run(sources, dry_run=True)
    logger.info(
        "serializer self-check item:\n%s",
        json.dumps(atom_to_hindsight_item(sample_atom()), indent=2),
    )
    return result


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="run live (default: dry-run)")
    parser.add_argument(
        "--confirmed-atom-format",
        action="store_true",
        help="operator ack that atom_to_hindsight_item matches Orion's live d0kh format",
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    if not args.execute:
        _dry_run_plan(Path(args.repo_root))
        return 0
    if not args.confirmed_atom_format:
        logger.error(
            "refusing --execute: pass --confirmed-atom-format only AFTER Orion's "
            "Agency_OS-d0kh live-format confirm. Backfill not run."
        )
        return 2
    logger.error("live --execute path requires atomizer+store wiring from env — not auto-run here")
    return 3


if __name__ == "__main__":
    sys.exit(main())
