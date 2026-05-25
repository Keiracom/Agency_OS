"""vault_decryptor.py — HashiCorp Vault Transit envelope decryptor.

Phase A2 build per bd Agency_OS-31bk (HashiCorp Vault self-hosted on Vultr
for BYOK envelope encryption).

CANONICAL KEY ANCHOR — ceo:keiracom_architecture_v2_locked Cat 16
infra.secrets_management (verbatim from
/home/elliotbot/clawd/Agency_OS/docs/architecture/keiracom_architecture_v2_inventory.md
line 208):

  "Secrets management — HashiCorp Vault self-hosted on Vultr (single node V1)
   with Transit engine for BYOK envelope encryption. Three categories:
   customer BYOK keys (envelope-encrypted in Postgres, KMS-managed), internal
   service credentials (Vault store), Composio OAuth tokens (managed by
   Composio's credential store)."

REPLACES the `_passthrough_decryptor` callable in
src/keiracom_system/tenant/keiracom_tenant_extension.py (the prior plan was
pgcrypto.pgp_sym_decrypt; Phase A2 supersedes that with Vault Transit per
Aiden + Viktor Cat 16 ratify 2026-05-25).

PER-TENANT KEYING: Vault Transit keys are named `<prefix><tenant_id>` so a
ciphertext can only be decrypted by the Vault key that encrypted it. Cross-
tenant decrypt attempts return HTTP 400 from Vault with "cipher: message
authentication failed" — exactly the fail-closed shape the il34 spike
criterion #3 verified for the placeholder envelope.

USAGE:
    from keiracom_system.vault import VaultDecryptor

    decryptor = VaultDecryptor(
        addr="https://vault.keiracom.internal:8200",
        token=os.environ["VAULT_TOKEN"],
    )
    # Wire into KeiracomTenantExtension as the decryptor callable:
    ext = KeiracomTenantExtension(db=db, decryptor=decryptor)

TESTABILITY: `http_post` is injectable so unit tests don't need a live Vault
or `requests`/`httpx` in the test path. Smoke tests against a real Vault use
the default urllib transport.

DEGRADED-MODE FALLBACK (documented but NOT implemented in V1 per Phase A2
dispatch): when Vault is unreachable for >N seconds, the KeiracomTenantExtension
should optionally fall back to reading from an envelope-encrypted Postgres
cache populated at successful Vault decrypts. Build-track follow-up bd to be
filed post-V1-launch; V1 ships with Vault as hard-dependency.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_KEY_NAME_PREFIX = "keiracom-tenant-"
DEFAULT_TIMEOUT_SECONDS = 10.0

HTTPPostFn = Callable[[str, dict[str, Any], dict[str, str], float], "_HTTPResponse"]


class VaultDecryptError(RuntimeError):
    """Raised on any Vault-side or transport error during decrypt."""


class _HTTPResponse:
    """Minimal response shape — status_code + json — that both urllib and
    a real httpx.Response can adapt to.
    """

    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return json.loads(self._body.decode("utf-8") or "null")

    @property
    def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")


def _default_http_post(
    url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float
) -> _HTTPResponse:
    """Stdlib urllib POST — keeps the module dependency-free."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        method="POST",
        data=body,
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — trusted Vault URL
            return _HTTPResponse(status_code=resp.status, body=resp.read())
    except urllib.error.HTTPError as exc:
        # Vault returns useful error bodies on 4xx — capture rather than re-raise
        return _HTTPResponse(status_code=exc.code, body=exc.read())


class VaultDecryptor:
    """Callable that decrypts a Vault Transit ciphertext for a specific tenant.

    Conforms to the `Callable[[str, str], str]` shape expected by
    KeiracomTenantExtension's `decryptor` constructor arg
    (signature: `(ciphertext, tenant_id) -> plaintext`).
    """

    def __init__(
        self,
        addr: str,
        token: str,
        key_name_prefix: str = DEFAULT_KEY_NAME_PREFIX,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        http_post: HTTPPostFn | None = None,
    ):
        self.addr = addr.rstrip("/")
        self._token = token
        self.key_name_prefix = key_name_prefix
        self.timeout = timeout_seconds
        self._http_post = http_post or _default_http_post

    def _key_name(self, tenant_id: str) -> str:
        return f"{self.key_name_prefix}{tenant_id}"

    def __call__(self, ciphertext: str, tenant_id: str) -> str:
        """Decrypt a Vault Transit ciphertext for the given tenant_id.

        Raises VaultDecryptError on:
          - Transport error (Vault unreachable)
          - Non-2xx response from Vault (auth failure, key-not-found, ciphertext-tampered)
          - Missing `data.plaintext` in response (Vault contract violation)
          - Base64 decode failure on returned plaintext
        """
        if not ciphertext:
            raise VaultDecryptError("ciphertext is empty")
        if not tenant_id:
            raise VaultDecryptError("tenant_id is empty")

        url = f"{self.addr}/v1/transit/decrypt/{self._key_name(tenant_id)}"
        headers = {"X-Vault-Token": self._token}
        payload = {"ciphertext": ciphertext}
        try:
            resp = self._http_post(url, payload, headers, self.timeout)
        except Exception as exc:
            raise VaultDecryptError(f"vault transport error: {exc}") from exc

        if resp.status_code != 200:
            body_preview = resp.text[:200]
            raise VaultDecryptError(
                f"vault decrypt HTTP {resp.status_code} for tenant {tenant_id!r}: {body_preview}"
            )

        try:
            data = resp.json()
        except Exception as exc:
            raise VaultDecryptError(f"vault response not JSON: {exc}") from exc

        b64_plaintext = (data or {}).get("data", {}).get("plaintext")
        if not b64_plaintext:
            raise VaultDecryptError(
                f"vault response missing data.plaintext for tenant {tenant_id!r}: {data!r}"
            )

        try:
            plaintext_bytes = base64.b64decode(b64_plaintext)
        except Exception as exc:
            raise VaultDecryptError(f"vault plaintext not valid base64: {exc}") from exc

        return plaintext_bytes.decode("utf-8")


def from_env() -> VaultDecryptor:
    """Construct a VaultDecryptor from VAULT_ADDR + VAULT_TOKEN env vars.

    Optional env: KEIRACOM_VAULT_KEY_PREFIX (default 'keiracom-tenant-').
    Raises EnvironmentError if required env vars are absent.
    """
    addr = os.environ.get("VAULT_ADDR")
    token = os.environ.get("VAULT_TOKEN")
    if not addr or not token:
        raise OSError(
            "VaultDecryptor.from_env(): VAULT_ADDR and VAULT_TOKEN must both be set "
            f"(got VAULT_ADDR={'set' if addr else 'unset'}, "
            f"VAULT_TOKEN={'set' if token else 'unset'})"
        )
    prefix = os.environ.get("KEIRACOM_VAULT_KEY_PREFIX", DEFAULT_KEY_NAME_PREFIX)
    return VaultDecryptor(addr=addr, token=token, key_name_prefix=prefix)
