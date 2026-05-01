"""src/governance/coordinator.py — shared-state claims + DSAE draft merger.

GOV-PHASE1-TRACK-B / B2.

Two surfaces:

1. CLAIMS — bots write rows to public.coordinator_claims before any
   shared-resource action (commit, dispatch, shared-file edit, watcher,
   merge). Peers see the claim instantly via Supabase Realtime
   subscription. Enforces R2 Claim-Before-Commit + Claim-Before-Touch
   shared-files rule (~/.claude/CLAUDE.md §Shared Governance Laws).

2. DSAE MERGER — when both bots post draft responses concurrently
   (DSAE Protocol DISCUSS phase), `merge_drafts()` classifies whether
   they AGREE-same-examples / AGREE-different-examples / DIFFER and
   recommends a consolidation or sequencing action.

Public API:
    claim(callsign, action, target_path, *, metadata=None,
          expires_in_seconds=300, client=None) -> ClaimRecord
    release(claim_id, *, client=None) -> bool
    list_active_claims(*, target_path=None, callsign=None,
                       client=None) -> list[ClaimRecord]
    subscribe_realtime(handler, *, client=None) -> closeable
    merge_drafts(draft_a, draft_b, *, classifier=None) -> MergerVerdict

The Supabase client is injectable for hermetic tests; production uses
src.integrations.supabase.create_client(). The classifier is also
injectable; production uses governance.router._build_openai_client().
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)

ClaimAction = Literal["commit", "dispatch", "shared-file-edit", "watcher", "merge"]
ClaimStatus = Literal["active", "released", "expired"]
MergerVerdictKind = Literal[
    "agree_same_examples",
    "agree_different_examples",
    "differ",
    "classifier_failed",
]


# ── Claims ───────────────────────────────────────────────────────────────────

@dataclass
class ClaimRecord:
    id: str
    callsign: str
    action: ClaimAction
    target_path: str
    claimed_at: str
    released_at: str | None
    status: ClaimStatus
    expires_at: str
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> ClaimRecord:
        return cls(
            id=str(row.get("id", "")),
            callsign=row["callsign"],
            action=row["action"],
            target_path=row["target_path"],
            claimed_at=str(row.get("claimed_at", "")),
            released_at=(str(row["released_at"]) if row.get("released_at") else None),
            status=row.get("status", "active"),
            expires_at=str(row.get("expires_at", "")),
            metadata=row.get("metadata"),
        )


def _build_supabase_client():
    """Lazy-construct a Supabase client. Returns None if env or pkg missing."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client  # type: ignore
    except ImportError:
        logger.warning("coordinator: supabase package not installed")
        return None
    return create_client(url, key)


