"""
FILE: src/api/routes/onboarding.py
TASK: ICP-013
PHASE: 11 (ICP Discovery System)
PURPOSE: API endpoints for ICP extraction and onboarding flow

DEPENDENCIES:
- src/api/dependencies.py
- src/agents/icp_discovery_agent.py
- src/orchestration/flows/onboarding_flow.py

ENDPOINTS:
- POST /api/v1/onboarding/analyze - Submit website URL for extraction
- GET /api/v1/onboarding/status/{job_id} - Check extraction progress
- GET /api/v1/onboarding/result/{job_id} - Get extracted ICP profile
- POST /api/v1/onboarding/confirm - Confirm/edit ICP
- GET /api/v1/clients/{id}/icp - Get client ICP profile
- PUT /api/v1/clients/{id}/icp - Update client ICP profile
"""

from datetime import datetime
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    ClientContext,
    CurrentUser,
    get_current_client,
    get_current_user_from_token,
    get_db_session,
    require_admin,
    require_member,
)
from src.exceptions import ResourceNotFoundError
from src.models.membership import Membership


router = APIRouter(tags=["onboarding"])


# ============================================
# Pydantic Schemas
# ============================================


class AnalyzeWebsiteRequest(BaseModel):
    """Request to analyze a website for ICP extraction."""

    website_url: str = Field(
        ...,
        min_length=5,
        description="Website URL to analyze (e.g., https://example.com)"
    )


class AnalyzeWebsiteResponse(BaseModel):
    """Response from analyze request."""

    job_id: UUID = Field(description="Extraction job ID")
    status: str = Field(description="Job status: pending, running, completed, failed")
    website_url: str = Field(description="Website being analyzed")
    message: str = Field(description="Status message")


class ExtractionStatus(BaseModel):
    """Current status of an extraction job."""

    job_id: UUID = Field(description="Extraction job ID")
    status: str = Field(description="Job status")
    current_step: Optional[str] = Field(None, description="Current step")
    completed_steps: int = Field(0, description="Completed steps")
    total_steps: int = Field(8, description="Total steps")
    progress_percent: float = Field(0.0, description="Progress percentage")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    error_message: Optional[str] = Field(None, description="Error if failed")


class ICPProfileResponse(BaseModel):
    """ICP profile response."""

    # Agency info
    company_name: str = Field(default="", description="Agency name")
    website_url: str = Field(default="", description="Website URL")
    company_description: str = Field(default="", description="Description")

    # Services
    services_offered: list[str] = Field(default_factory=list)
    primary_service_categories: list[str] = Field(default_factory=list)

    # Value proposition
    value_proposition: str = Field(default="")
    taglines: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)

    # Company info
    team_size: Optional[int] = Field(None)
    size_range: str = Field(default="small")
    years_in_business: Optional[int] = Field(None)

    # Portfolio
    portfolio_companies: list[str] = Field(default_factory=list)
    notable_brands: list[str] = Field(default_factory=list)

    # ICP targeting
    icp_industries: list[str] = Field(default_factory=list)
    icp_company_sizes: list[str] = Field(default_factory=list)
    icp_revenue_ranges: list[str] = Field(default_factory=list)
    icp_locations: list[str] = Field(default_factory=list)
    icp_titles: list[str] = Field(default_factory=list)
    icp_pain_points: list[str] = Field(default_factory=list)
    icp_signals: list[str] = Field(default_factory=list)

    # ALS weights
    als_weights: dict[str, int] = Field(default_factory=dict)

    # Metadata
    pattern_description: str = Field(default="")
    confidence: float = Field(default=0.0)
    extracted_at: Optional[datetime] = Field(None)
    confirmed_at: Optional[datetime] = Field(None)


class ICPUpdateRequest(BaseModel):
    """Request to update ICP profile."""

    # Agency info (optional updates)
    company_description: Optional[str] = Field(None)
    services_offered: Optional[list[str]] = Field(None)
    value_proposition: Optional[str] = Field(None)
    default_offer: Optional[str] = Field(None)

    # ICP targeting
    icp_industries: Optional[list[str]] = Field(None)
    icp_company_sizes: Optional[list[str]] = Field(None)
    icp_revenue_range: Optional[str] = Field(None)
    icp_locations: Optional[list[str]] = Field(None)
    icp_titles: Optional[list[str]] = Field(None)
    icp_pain_points: Optional[list[str]] = Field(None)

    # ALS weights
    als_weights: Optional[dict[str, int]] = Field(None)


