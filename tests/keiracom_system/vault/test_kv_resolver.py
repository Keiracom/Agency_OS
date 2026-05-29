"""Tests for the cold-start Vault KV resolver (P10 / Agency_OS-xlpe)."""

from __future__ import annotations

import pytest

from src.keiracom_system.vault import kv_resolver as kv


def test_kv_data_path_convention():
    # secret/keiracom/<service>/<key> → KV v2 read path
    assert kv.kv_data_path("anthropic", "api_key") == "/v1/secret/data/keiracom/anthropic/api_key"
    assert (
        kv.kv_data_path("supabase", "database_url")
        == "/v1/secret/data/keiracom/supabase/database_url"
    )


def test_manifest_paths_unique():
    paths = [kv.kv_data_path(s, k) for _, s, k in kv.SECRET_MANIFEST]
    assert len(paths) == len(set(paths)), "duplicate vault path in SECRET_MANIFEST"


def _fake_vault(values: dict[str, str]):
    """Return a _vault_get stand-in mapping path → KV v2 body (or None=404)."""

    def _get(addr, token, path, timeout):
        if path in values:
            return {"data": {"data": {"value": values[path]}}}
        return None

    return _get


def test_resolve_collects_resolved_and_missing(monkeypatch):
    manifest = (
        ("ANTHROPIC_API_KEY", "anthropic", "api_key"),
        ("OPENAI_API_KEY", "openai", "api_key"),
    )
    values = {kv.kv_data_path("anthropic", "api_key"): "sk-ant-xxx"}  # openai absent → missing
    monkeypatch.setattr(kv, "_vault_get", _fake_vault(values))
    res = kv.resolve("http://v", "tok", manifest=manifest)
    assert res.resolved == {"ANTHROPIC_API_KEY": "sk-ant-xxx"}
    assert res.missing == ["OPENAI_API_KEY"]
    assert res.errors == {}


def test_resolve_records_errors(monkeypatch):
    def _boom(addr, token, path, timeout):
        raise RuntimeError("vault down")

    monkeypatch.setattr(kv, "_vault_get", _boom)
    res = kv.resolve("http://v", "tok", manifest=(("X", "svc", "k"),))
    assert "X" in res.errors and res.resolved == {}


def test_resolve_into_env_injects(monkeypatch):
    manifest = (("MY_SECRET", "svc", "k"),)
    values = {kv.kv_data_path("svc", "k"): "the-value"}
    monkeypatch.setattr(kv, "_vault_get", _fake_vault(values))
    monkeypatch.setenv("VAULT_ADDR", "http://127.0.0.1:8200")
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    monkeypatch.delenv("MY_SECRET", raising=False)
    res = kv.resolve_into_env(manifest=manifest)
    import os

    assert os.environ["MY_SECRET"] == "the-value"
    assert res.resolved["MY_SECRET"] == "the-value"


def test_resolve_into_env_requires_vault_addr_token(monkeypatch):
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    monkeypatch.delenv("VAULT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="VAULT_ADDR"):
        kv.resolve_into_env(manifest=(("X", "s", "k"),))


def test_read_secret_extracts_value(monkeypatch):
    monkeypatch.setattr(
        kv, "_vault_get", _fake_vault({kv.kv_data_path("r2", "account_id"): "abc123"})
    )
    assert kv.read_secret("http://v", "tok", "r2", "account_id") == "abc123"
    assert kv.read_secret("http://v", "tok", "r2", "missing") is None
