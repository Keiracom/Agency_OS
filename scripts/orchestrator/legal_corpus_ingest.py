#!/usr/bin/env python3
"""legal_corpus_ingest.py — KEI-187: one-shot ingest of curated legal corpus.

Builds Weaviate `legal_corpus` collection (created on first run) and POSTs one
object per chunk drawn from docs/legal_corpus/<category>.md. Categories match
the 7 ratified buckets: privacy-act-au, gdpr, ccpa, oaic, paddle-dpa,
saas-tos-pattern, ai-compliance-precedent.

This is NOT a daemon — the legal corpus is a fixed reference set. Re-runs are
idempotent: deterministic UUID per (category, chunk_id) means re-ingest no-ops
on already-indexed chunks (Weaviate 422 already-exists treated as success).

Each chunk carries:
  - raw_text          full chunk text (one normative passage)
  - category          one of the 7 ratified buckets
  - source_url        canonical URL (legislation register / vendor doc)
  - source_date       ISO date of the underlying source (when published / last revised)
  - chunk_id          stable id within the category (kebab-case slug)
  - environment_hash  sha256 of raw_text for change detection
  - created_at        timestamp of ingest

Schema mirrors the existing 5-property pattern (raw_text + environment_hash +
created_at + agent + kei) plus 4 corpus-specific properties.

Usage:
    python3 scripts/orchestrator/legal_corpus_ingest.py            # full ingest
    python3 scripts/orchestrator/legal_corpus_ingest.py --dry-run  # parse + count only
    python3 scripts/orchestrator/legal_corpus_ingest.py --category gdpr  # one bucket

Acceptance per KEI-187:
  - legal_corpus collection exists with all 7 categories populated
  - bd recall <topic> returns relevant chunks
  - CEO can draft Privacy Policy / ToS / DPA referencing the corpus

Source files live in docs/legal_corpus/<category>.md — see docs/legal_corpus/README.md
for the format spec and provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO_ROOT / "scripts" / "orchestrator"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

logger = logging.getLogger("legal_corpus_ingest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CORPUS_CLASS = "Legal_corpus"
SOURCE_NAME = "legal_corpus"
CORPUS_DIR = REPO_ROOT / "docs" / "legal_corpus"

CATEGORIES: tuple[str, ...] = (
    "privacy-act-au",
    "gdpr",
    "ccpa",
    "oaic",
    "paddle-dpa",
    "saas-tos-pattern",
    "ai-compliance-precedent",
)

CORPUS_SCHEMA = {
    "class": CORPUS_CLASS,
    "vectorizer": "none",
    "properties": [
        {"name": "raw_text", "dataType": ["text"]},
        {"name": "environment_hash", "dataType": ["text"]},
        {"name": "created_at", "dataType": ["date"]},
        {"name": "agent", "dataType": ["text"]},
        {"name": "kei", "dataType": ["text"]},
        {"name": "category", "dataType": ["text"]},
        {"name": "source_url", "dataType": ["text"]},
        {"name": "source_date", "dataType": ["text"]},
        {"name": "chunk_id", "dataType": ["text"]},
    ],
}


@dataclass(frozen=True)
class CorpusChunk:
    category: str
    chunk_id: str
    source_url: str
    source_date: str
    raw_text: str

    def env_hash(self) -> str:
        return hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()[:16]


_CHUNK_DELIM = re.compile(r"^---$", re.MULTILINE)
_HEADER_LINE = re.compile(r"^\s*([A-Za-z_]+)\s*:\s*(.+?)\s*$")


def parse_corpus_file(category: str, text: str) -> list[CorpusChunk]:
    """Parse a markdown corpus file into CorpusChunk records.

    File format: each chunk is a YAML-like header followed by the body, separated
    by `---` lines. Headers required: chunk_id, source_url, source_date.

      chunk_id: app-1-collection
      source_url: https://www.oaic.gov.au/...
      source_date: 2014-03-12

      <body text — one normative passage>
      ---
      chunk_id: app-3-quality
      ...
    """
    chunks: list[CorpusChunk] = []
    sections = [s.strip() for s in _CHUNK_DELIM.split(text) if s.strip()]
    for section in sections:
        lines = section.splitlines()
        headers: dict[str, str] = {}
        # Default: if the loop never finds a non-header transition (i.e. the
        # whole section is headers with no body), body_start = len(lines) so
        # the body slice comes out empty and the malformed check drops it.
        body_start = len(lines)
        for i, line in enumerate(lines):
            m = _HEADER_LINE.match(line)
            if m and not line.startswith(" "):
                headers[m.group(1).lower()] = m.group(2)
            else:
                # First non-header line ends the header block.
                if headers and line.strip() == "":
                    body_start = i + 1
                    break
                if headers and not _HEADER_LINE.match(line):
                    body_start = i
                    break
        body = "\n".join(lines[body_start:]).strip()
        chunk_id = headers.get("chunk_id", "").strip()
        source_url = headers.get("source_url", "").strip()
        source_date = headers.get("source_date", "").strip()
        if not chunk_id or not body:
            logger.warning(
                "[%s] skipping malformed chunk: id=%r body_len=%d", category, chunk_id, len(body)
            )
            continue
        chunks.append(
            CorpusChunk(
                category=category,
                chunk_id=chunk_id,
                source_url=source_url,
                source_date=source_date,
                raw_text=body,
            )
        )
    return chunks


def load_corpus(corpus_dir: Path, categories: tuple[str, ...]) -> list[CorpusChunk]:
    """Load all chunks from corpus_dir/<category>.md for the given categories."""
    all_chunks: list[CorpusChunk] = []
    for category in categories:
        path = corpus_dir / f"{category}.md"
        if not path.exists():
            logger.warning("missing corpus file: %s", path)
            continue
        text = path.read_text(encoding="utf-8")
        chunks = parse_corpus_file(category, text)
        logger.info("[%s] loaded %d chunks", category, len(chunks))
        all_chunks.extend(chunks)
    return all_chunks


def build_object(chunk: CorpusChunk, created_at_iso: str) -> dict[str, Any]:
    """Build a Weaviate object payload for one chunk."""
    from indexer_base import deterministic_uuid

    return {
        "class": CORPUS_CLASS,
        "id": deterministic_uuid(SOURCE_NAME, f"{chunk.category}:{chunk.chunk_id}"),
        "properties": {
            "raw_text": chunk.raw_text,
            "environment_hash": chunk.env_hash(),
            "created_at": created_at_iso,
            "agent": "scout",
            "kei": "KEI-187",
            "category": chunk.category,
            "source_url": chunk.source_url,
            "source_date": chunk.source_date,
            "chunk_id": chunk.chunk_id,
        },
    }


def main(argv: list[str] | None = None) -> int:
    import datetime as _dt

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse + count only; do not POST to Weaviate",
    )
    parser.add_argument(
        "--category",
        choices=CATEGORIES,
        default=None,
        help="ingest only one category (default: all 7)",
    )
    parser.add_argument(
        "--corpus-dir",
        default=str(CORPUS_DIR),
        help="override docs/legal_corpus path",
    )
    args = parser.parse_args(argv)

    categories = (args.category,) if args.category else CATEGORIES
    corpus_dir = Path(args.corpus_dir).resolve()
    chunks = load_corpus(corpus_dir, categories)
    if not chunks:
        logger.error("no chunks loaded; nothing to ingest")
        return 1

    if args.dry_run:
        by_cat: dict[str, int] = {}
        for c in chunks:
            by_cat[c.category] = by_cat.get(c.category, 0) + 1
        logger.info("dry-run — %d chunks total: %s", len(chunks), json.dumps(by_cat))
        return 0

    # Live ingest path — defer indexer_base import until needed so dry-run +
    # parsing tests can execute without psycopg/Weaviate deps.
    from indexer_base import ensure_class, post_object

    ensure_class(CORPUS_CLASS, CORPUS_SCHEMA)
    created_at = _dt.datetime.now(_dt.UTC).isoformat()
    success = 0
    failed = 0
    for chunk in chunks:
        obj = build_object(chunk, created_at)
        try:
            post_object(obj)
            success += 1
        except Exception as exc:
            logger.warning("[%s] %s failed: %s", chunk.category, chunk.chunk_id, exc)
            failed += 1
    logger.info("ingest complete: %d success, %d failed (of %d)", success, failed, len(chunks))
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
