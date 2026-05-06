"""
P1 — Governance hook: Step 0 RESTATE runtime gate (OpenClaw research).

PreToolUse hook wired in .claude/settings.json. Reads PreToolUse stdin
JSON from Claude Code, inspects the in-flight transcript for a Step 0
RESTATE block since the most recent USER message, and:

  - mode='enforce' (default): blocks mutating tools (Write / Edit /
    NotebookEdit) when no Step 0 is found by exiting 2 with a
    human-readable reason on stderr — Claude Code surfaces that as
    a tool-call failure so the assistant can self-correct.
  - mode='warn': always exit 0; log the missing-Step-0 warning to
    stderr so it appears in transcripts but never blocks execution.
    Use this during rollout / per-session debugging.

Environment knobs:
  GOV_HOOK_MODE        enforce | warn   (default 'enforce')
  GOV_HOOK_LOG         path to extra log file (default unset → stderr only)

# ── SECURITY GUARDS (per OpenClaw research note) ──────────────────────────
# This file is the trusted boundary between Claude Code and the rest of
# the dev environment. ANY unsafe input handling here would let a
# crafted hook payload escalate to arbitrary code execution. Hard rules:
#
#   1. NO subprocess / shell calls. Period. The hook does pure file IO
#      against a single transcript path validated against an allow-list.
#   2. NO URL following. transcript_path is the only path we read; any
#      string that looks like a URL (http://, https://, file://) is
#      rejected at parse time.
#   3. transcript_path must be:
#        - absolute
#        - resolved (no '..' / symlinks resolved away)
#        - inside ~/.claude/projects/  (Claude Code's canonical store)
#        - end with .jsonl
#      Any failure → log and allow (fail-open) so a malformed payload
#      can't block legitimate edits.
#   4. Read at most TRANSCRIPT_TAIL_BYTES (default 256 KB) from the
#      END of the transcript file. Never load arbitrary-size content.
#   5. tool_name is matched against a closed enum; never used as a
#      shell argument or path component.
#   6. Hook ALWAYS handles exceptions and falls open (exit 0) on
#      unexpected errors so a hook bug can't paralyse the user's
#      session. Enforcement only fires on the well-defined
#      "Step 0 missing AND mutating tool" path.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

# Ensure the repo root is importable so `src.config.sandbox` resolves
# whether the hook is invoked via `python3 scripts/governance_hooks.py`
# or as a Claude Code PreToolUse spawn (cwd may not be on sys.path).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from src.config.sandbox import validate_tool_access  # P6 wire-up
except Exception:  # noqa: BLE001 — fail-open if module missing

    def validate_tool_access(_agent: str, _tool: str) -> bool:
        return True


logging.basicConfig(
    level=logging.INFO,
    format="[gov-hook] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
MUTATING_TOOLS = frozenset({"Write", "Edit", "NotebookEdit"})

# Step 0 markers per CLAUDE.md §LAW XV-D. We require ≥ MIN_MARKERS_PRESENT
# of the four labelled bullets to be present in the most-recent assistant
# turn(s) to count as a valid Step 0.
STEP0_MARKERS = ("objective:", "scope:", "success criteria:", "assumptions:")
MIN_MARKERS_PRESENT = 3

TRANSCRIPT_TAIL_BYTES = 256 * 1024  # safety cap on transcript reads
TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects"

# Reject any path containing these substrings (URL-ish patterns + traversal).
PATH_DENY_SUBSTRINGS = ("://", "..", "\x00")

# Block on these stdin keys if they ever look like URLs (defence in depth).
_URL_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)


# ── Validation ─────────────────────────────────────────────────────────────


def validate_transcript_path(raw: str | None) -> Path | None:
    """Return a safe Path or None. Never raises."""
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
    if not p.is_absolute():
        return None
    if not str(p).endswith(".jsonl"):
        return None
    try:
        # Constrain to Claude Code's transcript store.
        p.relative_to(TRANSCRIPT_ROOT.resolve())
    except ValueError:
        return None
    if not p.exists() or not p.is_file():
        return None
    return p


def read_hook_input() -> dict:
    """Parse the hook's stdin JSON. Returns {} on any failure."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not parse hook input: %s", exc)
        return {}


# ── Transcript inspection ──────────────────────────────────────────────────