class ConfirmICPRequest(BaseModel):
    """Request to confirm extracted ICP."""

    job_id: UUID = Field(description="Extraction job ID to confirm")
    adjustments: Optional[ICPUpdateRequest] = Field(
        None, description="Optional adjustments to apply"
    )


# ============================================
# Routes
# ============================================


@router.post(
    "/onboarding/analyze",
    response_model=AnalyzeWebsiteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_website(
    request: AnalyzeWebsiteRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(get_current_user_from_token)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AnalyzeWebsiteResponse:
    """
    Submit a website URL for ICP extraction.

    This starts an async extraction job that runs in the background.
    Use the returned job_id to check status and get results.

    Note: Uses user-only auth since during onboarding the user may not have
    full client context yet. Looks up the user's client from memberships.
    """
    from uuid import uuid4

    # Look up user's client from memberships (they should be owner)
    result = await db.execute(
        select(Membership.client_id)
        .where(
            and_(
                Membership.user_id == current_user.id,
                Membership.deleted_at.is_(None),
            )
        )
        .limit(1)
    )
    client_id = result.scalar_one_or_none()

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No client found for user. Please complete signup first.",
        )

    # Normalize URL
    url = request.website_url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Create extraction job record
    job_id = uuid4()

    # Import model here to avoid circular imports
    try:
        # Try to insert job record
        await db.execute(
            text("""
            INSERT INTO icp_extraction_jobs
            (id, client_id, status, website_url, created_at)
            VALUES (:id, :client_id, 'pending', :url, :now)
            """),
            {
                "id": str(job_id),
                "client_id": str(client_id),
                "url": url,
                "now": datetime.utcnow(),
            },
        )
        await db.commit()
    except Exception as e:
        # Log error but continue - extraction can still run
        import logging
        logging.error(f"Failed to insert ICP extraction job: {e}")

    # Queue background extraction
    background_tasks.add_task(
        run_extraction_background,
        job_id=job_id,
        client_id=client_id,
        website_url=url,
    )

    return AnalyzeWebsiteResponse(
        job_id=job_id,
        status="pending",
        website_url=url,
        message="ICP extraction started. Check status with job_id.",
    )


async def run_extraction_background(
    job_id: UUID,
    client_id: UUID,
    website_url: str,
) -> None:
    """
    Run ICP extraction in background.

    This is called by background_tasks.add_task().
    """
    from src.agents.icp_discovery_agent import get_icp_discovery_agent
    from src.integrations.supabase import get_db_session as get_db_session_context

    agent = get_icp_discovery_agent()

    try:
        # Update status to running
        async with get_db_session_context() as db:
            await db.execute(
                text("""
                UPDATE icp_extraction_jobs
                SET status = 'running', started_at = :now
                WHERE id = :job_id
                """),
                {"job_id": str(job_id), "now": datetime.utcnow()},
            )
            await db.commit()

        # Run extraction
        result = await agent.extract_icp(website_url)

        # Save result
        async with get_db_session_context() as db:
            if result.success and result.profile:
                # Update job with success
                await db.execute(
                    text("""
                    UPDATE icp_extraction_jobs
                    SET status = 'completed',
                        completed_at = :now,
                        extracted_icp = :icp
                    WHERE id = :job_id
                    """),
                    {
                        "job_id": str(job_id),
                        "now": datetime.utcnow(),
                        "icp": result.profile.model_dump_json(),
                    },
                )
            else:
                # Update job with failure
                await db.execute(
                    text("""
                    UPDATE icp_extraction_jobs
                    SET status = 'failed',
                        completed_at = :now,
                        error_message = :error
                    WHERE id = :job_id
                    """),
                    {
                        "job_id": str(job_id),
                        "now": datetime.utcnow(),
                        "error": result.error or "Unknown error",
                    },
                )
            await db.commit()

    except Exception as e:
        # Handle unexpected errors
        import logging
        logging.error(f"ICP extraction failed for job {job_id}: {e}")
        try:
            async with get_db_session_context() as db:
                await db.execute(
                    text("""
                    UPDATE icp_extraction_jobs
                    SET status = 'failed',
                        completed_at = :now,
                        error_message = :error
                    WHERE id = :job_id
                    """),
                    {
                        "job_id": str(job_id),
                        "now": datetime.utcnow(),
                        "error": str(e),
                    },
                )
                await db.commit()
        except Exception:
            pass


@router.get(
    "/onboarding/status/{job_id}",
    response_model=ExtractionStatus,
)
async def get_extraction_status(
    job_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user_from_token)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ExtractionStatus:
    """
    Get the status of an ICP extraction job.

    Uses user-only auth during onboarding, looks up client from memberships.
    """
    # Look up user's client from memberships
    client_result = await db.execute(
        select(Membership.client_id)
        .where(
            and_(
                Membership.user_id == current_user.id,
                Membership.deleted_at.is_(None),
            )
        )
        .limit(1)
    )
    client_id = client_result.scalar_one_or_none()

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No client found for user.",
        )

    result = await db.execute(
        text("""
        SELECT id, status, current_step, completed_steps, total_steps,
               started_at, completed_at, error_message
        FROM icp_extraction_jobs
        WHERE id = :job_id AND client_id = :client_id
        """),
        {"job_id": str(job_id), "client_id": str(client_id)},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction job not found",
        )

    completed_steps = row.completed_steps or 0
    total_steps = row.total_steps or 8
    progress = (completed_steps / total_steps * 100) if total_steps > 0 else 0

    return ExtractionStatus(
        job_id=row.id,
        status=row.status,
        current_step=row.current_step,
        completed_steps=completed_steps,
        total_steps=total_steps,
        progress_percent=progress,
        started_at=row.started_at,
        completed_at=row.completed_at,
        error_message=row.error_message,
    )


