"""tests for scripts/cognee_ingest.py — Stream 1 batch ingestion.

All Cognee calls mocked (sole call surface via src.cognee.client wrapper).
Filesystem isolated via tmp_path + monkeypatch on REPO_ROOT / WORKTREES.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "cognee_ingest.py"


@pytest.fixture(scope="module")
def ingest_mod():
    spec = importlib.util.spec_from_file_location("cognee_ingest", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cognee_ingest"] = mod
    spec.loader.exec_module(mod)
    return mod


# _split_markdown ────────────────────────────────────────────────────────────


def test_split_markdown_at_h2_boundaries(ingest_mod) -> None:
    text = "intro\n\n## A\nbody-a\n\n## B\nbody-b"
    chunks = ingest_mod._split_markdown(text)
    assert len(chunks) == 3
    assert chunks[0] == "intro"
    assert chunks[1].startswith("## A")
    assert chunks[2].startswith("## B")


def test_split_markdown_falls_back_to_fixed_size(ingest_mod) -> None:
    huge = "x" * 9500
    chunks = ingest_mod._split_markdown(huge, max_chars=4000)
    assert len(chunks) == 3
    assert all(len(c) <= 4000 for c in chunks)


def test_split_markdown_drops_empty_sections(ingest_mod) -> None:
    text = "\n\n\n## A\nbody\n\n## B\n\n"
    chunks = ingest_mod._split_markdown(text)
    assert all(c.strip() for c in chunks)
    assert any("body" in c for c in chunks)


# load_file_chunks ───────────────────────────────────────────────────────────


def test_load_file_chunks_missing_file(ingest_mod, tmp_path) -> None:
    assert ingest_mod.load_file_chunks(tmp_path / "absent.md", "manual", []) == []


def test_load_file_chunks_attaches_source_and_extras(ingest_mod, tmp_path) -> None:
    p = tmp_path / "x.md"
    p.write_text("## Heading\nbody text")
    chunks = ingest_mod.load_file_chunks(p, "manual", ["file:custom"])
    assert chunks
    source_tag, chunk, node_set = chunks[0]
    assert source_tag == "manual"
    assert "body text" in chunk
    assert "source:manual" in node_set
    assert "file:custom" in node_set


# _stream_1_sources ──────────────────────────────────────────────────────────


def test_stream_1_sources_includes_top_level_docs(ingest_mod) -> None:
    sources = ingest_mod._stream_1_sources()
    rel_paths = [
        str(p.relative_to(ingest_mod.REPO_ROOT))
        for p, _, _ in sources
        if p.is_relative_to(ingest_mod.REPO_ROOT)
    ]
    assert "docs/MANUAL.md" in rel_paths
    assert "ARCHITECTURE.md" in rel_paths
    assert "DEFINITION_OF_DONE.md" in rel_paths


def test_stream_1_sources_includes_six_worktree_identity_and_heartbeat(ingest_mod) -> None:
    sources = ingest_mod._stream_1_sources()
    identity_tags = [tags for _, tag, tags in sources if tag == "identity"]
    heartbeat_tags = [tags for _, tag, tags in sources if tag == "heartbeat"]
    assert len(identity_tags) == 6
    assert len(heartbeat_tags) == 6
    # Each is tagged with the agent callsign
    callsigns = {t.split(":")[1] for tags in identity_tags for t in tags if t.startswith("agent:")}
    assert callsigns == {"elliot", "aiden", "max", "atlas", "orion", "scout"}


# parse_sources_override ─────────────────────────────────────────────────────


def test_parse_sources_override_resolves_relative_to_repo(ingest_mod) -> None:
    out = ingest_mod.parse_sources_override("docs/MANUAL.md,ARCHITECTURE.md")
    assert len(out) == 2
    assert all(p.is_absolute() for p, _, _ in out)
    assert all(tag == "override" for _, tag, _ in out)


def test_parse_sources_override_empty(ingest_mod) -> None:
    assert ingest_mod.parse_sources_override("") == []
    assert ingest_mod.parse_sources_override("   ,  ,") == []


def test_parse_sources_override_absolute_path_preserved(ingest_mod, tmp_path) -> None:
    out = ingest_mod.parse_sources_override(str(tmp_path / "x.md"))
    assert len(out) == 1
    assert out[0][0] == tmp_path / "x.md"


# collect_chunks ─────────────────────────────────────────────────────────────


def test_collect_chunks_filters_missing_files(ingest_mod, tmp_path) -> None:
    real = tmp_path / "real.md"
    real.write_text("body")
    sources = [
        (real, "manual", ["file:real"]),
        (tmp_path / "fake.md", "manual", ["file:fake"]),
    ]
    chunks = ingest_mod.collect_chunks(sources)
    assert len(chunks) == 1
    assert "body" in chunks[0][1]


# ingest (the async core) ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ingest_dry_run_does_not_call_add(ingest_mod) -> None:
    chunks = [("manual", "text", ["source:manual"])]
    ok, fail = await ingest_mod.ingest(
        chunks,
        org_id="org",
        app_id="app",
        agent_id="max",
        dry_run=True,
        skip_cognify=False,
    )
    assert ok == 1
    assert fail == 0


@pytest.mark.asyncio
async def test_ingest_calls_wrapper_add_and_cognify(ingest_mod, monkeypatch) -> None:
    fake_add = AsyncMock(return_value="added")
    fake_cognify = AsyncMock(return_value="cognified")
    # Inject a fake src.cognee.client module
    fake_module = MagicMock()
    fake_module.add = fake_add
    fake_module.cognify = fake_cognify
    monkeypatch.setitem(sys.modules, "src.cognee.client", fake_module)

    chunks = [
        ("manual", "text1", ["source:manual"]),
        ("architecture", "text2", ["source:architecture"]),
    ]
    ok, fail = await ingest_mod.ingest(
        chunks,
        org_id="org",
        app_id="app",
        agent_id="max",
        dry_run=False,
        skip_cognify=False,
    )
    assert ok == 2
    assert fail == 0
    assert fake_add.await_count == 2
    assert fake_cognify.await_count == 1


@pytest.mark.asyncio
async def test_ingest_skip_cognify(ingest_mod, monkeypatch) -> None:
    fake_add = AsyncMock(return_value="ok")
    fake_cognify = AsyncMock()
    fake_module = MagicMock()
    fake_module.add = fake_add
    fake_module.cognify = fake_cognify
    monkeypatch.setitem(sys.modules, "src.cognee.client", fake_module)

    await ingest_mod.ingest(
        [("manual", "t", [])],
        org_id="org",
        app_id="app",
        agent_id="max",
        dry_run=False,
        skip_cognify=True,
    )
    assert fake_cognify.await_count == 0


@pytest.mark.asyncio
async def test_ingest_per_chunk_failure_continues(ingest_mod, monkeypatch) -> None:
    async def flaky_add(content, **kwargs):
        if "bad" in content:
            raise RuntimeError("simulated cognee failure")
        return "ok"

    fake_module = MagicMock()
    fake_module.add = flaky_add
    fake_module.cognify = AsyncMock()
    monkeypatch.setitem(sys.modules, "src.cognee.client", fake_module)

    chunks = [
        ("manual", "good1", []),
        ("manual", "bad", []),
        ("manual", "good2", []),
    ]
    ok, fail = await ingest_mod.ingest(
        chunks,
        org_id="org",
        app_id="app",
        agent_id="max",
        dry_run=False,
        skip_cognify=True,
    )
    assert ok == 2
    assert fail == 1


@pytest.mark.asyncio
async def test_ingest_wrapper_import_failure_returns_all_fail(ingest_mod, monkeypatch) -> None:
    # Force import of src.cognee.client to fail
    real_import = (
        __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__
    )

    def fake_import(name, *args, **kwargs):
        if name == "src.cognee.client":
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.delitem(sys.modules, "src.cognee.client", raising=False)

    chunks = [("manual", "t1", []), ("manual", "t2", [])]
    ok, fail = await ingest_mod.ingest(
        chunks,
        org_id="org",
        app_id="app",
        agent_id="max",
        dry_run=False,
        skip_cognify=True,
    )
    assert ok == 0
    assert fail == 2


# main CLI ──────────────────────────────────────────────────────────────────


def test_main_dry_run_returns_zero(ingest_mod, monkeypatch, tmp_path) -> None:
    p = tmp_path / "x.md"
    p.write_text("body")
    result = ingest_mod.main(["--sources", str(p), "--dry-run"])
    assert result == 0


def test_main_no_chunks_returns_one(ingest_mod, tmp_path) -> None:
    # All --sources point to non-existent files → no chunks
    result = ingest_mod.main(["--sources", str(tmp_path / "absent.md"), "--dry-run"])
    assert result == 1


def test_main_default_args_dry_run(ingest_mod) -> None:
    # Default uses STREAM_1_SOURCES; --dry-run avoids wrapper import
    result = ingest_mod.main(["--dry-run"])
    assert result == 0
