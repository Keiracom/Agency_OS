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


# ─── Stream 2/3/4 SQL-backed loaders ────────────────────────────────────────
# Per Dave directive ts ~1778618600: Phase 1 corpus extension beyond .md files.
# Each loader emits (source_tag, chunk_content, node_set) tuples — same shape
# collect_chunks() outputs, so main() can just concat with file-derived chunks.


def _safe_sb_get(table: str, params: dict) -> list:
    """Best-effort sb_get wrapper. Returns [] on import failure or REST error
    (logged). The stream-loader is called inside the main() pre-flight, where
    a partial-source-failure should not abort the whole ingest."""
    try:
        from src.evo.supabase_client import sb_get
    except ImportError as exc:
        logger.warning("supabase_client import failed: %s", exc)
        return []
    try:
        return sb_get(table, params)
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("sb_get %s failed: %s", table, exc)
        return []


def _stream_2_chunks() -> list[tuple[str, str, list[str]]]:
    """Stream 2: Supabase memory tables (agent_memories + ceo_memory +
    governance_events + cis_directive_metrics). One chunk per row, tagged
    with table + per-row metadata in node_set."""
    out: list[tuple[str, str, list[str]]] = []

    # agent_memories — content + callsign + source_type
    for r in _safe_sb_get(
        "agent_memories",
        {
            "state": "eq.confirmed",
            "select": "id,callsign,source_type,content,typed_metadata",
            "order": "created_at.desc",
            "limit": "1000",
        },
    ):
        content = r.get("content") or ""
        if not content.strip():
            continue
        callsign = r.get("callsign", "unknown")
        source_type = r.get("source_type", "unknown")
        out.append(
            (
                "agent_memories",
                content,
                [
                    "source:agent_memories",
                    f"callsign:{callsign}",
                    f"type:{source_type}",
                    f"row:{r.get('id', '?')}",
                ],
            )
        )

    # ceo_memory — key + value (jsonb)
    import json as _json

    for r in _safe_sb_get("ceo_memory", {"select": "key,value", "limit": "500"}):
        key = r.get("key", "")
        value = r.get("value", "")
        if isinstance(value, (dict, list)):
            value_str = _json.dumps(value, default=str)
        else:
            value_str = str(value or "")
        if not value_str.strip():
            continue
        out.append(
            (
                "ceo_memory",
                f"[{key}]\n{value_str}",
                ["source:ceo_memory", f"key:{key}"],
            )
        )

    # governance_events — event log (best-effort; skip if table missing)
    for r in _safe_sb_get(
        "governance_events",
        {"select": "event_type,payload,created_at", "order": "created_at.desc", "limit": "200"},
    ):
        event_type = r.get("event_type", "unknown")
        payload = r.get("payload", "")
        if isinstance(payload, (dict, list)):
            payload_str = _json.dumps(payload, default=str)
        else:
            payload_str = str(payload or "")
        if not payload_str.strip():
            continue
        out.append(
            (
                "governance_events",
                f"[{event_type}]\n{payload_str}",
                ["source:governance_events", f"event_type:{event_type}"],
            )
        )

    # cis_directive_metrics — execution metrics
    for r in _safe_sb_get(
        "cis_directive_metrics",
        {"select": "directive_id,directive_ref,notes,callsign,agents_used", "limit": "500"},
    ):
        notes = r.get("notes") or ""
        if not notes.strip():
            continue
        directive_ref = r.get("directive_ref") or str(r.get("directive_id", "?"))
        out.append(
            (
                "cis_directive_metrics",
                f"[directive {directive_ref}]\n{notes}",
                [
                    "source:cis_directive_metrics",
                    f"directive_ref:{directive_ref}",
                    f"callsign:{r.get('callsign', '?')}",
                ],
            )
        )

    return out


