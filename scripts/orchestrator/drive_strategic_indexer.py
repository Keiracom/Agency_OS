#!/usr/bin/env python3
"""drive_strategic_indexer.py — KEI-208 Drive → Weaviate StrategicDocuments.

Pulls a configurable list of Google Drive docs (config/drive_index_targets.json)
into the Weaviate `StrategicDocuments` collection. Same shape as the KEI-85
indexer family (extends BaseIndexer; deterministic UUIDs; idempotent upsert).

Chunk strategy: heading-boundary split, NOT fixed-token. Each Google Docs
heading (HEADING_1 / HEADING_2 / HEADING_3) starts a new section; the section
spans paragraphs until the next heading. Each section becomes one Weaviate
object so retrieval returns semantic-coherent chunks.

Drive auth: reuses /home/elliotbot/google-service-account.json (same pattern
as write_manual_mirror.py + drive_intelligence_feed). Scope: docs.readonly.

Usage:
    python3 scripts/orchestrator/drive_strategic_indexer.py             # daemon loop (6h poll)
    python3 scripts/orchestrator/drive_strategic_indexer.py --once      # one batch
    python3 scripts/orchestrator/drive_strategic_indexer.py --batch=5   # limit doc count
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Bootstrap so `from indexer_base import ...` works when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from indexer_base import (  # noqa: E402
    BaseIndexer,
    aggregate_count,
    deterministic_uuid,
)

logger = logging.getLogger("drive_strategic_indexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

STRATEGIC_CLASS = "StrategicDocuments"
SOURCE_NAME = "drive_strategic"
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "drive_index_targets.json"
)
SERVICE_ACCOUNT_FILE = "/home/elliotbot/google-service-account.json"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]

POLL_SECONDS = int(os.environ.get("DRIVE_STRATEGIC_POLL_SECONDS", "21600"))  # 6h default


# ─── data classes ─────────────────────────────────────────────────────────


@dataclass
class DriveSection:
    """One heading-bounded section of a Drive doc — becomes one Weaviate object."""

    doc_id: str
    doc_url: str
    doc_title: str
    section: str  # heading text or "(intro)" for content before any heading
    content: str  # all body text under this heading until next heading
    updated_at: str  # ISO8601 from Drive modifiedTime
    ratified_by: str
    ratified_at: str  # from config

    @property
    def identity(self) -> str:
        """Stable key for deterministic UUID — survives doc edits as long as
        the heading text doesn't change."""
        return f"{self.doc_id}::{self.section}"


# ─── Drive client ─────────────────────────────────────────────────────────


def _docs_client() -> Any:
    """Lazy-build the googleapiclient.discovery Docs v1 client. Same auth path
    as write_manual_mirror.py — service account JSON keyfile."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "drive_strategic_indexer requires `pip install google-api-python-client google-auth`"
        ) from exc

    if not Path(SERVICE_ACCOUNT_FILE).exists():
        raise RuntimeError(f"service account file not found: {SERVICE_ACCOUNT_FILE}")

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=DRIVE_SCOPES
    )
    return build("docs", "v1", credentials=creds, cache_discovery=False)


# ─── parser: heading-bounded chunker ──────────────────────────────────────


def _paragraph_text(element: dict) -> str:
    """Extract plaintext from a single docs API paragraph element."""
    parts: list[str] = []
    for run in element.get("paragraph", {}).get("elements", []):
        text_run = run.get("textRun", {})
        content = text_run.get("content", "")
        if content:
            parts.append(content)
    return "".join(parts).rstrip("\n")


def parse_doc_sections(
    doc_body: list[dict],
    *,
    doc_id: str,
    doc_url: str,
    doc_title: str,
    updated_at: str,
    ratified_by: str,
    ratified_at: str,
) -> list[DriveSection]:
    """Walk the doc body, emit one DriveSection per heading boundary.

    Heading boundary = paragraphStyle.namedStyleType starts with HEADING_.
    Body text before any heading lands in the synthetic "(intro)" section.
    Empty sections are dropped (the post-section content stays attached
    to the last seen heading).
    """
    sections: list[DriveSection] = []
    current_heading = "(intro)"
    current_body: list[str] = []

    def _flush() -> None:
        text = "\n".join(line for line in current_body if line).strip()
        if text:
            sections.append(
                DriveSection(
                    doc_id=doc_id,
                    doc_url=doc_url,
                    doc_title=doc_title,
                    section=current_heading,
                    content=text,
                    updated_at=updated_at,
                    ratified_by=ratified_by,
                    ratified_at=ratified_at,
                )
            )

    for element in doc_body:
        if "paragraph" not in element:
            continue
        para = element["paragraph"]
        style = (para.get("paragraphStyle") or {}).get("namedStyleType", "")
        text = _paragraph_text(element)
        if style.startswith("HEADING_"):
            _flush()
            current_heading = text or current_heading
            current_body = []
        else:
            current_body.append(text)
    _flush()
    return sections


# ─── indexer ──────────────────────────────────────────────────────────────


@dataclass
class DriveStrategicIndexer(BaseIndexer[DriveSection]):
    """Indexes Drive doc sections into Weaviate StrategicDocuments."""

    config_path: Path = DEFAULT_CONFIG_PATH
    _doc_cache: list[DriveSection] = field(default_factory=list)

    @property
    def source_name(self) -> str:
        return SOURCE_NAME

    @property
    def target_class(self) -> str:
        return STRATEGIC_CLASS

    @property
    def class_schema(self) -> dict:
        return {
            "class": STRATEGIC_CLASS,
            "description": "Ratified strategic decisions chunked from Drive (KEI-208).",
            "vectorizer": "text2vec-openai",
            "properties": [
                {"name": "doc_id", "dataType": ["text"]},
                {"name": "doc_url", "dataType": ["text"]},
                {"name": "title", "dataType": ["text"]},
                {"name": "section", "dataType": ["text"]},
                {"name": "content", "dataType": ["text"]},
                {"name": "updated_at", "dataType": ["date"]},
                {"name": "ratified_by", "dataType": ["text"]},
                {"name": "ratified_at", "dataType": ["date"]},
            ],
        }

    def identity_key(self, row: DriveSection) -> str:
        return row.identity

    def fetch_batch(self, batch_size: int) -> list[DriveSection]:
        """Pull all sections from all configured docs in one batch. The
        BaseIndexer wraps this in upsert + retry; deterministic UUIDs make
        re-runs idempotent so we don't track cursors per doc."""
        if not self._doc_cache:
            self._doc_cache = self._fetch_all_sections()
        # Yield up to batch_size at a time so BaseIndexer can chunk POSTs.
        batch = self._doc_cache[:batch_size]
        self._doc_cache = self._doc_cache[batch_size:]
        return batch

    def build_object(self, row: DriveSection) -> dict:
        return {
            "id": deterministic_uuid(self.source_name, row.identity),
            "class": self.target_class,
            "properties": {
                "doc_id": row.doc_id,
                "doc_url": row.doc_url,
                "title": row.doc_title,
                "section": row.section,
                "content": row.content,
                "updated_at": row.updated_at,
                "ratified_by": row.ratified_by,
                "ratified_at": row.ratified_at,
            },
        }

    def _fetch_all_sections(self) -> list[DriveSection]:
        """Fetch every doc in config; parse sections; flatten."""
        with self.config_path.open(encoding="utf-8") as fh:
            config = json.load(fh)
        targets = config.get("documents", [])
        if not targets:
            logger.warning("config %s has no documents — nothing to index", self.config_path)
            return []
        docs = _docs_client()
        all_sections: list[DriveSection] = []
        for target in targets:
            doc_id = target["doc_id"]
            try:
                resp = docs.documents().get(documentId=doc_id).execute()
            except Exception as exc:  # noqa: BLE001 — surface but continue
                logger.warning("fetch failed doc_id=%s: %s", doc_id, exc)
                continue
            sections = parse_doc_sections(
                resp.get("body", {}).get("content", []),
                doc_id=doc_id,
                doc_url=f"https://docs.google.com/document/d/{doc_id}",
                doc_title=target.get("title") or resp.get("title", ""),
                updated_at=resp.get("revisionId", "")[:10] or "2026-01-01",
                ratified_by=target.get("ratified_by", "dave"),
                ratified_at=target.get("ratified_at", "2026-01-01"),
            )
            logger.info("doc_id=%s sections=%d", doc_id, len(sections))
            all_sections.extend(sections)
        return all_sections


