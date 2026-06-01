#!/usr/bin/env python3
"""roadmap_status.py — render the V2 roadmap STATUS block from public.gate_roadmap.

Dave directive 2026-05-31. Renders the current per-component status table that
gets stitched into docs/ROADMAP_V2.md between the STATUS_BLOCK_START/END markers.

CLI:
  python3 scripts/roadmap_status.py --render   # stdout: markdown table
  python3 scripts/roadmap_status.py --write    # rewrites STATUS block in ROADMAP_V2.md

Failure modes:
  - DB unreachable / query fails: emit `<!-- STATUS_BLOCK_UNAVAILABLE: <reason> -->`
    between the markers (write) or to stdout (render). Exit 0 ALWAYS so the
    auto-commit step in CI never breaks the build.
  - Markers missing in target file: exit 0, print a warning to stderr, no write.

Env:
  DATABASE_URL or SUPABASE_DB_DSN — Postgres DSN. Tried in that order.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROADMAP_PATH = REPO_ROOT / "docs" / "ROADMAP_V2.md"

STATUS_BLOCK_START = "<!-- STATUS_BLOCK_START -->"
STATUS_BLOCK_END = "<!-- STATUS_BLOCK_END -->"

STATUS_EMOJI = {
    "not_started": "⬜",
    "built": "🔨",
    "proven": "✅",
    "skipped": "⏭",
    "deferred": "⏸",
}

QUERY = """
SELECT component, phase, subphase, proof_gate, status, owner,
       kei_link, blocker_text, last_verified
  FROM public.gate_roadmap
 ORDER BY phase, component
"""


def _dsn() -> str | None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_DSN") or None
    if not raw:
        return None
    # Strip async driver tag — psycopg sync can't parse `postgresql+asyncpg://`.
    # Mirrors scripts/tasks_cli.py _dsn() so the env vars are interchangeable.
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def _fmt_status(status: str | None) -> str:
    if not status:
        return "—"
    return f"{STATUS_EMOJI.get(status, '?')} {status}"


def _fmt_last_verified(value) -> str:
    if value is None:
        return "—"
    s = str(value)
    return s.split(".")[0].replace("T", " ")[:19] if "T" in s or " " in s else s


def _fmt_kei(kei_link: str | None) -> str:
    if not kei_link:
        return "—"
    return f"[{kei_link}]({kei_link})" if kei_link.startswith("http") else kei_link


def _fmt_phase(phase: str | None, subphase: str | None) -> str:
    if phase and subphase:
        return f"{phase} / {subphase}"
    return phase or "—"


def _render_table(rows: list[tuple]) -> str:
    if not rows:
        return "_No gate_roadmap rows yet — populated as components ship._"
    header = "| Component | Phase | Status | Owner | Last Verified | Gate |"
    sep = "| --- | --- | --- | --- | --- | --- |"
    lines = [header, sep]
    for (
        component,
        phase,
        subphase,
        proof_gate,
        status,
        owner,
        kei_link,
        _blocker,
        last_verified,
    ) in rows:
        lines.append(
            f"| {component or '—'} "
            f"| {_fmt_phase(phase, subphase)} "
            f"| {_fmt_status(status)} "
            f"| {owner or '—'} "
            f"| {_fmt_last_verified(last_verified)} "
            f"| {proof_gate or _fmt_kei(kei_link)} |"
        )
    return "\n".join(lines)


def _fetch_rows() -> tuple[list[tuple] | None, str | None]:
    """Returns (rows, error_message). On success error_message is None."""
    dsn = _dsn()
    if not dsn:
        return None, "DATABASE_URL / SUPABASE_DB_DSN not set"
    try:
        import psycopg
    except ImportError as exc:
        return None, f"psycopg import failed: {exc}"
    try:
        with psycopg.connect(dsn, connect_timeout=10) as conn, conn.cursor() as cur:
            cur.execute(QUERY)
            return list(cur.fetchall()), None
    except Exception as exc:  # broad: any DB error → unavailable stub
        return None, f"{type(exc).__name__}: {exc}"


def render() -> str:
    rows, err = _fetch_rows()
    if err is not None:
        return f"<!-- STATUS_BLOCK_UNAVAILABLE: {err} -->"
    return _render_table(rows or [])


def _replace_block(text: str, new_inner: str) -> tuple[str, bool]:
    """Return (new_text, replaced?). replaced=False when markers missing."""
    pattern = re.compile(
        re.escape(STATUS_BLOCK_START) + r".*?" + re.escape(STATUS_BLOCK_END),
        re.DOTALL,
    )
    if not pattern.search(text):
        return text, False
    replacement = f"{STATUS_BLOCK_START}\n{new_inner}\n{STATUS_BLOCK_END}"
    return pattern.sub(replacement, text, count=1), True


def write_to_roadmap(path: Path | None = None) -> int:
    if path is None:
        # Look up at call time so tests can monkeypatch mod.ROADMAP_PATH.
        path = ROADMAP_PATH
    if not path.exists():
        print(f"WARN: {path} does not exist — nothing to write.", file=sys.stderr)
        return 0
    body = render()
    text = path.read_text(encoding="utf-8")
    new_text, replaced = _replace_block(text, body)
    if not replaced:
        print(
            f"WARN: STATUS_BLOCK markers not found in {path} — nothing to write.",
            file=sys.stderr,
        )
        return 0
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="print table to stdout")
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite the STATUS block in docs/ROADMAP_V2.md",
    )
    args = parser.parse_args(argv)
    if not (args.render or args.write):
        parser.print_help(sys.stderr)
        return 0
    try:
        if args.render:
            print(render())
        if args.write:
            return write_to_roadmap()
    except Exception as exc:
        # LAST-RESORT guard: renderer failure must NEVER break CI.
        print(f"<!-- STATUS_BLOCK_UNAVAILABLE: renderer crashed: {exc} -->", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
