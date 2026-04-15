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

        # Step 2: Verify DM is the correct LOCAL AU decision-maker
        content = result.get("content")
        if result.get("f_status") == "success" and content:
            dm = (content.get("dm_candidate") or {}).get("name")
            if dm and dm.lower() not in ("null", "none", ""):
                result = await self._verify_dm(domain, content, result, max_retries)

        return result

    async def _verify_dm(
        self,
        domain: str,
        f3a_content: dict,
        f3a_result: dict,
        max_retries: int = 4,
    ) -> dict[str, Any]:
        """Step 2: Verify DM is the correct LOCAL Australian decision-maker."""
        biz = f3a_content.get("business_name", "unknown")
        dm = (f3a_content.get("dm_candidate") or {}).get("name", "")
        role = (f3a_content.get("dm_candidate") or {}).get("role", "")

        verify_system = (
            "You are verifying a decision-maker identification for an Australian SMB. "
            "Return ONLY valid JSON.\n\n"
            "Check: Is this person the LOCAL Australian decision-maker for this specific business? "
            "If this is an international brand with a local Australian operation (distributor, licensee, "
            "franchisee), identify the LOCAL director instead. Check ABN registry for the entity behind "
            "this domain.\n\n"
            '{"dm_verified": true, "dm_candidate": {"name": "verified or corrected name", '
            '"role": "title"}, "entity_name": "registered AU company", '
            '"verification_note": "why verified or changed"}\n\n'
            "If the original DM is correct for the Australian operation, return dm_verified: true "
            "with the same name. If wrong, return dm_verified: false with the corrected local DM."
        )
        verify_prompt = (
            f"Domain: {domain}\n"
            f"Business: {biz}\n"
            f"DM candidate: {dm} ({role})\n\n"
            "Verify this is the correct LOCAL Australian decision-maker."
        )

        v_result = await gemini_call_with_retry(
            api_key=self.api_key,
            system_prompt=verify_system,
            user_prompt=verify_prompt,
            enable_grounding=True,
            max_retries=max_retries,
            model=GEMINI_MODEL_DM,
        )
        self._accumulate(v_result)

        v_content = v_result.get("content")
        if not v_content or v_result.get("f_status") != "success":
            return f3a_result  # verification failed, trust step 1

        verified = v_content.get("dm_verified")
        corrected_dm = (v_content.get("dm_candidate") or {}).get("name")
        corrected_role = (v_content.get("dm_candidate") or {}).get("role")

        if str(verified).lower() == "true":
            # Confirmed — keep original
            f3a_result["content"]["_dm_verified"] = True
            f3a_result["content"]["_dm_verification_note"] = v_content.get("verification_note", "")
            return f3a_result

        if corrected_dm and corrected_dm != dm:
            # Corrected — update DM in f3a content
            logger.info("DM CORRECTED for %s: %s → %s (%s)", domain, dm, corrected_dm, v_content.get("verification_note", ""))
            f3a_result["content"]["dm_candidate"]["name"] = corrected_dm
            if corrected_role:
                f3a_result["content"]["dm_candidate"]["role"] = corrected_role
            f3a_result["content"]["_dm_verified"] = True
            f3a_result["content"]["_dm_corrected_from"] = dm
            f3a_result["content"]["_dm_verification_note"] = v_content.get("verification_note", "")
            if v_content.get("entity_name"):
                f3a_result["content"]["_entity_name"] = v_content["entity_name"]

        return f3a_result

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
