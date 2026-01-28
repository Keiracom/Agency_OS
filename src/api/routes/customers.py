"""
FILE: src/api/routes/customers.py
TASK: CUST-013, CUST-014, CUST-015
PHASE: 24F - Customer Import
PURPOSE: API endpoints for customer import and suppression management
LAYER: 4 - api
IMPORTS: services
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_from_token, get_db_session
from src.services import (
    BuyerSignalService,
    ColumnMapping,
    CustomerImportService,
    SuppressionService,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/customers", tags=["customers"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class CRMImportRequest(BaseModel):
    """Request to import customers from CRM."""

    crm_type: str = Field(..., description="CRM type: hubspot, pipedrive, or close")
    api_key: str | None = Field(
        None, description="API key for the CRM (not needed for HubSpot OAuth)"
    )
    days_back: int = Field(365, description="Import closed-won deals from last N days")


class CSVImportRequest(BaseModel):
    """Request schema for CSV import form data."""

    domain_column: str = Field("domain", description="Column name for domain")
    email_column: str | None = Field(None, description="Column name for email")
    company_name_column: str | None = Field(None, description="Column name for company")
    source: str = Field("csv_import", description="Import source label")


class SuppressionAddRequest(BaseModel):
    """Request to add to suppression list."""

    domain: str | None = Field(None, description="Domain to suppress")
    email: str | None = Field(None, description="Email to suppress")
    company_name: str | None = Field(None, description="Company name")
    reason: str = Field("manual", description="Reason: existing_customer, competitor, manual, etc.")
    notes: str | None = Field(None, description="Additional notes")


class SuppressionCheckRequest(BaseModel):
    """Request to check suppression status."""

    email: str | None = Field(None, description="Email to check")
    domain: str | None = Field(None, description="Domain to check")


class CustomerResponse(BaseModel):
    """Customer response model."""

    id: UUID
    company_name: str | None
    domain: str | None
    contact_email: str | None
    deal_value: float | None
    closed_at: str | None
    source: str
    auto_suppressed: bool


class SuppressionResponse(BaseModel):
    """Suppression entry response model."""

    id: UUID
    domain: str | None
    email: str | None
    company_name: str | None
    reason: str
    source: str
    notes: str | None
    expires_at: str | None
    created_at: str


class ImportResultResponse(BaseModel):
    """Import result response."""

    success: bool
    imported: int
    skipped: int
    failed: int
    errors: list[str]


class SuppressionCheckResponse(BaseModel):
    """Suppression check response."""

    suppressed: bool
    reason: str | None = None
    details: str | None = None


# ============================================================================
# CUSTOMER IMPORT ENDPOINTS
# ============================================================================


@router.post("/import/crm", response_model=ImportResultResponse)
async def import_from_crm(
    request: CRMImportRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Import customers from CRM (closed-won deals).

    Supported CRMs:
    - hubspot: Uses OAuth (configured at account level)
    - pipedrive: Requires API key
    - close: Requires API key

    Imported customers are automatically added to suppression list.
    """
    client_id = UUID(current_user["client_id"])

    service = CustomerImportService(db)

    try:
        result = await service.import_from_crm(
            client_id=client_id,
            crm_type=request.crm_type,
            api_key=request.api_key,
            days_back=request.days_back,
        )

        return ImportResultResponse(
            success=result.success,
            imported=result.imported,
            skipped=result.skipped,
            failed=result.failed,
            errors=result.errors,
        )

    except Exception as e:
        logger.error(f"CRM import failed: {e}")
        raise HTTPException(status_code=500, detail=f"CRM import failed: {str(e)}")


