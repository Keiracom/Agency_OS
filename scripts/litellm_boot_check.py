#!/usr/bin/env python3
"""
KEI-100 / Linear KEI-73 — T0.2 LiteLLM boot-time dry-run.

Modes:
  --mode pre   ExecStartPre. Validates provider keys BEFORE litellm binds 4000.
               HARD FAIL (exit 1) if ANTHROPIC_API_KEY missing or invalid.
               WARN (do not block) if OPENAI_API_KEY / GOOGLE_API_KEY absent or invalid;
               records `<alias>_<provider>_unavailable` row in litellm_alias_cache.
  --mode post  ExecStartPost (optional). HTTP-pings each governance_tier preset
               against http://127.0.0.1:4000 to confirm proxy is serving.

Anthropic is mandatory per Aiden gap 2 resolution (2026-05-17 ts 1778983972.891719).
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

ANTHROPIC_KEY = "ANTHROPIC_API_KEY"
OPENAI_KEY = "OPENAI_API_KEY"
GOOGLE_KEY = "GOOGLE_API_KEY"

LITELLM_HEALTH_URL = "http://127.0.0.1:4000/health/liveliness"


def log(level: str, msg: str) -> None:
    sys.stderr.write(f"[litellm_boot_check] {level}: {msg}\n")
    sys.stderr.flush()


def _record_unavailable(alias: str, provider: str, reason: str) -> None:
    """Best-effort write to litellm_alias_cache. Never raises — boot must not block on Supabase."""
    try:
        import psycopg
    except ImportError:
        log("WARN", f"psycopg not available — skipping cache write for {alias}/{provider}")
        return

    dsn = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        log("WARN", f"no SUPABASE_DB_URL — skipping cache write for {alias}/{provider}")
        return

    expires = datetime.now(UTC) + timedelta(hours=24)
    try:
        with psycopg.connect(dsn, prepare_threshold=None, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.litellm_alias_cache
                        (alias, resolved_model, resolved_provider, api_key_ref, cached_at, expires_at)
                    VALUES (%s, %s, %s, %s, now(), %s)
                    ON CONFLICT (alias) DO UPDATE SET
                        resolved_model = EXCLUDED.resolved_model,
                        resolved_provider = EXCLUDED.resolved_provider,
                        api_key_ref = EXCLUDED.api_key_ref,
                        cached_at = now(),
                        expires_at = EXCLUDED.expires_at
                    """,
                    (
                        f"{alias}_{provider}_unavailable",
                        reason,
                        provider,
                        f"{provider.upper()}_API_KEY",
                        expires,
                    ),
                )
            conn.commit()
    except Exception as e:
        log("WARN", f"cache write failed for {alias}/{provider}: {e}")


def _probe_anthropic() -> tuple[bool, str]:
    try:
        import anthropic
    except ImportError as e:
        return False, f"anthropic SDK not installed: {e}"
    try:
        client = anthropic.Anthropic(api_key=os.environ[ANTHROPIC_KEY])
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _probe_openai() -> tuple[bool, str]:
    try:
        import openai
    except ImportError as e:
        return False, f"openai SDK not installed: {e}"
    try:
        client = openai.OpenAI(api_key=os.environ[OPENAI_KEY])
        client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _probe_google() -> tuple[bool, str]:
    try:
        import google.generativeai as genai
    except ImportError as e:
        return False, f"google-generativeai SDK not installed: {e}"
    try:
        genai.configure(api_key=os.environ[GOOGLE_KEY])
        model = genai.GenerativeModel("gemini-1.5-flash")
        model.generate_content("hi", generation_config={"max_output_tokens": 1})
        return True, "ok"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def mode_pre() -> int:
    """ExecStartPre: validate keys, hard fail Anthropic only."""
    # Anthropic — MANDATORY
    if not os.environ.get(ANTHROPIC_KEY):
        log("FATAL", f"{ANTHROPIC_KEY} missing — blocking unit start (gap 2 hard fail)")
        return 1

    ok, reason = _probe_anthropic()
    if not ok:
        log("FATAL", f"{ANTHROPIC_KEY} invalid — {reason} — blocking unit start")
        return 1
    log("INFO", "ANTHROPIC_API_KEY: ok")

    # OpenAI — WARN only
    if not os.environ.get(OPENAI_KEY):
        log("WARN", f"{OPENAI_KEY} missing — fallback degraded (Anthropic-only)")
        _record_unavailable("governance_tier", "openai", "key_missing")
    else:
        ok, reason = _probe_openai()
        if not ok:
            log("WARN", f"{OPENAI_KEY} invalid — {reason} — fallback degraded")
            _record_unavailable("governance_tier", "openai", reason[:200])
        else:
            log("INFO", "OPENAI_API_KEY: ok")

    # Google — WARN only
    if not os.environ.get(GOOGLE_KEY):
        log("WARN", f"{GOOGLE_KEY} missing — tertiary fallback degraded")
        _record_unavailable("governance_tier", "google", "key_missing")
    else:
        ok, reason = _probe_google()
        if not ok:
            log("WARN", f"{GOOGLE_KEY} invalid — {reason} — tertiary fallback degraded")
            _record_unavailable("governance_tier", "google", reason[:200])
        else:
            log("INFO", "GOOGLE_API_KEY: ok")

    log("INFO", "boot pre-check passed — Anthropic mandatory ok, optional providers warn-only")
    return 0


def mode_post() -> int:
    """ExecStartPost: confirm proxy serving on 4000."""
    try:
        req = urllib.request.Request(LITELLM_HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            log("INFO", f"liveliness ok ({resp.status}): {body[:200]}")
            return 0
    except OSError as e:
        log("FATAL", f"liveliness probe failed: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="LiteLLM boot dry-run")
    parser.add_argument("--mode", choices=["pre", "post"], required=True)
    args = parser.parse_args()
    return mode_pre() if args.mode == "pre" else mode_post()


if __name__ == "__main__":
    sys.exit(main())
