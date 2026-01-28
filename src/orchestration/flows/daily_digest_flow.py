"""
FILE: src/orchestration/flows/daily_digest_flow.py
PURPOSE: Prefect flow for sending daily digest emails to clients
PHASE: H (Client Transparency)
TASK: Item 44 - Daily Digest Email
DEPENDENCIES:
  - src/services/digest_service.py
  - src/engines/email.py
  - src/integrations/salesforge.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 7: Prefect for orchestration
"""

import logging
from datetime import date, timedelta
from uuid import UUID

from prefect import flow, get_run_logger, task
from prefect.runtime import flow_run

from src.config.database import get_db_session
from src.config.settings import settings
from src.services.digest_service import DigestService

logger = logging.getLogger(__name__)


@task(name="get_clients_for_digest", retries=2, retry_delay_seconds=10)
async def get_clients_for_digest_task(target_hour: int = 7) -> list[dict]:
    """
    Get all clients that should receive a digest at the specified hour.

    Args:
        target_hour: Hour of day in client's timezone (0-23)

    Returns:
        List of client dicts with id and name
    """
    log = get_run_logger()

    async with get_db_session() as db:
        service = DigestService(db)
        clients = await service.get_clients_for_digest(target_hour=target_hour)

        result = [{"id": str(client.id), "name": client.name} for client in clients]

        log.info(f"Found {len(result)} clients for digest at hour {target_hour}")
        return result


@task(name="get_digest_data", retries=2, retry_delay_seconds=5)
async def get_digest_data_task(client_id: str, digest_date: date) -> dict:
    """
    Get digest data for a client.

    Args:
        client_id: Client UUID as string
        digest_date: Date to generate digest for

    Returns:
        Digest data dict
    """
    log = get_run_logger()

    async with get_db_session() as db:
        service = DigestService(db)

        # Check if already sent
        already_sent = await service.check_already_sent(UUID(client_id), digest_date)
        if already_sent:
            log.info(f"Digest already sent for client {client_id} on {digest_date}")
            return {"skipped": True, "reason": "already_sent"}

        # Get digest data
        digest_data = await service.get_digest_data(UUID(client_id), digest_date)
        log.info(
            f"Got digest data for {digest_data['client_name']}: "
            f"sent={digest_data['metrics']['sent']}, "
            f"replies={digest_data['metrics']['replies']}"
        )

        return digest_data


@task(name="render_digest_html", retries=1)
async def render_digest_html_task(digest_data: dict) -> str | None:
    """
    Render digest data as HTML email.

    Args:
        digest_data: Data from get_digest_data_task

    Returns:
        HTML string or None if skipped
    """
    if digest_data.get("skipped"):
        return None

    async with get_db_session() as db:
        service = DigestService(db)

        # Get dashboard URL from settings
        dashboard_url = getattr(settings, "FRONTEND_URL", "https://app.agencyos.ai")

        html = service.render_digest_html(digest_data, dashboard_url=f"{dashboard_url}/dashboard")

        return html


@task(name="get_recipients", retries=2, retry_delay_seconds=5)
async def get_recipients_task(client_id: str) -> list[str]:
    """
    Get email recipients for digest.

    Args:
        client_id: Client UUID as string

    Returns:
        List of email addresses
    """
    async with get_db_session() as db:
        service = DigestService(db)
        recipients = await service.get_digest_recipients(UUID(client_id))
        return recipients


