"""System tasks proving the worker runs (T-007)."""

from app.worker import QUEUE_DEFAULT, celery_app


# celery_app is untyped (no celery stubs), so its decorator is untyped for mypy strict.
@celery_app.task(name="app.workers.system.ping", queue=QUEUE_DEFAULT)  # type: ignore[untyped-decorator]
def ping() -> str:
    """Liveness probe task: `celery -A app.worker call app.workers.system.ping`."""
    return "pong"
