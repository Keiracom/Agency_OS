"""CompletionClaimContract — typed shape for a bot's completion claim.

Encodes R9 Verify-Before-Claim + LAW XV Four-Store Completion + LAW XIV
Raw Output Mandate. Every '[COMPLETE:<callsign>]' message should be
expressible as one of these.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CompletionClaimContract(BaseModel):
    """Structured completion claim."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    callsign: Literal["elliot", "aiden", "orion", "atlas", "scout"] = Field(
        ..., description="Bot claiming completion.",
    )
    task_ref: str = Field(
        ..., min_length=1, max_length=200,
        description="Directive reference label.",
    )
    branch: str = Field(
        ..., min_length=1, max_length=200,
        description="Git branch holding the work.",
    )
    commit_sha: str = Field(
        ..., min_length=7, max_length=64,
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
        default="", max_length=20000,
        description=(
            "Raw stdout/stderr from verification commands. Required by R9 "
            "for any non-trivial completion claim."
        ),
    )

    # LAW XV Four-Store Completion check.
    stored_in_manual: bool = Field(default=False)
    stored_in_ceo_memory: bool = Field(default=False)
    stored_in_cis_metrics: bool = Field(default=False)
    stored_in_drive_mirror: bool = Field(default=False)

    # Spend audit.
    audit_aud_spend: float = Field(
        default=0.0, ge=0,
        description="Actual AUD spent executing the directive.",
    )

    # Metadata.
    completed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the work was claimed complete.",
    )
    notes: str = Field(
        default="", max_length=4000,
        description="Free-form notes (deferred items, follow-ups, caveats).",
    )

    def four_store_complete(self) -> bool:
        """LAW XV check — all four stores written?"""
        return all(
            (
                self.stored_in_manual,
                self.stored_in_ceo_memory,
                self.stored_in_cis_metrics,
                self.stored_in_drive_mirror,
            )
        )
