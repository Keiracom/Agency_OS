#!/usr/bin/env python3
"""cognee_kuzu_capped_launcher.py — KEI-77 fix.

Cognee 1.0.9's ladybug adapter hard-codes `max_db_size=4 GB` in 4 places
(`infrastructure/databases/graph/ladybug/adapter.py` lines 93, 127, 148,
181). Kuzu mmap()'s the full max_db_size at Database init, which collides
with the KEI-44 3 GB cgroup cap on cognee.service: every add()/cognify()
fails with `Buffer manager exception: Mmap for size 4294967296 failed`
(4294967296 == 4 GB exact). 1382 consecutive failures observed in
~/.cognee/logs/2026-05-13_20-53-51.log on 2026-05-13 21:27, no successful
writes since.

This launcher monkey-patches `ladybug.database.Database.__init__` to clamp
`max_db_size` and `buffer_pool_size` from env, then exec's uvicorn. Patch
survives pip upgrades because it runs at process start, not in-source.

Env (set in cognee.service unit):
    COGNEE_KUZU_MAX_DB_SIZE_MB     default 1024  (was 4096, now fits 3G cap)
    COGNEE_KUZU_BUFFER_POOL_MB     default 768   (was 2048, give DB headroom)

The 1 GB max_db_size + 768 MB buffer pool + cognee runtime (~800 MB peak
per `systemctl --user status cognee` observed RSS) = ~2.5 GB, well inside
the 3 GB cgroup ceiling.
"""

from __future__ import annotations

import os
import sys

# Provider → env-var that typically holds the key for that provider.
# Cognee/LiteLLM expects LLM_API_KEY + EMBEDDING_API_KEY, but our .env stores
# secrets under provider-specific names (GEMINI_API_KEY etc) so they're not
# duplicated. This mapping bridges that at launch (KEI-81).
_PROVIDER_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
}


def _map_provider_key(target_env: str, provider_env: str) -> None:
    """If `target_env` is unset/empty but the configured provider has a
    matching `<PROVIDER>_API_KEY` env var, copy it across. Idempotent;
    skip when target already has a non-empty value (operator override wins).
    """
    if os.environ.get(target_env, "").strip():
        return
    provider = (os.environ.get(provider_env, "") or "").strip().lower()
    source_env = _PROVIDER_KEY_ENV.get(provider)
    if not source_env:
        return
    source_val = os.environ.get(source_env, "").strip()
    if not source_val:
        return
    os.environ[target_env] = source_val
    print(
        f"[cognee_kuzu_capped_launcher] mapped {target_env}={source_env} "
        f"(provider={provider})",
        file=sys.stderr,
    )


def _apply_key_mapping() -> None:
    """Map provider-specific keys to LiteLLM-expected LLM_API_KEY +
    EMBEDDING_API_KEY. KEI-81 fix.
    """
    _map_provider_key("LLM_API_KEY", "LLM_PROVIDER")
    _map_provider_key("EMBEDDING_API_KEY", "EMBEDDING_PROVIDER")


def _apply_patch() -> None:
    """Monkey-patch ladybug.database.Database.__init__ to clamp sizes."""
    max_db_mb = int(os.environ.get("COGNEE_KUZU_MAX_DB_SIZE_MB", "1024"))
    pool_mb = int(os.environ.get("COGNEE_KUZU_BUFFER_POOL_MB", "768"))
    max_db_bytes = max_db_mb * 1024 * 1024
    pool_bytes = pool_mb * 1024 * 1024

    try:
        from ladybug.database import Database
    except ImportError:
        print("WARNING: ladybug not importable; patch skipped", file=sys.stderr)
        return

    original_init = Database.__init__

    def capped_init(self, *args, **kwargs):
        # Clamp caller's value to our ceiling (don't expand, only shrink).
        requested_max = kwargs.get("max_db_size", max_db_bytes) or max_db_bytes
        kwargs["max_db_size"] = min(requested_max, max_db_bytes)
        requested_pool = kwargs.get("buffer_pool_size", pool_bytes) or pool_bytes
        kwargs["buffer_pool_size"] = min(requested_pool, pool_bytes)
        return original_init(self, *args, **kwargs)

    Database.__init__ = capped_init
    print(
        f"[cognee_kuzu_capped_launcher] patched: max_db_size<= {max_db_mb}MB, "
        f"buffer_pool_size<= {pool_mb}MB",
        file=sys.stderr,
    )


def main() -> int:
    _apply_key_mapping()
    _apply_patch()
    # Exec uvicorn with the patched runtime. sys.executable + `-m uvicorn` so
    # the launcher works under systemd (where PATH doesn't include the venv's
    # bin/ dir, and bare `uvicorn` is FileNotFoundError). Using -m also keeps
    # cognee.service PID singular — execvp replaces the launcher process.
    args = [
        sys.executable,
        "-m", "uvicorn",
        "cognee.api.client:app",
        "--host", os.environ.get("COGNEE_HOST", "127.0.0.1"),
        "--port", os.environ.get("COGNEE_PORT", "8000"),
    ]
    os.execvp(args[0], args)


if __name__ == "__main__":
    raise SystemExit(main())
