"""Celery tasks that run outside the API worker processes."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from src.jobs.persistence import (
    claim_job,
    complete_job,
    fail_job,
    get_job_for_worker,
)
from src.script_chat.persistence import close_script_chat_pool, open_script_chat_pool
from src.services.timed_script_service import generate_timed_script
from src.workers.celery_app import celery_app


logger = logging.getLogger(__name__)


async def _process_timed_script(job_id: str, language: str | None = None) -> dict:
    await open_script_chat_pool()
    try:
        job = await claim_job(job_id)
        if job is None:
            existing_job = await get_job_for_worker(job_id)
            return {
                "job_id": job_id,
                "status": existing_job["status"] if existing_job else "missing",
            }

        input_path = Path(job["input_path"])
        try:
            result = generate_timed_script(input_path, language=language)
            if not result.get("success"):
                await fail_job(job_id, result.get("error", "Timed script generation failed"))
                return {"job_id": job_id, "status": "failed"}

            result["audio_file"] = job["original_filename"] or input_path.name
            await complete_job(job_id, result)
            return {"job_id": job_id, "status": "completed"}
        finally:
            input_path.unlink(missing_ok=True)
    except Exception as exc:
        logger.exception("Timed script job %s failed", job_id)
        try:
            await fail_job(job_id, str(exc))
        except Exception:
            logger.exception("Could not persist failure for timed script job %s", job_id)
        raise
    finally:
        await close_script_chat_pool()


@celery_app.task(name="src.workers.tasks.process_timed_script")
def process_timed_script(job_id: str, language: str | None = None) -> dict:
    """Transcribe one queued timed-script audio file with the worker-local Whisper model."""
    return asyncio.run(_process_timed_script(job_id, language))
