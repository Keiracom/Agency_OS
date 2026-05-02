"""PeerReviewContract — bot-on-bot peer review verdict.

Used when one bot reviews the other's PR / proposal. Encodes the R6
Verdict-Wait + R8 Dual-Concur Yellow Flag + DSAE AGREE/DIFFER protocols
in a single typed shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PeerReviewContract(BaseModel):
    """Structured peer-review verdict."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reviewer_callsign: Literal["elliot", "aiden", "orion", "atlas", "scout"] = Field(
        ...,
        description="Who is posting the review.",
    )
    target_pr: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="PR URL or branch identifier under review.",
    )
    status: Literal["concur", "differ", "yellow_flag"] = Field(
        ...,
        description=(
            "concur = approve. differ = halt + verdict-wait per R6. "
            "yellow_flag = dual-concur agreed too fast (R8); re-check needed."
        ),
    )
    diff_findings: list[str] = Field(
        default_factory=list,
        description="Concrete observations that drove the verdict.",
    )
    recommendation: str = Field(
        default="",
        max_length=2000,
        description="Recommended next action for the originating bot.",
    )
    audit_evidence: list[str] = Field(
        default_factory=list,
        description=(
            "Per R7 Audit-Before-Recommend / R10 Audit-In-Proposal: grep / "
            "git ls-files / find output supporting the verdict."
        ),
    )
    posted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the review was posted.",
    )
