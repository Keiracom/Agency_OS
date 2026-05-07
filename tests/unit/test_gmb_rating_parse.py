"""Tests for BrightDataGMBClient._parse_rating staticmethod."""


from src.integrations.bright_data_gmb_client import BrightDataGMBClient

parse = BrightDataGMBClient._parse_rating


def test_none_returns_none():
    assert parse(None) is None


def test_plain_float():
    assert parse(4.5) == 4.5


def test_string_with_review_count():
    assert parse("4.5 (123 reviews)") == 4.5


def test_dict_with_value_key():
    assert parse({"value": 4.5, "count": 123}) == 4.5


def test_dict_missing_value_key():
    assert parse({"count": 123}) is None


def test_empty_string_returns_none():
    assert parse("") is None


def test_int_input():
    assert parse(4) == 4.0


def test_rounding():
    assert parse(4.567) == 4.6


def test_bad_input_never_raises():
    assert parse(object()) is None
