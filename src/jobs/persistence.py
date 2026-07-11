"""Async persistence operations for background jobs."""
from __future__ import annotations

from typing import Any, Optional

from psycopg.types.json import Jsonb

from src.script_chat.persistence import get_pool


JOB_COLUMNS = """
    id, user_id, job_type, status, celery_task_id, original_filename,
    input_path, result, error_message, progress, current_stage,
    created_at, started_at, completed_at, updated_at
"""


async def create_job(
    *,
    user_id: str,
    job_type: str,
    input_path: str,
    original_filename: Optional[str],
) -> dict[str, Any]:
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                f"""
                INSERT INTO background_jobs
                    (user_id, job_type, input_path, original_filename)
                VALUES (%s, %s, %s, %s)
                RETURNING {JOB_COLUMNS}
                """,
                (user_id, job_type, input_path, original_filename),
            )
            row = await cursor.fetchone()
    if row is None:
        raise RuntimeError("Failed to create background job")
    return row


async def attach_celery_task(job_id: str, celery_task_id: str) -> None:
    async with get_pool().connection() as connection:
        await connection.execute(
            """
            UPDATE background_jobs
            SET celery_task_id = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (celery_task_id, job_id),
        )


async def fail_job(job_id: str, error_message: str) -> None:
    async with get_pool().connection() as connection:
        await connection.execute(
            """
            UPDATE background_jobs
            SET status = 'failed', error_message = %s, completed_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """,
            (error_message[:10000], job_id),
        )


async def get_job(job_id: str, user_id: str) -> Optional[dict[str, Any]]:
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                f"""
                SELECT {JOB_COLUMNS}
                FROM background_jobs
                WHERE id = %s AND user_id = %s
                """,
                (job_id, user_id),
            )
            return await cursor.fetchone()


async def list_jobs(
    user_id: str,
    limit: int = 50,
    job_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            type_clause = "AND job_type = %s" if job_type else ""
            params = (user_id, job_type, limit) if job_type else (user_id, limit)
            await cursor.execute(
                f"""
                SELECT {JOB_COLUMNS}
                FROM background_jobs
                WHERE user_id = %s {type_clause}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                params,
            )
            return await cursor.fetchall()


async def claim_job(
    job_id: str,
    celery_task_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Atomically claim a job for processing, returning the claimed row or None.

    A job is claimable when it is still ``queued`` or when the *same* Celery
    task is being redelivered after a worker crash (a ``running`` row whose
    ``celery_task_id`` matches). The latter case is what keeps a job from being
    stuck in ``running`` forever when ``task_acks_late`` +
    ``task_reject_on_worker_lost`` cause Redis to redeliver the task. Any other
    delivery — a stale duplicate, or a row already owned by a different task —
    is a no-op and returns None.

    The owning ``celery_task_id`` is recorded on claim so redelivery matching
    works even if the API's ``attach_celery_task`` update raced the worker.
    """
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                f"""
                UPDATE background_jobs
                SET status = 'running', progress = 10, current_stage = 'transcribing',
                    celery_task_id = COALESCE(%s, celery_task_id),
                    started_at = COALESCE(started_at, NOW()), updated_at = NOW()
                WHERE id = %s
                  AND (
                    status = 'queued'
                    OR (status = 'running' AND %s::text IS NOT NULL AND celery_task_id = %s)
                  )
                RETURNING {JOB_COLUMNS}
                """,
                (celery_task_id, job_id, celery_task_id, celery_task_id),
            )
            return await cursor.fetchone()


async def reap_stale_jobs(
    timeout_seconds: int,
    job_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Fail jobs stuck in ``running`` past ``timeout_seconds``; return the rows.

    This is the safety net for the case a redelivery cannot cover: the worker
    died and the broker never re-queued the task (message lost, no worker
    online, broker restarted). Such a row would otherwise stay ``running``
    forever and any UI polling it would poll forever. Returning the affected
    rows lets the caller clean up each job's input file.
    """
    type_clause = "AND job_type = %s" if job_type else ""
    params: list[Any] = [timeout_seconds]
    if job_type:
        params.append(job_type)
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                f"""
                UPDATE background_jobs
                SET status = 'failed',
                    error_message = 'Job exceeded the maximum processing time and was marked as failed by the stale-job reaper.',
                    completed_at = NOW(), updated_at = NOW()
                WHERE status = 'running'
                  AND COALESCE(started_at, updated_at) < NOW() - (%s * INTERVAL '1 second')
                  {type_clause}
                RETURNING {JOB_COLUMNS}
                """,
                params,
            )
            return await cursor.fetchall()


async def get_job_for_worker(job_id: str) -> Optional[dict[str, Any]]:
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                f"SELECT {JOB_COLUMNS} FROM background_jobs WHERE id = %s",
                (job_id,),
            )
            return await cursor.fetchone()


async def complete_job(job_id: str, result: dict[str, Any]) -> None:
    async with get_pool().connection() as connection:
        await connection.execute(
            """
            UPDATE background_jobs
            SET status = 'completed', progress = 100, current_stage = 'completed',
                result = %s, error_message = NULL, completed_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """,
            (Jsonb(result), job_id),
        )