@router.get(
    "/onboarding/result/{job_id}",
    response_model=ICPProfileResponse,
)
async def get_extraction_result(
    job_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user_from_token)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ICPProfileResponse:
    """
    Get the extracted ICP profile from a completed job.

    Uses user-only auth during onboarding, looks up client from memberships.
    """
    import json

    # Look up user's client from memberships
    client_result = await db.execute(
        select(Membership.client_id)
        .where(
            and_(
                Membership.user_id == current_user.id,
                Membership.deleted_at.is_(None),
            )
        )
        .limit(1)
    )
    client_id = client_result.scalar_one_or_none()

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No client found for user.",
        )

    result = await db.execute(
        text("""
        SELECT status, extracted_icp, error_message
        FROM icp_extraction_jobs
        WHERE id = :job_id AND client_id = :client_id
        """),
        {"job_id": str(job_id), "client_id": str(client_id)},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction job not found",
        )

    if row.status == "pending" or row.status == "running":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Extraction still in progress",
        )

    if row.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=row.error_message or "Extraction failed",
        )

    if not row.extracted_icp:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No ICP data available",
        )

    # Parse the stored ICP data
    try:
        if isinstance(row.extracted_icp, str):
            icp_data = json.loads(row.extracted_icp)
        else:
            icp_data = row.extracted_icp
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse ICP data",
        )

    return ICPProfileResponse(**icp_data)


@router.post(
    "/onboarding/confirm",
    status_code=status.HTTP_200_OK,
)
async def confirm_icp(
    request: ConfirmICPRequest,
    client: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """
    Confirm and apply the extracted ICP to the client profile.

    Optionally apply adjustments before saving.
    """
    import json

    # Get the extraction result
    result = await db.execute(
        text("""
        SELECT extracted_icp
        FROM icp_extraction_jobs
        WHERE id = :job_id AND client_id = :client_id AND status = 'completed'
        """),
        {"job_id": str(request.job_id), "client_id": str(client.client_id)},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completed extraction job not found",
        )

    # Parse ICP data
    try:
        if isinstance(row.extracted_icp, str):
            icp_data = json.loads(row.extracted_icp)
        else:
            icp_data = row.extracted_icp
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse ICP data",
        )

    # Apply adjustments if provided
    if request.adjustments:
        adj = request.adjustments.model_dump(exclude_none=True)
        for key, value in adj.items():
            icp_data[key] = value

    # Update client with ICP data
    # Note: For asyncpg with raw text() queries:
    # - TEXT[] fields need native Python lists (asyncpg handles conversion)
    # - JSONB fields need JSON strings with explicit CAST
    update_fields = {
        "website_url": icp_data.get("website_url"),
        "company_description": icp_data.get("company_description") or icp_data.get("value_proposition"),
        "services_offered": icp_data.get("services_offered", []),  # TEXT[]
        "value_proposition": icp_data.get("value_proposition"),
        "team_size": icp_data.get("team_size"),
        "icp_industries": icp_data.get("icp_industries", []),  # TEXT[]
        "icp_company_sizes": icp_data.get("icp_company_sizes", []),  # TEXT[]
        "icp_locations": icp_data.get("icp_locations", []),  # TEXT[]
        "icp_titles": icp_data.get("icp_titles", []),  # TEXT[]
        "icp_pain_points": icp_data.get("icp_pain_points", []),  # TEXT[]
        "als_weights": json.dumps(icp_data.get("als_weights", {})),  # JSONB - needs JSON string
        "icp_extracted_at": datetime.utcnow(),
        "icp_extraction_source": "ai_extraction",
        "icp_confirmed_at": datetime.utcnow(),
        "icp_extraction_job_id": str(request.job_id),
        "updated_at": datetime.utcnow(),
    }

    # Only als_weights is JSONB, needs explicit cast
    jsonb_fields = ["als_weights"]

    # Build SQL update with explicit JSONB casts for asyncpg compatibility
    set_parts = []
    for k in update_fields.keys():
        if k in jsonb_fields:
            set_parts.append(f"{k} = CAST(:{k} AS jsonb)")
        else:
            set_parts.append(f"{k} = :{k}")
    set_clauses = ", ".join(set_parts)

    await db.execute(
        text(f"""
        UPDATE clients
        SET {set_clauses}
        WHERE id = :client_id AND deleted_at IS NULL
        """),
        {"client_id": str(client.client_id), **update_fields},
    )
    await db.commit()

    return {
        "success": True,
        "message": "ICP profile confirmed and saved",
        "client_id": str(client.client_id),
    }


