"""CompletionClaimContract — typed shape for a bot's completion claim.

Encodes R9 Verify-Before-Claim + LAW XV Three-Store Completion + LAW XIV
Raw Output Mandate. Every '[COMPLETE:<callsign>]' message should be
expressible as one of these.

Amended 2026-05-27 (PR #1214 Agency_OS-uik): docs/MANUAL.md ARCHIVED.
Required stores collapsed from four to two (ceo_memory + cis_metrics);
Drive mirror is best-effort, not gated. `stored_in_manual` field retained
on the model for backwards-compat with serialized claims but is no longer
checked by `three_store_complete()`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CompletionClaimContract(BaseModel):
    """Structured completion claim."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    callsign: Literal["elliot", "aiden", "orion", "atlas", "scout"] = Field(
        ...,
        description="Bot claiming completion.",
    )
    task_ref: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Directive reference label.",
    )
    branch: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Git branch holding the work.",
    )
    commit_sha: str = Field(
        ...,
        min_length=7,
        max_length=64,
        description="Commit SHA (short or full).",
    )
    pr_url: str | None = Field(
        default=None,
        description="PR URL when one is opened. Null when dispatch said no-PR.",
    )

    # R9 — verification command output paste, not a paraphrase.
    verification_commands: list[str] = Field(
        default_factory=list,
        description="Shell commands run for verification (e.g. 'pytest tests/...').",
    )
    verification_stdout: str = Field(
        default="",
        max_length=20000,
        description=(
            "Raw stdout/stderr from verification commands. Required by R9 "
            "for any non-trivial completion claim."
        ),
    )

    # LAW XV Three-Store Completion check (amended 2026-05-27 PR #1214).
    # stored_in_manual + stored_in_drive_mirror retained for serialization
    # backwards-compat but NOT checked by three_store_complete() — Manual is
    # archived; Drive mirror is best-effort.
    stored_in_manual: bool = Field(default=False)
    stored_in_ceo_memory: bool = Field(default=False)
    stored_in_cis_metrics: bool = Field(default=False)
    stored_in_drive_mirror: bool = Field(default=False)

    # Spend audit.
    audit_aud_spend: float = Field(
        default=0.0,
        ge=0,
        description="Actual AUD spent executing the directive.",
    )

    # Metadata.
    completed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the work was claimed complete.",
    )
    notes: str = Field(
        default="",
        max_length=4000,
        description="Free-form notes (deferred items, follow-ups, caveats).",
    )

    def three_store_complete(self) -> bool:
        """LAW XV check — both required stores written?

        Amended 2026-05-27 (PR #1214 Agency_OS-uik): only ceo_memory +
        cis_metrics are required. Drive mirror is best-effort (non-blocking);
        Manual is archived. The legacy `stored_in_manual` and
        `stored_in_drive_mirror` flags are kept on the model for serialized-
        claim backwards-compat but NOT checked here.
        """
        return self.stored_in_ceo_memory and self.stored_in_cis_metrics

    # Deprecated alias kept for backwards-compat with callers that still
    # reference the four-store method name. Removes when no callers remain.
    def four_store_complete(self) -> bool:
        """DEPRECATED — renamed to three_store_complete in PR #1214. Forwards
        to the new method for callers that haven't updated yet."""
        return self.three_store_complete()
