"""Unit coverage for asynchronous timed-script job submission."""
import io
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import UploadFile

from src.api.routes import timed_script
from src.workers import tasks


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


class TimedScriptWorkerTaskTests(unittest.IsolatedAsyncioTestCase):
    """Behaviour of the Whisper worker task around crashes and redeliveries."""

    async def asyncSetUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="timed-script-worker-test-"))
        self.input_path = self.temp_dir / "audio.wav"
        self.input_path.write_bytes(b"fake audio")
        self.job_id = str(uuid4())

    async def asyncTearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _job(self, **overrides):
        job = {
            "id": self.job_id,
            "input_path": str(self.input_path),
            "original_filename": "audio.wav",
            "status": "running",
        }
        job.update(overrides)
        return job

    def _patch_worker(self, **overrides):
        defaults = dict(
            open_script_chat_pool=AsyncMock(),
            close_script_chat_pool=AsyncMock(),
            reap_stale_jobs=AsyncMock(return_value=[]),
            claim_job=AsyncMock(return_value=self._job()),
            complete_job=AsyncMock(),
            fail_job=AsyncMock(),
            get_job_for_worker=AsyncMock(),
            generate_timed_script=Mock(return_value={"success": True, "sentences": []}),
        )
        defaults.update(overrides)
        return patch.multiple(tasks, **defaults)

    async def test_successful_job_completes_and_removes_input(self):
        claim = AsyncMock(return_value=self._job())
        complete = AsyncMock()
        with self._patch_worker(claim_job=claim, complete_job=complete):
            result = await tasks._process_timed_script(self.job_id, "celery-task-1", None)

        self.assertEqual(result["status"], "completed")
        # The task id is threaded into claim so a redelivery of the same task can
        # re-claim the row instead of finding it stuck in 'running'.
        claim.assert_awaited_once_with(self.job_id, "celery-task-1")
        complete.assert_awaited_once()
        self.assertFalse(self.input_path.exists())

    async def test_unclaimable_redelivery_preserves_input_file(self):
        generate = Mock()
        with self._patch_worker(
            claim_job=AsyncMock(return_value=None),
            get_job_for_worker=AsyncMock(return_value={"status": "completed"}),
            generate_timed_script=generate,
        ):
            result = await tasks._process_timed_script(self.job_id, "celery-task-1", None)

        self.assertEqual(result["status"], "completed")
        generate.assert_not_called()
        # A delivery we could not claim belongs to another attempt; its input
        # must survive rather than being deleted out from under it.
        self.assertTrue(self.input_path.exists())

    async def test_generation_failure_marks_failed_and_removes_input(self):
        fail = AsyncMock()
        with self._patch_worker(
            fail_job=fail,
            generate_timed_script=Mock(return_value={"success": False, "error": "boom"}),
        ):
            result = await tasks._process_timed_script(self.job_id, "celery-task-1", None)

        self.assertEqual(result["status"], "failed")
        fail.assert_awaited_once()
        self.assertFalse(self.input_path.exists())

    async def test_input_preserved_when_failure_cannot_be_persisted(self):
        # A crash we cannot even record as 'failed' (e.g. DB down) must leave the
        # input on disk so the redelivered task can still transcribe it.
        with self._patch_worker(
            generate_timed_script=Mock(side_effect=RuntimeError("whisper crashed")),
            fail_job=AsyncMock(side_effect=RuntimeError("db down")),
        ):
            with self.assertRaises(RuntimeError):
                await tasks._process_timed_script(self.job_id, "celery-task-1", None)

        self.assertTrue(self.input_path.exists())

    async def test_processing_reaps_stale_jobs_first(self):
        reap = AsyncMock(return_value=[])
        with self._patch_worker(reap_stale_jobs=reap):
            await tasks._process_timed_script(self.job_id, "celery-task-1", None)

        reap.assert_awaited_once_with(tasks._job_timeout_seconds(), job_type="timed_script")

    async def test_reap_helper_removes_stale_input_files(self):
        stale = self.temp_dir / "stale.wav"
        stale.write_bytes(b"stale audio")
        with patch.object(
            tasks,
            "reap_stale_jobs",
            AsyncMock(return_value=[{"id": self.job_id, "input_path": str(stale)}]),
        ):
            reaped = await tasks._reap_stale_jobs(60)

        self.assertEqual(reaped, [self.job_id])
        self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
