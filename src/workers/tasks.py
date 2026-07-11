"""Celery tasks that run outside the API worker processes."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from src.jobs.persistence import (
    claim_job,
    complete_job,
    fail_job,
    get_job_for_worker,
    reap_stale_jobs,
)
from src.script_chat.persistence import close_script_chat_pool, open_script_chat_pool
from src.services.timed_script_service import generate_timed_script
from src.workers.celery_app import celery_app


logger = logging.getLogger(__name__)

# A job running longer than this is treated as stuck (its worker died without the
# broker redelivering the task) and is failed so the UI stops polling forever.
# Must comfortably exceed the slowest realistic transcription.
DEFAULT_JOB_TIMEOUT_SECONDS = 1800


def _job_timeout_seconds() -> int:
    raw = os.getenv("TIMED_SCRIPT_JOB_TIMEOUT_SECONDS")
    if raw is None:
        return DEFAULT_JOB_TIMEOUT_SECONDS
    try:
        return max(60, int(raw))
    except ValueError:
        logger.warning("Invalid TIMED_SCRIPT_JOB_TIMEOUT_SECONDS=%r; using default", raw)
        return DEFAULT_JOB_TIMEOUT_SECONDS


async def _reap_stale_jobs(timeout_seconds: int) -> list[str]:
    """Fail stale timed-script jobs and delete their now-unusable input files."""
    reaped = await reap_stale_jobs(timeout_seconds, job_type="timed_script")
    for job in reaped:
        input_path = job.get("input_path")
        if input_path:
            Path(input_path).unlink(missing_ok=True)
    if reaped:
        logger.warning("Reaped %d stale timed-script job(s)", len(reaped))
    return [str(job["id"]) for job in reaped]


async def _process_timed_script(
    job_id: str,
    celery_task_id: str | None = None,
    language: str | None = None,
) -> dict:
    await open_script_chat_pool()
    input_path: Path | None = None
    reached_terminal = False
    try:
        # Best-effort sweep so a job whose redelivery never arrived still resolves
        # whenever the worker picks up new work, even without a Celery beat process.
        try:
            await _reap_stale_jobs(_job_timeout_seconds())
        except Exception:
            logger.exception("Stale-job reap failed while processing %s", job_id)

        job = await claim_job(job_id, celery_task_id)
        if job is None:
            existing_job = await get_job_for_worker(job_id)
            return {
                "job_id": job_id,
                "status": existing_job["status"] if existing_job else "missing",
            }

        input_path = Path(job["input_path"])
        result = generate_timed_script(input_path, language=language)
        if not result.get("success"):
            await fail_job(job_id, result.get("error", "Timed script generation failed"))
            reached_terminal = True
            return {"job_id": job_id, "status": "failed"}

        result["audio_file"] = job["original_filename"] or input_path.name
        await complete_job(job_id, result)
        reached_terminal = True
        return {"job_id": job_id, "status": "completed"}
    except Exception as exc:
        logger.exception("Timed script job %s failed", job_id)
        try:
            await fail_job(job_id, str(exc))
            reached_terminal = True
        except Exception:
            logger.exception("Could not persist failure for timed script job %s", job_id)
        raise
    finally:
        # Only delete the upload once the job has reached a terminal state
        # (completed/failed). A worker killed mid-transcription never runs this
        # block, and a failure we could not persist leaves reached_terminal
        # False, so in both cases the input survives for a redelivered attempt.
        if input_path is not None and reached_terminal:
            input_path.unlink(missing_ok=True)
        await close_script_chat_pool()


@celery_app.task(bind=True, name="src.workers.tasks.process_timed_script")
def process_timed_script(self, job_id: str, language: str | None = None) -> dict:
    """Transcribe one queued timed-script audio file with the worker-local Whisper model."""
    return asyncio.run(_process_timed_script(job_id, self.request.id, language))


async def _reap_and_close(timeout_seconds: int) -> dict:
    await open_script_chat_pool()
    try:
        return {"reaped": await _reap_stale_jobs(timeout_seconds)}
    finally:
        await close_script_chat_pool()


@celery_app.task(name="src.workers.tasks.reap_stale_timed_script_jobs")
def reap_stale_timed_script_jobs(timeout_seconds: int | None = None) -> dict:
    """Fail timed-script jobs stuck in 'running' so their UI stops polling forever.

    Runs opportunistically inside every ``process_timed_script`` call and, when a
    Celery beat process is configured, on the ``beat_schedule`` interval so idle
    deployments still recover stuck jobs.
    """
    seconds = timeout_seconds if timeout_seconds is not None else _job_timeout_seconds()
    return asyncio.run(_reap_and_close(seconds))
