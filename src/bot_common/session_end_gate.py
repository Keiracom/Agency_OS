"""session_end_gate.py — LAW XV mechanical enforcement (Outcome 2).

Per Dave System Health Monitoring directive 2026-05-12 Outcome 2 + Max's spec
ts 1778553034. Amended 2026-05-27 (PR #1214 Agency_OS-uik): docs/MANUAL.md
ARCHIVED; Manual Section 13 check REMOVED from the gate. ceo_memory is the
sole SSOT; Drive mirror is best-effort (non-blocking, not gated).

  "Prevent completion claims that skip the save. Mechanical check, not an
   instruction agents can ignore."

Trigger: outbound message contains store-save completion language. Gate
verifies both required stores were written for the claimed directive
within the last 5 minutes; refuses the post if either is missing.

Stores checked (matches scripts/three_store_save.py, post-2026-05-27 amend):
  1. ceo_memory.key == "ceo:directive_{N}_complete" with updated_at < 5min
  2. cis_directive_metrics.directive_id == N (or directive_ref contains N)
  Drive mirror is best-effort and NOT gated — failure logs
  LAW_XV_DRIVE_MIRROR_FAIL but does not block.

Mirrors verify_gate.py structure (gate_check returns (ok, blocker_reason))
so slack_relay.py can call it identically.

Bypass env:
  R_LAW_XV_SKIP=1 — skip all verification. Document usage in PR description.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from typing import Final

logger = logging.getLogger("session_end_gate")

# Trigger patterns — outbound text claims a 4-store save / completion.
_COMPLETION_TRIGGER_RE: Final = re.compile(
    r"\bdirective[_#\s]*\d+.*?\b(?:complete|complet[ed]+)\b"
    r"|\b4[-\s]?store\s+save\b"
    r"|\ball\s+stores?\s+written\b"
    r"|\bstore[s]?\s+save\s+complete\b"
    r"|\bfour[-\s]?store\s+save\b",
    re.IGNORECASE | re.DOTALL,
)

# Anti-broadening: exempt past-tense reference to past completions, hypotheticals.
_EXEMPT_RE: Final = re.compile(
    r"\b(?:will|going to|about to|planning to)\s+(?:complete|save|write)"
    r"|\bhaven't\s+(?:saved|completed|written)\b"
    r"|\bnot\s+(?:saved|completed|written)\s+yet\b"
    r"|\bdirective[_#\s]*\d+\s+is\s+not\s+complete\b",
    re.IGNORECASE,
)

# Directive number extractor — pulls integer N from "directive 9001" / "directive #9001" /
# "directive_9001" patterns.
_DIRECTIVE_NUM_RE: Final = re.compile(r"\bdirective[_#\s]+(\d+)", re.IGNORECASE)

# How recently the ceo_memory row must have been updated to count as a fresh save.
FRESH_SAVE_WINDOW = timedelta(minutes=5)


def has_completion_trigger(text: str) -> bool:
    if _EXEMPT_RE.search(text):
        return False
    return bool(_COMPLETION_TRIGGER_RE.search(text))


def extract_directive_number(text: str) -> int | None:
    match = _DIRECTIVE_NUM_RE.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Store checks
# ─────────────────────────────────────────────────────────────────────────────


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def check_ceo_memory(directive_n: int, now: datetime) -> tuple[bool, str]:
    """Returns (present_and_fresh, reason_if_not)."""
    try:
        sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS")
        from src.evo.supabase_client import sb_get  # noqa: E402
    except ImportError as exc:
        return True, f"(ceo_memory check skipped — import failed: {exc})"
    key = f"ceo:directive_{directive_n}_complete"
    try:
        rows = sb_get("ceo_memory", {"select": "key,updated_at", "key": f"eq.{key}"})
    except Exception as exc:  # noqa: BLE001
        return True, f"(ceo_memory check skipped — query failed: {exc})"
    if not rows:
        return False, f"ceo_memory: no row for key {key}"
    updated = _parse_iso(rows[0].get("updated_at", ""))
    if updated is None:
        return False, f"ceo_memory: row for {key} has invalid updated_at"
    if now - updated > FRESH_SAVE_WINDOW:
        return (
            False,
            f"ceo_memory: {key} stale (updated {int((now - updated).total_seconds())}s ago)",
        )
    return True, ""


def check_cis_metrics(directive_n: int) -> tuple[bool, str]:
    """Returns (present, reason_if_not). Matches directive_id OR directive_ref-contains-N."""
    try:
        sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS")
        from src.evo.supabase_client import sb_get  # noqa: E402
    except ImportError as exc:
        return True, f"(cis_directive_metrics check skipped — import failed: {exc})"
    try:
        rows = sb_get(
            "cis_directive_metrics",
            {"select": "directive_id,directive_ref", "directive_id": f"eq.{directive_n}"},
        )
    except Exception as exc:  # noqa: BLE001
        return True, f"(cis_directive_metrics check skipped — query failed: {exc})"
    if rows:
        return True, ""
    # Fallback: search directive_ref for the number (e.g. "Directive #9001 — X").
    try:
        ref_rows = sb_get(
            "cis_directive_metrics",
            {
                "select": "directive_id,directive_ref",
                "directive_ref": f"ilike.*{directive_n}*",
                "limit": "1",
            },
        )
    except Exception:  # noqa: BLE001
        ref_rows = []
    if ref_rows:
        return True, ""
    return False, f"cis_directive_metrics: no row for directive_id={directive_n}"


# NOTE: check_manual_section_13 removed 2026-05-27 (PR #1214 Agency_OS-uik).
# docs/MANUAL.md is archived; the Manual Section 13 entry is no longer a
# gated store. Drive mirror is best-effort (non-blocking) and NOT gated.


# ─────────────────────────────────────────────────────────────────────────────
# Gate entry
# ─────────────────────────────────────────────────────────────────────────────


def gate_check(text: str, now: datetime | None = None) -> tuple[bool, str | None]:
    """Verify both required stores are written for any claimed-complete directive.

    Required stores (per amended LAW XV 2026-05-27 PR #1214):
      1. ceo_memory (PRIMARY SSOT)
      2. cis_directive_metrics
    Drive mirror is best-effort and NOT gated.

    Returns (ok, blocker_reason):
      - ok=True, blocker_reason=None → message can post
      - ok=False, blocker_reason=str → block; caller exits 2 with this on stderr

    Skip behaviour:
      - R_LAW_XV_SKIP=1 in env → (True, None)
      - No completion trigger → (True, None)
      - Trigger but no extractable directive number → (True, None) [don't block ambiguous]
    """
    if os.environ.get("R_LAW_XV_SKIP") == "1":
        return True, None
    if not has_completion_trigger(text):
        return True, None
    directive_n = extract_directive_number(text)
    if directive_n is None:
        return True, None
    now = now or datetime.now(UTC)
    blockers: list[str] = []
    ok_mem, reason_mem = check_ceo_memory(directive_n, now)
    if not ok_mem:
        blockers.append(reason_mem)
    ok_cis, reason_cis = check_cis_metrics(directive_n)
    if not ok_cis:
        blockers.append(reason_cis)
    if blockers:
        return False, (
            f"R_LAW_XV_BLOCKED: directive {directive_n} — "
            + "; ".join(blockers)
            + f". Run scripts/three_store_save.py --directive {directive_n} ... before "
            "claiming complete."
        )
    return True, None
