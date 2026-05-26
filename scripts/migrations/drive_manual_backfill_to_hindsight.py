#!/usr/bin/env python3
"""drive_manual_backfill_to_hindsight.py — Phase A5 piece 3.

Ingests Drive Manual content (Agency OS Manual + Keiracom Manual) into
Hindsight under Dave's fleet tenant_id via DecisionWrapper. Per Path (C)
dual-store resolution + ceo:dave_decisions_2026_05_26 decision_1 A5 scope.

Input shape: one or more local text files containing the Drive Manual
content. Operator pre-exports Drive docs to local files via either:
- `skills/drive-manual/write_manual.py` reverse mirror (Drive → local)
- Drive UI "File → Download → Plain Text" export
- Existing `docs/MANUAL.md` repo mirror (LAW XV three-store target)

File-input mode keeps this script dependency-free (no google-api-python-client
needed at runtime) and follows the same shape as piece 1b consuming the
piece 1a classification JSONL.

Chunking: each input file is split on markdown `## ` section headings;
each section becomes one Hindsight memory so recall granularity matches
section identity. Files with no `## ` headings ingest as a single chunk.

bd: Agency_OS-ushm
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("drive_manual_backfill_to_hindsight")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from keiracom_system.fleet.hindsight.smoke_wrappers import (  # noqa: E402
    FLEET_TENANT_ID,
    FleetHindsightClient,
    FleetTenantExtension,
)
from src.keiracom_system.memory.wrappers import DecisionWrapper  # noqa: E402

DEFAULT_STATE_FILE = Path("runtime/a5_piece_3_drive_manual_state.jsonl")
SECTION_HEADING_PATTERN = re.compile(r"^## (?P<title>.+)$", re.MULTILINE)


def chunk_by_section(text: str) -> list[dict[str, Any]]:
    """Split markdown text on `## ` headings.

    Returns list of {"heading": str, "body": str, "index": int}.
    Files with no `## ` headings return a single whole-file chunk with
    heading=None.
    """
    matches = list(SECTION_HEADING_PATTERN.finditer(text))
    if not matches:
        return [{"heading": None, "body": text.strip(), "index": 0}]
    chunks: list[dict[str, Any]] = []
    # Preamble before the first heading (if any non-empty)
    preamble = text[: matches[0].start()].strip()
    if preamble:
        chunks.append({"heading": None, "body": preamble, "index": 0})
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        chunks.append({"heading": m.group("title").strip(), "body": body, "index": len(chunks)})
    return chunks


def build_external_id(file_path: Path, chunk_index: int) -> str:
    return f"{file_path}#{chunk_index}"


def build_metadata(file_path: Path, chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "a5_piece_3_drive_manual_backfill",
        "source_file": str(file_path),
        "chunk_index": chunk["index"],
        "chunk_heading": chunk["heading"] or "",
        "external_id": build_external_id(file_path, chunk["index"]),
    }


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if entry.get("ok") and entry.get("external_id"):
                seen.add(entry["external_id"])
        except json.JSONDecodeError:
            continue
    return seen


def append_state(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")


def ingest_chunk(
    file_path: Path,
    chunk: dict[str, Any],
    *,
    decision_wrapper: DecisionWrapper,
) -> tuple[bool, str]:
    metadata = build_metadata(file_path, chunk)
    try:
        resp = decision_wrapper.ingest(
            tenant_id=FLEET_TENANT_ID,
            content=chunk["body"],
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"exception: {type(exc).__name__}: {exc}"
    if isinstance(resp, dict) and "error" in resp:
        return False, f"hindsight_error: {str(resp)[:200]}"
    return True, str(resp)[:120]


def run(
    *,
    input_files: list[Path],
    execute: bool,
    state_path: Path,
    wrapper_factory: Any | None = None,
) -> int:
    missing = [p for p in input_files if not p.exists()]
    if missing:
        for p in missing:
            logger.error("input file not found: %s", p)
        return 2
    if not input_files:
        logger.error("no input files provided")
        return 2
    seen = load_state(state_path)
    wrapper = (
        (
            wrapper_factory
            or (lambda: DecisionWrapper(FleetHindsightClient(), FleetTenantExtension()))
        )()
        if execute
        else None
    )
    n_total = n_ok = n_fail = n_skip = 0
    for file_path in input_files:
        text = file_path.read_text(encoding="utf-8")
        chunks = chunk_by_section(text)
        logger.info("file=%s chunks=%d", file_path, len(chunks))
        for chunk in chunks:
            n_total += 1
            ext_id = build_external_id(file_path, chunk["index"])
            if ext_id in seen:
                n_skip += 1
                continue
            if not execute:
                logger.info(
                    "dry-run: would ingest %s heading=%r",
                    ext_id,
                    chunk["heading"],
                )
                continue
            ok, info = ingest_chunk(file_path, chunk, decision_wrapper=wrapper)
            entry = {"external_id": ext_id, "ok": ok, "info": info}
            append_state(state_path, entry)
            if ok:
                n_ok += 1
            else:
                n_fail += 1
                logger.warning("ingest %s FAILED: %s", ext_id, info)
    logger.info(
        "summary: total=%d ok=%d fail=%d skip=%d (execute=%s)",
        n_total,
        n_ok,
        n_fail,
        n_skip,
        execute,
    )
    return 0 if n_fail == 0 else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input", action="append", type=Path, required=True, help="local file path (repeatable)"
    )
    p.add_argument("--execute", action="store_true", help="write to Hindsight (default: dry-run)")
    p.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    return run(input_files=args.input, execute=args.execute, state_path=args.state_file)


if __name__ == "__main__":
    sys.exit(main())
