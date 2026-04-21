"""Prefect Deployment: Pipeline F Master Flow
P4 Build — manual trigger for P5 validation, cron placeholder for production.
"""
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

from src.orchestration.flows.pipeline_f_master_flow import pipeline_f_master_flow

pipeline_f_deployment = Deployment.build_from_flow(
    flow=pipeline_f_master_flow,
    name="pipeline-f-p5",
    version="1.0.0",
    tags=["p4", "pipeline-f", "master-flow"],
    description="P4 Build: Pipeline F master flow. Manual trigger for P5 validation.",
    schedule=None,  # Manual trigger only for P5. Production cron TBD post-P5.
    parameters={
        "categories": ["dental", "plumbing", "legal", "accounting", "fitness"],
        "domains_per_category": 2,
        "dry_run": False,
        "budget_cap_aud": 25.0,
    },
    work_queue_name="default",
)


if __name__ == "__main__":
    pipeline_f_deployment.apply()
    print("Deployed: pipeline-f-master-flow/pipeline-f-p5 (manual trigger)")
    print("Run via: prefect deployment run 'pipeline-f-master-flow/pipeline-f-p5'")
