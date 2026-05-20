"""Unit tests for infra/weaviate/schema.py (KEI-48)."""

from __future__ import annotations

from unittest import mock

import pytest

from infra.weaviate import schema


def test_collections_match_dave_spec() -> None:
    """The 5 collection names must match Dave's KEI-48 spec verbatim."""
    assert schema.COLLECTIONS == (
        "codebase",
        "decisions",
        "discoveries",
        "sessions",
        "keis",
    )


def test_mandatory_properties_present() -> None:
    """Every collection must have the 6 properties from
    docs/schema/weaviate-schema-requirements.md (raw_text/environment_hash/
    created_at/agent/kei + KEI-75 source_id).
    """
    names = {p["name"] for p in schema.MANDATORY_PROPERTIES}
    assert names == {"raw_text", "environment_hash", "created_at", "agent", "kei", "source_id"}

    by_name = {p["name"]: p["dataType"] for p in schema.MANDATORY_PROPERTIES}
    assert by_name["raw_text"] == ["text"]
    assert by_name["environment_hash"] == ["text"]
    assert by_name["created_at"] == ["date"]
    assert by_name["agent"] == ["text"]
    assert by_name["kei"] == ["text"]
    assert by_name["source_id"] == ["text"]


def test_class_definition_capitalises_name_and_pins_vectorizer_none() -> None:
    cls = schema.class_definition("discoveries")
    assert cls["class"] == "Discoveries"
    assert cls["vectorizer"] == "none"
    prop_names = [p["name"] for p in cls["properties"]]
    assert prop_names == [
        "raw_text",
        "environment_hash",
        "created_at",
        "agent",
        "kei",
        "source_id",
    ]


@pytest.mark.parametrize(
    "raw_name,expected_class",
    [
        ("codebase", "Codebase"),
        ("decisions", "Decisions"),
        ("discoveries", "Discoveries"),
        ("sessions", "Sessions"),
        ("keis", "Keis"),
    ],
)
def test_class_definition_all_5_collections(raw_name: str, expected_class: str) -> None:
    cls = schema.class_definition(raw_name)
    assert cls["class"] == expected_class
    assert cls["vectorizer"] == "none"
    assert "Agency OS" in cls["description"]


def test_apply_schema_dry_run_creates_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dry-run mode must not POST anywhere — only print the plan."""
    monkeypatch.setattr(schema, "existing_classes", lambda _u: set())
    post_calls: list = []
    monkeypatch.setattr(schema, "_post", lambda *a, **kw: post_calls.append((a, kw)) or {})

    rc = schema.apply_schema(
        "http://test:8090",  # NOSONAR python:S5332 test fixture, no real network
        dry_run=True,
    )
    assert rc == 0
    assert post_calls == []


def test_apply_schema_skips_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Idempotent: already-present collections are NOT re-created."""
    monkeypatch.setattr(
        schema,
        "existing_classes",
        lambda _u: {"Codebase", "Decisions"},
    )
    post_calls: list = []

    def fake_post(url: str, payload: dict, timeout: float = 10.0) -> dict:
        post_calls.append(payload["class"])
        return {}

    monkeypatch.setattr(schema, "_post", fake_post)
    rc = schema.apply_schema(
        "http://test:8090",  # NOSONAR python:S5332 test fixture, no real network
        dry_run=False,
    )
    assert rc == 0
    # Only the 3 missing get created.
    assert set(post_calls) == {"Discoveries", "Sessions", "Keis"}


def test_apply_schema_post_failure_returns_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error

    monkeypatch.setattr(schema, "existing_classes", lambda _u: set())

    def fake_post(*_a: object, **_kw: object) -> dict:
        raise urllib.error.HTTPError(
            "http://test:8090/v1/schema",  # NOSONAR python:S5332 test fixture, no real network
            422,
            "Unprocessable",
            {},
            mock.Mock(read=lambda: b"x"),
        )

    monkeypatch.setattr(schema, "_post", fake_post)
    rc = schema.apply_schema(
        "http://test:8090",  # NOSONAR python:S5332 test fixture, no real network
        dry_run=False,
    )
    assert rc == 1