def read_transcript_tail(path: Path) -> str:
    """Read up to TRANSCRIPT_TAIL_BYTES from the END of a .jsonl transcript.
    Pure file IO; no shell, no subprocess."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            if size > TRANSCRIPT_TAIL_BYTES:
                f.seek(size - TRANSCRIPT_TAIL_BYTES)
                # Drop a partial line at the start of the window.
                _ = f.readline()
            return f.read().decode("utf-8", errors="replace")
    except OSError as exc:
        logger.warning("transcript read failed: %s", exc)
        return ""


def _iter_jsonl_records(blob: str):
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _record_text(rec: dict) -> str:
    """Best-effort flatten of a transcript record into searchable text.
    Never executes anything; only string concatenation."""
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
    return "\n".join(parts)


def has_step0_since_last_user(transcript_blob: str) -> bool:
    """Walk records oldest-first within the tail; reset 'seen' on each USER
    message; mark 'seen' when an assistant text contains ≥ MIN_MARKERS_PRESENT
    Step 0 labels. Return the final 'seen' state."""
    seen = False
    for rec in _iter_jsonl_records(transcript_blob):
        role = (rec.get("message") or {}).get("role") or rec.get("role") or rec.get("type")
        text_lower = _record_text(rec).lower()
        if role == "user":
            seen = False
            continue
        if role == "assistant" or role == "model":
            if not text_lower:
                continue
            hits = sum(1 for m in STEP0_MARKERS if m in text_lower)
            if hits >= MIN_MARKERS_PRESENT:
                seen = True
    return seen


# ── Decision ───────────────────────────────────────────────────────────────


def _agent_type_from_env() -> str:
    """Map the session CALLSIGN to a sandbox agent_type. Each callsign
    operates as a build-2-equivalent surface by default; specialised
    callsigns (scout=research, atlas=build) can be tightened later by
    extending the map. Returns "" when CALLSIGN is unset, which the
    sandbox layer treats as deny-by-default."""
    cs = (os.environ.get("CALLSIGN") or "").strip().lower()
    if not cs:
        return ""
    return {
        "elliot": "build-2",
        "atlas": "build-2",
        "aiden": "build-3",
        "orion": "build-3",
        "scout": "research-1",
    }.get(cs, "build-2")


def decide(hook_input: dict) -> tuple[int, str]:
    """Return (exit_code, message). exit_code=0 allows; 2 blocks."""
    tool_name = hook_input.get("tool_name") or ""

    # GOV-12 sandbox check (P6 wire-up). Runs BEFORE the Step 0 check so
    # an off-allowlist tool is rejected even when Step 0 is satisfied.
    # Skipped when CALLSIGN is unset (local dev / one-off scripts) so
    # we don't block legitimate ad-hoc runs.
    agent_type = _agent_type_from_env()
    if agent_type and tool_name and not validate_tool_access(agent_type, tool_name):
        return (
            2,
            f"sandbox:tool_not_in_allowlist — agent_type={agent_type!r} "
            f"is not permitted to invoke tool={tool_name!r}. See "
            f"src/config/sandbox.py:AGENT_ALLOWLISTS.",
        )

    if tool_name not in MUTATING_TOOLS:
        return 0, "non-mutating tool — allow"

    transcript = validate_transcript_path(hook_input.get("transcript_path"))
    if transcript is None:
        # Fail-open: a missing/invalid transcript path means we cannot
        # prove Step 0 is missing. Don't block legitimate work.
        return 0, "transcript unavailable — fail-open allow"

    blob = read_transcript_tail(transcript)
    if has_step0_since_last_user(blob):
        return 0, "step0 found in current directive turn — allow"

    return (
        2,
        f"LAW XV-D: Step 0 RESTATE not detected in current directive before "
        f"{tool_name}. Post Objective / Scope / Success criteria / Assumptions "
        f"and wait for confirmation, OR set GOV_HOOK_MODE=warn to bypass.",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P1 governance PreToolUse hook.")
    ap.add_argument(
        "--mode",
        choices=("enforce", "warn"),
        default=os.environ.get("GOV_HOOK_MODE", "enforce"),
        help="Override mode (otherwise GOV_HOOK_MODE env).",
    )
    args = ap.parse_args(argv)

    hook_input = read_hook_input()
    code, msg = decide(hook_input)

    if code == 0:
        logger.info(msg)
        return 0

    # code == 2 → would block in enforce mode, log-only in warn
    logger.warning("WOULD BLOCK: %s", msg)
    if args.mode == "warn":
        logger.info("warn mode — exit 0 (no block)")
        return 0
    # enforce: write the reason to stderr (Claude Code shows this) + exit 2
    print(msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        logger.exception("hook crashed (fail-open): %s", exc)
        sys.exit(0)
