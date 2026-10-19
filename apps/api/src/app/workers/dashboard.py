"""Celery task for the dynamic metric/alert engine (T-304).

``recompute_metrics_task`` re-derives metric ACTUAL values and alert states from
committed ``business_records``. It is idempotent: re-running it for the same inputs
supersedes the current value with an equivalent one and leaves at most one open alert
per metric (the engine itself enforces this). The task is normally enqueued after a
batch commit or on a daily schedule; the synchronous ``recompute_for_record_type``
hook in the Action Registry handles the per-document case.
"""

from __future__ import annotations

import logging
from typing import Any

from app.db.session import SessionLocal
from app.modules.dashboard.engine import recompute_metrics
from app.worker import QUEUE_DEFAULT, celery_app
from app.workers.base import IdempotentTask

logger = logging.getLogger(__name__)


@celery_app.task(  # type: ignore[untyped-decorator]
    base=IdempotentTask,
    bind=True,
    name="app.workers.dashboard.recompute_metrics",
    queue=QUEUE_DEFAULT,
    max_retries=3,
)
def recompute_metrics_task(
    self: Any,
    metric_codes: list[str] | None = None,
    period_key: str | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Recompute metrics from business records and commit. Returns the codes recomputed."""
    logger.info("recompute_metrics_task start (codes=%s period=%s)", metric_codes, period_key)
    if db is not None:
        recomputed = recompute_metrics(db, metric_codes, period_key)
        db.commit()
        return {"recomputed": recomputed}
    with SessionLocal() as session:
        recomputed = recompute_metrics(session, metric_codes, period_key)
        session.commit()
        return {"recomputed": recomputed}
