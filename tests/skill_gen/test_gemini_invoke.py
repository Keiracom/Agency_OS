"""Tests for src/skill_gen/gemini_invoke.py — Gemini 2.5 Flash Lite wrapper."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.skill_gen.gemini_invoke import (
    DEFAULT_MODEL,
    GEMINI_API_KEY_ENV,
    GeminiNotConfigured,
    GeminiResult,
    invoke,
)


def _stub_client(text="ok", prompt_tokens=42, output_tokens=7):
    """Build a fake google.genai.Client substitute. Captures every call so
    tests can assert what was sent to the SDK."""
    calls: list[dict] = []

    class _Models:
        def generate_content(self, *, model, contents):
            calls.append({"model": model, "contents": contents})
            usage = SimpleNamespace(
                prompt_token_count=prompt_tokens,
                candidates_token_count=output_tokens,
            )
            return SimpleNamespace(text=text, usage_metadata=usage)

    class _Client:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = _Models()

    def factory(api_key):
        return _Client(api_key)

    return factory, calls


def test_invoke_returns_gemini_result_with_text_and_usage():
    factory, calls = _stub_client(text="hello")
    result = invoke("the prompt", api_key="fake-key", client_factory=factory)
    assert isinstance(result, GeminiResult)
    assert result.text == "hello"
    assert result.model == DEFAULT_MODEL
    assert result.prompt_tokens == 42
    assert result.output_tokens == 7
    assert calls[0]["model"] == DEFAULT_MODEL
    assert calls[0]["contents"] == "the prompt"


def test_invoke_passes_explicit_model_override():
    factory, calls = _stub_client()
    invoke(
        "x",
        model="gemini-2.0-flash-lite",
        api_key="fake-key",
        client_factory=factory,
    )
    assert calls[0]["model"] == "gemini-2.0-flash-lite"


def test_invoke_reads_api_key_from_env(monkeypatch):
    factory, _ = _stub_client()
    monkeypatch.setenv(GEMINI_API_KEY_ENV, "from-env-key-XYZ")
    captured_keys: list[str] = []

    def capture_factory(api_key):
        captured_keys.append(api_key)
        return factory(api_key)

    invoke("x", client_factory=capture_factory)
    assert captured_keys[0] == "from-env-key-XYZ"


def test_invoke_raises_when_api_key_absent(monkeypatch):
    monkeypatch.delenv(GEMINI_API_KEY_ENV, raising=False)
    with pytest.raises(GeminiNotConfigured):
        invoke("x", client_factory=lambda _key: None)


def test_invoke_handles_missing_usage_metadata():
    """Some Gemini responses (older API versions / streamed paths) lack
    usage_metadata. We default token counts to None instead of crashing."""
    factory, _ = _stub_client()

    class _MinimalClient:
        def __init__(self, _api_key):
            self.models = self  # self.models.generate_content works

        def generate_content(self, *, model, contents):
            return SimpleNamespace(text="bare response")  # no usage_metadata attr

    result = invoke("x", api_key="k", client_factory=lambda key: _MinimalClient(key))
    assert result.text == "bare response"
    assert result.prompt_tokens is None
    assert result.output_tokens is None


def test_invoke_returns_empty_text_when_response_text_none():
    """Gemini may return response.text == None in some edge cases — never crash."""

    class _NoneClient:
        def __init__(self, _api_key):
            self.models = self

        def generate_content(self, *, model, contents):
            return SimpleNamespace(text=None, usage_metadata=None)

    result = invoke("x", api_key="k", client_factory=lambda k: _NoneClient(k))
    assert result.text == ""
