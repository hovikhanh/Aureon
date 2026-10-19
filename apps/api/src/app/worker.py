"""Celery application for the Aureon IDP worker (T-007; 07 §5, §5.1, §6.2).

Start (from repo root, CLAUDE.md § Commands / 07 §6.3)::

    uv run celery -A app.worker worker --loglevel=info

Beat: no periodic schedule exists yet. If one is added later, run exactly ONE
``celery -A app.worker beat`` instance (07 §5.1 "Celery beat: chỉ 1 instance";
CLAUDE.md § Celery gotcha) — never embed beat in workers via ``-B``.
"""

from typing import Final

# celery 5.6 ships no type stubs / py.typed and the project forbids new deps
# (CLAUDE.md "Cấm tự quyết" #4), so the import is untyped; scoped to this line only.
from celery import Celery  # type: ignore[import-untyped]
from kombu import Queue  # type: ignore[import-untyped]  # same reason: kombu has no py.typed

from app.core.config import get_config

# 07 §5.1 — soft/hard time limit per pipeline step (long extraction overrides per task:
# EXTRACT_LONG_* below, passed as task options by T-211).
SOFT_TIME_LIMIT_S: Final = 120
TIME_LIMIT_S: Final = 150
EXTRACT_LONG_SOFT_TIME_LIMIT_S: Final = 300
EXTRACT_LONG_TIME_LIMIT_S: Final = 330
# 07 §5.1 — result_expires 24 h so Redis does not fill up.
RESULT_EXPIRES_S: Final = 24 * 60 * 60
# 07 §5.1 — queues: `idp` (pipeline), `default` (metric recompute, indexing).
QUEUE_DEFAULT: Final = "default"
QUEUE_IDP: Final = "idp"
# 07 §5.1 retry policy (max 3, backoff 2s → 8s → 30s) lives on IdempotentTask (workers/base.py).

# Task modules registered with the worker (07 §4: tasks live in app/workers/).
TASK_MODULES: Final = ("app.workers.system", "app.workers.idp", "app.workers.dashboard")


def create_celery_app() -> Celery:
    cfg = get_config()
    app = Celery(
        "aureon",
        # Every task defaults to the idempotent base (CLAUDE.md § Celery: all tasks idempotent).
        task_cls="app.workers.base:IdempotentTask",
        include=list(TASK_MODULES),
    )
    app.conf.update(
        # 07 §7 — CELERY_BROKER_URL / CELERY_RESULT_BACKEND via ConfigService only.
        broker_url=cfg.celery_broker_url.get_secret_value(),
        result_backend=cfg.celery_result_backend.get_secret_value(),
        broker_connection_retry_on_startup=True,
        # 07 §5.1 time limits + result expiry.
        task_soft_time_limit=SOFT_TIME_LIMIT_S,
        task_time_limit=TIME_LIMIT_S,
        result_expires=RESULT_EXPIRES_S,
        # JSON only: task args are ids, never pickled objects (07 §8 security).
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # Store UTC internally; local zone only matters for a future beat (proposed DEC).
        enable_utc=True,
        timezone="Asia/Ho_Chi_Minh",
        # Ack after the task finishes so a crashed worker's task is redelivered; safe
        # because tasks are idempotent by task_id (07 §5.1). One message at a time per
        # process keeps long IDP steps from starving siblings (proposed DEC).
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_track_started=True,
        # 07 §5.1 queues.
        task_default_queue=QUEUE_DEFAULT,
        task_queues=(
            Queue(QUEUE_DEFAULT, routing_key=QUEUE_DEFAULT),
            Queue(QUEUE_IDP, routing_key=QUEUE_IDP),
        ),
    )
    return app


celery_app: Final[Celery] = create_celery_app()
