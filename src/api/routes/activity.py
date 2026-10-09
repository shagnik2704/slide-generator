"""Activity API routes and audit log extraction service."""
import time
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response

from src.api.auth import get_current_user, TokenData
from src.activity.tracker import (
    export_activities,
    get_distinct_activity_types,
    get_user_activities,
    get_user_creations,
    get_user_journey,
    query_all_activities,
)

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/me")
async def get_my_activities(current_user: TokenData = Depends(get_current_user)):
    """Return the recent activity log for the authenticated user."""
    user_id = getattr(current_user, "sub", None)
    email = getattr(current_user, "email", None)
    activities = await get_user_activities(user_id=user_id, email=email, limit=50)
    return {"activities": activities}


@router.get("/creations")
async def get_my_creations(current_user: TokenData = Depends(get_current_user)):
    """Return all platform creations (timed scripts, scripts, slides, audio, etc.) for the authenticated user."""
    user_id = getattr(current_user, "sub", None)
    email = getattr(current_user, "email", None)
    creations = await get_user_creations(user_id=user_id, email=email, limit=100)
    return {"creations": creations}


@router.get("/admin/logs")
async def get_all_activities(
    user_id: Optional[str] = Query(None, description="Filter by user UUID"),
    email: Optional[str] = Query(None, description="Filter by user email address"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type (e.g. slide_generation)"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. completed, failed)"),
    search: Optional[str] = Query(None, description="Text search across detail and email"),
    start_date: Optional[str] = Query(None, description="ISO timestamp start filter"),
    end_date: Optional[str] = Query(None, description="ISO timestamp end filter"),
    limit: int = Query(50, ge=1, le=500, description="Page size limit"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Query, search, and extract user activities across all users and features.
    Provides comprehensive filtering and pagination for auditing and diagnostics.
    """
    result = await query_all_activities(
        user_id=user_id,
        email=email,
        activity_type=activity_type,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return result


@router.get("/admin/types")
async def get_activity_types_endpoint(current_user: TokenData = Depends(get_current_user)):
    """Return distinct activity types present in the activity logs for filtering."""
    types = await get_distinct_activity_types()
    return {"activity_types": types}


@router.get("/admin/users/{user_identifier}/journey")
async def get_user_activity_journey(
    user_identifier: str,
    limit: int = Query(200, ge=1, le=1000),
    current_user: TokenData = Depends(get_current_user),
):
    """Return chronological timeline of all activities for a specific user ID or email."""
    journey = await get_user_journey(user_identifier=user_identifier, limit=limit)
    return journey


@router.get("/admin/export")
async def export_activity_logs(
    format: str = Query("csv", pattern="^(csv|json)$", description="Export format: csv or json"),
    user_id: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    max_records: int = Query(5000, ge=1, le=10000),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Extract and download activity audit logs as CSV or JSON file.
    """
    content, media_type = await export_activities(
        user_id=user_id,
        email=email,
        activity_type=activity_type,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date,
        export_format=format,
        max_records=max_records,
    )
    ext = "json" if format.lower() == "json" else "csv"
    filename = f"user_activity_audit_{int(time.time())}.{ext}"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

