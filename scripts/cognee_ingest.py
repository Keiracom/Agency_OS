#!/usr/bin/env python3
"""cognee_ingest.py — Stream 1 batch ingestion of Agency OS canonical files.

Phase 1 dispatch (Max, per Elliot ts 1778562982 / ts 1778565xxx source-list
confirm, Dave umbrella ts 1778562801). Sole Cognee call surface:
`src.cognee.client.{add, cognify}` (Aiden Phase 0 wrapper, PR #764). Direct
cognee SDK imports outside that wrapper are forbidden.

Stream 1 covers .md files only:
    docs/MANUAL.md                            (CEO SSOT, manual)
    ARCHITECTURE.md                           (system architecture)
    DEFINITION_OF_DONE.md                     (governance acceptance criteria)
    .claude/modules/*.md                      (canonical CLAUDE.md modules — main worktree only, lockstep)
    skills/*/SKILL.md                         (one per skill, 15 expected)
    .../Agency_OS-{callsign}/IDENTITY.md      (per-worktree, tagged agent_id)
    .../Agency_OS-{callsign}/HEARTBEAT.md     (per-worktree, tagged agent_id)

Streams 2/3/4 (SQL tables, cloud APIs, file paths beyond .md) deferred to
follow-up PRs — different ingest shapes; not in this PR's scope.

Usage:
    cognee_ingest.py [--sources path1,path2,...] [--include-aux-skills]
                     [--dry-run] [--org-id ID] [--app-id ID] [--agent-id ID]
                     [--skip-cognify]

    --sources: comma-separated explicit paths (overrides STREAM_1_SOURCES default)
    --include-aux-skills: also ingest skills/**/*.md beyond just SKILL.md
                          (off by default — auxiliary skill docs skew the graph)
    --dry-run: print what would be ingested; do not call add() or cognify()
    --org-id: default 'keiracom_platform'
    --app-id: default 'agency_os'
    --agent-id: default 'max' — tagged on every chunk (override per ingest run)
    --skip-cognify: don't call cognify() at the end

Missing-on-disk sources log to stderr + skip (idempotent; directive expects
tolerant). Exit codes: 0 ok or dry-run, 1 partial failure, 2 fatal.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("cognee_ingest")

DEFAULT_ORG = "keiracom_platform"
DEFAULT_APP = "agency_os"
DEFAULT_AGENT = "max"
CHUNK_CHAR_CAP = 4000

# Per Orion's filesystem audit (PR #758) — clawd root contains six worktrees.
# Each has its own IDENTITY.md + HEARTBEAT.md tagged with that callsign so
# the graph distinguishes per-agent identity / continuation state.
CLAWD_ROOT = REPO_ROOT.parent  # /home/elliotbot/clawd
WORKTREES: dict[str, Path] = {
    "elliot": CLAWD_ROOT / "Agency_OS",
    "aiden": CLAWD_ROOT / "Agency_OS-aiden",
    "max": CLAWD_ROOT / "Agency_OS-max",
    "atlas": CLAWD_ROOT / "Agency_OS-atlas",
    "orion": CLAWD_ROOT / "Agency_OS-orion",
    "scout": CLAWD_ROOT / "Agency_OS-scout",
}


def _stream_1_sources() -> list[tuple[Path, str, list[str]]]:
    """Return [(path, source_tag, extra_node_set), ...] for the default ingest.

    extra_node_set is per-file metadata (file:..., agent:... for worktrees).
    """
    out: list[tuple[Path, str, list[str]]] = []

    # Top-level governance + architecture docs (main worktree)
    for name, tag in (
        ("docs/MANUAL.md", "manual"),
        ("ARCHITECTURE.md", "architecture"),
        ("DEFINITION_OF_DONE.md", "dod"),
    ):
        out.append((REPO_ROOT / name, tag, [f"file:{name}"]))

    # CLAUDE.md modules — lockstep across worktrees, ingest from main only
    modules_dir = REPO_ROOT / ".claude" / "modules"
    if modules_dir.is_dir():
        for path in sorted(modules_dir.glob("*.md")):
            out.append((path, "claude_modules", [f"file:.claude/modules/{path.name}"]))

    # Skills — by default just SKILL.md (one per skill)
    skills_dir = REPO_ROOT / "skills"
    if skills_dir.is_dir():
        for path in sorted(skills_dir.glob("*/SKILL.md")):
            skill_name = path.parent.name
            out.append(
                (path, "skill", [f"skill:{skill_name}", f"file:skills/{skill_name}/SKILL.md"])
            )

    # Per-worktree IDENTITY.md + HEARTBEAT.md, tagged with worktree's callsign
    for callsign, root in WORKTREES.items():
        for filename, tag in (("IDENTITY.md", "identity"), ("HEARTBEAT.md", "heartbeat")):
            out.append((root / filename, tag, [f"agent:{callsign}", f"worktree:{callsign}"]))

    return out


def _aux_skill_sources() -> list[tuple[Path, str, list[str]]]:
    """Auxiliary skill docs (READMEs, examples, supplements) — opt-in via flag."""
    out: list[tuple[Path, str, list[str]]] = []
    skills_dir = REPO_ROOT / "skills"
    if skills_dir.is_dir():
        for path in sorted(skills_dir.rglob("*.md")):
            if path.name == "SKILL.md":
                continue
            try:
                rel = path.relative_to(REPO_ROOT)
            except ValueError:
                continue
            skill_name = path.parts[len(REPO_ROOT.parts)]  # 'skills', then subdir
            out.append((path, "skill_aux", [f"skill:{skill_name}", f"file:{rel}"]))
    return out


def _split_markdown(text: str, max_chars: int = CHUNK_CHAR_CAP) -> list[str]:
    """Split markdown into ~max_chars chunks at ## boundaries; falls back to fixed-size."""
    sections: list[str] = []
    buf: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("## ") and buf:
            sections.append("".join(buf))
            buf = [line]
        else:
            buf.append(line)
    if buf:
        sections.append("".join(buf))

    out: list[str] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= max_chars:
            out.append(section)
        else:
            for i in range(0, len(section), max_chars):
                piece = section[i : i + max_chars].strip()
                if piece:
                    out.append(piece)
    return out


