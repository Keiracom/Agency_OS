"""spawn_composer — assemble the A+B+C+D+E initial prompt for an ephemeral agent.

Per PR #1140 §3 + §5 (ephemeral agent system scoping). Called by every
per-callsign dispatcher (§7 piece 1) when spawning a fresh Claude Code
subprocess. Pure builder — returns the composed prompt string; spawning
is the dispatcher's job.

Five parts per §3:
  Part A — per-callsign role brief (docs/runbooks/<callsign>-identity.md;
           falls back to repo-root IDENTITY.md)
  Part B — canonical-key snapshot from ceo_memory (ceo:comm_architecture +
           ceo:memory_abstraction_layer_v1 + ceo:agency_os_keiracom_separation_v1).
           Fresh per spawn — no cache (staleness is the failure mode).
  Part C — pending inbox queue at /tmp/telegram-relay-<callsign>/inbox/
  Part D — recent ceo_memory: last 5 daily_log/core_fact for callsign +
           dave_confirmed entries from last 7 days
  Part E — last 10 entries from public.agent_memories for this callsign

Resume-spawn branch (§5):
  If resume_context is supplied (a decoded decision_response envelope plus
  the paused agent's state-snapshot), emit A+B+D+E + state-snapshot +
  decision and SKIP Part C — resume agents don't re-process the inbox.

DI: caller passes a DB cursor/connection implementing _DBProtocol + repo
root + inbox root + optional `now` (for testability). No env-var reads;
no fs writes; no network calls. Boundary-matrix-v1 guard (b) compatible
even though this module lives in src/relay/ (outside BMV1 scope).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

# Section headers — kept as constants so the spawned agent + future
# debuggers can grep for them in a captured prompt.
_HEADER_A = "=== PART A — ROLE BRIEF ==="
_HEADER_B = "=== PART B — CANONICAL CEO_MEMORY KEYS ==="
_HEADER_C = "=== PART C — PENDING INBOX QUEUE ==="
_HEADER_D = "=== PART D — RECENT CEO_MEMORY ==="
_HEADER_E = "=== PART E — RECENT AGENT MEMORIES ==="
_HEADER_RESUME = "=== RESUME CONTEXT — PAUSED-TASK STATE + DECISION ==="

# Per-part byte caps — bound the prompt size so a long-running inbox queue
# or stale ceo_memory entry can't blow Claude's context budget.
MAX_PART_BYTES = 4096

# Canonical keys per §3 line 48 — fresh-query per spawn.
CANONICAL_KEYS: tuple[str, ...] = (
    "ceo:comm_architecture",
    "ceo:memory_abstraction_layer_v1",
    "ceo:agency_os_keiracom_separation_v1",
)

DAILY_LOG_LIMIT = 5
AGENT_MEMORY_LIMIT = 10
DAVE_CONFIRMED_WINDOW_SECONDS = 7 * 86400


class _DBProtocol(Protocol):
    """Subset of a DB cursor we depend on. Mirrors PR #1173 _DBProtocol shape."""

    def execute(self, query: str, *params: Any) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> Any: ...


