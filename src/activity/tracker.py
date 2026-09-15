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


async def get_user_activities(
    *,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retrieve recent activity logs for a user.

    Synthesizes activity events across user_activities, background_jobs (e.g. timed scripts),
    and script_chat_threads so any past creations (even prior to user_activities migration)
    seamlessly appear in the user's chronological activity history.
    """
    if not user_id and not email:
        return []

    clean_user_id: Optional[str] = None
    if user_id:
        try:
            clean_user_id = str(UUID(str(user_id)))
        except (ValueError, TypeError, AttributeError):
            clean_user_id = None

    try:
        from src.script_chat.persistence import get_pool
        pool = get_pool()
        results: list[dict[str, Any]] = []
        logged_job_ids: set[str] = set()
        logged_thread_ids: set[str] = set()

        async with pool.connection() as conn:
            # 1. Fetch recorded entries from user_activities
            async with conn.cursor() as cur:
                if clean_user_id and email:
                    await cur.execute(
                        """
                        SELECT id, user_id, email, activity_type, detail, status, metadata, created_at
                        FROM user_activities
                        WHERE user_id = %s OR email = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (clean_user_id, email, limit),
                    )
                elif clean_user_id:
                    await cur.execute(
                        """
                        SELECT id, user_id, email, activity_type, detail, status, metadata, created_at
                        FROM user_activities
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (clean_user_id, limit),
                    )
                else:
                    await cur.execute(
                        """
                        SELECT id, user_id, email, activity_type, detail, status, metadata, created_at
                        FROM user_activities
                        WHERE email = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (email, limit),
                    )

                rows = await cur.fetchall()
                for row in rows:
                    meta = row[6] or {}
                    if isinstance(meta, dict):
                        if "job_id" in meta:
                            logged_job_ids.add(str(meta["job_id"]))
                        if "thread_id" in meta:
                            logged_thread_ids.add(str(meta["thread_id"]))
                    results.append({
                        "id": row[0],
                        "user_id": str(row[1]) if row[1] else None,
                        "email": row[2],
                        "activity_type": row[3],
                        "detail": row[4],
                        "status": row[5],
                        "metadata": meta,
                        "created_at": row[7].isoformat() if row[7] else None,
                    })

            # 2. Synthesize historical background jobs if not already logged
            if clean_user_id:
                try:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            SELECT id, user_id, original_filename, status, result, created_at
                            FROM background_jobs
                            WHERE user_id = %s
                            ORDER BY created_at DESC
                            LIMIT %s
                            """,
                            (clean_user_id, limit),
                        )
                        job_rows = await cur.fetchall()
                        for jr in job_rows:
                            jid = str(jr[0])
                            if jid not in logged_job_ids:
                                results.append({
                                    "id": f"job_{jid}",
                                    "user_id": str(jr[1]),
                                    "email": email or "",
                                    "activity_type": "timed_script",
                                    "detail": f"Timed script: {jr[2] or 'Audio'}",
                                    "status": jr[3] or "completed",
                                    "metadata": {"job_id": jid, "original_filename": jr[2], "result": jr[4]},
                                    "created_at": jr[5].isoformat() if jr[5] else None,
                                })
                except Exception as e:
                    logger.debug("Failed to synthesize background_jobs in activities: %s", e)

            # 3. Synthesize historical script chat threads if not already logged
            if clean_user_id:
                try:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            SELECT thread_id, user_id, title, foss_name, outline_preview, current_stage, status, created_at
                            FROM script_chat_threads
                            WHERE user_id = %s AND archived_at IS NULL
                            ORDER BY created_at DESC
                            LIMIT %s
                            """,
                            (clean_user_id, limit),
                        )
                        t_rows = await cur.fetchall()
                        for tr in t_rows:
                            tid = str(tr[0])
                            if tid not in logged_thread_ids:
                                label = tr[2] or tr[3] or tr[4] or "Tutorial Script"
                                results.append({
                                    "id": f"thread_{tid}",
                                    "user_id": str(tr[1]),
                                    "email": email or "",
                                    "activity_type": "script_chat",
                                    "detail": f"Script Chat: {label[:60]}",
                                    "status": tr[6] or "completed",
                                    "metadata": {"thread_id": tid, "foss_name": tr[3], "current_stage": tr[5]},
                                    "created_at": tr[7].isoformat() if tr[7] else None,
                                })
                except Exception as e:
                    logger.debug("Failed to synthesize script_chat_threads in activities: %s", e)

        # Sort combined results descending by created_at
        results.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return results[:limit]
    except Exception as exc:
        logger.debug("Failed to get user activities: %s", exc)
        return []


