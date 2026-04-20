"""
Celery Application
------------------
Configures Celery with RabbitMQ broker and Redis result backend.
Two queues:
  fast_lane  : clips < 10 minutes
  slow_lane  : clips 10-60 minutes (long-running workers)
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from celery import Celery
from src.core.config import settings

celery_app = Celery(
    "sas",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.workers.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "src.workers.tasks.analyze_audio_task": {
            "queue": "fast_lane",
        },
        "src.workers.tasks.analyze_audio_long_task": {
            "queue": "slow_lane",
        },
    },

    # Result expiry: keep results 24 hours
    result_expires=86400,

    # Worker settings
    worker_prefetch_multiplier=1,   # process one task at a time per worker
    task_acks_late=True,            # ack after completion (safe for retries)

    # Retry settings
    task_max_retries=2,
    task_default_retry_delay=10,
)