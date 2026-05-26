"""Skills directory atomizer tests — Week 2 acceptance criterion (orchestrator)."""

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from src.keiracom_system.atomization import skills_atomizer
from src.keiracom_system.atomization.atomizer import AtomizerJob


class _FakeAtomizer:
    """Atomizer-shape fake — records each atomize() call + returns a synthetic job."""

    def __init__(self, *, fail_paths: set[str] | None = None):
        self.calls: list[dict[str, Any]] = []
        self.fail_paths = fail_paths or set()

    def atomize(self, *, source_ref: str, source_kind: str, source_text: str) -> AtomizerJob:
        self.calls.append(
            {"source_ref": source_ref, "source_kind": source_kind, "len": len(source_text)}
        )
        if source_ref in self.fail_paths:
            raise RuntimeError(f"simulated failure for {source_ref}")
        return AtomizerJob(
            job_id=uuid4(),
            tenant_id=uuid4(),
            source_ref=source_ref,
            source_kind=source_kind,
            atomizer_model="test/flash",
            atomizer_temp=0.0,
            atoms_produced=2,
            atom_ids=[uuid4(), uuid4()],
            status="atomizer_done",
        )


def _write_skills(root: Path, files: dict[str, str]) -> None:
    for rel_path, content in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


# ---- iter_skill_files ------------------------------------------------------


def test_iter_skill_files_yields_sorted_md_files(tmp_path: Path):
    _write_skills(
        tmp_path,
        {
            "b/SKILL.md": "B",
            "a/SKILL.md": "A",
            "c/IGNORE.txt": "not md",
            "a/sub/extra.md": "subdir",
        },
    )
    files = list(skills_atomizer.iter_skill_files(tmp_path))
    rel_paths = [str(f.relative_to(tmp_path)) for f in files]
    assert rel_paths == sorted(rel_paths)
    # txt file excluded
    assert all(p.endswith(".md") for p in rel_paths)
    assert "a/SKILL.md" in rel_paths
    assert "a/sub/extra.md" in rel_paths
    assert "b/SKILL.md" in rel_paths


def test_iter_skill_files_raises_on_missing_root(tmp_path: Path):
    with pytest.raises(skills_atomizer.SkillsAtomizerError, match="not a directory"):
        list(skills_atomizer.iter_skill_files(tmp_path / "does_not_exist"))


# ---- State file round-trip -------------------------------------------------


def test_state_roundtrip_only_keeps_ok_true(tmp_path: Path):
    state = tmp_path / "state.jsonl"
    assert skills_atomizer.load_state(state) == set()
    skills_atomizer.append_state(state, {"source_ref": "skills/a.md", "ok": True, "info": ""})
    skills_atomizer.append_state(state, {"source_ref": "skills/b.md", "ok": False, "info": "err"})
    skills_atomizer.append_state(state, {"source_ref": "skills/c.md", "ok": True, "info": ""})
    seen = skills_atomizer.load_state(state)
    assert seen == {"skills/a.md", "skills/c.md"}


def test_state_file_handles_corrupt_lines(tmp_path: Path):
    state = tmp_path / "state.jsonl"
    state.write_text(
        '{"source_ref": "ok1", "ok": true}\n{garbled json\n{"source_ref": "ok2", "ok": true}\n',
        encoding="utf-8",
    )
    seen = skills_atomizer.load_state(state)
    assert seen == {"ok1", "ok2"}


# ---- atomize_skill ---------------------------------------------------------


def test_atomize_skill_happy_path(tmp_path: Path):
    skill = tmp_path / "skills" / "x" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Skill X\n\nDo X when Y.", encoding="utf-8")
    fake = _FakeAtomizer()
    ok, info = skills_atomizer.atomize_skill(
        atomizer=fake,
        skill_path=skill,
        skills_root=tmp_path / "skills",
    )
    assert ok is True
    assert "atoms=2" in info
    assert len(fake.calls) == 1
    assert fake.calls[0]["source_ref"] == "skills/x/SKILL.md"
    assert fake.calls[0]["source_kind"] == "skill"


def test_atomize_skill_rejects_oversize_file(tmp_path: Path):
    skill = tmp_path / "skills" / "huge" / "BIG.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("x" * (skills_atomizer.MAX_SKILL_BYTES + 1), encoding="utf-8")
    fake = _FakeAtomizer()
    ok, info = skills_atomizer.atomize_skill(
        atomizer=fake,
        skill_path=skill,
        skills_root=tmp_path / "skills",
    )
    assert ok is False
    assert "exceeds MAX_SKILL_BYTES" in info
    # Did not call atomize on the oversized file
    assert fake.calls == []


def test_atomize_skill_returns_false_on_atomizer_exception(tmp_path: Path):
    skill = tmp_path / "skills" / "fail.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("content", encoding="utf-8")
    fake = _FakeAtomizer(fail_paths={"skills/fail.md"})
    ok, info = skills_atomizer.atomize_skill(
        atomizer=fake,
        skill_path=skill,
        skills_root=tmp_path / "skills",
    )
    assert ok is False
    assert "simulated failure" in info


# ---- run() — dry-run + execute paths ---------------------------------------


def test_run_dry_run_does_not_call_atomize(tmp_path: Path):
    skills_root = tmp_path / "skills"
    _write_skills(skills_root, {"a.md": "A", "b.md": "B"})
    fake = _FakeAtomizer()
    rc = skills_atomizer.run(
        atomizer=fake,
        skills_root=skills_root,
        state_path=tmp_path / "state.jsonl",
        execute=False,
    )
    assert rc == 0
    assert fake.calls == []  # dry-run skips


def test_run_execute_atomizes_each_skill(tmp_path: Path):
    skills_root = tmp_path / "skills"
    _write_skills(skills_root, {"a.md": "A", "sub/b.md": "B"})
    fake = _FakeAtomizer()
    rc = skills_atomizer.run(
        atomizer=fake,
        skills_root=skills_root,
        state_path=tmp_path / "state.jsonl",
        execute=True,
    )
    assert rc == 0
    assert len(fake.calls) == 2
    refs = {c["source_ref"] for c in fake.calls}
    assert refs == {"skills/a.md", "skills/sub/b.md"}


def test_run_execute_returns_one_on_any_failure(tmp_path: Path):
    skills_root = tmp_path / "skills"
    _write_skills(skills_root, {"good.md": "OK", "bad.md": "BAD"})
    fake = _FakeAtomizer(fail_paths={"skills/bad.md"})
    rc = skills_atomizer.run(
        atomizer=fake,
        skills_root=skills_root,
        state_path=tmp_path / "state.jsonl",
        execute=True,
    )
    assert rc == 1


def test_run_skips_already_atomized(tmp_path: Path):
    skills_root = tmp_path / "skills"
    _write_skills(skills_root, {"a.md": "A", "b.md": "B"})
    state = tmp_path / "state.jsonl"
    # Pre-populate state: a.md already done
    skills_atomizer.append_state(state, {"source_ref": "skills/a.md", "ok": True, "info": ""})
    fake = _FakeAtomizer()
    rc = skills_atomizer.run(
        atomizer=fake,
        skills_root=skills_root,
        state_path=state,
        execute=True,
    )
    assert rc == 0
    refs = [c["source_ref"] for c in fake.calls]
    assert refs == ["skills/b.md"]  # a.md skipped


def test_run_missing_skills_root_returns_two(tmp_path: Path):
    fake = _FakeAtomizer()
    rc = skills_atomizer.run(
        atomizer=fake,
        skills_root=tmp_path / "nonexistent",
        state_path=tmp_path / "state.jsonl",
        execute=True,
    )
    assert rc == 2
