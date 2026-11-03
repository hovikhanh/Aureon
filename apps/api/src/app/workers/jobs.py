"""Scheduled jobs (T-235, DEC-203): beat → these Celery tasks → module public services.

Every job is idempotent per business day (the services guard duplicates), runs in its own
event loop with a NullPool engine and loops over the active tenants (R-DEC-21): one
transaction per tenant, run inside `tenant_scope(tenant)`, so a tenant never sees another
tenant's rows and one tenant's failure does not roll back the others'. Results are summed.
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.clock import business_today
from app.core.tenant import active_tenant_ids, tenant_scope
from app.modules.ai.services.verification import verify_action_outcomes
from app.modules.execution.services.at_risk import AtRiskService, checkin_reminder
from app.modules.execution.services.task_service import detect_overdue_tasks
from app.modules.finance.services.analytics_service import FinanceAnalyticsService
from app.modules.finance.services.invoice_service import InvoiceService
from app.modules.hr.services.hiring_service import detect_delayed_hiring_plans
from app.modules.idp.services.sla_service import SlaService
from app.modules.platform.services.metric_store import MetricStore
from app.worker import celery_app
from app.workers.consumers import load_metric_providers
from app.workers.events import _engine

load_metric_providers()

Job = Callable[[AsyncSession], Awaitable[Any]]

JOB_LIMITS: dict[str, Any] = {"time_limit": 300, "soft_time_limit": 240}


async def _run_tenant(engine: AsyncEngine, tenant: uuid.UUID, job: Job) -> Any:
    with tenant_scope(tenant):
        async with AsyncSession(engine, expire_on_commit=False) as session:
            out = await job(session)
            await session.commit()
            return out


def _merge(total: Any, out: Any) -> Any:
    if total is None:
        return out
    if isinstance(out, dict):
        return {k: total.get(k, 0) + out.get(k, 0) for k in {*total, *out}}
    if isinstance(out, bool):
        return bool(total) or out
    return total + out


async def _run(job: Job) -> Any:
    total: Any = None
    async with _engine() as engine:
        for tenant in active_tenant_ids():
            total = _merge(total, await _run_tenant(engine, tenant, job))
    return total


async def burn_check(db: AsyncSession) -> bool:
    return await FinanceAnalyticsService(db).check_burn_over_forecast(business_today())


async def invoices_overdue(db: AsyncSession) -> int:
    return await InvoiceService(db).mark_overdue(business_today())


async def late_hiring(db: AsyncSession) -> int:
    return len(await detect_delayed_hiring_plans(db, business_today()))


async def overdue_tasks(db: AsyncSession) -> int:
    return len(await detect_overdue_tasks(db, business_today()))


async def kr_at_risk(db: AsyncSession) -> int:
    return await AtRiskService(db).daily(business_today())


async def weekly_checkin_reminder(db: AsyncSession) -> int:
    return await checkin_reminder(db, business_today())


async def recompute(db: AsyncSession) -> dict[str, int]:
    return await MetricStore(db).recompute(business_today())


async def review_sla(db: AsyncSession) -> int:
    return len(await SlaService(db).check_review_sla())


async def calendar_pull(db: AsyncSession) -> int:
    from app.modules.execution.services.calendar_sync import CalendarSyncService

    return await CalendarSyncService(db).pull_all()


async def briefings(db: AsyncSession) -> int:
    from app.modules.ai.services.briefing_service import BriefingService

    return await BriefingService(db).generate_all()


async def decision_reviews(db: AsyncSession) -> int:
    from app.modules.execution.services.meeting_service import MeetingService

    return await MeetingService(db).remind_due_reviews(business_today())


async def purge_import_rows(db: AsyncSession) -> dict[str, int]:
    from app.modules.idp.services.retention_service import purge_import_rows as purge

    return await purge(db)


async def sweep_orphan_storage(db: AsyncSession) -> dict[str, int]:
    from app.modules.idp.services.retention_service import sweep_orphan_storage as sweep

    out = await sweep(db)
    return {k: v for k, v in out.items() if isinstance(v, int)}


@celery_app.task(name="app.jobs.daily_burn_check", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def daily_burn_check() -> bool:
    return bool(asyncio.run(_run(burn_check)))


@celery_app.task(name="app.jobs.mark_invoices_overdue", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def mark_invoices_overdue() -> int:
    return int(asyncio.run(_run(invoices_overdue)))


@celery_app.task(name="app.jobs.detect_late_hiring", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def detect_late_hiring() -> int:
    return int(asyncio.run(_run(late_hiring)))


@celery_app.task(name="app.jobs.detect_overdue_tasks", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def detect_overdue_tasks_job() -> int:
    return int(asyncio.run(_run(overdue_tasks)))


@celery_app.task(name="app.jobs.verify_action_outcome", time_limit=60, soft_time_limit=50)  # type: ignore[untyped-decorator]
def verify_action_outcome() -> int:
    return int(asyncio.run(_run(verify_action_outcomes)))


@celery_app.task(name="app.jobs.recompute_metrics", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def recompute_metrics() -> dict[str, int]:
    result: dict[str, int] = asyncio.run(_run(recompute))
    return result


@celery_app.task(name="app.jobs.check_review_sla", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def check_review_sla() -> int:
    """Hourly (T-412): escalate overdue IDP reviews → `idp.review_escalated` + notification."""
    return int(asyncio.run(_run(review_sla)))


@celery_app.task(name="app.jobs.detect_kr_at_risk", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def detect_kr_at_risk() -> int:
    return int(asyncio.run(_run(kr_at_risk)))


@celery_app.task(name="app.jobs.checkin_reminder", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def checkin_reminder_job() -> int:
    return int(asyncio.run(_run(weekly_checkin_reminder)))


@celery_app.task(name="app.jobs.calendar_sync", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def calendar_sync() -> int:
    """M3.1 T-804: every CALENDAR_SYNC_INTERVAL_SECONDS pull incremental changes per account."""
    return int(asyncio.run(_run(calendar_pull)))


@celery_app.task(name="app.jobs.generate_briefings", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def generate_briefings() -> int:
    """M3.3 T-819/T-819b: at BRIEFING_TIME snapshot one CEO Daily Briefing per active CEO/DIR
    (idempotent per recipient/day) + e-mail summary (no level-3/4 data)."""
    return int(asyncio.run(_run(briefings)))


@celery_app.task(name="app.jobs.decision_reviews", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def decision_reviews_job() -> int:
    """M3.3 T-821 (R-DEC-135): daily Decision Log 30/60/90 review reminder to the owner,
    idempotent per (decision, review date)."""
    return int(asyncio.run(_run(decision_reviews)))


@celery_app.task(name="app.jobs.purge_import_rows", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def purge_import_rows_job() -> dict[str, int]:
    """T-1010 (05 §2.7 / OQ-05-11): drop C5 `import_rows` of finished batches whose 7-day undo
    window closed. Idempotent — a second run finds nothing. `extracted_fields` are kept."""
    out = asyncio.run(_run(purge_import_rows))
    return dict(out or {"batches": 0, "rows": 0})


@celery_app.task(name="app.jobs.sweep_orphan_storage", **JOB_LIMITS)  # type: ignore[untyped-decorator]
def sweep_orphan_storage_job() -> dict[str, int]:
    """T-1011 (handover `IDP_Operations.md` §5.1 as code): report object-store files with no
    `source_documents` row; deletes them only when `IDP_ORPHAN_SWEEP_DELETE=true`."""
    out = asyncio.run(_run(sweep_orphan_storage))
    return dict(out or {"scanned": 0, "orphans": 0, "deleted": 0})
