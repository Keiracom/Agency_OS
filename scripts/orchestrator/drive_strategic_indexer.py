#!/usr/bin/env python3
"""drive_strategic_indexer.py — Drive → Weaviate StrategicDocuments indexer (KEI-208).

Loads target doc IDs exclusively from config/drive_index_targets.json.
No doc IDs are hardcoded in this file.  Adding a new document = append to
config + restart the timer.

Drive auth: uses the keiradrive MCP server via subprocess
(mcp__keiradrive__keiradrive_read_doc pattern).  No googleapiclient
dependency exists in the repo as of KEI-208.  If a future KEI adds
google-api-python-client, migrate and update this docstring per LAW XIII.

Vectorizer: text2vec-openai (OPENAI_API_KEY required in env).

Modes:
    --mode=full         Bulk backfill all targets (default)
    --mode=incremental  Only re-index docs whose Drive modifiedTime advanced

Usage:
    python3 scripts/orchestrator/drive_strategic_indexer.py --mode=full
    python3 scripts/orchestrator/drive_strategic_indexer.py --mode=incremental

Per reference_psycopg_supabase_pgbouncer: psycopg with prepare_threshold=None
and +asyncpg DSN prefix stripped.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ─── Path bootstrap ──────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _REPO_ROOT / "config" / "drive_index_targets.json"
_LOG_PATH = Path("/home/elliotbot/clawd/logs/drive_strategic_indexer.log")

sys.path.insert(0, str(_REPO_ROOT / "scripts" / "orchestrator"))

from _strategic_collection_schema import ensure_strategic_class  # noqa: E402
from indexer_base import WEAVIATE_BASE, deterministic_uuid, post_object  # noqa: E402

# ─── Logging ─────────────────────────────────────────────────────────────────
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(_LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("drive_strategic_indexer")

SOURCE_NAME = "drive_strategic"
STRATEGIC_DOCS_CLASS = "StrategicDocuments"
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)

# ─── Supabase DSN helpers ────────────────────────────────────────────────────
REQUEST_TIMEOUT = 10.0
_WEAVIATE_OBJECTS_URL = f"{WEAVIATE_BASE}/v1/objects"


# ─── Config ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DriveTarget:
    doc_id: str
    title: str
    ratified_by: str
    ratified_at: str


def load_config(path: Path = _CONFIG_PATH) -> list[DriveTarget]:
    """Load drive_index_targets.json.  Raises ValueError on missing 'targets'."""
    raw = json.loads(path.read_text())
    if "targets" not in raw:
        raise ValueError(f"config missing 'targets' key: {path}")
    return [
        DriveTarget(
            doc_id=t["doc_id"],
            title=t["title"],
            ratified_by=t["ratified_by"],
            ratified_at=t["ratified_at"],
        )
        for t in raw["targets"]
    ]


# ─── Drive fetch (keiradrive MCP subprocess) ──────────────────────────────────
_MCP_BRIDGE = str(_REPO_ROOT / "skills" / "mcp-bridge" / "scripts" / "mcp-bridge.js")


def fetch_drive_doc(doc_id: str) -> dict[str, Any]:
    """Fetch doc via keiradrive MCP bridge subprocess.

    Returns dict with at minimum 'content' (markdown text) and
    'modifiedTime' (ISO-8601 string or empty).
    Raises RuntimeError on non-zero exit.
    """
    args_json = json.dumps({"fileId": doc_id})
    result = subprocess.run(
        ["node", _MCP_BRIDGE, "call", "keiradrive", "keiradrive_read_doc", args_json],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"keiradrive_read_doc failed for {doc_id}: {result.stderr[:500]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"keiradrive_read_doc non-JSON response for {doc_id}: {result.stdout[:200]}"
        ) from exc
    return data


# ─── Chunking ─────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DocChunk:
    section_title: str
    content: str


def chunk_by_heading(markdown: str) -> list[DocChunk]:
    """Split markdown by h1/h2/h3 boundaries.  Each heading → one chunk.

    Content before the first heading is emitted as a 'preamble' chunk
    only if non-empty.  Section title = heading text (stripped of #).
    """
    chunks: list[DocChunk] = []
    matches = list(_HEADING_RE.finditer(markdown))
    if not matches:
        stripped = markdown.strip()
        if stripped:
            chunks.append(DocChunk(section_title="(document)", content=stripped))
        return chunks

    preamble = markdown[: matches[0].start()].strip()
    if preamble:
        chunks.append(DocChunk(section_title="(preamble)", content=preamble))

    for i, m in enumerate(matches):
        section_title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        chunks.append(DocChunk(section_title=section_title, content=body))

    return chunks


# ─── UUID + object build ──────────────────────────────────────────────────────
def section_uuid(doc_id: str, section_title: str) -> str:
    """Deterministic UUID for (doc_id, section_title).  Stable across runs."""
    return deterministic_uuid(SOURCE_NAME, f"{doc_id}::{section_title}")


def build_weaviate_object(
    target: DriveTarget,
    chunk: DocChunk,
    updated_at: str,
) -> dict:
    obj_id = section_uuid(target.doc_id, chunk.section_title)
    return {
        "id": obj_id,
        "class": STRATEGIC_DOCS_CLASS,
        "properties": {
            "doc_id": target.doc_id,
            "doc_url": f"https://docs.google.com/document/d/{target.doc_id}",
            "title": target.title,
            "section": chunk.section_title,
            "content": chunk.content,
            "updated_at": updated_at or "1970-01-01T00:00:00Z",
            "ratified_by": target.ratified_by,
            "ratified_at": target.ratified_at + "T00:00:00Z",
        },
    }


# ─── CEO memory write ─────────────────────────────────────────────────────────
def write_ceo_memory(summary: dict[str, Any]) -> None:
    """Write indexer run summary to public.ceo_memory."""
    raw_dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not raw_dsn:
        logger.warning("no DATABASE_URL — skipping ceo_memory write")
        return
    dsn = raw_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        import psycopg  # noqa: PLC0415

        sql = (
            "INSERT INTO public.ceo_memory (key, value) "
            "VALUES ('ceo:memory:drive_indexer', %s::jsonb) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        )
        with psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as conn:
            conn.execute(sql, (json.dumps(summary),))
        logger.info("ceo_memory updated: ceo:memory:drive_indexer")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ceo_memory write failed (non-fatal): %s", exc)


# ─── Incremental state (modifiedTime cache) ───────────────────────────────────
_STATE_FILE = _REPO_ROOT / ".drive_indexer_state.json"


def load_modified_times() -> dict[str, str]:
    try:
        return json.loads(_STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_modified_times(state: dict[str, str]) -> None:
    _STATE_FILE.write_text(json.dumps(state, indent=2))


# ─── Core index function ──────────────────────────────────────────────────────
def index_target(
    target: DriveTarget,
    *,
    force: bool = False,
    modified_cache: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Fetch + chunk + upsert one target.  Returns per-doc outcome dict."""
    outcome: dict[str, Any] = {
        "doc_id": target.doc_id,
        "title": target.title,
        "skipped": False,
        "chunks_total": 0,
        "chunks_ok": 0,
        "chunks_failed": 0,
        "error": None,
    }
    try:
        doc_data = fetch_drive_doc(target.doc_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("fetch failed for %s (%s): %s", target.doc_id, target.title, exc)
        outcome["error"] = str(exc)
        return outcome

    modified_time = doc_data.get("modifiedTime", "") or doc_data.get("modified_time", "")

    if not force and modified_cache is not None:
        cached = modified_cache.get(target.doc_id)
        if cached and cached == modified_time:
            logger.info("skip %s — modifiedTime unchanged (%s)", target.title, modified_time)
            outcome["skipped"] = True
            return outcome

    content = doc_data.get("content", "") or doc_data.get("text", "")
    chunks = chunk_by_heading(content)
    outcome["chunks_total"] = len(chunks)

    for chunk in chunks:
        obj = build_weaviate_object(target, chunk, modified_time)
        if post_object(obj):
            outcome["chunks_ok"] += 1
        else:
            outcome["chunks_failed"] += 1
            logger.warning("upsert failed for %s :: %s", target.doc_id, chunk.section_title)

    if modified_cache is not None:
        modified_cache[target.doc_id] = modified_time

    logger.info(
        "indexed %s — chunks=%d ok=%d failed=%d",
        target.title,
        outcome["chunks_total"],
        outcome["chunks_ok"],
        outcome["chunks_failed"],
    )
    return outcome


# ─── Entrypoint ──────────────────────────────────────────────────────────────
def run(mode: str) -> None:
    targets = load_config()
    ensure_strategic_class()
    logger.info("drive_strategic_indexer start mode=%s targets=%d", mode, len(targets))

    force = mode == "full"
    modified_cache = load_modified_times()

    results: list[dict[str, Any]] = []
    for target in targets:
        results.append(index_target(target, force=force, modified_cache=modified_cache))

    save_modified_times(modified_cache)

    total_ok = sum(r["chunks_ok"] for r in results)
    total_failed = sum(r["chunks_failed"] for r in results)
    skipped = sum(1 for r in results if r.get("skipped"))
    errors = sum(1 for r in results if r.get("error"))

    summary = {
        "mode": mode,
        "docs": len(targets),
        "skipped": skipped,
        "errors": errors,
        "chunks_ok": total_ok,
        "chunks_failed": total_failed,
    }
    logger.info("run complete: %s", summary)
    write_ceo_memory(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Drive → Weaviate StrategicDocuments indexer")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="full=backfill all targets; incremental=only changed docs",
    )
    args = parser.parse_args()
    run(args.mode)


if __name__ == "__main__":
    main()
