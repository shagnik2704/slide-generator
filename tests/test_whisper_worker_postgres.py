"""Optional integration coverage for the Celery Whisper task lifecycle."""
import asyncio
import importlib.util
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from src.jobs.persistence import create_job, get_job
from src.script_chat.migrate import migrate_application_schema, migrate_checkpoint_schema
from src.script_chat.persistence import close_script_chat_pool, open_script_chat_pool
from src.users.persistence import upsert_user

if importlib.util.find_spec("whisper") is not None:
    from src.workers import tasks
else:
    tasks = None


TEST_DATABASE_URL = os.getenv("SCRIPT_CHAT_TEST_DATABASE_URL")


@unittest.skipUnless(
    TEST_DATABASE_URL and tasks is not None,
    "Set SCRIPT_CHAT_TEST_DATABASE_URL and install the whisper-worker extra",
)
class WhisperWorkerPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_claims_and_completes_a_job(self):
        previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        original_generator = tasks.generate_timed_script
        audio_path = None
        try:
            await asyncio.to_thread(migrate_application_schema)
            await migrate_checkpoint_schema()
            await open_script_chat_pool()
            user = await upsert_user(
                provider="google",
                provider_subject=f"worker-owner-{uuid.uuid4()}",
                email=f"worker-owner-{uuid.uuid4()}@example.com",
            )
            user_id = str(user["id"])
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
                audio_file.write(b"fake audio")
                audio_path = Path(audio_file.name)
            job = await create_job(
                user_id=user_id,
                job_type="timed_script",
                input_path=str(audio_path),
                original_filename="worker.wav",
            )
            job_id = str(job["id"])
            await close_script_chat_pool()

            tasks.generate_timed_script = lambda path, language=None: {
                "success": True,
                "audio_file": str(path),
                "total_sentences": 1,
                "sentences": [],
            }
            await asyncio.to_thread(tasks.process_timed_script.run, job_id, "en")

            await open_script_chat_pool()
            saved = await get_job(job_id, user_id)
            self.assertEqual(saved["status"], "completed")
            self.assertEqual(saved["result"]["audio_file"], "worker.wav")
            self.assertFalse(audio_path.exists())
        finally:
            tasks.generate_timed_script = original_generator
            if audio_path is not None:
                audio_path.unlink(missing_ok=True)
            await close_script_chat_pool()
            if previous_database_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous_database_url


if __name__ == "__main__":
    unittest.main()
