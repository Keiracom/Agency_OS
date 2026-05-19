"""Regression: kei196_reingest_with_vectorizer.py vectorizer config + key header.

Locks in the three corrections from KEI-201 follow-up (Scout's empirical fix
in PR #1025 commit ef408fe05):

1. moduleConfig has apiEndpoint=generativelanguage.googleapis.com (without
   this, Weaviate's text2vec-google module assumes Vertex and demands
   projectId).
2. modelId=gemini-embedding-001 (NOT text-embedding-004 — that's the Vertex
   name and 404s on AI Studio v1beta).
3. _attach_studio_key attaches X-Goog-Studio-Api-Key header from the
   script-process GOOGLE_API_KEY env (Weaviate process does not carry it).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))


def _load_module(monkeypatch, *, google_api_key: str = "fake-test-key"):
    """Reload the module with a controlled GOOGLE_API_KEY env."""
    monkeypatch.setenv("GOOGLE_API_KEY", google_api_key)
    sys.modules.pop("kei196_reingest_with_vectorizer", None)
    return importlib.import_module("kei196_reingest_with_vectorizer")


def test_module_config_has_ai_studio_api_endpoint(monkeypatch):
    mod = _load_module(monkeypatch)
    cfg = mod.NEW_MODULE_CONFIG["text2vec-google"]
    assert cfg["apiEndpoint"] == "generativelanguage.googleapis.com", (
        "Missing apiEndpoint pins Weaviate to Vertex AI mode (demands projectId). "
        "AI Studio mode requires apiEndpoint=generativelanguage.googleapis.com — "
        "see KEI-201 PR #1025."
    )


def test_module_config_uses_ai_studio_model_id(monkeypatch):
    mod = _load_module(monkeypatch)
    cfg = mod.NEW_MODULE_CONFIG["text2vec-google"]
    assert cfg["modelId"] == "gemini-embedding-001", (
        f"modelId must be gemini-embedding-001 (AI Studio v1beta name). "
        f"text-embedding-004 is the Vertex name and 404s on AI Studio. "
        f"Got: {cfg['modelId']!r}"
    )


def test_module_config_disables_class_name_vectorization(monkeypatch):
    mod = _load_module(monkeypatch)
    cfg = mod.NEW_MODULE_CONFIG["text2vec-google"]
    assert cfg["vectorizeClassName"] is False


def test_attach_studio_key_sets_header_when_env_present(monkeypatch):
    mod = _load_module(monkeypatch, google_api_key="real-test-key")
    req = urlrequest.Request("http://localhost/v1/objects", method="POST")
    mod._attach_studio_key(req)
    assert req.get_header("X-goog-studio-api-key") == "real-test-key"


def test_attach_studio_key_skips_header_when_env_blank(monkeypatch):
    mod = _load_module(monkeypatch, google_api_key="")
    req = urlrequest.Request("http://localhost/v1/objects", method="POST")
    mod._attach_studio_key(req)
    assert req.get_header("X-goog-studio-api-key") is None, (
        "When GOOGLE_API_KEY is unset the script must not attach an empty "
        "header (would 401 the Weaviate request with a confusing blank-key)."
    )


def test_target_collections_includes_agent_memories(monkeypatch):
    """KEI-70st sibling: AgentMemories needs vectorizer reingest after the
    indexer-base prepare_threshold fix refills the collection."""
    mod = _load_module(monkeypatch)
    assert "AgentMemories" in mod.TARGET_COLLECTIONS
    assert len(mod.TARGET_COLLECTIONS) >= 5
