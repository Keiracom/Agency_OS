#!/usr/bin/env python3
"""provision_vault_secrets.py — load fleet secrets from .env into Vault KV v2 (P10).

One-time/idempotent provisioner: for every SECRET_MANIFEST entry whose env var is
present in the current environment (sourced from .env), write it to
secret/keiracom/<service>/<key> as {"value": <secret>}. Vault is the canonical
store; .env becomes legacy-only after this.

Usage (source .env first so the values are in env):
  set -a; source ~/.config/agency-os/.env; set +a
  VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=... \
    python3 scripts/provision_vault_secrets.py [--dry-run]

Secret VALUES are never printed — only env-var names + per-path written/skipped.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib import request as urlrequest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.keiracom_system.vault.kv_resolver import SECRET_MANIFEST, kv_data_path  # noqa: E402


def _vault_put(
    addr: str, token: str, service: str, key: str, value: str, timeout: float = 10.0
) -> int:
    body = json.dumps({"data": {"value": value}}).encode()
    req = urlrequest.Request(
        f"{addr.rstrip('/')}{kv_data_path(service, key)}",
        data=body,
        method="POST",
        headers={"X-Vault-Token": token, "Content-Type": "application/json"},
    )
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        return resp.status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    addr = os.environ.get("VAULT_ADDR")
    token = os.environ.get("VAULT_TOKEN")
    if not addr or not token:
        print("ERROR: VAULT_ADDR + VAULT_TOKEN must be set", file=sys.stderr)
        return 2

    written, skipped_absent, failed = [], [], []
    for env_var, service, key in SECRET_MANIFEST:
        val = os.environ.get(env_var)
        if not val:
            skipped_absent.append(env_var)
            continue
        path = f"secret/keiracom/{service}/{key}"
        if args.dry_run:
            print(f"  [dry-run] would write {env_var} -> {path} ({len(val)} chars)")
            written.append(env_var)
            continue
        try:
            status = _vault_put(addr, token, service, key, val)
            if 200 <= status < 300:
                written.append(env_var)
                print(f"  wrote {env_var} -> {path}")
            else:
                failed.append((env_var, f"HTTP {status}"))
        except Exception as exc:  # noqa: BLE001
            failed.append((env_var, str(exc)[:120]))
            print(f"  FAILED {env_var} -> {path}: {str(exc)[:120]}", file=sys.stderr)

    print(
        f"\nprovision summary: wrote={len(written)} "
        f"absent_in_env={len(skipped_absent)} failed={len(failed)} "
        f"(manifest size={len(SECRET_MANIFEST)})"
    )
    if skipped_absent:
        print("absent in .env (not provisioned):", ", ".join(skipped_absent))
    if failed:
        print("FAILURES:", failed, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
