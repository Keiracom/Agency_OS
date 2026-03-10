"""
Prefect Deployments Package
Contains deployment configurations for all flows.
"""

from src.orchestration.deployments.cis_learning_deployment import (
    cis_manual_deployment,
    cis_weekly_deployment,
)

__all__ = [
    "cis_weekly_deployment",
    "cis_manual_deployment",
]