@router.post("/import/csv", response_model=ImportResultResponse)
async def import_from_csv(
    file: UploadFile = File(...),
    domain_column: str = Form("domain"),
    email_column: str | None = Form(None),
    company_name_column: str | None = Form(None),
    source: str = Form("csv_import"),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Import customers from CSV file.

    The CSV should have at least a domain column. Optional columns:
    - email: Contact email
    - company_name: Company name

    All imported customers are automatically added to suppression list.
    """
    client_id = UUID(current_user["client_id"])

    # Read CSV content
    content = await file.read()
    try:
        csv_content = content.decode("utf-8")
    except UnicodeDecodeError:
        csv_content = content.decode("latin-1")

    # Build column mapping
    column_mapping = ColumnMapping(
        domain=domain_column,
        email=email_column,
        company_name=company_name_column,
    )

    service = CustomerImportService(db)

    try:
        result = await service.import_from_csv(
            client_id=client_id,
            csv_content=csv_content,
            column_mapping=column_mapping,
            source=source,
        )

        return ImportResultResponse(
            success=result.success,
            imported=result.imported,
            skipped=result.skipped,
            failed=result.failed,
            errors=result.errors,
        )

    except Exception as e:
        logger.error(f"CSV import failed: {e}")
        raise HTTPException(status_code=500, detail=f"CSV import failed: {str(e)}")


@router.get("", response_model=list[CustomerResponse])
async def list_customers(
    source: str | None = Query(None, description="Filter by import source"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """List imported customers for the client."""
    client_id = UUID(current_user["client_id"])

    service = CustomerImportService(db)
    customers = await service.list_customers(
        client_id=client_id,
        source=source,
        limit=limit,
        offset=offset,
    )

    return [
        CustomerResponse(
            id=c.id,
            company_name=c.company_name,
            domain=c.domain,
            contact_email=c.contact_email,
            deal_value=c.deal_value,
            closed_at=c.closed_at.isoformat() if c.closed_at else None,
            source=c.source,
            auto_suppressed=c.auto_suppressed,
        )
        for c in customers
    ]


@router.get("/count")
async def get_customer_count(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """Get count of imported customers."""
    client_id = UUID(current_user["client_id"])

    service = CustomerImportService(db)
    count = await service.get_customer_count(client_id)

    return {"count": count}


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """Get a specific customer by ID."""
    client_id = UUID(current_user["client_id"])

    service = CustomerImportService(db)
    customer = await service.get_customer(client_id, customer_id)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return CustomerResponse(
        id=customer.id,
        company_name=customer.company_name,
        domain=customer.domain,
        contact_email=customer.contact_email,
        deal_value=customer.deal_value,
        closed_at=customer.closed_at.isoformat() if customer.closed_at else None,
        source=customer.source,
        auto_suppressed=customer.auto_suppressed,
    )


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: UUID,
    remove_suppression: bool = Query(False, description="Also remove from suppression list"),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Delete a customer record.

    Optionally removes the associated suppression entry.
    """
    client_id = UUID(current_user["client_id"])

    service = CustomerImportService(db)
    deleted = await service.delete_customer(
        client_id=client_id,
        customer_id=customer_id,
        remove_suppression=remove_suppression,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {"deleted": True}


# ============================================================================
# SUPPRESSION ENDPOINTS
# ============================================================================


@router.post("/suppression", response_model=SuppressionResponse)
async def add_suppression(
    request: SuppressionAddRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Add entry to suppression list.

    Suppressed domains/emails will not be contacted by any outreach.
    """
    client_id = UUID(current_user["client_id"])

    if not request.domain and not request.email:
        raise HTTPException(status_code=400, detail="Must provide either domain or email")

    service = SuppressionService(db)

    try:
        await service.add_suppression(
            client_id=client_id,
            domain=request.domain,
            email=request.email,
            company_name=request.company_name,
            reason=request.reason,
            source="manual",
            notes=request.notes,
        )

        # Return the created entry
        entries = await service.list_suppressions(client_id, limit=1)
        entry = entries[0] if entries else None

        if entry:
            return SuppressionResponse(
                id=entry.id,
                domain=entry.domain,
                email=entry.email,
                company_name=entry.company_name,
                reason=entry.reason,
                source=entry.source,
                notes=entry.notes,
                expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
                created_at=entry.created_at.isoformat(),
            )

        raise HTTPException(status_code=500, detail="Failed to create suppression entry")

    except Exception as e:
        logger.error(f"Failed to add suppression: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suppression", response_model=list[SuppressionResponse])
async def list_suppressions(
    reason: str | None = Query(None, description="Filter by reason"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """List suppression entries for the client."""
    client_id = UUID(current_user["client_id"])

    service = SuppressionService(db)
    entries = await service.list_suppressions(
        client_id=client_id,
        reason=reason,
        limit=limit,
        offset=offset,
    )

    return [
        SuppressionResponse(
            id=e.id,
            domain=e.domain,
            email=e.email,
            company_name=e.company_name,
            reason=e.reason,
            source=e.source,
            notes=e.notes,
            expires_at=e.expires_at.isoformat() if e.expires_at else None,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.get("/suppression/count")
async def get_suppression_count(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """Get count of suppression entries."""
    client_id = UUID(current_user["client_id"])

    service = SuppressionService(db)
    count = await service.get_suppression_count(client_id)

    return {"count": count}


@router.post("/suppression/check", response_model=SuppressionCheckResponse)
async def check_suppression(
    request: SuppressionCheckRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Check if an email or domain is suppressed.

    Use this before adding leads to ensure they're not existing customers
    or competitors.
    """
    client_id = UUID(current_user["client_id"])

    if not request.email and not request.domain:
        raise HTTPException(status_code=400, detail="Must provide either email or domain")

    service = SuppressionService(db)
    result = await service.is_suppressed(
        client_id=client_id,
        email=request.email,
        domain=request.domain,
    )

    if result:
        return SuppressionCheckResponse(
            suppressed=True,
            reason=result.reason,
            details=result.details,
        )

    return SuppressionCheckResponse(suppressed=False)


@router.delete("/suppression/{suppression_id}")
async def remove_suppression(
    suppression_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """Remove entry from suppression list."""
    client_id = UUID(current_user["client_id"])

    service = SuppressionService(db)
    removed = await service.remove_suppression(
        client_id=client_id,
        suppression_id=suppression_id,
    )

    if not removed:
        raise HTTPException(status_code=404, detail="Suppression entry not found")

    return {"removed": True}


# ============================================================================
# BUYER SIGNALS ENDPOINTS
# ============================================================================


@router.get("/buyer-signals/check")
async def check_buyer_signal(
    domain: str = Query(..., description="Domain to check"),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Check if a domain is a known buyer on the platform.

    Returns buyer signal data if the company has purchased
    agency services from any client on the platform.
    """
    service = BuyerSignalService(db)
    signal = await service.get_buyer_signal(domain)

    if not signal:
        return {"found": False}

    return {
        "found": True,
        "domain": signal.domain,
        "company_name": signal.company_name,
        "industry": signal.industry,
        "times_bought": signal.times_bought,
        "avg_deal_value": signal.avg_deal_value,
        "buyer_score": signal.buyer_score,
    }


@router.get("/buyer-signals/boost")
async def get_buyer_boost(
    domain: str = Query(..., description="Domain to check"),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Get the score boost for a domain if it's a known buyer.

    Used by the Scorer Engine to add bonus points to leads
    from companies that have bought agency services before.
    """
    service = BuyerSignalService(db)
    boost = await service.get_buyer_score_boost(domain)

    return {
        "boost_points": boost.boost_points,
        "reason": boost.reason,
        "signal": boost.signal.model_dump() if boost.signal else None,
    }


@router.get("/buyer-signals/stats")
async def get_buyer_signal_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """Get aggregate statistics about platform buyer signals."""
    service = BuyerSignalService(db)
    stats = await service.get_platform_stats()

    return stats


@router.get("/buyer-signals/top-industries")
async def get_top_buyer_industries(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_from_token),
):
    """Get industries with highest buyer signal concentration."""
    service = BuyerSignalService(db)
    industries = await service.get_top_industries(limit)

    return {"industries": industries}


# ============================================================================
# VERIFICATION CHECKLIST
# ============================================================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] CRM import endpoint (POST /import/crm)
# [x] CSV import endpoint (POST /import/csv)
# [x] List customers endpoint (GET /)
# [x] Get customer endpoint (GET /{id})
# [x] Delete customer endpoint (DELETE /{id})
# [x] Add suppression endpoint (POST /suppression)
# [x] List suppressions endpoint (GET /suppression)
# [x] Check suppression endpoint (POST /suppression/check)
# [x] Remove suppression endpoint (DELETE /suppression/{id})
# [x] Buyer signal check endpoint (GET /buyer-signals/check)
# [x] Buyer boost endpoint (GET /buyer-signals/boost)
# [x] Buyer stats endpoint (GET /buyer-signals/stats)
# [x] All endpoints use Depends(get_current_user_from_token)
# [x] All endpoints use Depends(get_db_session)
# [x] Pydantic models for request/response
