"""
Prefect Deployment: CIS Learning Engine
Directive #147: Weekly weight optimization

Schedule: Every Sunday at 3:00 AM UTC
- Runs after a full week of outcomes
- Low-traffic time for minimal impact
- Before Monday campaigns begin

Manual trigger available via:
    prefect deployment run 'cis-learning-engine/cis-weekly'
"""

from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

from src.orchestration.flows.cis_learning_flow import cis_learning_flow

# Weekly deployment - runs every Sunday at 3 AM UTC
cis_weekly_deployment = Deployment.build_from_flow(
    flow=cis_learning_flow,
    name="cis-weekly",
    version="1.0.0",
    tags=["cis", "learning", "weekly", "directive-147"],
    description=(
        "Directive #147: CIS Learning Engine - Weekly weight adjustment. "
        "Analyzes meeting outcomes and adjusts propensity weights for "
        "continuous improvement. This is the moat."
    ),
    schedule=CronSchedule(
        cron="0 3 * * 0",  # Every Sunday at 3:00 AM UTC
        timezone="UTC",
    ),
    parameters={
        "customer_id": None,  # Global weights
        "run_type": "weekly",
    },
    work_queue_name="default",
)


# Manual/on-demand deployment - no schedule
cis_manual_deployment = Deployment.build_from_flow(
    flow=cis_learning_flow,
    name="cis-manual",
    version="1.0.0",
    tags=["cis", "learning", "manual", "directive-147"],
    description=(
        "Directive #147: CIS Learning Engine - Manual trigger. "
        "Use for testing or forced weight updates."
    ),
    schedule=None,  # No automatic schedule
    parameters={
        "customer_id": None,
        "run_type": "manual",
    },
    work_queue_name="default",
)


if __name__ == "__main__":
    # Deploy both configurations
    cis_weekly_deployment.apply()
    print("✓ Deployed: cis-learning-engine/cis-weekly (Sundays 3 AM UTC)")

    cis_manual_deployment.apply()
    print("✓ Deployed: cis-learning-engine/cis-manual (on-demand)")

    print("\nDeployment commands:")
    print("  Run weekly:  prefect deployment run 'cis-learning-engine/cis-weekly'")
    print("  Run manual:  prefect deployment run 'cis-learning-engine/cis-manual'")
    print("  With customer: prefect deployment run 'cis-learning-engine/cis-manual' -p customer_id=<uuid>")
