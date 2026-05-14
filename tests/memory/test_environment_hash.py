"""
FILE: tests/memory/test_environment_hash.py
PURPOSE: Unit tests for src/memory/environment_hash.py

Covers:
- Returns all required keys
- Hash is deterministic for same input
- Hash changes when any field changes
- Defensive degradation when a package is uninstalled

KEI: KEI-60 (Linear: https://linear.app/keiracom/issue/KEI-62)
"""
from __future__ import annotations

import hashlib
import json
from unittest.mock import patch


def _import_module():
    """Import fresh to allow monkeypatching helpers."""
    import importlib

    import src.memory.environment_hash as m

    importlib.reload(m)
    return m


class TestRequiredKeys:
    """get_environment_hash() returns all required top-level keys."""

    def test_all_required_keys_present(self):
        from src.memory.environment_hash import get_environment_hash

        result = get_environment_hash()
        required = {"infrastructure", "container_runtime", "os", "embedding_model", "key_software", "hash"}
        assert required.issubset(result.keys()), f"Missing keys: {required - result.keys()}"

    def test_key_software_has_cognee_and_weaviate(self):
        from src.memory.environment_hash import get_environment_hash

        result = get_environment_hash()
        ks = result["key_software"]
        assert "cognee" in ks
        assert "weaviate" in ks

    def test_all_values_are_strings_except_key_software(self):
        from src.memory.environment_hash import get_environment_hash

        result = get_environment_hash()
        for key in ("infrastructure", "container_runtime", "os", "embedding_model", "hash"):
            assert isinstance(result[key], str), f"Field '{key}' is not a string"
        assert isinstance(result["key_software"], dict)

    def test_hash_is_hex_string(self):
        from src.memory.environment_hash import get_environment_hash

        result = get_environment_hash()
        h = result["hash"]
        assert len(h) == 64, f"SHA-256 hex should be 64 chars, got {len(h)}"
        int(h, 16)  # raises ValueError if not valid hex


class TestDeterminism:
    """Hash is deterministic for same inputs, different for changed inputs."""

    def _make_hash(self, payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def test_same_inputs_produce_same_hash(self):
        from src.memory.environment_hash import get_environment_hash

        r1 = get_environment_hash()
        r2 = get_environment_hash()
        assert r1["hash"] == r2["hash"]

    def test_hash_changes_when_infrastructure_changes(self):
        with patch("src.memory.environment_hash._get_hostname", return_value="host-A"):
            from src.memory import environment_hash as m

            r1 = m.get_environment_hash()

        with patch("src.memory.environment_hash._get_hostname", return_value="host-B"):
            r2 = m.get_environment_hash()

        assert r1["hash"] != r2["hash"]

    def test_hash_changes_when_embedding_model_changes(self, monkeypatch):

        monkeypatch.setenv("AGENCY_OS_EMBEDDING_MODEL", "gemini-embedding-001")
        from src.memory import environment_hash as m

        r1 = m.get_environment_hash()

        monkeypatch.setenv("AGENCY_OS_EMBEDDING_MODEL", "text-embedding-3-small")
        r2 = m.get_environment_hash()

        assert r1["hash"] != r2["hash"]

    def test_hash_changes_when_os_changes(self):
        with patch("src.memory.environment_hash._get_os_info", return_value="Linux/5.0"):
            from src.memory import environment_hash as m

            r1 = m.get_environment_hash()

        with patch("src.memory.environment_hash._get_os_info", return_value="Linux/6.0"):
            r2 = m.get_environment_hash()

        assert r1["hash"] != r2["hash"]

    def test_hash_field_not_included_in_its_own_computation(self):
        """Verify that 'hash' is excluded from the canonical JSON used to compute itself."""
        from src.memory.environment_hash import get_environment_hash

        result = get_environment_hash()
        # Reconstruct canonical payload without 'hash'
        payload = {k: v for k, v in result.items() if k != "hash"}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(canonical.encode()).hexdigest()
        assert result["hash"] == expected_hash


class TestDefensiveDegradation:
    """Failures in sub-calls produce 'unknown' rather than raising."""

    def test_hostname_failure_returns_unknown(self):
        # Patch socket.gethostname to raise inside the real _get_hostname helper
        from src.memory import environment_hash as m

        with patch("src.memory.environment_hash.socket.gethostname", side_effect=OSError("fail")):
            result = m._get_hostname()
        assert result == "unknown"

    def test_missing_package_returns_unknown(self):
        from src.memory import environment_hash as m

        result = m._get_package_version("definitely-not-installed-package-xyzzy")
        assert result == "unknown"

    def test_get_environment_hash_survives_all_helpers_failing(self):
        """Even if every sub-helper returns 'unknown', the function returns a valid dict."""
        with (
            patch("src.memory.environment_hash._get_hostname", return_value="unknown"),
            patch("src.memory.environment_hash._get_container_runtime", return_value="unknown"),
            patch("src.memory.environment_hash._get_os_info", return_value="unknown"),
            patch("src.memory.environment_hash._get_embedding_model", return_value="unknown"),
            patch(
                "src.memory.environment_hash._get_package_version",
                return_value="unknown",
            ),
        ):
            from src.memory import environment_hash as m

            result = m.get_environment_hash()

        required = {"infrastructure", "container_runtime", "os", "embedding_model", "key_software", "hash"}
        assert required.issubset(result.keys())
        assert len(result["hash"]) == 64

    def test_embedding_model_defaults_to_unknown_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("AGENCY_OS_EMBEDDING_MODEL", raising=False)
        from src.memory import environment_hash as m

        result = m._get_embedding_model()
        assert result == "unknown"
