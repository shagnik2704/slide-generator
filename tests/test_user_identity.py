"""Unit coverage for application-issued user identity tokens."""
import asyncio
import os
import unittest
import uuid

from jose import jwt

from src.api.auth import create_access_token, verify_token
from src.api.config import settings


TEST_DATABASE_URL = os.getenv("SCRIPT_CHAT_TEST_DATABASE_URL")


class UserIdentityTokenTests(unittest.TestCase):
    def test_jwt_subject_is_the_application_user_id(self):
        user_id = "5b1f5555-32ec-4da2-8f5d-c95d20732fd5"
        token = create_access_token(
            subject=user_id,
            email="owner@example.com",
            name="Owner",
        )

        token_data = verify_token(token)

        self.assertIsNotNone(token_data)
        self.assertEqual(token_data.sub, user_id)
        self.assertEqual(token_data.email, "owner@example.com")

    def test_legacy_email_subject_requires_reauthentication(self):
        token = jwt.encode(
            {
                "sub": "owner@example.com",
                "email": "owner@example.com",
                "name": "Owner",
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        self.assertIsNone(verify_token(token))


@unittest.skipUnless(TEST_DATABASE_URL, "Set SCRIPT_CHAT_TEST_DATABASE_URL to run PostgreSQL integration tests")
class UpsertUserReconciliationTests(unittest.IsolatedAsyncioTestCase):
    """PostgreSQL coverage for email-collision reconciliation in upsert_user."""

    async def asyncSetUp(self):
        from src.script_chat.migrate import (
            migrate_application_schema,
            migrate_checkpoint_schema,
        )
        from src.script_chat.persistence import open_script_chat_pool

        self._previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        await asyncio.to_thread(migrate_application_schema)
        await migrate_checkpoint_schema()
        await open_script_chat_pool()

    async def asyncTearDown(self):
        from src.script_chat.persistence import close_script_chat_pool

        await close_script_chat_pool()
        if self._previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self._previous_database_url

    async def test_returning_user_can_take_email_owned_by_a_legacy_row(self):
        """A Google user whose email now matches a legacy row keeps one identity.

        Reproduces the OAuth-callback 500: the provider-identity UPDATE would set
        an email already held by a different users row, violating uq_users_email.
        After the fix the upsert reconciles the two rows into a single identity
        that still owns the legacy row's existing threads.
        """
        from src.script_chat.persistence import create_thread, get_pool, get_thread
        from src.users.persistence import upsert_user

        provider_subject = f"google-{uuid.uuid4()}"
        original_email = f"user-{uuid.uuid4()}@example.com"
        # The email the migration backfilled onto a separate 'legacy' row.
        legacy_email = f"legacy-{uuid.uuid4()}@example.com"

        # A returning Google identity that already owns a thread.
        identity = await upsert_user(
            provider="google",
            provider_subject=provider_subject,
            email=original_email,
            name="Original Name",
        )
        identity_id = str(identity["id"])
        identity_thread = f"identity-thread-{uuid.uuid4()}"
        await create_thread(identity_thread, identity_id, "NumPy", "Outline")

        # A distinct legacy row (from migration 20260711_02) owning the email the
        # Google account is about to change to, plus a thread it still owns.
        async with get_pool().connection() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO users (provider, provider_subject, email)
                    VALUES ('legacy', %s, %s)
                    RETURNING id
                    """,
                    (legacy_email, legacy_email),
                )
                legacy_row = await cursor.fetchone()
        legacy_id = str(legacy_row["id"])
        legacy_thread = f"legacy-thread-{uuid.uuid4()}"
        await create_thread(legacy_thread, legacy_id, "SciPy", "Outline")

        # Google reports the same subject with the email now owned by the legacy
        # row. Before the fix this raised (aborting the OAuth callback with a 500).
        reconciled = await upsert_user(
            provider="google",
            provider_subject=provider_subject,
            email=legacy_email,
            name="Updated Name",
        )

        # A single, stable identity survives: the provider-identity row, now
        # carrying the collided email and refreshed profile.
        self.assertEqual(str(reconciled["id"]), identity_id)
        self.assertEqual(reconciled["provider"], "google")
        self.assertEqual(reconciled["email"], legacy_email)
        self.assertEqual(reconciled["name"], "Updated Name")

        # The surviving identity owns both its own and the legacy row's threads.
        self.assertIsNotNone(await get_thread(identity_thread, identity_id))
        self.assertIsNotNone(await get_thread(legacy_thread, identity_id))

        # The legacy row was folded in, leaving exactly one owner for the email.
        async with get_pool().connection() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT id FROM users WHERE email = %s",
                    (legacy_email,),
                )
                owners = await cursor.fetchall()
        self.assertEqual([str(row["id"]) for row in owners], [identity_id])


if __name__ == "__main__":
    unittest.main()
