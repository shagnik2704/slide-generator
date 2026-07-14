"""Optional PostgreSQL coverage for the durable Celery job record."""
import asyncio
import os
import unittest
import uuid

from src.script_chat.migrate import migrate_application_schema, migrate_checkpoint_schema
from src.script_chat.persistence import close_script_chat_pool, open_script_chat_pool
from src.users.persistence import upsert_user
from src.jobs.persistence import (
    claim_job,
    complete_job,
    create_job,
    get_job,
    list_jobs,
    reap_stale_jobs,
)


TEST_DATABASE_URL = os.getenv("SCRIPT_CHAT_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "Set SCRIPT_CHAT_TEST_DATABASE_URL to run PostgreSQL integration tests")
class BackgroundJobPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        await asyncio.to_thread(migrate_application_schema)
        await migrate_checkpoint_schema()
        await open_script_chat_pool()

    async def asyncTearDown(self):
        await close_script_chat_pool()
        if self._previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self._previous_database_url

    async def _make_user_id(self) -> str:
        user = await upsert_user(
            provider="google",
            provider_subject=f"job-owner-{uuid.uuid4()}",
            email=f"job-owner-{uuid.uuid4()}@example.com",
            name="Job Owner",
        )
        return str(user["id"])

    async def _make_job(self, user_id: str) -> str:
        job = await create_job(
            user_id=user_id,
            job_type="timed_script",
            input_path="/app/uploads/timed_script_jobs/example.wav",
            original_filename="example.wav",
        )
        return str(job["id"])

    async def test_job_can_be_claimed_completed_and_reloaded(self):
        user_id = await self._make_user_id()
        job_id = await self._make_job(user_id)

        claimed = await claim_job(job_id)
        self.assertEqual(claimed["status"], "running")
        self.assertIsNone(await claim_job(job_id))

        result = {"success": True, "total_sentences": 1, "sentences": []}
        await complete_job(job_id, result)
        saved = await get_job(job_id, user_id)

        self.assertEqual(saved["status"], "completed")
        self.assertEqual(saved["progress"], 100)
        self.assertEqual(saved["result"], result)
        self.assertTrue(any(row["id"] == saved["id"] for row in await list_jobs(user_id)))

    async def test_running_job_reclaimed_only_by_same_celery_task(self):
        user_id = await self._make_user_id()
        job_id = await self._make_job(user_id)

        # First delivery claims the queued job and records its owning task id.
        first = await claim_job(job_id, "task-A")
        self.assertEqual(first["status"], "running")
        self.assertEqual(first["celery_task_id"], "task-A")

        # A different task (or an anonymous claim) may not steal a running job.
        self.assertIsNone(await claim_job(job_id, "task-B"))
        self.assertIsNone(await claim_job(job_id))

        # The same task being redelivered after a worker crash re-claims it,
        # which is what keeps the row from being stuck in 'running' forever.
        reclaimed = await claim_job(job_id, "task-A")
        self.assertIsNotNone(reclaimed)
        self.assertEqual(reclaimed["status"], "running")
        # started_at is preserved across the re-claim rather than reset.
        self.assertEqual(reclaimed["started_at"], first["started_at"])

    async def test_reaper_fails_only_stale_running_jobs(self):
        user_id = await self._make_user_id()
        running_id = await self._make_job(user_id)
        queued_id = await self._make_job(user_id)
        fresh_id = await self._make_job(user_id)

        await claim_job(running_id, "task-stale")
        await claim_job(fresh_id, "task-fresh")

        # A generous timeout leaves freshly running jobs alone.
        self.assertEqual(await reap_stale_jobs(3600, job_type="timed_script"), [])

        # A zero timeout treats every running job as overdue.
        reaped = await reap_stale_jobs(0, job_type="timed_script")
        reaped_ids = {str(row["id"]) for row in reaped}
        self.assertIn(running_id, reaped_ids)
        self.assertIn(fresh_id, reaped_ids)
        self.assertNotIn(queued_id, reaped_ids)  # never left 'queued'

        stale = await get_job(running_id, user_id)
        self.assertEqual(stale["status"], "failed")
        self.assertIsNotNone(stale["error_message"])
        self.assertIsNotNone(stale["completed_at"])

        # The queued job is untouched and still claimable.
        still_queued = await get_job(queued_id, user_id)
        self.assertEqual(still_queued["status"], "queued")
        self.assertIsNotNone(await claim_job(queued_id, "task-late"))


if __name__ == "__main__":
    unittest.main()
