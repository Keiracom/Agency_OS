"""
OpenAI cost logger — append-only JSONL for all OpenAI API calls in the listener subsystem.
F4-PART2-SETUP: 7 days of data collection before budget trigger ratification.
"""

import json
import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

COST_LOG_PATH = "/home/elliotbot/clawd/logs/openai-cost.jsonl"

# OpenAI pricing (USD) as of 2025-05 — update if pricing changes
PRICING = {
    "text-embedding-3-small": {"input": 0.02 / 1_000_000},  # $0.02/1M tokens
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},  # $0.15/$0.60 per 1M
}


def log_openai_call(
    callsign: str,
    use_case: str,
    model: str,
    input_tokens: int,
    output_tokens: int = 0,
) -> None:
    """Append one cost event to the JSONL log. Best-effort, never raises."""
    try:
        pricing = PRICING.get(model, {})
        cost_usd = input_tokens * pricing.get("input", 0) + output_tokens * pricing.get("output", 0)
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "callsign": callsign,
            "use_case": use_case,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": round(cost_usd, 8),
        }
        with open(COST_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning(f"[openai-cost] log write failed: {exc}")
