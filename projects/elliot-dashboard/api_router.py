"""
Elliot Dashboard API Router

FastAPI router for Elliot dashboard endpoints.
Add to Agency OS backend: app.include_router(elliot_router, prefix="/api/elliot")
"""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from supabase import Client

# Assuming these exist in Agency OS backend
from app.core.auth import get_current_admin_user
from app.core.database import get_supabase_client


router = APIRouter(tags=["elliot"])


# =============================================================================
# MODELS
# =============================================================================

class DailyLogBase(BaseModel):
    log_date: date
    accomplishments: List[str] = []
    interactions: List[dict] = []
    issues: List[str] = []
    notes: Optional[str] = None
    raw_content: Optional[str] = None


class DailyLogResponse(DailyLogBase):
    id: UUID
    sync_source: Optional[str]
    synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LearningBase(BaseModel):
    learning_key: str
    category: Optional[str] = None
    title: str
    description: str
    context: Optional[str] = None
    source_type: Optional[str] = None
    impact_level: str = "medium"


class LearningResponse(LearningBase):
    id: UUID
    learned_date: date
    times_applied: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DecisionBase(BaseModel):
    title: str
    context: str
    options: List[dict] = []
    chosen_option: str
    rationale: str
    expected_outcome: Optional[str] = None
    category: Optional[str] = None
    importance: str = "medium"
    stakeholders: List[str] = []


class DecisionCreate(DecisionBase):
    decision_key: Optional[str] = None
    decision_date: Optional[date] = None


class DecisionOutcomeUpdate(BaseModel):
    actual_outcome: str
    outcome_status: str  # 'success', 'partial', 'failure'
    outcome_date: Optional[date] = None
    learning_extracted: Optional[str] = None


class DecisionResponse(DecisionBase):
    id: UUID
    decision_key: str
    decision_date: date
    actual_outcome: Optional[str]
    outcome_date: Optional[date]
    outcome_status: str
    learning_extracted: Optional[str]
    linked_learning_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActivityBase(BaseModel):
    activity_type: str
    channel: Optional[str] = None
    summary: str
    details: Optional[dict] = None
    related_files: List[str] = []
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None
    token_usage: Optional[dict] = None
    status: str = "completed"
    error_message: Optional[str] = None


