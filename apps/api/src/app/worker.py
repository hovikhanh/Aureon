"""Celery app: `uv run celery -A app.worker worker|beat` (beat: exactly 1 instance)."""

from celery import Celery

from app.core.config import get_config

_cfg = get_config()

celery_app = Celery(
    "aureon",
    broker=_cfg.celery_broker_url.get_secret_value(),
    backend=_cfg.celery_result_backend.get_secret_value(),
    include=["app.workers.events"],
)
celery_app.conf.update(
    task_acks_late=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    result_expires=3600,
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    task_routes={"app.events.*": {"queue": "events"}},
    beat_schedule={
        "relay-outbox-events": {
            "task": "app.events.relay_outbox_events",
            "schedule": _cfg.outbox_relay_interval_seconds,
            "options": {"expires": _cfg.outbox_relay_interval_seconds * 5},
        },
    },
)

app = celery_app
