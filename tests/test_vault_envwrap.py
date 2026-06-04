"""Unit tests for scripts/vault_envwrap.py — the Vault-resolved service launcher.

Fast units (mock resolve). The live Vault proof is scripts/proof_bar/vault_envwrap_live.sh.
"""

from __future__ import annotations

import importlib

vw = importlib.import_module("scripts.vault_envwrap")


class _Result:
    def __init__(self, n):
        self.resolved = {f"K{i}": "v" for i in range(n)}
        self.missing = []
        self.errors = {}


def _patch_resolve(monkeypatch, n=None, raises=False):
    import src.keiracom_system.vault.kv_resolver as kv

    def fake():
        if raises:
            raise RuntimeError("vault down")
        return _Result(n)

    monkeypatch.setattr(kv, "resolve_into_env", fake)


def test_verify_ok_when_secrets_resolve(monkeypatch, capsys):
    _patch_resolve(monkeypatch, n=5)
    rc = vw.main(["vault_envwrap.py", "--verify"])
    assert rc == 0


def test_verify_fails_when_zero_resolved(monkeypatch):
    _patch_resolve(monkeypatch, n=0)
    rc = vw.main(["vault_envwrap.py", "--verify"])
    assert rc == 1


def test_graceful_fallback_on_vault_failure(monkeypatch):
    """Vault unreachable → resolve returns (0,-1), --verify reports failure but
    does NOT raise (graceful — exec path would fall back to inherited .env)."""
    _patch_resolve(monkeypatch, raises=True)
    rc = vw.main(["vault_envwrap.py", "--verify"])
    assert rc == 1  # verify flags it, but no exception bubbled


def test_no_command_after_separator_returns_2(monkeypatch):
    _patch_resolve(monkeypatch, n=3)
    assert vw.main(["vault_envwrap.py", "--"]) == 2


def test_exec_replaces_process(monkeypatch):
    """Default mode resolves then execvp's the command after `--`."""
    _patch_resolve(monkeypatch, n=3)
    called = {}
    monkeypatch.setattr(vw.os, "execvp", lambda f, a: called.update(file=f, argv=a))
    vw.main(["vault_envwrap.py", "--", "/bin/echo", "hi"])
    assert called["file"] == "/bin/echo"
    assert called["argv"] == ["/bin/echo", "hi"]
