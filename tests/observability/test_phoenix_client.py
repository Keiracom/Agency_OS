"""GOV-PHASE2 Auditor — phoenix_client export tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.observability import phoenix_client


def _mk_tracer() -> MagicMock:
    """Build a tracer mock whose start_as_current_span returns a context-manager span."""
    span = MagicMock()
    span.set_attribute = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=span)
    cm.__exit__ = MagicMock(return_value=False)
    tracer = MagicMock()
    tracer.start_as_current_span.return_value = cm
    return tracer, span


def test_export_event_happy_path():
    tracer, span = _mk_tracer()
    event = {
        "event_type": "tool_call",
        "callsign": "aiden",
        "tool_name": "Bash",
        "file_path": "src/foo.py",
        "directive_id": "TEST-1",
        "event_data": {"hook": "recorder", "extra": 42},
        "timestamp": "2026-05-01T13:00:00Z",
    }
    ok = phoenix_client.export_event(tracer, event)
    assert ok is True
    tracer.start_as_current_span.assert_called_once_with("tool_call")
    attr_calls = {c.args[0]: c.args[1] for c in span.set_attribute.call_args_list}
    assert attr_calls["callsign"] == "aiden"
    assert attr_calls["tool_name"] == "Bash"
    assert attr_calls["directive_id"] == "TEST-1"
    assert attr_calls["event_data.hook"] == "recorder"
    assert attr_calls["event_data.extra"] == "42"
    assert attr_calls["source_timestamp"] == "2026-05-01T13:00:00Z"


def test_export_event_returns_false_when_tracer_none():
    assert phoenix_client.export_event(None, {"event_type": "x"}) is False


def test_export_event_handles_missing_fields():
    tracer, span = _mk_tracer()
    ok = phoenix_client.export_event(tracer, {"event_type": "minimal"})
    assert ok is True
    attr_calls = {c.args[0]: c.args[1] for c in span.set_attribute.call_args_list}
    assert attr_calls["callsign"] == ""
    assert attr_calls["tool_name"] == ""
    assert "source_timestamp" not in attr_calls


def test_export_event_swallows_span_exception():
    tracer = MagicMock()
    tracer.start_as_current_span.side_effect = RuntimeError("OTLP down")
    ok = phoenix_client.export_event(tracer, {"event_type": "x"})
    assert ok is False


def test_init_tracer_returns_none_when_phoenix_missing():
    with patch("src.observability.phoenix_client.logger"):
        with patch.dict("sys.modules", {"phoenix.otel": None}):
            tracer = phoenix_client.init_tracer()
            assert tracer is None
