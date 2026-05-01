"""DirectiveContract — typed shape for a Dave-issued directive.

Maps to the [DISPATCH FROM aiden] / Dave-supergroup directive format.
Used by Step 0 RESTATE generators to produce structured restate blocks.

Fields (per dispatch GOV-PHASE1-TRACK-B / B3):
  intent             — one-line objective
  context            — background paragraph (why now)
  latitude           — what the bot may decide vs must escalate
  frozen_artifacts   — files / branches / states that must NOT change
  success_criteria   — list of acceptance gates
  scope_in / out     — explicit IN-scope / OUT-of-scope items
  spend_aud_cap      — AUD spend ceiling (0 for read-only)
  step0_exemption    — true for clone dispatches
  source             — 'dave' | 'parent_bot' | 'self'
  ratified_at        — ISO timestamp
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DirectiveContract(BaseModel):
    """Structured shape of a directive dispatched to a bot or clone."""

    model_config = ConfigDict(
        extra="forbid",            # Anthropic structured outputs reject unknown keys
        str_strip_whitespace=True,
    )

    intent: str = Field(
        ..., min_length=1, max_length=500,
        description="One-line objective. Must be answerable as a single goal.",
    )
    context: str = Field(
        default="", max_length=4000,
        description="Background paragraph — why now, what changed.",
    )
    latitude: str = Field(
        default="", max_length=2000,
        description="What the bot may decide autonomously vs what must escalate.",
    )
    frozen_artifacts: list[str] = Field(
        default_factory=list,
        description="Files / branches / states that must NOT be modified.",
    )
    success_criteria: list[str] = Field(
        default_factory=list, min_length=0,
        description="Acceptance gates. Empty list = no formal gates (rare).",
    )
    scope_in: list[str] = Field(
        default_factory=list,
        description="Explicit in-scope items.",
    )
    scope_out: list[str] = Field(
        default_factory=list,
        description="Explicit out-of-scope items.",
    )
    spend_aud_cap: float = Field(
        default=0.0, ge=0,
        description="AUD spend ceiling for executing this directive. 0 = read-only.",
    )
    step0_exemption: bool = Field(
        default=False,
        description="True for clone dispatches under Clone Step 0 Exemption.",
    )
    source: Literal["dave", "parent_bot", "self"] = Field(
        ..., description="Who originated the directive.",
    )
    ratified_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the directive was ratified.",
    )
    task_ref: str = Field(
        default="", max_length=200,
        description="Short reference label (e.g. 'GOV-PHASE1-TRACK-B').",
    )