@task(name="send_digest_email", retries=3, retry_delay_seconds=30)
async def send_digest_email_task(
    client_id: str,
    client_name: str,
    recipients: list[str],
    html_content: str,
    digest_date: date,
) -> dict:
    """
    Send digest email via Salesforge.

    Args:
        client_id: Client UUID as string
        client_name: Client name for email
        recipients: List of recipient emails
        html_content: HTML email content
        digest_date: Date the digest is for

    Returns:
        Send result dict
    """
    log = get_run_logger()

    if not recipients:
        log.warning(f"No recipients for client {client_id}")
        return {"sent": False, "reason": "no_recipients"}

    if not html_content:
        log.info(f"No content to send for client {client_id}")
        return {"sent": False, "reason": "no_content"}

    # TEST_MODE: Redirect to test recipient
    if settings.TEST_MODE:
        original_recipients = recipients
        recipients = [settings.TEST_EMAIL_RECIPIENT]
        log.info(f"TEST_MODE: Redirecting digest from {original_recipients} to {recipients}")

    try:
        # Import email engine
        from src.engines.email import EmailEngine

        async with get_db_session() as db:
            email_engine = EmailEngine(db)

            # Send to each recipient
            sent_count = 0
            errors = []

            for recipient in recipients:
                try:
                    # Use a transactional send (not cold outreach mailbox)
                    result = await email_engine.send_transactional(
                        to_email=recipient,
                        subject=f"Daily Digest - {client_name} - {digest_date.strftime('%B %d, %Y')}",
                        html_body=html_content,
                        from_name="Agency OS",
                    )

                    if result.get("success"):
                        sent_count += 1
                        log.info(f"Sent digest to {recipient}")
                    else:
                        errors.append(f"{recipient}: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    errors.append(f"{recipient}: {str(e)}")
                    log.error(f"Failed to send digest to {recipient}: {e}")

            return {
                "sent": True,
                "sent_count": sent_count,
                "total_recipients": len(recipients),
                "errors": errors if errors else None,
            }

    except Exception as e:
        log.error(f"Failed to send digest for client {client_id}: {e}")
        return {"sent": False, "error": str(e)}


@task(name="log_digest_result", retries=2, retry_delay_seconds=5)
async def log_digest_result_task(
    client_id: str,
    digest_date: date,
    recipients: list[str],
    digest_data: dict,
    send_result: dict,
) -> None:
    """
    Log digest send result.

    Args:
        client_id: Client UUID as string
        digest_date: Date the digest is for
        recipients: List of recipient emails
        digest_data: Original digest data
        send_result: Result from send task
    """
    log = get_run_logger()

    async with get_db_session() as db:
        service = DigestService(db)

        # Determine status
        if digest_data.get("skipped"):
            status = "skipped"
            error_message = digest_data.get("reason")
        elif send_result.get("sent"):
            status = "sent"
            error_message = None
        else:
            status = "failed"
            error_message = send_result.get("error") or send_result.get("reason")

        # Build content summary
        content_summary = {}
        if not digest_data.get("skipped"):
            content_summary = {
                "top_campaigns": [c["campaign_name"] for c in digest_data.get("top_campaigns", [])],
                "content_count": len(digest_data.get("content_samples", [])),
            }

        await service.log_digest_sent(
            client_id=UUID(client_id),
            digest_date=digest_date,
            recipients=recipients,
            metrics_snapshot=digest_data.get("metrics", {}),
            content_summary=content_summary,
            status=status,
            error_message=error_message,
        )

        log.info(f"Logged digest result for client {client_id}: {status}")


@flow(name="send_client_digest", log_prints=True)
async def send_client_digest_flow(client_id: str, client_name: str, digest_date: date) -> dict:
    """
    Send digest email to a single client.

    Args:
        client_id: Client UUID as string
        client_name: Client name
        digest_date: Date to generate digest for

    Returns:
        Result dict
    """
    log = get_run_logger()
    log.info(f"Processing digest for client {client_name} ({client_id})")

    # Get digest data
    digest_data = await get_digest_data_task(client_id, digest_date)

    # If skipped, log and return
    if digest_data.get("skipped"):
        await log_digest_result_task(
            client_id=client_id,
            digest_date=digest_date,
            recipients=[],
            digest_data=digest_data,
            send_result={"sent": False, "reason": "skipped"},
        )
        return {"client_id": client_id, "status": "skipped", "reason": digest_data.get("reason")}

    # Render HTML
    html_content = await render_digest_html_task(digest_data)

    # Get recipients
    recipients = await get_recipients_task(client_id)

    # Send email
    send_result = await send_digest_email_task(
        client_id=client_id,
        client_name=client_name,
        recipients=recipients,
        html_content=html_content,
        digest_date=digest_date,
    )

    # Log result
    await log_digest_result_task(
        client_id=client_id,
        digest_date=digest_date,
        recipients=recipients,
        digest_data=digest_data,
        send_result=send_result,
    )

    return {
        "client_id": client_id,
        "client_name": client_name,
        "status": "sent" if send_result.get("sent") else "failed",
        "metrics": digest_data.get("metrics"),
        "recipients_count": len(recipients),
        "error": send_result.get("error"),
    }


@flow(name="daily_digest_flow", log_prints=True)
async def daily_digest_flow(
    target_hour: int = 7,
    digest_date: date | None = None,
) -> dict:
    """
    Main daily digest flow - sends digests to all eligible clients.

    Runs daily at configured hour (default 7 AM AEST).
    Sends summary of previous day's activity.

    Args:
        target_hour: Hour to target for digest sends (clients configured for this hour)
        digest_date: Date to generate digest for (defaults to yesterday)

    Returns:
        Summary of all digest sends
    """
    log = get_run_logger()
    run_id = flow_run.id if flow_run else "manual"

    log.info(f"Starting daily digest flow (run_id={run_id})")

    # Default to yesterday's digest
    if digest_date is None:
        digest_date = date.today() - timedelta(days=1)

    log.info(f"Generating digests for date: {digest_date}, target_hour: {target_hour}")

    # Get clients for this hour
    clients = await get_clients_for_digest_task(target_hour=target_hour)

    if not clients:
        log.info("No clients eligible for digest at this hour")
        return {
            "status": "complete",
            "clients_processed": 0,
            "digest_date": digest_date.isoformat(),
        }

    # Process each client
    results = []
    success_count = 0
    failed_count = 0
    skipped_count = 0

    for client in clients:
        try:
            result = await send_client_digest_flow(
                client_id=client["id"],
                client_name=client["name"],
                digest_date=digest_date,
            )
            results.append(result)

            if result["status"] == "sent":
                success_count += 1
            elif result["status"] == "skipped":
                skipped_count += 1
            else:
                failed_count += 1

        except Exception as e:
            log.error(f"Error processing digest for client {client['name']}: {e}")
            results.append(
                {
                    "client_id": client["id"],
                    "client_name": client["name"],
                    "status": "error",
                    "error": str(e),
                }
            )
            failed_count += 1

    log.info(
        f"Daily digest complete: {success_count} sent, "
        f"{skipped_count} skipped, {failed_count} failed"
    )

    return {
        "status": "complete",
        "digest_date": digest_date.isoformat(),
        "clients_processed": len(clients),
        "success_count": success_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "results": results,
    }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Uses Prefect @flow and @task decorators
# [x] Tasks have retries configured
# [x] Session managed via get_db_session context manager
# [x] TEST_MODE support for email redirect
# [x] Digest data aggregation
# [x] HTML rendering
# [x] Email sending via engine
# [x] Result logging to digest_logs table
# [x] Duplicate send prevention
# [x] Error handling and logging
# [x] Main flow processes all eligible clients