def load_file_chunks(
    path: Path, source_tag: str, extra_node_set: list[str]
) -> list[tuple[str, str, list[str]]]:
    """Return [(source_tag, chunk, node_set), ...] for one file. Missing → []."""
    if not path.exists():
        logger.warning("source file missing: %s (skipped)", path)
        return []
    try:
        text = path.read_text()
    except OSError as exc:
        logger.warning("read failed for %s: %s", path, exc)
        return []
    return [
        (source_tag, chunk, [f"source:{source_tag}", *extra_node_set])
        for chunk in _split_markdown(text)
    ]


def collect_chunks(
    sources: Iterable[tuple[Path, str, list[str]]],
) -> list[tuple[str, str, list[str]]]:
    """Walk sources, return [(source_tag, chunk, node_set), ...]."""
    chunks: list[tuple[str, str, list[str]]] = []
    for path, source_tag, extra in sources:
        chunks.extend(load_file_chunks(path, source_tag, extra))
    return chunks


def parse_sources_override(raw: str) -> list[tuple[Path, str, list[str]]]:
    """`--sources` value to (path, tag, extras) triples. Tag = 'override:<filename>'."""
    out: list[tuple[Path, str, list[str]]] = []
    for raw_path in (p.strip() for p in raw.split(",") if p.strip()):
        path = Path(raw_path)
        if not path.is_absolute():
            path = REPO_ROOT / path
        out.append((path, "override", [f"file:{path.name}"]))
    return out


