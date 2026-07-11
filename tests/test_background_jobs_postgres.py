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
)


TEST_DATABASE_URL = os.getenv("SCRIPT_CHAT_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "Set SCRIPT_CHAT_TEST_DATABASE_URL to run PostgreSQL integration tests")
class BackgroundJobPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def test_job_can_be_claimed_completed_and_reloaded(self):
        previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        try:
            await asyncio.to_thread(migrate_application_schema)
            await migrate_checkpoint_schema()
            await open_script_chat_pool()

            user = await upsert_user(
                provider="google",
                provider_subject=f"job-owner-{uuid.uuid4()}",
                email=f"job-owner-{uuid.uuid4()}@example.com",
                name="Job Owner",
            )
            user_id = str(user["id"])
            job = await create_job(
                user_id=user_id,
                job_type="timed_script",
                input_path="/app/uploads/timed_script_jobs/example.wav",
                original_filename="example.wav",
            )
            job_id = str(job["id"])

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
        finally:
            await close_script_chat_pool()
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url


if __name__ == "__main__":
    unittest.main()
