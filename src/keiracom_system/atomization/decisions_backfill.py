"""decisions_backfill.py — one-time historical decision backfill → Hindsight.

Pulls the historical ratified-decision backlog (ceo_memory directive keys +
CONSOLIDATED_RULES + v2 inventory + MANUAL §13 via decision_sources), atomizes
each into AtomV1 (DecisionsAtomizer), and ingests the atoms into the Hindsight
`fleet_decisions` bank — so a freshly-spawned agent recalls the full decision
history, not just atoms written after live atomization came online.

Format is RECONCILED with the live writer: `atom_to_hindsight_item` +
`default_hindsight_ingest` are imported from the one-source seam
`atomization/hindsight_writer.py` (Orion PR #1292 / Agency_OS-9goi) — literally
the same functions the live exit-cycle writer uses, so backfilled and live atoms
are byte-identical (only `source` differs: decisions_backfill vs live_spawn_exit).

Default is dry-run (enumerate + plan, no LLM spend, no Hindsight write). The
`--execute` path stays gated behind `--confirmed-atom-format` as an explicit
operator go-ahead before a real prod backfill run.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from src.keiracom_system.atomization.decision_sources import (
    DecisionSource,
    decision_composition_tags,
    iter_all_decision_sources,
)

# ONE-SOURCE seam (Elliot mandate; Orion PR #1292 / Agency_OS-9goi): the AtomV1→
# Hindsight item mapping + ingest live in exactly ONE place so the live exit-cycle
# writer and this backfill are byte-identical. atom_to_hindsight_item defaults
# source="decisions_backfill" (our provenance); the live writer passes
# source="live_spawn_exit" — the only field that differs. The shared converter
# str()s schema_version (Hindsight 422s on non-string metadata) — fixes the
# int-schema_version bug that would have failed every backfilled atom on --execute.
from src.keiracom_system.atomization.hindsight_writer import (
    DEFAULT_BANK,
    atom_to_hindsight_item,
    default_hindsight_ingest,
)
from src.keiracom_system.atomization.schema import AtomV1

# Reuse the live writer's fleet tenant sentinel (Agency_OS-c66k blocker A, Orion
# lane-owner confirm 2026-05-29): backfilled atoms MUST share the live writer's
# tenant partition (0…01) or L2 recall splits across two tenants. Direct import
# (not a redefined literal) so it can never drift from exit_cycle.
from src.keiracom_system.chat.exit_cycle import FLEET_TENANT_UUID

logger = logging.getLogger(__name__)

IngestFn = Callable[[str, list[dict[str, Any]]], None]


@dataclass
class BackfillResult:
    sources_seen: int = 0
    atoms_produced: int = 0
    atoms_ingested: int = 0
    skipped: int = 0  # already-backfilled sources (idempotency ledger hit)
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


# ───────────────────────────────────────────────────────────────────────
# Direct-write backfill (Agency_OS-c66k blocker B — Elliot ratified path:
# direct Hindsight-bank write, NO LLM atomizer / AtomStore / TEI / pgvector).
# Builds an AtomV1 verbatim from each DecisionSource and ingests it straight to
# the bank via the same one-source seam the live writer uses. Deterministic
# atom_id + a keiracom_atomizer_jobs.source_ref ledger give re-run idempotency
# (blocker C); FLEET_TENANT_UUID stamps the correct partition (blocker A).
# ───────────────────────────────────────────────────────────────────────

# (source_ref) -> bool : has this source already been backfilled?
IsBackfilledFn = Callable[[str], bool]
# (source_ref, source_kind, atom_id) -> None : record a completed backfill.
RecordFn = Callable[[str, str, str], None]


def build_atom_from_source(source: DecisionSource, *, today: str) -> AtomV1:
    """Map a DecisionSource verbatim to a fleet decision AtomV1 — no LLM.

    Mirrors exit_cycle._build_atom field shape so direct-write backfill atoms
    are indistinguishable from live ones (only provenance.source differs).
    atom_id is deterministic in source_ref so a re-run produces the same id.
    """
    return AtomV1(
        atom_id=uuid5(NAMESPACE_URL, f"keiracom:c66k:{source.source_ref}"),
        tenant_id=FLEET_TENANT_UUID,
        trigger_condition={
            "kind": "context_predicate",
            "params": {"source": source.source_ref, "source_kind": source.source_kind},
        },
        content=source.source_text,
        anti_pattern=None,
        example=None,
        provenance={
            "source": source.source_ref,
            "freshness": today,
            "confidence": 1.0,  # ratified historical items are ground truth
            "last_validated": today,
        },
        composition_tags=decision_composition_tags(),
    )


def make_db_ledger(db: Any) -> tuple[IsBackfilledFn, RecordFn]:
    """Idempotency ledger over keiracom_atomizer_jobs.source_ref (blocker C).

    `db` is a psycopg-style cursor — execute(query, params_seq) + fetchone().
    is_backfilled() short-circuits a source that already has a completed job
    row; record() writes one after ingest.
    """

    def is_backfilled(source_ref: str) -> bool:
        db.execute(
            "SELECT 1 FROM keiracom_atomizer_jobs "
            "WHERE source_ref = %s AND status = 'atomizer_done' LIMIT 1",
            (source_ref,),
        )
        return db.fetchone() is not None

    def record(source_ref: str, source_kind: str, atom_id: str) -> None:
        db.execute(
            "INSERT INTO keiracom_atomizer_jobs ("
            "job_id, tenant_id, source_ref, source_kind, atomizer_model, "
            "atomizer_temp, atoms_produced, status"
            ") VALUES (%s, %s, %s, %s, 'direct_backfill', 0, 1, 'atomizer_done')",
            (str(uuid4()), str(FLEET_TENANT_UUID), source_ref, source_kind),
        )

    return is_backfilled, record


def run_direct(
    sources: Sequence[DecisionSource],
    *,
    ingest_fn: IngestFn = default_hindsight_ingest,
    bank: str = DEFAULT_BANK,
    today: str | None = None,
    is_backfilled: IsBackfilledFn | None = None,
    record: RecordFn | None = None,
    dry_run: bool = True,
) -> BackfillResult:
    """Direct-write each source to the Hindsight bank. Idempotent + dry-run-safe.

    dry_run still runs the idempotency read + builds every atom (so schema
    errors surface pre-prod) but performs no ingest and writes no ledger row.
    """
    day = today or datetime.now(UTC).strftime("%Y-%m-%d")
    result = BackfillResult(bank=bank, dry_run=dry_run)
    for source in sources:
        result.sources_seen += 1
        result.by_source_kind[source.source_kind] = (
            result.by_source_kind.get(source.source_kind, 0) + 1
        )
        if not (source.source_text or "").strip():
            logger.warning("skip empty source_text: %s", source.source_ref)
            continue
        if is_backfilled is not None and is_backfilled(source.source_ref):
            result.skipped += 1
            continue
        try:
            atom = build_atom_from_source(source, today=day)
        except ValueError as exc:  # schema-invalid content — log + skip, never abort the run
            logger.warning("skip schema-invalid source %s: %s", source.source_ref, exc)
            continue
        item = atom_to_hindsight_item(atom)
        result.atoms_produced += 1
        if dry_run:
            continue
        self_ingest = ingest_fn  # local alias keeps the call line short
        self_ingest(bank, [item])
        result.atoms_ingested += 1
        if record is not None:
            record(source.source_ref, source.source_kind, str(atom.atom_id))
    logger.info(
        "decisions_backfill DIRECT %s: sources=%d by_kind=%s built=%d ingested=%d "
        "skipped=%d bank=%s",
        "PLAN" if dry_run else "RUN",
        result.sources_seen,
        result.by_source_kind,
        result.atoms_produced,
        result.atoms_ingested,
        result.skipped,
        result.bank,
    )
    return result


STAGING_BANK = "fleet_decisions_staging"


def _connect_cursor() -> tuple[Any | None, Any | None]:
    """Open a psycopg connection+cursor from DATABASE_URL (CLI-local).

    psycopg is imported inside this CLI helper, never in the library functions
    (run_direct/build_atom_from_source take an injected db). This module is on
    the BMV1 Guard (b) exemption list — CLI backfill entrypoint, not the agent
    hot path; see scripts/ci/check_no_direct_db_outside_mal.sh (the guard greps
    indented imports too, so the exemption — not deferral — is what permits it).
    Returns (None, None) when no DSN is set — caller falls back to docs-only.
    """
    import os

    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not raw:
        return None, None
    import psycopg

    dsn = raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = psycopg.connect(dsn, autocommit=True, prepare_threshold=None)
    return conn, conn.cursor()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="run live (default: dry-run plan)")
    parser.add_argument(
        "--confirmed-atom-format",
        action="store_true",
        help="operator/Orion ack the atom format matches the live writer (Agency_OS-d0kh)",
    )
    parser.add_argument(
        "--bank",
        default=STAGING_BANK,
        help=f"Hindsight bank (default {STAGING_BANK}; staging-first per c66k criterion d)",
    )
    parser.add_argument(
        "--i-understand-prod",
        action="store_true",
        help=f"required to target the live {DEFAULT_BANK} bank (else staging only)",
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    # Prod-bank guard (Orion criterion d — staging-first): never write the live
    # bank without the explicit ack.
    if args.bank == DEFAULT_BANK and not args.i_understand_prod:
        logger.error(
            "refusing bank=%s without --i-understand-prod (default is staging %s). "
            "Run staging first, review atom output with Orion, then re-run with the ack.",
            DEFAULT_BANK,
            STAGING_BANK,
        )
        return 2

    conn, cur = _connect_cursor()
    try:
        sources = list(iter_all_decision_sources(db=cur, repo_root=Path(args.repo_root)))
        is_backfilled = record = None
        if cur is not None:
            is_backfilled, record = make_db_ledger(cur)

        if not args.execute:
            result = run_direct(sources, bank=args.bank, is_backfilled=is_backfilled, dry_run=True)
            logger.info(
                "DRY-RUN PLAN: %d sources, %d atoms would be written, %d already "
                "backfilled (skipped). LLM spend: $0 AUD (direct-write, no atomizer). "
                "bank=%s. Pass --execute --confirmed-atom-format to run.",
                result.sources_seen,
                result.atoms_produced,
                result.skipped,
                args.bank,
            )
            return 0

        if not args.confirmed_atom_format:
            logger.error("refusing --execute without --confirmed-atom-format (Orion d0kh gate).")
            return 2

        result = run_direct(
            sources,
            bank=args.bank,
            is_backfilled=is_backfilled,
            record=record,
            dry_run=False,
        )
        logger.info(
            "EXECUTE complete: %d sources processed, %d atoms ingested, %d skipped. bank=%s",
            result.sources_seen,
            result.atoms_ingested,
            result.skipped,
            args.bank,
        )
        return 0
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
