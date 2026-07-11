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


async def claim_job(job_id: str) -> Optional[dict[str, Any]]:
    """Atomically claim a queued job; duplicate deliveries become no-ops."""
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                f"""
                UPDATE background_jobs
                SET status = 'running', progress = 10, current_stage = 'transcribing',
                    started_at = NOW(), updated_at = NOW()
                WHERE id = %s AND status = 'queued'
                RETURNING {JOB_COLUMNS}
                """,
                (job_id,),
            )
            return await cursor.fetchone()


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
