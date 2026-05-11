"""src/replay — Drevon PR-A.5 deterministic claim verification via turn_logs.

Per Dave #ceo decision #5 (2026-05-11): replace R3 LLM fabrication-detection
with a structural fix that queries `turn_logs` to verify "PR #N merged" /
"commit <hash>" claims against actual session history.

Public interface:
    verify_completion_claim(text, session_id=None, callsign=None)
        Returns (verified, reason). Used by central_listener as a post-LLM
        check (gated behind REPLAY_ON_CLAIM_ENABLED env var).
"""

from src.replay.claim_verifier import verify_completion_claim

__all__ = ["verify_completion_claim"]
