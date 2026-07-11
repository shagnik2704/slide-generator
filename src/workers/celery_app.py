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
    },
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