async def get_user_creations(
    *,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Retrieve all platform creations grouped by category for a user."""
    empty_result = {
        "timed_scripts": [],
        "scripts": [],
        "slides": [],
        "audio": [],
        "videos": [],
        "total_count": 0,
    }
    if not user_id and not email:
        return empty_result

    clean_user_id: Optional[str] = None
    if user_id:
        try:
            clean_user_id = str(UUID(str(user_id)))
        except (ValueError, TypeError, AttributeError):
            clean_user_id = None

    try:
        from src.script_chat.persistence import get_pool
        pool = get_pool()

        timed_scripts: list[dict[str, Any]] = []
        scripts: list[dict[str, Any]] = []
        slides: list[dict[str, Any]] = []
        audio: list[dict[str, Any]] = []
        videos: list[dict[str, Any]] = []

        async with pool.connection() as conn:
            # 1. Fetch timed scripts from background_jobs
            if clean_user_id:
                try:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            SELECT id, original_filename, status, progress, current_stage,
                                   result, error_message, created_at, started_at, completed_at
                            FROM background_jobs
                            WHERE user_id = %s AND job_type = 'timed_script'
                            ORDER BY created_at DESC
                            LIMIT %s
                            """,
                            (clean_user_id, limit),
                        )
                        rows = await cur.fetchall()
                        for r in rows:
                            timed_scripts.append({
                                "id": str(r[0]),
                                "job_id": str(r[0]),
                                "original_filename": r[1],
                                "status": r[2],
                                "progress": r[3] or 0,
                                "current_stage": r[4],
                                "result": r[5],
                                "error_message": r[6],
                                "created_at": r[7].isoformat() if r[7] else None,
                                "completed_at": r[9].isoformat() if r[9] else None,
                            })
                except Exception as e:
                    logger.debug("Failed to query background_jobs in get_user_creations: %s", e)

            # 2. Fetch script chat threads
            if clean_user_id:
                try:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            SELECT thread_id, title, outline_preview, foss_name, current_stage,
                                   status, created_at, updated_at
                            FROM script_chat_threads
                            WHERE user_id = %s AND archived_at IS NULL
                            ORDER BY updated_at DESC
                            LIMIT %s
                            """,
                            (clean_user_id, limit),
                        )
                        rows = await cur.fetchall()
                        for r in rows:
                            scripts.append({
                                "id": str(r[0]),
                                "thread_id": str(r[0]),
                                "title": r[1],
                                "outline_preview": r[2],
                                "foss_name": r[3],
                                "current_stage": r[4],
                                "status": r[5],
                                "created_at": r[6].isoformat() if r[6] else None,
                                "updated_at": r[7].isoformat() if r[7] else None,
                            })
                except Exception as e:
                    logger.debug("Failed to query script_chat_threads in get_user_creations: %s", e)

            # 3. Fetch creation activities (slides, audio, video) from user_activities
            try:
                async with conn.cursor() as cur:
                    where_clause = "WHERE user_id = %s OR email = %s" if (clean_user_id and email) else ("WHERE user_id = %s" if clean_user_id else "WHERE email = %s")
                    params = (clean_user_id, email, limit * 2) if (clean_user_id and email) else ((clean_user_id, limit * 2) if clean_user_id else (email, limit * 2))
                    await cur.execute(
                        f"""
                        SELECT id, activity_type, detail, status, metadata, created_at
                        FROM user_activities
                        {where_clause}
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        params,
                    )
                    rows = await cur.fetchall()
                    for r in rows:
                        act_type = r[1]
                        meta = r[4] or {}
                        item = {
                            "id": r[0],
                            "activity_type": act_type,
                            "detail": r[2],
                            "status": r[3],
                            "metadata": meta,
                            "created_at": r[5].isoformat() if r[5] else None,
                        }
                        if act_type in ("slide_generation", "slides_generation"):
                            zip_fn = meta.get("zip_filename")
                            if zip_fn and not meta.get("zip_url"):
                                item["zip_url"] = f"/output/slides/{zip_fn}"
                            else:
                                item["zip_url"] = meta.get("zip_url")
                            slides.append(item)
                        elif act_type in ("voice_generation", "voice_generation_combined", "voice_patch", "regenerate_slide"):
                            item["audio_url"] = meta.get("audio_url")
                            audio.append(item)
                        elif act_type == "generate_video":
                            item["video_url"] = meta.get("video_url")
                            videos.append(item)
            except Exception as e:
                logger.debug("Failed to query user_activities in get_user_creations: %s", e)

        total_count = len(timed_scripts) + len(scripts) + len(slides) + len(audio) + len(videos)
        return {
            "timed_scripts": timed_scripts,
            "scripts": scripts,
            "slides": slides,
            "audio": audio,
            "videos": videos,
            "total_count": total_count,
        }
    except Exception as exc:
        logger.debug("Failed to get user creations: %s", exc)
        return empty_result