@router.get(
    "/clients/{client_id}/icp",
    response_model=ICPProfileResponse,
)
async def get_client_icp(
    client_id: UUID,
    user_client: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ICPProfileResponse:
    """
    Get the ICP profile for a client.
    """
    # Verify access to this client
    if user_client.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this client",
        )

    result = await db.execute(
        text("""
        SELECT name, website_url, company_description, services_offered,
               value_proposition, team_size, icp_industries, icp_company_sizes,
               icp_locations, icp_titles, icp_pain_points, als_weights,
               icp_extracted_at, icp_confirmed_at
        FROM clients
        WHERE id = :client_id AND deleted_at IS NULL
        """),
        {"client_id": str(client_id)},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    return ICPProfileResponse(
        company_name=row.name or "",
        website_url=row.website_url or "",
        company_description=row.company_description or "",
        services_offered=row.services_offered or [],
        value_proposition=row.value_proposition or "",
        icp_industries=row.icp_industries or [],
        icp_company_sizes=row.icp_company_sizes or [],
        icp_locations=row.icp_locations or [],
        icp_titles=row.icp_titles or [],
        icp_pain_points=row.icp_pain_points or [],
        als_weights=row.als_weights or {},
        extracted_at=row.icp_extracted_at,
        confirmed_at=row.icp_confirmed_at,
    )


@router.put(
    "/clients/{client_id}/icp",
    response_model=ICPProfileResponse,
)
async def update_client_icp(
    client_id: UUID,
    request: ICPUpdateRequest,
    user_client: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _admin: Annotated[bool, Depends(require_admin)],
) -> ICPProfileResponse:
    """
    Update the ICP profile for a client.

    Requires admin role.
    """
    # Verify access to this client
    if user_client.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this client",
        )

    import json as json_module

    # Build update dict from non-None values
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided",
        )

    # JSONB fields need to be serialized for asyncpg
    jsonb_fields = {"services_offered", "icp_industries", "icp_company_sizes",
                    "icp_locations", "icp_titles", "icp_pain_points", "als_weights"}
    for field in jsonb_fields:
        if field in updates and isinstance(updates[field], (list, dict)):
            updates[field] = json_module.dumps(updates[field])

    updates["updated_at"] = datetime.utcnow()

    # Build SQL update
    set_clauses = ", ".join([f"{k} = :{k}" for k in updates.keys()])
    await db.execute(
        text(f"""
        UPDATE clients
        SET {set_clauses}
        WHERE id = :client_id AND deleted_at IS NULL
        """),
        {"client_id": str(client_id), **updates},
    )
    await db.commit()

    # Return updated profile
    return await get_client_icp(client_id, user_client, db)


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] All endpoints documented
- [x] Pydantic schemas for request/response
- [x] Authentication via get_current_client
- [x] Soft delete checks in queries (deleted_at IS NULL)
- [x] Background task for async extraction
- [x] Progress tracking endpoints
- [x] ICP confirm/update endpoints
- [x] Client-scoped access control
- [x] Error handling with appropriate HTTP status codes
- [x] Type hints on all functions
"""
