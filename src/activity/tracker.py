"""Fail-safe, non-blocking user activity logging service."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional
from uuid import UUID

from psycopg.types.json import Jsonb

logger = logging.getLogger(__name__)


async def record_activity(
    *,
    user: Any = None,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    activity_type: str,
    detail: Optional[str] = None,
    status: str = "completed",
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Persist an activity event to PostgreSQL.

    Guaranteed fail-safe: this function NEVER raises exceptions under any
    circumstance (DB down, pool uninitialized, table missing, invalid UUID).
    Activity tracking failures are silently logged at DEBUG level so they
    never impact the primary user workflow.
    """
    try:
        from src.script_chat.persistence import get_pool

        # Resolve user_id and email from user object if provided
        effective_user_id = user_id or (getattr(user, "sub", None) or getattr(user, "id", None) if user else None)
        effective_email = email or (getattr(user, "email", None) if user else None)

        # Sanitize user_id: only pass valid UUID, otherwise None
        clean_user_id: Optional[str] = None
        if effective_user_id:
            try:
                clean_user_id = str(UUID(str(effective_user_id)))
            except (ValueError, TypeError, AttributeError):
                clean_user_id = None

        clean_email = (effective_email or "anonymous@edupyramids.org").strip()
        clean_detail = str(detail)[:255] if detail else None
        clean_status = str(status)[:32] if status else "completed"
        clean_metadata = Jsonb(metadata or {})

        pool = get_pool()
        async with pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO user_activities
                    (user_id, email, activity_type, detail, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (clean_user_id, clean_email, activity_type, clean_detail, clean_status, clean_metadata),
            )
    except Exception as exc:
        logger.debug("Failed to record activity log (%s): %s", activity_type, exc)


def log_activity(
    *,
    user: Any = None,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    activity_type: str,
    detail: Optional[str] = None,
    status: str = "completed",
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Fire-and-forget background task scheduler for record_activity.

    Allows route handlers to log user actions asynchronously without
    awaiting or adding latency to client responses.
    """
    try:
        effective_user_id = user_id or (getattr(user, "sub", None) or getattr(user, "id", None) if user else None)
        effective_email = email or (getattr(user, "email", None) if user else None)

        loop = asyncio.get_running_loop()
        loop.create_task(
            record_activity(
                user_id=effective_user_id,
                email=effective_email,
                activity_type=activity_type,
                detail=detail,
                status=status,
                metadata=metadata,
            )
        )
    except Exception as exc:
        logger.debug("Failed to schedule activity task (%s): %s", activity_type, exc)
