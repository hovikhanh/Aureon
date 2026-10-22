"""Celery app: `uv run celery -A app.worker worker|beat` (beat: exactly 1 instance)."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_config

_cfg = get_config()

celery_app = Celery(
    "aureon",
    broker=_cfg.celery_broker_url.get_secret_value(),
    backend=_cfg.celery_result_backend.get_secret_value(),
    include=["app.workers.events", "app.workers.jobs"],
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
    task_routes={"app.events.*": {"queue": "events"}, "app.jobs.*": {"queue": "default"}},
    beat_schedule={
        "relay-outbox-events": {
            "task": "app.events.relay_outbox_events",
            "schedule": _cfg.outbox_relay_interval_seconds,
            "options": {"expires": _cfg.outbox_relay_interval_seconds * 5},
        },
        # T-235 / DEC-203 — business jobs, local time Asia/Ho_Chi_Minh
        "daily-burn-check": {
            "task": "app.jobs.daily_burn_check",
            "schedule": crontab(minute=0, hour=9),
        },
        "mark-invoices-overdue": {
            "task": "app.jobs.mark_invoices_overdue",
            "schedule": crontab(minute=0, hour=10),
        },
        "detect-late-hiring": {
            "task": "app.jobs.detect_late_hiring",
            "schedule": crontab(minute=0, hour=11),
        },
        "detect-overdue-tasks": {  # EVT-execution.task_overdue (T-131)
            "task": "app.jobs.detect_overdue_tasks",
            "schedule": crontab(minute=30, hour=8),
        },
        "verify-action-outcome": {
            "task": "app.jobs.verify_action_outcome",
            "schedule": crontab(minute=5),
        },
        # 03 §1.3: metrics also recomputed daily at 01:00 (besides event-driven recompute)
        "recompute-metrics": {
            "task": "app.jobs.recompute_metrics",
            "schedule": crontab(minute=0, hour=1),
        },
        # T-412 / 04 §8.3 — escalate overdue IDP reviews, hourly
        "check-review-sla": {
            "task": "app.jobs.check_review_sla",
            "schedule": crontab(minute=15),
        },
    },
)

app = celery_app