# ─── main ────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(prog="drive_strategic_indexer")
    parser.add_argument("--once", action="store_true", help="run one batch then exit")
    parser.add_argument("--batch", type=int, default=200, help="max sections per batch")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="JSON config listing target doc_ids",
    )
    args = parser.parse_args()

    indexer = DriveStrategicIndexer(config_path=args.config)
    # KEI-208 follow-up fix: was `indexer.ensure_class()` which is not on
    # BaseIndexer — AttributeError crashed the script on first start, which
    # is why the StrategicDocuments class never appeared in Weaviate despite
    # PR #1018 being merged. Module-level `ensure_class(name, schema)` is the
    # underlying helper; BaseIndexer's instance method is `ensure_target_class`.
    indexer.ensure_target_class()
    if args.once:
        outcome = indexer.index_once(batch_size=args.batch)
        logger.info("once outcome: %s", outcome.to_dict())
        try:
            count = aggregate_count(STRATEGIC_CLASS)
            logger.info("StrategicDocuments count after run: %s", count)
        except Exception:  # noqa: BLE001
            pass
        return 1 if outcome.failed else 0
    return _run_daemon_loop(indexer, poll_seconds=POLL_SECONDS, batch_size=args.batch)


def _run_daemon_loop(
    indexer: DriveStrategicIndexer,
    *,
    poll_seconds: int,
    batch_size: int,
) -> int:
    """Daemon loop for the Drive-backed indexer.

    KEI-208 follow-up fix: was `indexer.run_forever(...)` which is not on
    BaseIndexer — AttributeError would crash daemon mode on startup. Drive
    indexer cannot use run_db_indexer (that's Postgres-specific via psycopg).
    This inline loop mirrors the run_db_indexer signal-handling + sleep shape.
    """
    shutdown_flag = {"requested": False}

    def _on_signal(signum: int, _frame: Any) -> None:
        logger.info("signal %s received — shutdown", signum)
        shutdown_flag["requested"] = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    while not shutdown_flag["requested"]:
        try:
            outcome = indexer.index_once(batch_size=batch_size)
            count = aggregate_count(STRATEGIC_CLASS)
            logger.info(
                "batch outcome=%s class_count=%s",
                outcome.to_dict(),
                count,
            )
        except Exception as exc:  # noqa: BLE001 — broad on purpose: surface every fault
            logger.exception("batch failed — sleeping then continuing: %s", exc)
        for _ in range(poll_seconds):
            if shutdown_flag["requested"]:
                break
            time.sleep(1)
    logger.info("drive_strategic_indexer exiting cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