class ActivityResponse(ActivityBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SyncTriggerRequest(BaseModel):
    direction: str = "file_to_db"  # 'file_to_db', 'db_to_file', 'bidirectional'
    file_types: List[str] = []  # empty = all


class ServiceHealthResponse(BaseModel):
    service_name: str
    status: str
    last_check_at: Optional[datetime]
    response_time_ms: Optional[int]
    details: Optional[dict]
    error_message: Optional[str]


# =============================================================================
# MEMORY ENDPOINTS
# =============================================================================

@router.get("/memory/daily", response_model=dict)
async def list_daily_logs(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(30, le=100),
    offset: int = 0,
    search: Optional[str] = None,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """List daily memory logs with optional filters."""
    query = db.table("elliot_daily_logs").select("*", count="exact")
    
    if start_date:
        query = query.gte("log_date", start_date.isoformat())
    if end_date:
        query = query.lte("log_date", end_date.isoformat())
    if search:
        # Full-text search in accomplishments and notes
        query = query.or_(f"notes.ilike.%{search}%,raw_content.ilike.%{search}%")
    
    result = query.order("log_date", desc=True).range(offset, offset + limit - 1).execute()
    
    return {
        "data": result.data,
        "total": result.count,
        "hasMore": result.count > offset + limit,
    }


@router.get("/memory/daily/{log_date}", response_model=DailyLogResponse)
async def get_daily_log(
    log_date: date,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Get a specific daily log by date."""
    result = db.table("elliot_daily_logs").select("*").eq("log_date", log_date.isoformat()).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Daily log not found")
    
    return result.data[0]


@router.post("/memory/daily", response_model=DailyLogResponse)
async def upsert_daily_log(
    log: DailyLogBase,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Create or update a daily log."""
    data = log.model_dump()
    data["log_date"] = data["log_date"].isoformat()
    data["sync_source"] = "dashboard"  # Mark as dashboard edit
    data["synced_at"] = datetime.utcnow().isoformat()
    
    result = db.table("elliot_daily_logs").upsert(data, on_conflict="log_date").execute()
    
    return result.data[0]


@router.get("/memory/weekly", response_model=dict)
async def list_weekly_rollups(
    year: Optional[int] = None,
    limit: int = Query(12, le=52),
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """List weekly rollups."""
    query = db.table("elliot_weekly_rollups").select("*")
    
    if year:
        query = query.like("year_week", f"{year}-W%")
    
    result = query.order("week_start", desc=True).limit(limit).execute()
    
    return {"data": result.data}


@router.get("/memory/patterns", response_model=List[dict])
async def get_patterns(
    category: Optional[str] = None,
    status: str = "active",
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Get all patterns."""
    query = db.table("elliot_patterns").select("*").eq("status", status)
    
    if category:
        query = query.eq("category", category)
    
    result = query.order("occurrence_count", desc=True).execute()
    
    return result.data


# =============================================================================
# KNOWLEDGE ENDPOINTS
# =============================================================================

@router.get("/knowledge/rules", response_model=List[dict])
async def get_rules(
    category: Optional[str] = None,
    active_only: bool = True,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Get all operating rules."""
    query = db.table("elliot_rules").select("*")
    
    if active_only:
        query = query.eq("is_active", True)
    if category:
        query = query.eq("category", category)
    
    result = query.order("sort_order").execute()
    
    return result.data


@router.get("/knowledge/learnings", response_model=dict)
async def list_learnings(
    category: Optional[str] = None,
    impact_level: Optional[str] = None,
    limit: int = Query(50, le=200),
    search: Optional[str] = None,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """List all learnings."""
    query = db.table("elliot_learnings").select("*", count="exact")
    
    if category:
        query = query.eq("category", category)
    if impact_level:
        query = query.eq("impact_level", impact_level)
    if search:
        query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")
    
    result = query.order("learned_date", desc=True).limit(limit).execute()
    
    return {"data": result.data, "total": result.count}


@router.post("/knowledge/learnings", response_model=LearningResponse)
async def create_learning(
    learning: LearningBase,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Add a new learning."""
    data = learning.model_dump()
    data["learned_date"] = date.today().isoformat()
    
    result = db.table("elliot_learnings").insert(data).execute()
    
    return result.data[0]


@router.get("/knowledge/decisions", response_model=dict)
async def list_decisions(
    outcome_status: Optional[str] = None,
    category: Optional[str] = None,
    importance: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, le=200),
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """List decisions with filters."""
    query = db.table("elliot_decisions").select("*", count="exact")
    
    if outcome_status:
        query = query.eq("outcome_status", outcome_status)
    if category:
        query = query.eq("category", category)
    if importance:
        query = query.eq("importance", importance)
    if start_date:
        query = query.gte("decision_date", start_date.isoformat())
    if end_date:
        query = query.lte("decision_date", end_date.isoformat())
    
    result = query.order("decision_date", desc=True).limit(limit).execute()
    
    # Calculate stats
    all_decisions = db.table("elliot_decisions").select("outcome_status").execute()
    stats = {
        "total": len(all_decisions.data),
        "pending": sum(1 for d in all_decisions.data if d["outcome_status"] == "pending"),
        "success": sum(1 for d in all_decisions.data if d["outcome_status"] == "success"),
        "failure": sum(1 for d in all_decisions.data if d["outcome_status"] == "failure"),
    }
    
    return {"data": result.data, "stats": stats}


@router.post("/knowledge/decisions", response_model=DecisionResponse)
async def create_decision(
    decision: DecisionCreate,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Log a new decision."""
    data = decision.model_dump()
    
    # Generate key if not provided
    if not data.get("decision_key"):
        import re
        key = re.sub(r'[^a-z0-9]+', '_', data["title"].lower())[:100]
        data["decision_key"] = key
    
    if not data.get("decision_date"):
        data["decision_date"] = date.today().isoformat()
    else:
        data["decision_date"] = data["decision_date"].isoformat()
    
    data["outcome_status"] = "pending"
    
    result = db.table("elliot_decisions").insert(data).execute()
    
    return result.data[0]


@router.get("/knowledge/decisions/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: UUID,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Get a specific decision."""
    result = db.table("elliot_decisions").select("*").eq("id", str(decision_id)).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    return result.data[0]


@router.patch("/knowledge/decisions/{decision_id}", response_model=DecisionResponse)
async def update_decision_outcome(
    decision_id: UUID,
    update: DecisionOutcomeUpdate,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Update a decision's outcome."""
    data = update.model_dump(exclude_unset=True)
    
    if "outcome_date" in data and data["outcome_date"]:
        data["outcome_date"] = data["outcome_date"].isoformat()
    elif "outcome_date" not in data:
        data["outcome_date"] = date.today().isoformat()
    
    result = db.table("elliot_decisions").update(data).eq("id", str(decision_id)).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    return result.data[0]


# =============================================================================
# ACTIVITY ENDPOINTS
# =============================================================================

@router.get("/activity", response_model=dict)
async def get_activity(
    activity_type: Optional[str] = None,
    channel: Optional[str] = None,
    session_id: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = Query(100, le=500),
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Get activity stream."""
    query = db.table("elliot_activity").select("*")
    
    if activity_type:
        query = query.eq("activity_type", activity_type)
    if channel:
        query = query.eq("channel", channel)
    if session_id:
        query = query.eq("session_id", session_id)
    if since:
        query = query.gt("created_at", since.isoformat())
    
    result = query.order("created_at", desc=True).limit(limit).execute()
    
    latest = result.data[0]["created_at"] if result.data else None
    
    return {"data": result.data, "latestTimestamp": latest}


@router.post("/activity", response_model=ActivityResponse, include_in_schema=False)
async def log_activity(
    activity: ActivityBase,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Log an activity (internal use by sync service)."""
    result = db.table("elliot_activity").insert(activity.model_dump()).execute()
    
    return result.data[0]


@router.get("/activity/stats", response_model=dict)
async def get_activity_stats(
    start_date: date,
    end_date: date,
    granularity: str = "daily",
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Get aggregated activity statistics."""
    query = db.table("elliot_activity_stats") \
        .select("*") \
        .gte("stat_date", start_date.isoformat()) \
        .lte("stat_date", end_date.isoformat())
    
    if granularity == "daily":
        query = query.is_("stat_hour", None)
    
    result = query.order("stat_date").execute()
    
    # Calculate summary
    total_activities = sum(r.get("total_activities", 0) for r in result.data)
    total_tokens = sum(r.get("total_input_tokens", 0) + r.get("total_output_tokens", 0) for r in result.data)
    
    channels = set()
    for r in result.data:
        if r.get("channel_breakdown"):
            channels.update(r["channel_breakdown"].keys())
    
    return {
        "summary": {
            "totalActivities": total_activities,
            "totalTokens": total_tokens,
            "activeChannels": list(channels),
        },
        "timeSeries": result.data,
    }


# =============================================================================
# SYNC ENDPOINTS
# =============================================================================

@router.post("/sync/trigger", response_model=dict)
async def trigger_sync(
    request: SyncTriggerRequest,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Trigger a manual sync operation."""
    # In production, this would trigger a Prefect flow
    # For now, we'll queue it via Redis
    import redis
    import json
    import os
    from uuid import uuid4
    
    sync_id = str(uuid4())
    
    try:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            r = redis.from_url(redis_url)
            r.rpush("sync:manual", json.dumps({
                "sync_id": sync_id,
                "direction": request.direction,
                "file_types": request.file_types,
                "requested_at": datetime.utcnow().isoformat(),
            }))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue sync: {str(e)}")
    
    return {
        "sync_id": sync_id,
        "status": "queued",
        "message": f"Sync {request.direction} queued",
    }


@router.get("/sync/status", response_model=dict)
async def get_sync_status(
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Get current sync status."""
    result = db.table("elliot_sync_state").select("*").order("last_sync_at", desc=True).execute()
    
    # Check for conflicts
    conflicts = [f for f in result.data if f.get("sync_status") == "conflict"]
    errors = [f for f in result.data if f.get("sync_status") == "error"]
    
    # Determine overall status
    if errors:
        overall = "error"
    elif conflicts:
        overall = "conflict"
    elif any(f.get("sync_status") == "pending" for f in result.data):
        overall = "pending"
    else:
        overall = "synced"
    
    last_sync = result.data[0]["last_sync_at"] if result.data else None
    
    return {
        "overall_status": overall,
        "last_sync_at": last_sync,
        "files": result.data,
        "conflicts": conflicts,
    }


# =============================================================================
# HEALTH ENDPOINTS
# =============================================================================

@router.get("/health/services", response_model=dict)
async def get_all_service_health(
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Get health status of all services."""
    result = db.table("service_health").select("*").execute()
    
    # Determine overall health
    statuses = [s["status"] for s in result.data]
    if "down" in statuses:
        overall = "down"
    elif "degraded" in statuses:
        overall = "degraded"
    elif all(s == "healthy" for s in statuses):
        overall = "healthy"
    else:
        overall = "unknown"
    
    return {
        "overall": overall,
        "services": result.data,
        "checked_at": datetime.utcnow().isoformat(),
    }


@router.get("/health/services/{service_name}", response_model=dict)
async def get_service_health(
    service_name: str,
    include_history: bool = False,
    history_hours: int = 24,
    db: Client = Depends(get_supabase_client),
    _: dict = Depends(get_current_admin_user),
):
    """Get health status of a specific service."""
    result = db.table("service_health").select("*").eq("service_name", service_name).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Service not found")
    
    response = result.data[0]
    
    if include_history:
        history_since = datetime.utcnow() - timedelta(hours=history_hours)
        history = db.table("service_health_history") \
            .select("status,response_time_ms,checked_at") \
            .eq("service_id", response["id"]) \
            .gte("checked_at", history_since.isoformat()) \
            .order("checked_at", desc=True) \
            .execute()
        
        response["history"] = history.data
    
    return response


# =============================================================================
# EXPORT ROUTER
# =============================================================================

elliot_router = router