def _stream_3_chunks() -> list[tuple[str, str, list[str]]]:
    """Stream 3: Drevon-port audit tables (sessions + turns + turn_logs).
    Chunk per row; turn_logs aggregates per-turn into one chunk to limit
    volume + keep semantic context together."""
    out: list[tuple[str, str, list[str]]] = []

    # sessions — one chunk per session row
    for r in _safe_sb_get(
        "sessions",
        {
            "deleted_at": "is.null",
            "select": "id,callsign,session_uuid,working_directory,started_at,ended_at,status",
            "order": "started_at.desc",
            "limit": "300",
        },
    ):
        content = (
            f"[session {r.get('id', '?')}] callsign={r.get('callsign', '?')} "
            f"status={r.get('status', '?')} cwd={r.get('working_directory', '?')} "
            f"started={r.get('started_at', '?')} ended={r.get('ended_at', '?')}"
        )
        out.append(
            (
                "sessions",
                content,
                [
                    "source:sessions",
                    f"callsign:{r.get('callsign', '?')}",
                    f"status:{r.get('status', '?')}",
                    f"row:{r.get('id', '?')}",
                ],
            )
        )

    # turns — one chunk per turn
    for r in _safe_sb_get(
        "turns",
        {
            "deleted_at": "is.null",
            "select": "id,session_id,turn_index,status,input_tokens,output_tokens,cost_aud",
            "order": "started_at.desc",
            "limit": "500",
        },
    ):
        content = (
            f"[turn {r.get('turn_index', '?')} of session {r.get('session_id', '?')}] "
            f"status={r.get('status', '?')} in_toks={r.get('input_tokens', '?')} "
            f"out_toks={r.get('output_tokens', '?')} cost_aud={r.get('cost_aud', '?')}"
        )
        out.append(
            (
                "turns",
                content,
                ["source:turns", f"session:{r.get('session_id', '?')}", f"row:{r.get('id', '?')}"],
            )
        )

    # turn_logs — per-row chunks; tool_args_json carries the meaningful content
    import json as _json

    for r in _safe_sb_get(
        "turn_logs",
        {
            "deleted_at": "is.null",
            "select": "id,turn_id,tool_name,tool_args_json,tool_result_summary,exit_status",
            "order": "started_at.desc",
            "limit": "500",
        },
    ):
        tool_name = r.get("tool_name", "?")
        tool_args = r.get("tool_args_json") or {}
        args_str = (
            _json.dumps(tool_args, default=str)
            if isinstance(tool_args, (dict, list))
            else str(tool_args)
        )
        summary = r.get("tool_result_summary") or ""
        exit_status = r.get("exit_status", "?")
        content = (
            f"[tool_call {tool_name} exit={exit_status}] "
            f"args={args_str[:500]} summary={summary[:300]}"
        )
        out.append(
            (
                "turn_logs",
                content,
                [
                    "source:turn_logs",
                    f"tool:{tool_name}",
                    f"exit:{exit_status}",
                    f"row:{r.get('id', '?')}",
                ],
            )
        )

    return out


def _stream_4_chunks() -> list[tuple[str, str, list[str]]]:
    """Stream 4: mem0-rescued subset of agent_memories (PR #770 tagged
    typed_metadata.node_set=['rescued','mem0_migration']).

    PostgREST JSONB contains-operator (cs) for the node_set tag.
    """
    out: list[tuple[str, str, list[str]]] = []

    for r in _safe_sb_get(
        "agent_memories",
        {
            "source_type": "eq.rescued_from_mem0",
            "select": "id,callsign,content,typed_metadata",
            "limit": "200",
        },
    ):
        content = r.get("content") or ""
        if not content.strip():
            continue
        meta = r.get("typed_metadata") or {}
        mem0_id = meta.get("mem0_id", "?") if isinstance(meta, dict) else "?"
        out.append(
            (
                "mem0_rescued",
                content,
                [
                    "source:mem0_rescued",
                    f"callsign:{r.get('callsign', '?')}",
                    f"mem0_id:{mem0_id}",
                    "rescued",
                    "mem0_migration",
                ],
            )
        )

    return out


def collect_stream_chunks(stream_id: int) -> list[tuple[str, str, list[str]]]:
    """Dispatch to the right loader. Stream 1 still uses _stream_1_sources +
    collect_chunks (file-backed); 2/3/4 use SQL loaders defined above."""
    if stream_id == 1:
        sources = _stream_1_sources()
        return collect_chunks(sources)
    if stream_id == 2:
        return _stream_2_chunks()
    if stream_id == 3:
        return _stream_3_chunks()
    if stream_id == 4:
        return _stream_4_chunks()
    logger.warning("unknown stream id: %d", stream_id)
    return []


def parse_streams(raw: str) -> list[int]:
    """'all' → [1,2,3,4]; comma-separated digits → subset; default [1]."""
    if not raw.strip():
        return [1]
    if raw.strip().lower() == "all":
        return [1, 2, 3, 4]
    out: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            n = int(token)
        except ValueError:
            logger.warning("--streams unknown token: %r (skipped)", token)
            continue
        if n in (1, 2, 3, 4):
            out.append(n)
        else:
            logger.warning("--streams unknown id: %d (skipped)", n)
    return out or [1]


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
    parser.add_argument(
        "--streams",
        default="1",
        help="comma-separated stream ids (1,2,3,4) or 'all'. Default: 1 (back-compat).",
    )
    args = parser.parse_args(argv)

    # --sources override forces stream 1 file-mode (existing back-compat).
    # Otherwise --streams selects which stream loaders to run + concat.
    if args.sources.strip():
        sources = parse_sources_override(args.sources)
        logger.info("--sources override: %d explicit paths", len(sources))
        chunks = collect_chunks(sources)
    else:
        stream_ids = parse_streams(args.streams)
        logger.info("ingesting streams: %s", stream_ids)
        chunks: list[tuple[str, str, list[str]]] = []
        for sid in stream_ids:
            if sid == 1:
                sources = _stream_1_sources()
                if args.include_aux_skills:
                    sources.extend(_aux_skill_sources())
                stream_chunks = collect_chunks(sources)
            else:
                stream_chunks = collect_stream_chunks(sid)
            logger.info("stream %d: %d chunks", sid, len(stream_chunks))
            chunks.extend(stream_chunks)
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
