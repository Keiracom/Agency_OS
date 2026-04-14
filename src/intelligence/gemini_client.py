"""
Gemini 2.5 Flash client for Pipeline F.

Features:
- URL context (fetch prospect domain)
- Google Search grounding
- Context caching on system prompt
- response_schema JSON mode
- Retry with backoff
- Cost tracking

Ratified: 2026-04-14. Pipeline F architecture.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Pricing (USD per token, Gemini 2.5 Flash)
# Under 200K context: $0.15/1M input, $0.60/1M output (text)
# With thinking: $0.70/1M thinking output
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
        """
        Call Gemini 2.5 Flash with optional grounding.

        Retry with exponential backoff + jitter on:
        - HTTP 429 (rate limit)
        - JSON parse failure (non-deterministic prose response)
        - Malformed JSON (truncation)

        Returns dict with: content (parsed JSON or raw), input_tokens,
        output_tokens, cost_usd, grounding_used, attempt, f3_status,
        f3_failure_reason.
        """
        import asyncio as _asyncio
        import random as _random

        url = f"{GEMINI_BASE}/models/{GEMINI_MODEL}:generateContent?key={self.api_key}"

        tools = []
        if enable_grounding:
            tools.append({"google_search": {}})

        total_in = total_out = 0
        total_cost = 0.0
        last_error = None
        last_raw = ""

        for attempt in range(1, max_retries + 1):
            # On retry: reinforce JSON-only instruction
            effective_prompt = user_prompt
            if attempt > 1:
                effective_prompt += "\n\nIMPORTANT: Return ONLY valid JSON. No prose, no markdown, no preamble."

            payload: dict[str, Any] = {
                "contents": [{"parts": [{"text": effective_prompt}]}],
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 16384},
            }
            if tools:
                payload["tools"] = tools
            if response_schema:
                payload["generationConfig"]["responseMimeType"] = "application/json"
                payload["generationConfig"]["responseSchema"] = response_schema

            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    resp = await client.post(url, json=payload)

                if resp.status_code == 429:
                    wait = 2 ** attempt + _random.random()
                    logger.warning("Gemini 429 attempt %d, backoff %.1fs", attempt, wait)
                    await _asyncio.sleep(wait)
                    continue

                if resp.status_code != 200:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    wait = 2 ** attempt + _random.random()
                    logger.warning("Gemini error attempt %d: %s, backoff %.1fs", attempt, last_error, wait)
                    await _asyncio.sleep(wait)
                    continue

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    last_error = "no candidates"
                    continue

                # Track usage across retries
                usage = data.get("usageMetadata", {})
                in_tok = usage.get("promptTokenCount", 0)
                out_tok = usage.get("candidatesTokenCount", 0)
                cost = in_tok * INPUT_COST_PER_TOKEN + out_tok * OUTPUT_COST_PER_TOKEN
                total_in += in_tok; total_out += out_tok; total_cost += cost

                # Extract text
                parts = candidates[0].get("content", {}).get("parts", [])
                text = ""
                for part in parts:
                    if "text" in part:
                        text += part["text"]
                last_raw = text

                # Try to parse JSON
                parsed = None
                try:
                    clean = text.strip()
                    if clean.startswith("```json"):
                        clean = clean.split("```json")[1].split("```")[0]
                    elif clean.startswith("```"):
                        clean = clean.split("```")[1].split("```")[0]
                    parsed = json.loads(clean.strip())
                except (json.JSONDecodeError, IndexError) as je:
                    parsed = None
                    last_error = f"json_parse: {je}"

                grounding_meta = candidates[0].get("groundingMetadata", {})

                if parsed and isinstance(parsed, dict) and parsed.get("s2_identity"):
                    # SUCCESS — update totals and return
                    self._total_input_tokens += total_in
                    self._total_output_tokens += total_out
                    self._total_cost_usd += total_cost
                    self._call_count += 1
                    return {
                        "content": parsed,
                        "raw_text": text,
                        "input_tokens": total_in,
                        "output_tokens": total_out,
                        "cost_usd": round(total_cost, 6),
                        "grounding_used": bool(grounding_meta),
                        "grounding_queries": len(grounding_meta.get("webSearchQueries", [])),
                        "url_context_used": False,
                        "model": GEMINI_MODEL,
                        "attempt": attempt,
                        "f3_status": "success",
                    }

                # JSON parse failed or missing s2_identity — retry with backoff
                if attempt < max_retries:
                    reason = "prose_response" if not text.strip().startswith("{") and "```" not in text else "json_parse_failure"
                    wait = 2 ** attempt + _random.random()
                    logger.warning("F3 %s attempt %d for %s, backoff %.1fs", reason, attempt, domain, wait)
                    await _asyncio.sleep(wait)
                    continue

            except httpx.TimeoutException:
                last_error = "timeout"
                wait = 2 ** attempt + _random.random()
                await _asyncio.sleep(wait)

        # All retries exhausted — classify failure
        self._total_input_tokens += total_in
        self._total_output_tokens += total_out
        self._total_cost_usd += total_cost
        self._call_count += 1

        # Classify failure reason
        if "429" in (last_error or ""):
            reason = "rate_limit"
        elif last_raw and not last_raw.strip().startswith("{") and "```" not in last_raw:
            reason = "prose_response"
        elif "json_parse" in (last_error or ""):
            reason = "json_truncation"
        else:
            reason = "unknown"

        return {
            "content": None,
            "raw_text": last_raw,
            "input_tokens": total_in,
            "output_tokens": total_out,
            "cost_usd": round(total_cost, 6),
            "grounding_used": False,
            "grounding_queries": 0,
            "url_context_used": False,
            "model": GEMINI_MODEL,
            "attempt": max_retries,
            "f3_status": "failed",
            "f3_failure_reason": reason,
            "error": last_error,
        }
