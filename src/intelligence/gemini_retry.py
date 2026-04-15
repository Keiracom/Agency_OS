"""Shared Gemini retry helper. Used by Stage 3 IDENTIFY, Stage 7 ANALYSE, Stage 10 VR+MSG.

Extracted from gemini_client.py to allow reuse across multiple callers
without class state. Standalone async function with exponential backoff.

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random

import httpx

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_MODEL_DM = "gemini-3.1-pro-preview"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

INPUT_COST = 0.00000015   # per token
OUTPUT_COST = 0.0000006   # per token


async def gemini_call_with_retry(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    enable_grounding: bool = True,
    max_retries: int = 4,
    max_output_tokens: int = 16384,
    temperature: float = 0.3,
    model: str | None = None,
) -> dict:
    """Call Gemini with exponential backoff retry.

    Returns:
        {
            content (dict|None): parsed JSON or None on failure,
            raw_text (str): last raw model output,
            input_tokens (int): cumulative across retries,
            output_tokens (int): cumulative across retries,
            cost_usd (float): cumulative cost across retries,
            grounding_queries (int): number of grounding queries used,
            attempt (int): final attempt number,
            f_status (str): "success" | "failed",
            f_failure_reason (str|None): reason string on failure,
        }
    """
    effective_model = model or GEMINI_MODEL
    url = f"{GEMINI_BASE}/models/{effective_model}:generateContent?key={api_key}"

    tools = []
    if enable_grounding:
        tools.append({"google_search": {}})

    total_in = total_out = 0
    total_cost = 0.0
    last_error = None
    last_raw = ""

    for attempt in range(1, max_retries + 1):
        effective_prompt = user_prompt
        if attempt > 1:
            effective_prompt += (
                "\n\nIMPORTANT: Return ONLY valid JSON. "
                "No prose, no markdown, no preamble."
            )

        payload: dict = {
            "contents": [{"parts": [{"text": effective_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(url, json=payload)

            if resp.status_code == 429:
                wait = 2 ** attempt + random.random()
                logger.warning("Gemini 429 attempt %d, backoff %.1fs", attempt, wait)
                await asyncio.sleep(wait)
                continue

            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                wait = 2 ** attempt + random.random()
                logger.warning(
                    "Gemini error attempt %d: %s, backoff %.1fs",
                    attempt, last_error, wait,
                )
                await asyncio.sleep(wait)
                continue

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                last_error = "no candidates"
                continue

            usage = data.get("usageMetadata", {})
            in_tok = usage.get("promptTokenCount", 0)
            out_tok = usage.get("candidatesTokenCount", 0)
            cost = in_tok * INPUT_COST + out_tok * OUTPUT_COST
            total_in += in_tok
            total_out += out_tok
            total_cost += cost

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            last_raw = text

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

            if parsed and isinstance(parsed, dict):
                return {
                    "content": parsed,
                    "raw_text": text,
                    "input_tokens": total_in,
                    "output_tokens": total_out,
                    "cost_usd": round(total_cost, 6),
                    "grounding_queries": len(
                        grounding_meta.get("webSearchQueries", [])
                    ),
                    "attempt": attempt,
                    "f_status": "success",
                    "f_failure_reason": None,
                }

            if attempt < max_retries:
                reason = (
                    "prose_response"
                    if not text.strip().startswith("{") and "```" not in text
                    else "json_parse_failure"
                )
                wait = 2 ** attempt + random.random()
                logger.warning(
                    "Gemini %s attempt %d, backoff %.1fs", reason, attempt, wait
                )
                await asyncio.sleep(wait)
                continue

        except httpx.TimeoutException:
            last_error = "timeout"
            wait = 2 ** attempt + random.random()
            await asyncio.sleep(wait)

    # All retries exhausted
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
        "grounding_queries": 0,
        "attempt": max_retries,
        "f_status": "failed",
        "f_failure_reason": reason,
    }
