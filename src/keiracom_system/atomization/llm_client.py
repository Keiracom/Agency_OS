"""LLMClient Protocol + Gemini adapter — atomization pilot Week 1.

Lets the atomizer + verifier take any callable matching the structured-output
contract, so unit tests inject canned responders without a Gemini API key.

The real Gemini adapter routes through the existing LiteLLM proxy
(gov.litellm_router; T0.2 substrate RUNNING per V2 inventory + PR #1156
design + Dave's 2026-05-20 internal-vs-customer-routing policy). Internal
governance never touches Anthropic API; customer-tier (pilot = Dave) routes
through Gemini.

API key resolution:
  - Default: env var GEMINI_API_KEY (pre-Vault interim)
  - Production: secret/keiracom/gemini/api_key via Vault decryptor (PR #1146)
    — wired by atomizer's caller; not this module's concern

LiteLLM endpoint: http://127.0.0.1:4000 (gov.litellm_router default port).
Structured output: Gemini generationConfig.responseSchema passthrough.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

log = logging.getLogger(__name__)

DEFAULT_LITELLM_BASE: str = "http://127.0.0.1:4000"  # NOSONAR S5332 loopback
DEFAULT_TIMEOUT_SECONDS: float = 60.0
DEFAULT_ATOMIZER_MODEL: str = "google/gemini-2.5-flash"
DEFAULT_VERIFIER_MODEL: str = "google/gemini-2.5-pro"

# Atomizer always at temperature=0 per dispatch hard constraint.
ATOMIZER_TEMPERATURE: float = 0.0


class LLMResponse:
    """Structured-output response carrier — parsed JSON + raw token counts."""

    def __init__(
        self,
        *,
        parsed: Any,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        model: str,
    ):
        self.parsed = parsed
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.latency_ms = latency_ms
        self.model = model


class LLMClient(Protocol):
    """Protocol matching the atomizer + verifier's LLM call signature.

    Concrete adapters: LiteLLMGeminiClient (production), fakes (tests).
    """

    def call_structured(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse: ...


class LLMClientError(RuntimeError):
    """Raised on LLM transport or response-parse error."""


HTTPPostFn = Callable[
    [str, dict[str, Any], dict[str, str], float],
    tuple[int, dict[str, Any]],
]


def _default_http_post(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, dict[str, Any]]:
    """Stdlib urllib POST returning (status, json_body).

    Atomizer/verifier failure is a runtime concern of the calling job — we
    do NOT swallow upstream errors here (unlike the cache metric emitter).
    """
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        try:
            err_body = json.loads(exc.read().decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, ValueError):
            err_body = {"error": "non-json error body"}
        return exc.code, err_body


class LiteLLMGeminiClient:
    """Production adapter — routes structured-output calls through the local
    LiteLLM proxy (gov.litellm_router) to Gemini Flash/Pro.

    DI knobs:
      - api_key: caller resolves from env var or Vault
      - http_post: injectable for tests / mock environments
      - base_url: override (e.g. for tests with a fake LiteLLM)
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_LITELLM_BASE,
        http_post: HTTPPostFn | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        if not api_key:
            raise LLMClientError("api_key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http_post = http_post or _default_http_post
        self._timeout = timeout_seconds

    def call_structured(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse:
        import time

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            # Gemini structured output: generationConfig.responseSchema +
            # responseMimeType. LiteLLM passes both through transparently.
            "response_format": {
                "type": "json_schema",
                "json_schema": response_schema,
            },
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        start = time.time()
        status, body = self._http_post(
            f"{self._base_url}/v1/chat/completions",
            payload,
            headers,
            self._timeout,
        )
        latency_ms = int((time.time() - start) * 1000)
        if not (200 <= status < 300):
            raise LLMClientError(f"LiteLLM {model} returned {status}: {str(body)[:300]}")
        # OpenAI-compatible response shape (LiteLLM proxy normalises Gemini).
        try:
            content_str = body["choices"][0]["message"]["content"]
            parsed = json.loads(content_str) if isinstance(content_str, str) else content_str
            usage = body.get("usage") or {}
            return LLMResponse(
                parsed=parsed,
                tokens_in=int(usage.get("prompt_tokens", 0)),
                tokens_out=int(usage.get("completion_tokens", 0)),
                latency_ms=latency_ms,
                model=model,
            )
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMClientError(
                f"LiteLLM {model} response parse failed: {exc} body={str(body)[:300]}"
            ) from exc


def resolve_api_key_from_env(env_var: str = "GEMINI_API_KEY") -> str:
    """Helper for callers — pull the Gemini key from env (interim) before the
    Vault-decryptor pathway lands per PR #1146 integration."""
    key = os.environ.get(env_var, "")
    if not key:
        raise LLMClientError(f"environment variable {env_var} not set — atomizer cannot start")
    return key
