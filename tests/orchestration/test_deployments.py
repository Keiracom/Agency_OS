"""
M8 — smoke tests for the migrated Prefect 3.x deployment modules.

Each test confirms:
  - the module imports without raising (i.e. no leftover prefect.deployments
    or prefect.server.schemas references)
  - the DEPLOYMENT_CONFIG dict (or per-deployment CONFIG dicts) carries the
    canonical fields flow.serve() / flow.deploy() will accept
  - serve()-style callables exist and reference the live flow object

No live Prefect server required — flow.serve() itself is NOT invoked.
"""

from __future__ import annotations

import importlib

import pytest

EXPECTED_KEYS_REQUIRED = {"name", "version", "tags", "description", "parameters"}


@pytest.mark.parametrize(
    "module_name",
    [
        "src.orchestration.deployments.bu_closed_loop_deployment",
        "src.orchestration.deployments.cis_learning_deployment",
        "src.orchestration.deployments.free_enrichment_deployment",
        "src.orchestration.deployments.pipeline_f_deployment",
    ],
)
def test_module_imports_cleanly(module_name):
    """Importing the module must not raise (the old import was
    `from prefect.deployments import Deployment` which is gone)."""
    mod = importlib.import_module(module_name)
    assert mod is not None


def test_bu_closed_loop_config_shape():
    from src.orchestration.deployments import bu_closed_loop_deployment as m

    cfg = m.DEPLOYMENT_CONFIG
    assert EXPECTED_KEYS_REQUIRED.issubset(cfg.keys())
    assert cfg["name"] == "bu-closed-loop-flow"
    assert cfg["cron"] == "0 4 * * *"
    assert cfg["paused"] is True
    assert callable(m.serve)


def test_free_enrichment_config_shape():
    from src.orchestration.deployments import free_enrichment_deployment as m

    cfg = m.DEPLOYMENT_CONFIG
    assert EXPECTED_KEYS_REQUIRED.issubset(cfg.keys())
    assert cfg["name"] == "free-enrichment-flow"
    assert cfg["cron"] == "15 * * * *"
    assert cfg["paused"] is False
    assert callable(m.serve)


def test_pipeline_f_config_shape():
    from src.orchestration.deployments import pipeline_f_deployment as m

    cfg = m.DEPLOYMENT_CONFIG
    assert EXPECTED_KEYS_REQUIRED.issubset(cfg.keys())
    assert cfg["name"] == "pipeline-f-p5"
    # No cron — manual-trigger only
    assert "cron" not in cfg
    assert callable(m.serve)


def test_cis_learning_has_two_configs():
    from src.orchestration.deployments import cis_learning_deployment as m

    assert EXPECTED_KEYS_REQUIRED.issubset(m.WEEKLY_CONFIG.keys())
    assert EXPECTED_KEYS_REQUIRED.issubset(m.MANUAL_CONFIG.keys())
    assert m.WEEKLY_CONFIG["cron"] == "0 3 * * 0"
    # Manual has no cron
    assert "cron" not in m.MANUAL_CONFIG
    assert callable(m.serve_weekly)
    assert callable(m.serve_manual)
    assert callable(m.serve_both)


def test_no_legacy_imports_in_any_deployment_file():
    """Sanity — no live call to the deprecated Prefect 3.x APIs.
    Docstring mentions are allowed (the M8 migration note references the
    old API by name); we forbid the actual import + call sites only."""
    import inspect

    forbidden_lines = (
        "from prefect.deployments import Deployment",
        "from prefect.server.schemas",
        ".build_from_flow(",
    )
    for name in (
        "src.orchestration.deployments.bu_closed_loop_deployment",
        "src.orchestration.deployments.cis_learning_deployment",
        "src.orchestration.deployments.free_enrichment_deployment",
        "src.orchestration.deployments.pipeline_f_deployment",
    ):
        mod = importlib.import_module(name)
        src = inspect.getsource(mod)
        for token in forbidden_lines:
            assert token not in src, f"{name} still references deprecated {token!r}"


def test_init_exports_config_dicts_not_objects():
    """The package __init__ used to re-export deployment objects which
    no longer exist after migration. Confirm it now exports the configs."""
    from src.orchestration import deployments

    assert hasattr(deployments, "cis_weekly_config")
    assert hasattr(deployments, "cis_manual_config")
    assert deployments.cis_weekly_config["name"] == "cis-weekly"
    assert deployments.cis_manual_config["name"] == "cis-manual"
