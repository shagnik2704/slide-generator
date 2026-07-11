"""Persistence operations for application users."""
from __future__ import annotations

from typing import Any

from src.script_chat.persistence import get_pool


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
                # Match the provider identity first so an email change updates
                # the same application user.
                await cursor.execute(
                    """
                    UPDATE users
                    SET email = %s,
                        name = %s,
                        picture = %s,
                        last_login_at = NOW(),
                        updated_at = NOW()
                    WHERE provider = %s AND provider_subject = %s
                    RETURNING id, provider, provider_subject, email, name, picture,
                              last_login_at, created_at, updated_at
                    """,
                    (
                        normalized_email,
                        name or None,
                        picture or None,
                        provider,
                        provider_subject,
                    ),
                )
                user = await cursor.fetchone()
                if user is not None:
                    return user

                # Matching by email upgrades identities backfilled by the
                # migration without losing ownership of existing threads.
                await cursor.execute(
                    """
                    INSERT INTO users
                        (provider, provider_subject, email, name, picture, last_login_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (email) DO UPDATE
                    SET provider = EXCLUDED.provider,
                        provider_subject = EXCLUDED.provider_subject,
                        name = EXCLUDED.name,
                        picture = EXCLUDED.picture,
                        last_login_at = NOW(),
                        updated_at = NOW()
                    RETURNING id, provider, provider_subject, email, name, picture,
                              last_login_at, created_at, updated_at
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
