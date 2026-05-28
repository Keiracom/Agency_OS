"""Smoke + behavior tests for scripts/hydrate_spawn_template.py.

The dispatch's required smoke test: hydrate for callsign=orion and assert
`<CALLSIGN>` does not appear in the output. Plus: model/orchestrator stamped,
worker vs deliberator line selection, mutual-exclusivity guard, runtime
placeholders (`[CLAIM:<callsign>]`, `<path>`) preserved, and the full
fully-hydrated assertion. Subprocess-invoked, exactly as a spawn launch runs it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "hydrate_spawn_template.py"


def _run(*args: str) -> tuple[int, str, str]:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return cp.returncode, cp.stdout, cp.stderr


def test_smoke_orion_no_callsign_placeholder_remains():
    """Dispatch's required smoke test."""
    rc, out, err = _run(
        "--callsign",
        "orion",
        "--orchestrator",
        "elliot",
        "--model",
        "gemini-2.5-flash",
        "--specialty",
        "build/retrieval",
    )
    assert rc == 0, err
    assert "<CALLSIGN>" not in out
    assert "orion" in out


def test_no_hydration_placeholders_remain_for_worker():
    rc, out, _ = _run(
        "--callsign",
        "orion",
        "--orchestrator",
        "elliot",
        "--model",
        "gemini-2.5-flash",
        "--specialty",
        "build/retrieval",
    )
    assert rc == 0
    for ph in ("<CALLSIGN>", "<ORCHESTRATOR>", "<MODEL>", "<ROLE_LENS>", "<SPECIALTY>"):
        assert ph not in out, f"{ph} survived hydration"


def test_scalars_are_stamped():
    rc, out, _ = _run(
        "--callsign",
        "orion",
        "--orchestrator",
        "elliot",
        "--model",
        "gemini-2.5-flash",
        "--specialty",
        "build/retrieval",
    )
    assert rc == 0
    assert "elliot" in out and "gemini-2.5-flash" in out and "build/retrieval" in out


def test_worker_omits_deliberation_lens_line():
    rc, out, _ = _run(
        "--callsign",
        "orion",
        "--orchestrator",
        "elliot",
        "--model",
        "gemini-2.5-flash",
        "--specialty",
        "build/retrieval",
    )
    assert rc == 0
    assert "Deliberation lens:" not in out  # line dropped for a worker
    assert "Specialty:" in out


def test_deliberator_omits_specialty_line():
    rc, out, _ = _run(
        "--callsign",
        "aiden",
        "--orchestrator",
        "dave",
        "--model",
        "claude-opus-4-6",
        "--role-lens",
        "governance/architecture",
    )
    assert rc == 0
    assert "Specialty:" not in out  # line dropped for a deliberator
    assert "Deliberation lens:" in out
    assert "governance/architecture" in out


def test_role_lens_and_specialty_are_mutually_exclusive():
    rc, _out, err = _run(
        "--callsign",
        "orion",
        "--orchestrator",
        "elliot",
        "--model",
        "gemini-2.5-flash",
        "--role-lens",
        "code-quality",
        "--specialty",
        "build/retrieval",
    )
    assert rc != 0
    assert "mutually exclusive" in err


def test_runtime_placeholders_are_preserved():
    """Lowercase / runtime placeholders inside the governance text must survive —
    the agent fills them when it posts a claim, not the hydrator."""
    rc, out, _ = _run(
        "--callsign",
        "orion",
        "--orchestrator",
        "elliot",
        "--model",
        "gemini-2.5-flash",
        "--specialty",
        "build/retrieval",
    )
    assert rc == 0
    assert "[CLAIM:<callsign>]" in out  # runtime placeholder, NOT hydrated
    assert "<path>" in out and "<min>" in out


def test_missing_required_arg_errors():
    rc, _out, err = _run("--callsign", "orion")
    assert rc != 0
    assert "orchestrator" in err.lower() or "required" in err.lower()


def _load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("_hydrate_spawn_template", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_omitting_a_conditional_bullet_drops_its_wrapped_continuation_lines():
    """Regression guard: omitting a conditional bullet must also drop its wrapped
    continuation lines, so no orphan fragment leaks into a worker's prompt."""
    mod = _load_module()
    template = (
        "- **Deliberation lens:** `<ROLE_LENS>` — review through this lens\n"
        "  (deliberators only: elliot, aiden, max).\n"
        "- **Specialty:** `<SPECIALTY>` — assumed competence.\n"
    )
    out = mod.hydrate(
        template,
        callsign="orion",
        orchestrator="elliot",
        model="gemini-2.5-flash",
        specialty="build/retrieval",  # worker → lens bullet omitted
    )
    assert "Deliberation lens:" not in out
    assert "(deliberators only:" not in out  # the wrapped continuation is gone too
    assert "build/retrieval" in out
