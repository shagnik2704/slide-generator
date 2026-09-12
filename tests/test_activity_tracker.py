"""Unit and integration tests for fail-safe activity tracking."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.activity.tracker import log_activity, record_activity


TEST_DATABASE_URL = os.getenv("SCRIPT_CHAT_TEST_DATABASE_URL")


class ActivityTrackerUnitTests(unittest.IsolatedAsyncioTestCase):
    """Unit tests ensuring activity tracker is 100% fail-safe and error-free."""

    async def test_record_activity_never_raises_when_db_down_or_uninitialized(self):
        """Even if get_pool raises an exception, record_activity must not raise."""
        with patch("src.script_chat.persistence.get_pool", side_effect=RuntimeError("DB pool not initialized")):
            try:
                await record_activity(
                    user_id=str(uuid4()),
                    email="test@example.com",
                    activity_type="voice_generation",
                    detail="Generated 5 slides",
                    status="completed",
                )
            except Exception as exc:
                self.fail(f"record_activity raised an exception when DB was down: {exc}")

    async def test_record_activity_handles_corrupt_or_invalid_user_id(self):
        """Invalid user_id strings (not UUIDs) should be sanitized to None rather than raising ValueError."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__aenter__.return_value = mock_conn

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            await record_activity(
                user_id="invalid-not-a-uuid",
                email="user@test.org",
                activity_type="slide_generation",
                detail="Test details",
            )

            # Check that execute was called with None for user_id
            self.assertTrue(mock_conn.execute.called)
            args = mock_conn.execute.call_args[0][1]
            self.assertIsNone(args[0])  # user_id should be None
            self.assertEqual(args[1], "user@test.org")
            self.assertEqual(args[2], "slide_generation")

    async def test_record_activity_truncates_long_strings(self):
        """Overly long details or statuses should be truncated safely."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__aenter__.return_value = mock_conn

        valid_uid = str(uuid4())
        super_long_detail = "X" * 500
        super_long_status = "S" * 100

        with patch("src.script_chat.persistence.get_pool", return_value=mock_pool):
            await record_activity(
                user_id=valid_uid,
                email="user@test.org",
                activity_type="test_type",
                detail=super_long_detail,
                status=super_long_status,
                metadata={"foo": "bar"},
            )

            self.assertTrue(mock_conn.execute.called)
            args = mock_conn.execute.call_args[0][1]
            self.assertEqual(args[0], valid_uid)
            self.assertEqual(len(args[3]), 255)  # detail truncated to 255
            self.assertEqual(len(args[4]), 32)   # status truncated to 32

    async def test_log_activity_schedules_async_task(self):
        """log_activity should create an asyncio task on the running event loop."""
        loop = asyncio.get_running_loop()
        task_created = []

        def custom_create_task(coro):
            task_created.append(coro)
            # Close coroutine to avoid un-awaited coroutine warning
            coro.close()
            return MagicMock()

        with patch.object(loop, "create_task", side_effect=custom_create_task):
            log_activity(
                user_id=str(uuid4()),
                email="async@example.com",
                activity_type="batch_translation",
                detail="Batch 3 languages",
            )

        self.assertEqual(len(task_created), 1)

    def test_log_activity_failsafe_without_running_loop(self):
        """If there is no running loop, log_activity handles RuntimeError silently."""
        with patch("asyncio.get_running_loop", side_effect=RuntimeError("no running event loop")):
            try:
                log_activity(
                    activity_type="voice_patch",
                    detail="Patch slide 1",
                )
            except Exception as exc:
                self.fail(f"log_activity raised exception when no event loop: {exc}")


@unittest.skipUnless(TEST_DATABASE_URL, "Set SCRIPT_CHAT_TEST_DATABASE_URL to run PostgreSQL integration tests")
class ActivityTrackerPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Integration test with real PostgreSQL instance and migrations."""

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
        if self._previous_database_url is not None:
            os.environ["DATABASE_URL"] = self._previous_database_url
        else:
            os.environ.pop("DATABASE_URL", None)

    async def test_roundtrip_persist_activity(self):
        from src.script_chat.persistence import get_pool

        test_email = f"track_{uuid4().hex[:8]}@example.com"
        await record_activity(
            email=test_email,
            activity_type="voice_generation",
            detail="5 slides generated",
            status="completed",
            metadata={"sample": "data"},
        )

        pool = get_pool()
        async with pool.connection() as conn:
            cursor = await conn.execute(
                "SELECT email, activity_type, detail, status, metadata FROM user_activities WHERE email = %s",
                (test_email,),
            )
            row = await cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], test_email)
        self.assertEqual(row[1], "voice_generation")
        self.assertEqual(row[2], "5 slides generated")
        self.assertEqual(row[3], "completed")
        self.assertEqual(row[4], {"sample": "data"})