async def ingest(
    chunks: list[tuple[str, str, list[str]]],
    *,
    org_id: str,
    app_id: str,
    agent_id: str,
    dry_run: bool,
    skip_cognify: bool,
) -> tuple[int, int]:
    """Run add() per chunk; cognify() once at end. Returns (ok, fail)."""
    if dry_run:
        for source_tag, chunk, node_set in chunks:
            logger.info(
                "[DRY-RUN] would add %s chunk (%d chars, node_set=%s)",
                source_tag,
                len(chunk),
                node_set,
            )
        return len(chunks), 0

    try:
        from src.cognee.client import add, cognify
    except ImportError as exc:
        logger.error("cognee.client import failed: %s — Phase 0 not live?", exc)
        return 0, len(chunks)

    ok, fail = 0, 0
    for source_tag, chunk, node_set in chunks:
        try:
            await add(
                chunk,
                org_id=org_id,
                app_id=app_id,
                agent_id=agent_id,
                node_set=node_set,
            )
            ok += 1
        except Exception as exc:  # noqa: BLE001 — best-effort per chunk
            logger.warning("add() failed for %s chunk: %s", source_tag, exc)
            fail += 1

    if ok > 0 and not skip_cognify:
        try:
            await cognify()
            logger.info("cognify() complete")
        except Exception as exc:  # noqa: BLE001
            logger.warning("cognify() failed: %s", exc)
            fail += 1

    return ok, fail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        default="",
        help="comma-separated explicit paths (overrides STREAM_1_SOURCES default)",
    )
    parser.add_argument(
        "--include-aux-skills",
        action="store_true",
        help="ingest skills/**/*.md beyond SKILL.md (off — keeps graph signal high)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--org-id", default=DEFAULT_ORG)
    parser.add_argument("--app-id", default=DEFAULT_APP)
    parser.add_argument("--agent-id", default=DEFAULT_AGENT)
    parser.add_argument("--skip-cognify", action="store_true")
    args = parser.parse_args(argv)

    if args.sources.strip():
        sources = parse_sources_override(args.sources)
        logger.info("--sources override: %d explicit paths", len(sources))
    else:
        sources = _stream_1_sources()
        if args.include_aux_skills:
            sources.extend(_aux_skill_sources())
        logger.info(
            "STREAM_1_SOURCES default: %d files%s",
            len(sources),
            " (+ aux skills)" if args.include_aux_skills else "",
        )

    chunks = collect_chunks(sources)
    if not chunks:
        logger.warning("no chunks collected — nothing to ingest")
        return 1

    logger.info(
        "collected %d chunks (org=%s app=%s agent=%s)",
        len(chunks),
        args.org_id,
        args.app_id,
        args.agent_id,
    )

    ok, fail = asyncio.run(
        ingest(
            chunks,
            org_id=args.org_id,
            app_id=args.app_id,
            agent_id=args.agent_id,
            dry_run=args.dry_run,
            skip_cognify=args.skip_cognify,
        )
    )
    logger.info("done: %d ok / %d failed", ok, fail)
    # Better Stack heartbeat (GOV-9 C resolution from PR-B #786): cognee
    # service runs on localhost so external HTTP monitoring isn't viable;
    # we observe successful ingest runs via heartbeat instead. Skip on
    # dry-run + on any failure so the monitor only ticks on clean success.
    if not args.dry_run and fail == 0 and ok > 0:
        _heartbeat()
    return 0 if fail == 0 else 1


def _heartbeat() -> None:
    """Better Stack heartbeat ping — best-effort, env-var-gated.

    Sent as the LAST step of main() on clean success only (no dry-run, no
    failures). Mirrors the pattern in elliot_polling_loop.py::_heartbeat.
    Missing env → skip; subprocess failure → log + drop. Never raises.
    """
    url = os.environ.get("BETTERSTACK_HB_COGNEE_PHASE1_INGEST", "")
    if not url:
        return
    try:
        subprocess.run(
            ["curl", "-fsS", "-m", "5", url],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("BetterStack heartbeat ping failed: %s", exc)


if __name__ == "__main__":
    sys.exit(main())
