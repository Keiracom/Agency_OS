"""Unit tests for src/retrieval/weaviate_store.

Covers the constraints LlamaIndex relies on:
    * health_check returns a falsy reachable flag when Weaviate is down.
    * get_vector_store rejects unknown collection names rather than
      letting LlamaIndex auto-create a non-canonical schema.
    * close_client swallows already-closed errors.
"""

from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from src.retrieval import weaviate_store


def test_health_check_unreachable_returns_error_field():
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        report = weaviate_store.health_check()
    assert report.reachable is False
    assert report.version == ""
    assert report.collections_present == frozenset()
    assert "connection refused" in (report.error or "")


def test_get_vector_store_rejects_unknown_collection():
    with pytest.raises(ValueError, match="unknown collection"):
        weaviate_store.get_vector_store("NotARealCollection")


def test_get_vector_store_passes_text_key_to_adapter():
    fake_store = object()
    fake_client = MagicMock()
    with patch(
        "llama_index.vector_stores.weaviate.WeaviateVectorStore",
        return_value=fake_store,
    ) as ctor:
        result = weaviate_store.get_vector_store("Discoveries", client=fake_client)
    assert result is fake_store
    ctor.assert_called_once()
    kwargs = ctor.call_args.kwargs
    assert kwargs["index_name"] == "Discoveries"
    assert kwargs["text_key"] == "raw_text"


def test_close_client_swallows_errors():
    bad_client = MagicMock()
    bad_client.close.side_effect = RuntimeError("already closed")
    weaviate_store.close_client(bad_client)


def test_expected_collections_match_schema_module():
    expected = frozenset({"Codebase", "Decisions", "Discoveries", "Sessions", "Keis"})
    assert expected == weaviate_store.EXPECTED_COLLECTIONS
