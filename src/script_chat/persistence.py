"""Pooled PostgreSQL persistence for Script Chat metadata and ownership."""
from __future__ import annotations

import os
from typing import Any, Optional

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from src.api.config import settings


_pool: AsyncConnectionPool | None = None


def get_database_url() -> str:
    """Return the runtime URL so integration tests can provide an isolated DB."""
    return os.getenv("DATABASE_URL", settings.database_url)


def get_sqlalchemy_database_url() -> str:
    """Return a psycopg-v3 SQLAlchemy URL for Alembic's synchronous engine."""
    database_url = get_database_url()
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Script Chat database pool has not been initialized")
    return _pool


async def assert_script_chat_schema() -> None:
    """Fail fast when application or LangGraph migrations have not run."""
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT
                    to_regclass('users') AS user_table,
                    to_regclass('script_chat_threads') AS thread_table,
                    to_regclass('background_jobs') AS job_table,
                    to_regclass('checkpoints') AS checkpoint_table
                """
            )
            tables = await cursor.fetchone()

    missing = []
    if not tables or tables["user_table"] is None:
        missing.append("users")
    if not tables or tables["thread_table"] is None:
        missing.append("script_chat_threads")
    if not tables or tables["job_table"] is None:
        missing.append("background_jobs")
    if not tables or tables["checkpoint_table"] is None:
        missing.append("LangGraph checkpoints")
    if missing:
        raise RuntimeError(
            "Script Chat database schema is not ready "
            f"(missing: {', '.join(missing)}). Run `python -m src.script_chat.migrate`."
        )


async def open_script_chat_pool() -> None:
    """Open the per-process connection pool and verify the migrated schema."""
    global _pool
    if _pool is not None:
        return

    pool = AsyncConnectionPool(
        get_database_url(),
        kwargs={"autocommit": True, "row_factory": dict_row},
        min_size=settings.database_pool_min_size,
        max_size=settings.database_pool_max_size,
        timeout=settings.database_pool_timeout_seconds,
        open=False,
        name="script-chat-metadata",
    )
    try:
        await pool.open(wait=True, timeout=settings.database_pool_timeout_seconds)
        _pool = pool
        await assert_script_chat_schema()
    except Exception:
        _pool = None
        await pool.close()
        raise


async def close_script_chat_pool() -> None:
    """Close all metadata connections owned by this API worker."""
    global _pool
    pool = _pool
    _pool = None
    if pool is not None:
        await pool.close()


async def check_script_chat_database() -> None:
    """Run the lightweight readiness query used by the API health endpoint."""
    async with get_pool().connection(timeout=settings.database_pool_timeout_seconds) as connection:
        await connection.execute("SELECT 1")


async def create_thread(
    thread_id: str,
    user_id: str,
    foss_name: Optional[str],
    outline_preview: Optional[str],
) -> dict[str, Any]:
    """Create the application record before a workflow can begin."""
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO script_chat_threads
                    (thread_id, user_id, foss_name, outline_preview)
                VALUES (%s, %s, %s, %s)
                RETURNING thread_id, user_id, title, outline_preview, foss_name,
                          current_stage, status, archived_at, created_at, updated_at
                """,
                (thread_id, user_id, foss_name, outline_preview),
            )
            row = await cursor.fetchone()
    if row is None:
        raise RuntimeError("Failed to create Script Chat thread metadata")
    return row


async def get_thread(thread_id: str, user_id: str) -> Optional[dict[str, Any]]:
    """Return a non-archived thread only when it belongs to the requester."""
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT thread_id, user_id, title, outline_preview, foss_name,
                       current_stage, status, archived_at, created_at, updated_at
                FROM script_chat_threads
                WHERE thread_id = %s AND user_id = %s AND archived_at IS NULL
                """,
                (thread_id, user_id),
            )
            return await cursor.fetchone()


async def list_threads(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """List the most recently active non-archived threads for one user."""
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT thread_id, title, outline_preview, foss_name, current_stage,
                       status, created_at, updated_at
                FROM script_chat_threads
                WHERE user_id = %s AND archived_at IS NULL
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return await cursor.fetchall()


async def update_thread(
    thread_id: str,
    *,
    current_stage: Optional[str],
    status: str,
    title: Optional[str] = None,
) -> None:
    """Persist the latest workflow state for discovery after reconnects."""
    async with get_pool().connection() as connection:
        await connection.execute(
            """
            UPDATE script_chat_threads
            SET current_stage = COALESCE(%s, current_stage),
                status = %s,
                title = COALESCE(%s, title),
                updated_at = NOW()
            WHERE thread_id = %s
            """,
            (current_stage, status, title, thread_id),
        )


async def archive_thread(thread_id: str, user_id: str) -> bool:
    """Hide a thread from normal discovery while retaining its checkpoints."""
    async with get_pool().connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                UPDATE script_chat_threads
                SET archived_at = NOW(), updated_at = NOW()
                WHERE thread_id = %s AND user_id = %s AND archived_at IS NULL
                RETURNING thread_id
                """,
                (thread_id, user_id),
            )
            return await cursor.fetchone() is not None


async def delete_thread(thread_id: str, user_id: str) -> None:
    """Remove metadata when initial checkpoint creation could not complete."""
    async with get_pool().connection() as connection:
        await connection.execute(
            "DELETE FROM script_chat_threads WHERE thread_id = %s AND user_id = %s",
            (thread_id, user_id),
        )
