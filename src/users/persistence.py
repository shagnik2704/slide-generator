"""Persistence operations for application users."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncCursor

from src.script_chat.persistence import get_pool


# Shared projection so every identity-returning statement yields the same shape.
_USER_COLUMNS = """
    id, provider, provider_subject, email, name, picture,
    last_login_at, created_at, updated_at
"""


async def _merge_user_ownership(
    cursor: AsyncCursor[Any],
    *,
    source_id: Any,
    target_id: Any,
) -> None:
    """Re-point everything owned by ``source_id`` onto ``target_id`` and drop it.

    Both ``script_chat_threads`` and ``background_jobs`` reference ``users.id``
    with ``ON DELETE RESTRICT``, so ownership must move before the source row can
    be deleted. Running this *before* the caller claims the source's email keeps
    ``uq_users_email`` from ever tripping inside the transaction.
    """
    await cursor.execute(
        "UPDATE script_chat_threads SET user_id = %s WHERE user_id = %s",
        (target_id, source_id),
    )
    await cursor.execute(
        "UPDATE background_jobs SET user_id = %s WHERE user_id = %s",
        (target_id, source_id),
    )
    await cursor.execute("DELETE FROM users WHERE id = %s", (source_id,))


async def upsert_user(
    *,
    provider: str,
    provider_subject: str,
    email: str,
    name: str = "",
    picture: str = "",
) -> dict[str, Any]:
    """Create or refresh a user and return their stable application identity."""
    normalized_email = email.strip().lower()
    async with get_pool().connection() as connection:
        async with connection.transaction():
            async with connection.cursor() as cursor:
                # Lock the provider identity and the row that currently owns the
                # incoming email (if either exists). Reconciling a cross-row email
                # collision up front — rather than letting an UPDATE trip
                # uq_users_email and abort the transaction — keeps the whole
                # operation on the happy path (psycopg forbids continuing a
                # transaction after a statement has errored).
                await cursor.execute(
                    """
                    SELECT id FROM users
                    WHERE provider = %s AND provider_subject = %s
                    FOR UPDATE
                    """,
                    (provider, provider_subject),
                )
                identity = await cursor.fetchone()

                await cursor.execute(
                    "SELECT id FROM users WHERE email = %s FOR UPDATE",
                    (normalized_email,),
                )
                email_owner = await cursor.fetchone()

                if identity is not None:
                    identity_id = identity["id"]
                    # A returning user whose email now belongs to a *different*
                    # row (e.g. a legacy backfill identity from migration
                    # 20260711_02, or another account). Fold that row's ownership
                    # into this identity so the refresh below can take the email.
                    if email_owner is not None and email_owner["id"] != identity_id:
                        await _merge_user_ownership(
                            cursor,
                            source_id=email_owner["id"],
                            target_id=identity_id,
                        )

                    await cursor.execute(
                        f"""
                        UPDATE users
                        SET email = %s,
                            name = %s,
                            picture = %s,
                            last_login_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING {_USER_COLUMNS}
                        """,
                        (
                            normalized_email,
                            name or None,
                            picture or None,
                            identity_id,
                        ),
                    )
                    user = await cursor.fetchone()
                    if user is None:
                        raise RuntimeError("Failed to refresh application user")
                    return user

                # No provider identity yet. Upgrading the email owner in place
                # cannot violate uq_users_provider_subject: a row already holding
                # this (provider, provider_subject) would have matched above.
                if email_owner is not None:
                    await cursor.execute(
                        f"""
                        UPDATE users
                        SET provider = %s,
                            provider_subject = %s,
                            name = %s,
                            picture = %s,
                            last_login_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING {_USER_COLUMNS}
                        """,
                        (
                            provider,
                            provider_subject,
                            name or None,
                            picture or None,
                            email_owner["id"],
                        ),
                    )
                    user = await cursor.fetchone()
                    if user is None:
                        raise RuntimeError("Failed to upgrade application user")
                    return user

                await cursor.execute(
                    f"""
                    INSERT INTO users
                        (provider, provider_subject, email, name, picture, last_login_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    RETURNING {_USER_COLUMNS}
                    """,
                    (
                        provider,
                        provider_subject,
                        normalized_email,
                        name or None,
                        picture or None,
                    ),
                )
                user = await cursor.fetchone()

    if user is None:
        raise RuntimeError("Failed to create or update application user")
    return user
