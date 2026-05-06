"""
P9 — Context forking for sub-agent dispatches (OpenClaw research).

When the orchestrator dispatches a clone (atlas / orion / aiden / scout) or
spawns a sub-agent for a focused task, the dispatch brief is usually a single
paragraph of intent. The receiving agent has none of the working state the
parent built up — recent decisions, the current Step 0 RESTATE, the file
paths under active edit. P9 closes that gap.

Public surface
--------------
    build_forked_context(transcript_path, max_tokens=4000) -> str

Reads the parent session's .jsonl transcript, extracts:
  1. Current directive — the most-recent Step 0 RESTATE block if present
     (Objective / Scope / Success criteria / Assumptions)
  2. Last N user / assistant text turns (chronological, oldest-first)
  3. Active file list — paths surfaced by recent Read / Edit / Write /
     NotebookEdit tool_use blocks
Returns a single markdown string capped at ~max_tokens (~4 chars/token).
Empty string when transcript is missing / invalid — caller can decide
whether to proceed without forked context.

Security guards
---------------
Same posture as scripts/governance_hooks.py (P1):
  - No subprocess. Pure file IO against one validated path.
  - transcript_path MUST be: absolute, resolved, inside
    ~/.claude/projects/ , end with .jsonl. Anything else returns "".
  - Reject paths containing '://' / '..' / null bytes.
  - Read at most TRANSCRIPT_TAIL_BYTES (default 256KB) from EOF.
  - tool_use input fields read as plain strings; never executed.
  - Module entry-point catches every Exception and returns "" so a
    bug here cannot block the dispatch.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[context-fork] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects"
TRANSCRIPT_TAIL_BYTES = 256 * 1024
PATH_DENY_SUBSTRINGS = ("://", "..", "\x00")
_URL_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)

# Approx 4 chars per token — used to cap the rendered brief.
CHARS_PER_TOKEN = 4

# Recent-turn ceiling. We always include the Step 0 + active file list, then
# fill the remaining char budget with the latest N text turns.
DEFAULT_MAX_RECENT_TURNS = 12

# Tool names whose input.file_path / input.path / input.notebook_path we
# treat as "active files" for the forked context.
_FILE_TOOLS = {"Read", "Edit", "Write", "NotebookEdit", "Glob", "Grep"}

STEP0_MARKERS = ("objective:", "scope:", "success criteria:", "assumptions:")


# ── Data shapes ────────────────────────────────────────────────────────────


@dataclass
class ForkedContext:
    step0_block: str | None = None
    recent_turns: list[tuple[str, str]] = field(default_factory=list)
    active_files: list[str] = field(default_factory=list)


# ── Validation (same posture as governance_hooks) ──────────────────────────


def _validate_transcript_path(raw: str | None) -> Path | None:
    if not raw or not isinstance(raw, str):
        return None
    if any(s in raw for s in PATH_DENY_SUBSTRINGS):
        return None
    if _URL_RE.match(raw):
        return None
    try:
        p = Path(raw).resolve(strict=False)
    except OSError:
        return None
    if not p.is_absolute() or not str(p).endswith(".jsonl"):
        return None
    try:
        p.relative_to(TRANSCRIPT_ROOT.resolve())
    except ValueError:
        return None
    if not p.exists() or not p.is_file():
        return None
    return p


def _read_tail(path: Path) -> str:
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            if size > TRANSCRIPT_TAIL_BYTES:
                f.seek(size - TRANSCRIPT_TAIL_BYTES)
                _ = f.readline()  # drop the partial first line
            return f.read().decode("utf-8", errors="replace")
    except OSError as exc:
        logger.warning("transcript read failed: %s", exc)
        return ""


def _iter_jsonl(blob: str):
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


# ── Extraction helpers ─────────────────────────────────────────────────────


def _record_text(rec: dict) -> str:
    """Best-effort flatten of a transcript record → searchable text."""
    parts: list[str] = []
    msg = rec.get("message") or rec
    content = msg.get("content")
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                t = block.get("text")
                if isinstance(t, str):
                    parts.append(t)
    text = msg.get("text")
    if isinstance(text, str):
        parts.append(text)
    return "\n".join(parts).strip()


def _record_role(rec: dict) -> str | None:
    msg = rec.get("message") or {}
    return msg.get("role") or rec.get("role") or rec.get("type")


def _record_tool_files(rec: dict) -> list[str]:
    """Extract file paths from tool_use blocks (Read/Edit/Write/NotebookEdit/
    Glob/Grep). Returns plain strings — never executed, never resolved."""
    out: list[str] = []
    msg = rec.get("message") or rec
    content = msg.get("content")
    if not isinstance(content, list):
        return out
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "tool_use":
            continue
        if block.get("name") not in _FILE_TOOLS:
            continue
        tool_input = block.get("input") or {}
        if not isinstance(tool_input, dict):
            continue
        for key in ("file_path", "path", "notebook_path"):
            v = tool_input.get(key)
            if isinstance(v, str) and v:
                out.append(v)
        # Glob / Grep also surface 'pattern' but we only want concrete files.
    return out


def _extract_step0(text: str) -> str | None:
    """Return the Step 0 RESTATE block if ≥ 3 markers present, else None."""
    lower = text.lower()
    hits = sum(1 for m in STEP0_MARKERS if m in lower)
    if hits < 3:
        return None
    # Trim to the smallest window that contains all markers.
    first = min(lower.find(m) for m in STEP0_MARKERS if m in lower)
    return text[first:].strip()


# ── Pure transform ─────────────────────────────────────────────────────────


def extract_context(blob: str, max_recent_turns: int = DEFAULT_MAX_RECENT_TURNS) -> ForkedContext:
    """Walk the transcript blob oldest→newest, build a ForkedContext."""
    ctx = ForkedContext()
    recent: list[tuple[str, str]] = []
    files_ordered: list[str] = []
    files_seen: set[str] = set()
    last_step0: str | None = None

    for rec in _iter_jsonl(blob):
        role = _record_role(rec)
        text = _record_text(rec)

        if role == "user":
            recent.append(("user", text))
        elif role in ("assistant", "model"):
            if text:
                recent.append(("assistant", text))
                step0 = _extract_step0(text)
                if step0:
                    last_step0 = step0
            for fp in _record_tool_files(rec):
                if fp not in files_seen:
                    files_seen.add(fp)
                    files_ordered.append(fp)

    ctx.step0_block = last_step0
    ctx.recent_turns = recent[-max_recent_turns:] if max_recent_turns > 0 else []
    ctx.active_files = files_ordered[-25:]  # bound the file list too
    return ctx


# ── Render ─────────────────────────────────────────────────────────────────


def _truncate_to_chars(s: str, char_budget: int) -> str:
    if len(s) <= char_budget:
        return s
    return s[: char_budget - 50] + "\n…[truncated to fit token budget]…"


def render_brief(ctx: ForkedContext, max_tokens: int) -> str:
    """Markdown render — Step 0 first, then active files, then recent turns.
    Truncates to ~max_tokens (CHARS_PER_TOKEN heuristic)."""
    char_budget = max(200, max_tokens * CHARS_PER_TOKEN)
    parts: list[str] = ["# Forked context (parent session)\n"]

    # 1. Current directive scope
    parts.append("## Current directive (Step 0)")
    if ctx.step0_block:
        parts.append(ctx.step0_block)
    else:
        parts.append("_No Step 0 RESTATE found in recent turns._")
    parts.append("")

    # 2. Active files
    parts.append("## Active files (recent tool surface)")
    if ctx.active_files:
        for fp in ctx.active_files:
            parts.append(f"- `{fp}`")
    else:
        parts.append("_No file-touching tool calls in recent turns._")
    parts.append("")

    # 3. Recent turns
    parts.append(f"## Recent turns (last {len(ctx.recent_turns)})")
    if ctx.recent_turns:
        for role, text in ctx.recent_turns:
            tag = "USER" if role == "user" else "ASSISTANT"
            parts.append(f"### {tag}")
            parts.append(text)
            parts.append("")
    else:
        parts.append("_No recent text turns in transcript window._")

    rendered = "\n".join(parts)
    return _truncate_to_chars(rendered, char_budget)


# ── Public API ─────────────────────────────────────────────────────────────


def build_forked_context(transcript_path: str | Path, max_tokens: int = 4000) -> str:
    """Read a parent session transcript and produce a markdown brief
    (Step 0 + active files + recent turns) to seed a sub-agent dispatch.

    Returns "" on any validation / IO failure so the caller can decide
    whether to proceed without forked context. NEVER raises."""
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        logger.warning("build_forked_context: invalid max_tokens %r", max_tokens)
        return ""

    raw = str(transcript_path) if transcript_path is not None else None
    p = _validate_transcript_path(raw)
    if p is None:
        logger.warning("build_forked_context: transcript path rejected: %r", raw)
        return ""

    blob = _read_tail(p)
    if not blob:
        return ""

    try:
        ctx = extract_context(blob)
        return render_brief(ctx, max_tokens=max_tokens)
    except Exception as exc:  # noqa: BLE001
        logger.warning("build_forked_context: extraction failed (fail-empty): %s", exc)
        return ""


# ── CLI for ad-hoc inspection ──────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P9 context forking — inspect a parent transcript.")
    ap.add_argument("transcript", help="Path to a .jsonl transcript inside ~/.claude/projects/")
    ap.add_argument("--max-tokens", type=int, default=4000)
    args = ap.parse_args(argv)
    out = build_forked_context(args.transcript, max_tokens=args.max_tokens)
    if not out:
        print("(no context — see stderr for reason)", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        logger.exception("CLI crashed (fail-open): %s", exc)
        sys.exit(0)
