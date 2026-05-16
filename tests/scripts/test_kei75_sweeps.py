"""KEI-75 sweep dry-run regression tests.

Locks the four corpus sweeps so future changes don't silently miss orphan
records, duplicate documents, or unstripped role-context prefixes.
Weaviate is fully mocked — these are unit tests over the sweep functions'
counting + reporting logic, not integration.
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

sweeps = importlib.import_module("scripts.orchestrator.kei75_sweeps")


def _obj(uuid_str: str, properties: dict) -> SimpleNamespace:
    return SimpleNamespace(uuid=uuid_str, properties=properties)


def _fake_client(by_collection: dict[str, list[SimpleNamespace]]) -> MagicMock:
    client = MagicMock()
    collections: dict[str, MagicMock] = {}

    def get(name: str) -> MagicMock:
        if name in collections:
            return collections[name]
        coll = MagicMock()
        objects = by_collection.get(name, [])

        def fetch_objects(limit=200, after=None, include_vector=False):
            if after is None:
                start = 0
            else:
                start = next(
                    (i + 1 for i, o in enumerate(objects) if o.uuid == after), len(objects)
                )
            slab = objects[start : start + limit]
            return SimpleNamespace(objects=slab)

        coll.query.fetch_objects.side_effect = fetch_objects
        coll.data.delete_by_id = MagicMock()
        coll.data.update = MagicMock()
        collections[name] = coll
        return coll

    client.collections.get.side_effect = get
    return client


def test_wave4_raw_text_counts_empty_objects():
    client = _fake_client(
        {
            "Sessions": [
                _obj("a", {"raw_text": "hello"}),
                _obj("b", {"raw_text": ""}),
                _obj("c", {"raw_text": "   "}),
                _obj("d", {"raw_text": None}),
            ]
        }
    )
    report = sweeps.sweep_wave4_raw_text(client, apply=False)
    assert report["sweep"] == "wave4-raw-text"
    assert report["would_change"] == 3
    assert report["applied"] is False
    assert client.collections.get("Sessions").data.delete_by_id.call_count == 0


def test_wave4_raw_text_applies_deletions():
    client = _fake_client({"Sessions": [_obj("a", {"raw_text": ""}), _obj("b", {"raw_text": ""})]})
    sweeps.sweep_wave4_raw_text(client, apply=True)
    assert client.collections.get("Sessions").data.delete_by_id.call_count == 2


def test_wave4_agent_counts_unknown_only():
    client = _fake_client(
        {
            "Sessions": [
                _obj("a", {"agent": "max"}),
                _obj("b", {"agent": "unknown"}),
                _obj("c", {"agent": "unknown"}),
            ]
        }
    )
    report = sweeps.sweep_wave4_agent(client, apply=False)
    assert report["would_change"] == 2


def test_wave3_dedup_keeps_oldest_within_bucket():
    client = _fake_client(
        {
            "Discoveries": [
                _obj(
                    "old", {"raw_text": "same body", "source_path": "x.md", "created_at": "2026-01"}
                ),
                _obj(
                    "mid", {"raw_text": "same body", "source_path": "x.md", "created_at": "2026-03"}
                ),
                _obj(
                    "new", {"raw_text": "same body", "source_path": "x.md", "created_at": "2026-05"}
                ),
                _obj(
                    "unique",
                    {"raw_text": "different", "source_path": "x.md", "created_at": "2026-01"},
                ),
            ]
        }
    )
    report = sweeps.sweep_wave3_dedup(client, apply=False)
    assert report["would_change"] == 2  # mid + new dropped, old kept, unique kept
    assert "old" not in report["sample"]
    assert "unique" not in report["sample"]


def test_wave3_dedup_skips_empty_text():
    client = _fake_client(
        {
            "Discoveries": [
                _obj("a", {"raw_text": "", "source_path": "x.md", "created_at": "2026-01"}),
                _obj("b", {"raw_text": "  ", "source_path": "x.md", "created_at": "2026-01"}),
            ]
        }
    )
    report = sweeps.sweep_wave3_dedup(client, apply=False)
    assert report["would_change"] == 0


def test_role_flag_strips_prefix_and_sets_metadata():
    client = _fake_client(
        {
            "Discoveries": [
                _obj(
                    "a", {"raw_text": "[ROLE-CONTEXT-PRE-2026-05-11: 'CTO'=Elliot, 'COO'=Max] body"}
                ),
                _obj("b", {"raw_text": "plain body"}),
            ],
            "Sessions": [
                _obj("c", {"raw_text": "[ROLE-CONTEXT-PRE-2026-05-11: foo] line two"}),
            ],
        }
    )
    report = sweeps.sweep_role_flag(client, apply=True)
    assert report["would_change"] == 2
    discoveries = client.collections.get("Discoveries")
    sessions = client.collections.get("Sessions")
    update_call = discoveries.data.update.call_args_list[0]
    assert update_call.kwargs["properties"]["raw_text"] == "body"
    assert update_call.kwargs["properties"]["role_flag"] == "pre_2026-05-11_role_swap"
    sessions_call = sessions.data.update.call_args_list[0]
    assert sessions_call.kwargs["properties"]["role_flag"] == "pre_2026-05-11_role_swap"


def test_sweep_names_exposes_all_plus_individual():
    assert {
        "wave4-raw-text",
        "wave4-agent",
        "wave3-dedup",
        "role-flag",
        "all",
    } == sweeps.SWEEP_NAMES
