"""Activity API routes."""
from fastapi import APIRouter, Depends

from src.api.auth import get_current_user, TokenData
from src.activity.tracker import get_user_activities

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/me")
async def get_my_activities(current_user: TokenData = Depends(get_current_user)):
    """Return the recent activity log for the authenticated user."""
    user_id = getattr(current_user, "sub", None)
    email = getattr(current_user, "email", None)
    activities = await get_user_activities(user_id=user_id, email=email, limit=50)
    return {"activities": activities}
