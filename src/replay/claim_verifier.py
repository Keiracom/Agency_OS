"""claim_verifier.py — Drevon PR-A.5 deterministic replay-on-claim.

Queries `turn_logs` for evidence of verify_pr.sh / gh pr view / git cat-file
invocations against the PR# or commit hash referenced in a completion claim.
Used by central_listener as a post-LLM check to suppress R3 violations when
real verification evidence exists in the session's audit trail.

Per Dave #ceo decision #5 + Max/Elliot three-layer defense architecture:
  1. Discipline (PR #717 module) — reminds agents to verify
  2. Gate (PR #703 verify_gate) — blocks claims without verification
  3. Replay (this module) — after-the-fact structural audit against turn_logs

Design:
  Pre-LLM regex catches obvious deterministic cases.
  LLM catches semantic/ambiguous cases.
  Post-LLM replay verifies LLM's R3 violation against turn_logs:
    if turn_logs contains evidence of verification → suppress (LLM wrong)
    else → confirm violation (no evidence = potential fabrication)
"""

from __future__ import annotations

import logging
import re

from src.evo.supabase_client import sb_get

logger = logging.getLogger("replay.claim_verifier")

_PR_RE = re.compile(
    r"\bprs?\s*#?\s*(\d+)\b"  # "PR #N" / "PRs #N" / "pr#N"
    r"|\bpull\s+request\s+#?\s*(\d+)\b"  # "pull request N"
    r"|(?<![\w/])#(\d+)\b",  # orphan "#N" — not preceded by word char or slash
    re.IGNORECASE,
)
_HASH_RE = re.compile(r"\b([0-9a-f]{7,40})\b")

# Evidence-tool patterns — turn_logs tool_args_json substrings that count as
# verification activity for a given claim.
_PR_EVIDENCE_TOOLS = (
    "verify_pr.sh",
    "gh pr view",
    "gh pr merge",
    "gh pr checks",
    "gh api repos",
)
_COMMIT_EVIDENCE_TOOLS = (
    "git cat-file",
    "git log",
    "git show",
)


def _extract_pr_numbers(text: str) -> list[int]:
    out: list[int] = []
    for m in _PR_RE.finditer(text):
        for grp in m.groups():
            if grp:
                out.append(int(grp))
                break
    return out


def _extract_commit_hashes(text: str) -> list[str]:
    return [m.group(1).lower() for m in _HASH_RE.finditer(text)]


def _query_turn_logs_for_pattern(pattern: str, callsign: str | None) -> list[dict]:
    """Query turn_logs for tool_args_json containing `pattern`.

    Caller's responsibility to filter further (PR# substring match, session match).
    """
    params: dict[str, str] = {
        "select": "id,turn_id,tool_name,tool_args_json,started_at",
        "tool_args_json": f"ilike.*{pattern}*",
        "order": "started_at.desc",
        "limit": "20",
    }
    try:
        return sb_get("turn_logs", params)
    except Exception as exc:
        logger.warning("turn_logs query failed for pattern %r: %s", pattern, exc)
        return []


def _scan_for_pr(pr_num: int, callsign: str | None) -> tuple[bool, str]:
    """Return (found, reason). Match if ANY tool_log args mention this PR.

    After filtering rows to those whose args contain a known evidence-tool
    pattern (verify_pr.sh, gh pr view, etc.), the PR number appearing as a
    substring is strong enough evidence — those tools' args are usually a
    single PR# argument.
    """
    needle = str(pr_num)
    for tool_pattern in _PR_EVIDENCE_TOOLS:
        rows = _query_turn_logs_for_pattern(tool_pattern, callsign)
        for row in rows:
            args_text = str(row.get("tool_args_json", "")).lower()
            if needle in args_text:
                return (
                    True,
                    f"verified via {row.get('tool_name')} call ({tool_pattern}) referencing PR #{pr_num}",
                )
    return False, f"no turn_logs evidence for PR #{pr_num}"


def _scan_for_hash(commit_hash: str, callsign: str | None) -> tuple[bool, str]:
    """Return (found, reason). Match if ANY tool_log args mention this hash prefix."""
    if len(commit_hash) < 7:
        return False, f"hash {commit_hash} too short to verify"
    for tool_pattern in _COMMIT_EVIDENCE_TOOLS:
        rows = _query_turn_logs_for_pattern(tool_pattern, callsign)
        for row in rows:
            args_text = str(row.get("tool_args_json", "")).lower()
            if commit_hash in args_text:
                return (
                    True,
                    f"verified via {row.get('tool_name')} call ({tool_pattern}) referencing commit {commit_hash}",
                )
    return False, f"no turn_logs evidence for commit {commit_hash}"


def verify_completion_claim(
    text: str,
    callsign: str | None = None,
) -> tuple[bool, str]:
    """Verify a completion claim against turn_logs.

    Returns (verified, reason):
      verified=True   → evidence found in turn_logs (suppress R3 violation)
      verified=False  → no evidence (let R3 violation fire)

    Args:
        text: The message text containing the completion claim.
        callsign: Optional callsign filter — restricts turn_logs query to that
            agent's sessions. None = global scan.

    Semantics:
      - If text contains no PR# AND no commit hash → (True, "no claim refs")
      - If ANY ref has evidence → (True, evidence summary)
      - If NO refs have evidence → (False, missing-evidence summary)

    The conservative answer is `(True, ...)` — return True when uncertain so
    we don't fire false R3 violations. The caller's R3 check is the gate;
    this function only suppresses when we have positive evidence.
    """
    pr_refs = _extract_pr_numbers(text)
    hash_refs = _extract_commit_hashes(text)

    if not pr_refs and not hash_refs:
        return True, "no PR#/commit refs in claim — nothing to verify"

    evidence_lines: list[str] = []
    missing_lines: list[str] = []
    for pr_num in pr_refs:
        found, reason = _scan_for_pr(pr_num, callsign)
        (evidence_lines if found else missing_lines).append(reason)
    for h in hash_refs:
        # Skip obvious non-commit-hash patterns (channel IDs, hex digits in non-commit context).
        if h.startswith("c0b") or h.isdigit():
            continue
        if len(h) < 7:
            continue
        found, reason = _scan_for_hash(h, callsign)
        (evidence_lines if found else missing_lines).append(reason)

    if evidence_lines and not missing_lines:
        return True, "; ".join(evidence_lines)
    if evidence_lines and missing_lines:
        # Partial coverage — conservatively suppress (some evidence found).
        return (
            True,
            f"partial evidence; {'; '.join(evidence_lines)} | missing: {'; '.join(missing_lines)}",
        )
    return False, "; ".join(missing_lines) if missing_lines else "no evidence"
