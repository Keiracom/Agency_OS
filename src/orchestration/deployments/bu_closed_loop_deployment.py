"""Prefect Deployment: BU Closed-Loop backlog driver flow.

Directive: BU Closed-Loop Engine — Substep 2 of 4.
Posture:   PAUSED by default. Schedule: daily 04:00 UTC.

Unpause criteria (per repo pause-governance policy in prefect.yaml):
  - S3 (data-mapping) ratified — domain_data reconstruction from BU columns
    needs to be complete enough that _run_stageN early-exits drop below
    a documented threshold.
  - Live-spend safety review confirmed AUD 0 budget enforcement holds when
    free_mode_only=True at scale.
"""
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

from src.orchestration.flows.bu_closed_loop_flow import bu_closed_loop_flow

bu_closed_loop_deployment = Deployment.build_from_flow(
    flow=bu_closed_loop_flow,
    name="bu-closed-loop-flow",
    version="1.0.0",
    tags=["bu-closed-loop", "backlog-driver", "free-mode", "paused"],
    description=(
        "BU Closed-Loop S2 backlog driver. PAUSED by default. Daily 04:00 UTC "
        "scan of stuck BU rows; advances by one stage per row in free-mode "
        "(zero AUD spend) using age-tiered cadence."
    ),
    schedule=CronSchedule(cron="0 4 * * *", timezone="UTC"),
    is_schedule_active=False,  # Schedule INACTIVE until S3 ratifies
    parameters={
        "max_rows": 500,
        "free_mode_only": True,
        "cadence_hot_days": 14,
        "cadence_warm_days": 60,
        "cadence_cold_days": 180,
    },
    work_queue_name="default",
)


if __name__ == "__main__":
    bu_closed_loop_deployment.apply()
    print("Deployed: bu-closed-loop-flow/bu-closed-loop-flow (PAUSED, 04:00 UTC daily)")
    print("Run via: prefect deployment run 'bu-closed-loop-flow/bu-closed-loop-flow'")
    print("Override: -p max_rows=100 -p free_mode_only=true -p cadence_hot_days=7")