def claim(
    callsign: str,
    action: ClaimAction,
    target_path: str,
    *,
    metadata: dict[str, Any] | None = None,
    expires_in_seconds: int = 300,
    client: Any | None = None,
) -> ClaimRecord:
    """Insert an active claim row + return the record.

    Caller is responsible for calling release() when work completes.
    """
    if client is None:
        client = _build_supabase_client()
    if client is None:
        raise RuntimeError(
            "coordinator: no Supabase client available; cannot claim"
        )
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    ).isoformat()
    payload = {
        "callsign": callsign,
        "action": action,
        "target_path": target_path,
        "status": "active",
        "expires_at": expires_at,
        "metadata": metadata,
    }
    response = (
        client.table("coordinator_claims")
        .insert(payload)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    if not rows:
        raise RuntimeError("coordinator: claim insert returned no row")
    return ClaimRecord.from_row(rows[0])


def release(claim_id: str, *, client: Any | None = None) -> bool:
    """Mark a claim as released. Returns True on success, False on miss."""
    if client is None:
        client = _build_supabase_client()
    if client is None:
        raise RuntimeError("coordinator: no Supabase client available; cannot release")
    now_iso = datetime.now(timezone.utc).isoformat()
    response = (
        client.table("coordinator_claims")
        .update({"status": "released", "released_at": now_iso})
        .eq("id", claim_id)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return bool(rows)


def list_active_claims(
    *,
    target_path: str | None = None,
    callsign: str | None = None,
    client: Any | None = None,
) -> list[ClaimRecord]:
    """Return active (un-released, un-expired) claims, optionally filtered."""
    if client is None:
        client = _build_supabase_client()
    if client is None:
        return []
    query = client.table("coordinator_claims").select("*").eq("status", "active")
    if target_path is not None:
        query = query.eq("target_path", target_path)
    if callsign is not None:
        query = query.eq("callsign", callsign)
    response = query.execute()
    rows = getattr(response, "data", None) or []
    out: list[ClaimRecord] = []
    now = datetime.now(timezone.utc)
    for row in rows:
        rec = ClaimRecord.from_row(row)
        # Drop expired rows from the active view (best-effort filter; the
        # SQL CHECK doesn't auto-flip status, just guards values).
        try:
            exp = datetime.fromisoformat(rec.expires_at.replace("Z", "+00:00"))
            if exp < now:
                continue
        except Exception:
            pass
        out.append(rec)
    return out


def check_conflict(
    callsign: str,
    target_path: str,
    *,
    client: Any | None = None,
) -> dict[str, Any] | None:
    """Return the first peer claim on target_path not from callsign, or None if no conflict."""
    claims = list_active_claims(target_path=target_path, client=client)
    for claim_rec in claims:
        if claim_rec.callsign != callsign and claim_rec.status == "active":
            return {
                "id": claim_rec.id,
                "callsign": claim_rec.callsign,
                "action": claim_rec.action,
                "target_path": claim_rec.target_path,
                "status": claim_rec.status,
                "expires_at": claim_rec.expires_at,
            }
    return None


def subscribe_realtime(
    handler: Callable[[dict[str, Any]], None],
    *,
    client: Any | None = None,
):
    """Subscribe to coordinator_claims changes via Supabase Realtime.
    `handler` is invoked with the raw payload on every INSERT/UPDATE.
    Returns a closeable handle (call .close() when done, if available).

    Production uses Supabase Realtime channel API. Test environments can
    inject a fake client whose channel().subscribe() yields immediately.
    """
    if client is None:
        client = _build_supabase_client()
    if client is None:
        logger.warning(
            "coordinator: subscribe_realtime called without a client; "
            "no subscription created"
        )
        return None
    channel = client.channel("coordinator-claims")
    channel.on(
        "postgres_changes",
        {"event": "*", "schema": "public", "table": "coordinator_claims"},
        handler,
    )
    channel.subscribe()
    return channel


# ── DSAE Merger ──────────────────────────────────────────────────────────────

@dataclass
class MergerVerdict:
    kind: MergerVerdictKind
    rationale: str
    consolidated: str | None = None  # populated for AGREE-same path
    sequenced_pair: tuple[str, str] | None = None  # (first_to_post, second) for AGREE-different
    raw_classifier_response: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_DSAE_SYSTEM_PROMPT = """You compare two peer-bot draft responses to the same
Dave directive. Decide one of:

  agree_same_examples       — same conclusion AND same supporting examples;
                              consolidate into one message.
  agree_different_examples  — same conclusion BUT different examples; sequence
                              both posts so Dave sees both perspectives.
  differ                    — different conclusions; needs explicit DIFFER
                              flag + verdict-wait per R6.

Respond with strict JSON: {"kind": "...", "rationale": "<one line>"}"""


def _heuristic_dsae_classify(draft_a: str, draft_b: str) -> MergerVerdict:
    """Conservative fallback used when classifier is unavailable. Errs
    toward `differ` to ensure Dave sees both drafts when uncertain."""
    a, b = draft_a.strip(), draft_b.strip()
    if not a or not b:
        return MergerVerdict(
            kind="agree_same_examples",
            rationale="one draft empty; using non-empty draft as consolidated",
            consolidated=a or b,
        )
    if a == b:
        return MergerVerdict(
            kind="agree_same_examples",
            rationale="exact text match",
            consolidated=a,
        )
    # Neither empty nor identical → safest is DIFFER (Dave sees both).
    return MergerVerdict(
        kind="differ",
        rationale="heuristic fallback (no classifier); defaulting to differ to surface both drafts",
    )


def merge_drafts(
    draft_a: str,
    draft_b: str,
    *,
    classifier: Callable[[str, str], MergerVerdict] | None = None,
) -> MergerVerdict:
    """Classify two drafts (DSAE DISCUSS phase) and recommend a merge or
    sequence. Pure heuristic if no classifier injected.

    Args:
        draft_a, draft_b: text bodies of the two peer drafts.
        classifier: optional injected classifier callable for tests; when
                    None, attempts to lazy-build an OpenAI gpt-4o-mini
                    client and falls back to heuristic on failure.

    Returns:
        MergerVerdict with `kind` + recommended action payload.
    """
    if classifier is not None:
        try:
            return classifier(draft_a, draft_b)
        except Exception as exc:
            logger.warning("coordinator: injected classifier failed: %s", exc)
            return MergerVerdict(
                kind="classifier_failed",
                rationale=f"injected classifier raised: {exc}",
                error=str(exc),
            )

    # Build OpenAI client at runtime; fall back to heuristic if absent.
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _heuristic_dsae_classify(draft_a, draft_b)
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)
    except ImportError:
        return _heuristic_dsae_classify(draft_a, draft_b)

    user_msg = f"DRAFT A:\n{draft_a}\n\n---\n\nDRAFT B:\n{draft_b}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _DSAE_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg[:6000]},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=120,
        )
    except Exception as exc:
        logger.warning("coordinator: classifier call failed: %s", exc)
        return MergerVerdict(
            kind="classifier_failed",
            rationale=f"openai call failed: {exc}",
            error=str(exc),
        )

    raw = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return MergerVerdict(
            kind="classifier_failed",
            rationale="non-json classifier response",
            raw_classifier_response=raw,
        )
    kind_raw = parsed.get("kind", "differ")
    valid_kinds = ("agree_same_examples", "agree_different_examples", "differ")
    kind: MergerVerdictKind = kind_raw if kind_raw in valid_kinds else "differ"
    verdict = MergerVerdict(
        kind=kind,
        rationale=str(parsed.get("rationale", "")),
        raw_classifier_response=raw,
    )
    if kind == "agree_same_examples":
        # Consolidate to draft_a as the canonical (both said the same).
        verdict.consolidated = draft_a
    elif kind == "agree_different_examples":
        verdict.sequenced_pair = (draft_a, draft_b)
    return verdict
