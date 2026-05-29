#!/usr/bin/env python3
"""run_atomiser_backfill.py — full decision-class backfill into fleet_decisions.

Production factory + runner for the decisions atomizer (TASK 2 of the
full-coverage atomization directive). Walks every decision source via
`decision_sources.iter_all_decision_sources` (original 4 + the e–i extension:
ceo: decision keys, completion:KEI-*, ceo:deliberation:*, personas/*.md,
docs/architecture/**.md) and atomizes each into the Hindsight `fleet_decisions`
bank.

Modes:
  --dry-run (default)  Walk sources, apply the checkpoint, print per-source +
                       totals + an $AUD cost estimate. No DB write, no LLM call.
  --execute            Construct the production Atomizer (LiteLLMGeminiClient +
                       AtomStore + job logger) and atomize each un-done source.
                       Pre-flight verifies the keiracom_atomizer_jobs /
                       keiracom_atoms tables exist; if not, exits cleanly with a
                       pointer to the migration (no partial writes).

Checkpoint: a JSONL cursor file records every processed source_ref so reruns
skip done items. When a DB is available the cursor is also seeded from
keiracom_atomizer_jobs (status='atomizer_done') so prior runs of the original
directive flow are not re-atomised.

Env: KEIRACOM_ATOMIZER_ENABLED=on, GEMINI_API_KEY, DATABASE_URL (all in
/home/elliotbot/.config/agency-os/.env).

Usage:
  python3 scripts/run_atomiser_backfill.py --dry-run
  python3 scripts/run_atomiser_backfill.py --execute   # after the migration lands
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from src.keiracom_system.atomization.decision_sources import (
    DecisionSource,
    iter_all_decision_sources,
)

log = logging.getLogger("atomiser_backfill")

CURSOR_DEFAULT = Path("runtime/atomiser_backfill_cursor.jsonl")
LOG_DEFAULT = Path("runtime/atomiser_backfill_log.jsonl")
ATOMIZER_TABLES = ("keiracom_atomizer_jobs", "keiracom_atoms")

# gemini-2.5-flash published rates (USD / 1M tokens). Estimate only — actual
# spend is logged per-source on --execute from the LLMResponse usage.
_USD_PER_1M_IN = 0.30
_USD_PER_1M_OUT = 2.50
_USD_TO_AUD = 1.55  # LAW II — 1 USD = 1.55 AUD
_CHARS_PER_TOKEN = 4
_OUTPUT_RATIO = 0.25  # atoms compress the source; output ≈ 25% of input tokens


@dataclass
class CostEstimate:
    sources: int
    tokens_in: int
    tokens_out: int

    @property
    def aud(self) -> float:
        usd = (self.tokens_in / 1e6) * _USD_PER_1M_IN + (self.tokens_out / 1e6) * _USD_PER_1M_OUT
        return usd * _USD_TO_AUD


def _load_cursor(path: Path) -> set[str]:
    """Return the set of already-processed source_refs from the cursor file."""
    done: set[str] = set()
    if not path.is_file():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            done.add(json.loads(line)["source_ref"])
        except (json.JSONDecodeError, KeyError):
            continue
    return done


def _seed_cursor_from_jobs(db: object, done: set[str]) -> set[str]:
    """Add source_refs already atomized (keiracom_atomizer_jobs done) to the cursor."""
    try:
        db.execute(  # type: ignore[attr-defined]
            "SELECT DISTINCT source_ref FROM keiracom_atomizer_jobs WHERE status = 'atomizer_done'"
        )
        for row in db.fetchall() or []:  # type: ignore[attr-defined]
            done.add(str(row[0]))
    except Exception as exc:  # noqa: BLE001 — table may not exist yet; fail-open
        log.warning("could not seed cursor from keiracom_atomizer_jobs: %s", exc)
    return done


def _append_cursor(path: Path, source_ref: str, atoms: int, tokens: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"source_ref": source_ref, "atoms": atoms, "tokens": tokens}) + "\n")


def _estimate(sources: list[DecisionSource]) -> CostEstimate:
    tokens_in = sum(len(s.source_text) // _CHARS_PER_TOKEN for s in sources)
    return CostEstimate(len(sources), tokens_in, int(tokens_in * _OUTPUT_RATIO))


def _filter_done(sources: Iterable[DecisionSource], done: set[str]) -> list[DecisionSource]:
    return [s for s in sources if s.source_ref not in done]


def _connect_db(dsn: str | None) -> object | None:
    """Open a psycopg connection cursor, or None when no DSN / driver."""
    if not dsn:
        return None
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        import psycopg

        conn = psycopg.connect(dsn, prepare_threshold=None, autocommit=True)
        return conn.cursor()
    except Exception as exc:  # noqa: BLE001 — dry-run can still walk file sources
        log.warning("DB connect failed (%s) — ceo_memory sources skipped", exc)
        return None


def _tables_present(db: object) -> bool:
    """True only when BOTH atomizer tables exist — pre-flight for --execute."""
    try:
        db.execute(  # type: ignore[attr-defined]
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ANY(%s)",
            list(ATOMIZER_TABLES),
        )
        return int((db.fetchone() or [0])[0]) == len(ATOMIZER_TABLES)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        log.error("table pre-flight failed: %s", exc)
        return False


def run_dry(sources: list[DecisionSource]) -> int:
    """Print every source that WOULD be atomized + the $AUD cost estimate."""
    by_kind: dict[str, int] = {}
    for s in sources:
        by_kind[s.source_kind] = by_kind.get(s.source_kind, 0) + 1
        log.info("would atomize %s [%s] %d chars", s.source_ref, s.source_kind, len(s.source_text))
    est = _estimate(sources)
    log.info("──────── DRY-RUN SUMMARY ────────")
    for kind, n in sorted(by_kind.items()):
        log.info("  %s: %d sources", kind, n)
    log.info(
        "TOTAL: %d sources · ~%d in + ~%d out tokens · est ~$%.2f AUD (gemini-2.5-flash)",
        est.sources,
        est.tokens_in,
        est.tokens_out,
        est.aud,
    )
    return 0


def _build_atomizer():  # pragma: no cover — exercised only on --execute post-migration
    """Construct the production decisions Atomizer (Gemini + AtomStore + jobs)."""
    from src.keiracom_system.atomization.atom_store import AtomStore
    from src.keiracom_system.atomization.decisions_atomizer import DecisionsAtomizer
    from src.keiracom_system.atomization.llm_client import LiteLLMGeminiClient
    from src.keiracom_system.embeddings.tei_client import TEIClient
    from src.retrieval.orchestrator import FLEET_TENANT_SLUG

    dsn = (os.environ.get("DATABASE_URL") or "").replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )
    import psycopg

    cur = psycopg.connect(dsn, prepare_threshold=None, autocommit=True).cursor()
    store = AtomStore(db=cur, tenant_id=FLEET_TENANT_SLUG, embedder=TEIClient())
    return DecisionsAtomizer(llm=LiteLLMGeminiClient(), store=store, job_db=cur), cur


def run_execute(sources: list[DecisionSource], cursor_path: Path) -> int:  # pragma: no cover
    """Atomize each source for real, checkpointing after each. Pre-flight-gated."""
    from src.keiracom_system.atomization.decisions_atomizer import (
        DecisionsAtomizerError,
    )

    atomizer, db = _build_atomizer()
    if not _tables_present(db):
        log.error(
            "BLOCKED: %s missing on the live DB. Apply supabase/migrations/"
            "20260526_keiracom_atomization_pilot.sql before --execute. No writes attempted.",
            " / ".join(ATOMIZER_TABLES),
        )
        return 2
    n_ok = n_fail = 0
    for s in sources:
        try:
            job = atomizer.atomize(s)
            n_ok += 1
            _append_cursor(cursor_path, s.source_ref, job.atoms_produced, 0)
            log.info("atomized %s — %d atoms", s.source_ref, job.atoms_produced)
        except DecisionsAtomizerError as exc:
            n_fail += 1
            log.warning("FAILED %s: %s", s.source_ref, exc)
    log.info("EXECUTE SUMMARY: ok=%d fail=%d", n_ok, n_fail)
    return 0 if n_fail == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute", action="store_true", help="atomize for real (default: dry-run)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="explicit dry-run (the default; walk + estimate, no writes/LLM)",
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--cursor", type=Path, default=CURSOR_DEFAULT)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    if os.environ.get("KEIRACOM_ATOMIZER_ENABLED", "").lower() not in {"1", "true", "on", "yes"}:
        log.error("KEIRACOM_ATOMIZER_ENABLED is not on — refusing to run.")
        return 3

    db = _connect_db(os.environ.get("DATABASE_URL"))
    done = _load_cursor(args.cursor)
    if db is not None:
        done = _seed_cursor_from_jobs(db, done)
    log.info("checkpoint: %d source_refs already done — will skip", len(done))

    all_sources = list(iter_all_decision_sources(db=db, repo_root=args.repo_root))
    pending = _filter_done(all_sources, done)
    log.info("sources: %d total, %d pending after checkpoint", len(all_sources), len(pending))

    if not args.execute:
        return run_dry(pending)
    return run_execute(pending, args.cursor)


if __name__ == "__main__":
    sys.exit(main())
