#!/usr/bin/env python3
"""vault_envwrap.py — Vault-resolved service launcher (vault_secrets Phase 2).

Systemd ExecStart wrapper: resolves every fleet secret from Vault into os.environ
(via kv_resolver.resolve_into_env), then exec's the wrapped service command so it
inherits the Vault-populated environment. Generalises the proven agent-spawn
cold-start (#1289) to host services.

GRACEFUL-FALLBACK mode (Dave/Elliot ratified for the staggered rollout): the unit
KEEPS `EnvironmentFile=.env` during cutover, so if Vault is unreachable/sealed the
inherited .env values remain and the service still boots. The launcher logs whether
it resolved from Vault or fell back — failure is visible, never silent, never an
outage. Plaintext .env is the rollback net until ALL units are proven; only then
does it become fail-closed + the carve-outs get pruned.

Split-resilient (design #1448 §11): self-locates its repo root from __file__, so the
kv_resolver import works wherever the repo lives after the repo-split.

Usage (systemd):
  ExecStart=%h/.local/bin/vault-envwrap -- /path/python /path/script.py
Modes:
  --verify   resolve + report, do NOT exec (dry-run; exit 0 if VAULT reachable)
  default    resolve (graceful), then exec the command after `--`
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]  # scripts/ -> repo root (split-resilient)
sys.path.insert(0, str(REPO))

logging.basicConfig(level=logging.INFO, format="vault-envwrap: %(message)s", stream=sys.stderr)
logger = logging.getLogger("vault_envwrap")


def _resolve() -> tuple[int, int]:
    """Resolve secrets from Vault into os.environ. Returns (resolved, missing).
    Graceful: any failure logs and returns (0, -1) — caller still exec's with the
    inherited (.env) environment as the rollback net."""
    from src.keiracom_system.vault.kv_resolver import resolve_into_env

    try:
        result = resolve_into_env()
    except Exception as exc:  # noqa: BLE001 — graceful fallback to inherited .env
        logger.warning("Vault resolve FAILED (%s) — falling back to inherited env", exc)
        return 0, -1
    logger.info(
        "resolved %d secrets from Vault (%d missing, %d errors)",
        len(result.resolved),
        len(result.missing),
        len(result.errors),
    )
    return len(result.resolved), len(result.missing)


def main(argv: list[str]) -> int:
    args = argv[1:]
    verify = False
    if args and args[0] == "--verify":
        verify = True
        args = args[1:]
    if args and args[0] == "--":
        args = args[1:]

    resolved, _ = _resolve()

    if verify:
        if resolved > 0:
            logger.info("VERIFY OK — %d secrets resolved from Vault", resolved)
            return 0
        logger.error("VERIFY FAILED — 0 secrets resolved from Vault")
        return 1

    if not args:
        logger.error("no command to exec after `--`")
        return 2

    # Replace the process image so the service inherits the resolved environment.
    os.execvp(args[0], args)
    return 127  # unreachable unless execvp fails


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
