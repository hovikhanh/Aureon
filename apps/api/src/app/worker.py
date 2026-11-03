"""Celery app: `uv run celery -A app.worker worker|beat` (beat: exactly 1 instance)."""

from celery import Celery
from celery.schedules import crontab

from app.core import log_redaction
from app.core.config import get_config

_cfg = get_config()


def _hhmm(value: str, *, default: tuple[int, int]) -> tuple[int, int]:
    """Parse a `HH:MM` config string into (hour, minute); fall back on a bad value."""
    try:
        h, m = value.split(":")
        return int(h), int(m)
    except (ValueError, AttributeError):
        return default


_BRIEF_H, _BRIEF_M = _hhmm(_cfg.briefing_time, default=(6, 0))

log_redaction.install()  # worker + beat: mask secrets in logs / task tracebacks (R-DEC-167)
celery_app = Celery(
    "aureon",
    broker=_cfg.celery_broker_url.get_secret_value(),
    backend=_cfg.celery_result_backend.get_secret_value(),
    include=[
        "app.workers.events",
        "app.workers.jobs",
        "app.workers.notifications",
        # IDP pipeline (04 §3): registers `app.idp.process_document`. Without this the worker
        # receives the task (enqueued on upload via `enqueue_pipeline`) but rejects it with
        # `KeyError: 'app.idp.process_document'`, leaving every uploaded document stuck at
        # UPLOADED (no extraction, no review) — unlike seeded docs that are pre-processed.
        "app.workers.idp_pipeline",
    ],
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
    task_routes={
        "app.events.*": {"queue": "events"},
        "app.jobs.*": {"queue": "default"},
        "app.notifications.*": {"queue": "default"},
        "app.idp.*": {"queue": "idp"},  # worker consumes `default,idp,events`
    },
    beat_schedule={
        "relay-outbox-events": {
            "task": "app.events.relay_outbox_events",
            "schedule": _cfg.outbox_relay_interval_seconds,
            "options": {"expires": _cfg.outbox_relay_interval_seconds * 5},
        },
        # T-616b / R-DEC-33 — e-mail channel for PENDING notifications
        "dispatch-notification-emails": {
            "task": "app.notifications.dispatch_email",
            "schedule": _cfg.notification_email_interval_seconds,
            "options": {"expires": _cfg.notification_email_interval_seconds * 2},
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
        "execution.kr_at_risk": {  # R-DEC-55 — daily KR at-risk (EVT-execution.okr_at_risk)
            "task": "app.jobs.detect_kr_at_risk",
            "schedule": crontab(minute=0, hour=7),
        },
        "execution.checkin_reminder": {  # 10 §9.2 — Friday weekly check-in reminder (F4)
            "task": "app.jobs.checkin_reminder",
            "schedule": crontab(minute=0, hour=8, day_of_week=5),
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
        # M3.1 T-804 / R-DEC-121 — two-way calendar sync (pull incremental), every 5 min default
        "calendar-sync": {
            "task": "app.jobs.calendar_sync",
            "schedule": _cfg.calendar_sync_interval_seconds,
            "options": {"expires": _cfg.calendar_sync_interval_seconds * 2},
        },
        # M3.3 T-819 / R-DEC-134 — CEO Daily Briefing at BRIEFING_TIME (default 06:00 local)
        "generate-briefings": {
            "task": "app.jobs.generate_briefings",
            "schedule": crontab(minute=_BRIEF_M, hour=_BRIEF_H),
        },
        # M3.3 T-821 / R-DEC-135 — Decision Log 30/60/90 review reminders, daily 07:30 local
        "decision-reviews": {
            "task": "app.jobs.decision_reviews",
            "schedule": crontab(minute=30, hour=7),
        },
        # T-1010 / 05 §2.7 (OQ-05-11) — purge C5 import rows past the undo window, daily 02:00
        "purge-import-rows": {
            "task": "app.jobs.purge_import_rows",
            "schedule": crontab(minute=0, hour=2),
        },
        # T-1011 — report (and, when IDP_ORPHAN_SWEEP_DELETE=true, remove) orphan storage files
        "sweep-orphan-storage": {
            "task": "app.jobs.sweep_orphan_storage",
            "schedule": crontab(minute=30, hour=2),
        },
    },
)

app = celery_app
