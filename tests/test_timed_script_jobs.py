"""Unit coverage for asynchronous timed-script job submission."""
import io
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import UploadFile

from src.api.routes import timed_script


TEST_USER = SimpleNamespace(sub=str(uuid4()))


def make_job(job_id):
    now = datetime.now(timezone.utc)
    return {
        "id": job_id,
        "job_type": "timed_script",
        "status": "queued",
        "original_filename": "voice.wav",
        "result": None,
        "error_message": None,
        "progress": 0,
        "current_stage": None,
        "created_at": now,
        "started_at": None,
        "completed_at": None,
        "updated_at": now,
    }


class TimedScriptJobRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_upload_dir = timed_script.TIMED_SCRIPT_UPLOAD_DIR
        self.original_create_job = timed_script.create_job
        self.original_attach_task = timed_script.attach_celery_task
        self.original_fail_job = timed_script.fail_job
        self.original_send_task = timed_script.celery_app.send_task
        self.temp_dir = Path(tempfile.mkdtemp(prefix="timed-script-test-"))
        self.job_id = uuid4()
        timed_script.TIMED_SCRIPT_UPLOAD_DIR = self.temp_dir
        timed_script.create_job = AsyncMock(return_value=make_job(self.job_id))
        timed_script.attach_celery_task = AsyncMock()
        timed_script.fail_job = AsyncMock()
        timed_script.celery_app.send_task = Mock(return_value=SimpleNamespace(id="celery-task-1"))

    async def asyncTearDown(self):
        timed_script.TIMED_SCRIPT_UPLOAD_DIR = self.original_upload_dir
        timed_script.create_job = self.original_create_job
        timed_script.attach_celery_task = self.original_attach_task
        timed_script.fail_job = self.original_fail_job
        timed_script.celery_app.send_task = self.original_send_task
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_upload_creates_job_without_running_whisper_in_api(self):
        upload = UploadFile(file=io.BytesIO(b"fake audio"), filename="voice.wav")

        response = await timed_script.generate_timed_script_endpoint(upload, None, TEST_USER)

        self.assertEqual(response["job_id"], str(self.job_id))
        self.assertEqual(response["status"], "queued")
        timed_script.celery_app.send_task.assert_called_once_with(
            "src.workers.tasks.process_timed_script",
            args=[str(self.job_id), None],
        )
        timed_script.attach_celery_task.assert_awaited_once_with(
            str(self.job_id), "celery-task-1"
        )
        timed_script.create_job.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
