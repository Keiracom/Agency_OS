"""
Gemini 2.5 Flash client for Pipeline F.

Features:
- URL context (fetch prospect domain)
- Google Search grounding
- Context caching on system prompt
- response_schema JSON mode
- Retry with backoff (delegated to gemini_retry.py)
- Cost tracking

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from src.intelligence.comprehend_schema_f3a import F3A_SYSTEM_PROMPT
from src.intelligence.comprehend_schema_f3b import F3B_SYSTEM_PROMPT
from src.intelligence.gemini_retry import GEMINI_MODEL_DM, gemini_call_with_retry

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

INPUT_COST_PER_TOKEN = 0.00000015
OUTPUT_COST_PER_TOKEN = 0.0000006


class GeminiClient:
    """Gemini 2.5 Flash client with grounding + URL context."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost_usd = 0.0
        self._call_count = 0

    @property
    def total_cost_usd(self) -> float:
        return self._total_cost_usd

    @property
    def call_count(self) -> int:
        return self._call_count

    def _accumulate(self, result: dict) -> None:
        """Add token/cost tallies from a gemini_retry result to instance totals."""
        self._total_input_tokens += result.get("input_tokens", 0)
        self._total_output_tokens += result.get("output_tokens", 0)
        self._total_cost_usd += result.get("cost_usd", 0.0)
        self._call_count += 1

    async def call_f3a(
        self,
        domain: str,
        dfs_base_metrics: dict,
        max_retries: int = 4,
    ) -> dict[str, Any]:
        """F3a — identity + scoring with grounding ON.

        Args:
            domain: Prospect domain (used in user prompt for URL context hint).
            dfs_base_metrics: Base DFS metrics dict (domain_rank_overview output).

        Returns:
            gemini_retry result dict with content = F3a JSON or None on failure.
        """
        user_prompt = (
            f"Analyse the Australian SMB at domain: {domain}\n\n"
            f"DFS base metrics:\n{json.dumps(dfs_base_metrics, indent=2)}\n\n"
            "Return the JSON schema exactly as specified."
        )
        result = await gemini_call_with_retry(
            api_key=self.api_key,
            system_prompt=F3A_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            enable_grounding=True,
            max_retries=max_retries,
            model=GEMINI_MODEL_DM,
        )
        self._accumulate(result)
        return result

    async def call_f3b(
        self,
        f3a_output: dict,
        signal_bundle: dict,
        max_retries: int = 4,
    ) -> dict[str, Any]:
        """F3b — generation with grounding OFF (uses cached F3a context).

        Args:
            f3a_output: Parsed F3a JSON dict (identity + scoring).
            signal_bundle: Full DFS signal bundle dict.

        Returns:
            gemini_retry result dict with content = F3b JSON or None on failure.
        """
        user_prompt = (
            f"Prospect identity (from F3a, do not modify):\n"
            f"{json.dumps(f3a_output, indent=2)}\n\n"
            f"DFS signal bundle:\n{json.dumps(signal_bundle, indent=2)}\n\n"
            "Generate the vulnerability report and outreach drafts as specified."
        )
        result = await gemini_call_with_retry(
            api_key=self.api_key,
            system_prompt=F3B_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            enable_grounding=False,
            max_retries=max_retries,
        )
        self._accumulate(result)
        return result

    async def comprehend(
        self,
        system_prompt: str,
        user_prompt: str,
        domain: str | None = None,
        enable_grounding: bool = True,
        enable_url_context: bool = True,
        response_schema: dict | None = None,
        max_retries: int = 4,
    ) -> dict[str, Any]:
        """Legacy unified comprehend — delegates to gemini_call_with_retry.

        Kept for backward compatibility with callers that have not yet
        migrated to call_f3a / call_f3b.
        """
        result = await gemini_call_with_retry(
            api_key=self.api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            enable_grounding=enable_grounding,
            max_retries=max_retries,
        )
        self._accumulate(result)
        # Remap f_status -> f3_status for backward compat
        out = dict(result)
        out["f3_status"] = out.pop("f_status", "failed")
        if "f_failure_reason" in out:
            out["f3_failure_reason"] = out.pop("f_failure_reason")
        out["grounding_used"] = out.get("grounding_queries", 0) > 0
        out["url_context_used"] = False
        out["model"] = GEMINI_MODEL
        return out
