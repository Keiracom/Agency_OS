"""kv_resolver.py — cold-start credential resolution from Vault KV v2 (P10 / Agency_OS-xlpe).

A FRESH process (launched `env -i` with ONLY VAULT_ADDR + VAULT_TOKEN, no .env
inheritance) calls `resolve_into_env()` to pull every fleet secret from Vault
KV v2 and populate os.environ — so the rest of the codebase reads creds exactly
as before, but the source is Vault, not an inherited .env.

Vault is canonical for internal service creds (ceo:keiracom_architecture_v2_locked
Cat 16; .env is legacy-only). Convention (ratified w/ Atlas, bd 8dvl):
  secret/keiracom/<service>/<key>   (KV v2 → read at /v1/secret/data/keiracom/<service>/<key>)
each holding a single field `value`. SECRET_MANIFEST is the shared contract
between this reader, the provisioner, and Atlas's spawn-path bootstrap.

This is the KV-secrets engine — NOT Vault Transit (vault_decryptor.py is the
BYOK envelope-decrypt path; wrong engine for static service creds).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger(__name__)

KV_MOUNT = "secret"  # KV v2 mount
KEIRACOM_PREFIX = "keiracom"
DEFAULT_TIMEOUT = 10.0


# (env_var, service, key) — secret/keiracom/<service>/<key> holds {"value": <env_var value>}.
SECRET_MANIFEST: tuple[tuple[str, str, str], ...] = (
    # Postgres / Supabase
    ("DATABASE_URL", "supabase", "database_url"),
    ("DATABASE_URL_MIGRATIONS", "supabase", "database_url_migrations"),
    ("SUPABASE_URL", "supabase", "url"),
    ("SUPABASE_SERVICE_KEY", "supabase", "service_key"),
    ("SUPABASE_ANON_KEY", "supabase", "anon_key"),
    ("SUPABASE_JWT_SECRET", "supabase", "jwt_secret"),
    # R2 (account_id + bucket are non-secret but needed to build the endpoint)
    ("R2_ACCOUNT_ID", "r2", "account_id"),
    ("R2_ACCESS_KEY_ID", "r2", "access_key_id"),
    ("R2_SECRET_ACCESS_KEY", "r2", "secret_access_key"),
    ("R2_BACKUP_BUCKET", "r2", "backup_bucket"),
    # LLMs
    ("ANTHROPIC_API_KEY", "anthropic", "api_key"),
    ("GEMINI_API_KEY", "gemini", "api_key"),
    ("OPENAI_API_KEY", "openai", "api_key"),
    ("GROQ_API_KEY", "groq", "api_key"),
    # Enrichment / data
    ("DATAFORSEO_LOGIN", "dataforseo", "login"),
    ("DATAFORSEO_PASSWORD", "dataforseo", "password"),
    ("BRIGHTDATA_API_KEY", "brightdata", "api_key"),
    ("CONTACTOUT_API_KEY", "contactout", "api_key"),
    ("HUNTER_API_KEY", "hunter", "api_key"),
    ("LEADMAGIC_API_KEY", "leadmagic", "api_key"),
    ("APIFY_API_TOKEN", "apify", "api_token"),
    ("ABN_LOOKUP_GUID", "abr", "lookup_guid"),
    ("SPIDER_API_KEY", "spider", "api_key"),
    # Outreach / comms
    ("RESEND_API_KEY", "resend", "api_key"),
    ("CLICKSEND_API_KEY", "clicksend", "api_key"),
    ("CLICKSEND_USERNAME", "clicksend", "username"),
    ("TWILIO_ACCOUNT_SID", "twilio", "account_sid"),
    ("TWILIO_AUTH_TOKEN", "twilio", "auth_token"),
    ("TELNYX_API_KEY", "telnyx", "api_key"),
    ("INFRAFORGE_API_KEY", "infraforge", "api_key"),
    ("WARMFORGE_API_KEY", "warmforge", "api_key"),
    ("ELEVENLABS_API_KEY", "elevenlabs", "api_key"),
    # Infra / orchestration
    ("UPSTASH_REDIS_REST_URL", "redis", "rest_url"),
    ("UPSTASH_REDIS_REST_TOKEN", "redis", "rest_token"),
    ("PREFECT_API_URL", "prefect", "api_url"),
    ("PREFECT_API_KEY", "prefect", "api_key"),
    ("RAILWAY_TOKEN", "railway", "token"),
    ("TELEGRAM_TOKEN", "telegram", "token"),
    # Billing
    ("STRIPE_SECRET_KEY", "stripe", "secret_key"),
    ("CLOUDFLARE_API_TOKEN", "cloudflare", "api_token"),
)


@dataclass
class ResolveResult:
    resolved: dict[str, str] = field(default_factory=dict)  # env_var -> value
    missing: list[str] = field(default_factory=list)  # paths absent in vault
    errors: dict[str, str] = field(default_factory=dict)  # env_var -> error


def kv_data_path(service: str, key: str) -> str:
    """KV v2 read path for the convention secret/keiracom/<service>/<key>."""
    return f"/v1/{KV_MOUNT}/data/{KEIRACOM_PREFIX}/{service}/{key}"


def _vault_get(addr: str, token: str, path: str, timeout: float) -> dict | None:
    req = urlrequest.Request(
        f"{addr.rstrip('/')}{path}", method="GET", headers={"X-Vault-Token": token}
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urlerror.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def read_secret(
    addr: str, token: str, service: str, key: str, *, timeout: float = DEFAULT_TIMEOUT
) -> str | None:
    """Read the `value` field at secret/keiracom/<service>/<key>; None if absent."""
    body = _vault_get(addr, token, kv_data_path(service, key), timeout)
    if body is None:
        return None
    return ((body.get("data") or {}).get("data") or {}).get("value")


def resolve(addr: str, token: str, *, manifest=SECRET_MANIFEST) -> ResolveResult:
    """Resolve every manifest secret from Vault. Pure (no env mutation)."""
    out = ResolveResult()
    for env_var, service, key in manifest:
        try:
            val = read_secret(addr, token, service, key)
        except Exception as exc:  # noqa: BLE001 — record per-secret, keep going
            out.errors[env_var] = str(exc)[:200]
            continue
        if val is None:
            out.missing.append(env_var)
        else:
            out.resolved[env_var] = val
    return out


def resolve_into_env(*, manifest=SECRET_MANIFEST) -> ResolveResult:
    """Cold-start entry: read VAULT_ADDR + VAULT_TOKEN from env, resolve all
    manifest secrets, and inject them into os.environ. Returns the result so
    callers can assert completeness. Raises if VAULT_ADDR/VAULT_TOKEN absent."""
    addr = os.environ.get("VAULT_ADDR")
    token = os.environ.get("VAULT_TOKEN")
    if not addr or not token:
        raise RuntimeError("cold-resolve requires VAULT_ADDR + VAULT_TOKEN in env")
    result = resolve(addr, token, manifest=manifest)
    for env_var, val in result.resolved.items():
        os.environ[env_var] = val
    logger.info(
        "cold-resolve: %d resolved, %d missing, %d errors",
        len(result.resolved),
        len(result.missing),
        len(result.errors),
    )
    return result
