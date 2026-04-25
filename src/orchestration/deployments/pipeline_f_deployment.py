"""Prefect Deployment: Pipeline F Master Flow
P4 Build — manual trigger for P5 validation, cron placeholder for production.

T4 (2026-04-24): Deployment parameters now include tier / demo_mode / client_id
so a single deployment can be triggered per-tier or per-client without redeploying.
"""
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

from src.orchestration.flows.pipeline_f_master_flow import pipeline_f_master_flow

pipeline_f_deployment = Deployment.build_from_flow(
    flow=pipeline_f_master_flow,
    name="pipeline-f-p5",
    version="1.1.0",
    tags=["p4", "pipeline-f", "master-flow", "cd-player-v1"],
    description=(
        "P4 Build: Pipeline F master flow (CD Player v1). Manual trigger for P5 validation. "
        "Tier-aware runtime via {tier, demo_mode, client_id} parameters."
    ),
    schedule=None,  # Manual trigger only for P5. Production cron TBD post-P5.
    parameters={
        # T4 params — tier-aware CD Player v1 wiring
        "tier": "ignition",
        "demo_mode": False,
        "client_id": None,
        # Legacy discovery + budget knobs
        "categories": ["dental", "plumbing", "legal", "accounting", "fitness"],
        "dry_run": False,
        "budget_cap_aud": None,  # None → let tier default win (see _tier_runtime)
    },
    work_queue_name="default",
)


if __name__ == "__main__":
    pipeline_f_deployment.apply()
    print("Deployed: pipeline-f-master-flow/pipeline-f-p5 (manual trigger, tier-aware)")
    print("Run via: prefect deployment run 'pipeline-f-master-flow/pipeline-f-p5'")
    print("Override params: prefect deployment run '...' -p tier=spark -p demo_mode=true -p client_id=test")
