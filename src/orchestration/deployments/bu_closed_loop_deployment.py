"""Prefect Deployment: BU Closed-Loop backlog driver flow.

Directive: BU Closed-Loop Engine — Substep 2 of 4.
Posture:   PAUSED by default. Schedule: daily 04:00 UTC.

M8 — migrated from Deployment.build_from_flow (removed in Prefect 3.x)
to flow.serve() per Prefect 3 docs. The DEPLOYMENT_CONFIG dict is the
single source of truth and is consumed both by the __main__ entry-point
(when this file is run directly) and by tests that validate config shape.

Production deployment is canonical via prefect.yaml's `bu-closed-loop-flow`
entry — running this script is for ad-hoc / local-dev serve sessions.

Unpause criteria (per repo pause-governance policy in prefect.yaml):
  - S3 (data-mapping) ratified — domain_data reconstruction from BU columns
    needs to be complete enough that _run_stageN early-exits drop below
    a documented threshold.
  - Live-spend safety review confirmed AUD 0 budget enforcement holds when
    free_mode_only=True at scale.
"""

from src.orchestration.flows.bu_closed_loop_flow import bu_closed_loop_flow

DEPLOYMENT_CONFIG = {
    "name": "bu-closed-loop-flow",
    "version": "1.0.0",
    "tags": ["bu-closed-loop", "backlog-driver", "free-mode", "paused"],
    "description": (
        "BU Closed-Loop S2 backlog driver. PAUSED by default. Daily 04:00 UTC "
        "scan of stuck BU rows; advances by one stage per row in free-mode "
        "(zero AUD spend) using age-tiered cadence."
    ),
    "cron": "0 4 * * *",
    "paused": True,  # PAUSED until S3 ratifies (was is_schedule_active=False)
    "parameters": {
        "max_rows": 500,
        "free_mode_only": True,
        "cadence_hot_days": 14,
        "cadence_warm_days": 60,
        "cadence_cold_days": 180,
    },
}


def serve() -> None:
    """Run the flow as a long-lived Prefect 3 server.
    Replaces the legacy Deployment.build_from_flow.apply pattern pattern."""
    bu_closed_loop_flow.serve(**DEPLOYMENT_CONFIG)


if __name__ == "__main__":
    print("Serving: bu-closed-loop-flow (PAUSED, 04:00 UTC daily)")
    print("Run via: prefect deployment run 'bu-closed-loop-flow/bu-closed-loop-flow'")
    print("Override: -p max_rows=100 -p free_mode_only=true -p cadence_hot_days=7")
    serve()
