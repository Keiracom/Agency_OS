"""
Prefect Deployments Package — config dicts + serve() entry-points.

M8 (2026-04-26): The legacy `Deployment.build_from_flow(...)` API was
removed in Prefect 3.x. Each deployment file now exposes a config dict
(consumed by tests) plus a `serve()` callable; the deployment object no
longer exists at module-import time, so the legacy re-exports
(cis_weekly_deployment / cis_manual_deployment) have been removed.

Production deployments are configured in prefect.yaml. The .py files in
this package are for ad-hoc / local-dev `flow.serve()` sessions — run
each as `python -m src.orchestration.deployments.X` when needed.
"""

from src.orchestration.deployments.cis_learning_deployment import (
    MANUAL_CONFIG as cis_manual_config,
)
from src.orchestration.deployments.cis_learning_deployment import (
    WEEKLY_CONFIG as cis_weekly_config,
)

__all__ = [
    "cis_weekly_config",
    "cis_manual_config",
]
