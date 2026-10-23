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


async def recompute(db: AsyncSession) -> dict[str, int]:
    return await MetricStore(db).recompute(business_today())


async def review_sla(db: AsyncSession) -> int:
    return len(await SlaService(db).check_review_sla())


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
