"""Metric emitter unit tests — Phase A7 sub-task 4."""

from src.keiracom_system.cache.metrics import (
    emit_anthropic_cache_tokens,
    make_better_stack_emitter,
)


def test_emitter_posts_to_ingest_url_with_auth_header():
    captured: list[tuple[str, dict, dict, float]] = []

    def fake_post(url: str, payload: dict, headers: dict, timeout: float) -> int:
        captured.append((url, payload, headers, timeout))
        return 202

    emit = make_better_stack_emitter(
        ingest_url="https://test.example/metrics",
        source_token="test-token",
        http_post=fake_post,
    )
    emit("keiracom.cache.valkey.lookup", {"tenant_id": "t1", "outcome": "hit"})
    assert len(captured) == 1
    url, payload, headers, timeout = captured[0]
    assert url == "https://test.example/metrics"
    assert headers["Authorization"] == "Bearer test-token"
    assert payload["metric"] == "keiracom.cache.valkey.lookup"
    assert payload["tags"]["outcome"] == "hit"


def test_emit_anthropic_three_types():
    captured: list[tuple[str, dict[str, str]]] = []

    def emit(name: str, tags: dict[str, str]) -> None:
        captured.append((name, tags))

    emit_anthropic_cache_tokens(
        emit,
        tenant_id="t1",
        model="claude-3-5-sonnet",
        cache_creation_input_tokens=100,
        cache_read_input_tokens=200,
        standard_input_tokens=300,
    )
    assert len(captured) == 3
    types = {tags["type"] for _, tags in captured}
    assert types == {"create", "read", "standard"}


def test_emit_anthropic_skips_zero_token_buckets():
    captured: list[tuple[str, dict[str, str]]] = []

    def emit(name: str, tags: dict[str, str]) -> None:
        captured.append((name, tags))

    emit_anthropic_cache_tokens(
        emit,
        tenant_id="t1",
        model="claude-3-5-haiku",
        cache_creation_input_tokens=0,
        cache_read_input_tokens=500,
        standard_input_tokens=0,
    )
    assert len(captured) == 1
    assert captured[0][1]["type"] == "read"


def test_emit_anthropic_none_emitter_noop():
    """Passing emitter=None must not raise — test/pre-Better-Stack envs."""
    emit_anthropic_cache_tokens(
        None,
        tenant_id="t1",
        model="m",
        cache_creation_input_tokens=10,
        cache_read_input_tokens=20,
        standard_input_tokens=30,
    )
    # No assertion needed — should just not raise.


def test_emitter_includes_metric_value_one():
    captured: list[tuple[str, dict, dict, float]] = []

    def fake_post(url: str, payload: dict, headers: dict, timeout: float) -> int:
        captured.append((url, payload, headers, timeout))
        return 202

    emit = make_better_stack_emitter(
        source_token="t",
        http_post=fake_post,
    )
    emit("metric.name", {"tag": "value"})
    assert captured[0][1]["value"] == 1
