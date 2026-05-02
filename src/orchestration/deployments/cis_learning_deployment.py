"""
Prefect Deployment: CIS Learning Engine
Directive #147: Weekly weight optimization

Schedule: Every Sunday at 3:00 AM UTC
- Runs after a full week of outcomes
- Low-traffic time for minimal impact
- Before Monday campaigns begin

Manual trigger available via:
    prefect deployment run 'cis-learning-engine/cis-weekly'

M8 — migrated from Deployment.build_from_flow (removed in Prefect 3.x)
to flow.serve() per Prefect 3 docs. The CONFIG dicts are the single
source of truth and importable for tests; the __main__ block hands them
to flow.serve() to start the deployment server.
"""

from src.orchestration.flows.cis_learning_flow import cis_learning_flow

# Weekly deployment — runs every Sunday at 3 AM UTC
WEEKLY_CONFIG = {
    "name": "cis-weekly",
    "version": "1.0.0",
    "tags": ["cis", "learning", "weekly", "directive-147"],
    "description": (
        "Directive #147: CIS Learning Engine - Weekly weight adjustment. "
        "Analyzes meeting outcomes and adjusts propensity weights for "
        "continuous improvement. This is the moat."
    ),
    "cron": "0 3 * * 0",  # Every Sunday at 3:00 AM UTC
    "parameters": {
        "customer_id": None,  # Global weights
        "run_type": "weekly",
    },
}


# Manual / on-demand deployment — no schedule
MANUAL_CONFIG = {
    "name": "cis-manual",
    "version": "1.0.0",
    "tags": ["cis", "learning", "manual", "directive-147"],
    "description": (
        "Directive #147: CIS Learning Engine - Manual trigger. "
        "Use for testing or forced weight updates."
    ),
    # No 'cron' key — Prefect interprets absence as no schedule.
    "parameters": {
        "customer_id": None,
        "run_type": "manual",
    },
}


def serve_weekly() -> None:
    """Long-running serve for the weekly deployment."""
    cis_learning_flow.serve(**WEEKLY_CONFIG)


def serve_manual() -> None:
    """Long-running serve for the manual deployment."""
    cis_learning_flow.serve(**MANUAL_CONFIG)


def serve_both() -> None:
    """Serve both weekly + manual under one process. Prefect 3 supports
    multi-deployment serve via flow.serve.to_deployment + serve(...)."""
    weekly = cis_learning_flow.to_deployment(**WEEKLY_CONFIG)
    manual = cis_learning_flow.to_deployment(**MANUAL_CONFIG)
    from prefect import serve as _serve

    _serve(weekly, manual)


if __name__ == "__main__":
    print("Serving: cis-learning-engine/cis-weekly + cis-manual")
    print("Run weekly:    prefect deployment run 'cis-learning-engine/cis-weekly'")
    print("Run manual:    prefect deployment run 'cis-learning-engine/cis-manual'")
    print(
        "With customer: prefect deployment run 'cis-learning-engine/cis-manual' -p customer_id=<uuid>"
    )
    serve_both()
