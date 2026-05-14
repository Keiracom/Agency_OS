"""
FILE: src/memory/environment_hash.py
PURPOSE: Produce the environment_hash JSON dict + sha256 string for Weaviate writes.
         Called by capture pipelines (KEI-48) when writing to Weaviate so every object
         is stamped with a reproducible execution-context fingerprint.

KEI: KEI-60 (Linear: https://linear.app/keiracom/issue/KEI-62)
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import subprocess


def _get_hostname() -> str:
    """Return hostname for infrastructure field."""
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def _get_container_runtime() -> str:
    """Return Docker version string or 'host' if not running in Docker."""
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return f"docker/{result.stdout.strip()}"
    except Exception:
        pass

    # Check /.dockerenv — present when running inside a container
    try:
        if os.path.exists("/.dockerenv"):
            return "docker/unknown-version"
    except Exception:
        pass

    return "host"


def _get_os_info() -> str:
    """Return OS distro + version string."""
    try:
        return f"{platform.system()}/{platform.release()}"
    except Exception:
        return "unknown"


def _get_embedding_model() -> str:
    """Return the pinned embedding model from env or 'unknown'."""
    return os.environ.get("AGENCY_OS_EMBEDDING_MODEL", "unknown")


def _get_package_version(package_name: str) -> str:
    """Return installed version of a Python package or 'unknown'."""
    try:
        from importlib.metadata import version

        return version(package_name)
    except Exception:
        return "unknown"


def get_environment_hash() -> dict:
    """
    Build and return the environment_hash dict.

    Structure::

        {
            "infrastructure": "<hostname>",
            "container_runtime": "<docker/version | host>",
            "os": "<System/release>",
            "embedding_model": "<pinned-version from AGENCY_OS_EMBEDDING_MODEL env>",
            "key_software": {
                "cognee": "<importlib.metadata version or 'unknown'>",
                "weaviate": "<importlib.metadata version or 'unknown'>"
            },
            "hash": "<sha256 hex of canonical JSON of the above fields>"
        }

    Defensive: any sub-call that fails populates that field with "unknown".
    The sha256 is computed over the canonical JSON of all fields EXCEPT "hash".
    """
    infrastructure = _get_hostname()
    container_runtime = _get_container_runtime()
    os_info = _get_os_info()
    embedding_model = _get_embedding_model()
    key_software = {
        "cognee": _get_package_version("cognee"),
        "weaviate": _get_package_version("weaviate-client"),
    }

    # Build the canonical payload — no "hash" field yet
    payload: dict = {
        "infrastructure": infrastructure,
        "container_runtime": container_runtime,
        "os": os_info,
        "embedding_model": embedding_model,
        "key_software": key_software,
    }

    # Deterministic JSON: sort_keys ensures same output for same input
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    return {**payload, "hash": digest}