def _truncate(text: str, max_bytes: int = MAX_PART_BYTES) -> str:
    """Bound a part to max_bytes with an explicit truncation marker."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    dropped = len(encoded) - max_bytes
    return encoded[:max_bytes].decode("utf-8", errors="ignore") + f"\n<truncated {dropped} bytes>"


def _part_a_role_brief(callsign: str, repo_root: Path) -> str:
    """Read docs/runbooks/<callsign>-identity.md, else repo-root IDENTITY.md."""
    runbook = repo_root / "docs" / "runbooks" / f"{callsign}-identity.md"
    identity = repo_root / "IDENTITY.md"
    for path in (runbook, identity):
        if path.exists():
            return _truncate(path.read_text(encoding="utf-8"))
    return f"<no role brief found for callsign={callsign!r}>"


def _part_b_canonical_keys(db: _DBProtocol) -> str:
    """Query ceo_memory for the 3 canonical keys; emit key + value verbatim."""
    sections: list[str] = []
    for key in CANONICAL_KEYS:
        db.execute("SELECT value FROM public.ceo_memory WHERE key = $1", key)
        row = db.fetchone()
        value = row[0] if row else None
        sections.append(f"--- {key} ---\n{value if value is not None else '<not set>'}")
    return _truncate("\n\n".join(sections))


def _part_c_inbox_queue(callsign: str, inbox_root: Path) -> str:
    """Read all *.json files under {inbox_root}/telegram-relay-<callsign>/inbox/."""
    inbox_dir = inbox_root / f"telegram-relay-{callsign}" / "inbox"
    if not inbox_dir.is_dir():
        return f"<inbox dir not present: {inbox_dir}>"
    files = sorted(inbox_dir.glob("*.json"))
    if not files:
        return "<inbox empty>"
    parts: list[str] = []
    for fp in files:
        try:
            parts.append(f"--- {fp.name} ---\n{fp.read_text(encoding='utf-8')}")
        except OSError as exc:
            parts.append(f"--- {fp.name} ---\n<read failed: {exc}>")
    return _truncate("\n\n".join(parts))


def _part_d_recent_ceo_memory(db: _DBProtocol, callsign: str, now: int) -> str:
    """Last 5 daily_log/core_fact for callsign + dave_confirmed last 7 days."""
    cutoff = now - DAVE_CONFIRMED_WINDOW_SECONDS
    db.execute(
        """
        SELECT source_type, LEFT(content, 400), EXTRACT(EPOCH FROM created_at)::bigint
          FROM public.agent_memories
         WHERE callsign = $1
           AND (
             (source_type IN ('daily_log','core_fact'))
             OR (source_type = 'dave_confirmed' AND EXTRACT(EPOCH FROM created_at) >= $2)
           )
         ORDER BY created_at DESC
         LIMIT $3
        """,
        callsign,
        cutoff,
        DAILY_LOG_LIMIT,
    )
    rows = db.fetchall() or []
    if not rows:
        return "<no recent ceo_memory entries>"
    return _truncate("\n\n".join(f"--- {r[0]} @ ts={r[2]} ---\n{r[1]}" for r in rows))


def _part_e_recent_agent_memories(db: _DBProtocol, callsign: str) -> str:
    """Last 10 agent_memories entries for this callsign."""
    db.execute(
        """
        SELECT source_type, LEFT(content, 400), EXTRACT(EPOCH FROM created_at)::bigint
          FROM public.agent_memories
         WHERE callsign = $1
         ORDER BY created_at DESC
         LIMIT $2
        """,
        callsign,
        AGENT_MEMORY_LIMIT,
    )
    rows = db.fetchall() or []
    if not rows:
        return "<no recent agent_memories>"
    return _truncate("\n\n".join(f"--- {r[0]} @ ts={r[2]} ---\n{r[1]}" for r in rows))


def _resume_section(resume_context: Mapping[str, Any]) -> str:
    """Format a resume-context block per §5 — state-snapshot + decision."""
    decision = resume_context.get("decision", "<decision missing>")
    original_ref = resume_context.get("original_task_ref", "<original_task_ref missing>")
    snapshot = resume_context.get("interim_state") or resume_context.get("state_snapshot") or {}
    return (
        f"original_task_ref: {original_ref}\n"
        f"decision: {decision}\n"
        f"interim_state:\n{json.dumps(snapshot, indent=2, sort_keys=True)}"
    )


def compose_initial_prompt(
    callsign: str,
    *,
    db: _DBProtocol,
    repo_root: Path,
    inbox_root: Path = Path("/tmp"),
    now: int,
    resume_context: Mapping[str, Any] | None = None,
) -> str:
    """Assemble the A+B+C+D+E (or A+B+D+E + resume) initial prompt.

    `now` is a unix-int timestamp — caller passes time.time() at spawn moment;
    explicit param keeps the function deterministic + testable.
    """
    if not callsign:
        raise ValueError("callsign is required")
    parts: list[str] = [
        f"{_HEADER_A}\n{_part_a_role_brief(callsign, repo_root)}",
        f"{_HEADER_B}\n{_part_b_canonical_keys(db)}",
    ]
    if resume_context is None:
        parts.append(f"{_HEADER_C}\n{_part_c_inbox_queue(callsign, inbox_root)}")
    parts.append(f"{_HEADER_D}\n{_part_d_recent_ceo_memory(db, callsign, now)}")
    parts.append(f"{_HEADER_E}\n{_part_e_recent_agent_memories(db, callsign)}")
    if resume_context is not None:
        parts.append(f"{_HEADER_RESUME}\n{_resume_section(resume_context)}")
    return "\n\n".join(parts)
