"""Prefect Deployment: Pipeline F Master Flow
P4 Build — manual trigger for P5 validation, cron placeholder for production.

T4 (2026-04-24): Deployment parameters now include tier / demo_mode / client_id
so a single deployment can be triggered per-tier or per-client without redeploying.

M8 (2026-04-26): Migrated from Deployment.build_from_flow (removed in
Prefect 3.x) to flow.serve() per Prefect 3 docs. Production deployment is
canonical via prefect.yaml's `pipeline-f-master-flow` entry; running this
script is for ad-hoc / local-dev serve sessions.
"""

from src.orchestration.flows.pipeline_f_master_flow import pipeline_f_master_flow

DEPLOYMENT_CONFIG = {
    "name": "pipeline-f-p5",
    "version": "1.1.0",
    "tags": ["p4", "pipeline-f", "master-flow", "cd-player-v1"],
    "description": (
        "P4 Build: Pipeline F master flow (CD Player v1). Manual trigger for P5 validation. "
        "Tier-aware runtime via {tier, demo_mode, client_id} parameters."
    ),
    # No 'cron' key — manual trigger only for P5. Production cron TBD post-P5.
    "parameters": {
        # T4 params — tier-aware CD Player v1 wiring
        "tier": "ignition",
        "demo_mode": False,
        "client_id": None,
        # Legacy discovery + budget knobs
        "categories": ["dental", "plumbing", "legal", "accounting", "fitness"],
        "dry_run": False,
        "budget_cap_aud": None,  # None → let tier default win (see _tier_runtime)
    },
}


def serve() -> None:
    """Run the flow as a long-lived Prefect 3 server.
    Replaces the legacy Deployment.build_from_flow.apply pattern pattern."""
    pipeline_f_master_flow.serve(**DEPLOYMENT_CONFIG)


if __name__ == "__main__":
    print("Serving: pipeline-f-master-flow/pipeline-f-p5 (manual trigger, tier-aware)")
    print("Run via: prefect deployment run 'pipeline-f-master-flow/pipeline-f-p5'")
    print(
        "Override params: prefect deployment run '...' -p tier=spark -p demo_mode=true -p client_id=test"
    )
    serve()
