"""
FILE: src/memory/client.py
PURPOSE: Lazy Supabase HTTP client config for the memory layer.
         No OpenAI — v1 is text+tag+type only.
"""

import os


def _supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL", "")
    if not url:
        raise RuntimeError("SUPABASE_URL not set in environment")
    return url.rstrip("/")


def _supabase_headers() -> dict[str, str]:
    key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_KEY (or SUPABASE_KEY) not set in environment")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


MEMORIES_ENDPOINT = "/rest/v1/agent_memories"
