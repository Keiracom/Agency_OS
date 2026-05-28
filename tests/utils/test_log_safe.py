"""Tests for src/utils/log_safe.scrub — the CRLF/log-injection barrier."""

from __future__ import annotations

from src.utils.log_safe import LOG_VALUE_CAP, scrub


def test_escapes_newline_and_carriage_return():
    out = scrub("line1\nline2\r\nINJECTED 200 OK")
    assert "\n" not in out
    assert "\r" not in out
    assert "\\n" in out
    assert "\\r" in out


def test_coerces_non_str():
    assert scrub(12345) == "12345"
    assert scrub(None) == "None"


def test_truncates_to_limit():
    assert len(scrub("x" * 500)) == LOG_VALUE_CAP
    assert len(scrub("x" * 500, limit=10)) == 10


def test_clean_value_unchanged():
    assert scrub("atlas") == "atlas"


def test_crlf_attack_collapses_to_single_line():
    # A forged second log line must not survive as an actual newline.
    payload = "ok\nERROR fake-breach detected"
    assert "\n" not in scrub(payload)
