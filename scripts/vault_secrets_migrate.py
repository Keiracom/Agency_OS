#!/usr/bin/env python3
"""vault_secrets_migrate.py — Phase 1 of the vault_secrets full migration.

Seeds the env-only service secrets into Vault KV v2 under the convention
secret/keiracom/<service>/<key> = {"value": <env value>}, matching kv_resolver's
SECRET_MANIFEST. Idempotent: skips a path that already exists (unless --overwrite)
and skips any env var that is absent/empty. Dual-read stays intact — this only
ADDS to Vault; nothing is removed from .env in this phase.

Ratified scope (Elliot 2026-06-03): staged migration, bootstrap allowlist =
{VAULT_ADDR, VAULT_TOKEN} only. Frontend/build-time vars are NOT agent-spawn
secrets and are excluded here (flagged for Vercel env separately).

Usage:
  python3 scripts/vault_secrets_migrate.py            # dry-run (report only)
  python3 scripts/vault_secrets_migrate.py --apply    # write missing secrets
  python3 scripts/vault_secrets_migrate.py --apply --overwrite
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib import error as urlerror
from urllib import request as urlrequest

# env_var -> (service, key). Mirrors kv_resolver.SECRET_MANIFEST convention.
# These are the manifest-gap service secrets found by the Phase 1 audit.
MIGRATE: dict[str, tuple[str, str]] = {
    "APOLLO_API_KEY": ("apollo", "api_key"),
    "BETTERSTACK_API_KEY": ("betterstack", "api_key"),
    "BRAVE_API_KEY": ("brave", "api_key"),
    "COO_BOT_TOKEN": ("telegram", "coo_bot_token"),
    "CREDENTIAL_ENCRYPTION_KEY": ("internal", "credential_encryption_key"),
    "CSB_API_KEY": ("csb", "api_key"),
    "DISPATCHER_JWT_SECRET": ("dispatcher", "jwt_secret"),
    "EMBEDDING_API_KEY": ("embedding", "api_key"),
    "GEMINI_API_KEY_BACKUP": ("gemini", "api_key_backup"),
    "GITHUB_TOKEN": ("github", "token"),
    "GOOGLE_API_KEY": ("google", "api_key"),
    "GOOGLE_CLIENT_SECRET": ("google", "client_secret"),
    "GOOGLE_GMAIL_CLIENT_SECRET": ("google", "gmail_client_secret"),
    "HEYREACH_API_KEY": ("heyreach", "api_key"),
    "LINEAR_API_KEY": ("linear", "api_key"),
    "LLM_API_KEY": ("llm", "api_key"),
    "MEM0_API_KEY": ("mem0", "api_key"),
    "NAMECHEAP_API_KEY": ("namecheap", "api_key"),
    "OPENROUTER_API_KEY": ("openrouter", "api_key"),
    "PROSPEO_API_KEY": ("prospeo", "api_key"),
    "SALESFORGE_API_KEY": ("salesforge", "api_key"),
    "SLACK_BOT_TOKEN": ("slack", "bot_token"),
    "SLACK_ENFORCER_APP_TOKEN": ("slack", "enforcer_app_token"),
    "STRIPE_SECRET_KEY": ("stripe", "secret_key"),  # in manifest, missing in Vault
    "SUPABASE_ACCESS_TOKEN": ("supabase", "access_token"),
    "UNIPILE_API_KEY": ("unipile", "api_key"),
    "UPSTASH_API_KEY": ("upstash", "api_key"),
    "VAPI_API_KEY": ("vapi", "api_key"),
    "VERCEL_TOKEN": ("vercel", "token"),
    "VULTR_API_KEY": ("vultr", "api_key"),
    "WEBSHARE_API_KEY": ("webshare", "api_key"),
    "YOUTUBE_CLIENT_SECRET": ("youtube", "client_secret"),
    "ZEROBOUNCE_API_KEY": ("zerobounce", "api_key"),
}

# Aliases — point at an EXISTING Vault path; do not seed a new value.
ALIASES: dict[str, tuple[str, str]] = {
    "SUPABASE_DB_DSN": ("supabase", "database_url"),   # env comment: copied from DATABASE_URL
    "OPENAI_APIKEY": ("openai", "api_key"),            # typo-variant of OPENAI_API_KEY
}

# Excluded from agent-spawn manifest (frontend/build-time → Vercel env).
FRONTEND_FLAGGED = [
    "NEXT_PUBLIC_PLASMIC_PROJECT_API_TOKEN", "PLASMIC_PREVIEW_SECRET",
    "EXPO_TOKEN", "V0_API_KEY",
]

# Bootstrap allowlist — permitted to remain in .env (ratified).
BOOTSTRAP_ALLOWLIST = ["VAULT_ADDR", "VAULT_TOKEN"]


def _put(addr: str, token: str, service: str, key: str, value: str) -> None:
    path = f"{addr.rstrip('/')}/v1/secret/data/keiracom/{service}/{key}"
    body = json.dumps({"data": {"value": value}}).encode()
    req = urlrequest.Request(
        path, data=body, method="POST",
        headers={"X-Vault-Token": token, "Content-Type": "application/json"},
    )
    urlrequest.urlopen(req, timeout=10).read()


def _exists(addr: str, token: str, service: str, key: str) -> bool:
    path = f"{addr.rstrip('/')}/v1/secret/data/keiracom/{service}/{key}"
    req = urlrequest.Request(path, headers={"X-Vault-Token": token})
    try:
        urlrequest.urlopen(req, timeout=10).read()
        return True
    except urlerror.HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write (default: dry-run)")
    ap.add_argument("--overwrite", action="store_true", help="overwrite existing paths")
    args = ap.parse_args()

    addr, token = os.environ.get("VAULT_ADDR"), os.environ.get("VAULT_TOKEN")
    if not addr or not token:
        print("ERROR: VAULT_ADDR + VAULT_TOKEN required", file=sys.stderr)
        return 3

    seeded, skipped_present, skipped_empty = [], [], []
    for env_var, (service, key) in MIGRATE.items():
        val = os.environ.get(env_var, "")
        if not val:
            skipped_empty.append(env_var)
            continue
        if not args.overwrite and _exists(addr, token, service, key):
            skipped_present.append(f"{env_var} -> {service}/{key}")
            continue
        if args.apply:
            _put(addr, token, service, key, val)
        seeded.append(f"{env_var} -> {service}/{key}")

    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"=== vault_secrets_migrate ({mode}) ===")
    print(f"seeded ({len(seeded)}):")
    for s in seeded:
        print(f"  + {s}")
    print(f"already-present, skipped ({len(skipped_present)}):")
    for s in skipped_present:
        print(f"  = {s}")
    print(f"absent/empty in env, skipped ({len(skipped_empty)}): {skipped_empty}")
    print(f"aliases (manifest reuse, not seeded): {list(ALIASES)}")
    print(f"frontend-flagged (move to Vercel, NOT agent manifest): {FRONTEND_FLAGGED}")
    print(f"bootstrap allowlist (stay in .env): {BOOTSTRAP_ALLOWLIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
