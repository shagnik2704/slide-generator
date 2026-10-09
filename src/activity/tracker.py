"""Fail-safe, non-blocking user activity logging service."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from psycopg.types.json import Jsonb

logger = logging.getLogger(__name__)


def extract_client_context(request: Any = None) -> dict[str, str]:
    """Safely extract client IP and user agent from FastAPI Request if available."""
    if not request:
        return {}
    context: dict[str, str] = {}
    try:
        # Check X-Forwarded-For (comma-separated, first entry is client IP)
        forwarded = getattr(request, "headers", {}).get("x-forwarded-for")
        if forwarded:
            context["ip_address"] = str(forwarded).split(",")[0].strip()
        elif getattr(request, "headers", {}).get("x-real-ip"):
            context["ip_address"] = str(request.headers.get("x-real-ip")).strip()
        elif getattr(request, "client", None) and getattr(request.client, "host", None):
            context["ip_address"] = str(request.client.host).strip()

        ua = getattr(request, "headers", {}).get("user-agent")
        if ua:
            context["user_agent"] = str(ua)[:255]
    except Exception:
        pass
    return context


async def record_activity(
    *,
    user: Any = None,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    activity_type: str,
    detail: Optional[str] = None,
    status: str = "completed",
    metadata: Optional[dict[str, Any]] = None,
    request: Any = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
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

        # Merge client context (IP, user agent) into metadata
        meta_dict = dict(metadata or {})
        client_ctx = extract_client_context(request)
        if ip_address:
            meta_dict["ip_address"] = str(ip_address)
        elif "ip_address" in client_ctx:
            meta_dict["ip_address"] = client_ctx["ip_address"]

        if user_agent:
            meta_dict["user_agent"] = str(user_agent)[:255]
        elif "user_agent" in client_ctx:
            meta_dict["user_agent"] = client_ctx["user_agent"]

        clean_metadata = Jsonb(meta_dict)

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
    request: Any = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """
    Fire-and-forget background task scheduler for record_activity.

    Allows route handlers to log user actions asynchronously without
    awaiting or adding latency to client responses.
    """
    try:
        effective_user_id = user_id or (getattr(user, "sub", None) or getattr(user, "id", None) if user else None)
        effective_email = email or (getattr(user, "email", None) if user else None)

        # Pre-extract client context on the request thread before passing to async task
        client_ctx = extract_client_context(request)
        meta_dict = dict(metadata or {})
        if ip_address:
            meta_dict["ip_address"] = str(ip_address)
        elif "ip_address" in client_ctx:
            meta_dict["ip_address"] = client_ctx["ip_address"]

        if user_agent:
            meta_dict["user_agent"] = str(user_agent)[:255]
        elif "user_agent" in client_ctx:
            meta_dict["user_agent"] = client_ctx["user_agent"]

        loop = asyncio.get_running_loop()
        loop.create_task(
            record_activity(
                user_id=effective_user_id,
                email=effective_email,
                activity_type=activity_type,
                detail=detail,
                status=status,
                metadata=meta_dict,
            )
        )
    except Exception as exc:
        logger.debug("Failed to schedule activity task (%s): %s", activity_type, exc)


def _val(row: Any, key: str, index: int, default: Any = None) -> Any:
    """Safely extract a value from a row whether it is a dict (psycopg dict_row) or a tuple/list."""
    if isinstance(row, dict):
        return row.get(key, default)
    if isinstance(row, (tuple, list)):
        return row[index] if 0 <= index < len(row) else default
    if hasattr(row, key):
        return getattr(row, key, default)
    return default


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
                    meta = _val(row, "metadata", 6) or {}
                    if isinstance(meta, dict):
                        if "job_id" in meta:
                            logged_job_ids.add(str(meta["job_id"]))
                        if "thread_id" in meta:
                            logged_thread_ids.add(str(meta["thread_id"]))
                    c_at = _val(row, "created_at", 7)
                    uid = _val(row, "user_id", 1)
                    results.append({
                        "id": _val(row, "id", 0),
                        "user_id": str(uid) if uid else None,
                        "email": _val(row, "email", 2),
                        "activity_type": _val(row, "activity_type", 3),
                        "detail": _val(row, "detail", 4),
                        "status": _val(row, "status", 5),
                        "metadata": meta,
                        "created_at": c_at.isoformat() if hasattr(c_at, "isoformat") else (str(c_at) if c_at else None),
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
                            jid = str(_val(jr, "id", 0))
                            if jid not in logged_job_ids:
                                orig_fn = _val(jr, "original_filename", 2)
                                c_at = _val(jr, "created_at", 5)
                                results.append({
                                    "id": f"job_{jid}",
                                    "user_id": str(_val(jr, "user_id", 1)),
                                    "email": email or "",
                                    "activity_type": "timed_script",
                                    "detail": f"Timed script: {orig_fn or 'Audio'}",
                                    "status": _val(jr, "status", 3) or "completed",
                                    "metadata": {
                                        "job_id": jid,
                                        "original_filename": orig_fn,
                                        "result": _val(jr, "result", 4),
                                    },
                                    "created_at": c_at.isoformat() if hasattr(c_at, "isoformat") else (str(c_at) if c_at else None),
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
                            tid = str(_val(tr, "thread_id", 0))
                            if tid not in logged_thread_ids:
                                title = _val(tr, "title", 2)
                                foss = _val(tr, "foss_name", 3)
                                preview = _val(tr, "outline_preview", 4)
                                label = title or foss or preview or "Tutorial Script"
                                c_at = _val(tr, "created_at", 7)
                                results.append({
                                    "id": f"thread_{tid}",
                                    "user_id": str(_val(tr, "user_id", 1)),
                                    "email": email or "",
                                    "activity_type": "script_chat",
                                    "detail": f"Script Chat: {label[:60]}",
                                    "status": _val(tr, "status", 6) or "completed",
                                    "metadata": {
                                        "thread_id": tid,
                                        "foss_name": foss,
                                        "current_stage": _val(tr, "current_stage", 5),
                                    },
                                    "created_at": c_at.isoformat() if hasattr(c_at, "isoformat") else (str(c_at) if c_at else None),
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
                            c_at = _val(r, "created_at", 7)
                            comp_at = _val(r, "completed_at", 9)
                            jid = str(_val(r, "id", 0))
                            timed_scripts.append({
                                "id": jid,
                                "job_id": jid,
                                "original_filename": _val(r, "original_filename", 1),
                                "status": _val(r, "status", 2),
                                "progress": _val(r, "progress", 3) or 0,
                                "current_stage": _val(r, "current_stage", 4),
                                "result": _val(r, "result", 5),
                                "error_message": _val(r, "error_message", 6),
                                "created_at": c_at.isoformat() if hasattr(c_at, "isoformat") else (str(c_at) if c_at else None),
                                "completed_at": comp_at.isoformat() if hasattr(comp_at, "isoformat") else (str(comp_at) if comp_at else None),
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
                            c_at = _val(r, "created_at", 6)
                            u_at = _val(r, "updated_at", 7)
                            tid = str(_val(r, "thread_id", 0))
                            scripts.append({
                                "id": tid,
                                "thread_id": tid,
                                "title": _val(r, "title", 1),
                                "outline_preview": _val(r, "outline_preview", 2),
                                "foss_name": _val(r, "foss_name", 3),
                                "current_stage": _val(r, "current_stage", 4),
                                "status": _val(r, "status", 5),
                                "created_at": c_at.isoformat() if hasattr(c_at, "isoformat") else (str(c_at) if c_at else None),
                                "updated_at": u_at.isoformat() if hasattr(u_at, "isoformat") else (str(u_at) if u_at else None),
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
                        act_type = _val(r, "activity_type", 1)
                        meta = _val(r, "metadata", 4) or {}
                        c_at = _val(r, "created_at", 5)
                        item = {
                            "id": _val(r, "id", 0),
                            "activity_type": act_type,
                            "detail": _val(r, "detail", 2),
                            "status": _val(r, "status", 3),
                            "metadata": meta,
                            "created_at": c_at.isoformat() if hasattr(c_at, "isoformat") else (str(c_at) if c_at else None),
                        }
                        if act_type in ("slide_generation", "slides_generation"):
                            zip_fn = meta.get("zip_filename")
                            if zip_fn and not meta.get("zip_url"):
                                item["zip_url"] = f"/output/slides/{zip_fn}"
                            else:
                                item["zip_url"] = meta.get("zip_url")
                            item["download_url"] = item["zip_url"]
                            item["url"] = item["zip_url"]
                            slides.append(item)
                        elif act_type in ("voice_generation", "voice_generation_combined", "voice_patch", "regenerate_slide"):
                            audio_url = meta.get("audio_url")
                            zip_url = meta.get("zip_url")
                            proj_id = meta.get("project_id")
                            clean_proj = re.sub(r'[^a-zA-Z0-9_-]', '_', re.sub(r'^project_', '', str(proj_id).strip())) if proj_id is not None else None
                            patch_id = meta.get("patch_id")
                            slide_num = meta.get("slide_number")

                            # Retroactive URL resolution if audio_url was not explicitly stored in metadata
                            if not audio_url:
                                if act_type == "voice_patch" and patch_id:
                                    audio_url = f"/output/audio/patches/patch_{patch_id}.wav"
                                elif act_type == "regenerate_slide" and clean_proj and slide_num is not None:
                                    audio_url = f"/output/audio/project_{clean_proj}/slide_{slide_num}.wav"
                                elif act_type == "voice_generation_combined" and clean_proj:
                                    audio_url = f"/output/audio/project_{clean_proj}/full_narration.wav"
                                elif act_type == "voice_generation" and clean_proj:
                                    audio_url = f"/output/audio/project_{clean_proj}/slide_1.wav"

                            # Retroactive ZIP URL resolution
                            if not zip_url and clean_proj and act_type in ("voice_generation", "voice_generation_combined", "regenerate_slide"):
                                zip_url = f"/output/audio/project_{clean_proj}/audio_project_{clean_proj}.zip"

                            item["audio_url"] = audio_url
                            item["url"] = audio_url
                            item["zip_url"] = zip_url
                            item["duration"] = meta.get("duration")
                            audio.append(item)
                        elif act_type == "generate_video":
                            item["video_url"] = meta.get("video_url")
                            item["url"] = meta.get("video_url")
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


async def query_all_activities(
    *,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    activity_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Search and filter across all user activities with pagination.
    Designed for administrative audit, compliance, and clean log extraction.
    """
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    try:
        from src.script_chat.persistence import get_pool
        pool = get_pool()
        conditions: list[str] = []
        params: list[Any] = []

        if user_id:
            try:
                clean_uid = str(UUID(str(user_id)))
                conditions.append("user_id = %s")
                params.append(clean_uid)
            except (ValueError, TypeError, AttributeError):
                return {
                    "total": 0,
                    "limit": limit,
                    "offset": offset,
                    "page": (offset // limit) + 1,
                    "total_pages": 1,
                    "activities": [],
                }

        if email:
            conditions.append("email ILIKE %s")
            params.append(f"%{email.strip()}%")

        if activity_type:
            conditions.append("activity_type = %s")
            params.append(activity_type.strip())

        if status:
            conditions.append("status = %s")
            params.append(status.strip())

        if search:
            search_param = f"%{search.strip()}%"
            conditions.append("(detail ILIKE %s OR email ILIKE %s OR activity_type ILIKE %s)")
            params.extend([search_param, search_param, search_param])

        if start_date:
            conditions.append("created_at >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("created_at <= %s")
            params.append(end_date)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        async with pool.connection() as conn:
            # 1. Total count
            count_query = f"SELECT COUNT(*) FROM user_activities {where_clause}"
            total = 0
            async with conn.cursor() as cur:
                await cur.execute(count_query, params)
                total_row = await cur.fetchone()
                if total_row:
                    total = total_row[0]

            # 2. Page of activities
            data_query = f"""
                SELECT id, user_id, email, activity_type, detail, status, metadata, created_at
                FROM user_activities
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            data_params = list(params) + [limit, offset]
            activities: list[dict[str, Any]] = []
            async with conn.cursor() as cur:
                await cur.execute(data_query, data_params)
                rows = await cur.fetchall()
                for r in rows:
                    c_at = _val(r, "created_at", 7)
                    uid = _val(r, "user_id", 1)
                    meta = _val(r, "metadata", 6) or {}
                    activities.append({
                        "id": _val(r, "id", 0),
                        "user_id": str(uid) if uid else None,
                        "email": _val(r, "email", 2),
                        "activity_type": _val(r, "activity_type", 3),
                        "detail": _val(r, "detail", 4),
                        "status": _val(r, "status", 5),
                        "metadata": meta,
                        "created_at": c_at.isoformat() if hasattr(c_at, "isoformat") else (str(c_at) if c_at else None),
                    })

            total_pages = ((total + limit - 1) // limit) if total > 0 else 1
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "page": (offset // limit) + 1,
                "total_pages": total_pages,
                "activities": activities,
            }
    except Exception as exc:
        logger.debug("Failed to query all activities: %s", exc)
        return {
            "total": 0,
            "limit": limit,
            "offset": offset,
            "page": 1,
            "total_pages": 1,
            "activities": [],
        }


async def get_distinct_activity_types() -> list[str]:
    """Retrieve list of unique activity types recorded in the user_activities table."""
    try:
        from src.script_chat.persistence import get_pool
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT DISTINCT activity_type
                    FROM user_activities
                    ORDER BY activity_type ASC
                    """
                )
                rows = await cur.fetchall()
                types: list[str] = []
                for r in rows:
                    val = _val(r, "activity_type", 0)
                    if val:
                        types.append(str(val))
                return types
    except Exception as exc:
        logger.debug("Failed to get distinct activity types: %s", exc)
        return []


async def get_user_journey(user_identifier: str, limit: int = 200) -> dict[str, Any]:
    """
    Build a comprehensive chronological audit trail of all actions performed by a user.
    Accepts user UUID or email address.
    """
    clean_uid: Optional[str] = None
    email: Optional[str] = None
    try:
        clean_uid = str(UUID(str(user_identifier)))
    except (ValueError, TypeError, AttributeError):
        email = str(user_identifier).strip()

    res = await query_all_activities(
        user_id=clean_uid,
        email=email if not clean_uid else None,
        limit=limit,
    )
    return {
        "user_identifier": user_identifier,
        "total_actions": res["total"],
        "timeline": res["activities"],
    }


async def export_activities(
    *,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    activity_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    export_format: str = "csv",
    max_records: int = 5000,
) -> tuple[str, str]:
    """
    Export filtered activities in CSV or JSON format.
    Returns (content_string, media_type).
    """
    res = await query_all_activities(
        user_id=user_id,
        email=email,
        activity_type=activity_type,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date,
        limit=max_records,
        offset=0,
    )
    items = res.get("activities", [])

    if export_format.lower() == "json":
        return json.dumps(items, indent=2, default=str), "application/json"

    # Default CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID",
        "Timestamp",
        "User ID",
        "Email",
        "Activity Type",
        "Status",
        "Detail",
        "IP Address",
        "User Agent",
        "Metadata",
    ])
    for item in items:
        meta = item.get("metadata") or {}
        writer.writerow([
            item.get("id"),
            item.get("created_at"),
            item.get("user_id") or "",
            item.get("email") or "",
            item.get("activity_type") or "",
            item.get("status") or "",
            item.get("detail") or "",
            meta.get("ip_address", ""),
            meta.get("user_agent", ""),
            json.dumps(meta, default=str),
        ])
    return output.getvalue(), "text/csv"
