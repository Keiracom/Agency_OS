"""Prefect Deployment: free-enrichment-flow (Stage 0/1 trigger fix).

Directive: BU Closed-Loop Engine — Substep 3.
Posture:   ACTIVE (paused=false). Stage 1 is AUD 0 — local DNS / httpx /
           abn_registry. Spider fallback is gated by SPIDER_API_KEY env var.
Schedule:  Hourly safety-net so newly-discovered BU rows enter the
           enrichment cursor without manual intervention.
"""
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

from src.orchestration.flows.free_enrichment_flow import free_enrichment_flow

free_enrichment_deployment = Deployment.build_from_flow(
    flow=free_enrichment_flow,
    name="free-enrichment-flow",
    version="1.0.0",
    tags=["bu-closed-loop", "free-enrichment", "stage-0-trigger", "free-mode"],
    description=(
        "BU Closed-Loop S3 free-enrichment flow. ACTIVE (AUD 0 — local DNS / "
        "httpx / abn_registry). Hourly safety-net: promotes stage-0/NULL BU "
        "rows to stage 1 then runs FreeEnrichment.run() over the backlog."
    ),
    schedule=CronSchedule(cron="15 * * * *", timezone="UTC"),
    is_schedule_active=True,
    parameters={
        "limit": 500,
        "promote_stage_0": True,
    },
    work_queue_name="default",
)


if __name__ == "__main__":
    free_enrichment_deployment.apply()
    print("Deployed: free-enrichment-flow/free-enrichment-flow (ACTIVE, hourly :15)")
    print("Run via: prefect deployment run 'free-enrichment-flow/free-enrichment-flow'")
    print("Override: -p limit=200 -p promote_stage_0=false")
