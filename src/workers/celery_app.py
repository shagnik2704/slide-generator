"""Celery application configuration for background workflows."""
from __future__ import annotations

import os

from celery import Celery


celery_app = Celery(
    "spoken_tutorial",
    include=["src.workers.tasks"],
)

celery_app.conf.update(
    broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    task_default_queue="default",
    task_routes={
        "src.workers.tasks.process_timed_script": {"queue": "whisper"},
        "src.workers.tasks.reap_stale_timed_script_jobs": {"queue": "whisper"},
    },
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Sweep jobs stuck in 'running' (worker died without a redelivery) on an
    # interval. Only fires when a `celery beat` process runs; the whisper worker
    # also reaps opportunistically on every job, so beat is optional.
    beat_schedule={
        "reap-stale-timed-script-jobs": {
            "task": "src.workers.tasks.reap_stale_timed_script_jobs",
            "schedule": float(os.getenv("TIMED_SCRIPT_REAPER_INTERVAL_SECONDS", "300")),
        },
    },
)
