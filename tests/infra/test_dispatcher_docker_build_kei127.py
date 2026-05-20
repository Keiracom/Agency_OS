"""Tests for KEI-127 — Docker build + push to Railway via GH Actions.

Acceptance gate: the workflow, Dockerfile, and railway.toml service entry
must stay aligned. If any one is silently dropped or renamed, build-and-push
breaks on next push to main.

These tests are config-shape gates — they do NOT invoke `docker build` or
`railway up` (no daemon, no credentials in CI). The actual end-to-end
"workflow runs green on a test push" is the post-merge operator step.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "build-push-docker.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile.dispatcher"
RAILWAY_TOML = REPO_ROOT / "railway.toml"


def _load_workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())


def _load_railway_toml() -> dict:
    return tomllib.loads(RAILWAY_TOML.read_text())


def test_workflow_file_exists() -> None:
    assert WORKFLOW.exists(), f"{WORKFLOW} missing — KEI-127 workflow scaffold"


def test_workflow_is_valid_yaml() -> None:
    wf = _load_workflow()
    assert isinstance(wf, dict), "workflow must parse as a YAML mapping"


def test_workflow_triggers_only_on_main_push() -> None:
    wf = _load_workflow()
    # PyYAML rendering: the `on:` key — note `on` parses as bool True in YAML 1.1
    # under the resolver default. Accept both forms so we survive any future
    # YAML loader change without test rewrite.
    on_key = wf.get("on") or wf.get(True)
    assert on_key is not None, "workflow has no `on:` trigger block"
    push = on_key.get("push")
    assert push is not None, "workflow must trigger on push"
    assert push.get("branches") == ["main"], (
        f"expected branches=[main], got {push.get('branches')!r}"
    )
    paths = push.get("paths") or []
    expected_paths = {
        "Dockerfile.dispatcher",
        "src/dispatcher/**",
        "railway.toml",
        ".github/workflows/build-push-docker.yml",
    }
    missing = expected_paths - set(paths)
    assert not missing, f"workflow path filter missing entries: {missing}"


def test_workflow_uses_railway_token_secret() -> None:
    text = WORKFLOW.read_text()
    assert "${{ secrets.RAILWAY_TOKEN }}" in text, "workflow must auth via RAILWAY_TOKEN secret"


def test_workflow_targets_dispatcher_service() -> None:
    text = WORKFLOW.read_text()
    assert "--service dispatcher" in text, (
        "workflow must `railway up --service dispatcher` (not agency-os) — "
        "deploying to the wrong service would clobber the API."
    )


def test_workflow_has_concurrency_guard() -> None:
    """Prevents two main pushes from racing the same Railway deploy."""
    wf = _load_workflow()
    assert wf.get("concurrency"), "workflow needs a concurrency: block"


def test_dockerfile_dispatcher_exists() -> None:
    assert DOCKERFILE.exists(), "Dockerfile.dispatcher missing"


def test_dockerfile_dispatcher_starts_uvicorn() -> None:
    text = DOCKERFILE.read_text()
    assert "src.dispatcher.main:app" in text, (
        "Dockerfile.dispatcher must start uvicorn against src.dispatcher.main:app"
    )
    assert 'CMD ["sh"' in text, (
        "Dockerfile.dispatcher must have a CMD line invoking sh -c uvicorn …"
    )


def test_dockerfile_dispatcher_uses_pinned_python() -> None:
    """Slim python:3.11-slim base — matches the API/Worker Dockerfile."""
    text = DOCKERFILE.read_text()
    assert "FROM python:3.11-slim" in text, "Dockerfile.dispatcher must FROM python:3.11-slim"


def test_dockerfile_dispatcher_runs_non_root() -> None:
    """Security — never run uvicorn as root in a container."""
    text = DOCKERFILE.read_text()
    assert "USER dispatcher" in text, (
        "Dockerfile.dispatcher must drop privileges to a non-root user"
    )


def test_railway_toml_has_dispatcher_service() -> None:
    cfg = _load_railway_toml()
    services = cfg.get("services") or []
    dispatcher = next((s for s in services if s.get("name") == "dispatcher"), None)
    assert dispatcher is not None, "railway.toml has no [[services]] entry name='dispatcher'"


def test_railway_toml_dispatcher_uses_correct_dockerfile() -> None:
    cfg = _load_railway_toml()
    dispatcher = next(s for s in cfg["services"] if s.get("name") == "dispatcher")
    build = dispatcher.get("build", {})
    assert build.get("dockerfilePath") == "Dockerfile.dispatcher", (
        f"dispatcher service must point at Dockerfile.dispatcher, got {build.get('dockerfilePath')!r}"
    )


def test_railway_toml_dispatcher_healthcheck() -> None:
    cfg = _load_railway_toml()
    dispatcher = next(s for s in cfg["services"] if s.get("name") == "dispatcher")
    deploy = dispatcher.get("deploy", {})
    assert deploy.get("healthcheckPath") == "/dispatcher/health", (
        "dispatcher service must health-check /dispatcher/health"
    )


def test_python_version_supports_tomllib() -> None:
    """Guard: tomllib requires Python 3.11+. Catches CI image regressions."""
    assert sys.version_info >= (3, 11), "tests require Python 3.11+ (tomllib)"
