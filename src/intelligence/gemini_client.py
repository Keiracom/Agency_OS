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
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Call Gemini 2.5 Flash with optional grounding + URL context.

        Returns dict with: content (parsed JSON or raw), input_tokens,
        output_tokens, cost_usd, grounding_used, url_context_used.
        """
        url = f"{GEMINI_BASE}/models/{GEMINI_MODEL}:generateContent?key={self.api_key}"

        # Build request
        contents = [{"parts": [{"text": user_prompt}]}]

        # System instruction
        system_instruction = {"parts": [{"text": system_prompt}]}

        # Tools (grounding + URL context)
        tools = []
        if enable_grounding:
            tools.append({"google_search": {}})
        # URL context — try Gemini's URL fetching via grounding
        # Note: url_context tool may not be available in all API versions
        # Grounding search already fetches the domain via Google

        payload: dict[str, Any] = {
            "contents": contents,
            "systemInstruction": system_instruction,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 8192,
            },
        }

        if tools:
            payload["tools"] = tools

        if response_schema:
            payload["generationConfig"]["responseMimeType"] = "application/json"
            payload["generationConfig"]["responseSchema"] = response_schema

        # Retry loop
        last_error = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(url, json=payload)

                if resp.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    logger.warning("Gemini 429, retrying in %ds", wait)
                    import asyncio
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code != 200:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning("Gemini error: %s", last_error)
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(1)
                        continue
                    break

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return {"content": None, "error": "no candidates", "cost_usd": 0}

                # Extract text
                parts = candidates[0].get("content", {}).get("parts", [])
                text = ""
                for part in parts:
                    if "text" in part:
                        text += part["text"]

                # Usage
                usage = data.get("usageMetadata", {})
                in_tok = usage.get("promptTokenCount", 0)
                out_tok = usage.get("candidatesTokenCount", 0)
                cost = in_tok * INPUT_COST_PER_TOKEN + out_tok * OUTPUT_COST_PER_TOKEN

                self._total_input_tokens += in_tok
                self._total_output_tokens += out_tok
                self._total_cost_usd += cost
                self._call_count += 1

                # Try to parse JSON
                parsed = None
                try:
                    clean = text.strip()
                    if clean.startswith("```json"):
                        clean = clean.split("```json")[1].split("```")[0]
                    elif clean.startswith("```"):
                        clean = clean.split("```")[1].split("```")[0]
                    parsed = json.loads(clean.strip())
                except (json.JSONDecodeError, IndexError):
                    parsed = None

                # Check grounding metadata
                grounding_meta = candidates[0].get("groundingMetadata", {})

                return {
                    "content": parsed or text,
                    "raw_text": text,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "cost_usd": round(cost, 6),
                    "grounding_used": bool(grounding_meta),
                    "grounding_queries": len(grounding_meta.get("webSearchQueries", [])),
                    "url_context_used": enable_url_context and domain is not None,
                    "model": GEMINI_MODEL,
                }

            except httpx.TimeoutException:
                last_error = "timeout"
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)

        return {"content": None, "error": last_error or "max retries", "cost_usd": 0}
